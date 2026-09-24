"""Tests for src/bench/benchmark.py: TTFT and tokens/s computed from a fake stream.

No real HTTP call is made — httpx.Client is monkeypatched with a fake streaming
client so the timing/parsing logic can be tested deterministically.
"""

from __future__ import annotations

import json

import pytest

from src.bench import benchmark


class _FakeResponse:
    def __init__(self, lines, status_ok=True):
        self._lines = lines
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise benchmark.httpx.HTTPStatusError("bad status", request=None, response=None)

    def iter_lines(self):
        yield from self._lines


class _FakeStreamCtx:
    def __init__(self, response):
        self._response = response

    def __enter__(self):
        return self._response

    def __exit__(self, *exc_info):
        return False


class _FakeClient:
    def __init__(self, lines, status_ok=True, *args, **kwargs):
        self._lines = lines
        self._status_ok = status_ok

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def stream(self, method, url, json):
        return _FakeStreamCtx(_FakeResponse(self._lines, self._status_ok))


def _ollama_lines(tokens: list[str], eval_count: int):
    lines = [json.dumps({"response": tok, "done": False}).encode() for tok in tokens]
    lines.append(json.dumps({"done": True, "eval_count": eval_count}).encode())
    return lines


def test_run_single_computes_ttft_and_tokens_per_sec(monkeypatch):
    # run_single calls perf_counter exactly 3 times on the happy path:
    # t_start, t_first (on the first response chunk), t_end (after done).
    ticks = iter([0.0, 0.01, 0.10])

    def fake_perf_counter():
        return next(ticks)

    lines = _ollama_lines(["Hello", " world", "!"], eval_count=3)
    monkeypatch.setattr(benchmark.time, "perf_counter", fake_perf_counter)
    monkeypatch.setattr(
        benchmark.httpx, "Client", lambda *a, **k: _FakeClient(lines)
    )

    prompt = {"id": "short-1", "class": "short", "text": "hello there"}
    result = benchmark.run_single("qwen3:4b", prompt)

    assert result.error is None
    assert result.model == "qwen3:4b"
    assert result.output_tokens == 3
    # t_start=0.0, t_first=0.01 -> ttft = 10ms
    assert result.ttft_ms == 10.0
    # t_end=0.10 -> total_ms = 100ms; tokens_per_sec = 3 / 0.1 = 30.0
    assert result.total_ms == 100.0
    assert result.tokens_per_sec == 30.0


def test_run_single_records_error_on_exception(monkeypatch):
    ticks = iter([0.0, 0.05])

    def fake_perf_counter():
        return next(ticks)

    def raising_client(*a, **k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(benchmark.time, "perf_counter", fake_perf_counter)
    monkeypatch.setattr(benchmark.httpx, "Client", raising_client)

    prompt = {"id": "short-1", "class": "short", "text": "hello"}
    result = benchmark.run_single("qwen3:4b", prompt)

    assert result.error == "connection refused"
    assert result.output_tokens == 0
    # No first token observed -> ttft falls back to total elapsed time
    assert result.ttft_ms == 50.0


def test_run_single_skips_malformed_json_lines(monkeypatch):
    ticks = iter([0.0, 0.02, 0.05])

    def fake_perf_counter():
        return next(ticks)

    lines = [b"not-json", json.dumps({"response": "ok", "done": False}).encode()]
    lines.append(json.dumps({"done": True, "eval_count": 1}).encode())

    monkeypatch.setattr(benchmark.time, "perf_counter", fake_perf_counter)
    monkeypatch.setattr(benchmark.httpx, "Client", lambda *a, **k: _FakeClient(lines))

    prompt = {"id": "short-1", "class": "short", "text": "hi"}
    result = benchmark.run_single("qwen3:4b", prompt)

    assert result.error is None
    assert result.output_tokens == 1


def test_load_prompts_reads_jsonl_and_skips_blank_lines(tmp_path, monkeypatch):
    fake_prompts = tmp_path / "prompts.jsonl"
    fake_prompts.write_text(
        '{"id": "a", "class": "short", "text": "x"}\n\n{"id": "b", "class": "long", "text": "y"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(benchmark, "PROMPTS_PATH", fake_prompts)

    prompts = benchmark.load_prompts()

    assert [p["id"] for p in prompts] == ["a", "b"]


def test_count_words_scales_with_word_count():
    assert benchmark._count_words("one two three") == max(1, int(3 * 1.3))
    assert benchmark._count_words("") == 1
