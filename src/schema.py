"""Contracts for benchmark results.

A single BenchmarkRun captures every measurable metric for one (model, prompt) pair.
BenchmarkSummary aggregates across a prompt_class (short/medium/long).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BenchmarkRun:
    model: str                    # e.g. "qwen3:4b"
    prompt_id: str                # from prompts.jsonl
    prompt_class: str             # "short" | "medium" | "long"
    prompt_tokens: int            # approximate input token count
    output_tokens: int            # tokens generated
    ttft_ms: float                # Time To First Token (ms)
    total_ms: float               # total generation time (ms)
    tokens_per_sec: float         # output_tokens / (total_ms / 1000)
    error: str | None = None      # None if successful


@dataclass
class BenchmarkSummary:
    model: str
    prompt_class: str
    n: int                        # number of runs
    avg_ttft_ms: float
    avg_tokens_per_sec: float
    avg_output_tokens: float
    p95_total_ms: float           # 95th percentile total latency
    error_rate: float             # fraction of failed runs


@dataclass
class CostProfile:
    """Cost model: local hardware amortised vs API pricing."""
    model: str
    tokens_per_sec: float
    # API pricing (USD per 1k tokens, input+output combined estimate)
    api_cost_per_1k: float
    # Local: GPU/CPU amortised per hour, tokens/hour from bench
    local_cost_per_1k: float
    # Break-even: how many tokens/month to justify local over API
    breakeven_tokens_month: float
