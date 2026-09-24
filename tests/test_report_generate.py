"""Tests for report aggregation and markdown generation in src/report/generate.py."""

from __future__ import annotations

from src.report.generate import _summarize, write_report
from src.schema import BenchmarkRun, CostProfile


def _run(model="qwen3:4b", prompt_id="short-1", prompt_class="short",
         ttft_ms=100.0, total_ms=200.0, tps=5.0, output_tokens=30, error=None):
    return BenchmarkRun(
        model=model,
        prompt_id=prompt_id,
        prompt_class=prompt_class,
        prompt_tokens=10,
        output_tokens=output_tokens,
        ttft_ms=ttft_ms,
        total_ms=total_ms,
        tokens_per_sec=tps,
        error=error,
    )


def test_summarize_averages_successful_runs_only():
    runs = [
        _run(ttft_ms=100.0, total_ms=200.0, tps=4.0),
        _run(ttft_ms=200.0, total_ms=400.0, tps=6.0),
        _run(ttft_ms=999.0, total_ms=999.0, tps=0.0, error="timeout"),
    ]
    summary = _summarize(runs, "qwen3:4b", "short")

    assert summary.n == 2
    assert summary.avg_ttft_ms == 150.0
    assert summary.avg_tokens_per_sec == 5.0
    # error_rate counts the failed run against all runs in the cell (1 of 3)
    assert summary.error_rate == round(1 - 2 / 3, 3)


def test_summarize_all_failed_returns_zeroed_summary_with_full_error_rate():
    runs = [_run(error="boom"), _run(error="boom again")]
    summary = _summarize(runs, "qwen3:4b", "short")

    assert summary.n == 0
    assert summary.error_rate == 1.0
    assert summary.avg_ttft_ms == 0


def test_summarize_p95_picks_the_95th_percentile_index():
    # 20 runs with total_ms = 1..20; p95 index = int(20*0.95)-1 = 18 -> value 19
    runs = [_run(total_ms=float(i), tps=1.0) for i in range(1, 21)]
    summary = _summarize(runs, "qwen3:4b", "short")
    assert summary.p95_total_ms == 19.0


def test_summarize_ignores_other_models_and_classes():
    runs = [
        _run(model="qwen3:4b", prompt_class="short", ttft_ms=10.0),
        _run(model="qwen3:4b", prompt_class="long", ttft_ms=999.0),
        _run(model="other-model", prompt_class="short", ttft_ms=999.0),
    ]
    summary = _summarize(runs, "qwen3:4b", "short")
    assert summary.n == 1
    assert summary.avg_ttft_ms == 10.0


def test_write_report_produces_expected_sections(tmp_path, monkeypatch):
    import src.report.generate as generate_module

    fake_path = tmp_path / "results.md"
    monkeypatch.setattr(generate_module, "RESULTS_MD", fake_path)

    runs = [_run(model="qwen3:4b", prompt_class="short", ttft_ms=100.0, total_ms=200.0, tps=5.0)]
    cost_profiles = [
        CostProfile(
            model="qwen3:4b",
            tokens_per_sec=5.0,
            api_cost_per_1k=0.42,
            local_cost_per_1k=0.005,
            breakeven_tokens_month=119048,
        )
    ]

    write_report(runs, cost_profiles)

    text = fake_path.read_text(encoding="utf-8")
    assert "# LLM Serving Cost — Benchmark Results" in text
    assert "Total runs: 1 · Models: qwen3:4b" in text
    assert "| `qwen3:4b` | short |" in text
    assert "119,048" in text
    assert "## Per-run Raw Data" in text
