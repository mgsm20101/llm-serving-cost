"""Tests for markdown rendering in src/report.py."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import src.report as report_module
from src.bench.results_writer import build_aggregates
from src.report import latency_row, render_report, sorted_aggregates, write_report
from src.schema import BenchmarkRun, CostProfile

STORED_RESULTS = Path(__file__).resolve().parents[1] / "results" / "bench_f6042d92.json"


def _run(model="qwen3:4b", prompt_class="short", ttft_ms=100.0, total_ms=200.0, tps=5.0, error=None):
    return BenchmarkRun(
        model=model,
        prompt_id=f"{prompt_class}-1",
        prompt_class=prompt_class,
        prompt_tokens=10,
        output_tokens=30,
        ttft_ms=ttft_ms,
        total_ms=total_ms,
        tokens_per_sec=tps,
        error=error,
    )


def _payload(runs):
    return {
        "source_commit_sha": "deadbeef01",
        "worktree_clean": True,
        "models": sorted({r.model for r in runs}),
        "runs": [asdict(r) for r in runs],
        "aggregates": build_aggregates(runs),
        "cost_profiles": [
            asdict(
                CostProfile(
                    model="qwen3:4b",
                    tokens_per_sec=5.0,
                    api_cost_per_1m=0.42,
                    local_cost_per_1m=0.005,
                    breakeven_tokens_month=119047619,
                    capacity_tokens_month=10_368_000,
                )
            )
        ],
    }


def test_latency_row_formats_medians_and_run_counts():
    agg = build_aggregates([_run(ttft_ms=1190.96, total_ms=24879.4, tps=9.5234)])[0]

    assert latency_row(agg) == ["qwen3:4b", "short", "1/1", "1,191", "9.52", "24,879"]


def test_latency_row_shows_dash_when_every_run_failed():
    agg = build_aggregates([_run(error="boom"), _run(error="boom again")])[0]

    assert latency_row(agg) == ["qwen3:4b", "short", "0/2", "—", "—", "—"]


def test_sorted_aggregates_orders_short_medium_long_within_model():
    runs = [_run(prompt_class=pc) for pc in ["long", "short", "medium"]]

    order = [a["prompt_class"] for a in sorted_aggregates(build_aggregates(runs))]

    assert order == ["short", "medium", "long"]


def test_write_report_produces_expected_sections(tmp_path, monkeypatch):
    fake_path = tmp_path / "results.md"
    monkeypatch.setattr(report_module, "RESULTS_MD", fake_path)

    assert write_report(_payload([_run()])) == fake_path

    text = fake_path.read_text(encoding="utf-8")
    assert "# LLM Serving Cost — Benchmark Results" in text
    assert "Source commit: `deadbeef01`" in text
    assert "Total runs: 1 · Models: qwen3:4b" in text
    assert "| `qwen3:4b` | short | 1/1 | 100 | 5.00 | 200 |" in text
    assert "119,047,619" in text
    assert "| no |" in text
    assert "## Per-run Raw Data" in text


def test_report_from_stored_results_shows_the_published_medians():
    payload = json.loads(STORED_RESULTS.read_text(encoding="utf-8"))

    text = render_report(payload)

    # The same medians the README quotes for the f6042d92 run.
    assert "| `gemma3:4b` | short | 4/4 | 1,191 | 9.52 | 24,879 |" in text
    assert "| `qwen2.5-coder:3b` | long | 4/4 | 578 | 8.32 | 36,180 |" in text
    assert "| `gemma3:4b` | 9.77 | 25,321,680 | $1.97 | $0.42 | 119,047,619 | no |" in text
