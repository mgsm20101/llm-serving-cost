"""Core benchmarking logic.

run_single streams one request to Ollama's /api/generate and returns a
BenchmarkRun with TTFT, total latency and tokens/sec. tokens/sec is
output tokens / total request time, so it includes the time to first token
(prompt processing, and model loading on a cold first request); it is not
decode-only throughput. The repetition loop lives in run_bench.py.

Why streaming? Streaming is the only way to measure TTFT accurately — it gives
us the exact moment the first token arrives from the model.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from src.config import settings
from src.schema import BenchmarkRun

PROMPTS_PATH = Path(__file__).resolve().parents[2] / "data" / "prompts.jsonl"


def load_prompts() -> list[dict]:
    return [
        json.loads(line)
        for line in PROMPTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _count_words(text: str) -> int:
    """Rough token estimate: words × 1.3 (Arabic words tend to be token-heavy)."""
    return max(1, int(len(text.split()) * 1.3))


def run_single(model: str, prompt: dict) -> BenchmarkRun:
    """Stream one generation and record timing metrics."""
    url = f"{settings.ollama_host.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt["text"],
        "stream": True,
        "options": {"temperature": 0, "num_predict": 300},
    }

    t_start = time.perf_counter()
    t_first: float | None = None
    output_tokens = 0
    error: str | None = None

    try:
        with httpx.Client(timeout=600) as client:
            with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    if t_first is None and chunk.get("response"):
                        t_first = time.perf_counter()

                    if chunk.get("response"):
                        # Ollama reports per-token so count each chunk
                        output_tokens += 1

                    if chunk.get("done"):
                        # Ollama gives eval_count (actual output token count)
                        output_tokens = chunk.get("eval_count", output_tokens)
                        break
    except Exception as exc:
        error = str(exc)

    t_end = time.perf_counter()
    ttft_ms = (t_first - t_start) * 1000 if t_first else (t_end - t_start) * 1000
    total_ms = (t_end - t_start) * 1000
    tokens_per_sec = (output_tokens / (total_ms / 1000)) if total_ms > 0 and output_tokens > 0 else 0.0

    return BenchmarkRun(
        model=model,
        prompt_id=prompt["id"],
        prompt_class=prompt["class"],
        prompt_tokens=_count_words(prompt["text"]),
        output_tokens=output_tokens,
        ttft_ms=round(ttft_ms, 1),
        total_ms=round(total_ms, 1),
        tokens_per_sec=round(tokens_per_sec, 2),
        error=error,
    )
