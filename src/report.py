"""Render docs/results.md from a results payload.

The input is the same dict that is written to results/bench_<sha8>.json, so
the report can be rebuilt from a stored run without Ollama:

    python -m src.report results/bench_f6042d92.json

The latency table uses the aggregates stored in the payload (medians and p95
from src/bench/results_writer.py), so docs/results.md, the console table and
the JSON file always show the same numbers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.schema import CostProfile

RESULTS_MD = Path(__file__).resolve().parents[1] / "docs" / "results.md"

PROMPT_CLASS_ORDER = ["short", "medium", "long"]

LATENCY_COLUMNS = ["Model", "Prompt class", "Runs ok", "Median TTFT (ms)", "Median tok/s", "P95 total (ms)"]


def _ms(value: float | None) -> str:
    return "—" if value is None else f"{value:,.0f}"


def latency_row(aggregate: dict) -> list[str]:
    """Format one aggregate cell as table cells, in LATENCY_COLUMNS order."""
    tps = aggregate["median_tokens_per_sec"]
    return [
        aggregate["model"],
        aggregate["prompt_class"],
        f"{aggregate['n_ok']}/{aggregate['n']}",
        _ms(aggregate["median_ttft_ms"]),
        "—" if tps is None else f"{tps:.2f}",
        _ms(aggregate["p95_total_ms"]),
    ]


def sorted_aggregates(aggregates: list[dict]) -> list[dict]:
    """Order cells by model, then short / medium / long."""
    return sorted(aggregates, key=lambda a: (a["model"], PROMPT_CLASS_ORDER.index(a["prompt_class"])))


def render_report(payload: dict) -> str:
    """Build the markdown text of docs/results.md from a results payload."""
    runs = payload["runs"]
    sha = payload["source_commit_sha"] or "no git commit"

    lines = [
        "# LLM Serving Cost — Benchmark Results",
        "",
        "Generated from `results/bench_<sha8>.json` by `src/report.py`.",
        "",
        f"Source commit: `{sha}` · worktree clean: {payload['worktree_clean']} · "
        f"Total runs: {len(runs)} · Models: {', '.join(payload['models'])}",
        "",
        "## Latency & Throughput",
        "",
        "Medians over successful runs; p95 over successful runs' total time. "
        "tok/s = output tokens / total request time, including time to first token.",
        "",
        "| " + " | ".join(LATENCY_COLUMNS) + " |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for agg in sorted_aggregates(payload["aggregates"]):
        cells = latency_row(agg)
        cells[0] = f"`{cells[0]}`"
        lines.append("| " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Cost model (local server vs hosted API)",
        "",
        "> Local: an assumed ~$50/month dedicated server (an input, not a measurement).",
        "> API: illustrative hosted pricing, $0.15 input / $0.60 output per 1M tokens, blended 40/60.",
        "> Capacity: mean tok/s over all successful runs of the model, running 24/7 for 30 days.",
        "",
        "| Model | Mean tok/s | Capacity (tok/month) | Local $/1M tok | API $/1M tok "
        "| Break-even (tok/month) | Reachable |",
        "|-------|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for cp in (CostProfile(**d) for d in payload["cost_profiles"]):
        lines.append(
            f"| `{cp.model}` | {cp.tokens_per_sec} | {cp.capacity_tokens_month:,} "
            f"| ${cp.local_cost_per_1m:.2f} | ${cp.api_cost_per_1m:.2f} "
            f"| {cp.breakeven_tokens_month:,} | {'yes' if cp.breakeven_reachable else 'no'} |"
        )

    lines += [
        "",
        "## Per-run Raw Data",
        "",
        "| Model | Prompt | Class | TTFT (ms) | Total (ms) | tok/s | Output tok | Error |",
        "|-------|--------|-------|:---:|:---:|:---:|:---:|:---:|",
    ]
    for r in runs:
        lines.append(
            f"| `{r['model']}` | {r['prompt_id']} | {r['prompt_class']} | {r['ttft_ms']}"
            f" | {r['total_ms']} | {r['tokens_per_sec']} | {r['output_tokens']} | {r['error'] or ''} |"
        )

    return "\n".join(lines) + "\n"


def write_report(payload: dict) -> Path:
    """Write docs/results.md from a results payload and return its path."""
    RESULTS_MD.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_MD.write_text(render_report(payload), encoding="utf-8")
    return RESULTS_MD


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.report results/bench_<sha8>.json")
    stored = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(f"Wrote {write_report(stored)}")
