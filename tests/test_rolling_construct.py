"""Roll construction (roll redesign Task 5).

Nearest later expiry first; within it the most favourable strike (lowest put / highest call)
whose net credit clears the floor and whose |delta| does not exceed the old leg's. Every
rejected quote is counted by reason code.
"""

from __future__ import annotations

import dataclasses
from datetime import date, timedelta

from src.common.config import RollCfg
from src.common.schemas import IVStats, OptionQuote, OptionRight, PositionSnapshot, TechnicalStats
from src.storage.roll_chains import RollChainState
from src.strategies.rolling import RollContext, construct_roll

_TODAY = date(2026, 10, 12)
_OLD = _TODAY + timedelta(days=4)
_W1 = _TODAY + timedelta(days=11)
_W2 = _TODAY + timedelta(days=18)
_IV = IVStats(symbol="GOOGL", iv_rank=40.0)
_TECH = TechnicalStats(symbol="GOOGL", price=325.0)


def q(strike: float, expiry: date, mid: float, delta: float | None, right=OptionRight.PUT):
    return OptionQuote(
        underlying="GOOGL",
        right=right,
        strike=strike,
        expiry=expiry,
        bid=round(mid - 0.05, 2),
        ask=round(mid + 0.05, 2),
        delta=delta,
        open_interest=1000,
        volume=100,
        underlying_price=325.0,
    )


def _ctx(right=OptionRight.PUT, strike=335.0, seq=0, **kw) -> RollContext:
    pos = PositionSnapshot(
        symbol="GOOGL x",
        sec_type="OPT",
        position=-2,
        avg_cost=1.0,
        right=right,
        strike=strike,
        expiry=_OLD,
        underlying="GOOGL",
        con_id=99,
    )
    cur_delta = -0.62 if right == OptionRight.PUT else 0.62
    base = {
        "position": pos,
        "current": q(strike, _OLD, 6.00, cur_delta, right),
        "spot": 325.0,
        "chain": RollChainState(seq, "c-root", _OLD, "c-root"),
        "closed_candidate_id": "c-root",
        "next_earnings": None,
        "ex_div_date": None,
        "dividend": None,
        "allow_debit": False,
        "today": _TODAY,
    }
    return RollContext(**(base | kw))


def _build(ctx: RollContext, quotes: list[OptionQuote], cfg: RollCfg | None = None):
    return construct_roll(ctx, quotes, _IV, _TECH, cfg or RollCfg())


def test_same_strike_credit_roll_is_chosen_when_it_is_the_only_credit() -> None:
    cand, rej = _build(_ctx(), [q(335.0, _W1, 6.40, -0.58), q(330.0, _W1, 5.90, -0.50)])
    assert cand is not None and cand.strike == 335.0 and cand.expiry == _W1
    assert cand.premium == 0.40 and rej == {"net_below_floor": 1}
    assert cand.roll_from is not None and cand.roll_from.seq == 1
    assert cand.roll_from.con_id == 99 and cand.roll_from.chain_id == "c-root"
    assert cand.contracts == 2


def test_most_favourable_strike_wins_inside_the_nearest_expiry() -> None:
    cand, _ = _build(_ctx(), [q(335.0, _W1, 6.40, -0.58), q(330.0, _W1, 6.06, -0.50)])
    assert cand is not None and cand.strike == 330.0


def test_nearest_expiry_wins_over_a_farther_better_strike() -> None:
    cand, _ = _build(_ctx(), [q(335.0, _W1, 6.40, -0.58), q(325.0, _W2, 6.50, -0.45)])
    assert cand is not None and cand.expiry == _W1


def test_a_csp_debit_roll_is_rejected() -> None:
    cand, rej = _build(_ctx(), [q(335.0, _W1, 5.98, -0.58)])
    assert cand is None and rej == {"net_below_floor": 1}


def test_a_keep_shares_call_may_pay_up_to_the_cap() -> None:
    ctx = _ctx(right=OptionRight.CALL, allow_debit=True)
    ok, _ = _build(ctx, [q(340.0, _W1, 5.80, 0.55, OptionRight.CALL)])
    assert ok is not None and ok.premium == -0.20 and ok.roll_from.allow_debit is True
    too_much, rej = _build(ctx, [q(340.0, _W1, 5.70, 0.55, OptionRight.CALL)])
    assert too_much is None and rej == {"net_below_floor": 1}


def test_delta_must_not_increase_and_must_be_known() -> None:
    _, rej = _build(_ctx(), [q(335.0, _W1, 6.40, -0.70), q(330.0, _W1, 6.40, None)])
    assert rej == {"delta_increases": 1, "delta_missing": 1}


def test_an_expiry_on_or_after_earnings_is_rejected() -> None:
    cand, rej = _build(_ctx(next_earnings=_W1), [q(335.0, _W1, 6.40, -0.58)])
    assert cand is None and rej == {"earnings_before_expiry": 1}


def test_a_call_with_thin_extrinsic_before_ex_div_is_rejected() -> None:
    # spot 325, new call 320 is ITM by 5; mid 5.10 → extrinsic 0.10 < dividend 0.24 + 0.05
    ctx = _ctx(
        right=OptionRight.CALL,
        strike=320.0,
        ex_div_date=_W1 - timedelta(days=2),
        dividend=0.24,
        current=q(320.0, _OLD, 5.05, 0.80, OptionRight.CALL),
    )
    cand, rej = _build(ctx, [q(320.0, _W1, 5.10, 0.78, OptionRight.CALL)])
    assert cand is None and rej == {"ex_div_assignment_risk": 1}


def test_strikes_in_the_wrong_direction_are_rejected() -> None:
    _, rej = _build(_ctx(), [q(340.0, _W1, 9.00, -0.55)])
    assert rej == {"strike_worse": 1}


def test_a_chain_at_its_roll_limit_inspects_nothing() -> None:
    assert _build(_ctx(seq=1), [q(335.0, _W1, 6.40, -0.58)]) == (None, {"roll_limit_reached": 1})


def test_an_expiry_beyond_the_extension_cap_is_rejected() -> None:
    cfg = RollCfg(limits={"max_extension_days": 10})
    cand, rej = _build(_ctx(), [q(335.0, _W2, 6.90, -0.55)], cfg)
    assert cand is None and rej == {"extension_cap": 1}


def test_an_unpriced_current_leg_stops_construction() -> None:
    ctx = _ctx()
    ctx = dataclasses.replace(
        ctx, current=ctx.current.model_copy(update={"bid": None, "ask": None})
    )
    assert _build(ctx, [q(335.0, _W1, 6.40, -0.58)]) == (None, {"current_unpriced": 1})


def test_candidate_identity_and_earnings_are_stamped() -> None:
    earnings = _W2 + timedelta(days=3)
    cand, _ = _build(_ctx(next_earnings=earnings), [q(335.0, _W1, 6.40, -0.58)])
    assert cand is not None and cand.strategy.value == "roll"
    assert cand.next_earnings == earnings
    assert cand.breakeven == 335.0 - 0.40
