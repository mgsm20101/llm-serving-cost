"""Tests for the cost model and break-even math in src/bench/cost.py."""

from __future__ import annotations

from src.bench import cost


def test_build_cost_profile_matches_documented_breakeven():
    # Reproduces the numbers published in docs/results.md: 3.99 tok/s measured,
    # default $50/month local server, default GPT-4o-mini blended pricing.
    profile = cost.build_cost_profile(model="qwen3:4b", avg_tokens_per_sec=3.99)

    assert profile.model == "qwen3:4b"
    assert profile.api_cost_per_1k == 0.42
    assert profile.breakeven_tokens_month == 119048


def test_breakeven_is_local_cost_over_blended_api_price():
    # Break-even should always equal (local $/month) / (blended $/token), independent
    # of tokens_per_sec — that only feeds local_cost_per_1k, not the break-even itself.
    profile = cost.build_cost_profile(model="m", avg_tokens_per_sec=10.0)
    expected = (cost.LOCAL_SERVER_COST_PER_MONTH_USD / profile.api_cost_per_1k) * 1000
    assert profile.breakeven_tokens_month == round(expected)


def test_breakeven_unaffected_by_tokens_per_sec():
    slow = cost.build_cost_profile(model="m", avg_tokens_per_sec=1.0)
    fast = cost.build_cost_profile(model="m", avg_tokens_per_sec=100.0)
    assert slow.breakeven_tokens_month == fast.breakeven_tokens_month


def test_faster_tokens_per_sec_lowers_local_cost_per_1k():
    slow = cost.build_cost_profile(model="m", avg_tokens_per_sec=1.0)
    fast = cost.build_cost_profile(model="m", avg_tokens_per_sec=10.0)
    assert fast.local_cost_per_1k < slow.local_cost_per_1k


def test_zero_tokens_per_sec_gives_infinite_local_cost():
    profile = cost.build_cost_profile(model="m", avg_tokens_per_sec=0.0)
    assert profile.local_cost_per_1k == float("inf")


def test_custom_api_pricing_changes_blended_rate_and_breakeven():
    profile = cost.build_cost_profile(
        model="m",
        avg_tokens_per_sec=4.0,
        api_input_per_1k=1.0,
        api_output_per_1k=1.0,
    )
    # 40% * 1.0 + 60% * 1.0 == 1.0 exactly
    assert profile.api_cost_per_1k == 1.0
    assert profile.breakeven_tokens_month == round(
        cost.LOCAL_SERVER_COST_PER_MONTH_USD / 1.0 * 1000
    )
