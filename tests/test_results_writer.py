"""Tests for src/bench/results_writer.py: payload assembly and file writing."""

from __future__ import annotations

import json

from src.bench.results_writer import (
    build_aggregates,
    build_results_payload,
    sha8,
    write_results_json,
)
from src.schema import BenchmarkRun, CostProfile


def _run(model="qwen3:4b", prompt_class="short", ttft_ms=100.0, total_ms=200.0, tps=5.0, error=None):
    return BenchmarkRun(
        model=model,
        prompt_id="short-1",
        prompt_class=prompt_class,
        prompt_tokens=10,
        output_tokens=25,
        ttft_ms=ttft_ms,
        total_ms=total_ms,
        tokens_per_sec=tps,
        error=error,
    )


def test_sha8_truncates_full_sha():
    assert sha8("abcdef0123456789") == "abcdef01"


def test_sha8_falls_back_when_no_git():
    assert sha8(None) == "nogit"


def test_build_aggregates_computes_median_and_p95_per_cell():
    runs = [
        _run(ttft_ms=100.0, total_ms=100.0, tps=4.0),
        _run(ttft_ms=200.0, total_ms=200.0, tps=6.0),
        _run(ttft_ms=300.0, total_ms=300.0, tps=8.0),
    ]
    aggregates = build_aggregates(runs)
    assert len(aggregates) == 1
    row = aggregates[0]
    assert row["model"] == "qwen3:4b"
    assert row["prompt_class"] == "short"
    assert row["n"] == 3
    assert row["n_ok"] == 3
    assert row["median_ttft_ms"] == 200.0
    assert row["median_tokens_per_sec"] == 6.0


def test_build_aggregates_excludes_errors_from_median_but_counts_error_rate():
    runs = [_run(tps=4.0), _run(tps=6.0), _run(tps=0.0, error="timeout")]
    row = build_aggregates(runs)[0]
    assert row["n"] == 3
    assert row["n_ok"] == 2
    assert row["error_rate"] == round(1 / 3, 3)


def test_build_aggregates_p95_picks_the_95th_percentile_index():
    # 20 runs with total_ms = 1..20; p95 index = int(20*0.95)-1 = 18 -> value 19
    runs = [_run(total_ms=float(i)) for i in range(1, 21)]
    assert build_aggregates(runs)[0]["p95_total_ms"] == 19.0


def test_build_aggregates_all_failed_cell_has_no_medians():
    row = build_aggregates([_run(error="boom"), _run(error="boom again")])[0]
    assert row["n_ok"] == 0
    assert row["error_rate"] == 1.0
    assert row["median_ttft_ms"] is None
    assert row["p95_total_ms"] is None


def test_build_aggregates_separates_different_models_and_classes():
    runs = [
        _run(model="qwen3:4b", prompt_class="short"),
        _run(model="qwen3:4b", prompt_class="long"),
        _run(model="other", prompt_class="short"),
    ]
    aggregates = build_aggregates(runs)
    assert len(aggregates) == 3


def test_build_results_payload_contains_provenance_fields():
    runs = [_run()]
    cost_profiles = [
        CostProfile(
            model="qwen3:4b",
            tokens_per_sec=4.0,
            api_cost_per_1m=0.42,
            local_cost_per_1m=0.005,
            breakeven_tokens_month=119047619,
            capacity_tokens_month=10_368_000,
        )
    ]
    payload = build_results_payload(
        runs=runs,
        cost_profiles=cost_profiles,
        models=["qwen3:4b"],
        ollama_host="http://127.0.0.1:11434",
        hardware="test-rig",
        repetitions=2,
        source_commit_sha="deadbeef01",
        worktree_clean=True,
        now=lambda: "2026-01-01T00:00:00+00:00",
    )

    assert payload["source_commit_sha"] == "deadbeef01"
    assert payload["worktree_clean"] is True
    assert payload["models"] == ["qwen3:4b"]
    assert payload["hardware"] == "test-rig"
    assert payload["repetitions_per_cell"] == 2
    assert "warmup_protocol" in payload
    assert len(payload["runs"]) == 1
    assert len(payload["aggregates"]) == 1
    assert len(payload["cost_profiles"]) == 1
    assert payload["timestamp"] == "2026-01-01T00:00:00+00:00"


def test_write_results_json_writes_readable_utf8_json(tmp_path):
    payload = {"a": 1, "arabic": "اختبار"}
    out_path = write_results_json(payload, "deadbeef", results_dir=tmp_path)

    assert out_path == tmp_path / "bench_deadbeef.json"
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded == payload
