"""Contracts for benchmark results.

A single BenchmarkRun captures every measurable metric for one (model, prompt) pair.
BenchmarkSummary aggregates across a prompt_class (short/medium/long).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BenchmarkRun:
    model: str                    # e.g. "gemma3:4b"
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
    # Blended API price, USD per 1M tokens (40% input / 60% output)
    api_cost_per_1m: float
    # Local fixed monthly cost spread over the measured monthly capacity, USD per 1M tokens
    local_cost_per_1m: float
    # Tokens/month at which API spend equals the local monthly cost
    breakeven_tokens_month: float
    # Tokens/month the measured throughput produces running 24/7
    capacity_tokens_month: float = 0

    @property
    def breakeven_reachable(self) -> bool:
        return 0 < self.breakeven_tokens_month <= self.capacity_tokens_month
