"""Contracts for benchmark results.

BenchmarkRun is one streamed request; CostProfile is the local-vs-API cost model
for one model. Per-cell aggregates (medians, p95) are plain dicts built in
src/bench/results_writer.py.
"""

from __future__ import annotations

from dataclasses import dataclass


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
