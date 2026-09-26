"""Main benchmark runner.

Run:  python run_bench.py [--model MODEL] [--allow-dirty]
Produces: docs/results.md, results/bench_<sha8>.json, and a printed table.

What it measures per (model, prompt) pair:
- TTFT  (Time To First Token): perceived latency for the user
- tokens/sec: sustained throughput during generation
- P95 total latency: worst-case tail

Why streaming?
Ollama's streaming API sends each token as it is generated. This is the only
way to measure TTFT accurately — without streaming we only see total latency.

Provenance: refuses to run on an uncommitted tree, or outside a git
repository, unless --allow-dirty is passed. Every run writes its raw
per-request data to results/bench_<sha8>.json, keyed by the commit it ran on.
"""

from __future__ import annotations

import argparse
import io
import sys
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.table import Table

from src.bench.benchmark import load_prompts, run_single
from src.bench.cost import build_cost_profile
from src.bench.provenance import DirtyWorktreeError, check_provenance
from src.bench.results_writer import build_results_payload, sha8, write_results_json
from src.config import settings
from src.report import LATENCY_COLUMNS, latency_row, sorted_aggregates, write_report

console = Console(file=sys.stdout)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the LLM serving benchmark.")
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Model to benchmark (repeatable). Defaults to BENCH_MODELS from .env.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Run even with uncommitted changes or outside a git repository.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    try:
        source_commit_sha, worktree_clean = check_provenance(args.allow_dirty)
    except DirtyWorktreeError as exc:
        console.print(f"[red]Refusing to run:[/red] {exc}")
        raise SystemExit(1) from exc

    prompts = load_prompts()
    models = args.models if args.models else settings.models

    console.print(f"[bold]Models:[/bold] {models}")
    console.print(f"[bold]Prompts:[/bold] {len(prompts)} · [bold]Runs/cell:[/bold] {settings.runs_per_cell}")
    console.print("")

    runs = []
    for model in models:
        for prompt in prompts:
            for run_i in range(1, settings.runs_per_cell + 1):
                label = f"{model} | {prompt['id']} | run {run_i}"
                console.print(f"[dim]  {label}...[/dim]", end=" ")
                result = run_single(model, prompt)
                runs.append(result)
                if result.error:
                    console.print(f"[red]ERR[/red] {result.error[:60]}")
                else:
                    console.print(
                        f"[green]ok[/green] TTFT={result.ttft_ms:.0f}ms "
                        f"tok/s={result.tokens_per_sec:.1f} out={result.output_tokens}"
                    )

    # Cost profiles
    cost_profiles = []
    for model in models:
        ok_runs = [r for r in runs if r.model == model and r.error is None]
        if ok_runs:
            avg_tps = sum(r.tokens_per_sec for r in ok_runs) / len(ok_runs)
            cost_profiles.append(build_cost_profile(model, avg_tps))

    payload = build_results_payload(
        runs=runs,
        cost_profiles=cost_profiles,
        models=models,
        ollama_host=settings.ollama_host,
        hardware=settings.hardware,
        repetitions=settings.runs_per_cell,
        source_commit_sha=source_commit_sha,
        worktree_clean=worktree_clean,
        now=lambda: datetime.now(timezone.utc).isoformat(),
    )
    print_summary(payload["aggregates"])
    console.print(f"[bold]Wrote[/bold] {write_results_json(payload, sha8(source_commit_sha))}")
    console.print(f"[bold]Wrote[/bold] {write_report(payload)}")


def print_summary(aggregates: list[dict]) -> None:
    """Print the same median/p95 table that docs/results.md shows."""
    table = Table(title="Results Summary", header_style="bold")
    for i, col in enumerate(LATENCY_COLUMNS):
        table.add_column(col, justify="left" if i < 2 else "right")
    for agg in sorted_aggregates(aggregates):
        table.add_row(*latency_row(agg))
    console.print(table)


if __name__ == "__main__":
    main()
