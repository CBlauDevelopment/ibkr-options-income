"""The month's pay stub: premium in, buybacks and commissions out, net, against a target."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from src.common.schemas import PnlLeg
from src.reporting.pay import SpreadPayInput, build_month_pay

OCT = date(2026, 10, 1)
TODAY = date(2026, 10, 13)


def leg(**over) -> PnlLeg:
    base = dict(
        candidate_id="c1",
        symbol="AAPL",
        underlying="AAPL",
        strategy="cash_secured_put",
        right="P",
        strike=180.0,
        expiry=date(2026, 11, 21),
        contracts=1,
        opened_at=datetime(2026, 10, 2, 15, 0),
        credit=235.0,
        debit=0.0,
        commissions=1.3,
        commissions_complete=True,
        days_held=0,
        outcome="still_open",
        is_live=False,
    )
    base.update(over)
    return PnlLeg(**base)


def pay(legs=(), spreads=(), **kw):
    args = dict(month=OCT, strategy="all", month_start_value=None, target_pct=None, today=TODAY)
    args.update(kw)
    return build_month_pay(list(legs), list(spreads), **args)


def test_an_empty_month_is_zero_income_with_no_target() -> None:
    p = pay()
    assert (p.premium_collected, p.bought_back, p.commissions, p.net) == (0.0, 0.0, 0.0, 0.0)
    assert p.target is None and p.progress_pct is None
    assert p.days_left == 18


def test_premium_counts_in_the_month_it_was_sold_and_buybacks_in_the_month_bought() -> None:
    sold_sep_bought_oct = leg(
        candidate_id="c2",
        opened_at=datetime(2026, 9, 20, 15, 0),
        closed_at=datetime(2026, 10, 5, 15, 0),
        credit=300.0,
        debit=120.0,
        commissions=2.6,
        outcome="closed_early",
    )
    p = pay([leg(), sold_sep_bought_oct])
    assert p.premium_collected == 235.0
    assert p.bought_back == 120.0
    assert p.commissions == pytest.approx(3.9)
    assert p.net == pytest.approx(235.0 - 120.0 - 3.9)
    assert (p.n_opened, p.n_closed) == (1, 1)


def test_month_is_new_york_time() -> None:
    # 2026-11-01 02:00 UTC is 2026-10-31 22:00 ET: October's pay.
    late = leg(opened_at=datetime(2026, 11, 1, 2, 0, tzinfo=UTC))
    assert pay([late]).premium_collected == 235.0
    assert pay([late], month=date(2026, 11, 1), today=date(2026, 11, 2)).premium_collected == 0.0


def test_an_expiry_on_the_first_closes_in_that_month() -> None:
    """build_legs stamps an expired or assigned leg's closed_at as naive midnight ON the expiry
    date - a calendar date, not a UTC instant - so it must not slide into the previous ET day."""
    expired = leg(
        opened_at=datetime(2026, 4, 20, 15, 0),
        expiry=date(2026, 5, 1),
        closed_at=datetime(2026, 5, 1, 0, 0),
        outcome="expired_worthless",
    )
    may = pay([expired], month=date(2026, 5, 1), today=date(2026, 5, 4))
    assert may.n_closed == 1
    assert may.commissions == pytest.approx(1.3)
    assert pay([expired], month=date(2026, 4, 1), today=date(2026, 5, 4)).n_closed == 0


def test_strategy_filter_and_rolls_follow_their_side() -> None:
    cc = leg(candidate_id="cc1", strategy="covered_call", right="C", credit=64.0)
    put_roll = leg(candidate_id="r1", strategy="roll", right="P", credit=50.0)
    assert pay([leg(), cc, put_roll], strategy="csp").premium_collected == 285.0
    assert pay([leg(), cc, put_roll], strategy="cc").premium_collected == 64.0
    assert pay([leg(), cc], strategy="spread").premium_collected == 0.0


def test_spreads_count_in_all_and_spread_only() -> None:
    s = SpreadPayInput(
        opened_at=datetime(2026, 10, 13, 14, 0),
        closed_at=datetime(2026, 10, 13, 19, 0),
        entry_credit=0.42,
        exit_debit=0.10,
        contracts_opened=2,
        contracts_open=0,
        entry_commission=2.6,
        exit_commission=2.6,
    )
    p = pay(spreads=[s], strategy="spread")
    assert p.premium_collected == pytest.approx(84.0)
    assert p.bought_back == pytest.approx(20.0)
    assert p.commissions == pytest.approx(5.2)
    assert pay(spreads=[s], strategy="csp").premium_collected == 0.0
    assert pay(spreads=[s]).premium_collected == pytest.approx(84.0)


def test_target_is_a_percent_of_month_start_value() -> None:
    p = pay([leg()], month_start_value=200_000.0, target_pct=1.0)
    assert p.target == 2_000.0
    assert p.progress_pct == pytest.approx((235.0 - 1.3) / 2_000.0 * 100)


def test_no_month_start_value_means_no_target_not_zero() -> None:
    p = pay([leg()], month_start_value=None, target_pct=1.0)
    assert p.target is None and p.progress_pct is None
    assert p.target_pct == 1.0


def test_incomplete_commissions_are_flagged() -> None:
    assert pay([leg(commissions_complete=False)]).commissions_complete is False


def test_a_past_month_has_no_days_left() -> None:
    assert pay(month=date(2026, 9, 1)).days_left == 0
