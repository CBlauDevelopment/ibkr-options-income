"""Roll trigger + decision tree (roll redesign Task 6)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.common.config import RollCfg
from src.common.schemas import (
    FundamentalStats,
    IVStats,
    OptionQuote,
    OptionRight,
    PositionSnapshot,
    TechnicalStats,
)
from src.storage.roll_chains import RollChainState
from src.strategies.roll_policy import decide, extrinsic, roll_trigger
from src.strategies.rolling import RollContext

_TODAY = date(2026, 10, 12)
_IV = IVStats(symbol="X", iv_rank=40.0)
_TECH = TechnicalStats(symbol="X", price=95.0)


def _pos(right=OptionRight.PUT, strike=100.0, days=8) -> PositionSnapshot:
    return PositionSnapshot(
        symbol="X x",
        sec_type="OPT",
        position=-1,
        avg_cost=1.0,
        right=right,
        strike=strike,
        expiry=_TODAY + timedelta(days=days),
        underlying="X",
        con_id=7,
    )


def _q(strike, days, mid, delta, right=OptionRight.PUT, spot=95.0) -> OptionQuote:
    return OptionQuote(
        underlying="X",
        right=right,
        strike=strike,
        expiry=_TODAY + timedelta(days=days),
        bid=round(mid - 0.05, 2),
        ask=round(mid + 0.05, 2),
        delta=delta,
        open_interest=500,
        volume=50,
        underlying_price=spot,
    )


# --- trigger ------------------------------------------------------------------------------


def _trig(pos, quote, fund=None, *, guard=True, cfg=None):
    return roll_trigger(pos, quote, fund, cfg or RollCfg(), ex_div_guard=guard, today=_TODAY)


def test_an_itm_put_inside_the_window_is_breached() -> None:
    assert _trig(_pos(days=8), _q(100.0, 8, 5.50, -0.70)) == "strike_breach"


def test_a_breach_with_weeks_left_and_thick_extrinsic_waits() -> None:
    assert _trig(_pos(days=20), _q(100.0, 20, 6.50, -0.65)) is None  # extrinsic 1.50


def test_a_breach_with_thin_extrinsic_acts_early() -> None:
    assert _trig(_pos(days=20), _q(100.0, 20, 5.05, -0.80)) == "strike_breach"  # ext 0.05


def test_the_delta_rule_alone_counts_as_a_breach() -> None:
    otm = _q(100.0, 8, 1.20, -0.55, spot=100.5)
    assert _trig(_pos(days=8), otm) == "strike_breach"


def test_an_otm_low_delta_short_is_not_breached() -> None:
    assert _trig(_pos(days=5), _q(100.0, 5, 0.40, -0.20, spot=104.0)) is None


def _call_fund(days_to_ex=3, div=0.24) -> FundamentalStats:
    return FundamentalStats(
        symbol="X", ex_dividend_date=_TODAY + timedelta(days=days_to_ex), dividend_per_share=div
    )


def test_a_short_call_with_extrinsic_below_the_dividend_triggers_ex_div() -> None:
    pos = _pos(OptionRight.CALL, 90.0, days=20)
    quote = _q(90.0, 20, 5.20, 0.45, OptionRight.CALL, spot=95.0)  # extrinsic 0.20 < 0.29
    assert _trig(pos, quote, _call_fund()) == "ex_div"
    assert _trig(pos, quote, _call_fund(), guard=False) is None
    assert _trig(pos, quote, _call_fund(days_to_ex=9)) is None  # beyond days_ahead


def test_puts_never_get_an_ex_div_trigger() -> None:
    assert _trig(_pos(days=20), _q(100.0, 20, 0.30, -0.10, spot=110.0), _call_fund()) is None


def test_extrinsic_subtracts_intrinsic() -> None:
    assert extrinsic(_q(100.0, 8, 5.50, -0.7), 95.0) == pytest.approx(0.50)
    assert extrinsic(_q(100.0, 8, 5.50, -0.7), None) is None


# --- decide -------------------------------------------------------------------------------


def _ctx(right=OptionRight.PUT, strike=100.0, cur_mid=5.50, seq=0) -> RollContext:
    pos = _pos(right, strike, days=5)
    delta = -0.70 if right == OptionRight.PUT else 0.70
    return RollContext(
        position=pos,
        current=_q(strike, 5, cur_mid, delta, right),
        spot=95.0,
        chain=RollChainState(seq, "c", pos.expiry, "c"),
        closed_candidate_id="c",
        next_earnings=None,
        ex_div_date=None,
        dividend=None,
        allow_debit=False,
        today=_TODAY,
    )


def _decide(ctx, quotes, cfg=None, *, own=True, basis=None, on_no_roll="policy"):
    return decide(
        ctx,
        quotes,
        _IV,
        _TECH,
        cfg or RollCfg(csp={"when_assignable": "roll_if_credit"}, cc={"keep_shares": True}),
        would_own=own,
        cc_basis=basis,
        on_no_roll=on_no_roll,
    )


_PUT_ROLL = [_q(100.0, 12, 5.90, -0.62)]
_CALL_ROLL_DEBIT = [_q(105.0, 12, 5.30, 0.55, OptionRight.CALL)]  # net −0.20


def test_a_put_on_a_name_we_would_not_own_rolls_when_it_can() -> None:
    # 2026-10-14 ruling: prefer rolling over closing in a loss.
    d = _decide(_ctx(), _PUT_ROLL, own=False)
    assert d.action == "roll" and d.candidate is not None


def test_a_put_on_a_name_we_would_not_own_is_closed_when_no_roll_qualifies() -> None:
    d = _decide(_ctx(), [], own=False)
    assert (d.action, d.reason) == ("close", "not_would_own")


def test_the_loss_line_rolls_when_a_roll_qualifies() -> None:
    d = _decide(_ctx(), _PUT_ROLL, on_no_roll="close")
    assert (d.action, d.reason) == ("roll", "loss_line_roll")
    assert d.candidate is not None and d.candidate.premium == 0.40


def test_the_loss_line_closes_when_no_roll_qualifies_instead_of_assigning() -> None:
    d = _decide(_ctx(), [_q(100.0, 12, 5.45, -0.62)], on_no_roll="close")
    assert (d.action, d.reason) == ("close", "net_below_floor")


def test_the_loss_line_on_a_covered_call_allows_the_capped_debit_roll() -> None:
    d = _decide(_ctx(OptionRight.CALL, 100.0), _CALL_ROLL_DEBIT, basis=90.0, on_no_roll="close")
    assert d.action == "roll" and d.candidate is not None and d.candidate.premium < 0


def test_a_would_own_put_rolls_for_a_credit() -> None:
    d = _decide(_ctx(), _PUT_ROLL)
    assert d.action == "roll" and d.candidate is not None and d.candidate.premium == 0.40


def test_a_would_own_put_with_no_credit_roll_is_assigned() -> None:
    d = _decide(_ctx(), [_q(100.0, 12, 5.45, -0.62)])
    assert (d.action, d.reason) == ("assign", "net_below_floor")


def test_assign_preference_skips_construction() -> None:
    d = _decide(_ctx(), _PUT_ROLL, RollCfg(csp={"when_assignable": "assign"}))
    assert (d.action, d.reason, d.candidate) == ("assign", "assign_preferred", None)


def test_a_keep_shares_call_rolls_up_and_out_for_a_capped_debit() -> None:
    d = _decide(_ctx(OptionRight.CALL, 100.0), _CALL_ROLL_DEBIT, basis=90.0)
    assert d.action == "roll" and d.reason == "keep_shares_roll"
    assert d.candidate is not None and d.candidate.roll_from.allow_debit is True


def test_a_call_with_no_roll_above_basis_is_called_away() -> None:
    d = _decide(_ctx(OptionRight.CALL, 100.0), [], basis=90.0)
    assert d.action == "let_called_away"


def test_a_call_with_no_roll_below_basis_is_held() -> None:
    d = _decide(_ctx(OptionRight.CALL, 100.0), [], basis=110.0)
    assert (d.action, d.reason) == ("hold", "below_basis_no_roll")


def test_keep_shares_off_lets_an_above_basis_call_go_without_trying() -> None:
    d = _decide(_ctx(OptionRight.CALL, 100.0), _CALL_ROLL_DEBIT, RollCfg(), basis=90.0)
    assert (d.action, d.reason) == ("let_called_away", "keep_shares_off")


def test_an_unpriced_current_leg_defers() -> None:
    ctx = _ctx()
    ctx = RollContext(
        **{**ctx.__dict__, "current": ctx.current.model_copy(update={"bid": None, "ask": None})}
    )
    assert (_decide(ctx, _PUT_ROLL).action, _decide(ctx, _PUT_ROLL).reason) == (
        "defer",
        "current_unpriced",
    )


def test_every_decision_explains_itself() -> None:
    for d in (
        _decide(_ctx(), _PUT_ROLL),
        _decide(_ctx(), []),
        _decide(_ctx(), [], own=False),
        _decide(_ctx(), [], on_no_roll="close"),
    ):
        assert d.detail
