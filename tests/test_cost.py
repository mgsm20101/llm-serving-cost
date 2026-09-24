"""Tests for the cost model and break-even math in src/bench/cost.py."""

from __future__ import annotations

import pytest

from src.bench import cost


def test_prices_are_per_million_tokens_as_vendors_publish_them():
    # $0.15 in / $0.60 out per 1M tokens, blended 40/60 -> $0.42 per 1M.
    profile = cost.build_cost_profile(model="m", avg_tokens_per_sec=4.0)

    assert profile.api_cost_per_1m == pytest.approx(0.42)


def test_breakeven_is_about_119_million_tokens_at_default_prices():
    # $50/month / $0.42 per 1M tokens. Treating the per-1M price as per-1k
    # would put this 1000x too low, at ~119 thousand.
    profile = cost.build_cost_profile(model="m", avg_tokens_per_sec=4.0)

    assert profile.breakeven_tokens_month == 119_047_619


def test_breakeven_is_local_cost_over_blended_api_price():
    profile = cost.build_cost_profile(model="m", avg_tokens_per_sec=10.0)
    expected = cost.LOCAL_SERVER_COST_PER_MONTH_USD / profile.api_cost_per_1m * 1_000_000

    assert profile.breakeven_tokens_month == round(expected)


def test_breakeven_unaffected_by_tokens_per_sec():
    slow = cost.build_cost_profile(model="m", avg_tokens_per_sec=1.0)
    fast = cost.build_cost_profile(model="m", avg_tokens_per_sec=100.0)

    assert slow.breakeven_tokens_month == fast.breakeven_tokens_month


def test_capacity_is_tokens_per_second_running_all_month():
    profile = cost.build_cost_profile(model="m", avg_tokens_per_sec=10.0)

    assert profile.capacity_tokens_month == 10 * 3600 * 24 * 30


def test_breakeven_reachable_only_when_capacity_exceeds_it():
    slow = cost.build_cost_profile(model="m", avg_tokens_per_sec=20.0)    # ~52M/month
    fast = cost.build_cost_profile(model="m", avg_tokens_per_sec=100.0)   # ~259M/month

    assert not slow.breakeven_reachable
    assert fast.breakeven_reachable


def test_local_cost_per_1m_is_monthly_cost_over_capacity():
    profile = cost.build_cost_profile(model="m", avg_tokens_per_sec=10.0)
    expected = 50.0 / (10 * 3600 * 24 * 30) * 1_000_000

    assert profile.local_cost_per_1m == pytest.approx(expected, rel=1e-4)


def test_zero_tokens_per_sec_gives_infinite_local_cost_and_no_capacity():
    profile = cost.build_cost_profile(model="m", avg_tokens_per_sec=0.0)

    assert profile.local_cost_per_1m == float("inf")
    assert profile.capacity_tokens_month == 0
    assert not profile.breakeven_reachable


def test_custom_api_pricing_changes_blended_rate_and_breakeven():
    profile = cost.build_cost_profile(
        model="m", avg_tokens_per_sec=4.0, api_input_per_1m=1.0, api_output_per_1m=1.0
    )

    assert profile.api_cost_per_1m == 1.0
    assert profile.breakeven_tokens_month == 50_000_000
