"""Offline assign / roll / close comparison at a strike breach (roll redesign Task 14)."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from src.analytics.black_scholes import bs_price
from src.backtest.roll_arms import format_arms_summary, simulate_breach_arms


def _series(n: int, drift: float, wiggle: float = 0.012) -> tuple[list[float], list[date]]:
    """Calendar-daily closes: a steady drift with an alternating wiggle so HV30 is defined."""
    start = date(2024, 1, 1)
    closes, price = [], 100.0
    for i in range(n):
        price *= math.exp(drift + (wiggle if i % 2 else -wiggle))
        closes.append(price)
    return closes, [start + timedelta(days=i) for i in range(n)]


_KW = dict(
    right="P",
    target_delta=0.25,
    dte=14,
    roll_dte=7,
    breach_dte=10,
    min_net_credit=0.05,
    max_debit=0.25,
    risk_free_rate=0.0,
    commission=0.65,
)


def test_a_falling_series_breaches_and_every_arm_reports_on_the_same_horizon() -> None:
    closes, dates = _series(240, drift=-0.006)
    res = simulate_breach_arms(closes, dates, **_KW)
    assert res.breaches > 0
    n = {arm: len(v) for arm, v in res.arms.items()}
    assert n == {"assign": res.breaches, "roll": res.breaches, "close": res.breaches}
    for a, r, c in zip(res.arms["assign"], res.arms["roll"], res.arms["close"], strict=True):
        assert a.horizon_date == r.horizon_date == c.horizon_date
        assert a.breach_date == r.breach_date == c.breach_date


def test_a_rising_series_never_breaches_a_put() -> None:
    closes, dates = _series(240, drift=0.004)
    res = simulate_breach_arms(closes, dates, **_KW)
    assert res.cycles > 0 and res.breaches == 0
    assert all(len(v) == 0 for v in res.arms.values())


def test_the_close_arm_is_premium_minus_buyback_less_two_commissions() -> None:
    closes, dates = _series(240, drift=-0.006)
    res = simulate_breach_arms(closes, dates, **_KW)
    o = res.arms["close"][0]
    expected = (o.entry_premium - o.buyback) * 100 - 2 * 0.65
    assert o.pnl == pytest.approx(expected)
    assert o.buyback == pytest.approx(
        bs_price(o.spot_at_breach, o.strike, o.days_left_at_breach, o.iv_at_breach, "P", 0.0)
    )


def test_the_roll_arm_falls_back_to_assignment_when_no_credit_roll_exists() -> None:
    closes, dates = _series(240, drift=-0.006)
    res = simulate_breach_arms(closes, dates, **(_KW | {"min_net_credit": 50.0}))
    assert res.breaches > 0
    for roll, assign in zip(res.arms["roll"], res.arms["assign"], strict=True):
        assert roll.fell_back is True
        assert roll.pnl == pytest.approx(assign.pnl)


def test_the_summary_names_every_arm_and_flags_the_model() -> None:
    closes, dates = _series(240, drift=-0.006)
    text = format_arms_summary(simulate_breach_arms(closes, dates, **_KW), symbol="TEST")
    for needle in ("assign", "roll", "close", "Black-Scholes", "indicative"):
        assert needle in text


def test_the_cli_prints_the_summary(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import sys

    import scripts.roll_backtest as cli

    closes, dates = _series(240, drift=-0.006)
    monkeypatch.setattr(
        cli, "load_price_series", lambda *a, **k: list(zip(dates, closes, strict=True))
    )
    monkeypatch.setattr(cli, "setup_logging", lambda: None)
    monkeypatch.setattr(sys, "argv", ["roll_backtest", "--symbol", "TEST", "--dte", "14"])
    cli.main()
    out = capsys.readouterr().out
    assert "TEST:" in out and "breaches" in out
