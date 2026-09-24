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


def build_cost_profile(
    model: str,
    avg_tokens_per_sec: float,
    api_input_per_1k: float = 0.15,   # USD, GPT-4o-mini ballpark
    api_output_per_1k: float = 0.60,
) -> CostProfile:
    """
    Compute break-even volume for local vs API.

    break-even: LOCAL_cost/month = API_cost/month
    LOCAL_cost = $50 (fixed, regardless of volume)
    API_cost   = tokens_month / 1000 × api_combined_per_1k
    => tokens_month = 50 / (api_combined_per_1k / 1000)
    """
    # Blended API cost assuming ~40% input, ~60% output token ratio
    api_blended = 0.4 * api_input_per_1k + 0.6 * api_output_per_1k

    if avg_tokens_per_sec > 0:
        # Monthly capacity: tokens/sec × 3600 × 24 × 30 (if server runs 24/7)
        tokens_per_month_capacity = avg_tokens_per_sec * 3600 * 24 * 30
        local_cost_per_1k = (LOCAL_SERVER_COST_PER_MONTH_USD / tokens_per_month_capacity) * 1000
    else:
        local_cost_per_1k = float("inf")
        tokens_per_month_capacity = 0

    if api_blended > 0:
        breakeven = (LOCAL_SERVER_COST_PER_MONTH_USD / api_blended) * 1000
    else:
        breakeven = float("inf")

    return CostProfile(
        model=model,
        tokens_per_sec=round(avg_tokens_per_sec, 2),
        api_cost_per_1k=round(api_blended, 4),
        local_cost_per_1k=round(local_cost_per_1k, 6),
        breakeven_tokens_month=round(breakeven),
    )
