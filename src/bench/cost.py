"""Cost modelling: local on-prem vs cloud API.

Numbers are illustrative benchmarks for the CTO memo — the point is the
*methodology* (measure tokens/sec locally, compare to API per-token pricing,
compute the break-even volume). Swap the constants for your actual hardware.
"""

from __future__ import annotations

from src.schema import CostProfile

# ----- Cost-model assumptions for a HYPOTHETICAL target server (adjustable) -----
# This is NOT the machine the benchmark ran on. The benchmark box is a laptop
# (i7-8750H, 15.9 GB, GTX 1050 Ti); the figures below describe the dedicated server
# you would deploy onto, and they are the input to the break-even, not a measurement.
# Assumed server: 8-core, 32 GB RAM, power draw ~80W
# Monthly electricity: 80W × 24h × 30 days = 57.6 kWh × $0.12/kWh = $6.9
# Amortized hardware (e.g. $800 over 3 years): $22/month
# Total local monthly overhead: ~$29 for a dedicated CPU server
# But we also count opportunity cost / cloud VM equivalent: ~$50/month for comparable specs
LOCAL_SERVER_COST_PER_MONTH_USD = 50.0


HOURS_PER_MONTH = 24 * 30


def build_cost_profile(
    model: str,
    avg_tokens_per_sec: float,
    api_input_per_1m: float = 0.15,   # USD per 1M tokens, the unit API vendors publish
    api_output_per_1m: float = 0.60,
) -> CostProfile:
    """
    Compare a fixed-cost local server with per-token API pricing.

    break-even: tokens_month at which API spend equals the local monthly cost
        tokens_month = LOCAL_cost / (api_blended_per_1m / 1e6)
    capacity: what the measured throughput can produce if the server runs all month.
    The break-even only matters if capacity reaches it.
    """
    # Blended API price assuming ~40% input, ~60% output tokens.
    api_blended_per_1m = 0.4 * api_input_per_1m + 0.6 * api_output_per_1m

    capacity = avg_tokens_per_sec * 3600 * HOURS_PER_MONTH if avg_tokens_per_sec > 0 else 0
    local_cost_per_1m = (
        LOCAL_SERVER_COST_PER_MONTH_USD / capacity * 1_000_000 if capacity > 0 else float("inf")
    )
    breakeven = (
        LOCAL_SERVER_COST_PER_MONTH_USD / api_blended_per_1m * 1_000_000
        if api_blended_per_1m > 0
        else float("inf")
    )

    return CostProfile(
        model=model,
        tokens_per_sec=round(avg_tokens_per_sec, 2),
        api_cost_per_1m=round(api_blended_per_1m, 6),
        local_cost_per_1m=local_cost_per_1m if capacity == 0 else round(local_cost_per_1m, 4),
        breakeven_tokens_month=round(breakeven) if breakeven != float("inf") else breakeven,
        capacity_tokens_month=round(capacity),
    )
