"""Assemble and write the raw benchmark provenance file.

`run_bench.py` writes one JSON file per run to `results/bench_<sha8>.json`.
It carries every per-request measurement plus enough context (model, host,
hardware, git commit, warm-up protocol) that the numbers in `docs/results.md`
can be traced back to exactly how they were produced.

Building the payload is pure — no file I/O, no clock reads beyond the
`now` callable passed in — so it is fully unit-testable.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from src.schema import BenchmarkRun, CostProfile

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"

WARMUP_PROTOCOL = "none — no warm-up requests are issued; every run, including the first, is recorded"


def _percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[idx]


def _aggregate_cell(runs: list[BenchmarkRun]) -> dict:
    ok = [r for r in runs if r.error is None]
    if not ok:
        return {
            "n": len(runs),
            "n_ok": 0,
            "error_rate": 1.0,
            "median_ttft_ms": None,
            "median_tokens_per_sec": None,
            "p95_total_ms": None,
        }
    return {
        "n": len(runs),
        "n_ok": len(ok),
        "error_rate": round(1 - len(ok) / len(runs), 3),
        "median_ttft_ms": round(statistics.median(r.ttft_ms for r in ok), 1),
        "median_tokens_per_sec": round(statistics.median(r.tokens_per_sec for r in ok), 2),
        "p95_total_ms": round(_percentile95([r.total_ms for r in ok]), 1),
    }


def build_aggregates(runs: list[BenchmarkRun]) -> list[dict]:
    """One median/p95 aggregate row per (model, prompt_class) cell present in runs."""
    cells = sorted({(r.model, r.prompt_class) for r in runs})
    aggregates = []
    for model, prompt_class in cells:
        cell_runs = [r for r in runs if r.model == model and r.prompt_class == prompt_class]
        row = {"model": model, "prompt_class": prompt_class}
        row.update(_aggregate_cell(cell_runs))
        aggregates.append(row)
    return aggregates


def build_results_payload(
    *,
    runs: list[BenchmarkRun],
    cost_profiles: list[CostProfile],
    models: list[str],
    ollama_host: str,
    hardware: str,
    repetitions: int,
    source_commit_sha: str | None,
    worktree_clean: bool,
    now: Callable[[], str],
) -> dict:
    """Build the full JSON-serializable provenance payload."""
    return {
        "timestamp": now(),
        "source_commit_sha": source_commit_sha,
        "worktree_clean": worktree_clean,
        "models": models,
        "ollama_host": ollama_host,
        "hardware": hardware,
        "repetitions_per_cell": repetitions,
        "warmup_protocol": WARMUP_PROTOCOL,
        "runs": [asdict(r) for r in runs],
        "aggregates": build_aggregates(runs),
        "cost_profiles": [asdict(cp) for cp in cost_profiles],
    }


def sha8(source_commit_sha: str | None) -> str:
    """Short id used in the results filename; 'nogit' when there is no commit."""
    if not source_commit_sha:
        return "nogit"
    return source_commit_sha[:8]


def write_results_json(payload: dict, sha8_id: str, results_dir: Path = RESULTS_DIR) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / f"bench_{sha8_id}.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path
