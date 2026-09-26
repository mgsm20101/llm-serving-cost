"""Generate a markdown report from benchmark results.

Called by run_bench.py after all runs complete. Writes docs/results.md with:
- Per-model summary table (TTFT, tokens/sec, error rate)
- Per-prompt-class breakdown
- Cost profiles (local vs API break-even)
"""

from __future__ import annotations

import statistics
from pathlib import Path

from src.schema import BenchmarkRun, BenchmarkSummary, CostProfile

RESULTS_MD = Path(__file__).resolve().parents[1] / "docs" / "results.md"


def _summarize(runs: list[BenchmarkRun], model: str, prompt_class: str) -> BenchmarkSummary:
    cell = [r for r in runs if r.model == model and r.prompt_class == prompt_class and r.error is None]
    if not cell:
        return BenchmarkSummary(
            model=model, prompt_class=prompt_class, n=0,
            avg_ttft_ms=0, avg_tokens_per_sec=0, avg_output_tokens=0,
            p95_total_ms=0, error_rate=1.0,
        )
    all_cell = [r for r in runs if r.model == model and r.prompt_class == prompt_class]
    totals = sorted(r.total_ms for r in cell)
    p95_idx = max(0, int(len(totals) * 0.95) - 1)
    return BenchmarkSummary(
        model=model,
        prompt_class=prompt_class,
        n=len(cell),
        avg_ttft_ms=round(statistics.mean(r.ttft_ms for r in cell), 1),
        avg_tokens_per_sec=round(statistics.mean(r.tokens_per_sec for r in cell), 2),
        avg_output_tokens=round(statistics.mean(r.output_tokens for r in cell), 1),
        p95_total_ms=round(totals[p95_idx], 1),
        error_rate=round(1 - len(cell) / len(all_cell), 3),
    )


def write_report(runs: list[BenchmarkRun], cost_profiles: list[CostProfile]) -> None:
    models = sorted({r.model for r in runs})
    classes = ["short", "medium", "long"]

    lines = [
        "# LLM Serving Cost — Benchmark Results",
        "",
        f"Total runs: {len(runs)} · Models: {', '.join(models)}",
        "",
        "## Latency & Throughput",
        "",
        "| Model | Prompt class | Avg TTFT (ms) | Avg tok/s | P95 total (ms) | Avg output tokens |",
        "|-------|-------------|:---:|:---:|:---:|:---:|",
    ]
    for model in models:
        for pc in classes:
            s = _summarize(runs, model, pc)
            if s.n == 0:
                continue
            lines.append(
                f"| `{model}` | {pc} | {s.avg_ttft_ms} | {s.avg_tokens_per_sec} "
                f"| {s.p95_total_ms} | {s.avg_output_tokens:.0f} |"
            )

    lines += [
        "",
        "## Cost model (local server vs hosted API)",
        "",
        "> Local: an assumed ~$50/month dedicated server (an input, not a measurement).",
        "> API: illustrative hosted pricing, $0.15 input / $0.60 output per 1M tokens, blended 40/60.",
        "> Capacity: measured tok/s running 24/7 for 30 days on the benchmark machine.",
        "",
        "| Model | Avg tok/s | Capacity (tok/month) | Local $/1M tok | API $/1M tok "
        "| Break-even (tok/month) | Reachable |",
        "|-------|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for cp in cost_profiles:
        lines.append(
            f"| `{cp.model}` | {cp.tokens_per_sec} | {cp.capacity_tokens_month:,} "
            f"| ${cp.local_cost_per_1m:.2f} | ${cp.api_cost_per_1m:.2f} "
            f"| {cp.breakeven_tokens_month:,} | {'yes' if cp.breakeven_reachable else 'no'} |"
        )

    lines += [
        "",
        "## Per-run Raw Data",
        "",
        "| Model | Prompt | Class | TTFT (ms) | tok/s | Output tok | Error |",
        "|-------|--------|-------|:---:|:---:|:---:|:---:|",
    ]
    for r in runs:
        lines.append(
            f"| `{r.model}` | {r.prompt_id} | {r.prompt_class} | {r.ttft_ms}"
            f" | {r.tokens_per_sec} | {r.output_tokens} | {r.error or ''} |"
        )

    RESULTS_MD.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {RESULTS_MD}")
