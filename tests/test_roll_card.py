"""Roll decision card + operator Close button (roll redesign Task 11)."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.common.schemas import (
    CloseReason,
    OptionQuote,
    OptionRight,
    PositionSnapshot,
    RollDecision,
    RollOrigin,
    ScoreCard,
    Strategy,
    TradeCandidate,
)
from src.notify.formatters import format_roll_decision

_OLD = date.today() + timedelta(days=4)
_NEW = date.today() + timedelta(days=11)


def _pos() -> PositionSnapshot:
    return PositionSnapshot(
        symbol="GOOGL x",
        sec_type="OPT",
        position=-2,
        avg_cost=1.0,
        right=OptionRight.PUT,
        strike=335.0,
        expiry=_OLD,
        underlying="GOOGL",
        con_id=4242,
    )


def _quote() -> OptionQuote:
    return OptionQuote(
        underlying="GOOGL",
        right=OptionRight.PUT,
        strike=335.0,
        expiry=_OLD,
        bid=5.95,
        ask=6.05,
        delta=-0.62,
        underlying_price=329.10,
    )


def _roll() -> RollDecision:
    cand = TradeCandidate(
        candidate_id="r1",
        strategy=Strategy.ROLL,
        underlying="GOOGL",
        right=OptionRight.PUT,
        strike=330.0,
        expiry=_NEW,
        contracts=2,
        premium=0.06,
        collateral=66_000.0,
        roc_pct=0.0,
        annualized_yield_pct=0.0,
        breakeven=329.94,
        delta=-0.50,
        dte=11,
        scores=ScoreCard(symbol="GOOGL"),
        roll_from=RollOrigin(
            con_id=4242,
            candidate_id="c0",
            strike=335.0,
            expiry=_OLD,
            right=OptionRight.PUT,
            contracts=2,
            chain_id="c0",
            seq=1,
            original_expiry=_OLD,
            old_mid=6.00,
            new_mid=6.06,
        ),
    )
    return RollDecision(
        action="roll",
        reason="credit_roll",
        candidate=cand,
        rejections={"net_below_floor": 3},
        detail="Roll for a $0.06/sh net credit.",
    )


def test_a_roll_card_names_both_legs_the_net_and_the_chain() -> None:
    text = format_roll_decision(_pos(), _quote(), "strike_breach", _roll(), max_rolls=1)
    for needle in (
        "Roll proposal",
        "335P",
        "330P",
        "6\\.00",
        "6\\.06",
        "0\\.06",
        "$12",
        "2 contracts",
        "Roll 1 of 1",
        "329\\.94",
        "strike breach",
        "net below floor ×3",
    ):
        assert needle in text, needle
    assert len(text) <= 4096


def test_an_assign_card_says_why_there_is_no_roll() -> None:
    d = RollDecision(
        action="assign",
        reason="net_below_floor",
        rejections={"net_below_floor": 4},
        detail="No credit roll (net below floor ×4) — letting it assign at $335.",
    )
    text = format_roll_decision(_pos(), _quote(), "strike_breach", d, max_rolls=1)
    assert "Let it assign" in text and "net below floor" in text


def test_a_close_card_and_a_hold_card_name_their_reason() -> None:
    close = RollDecision(
        action="close", reason="not_would_own", detail="Not on the would-own list."
    )
    hold = RollDecision(action="hold", reason="leveraged_etf_no_roll", detail="Leveraged ETF.")
    assert "Close" in format_roll_decision(_pos(), _quote(), "strike_breach", close, max_rolls=1)
    assert "Hold" in format_roll_decision(_pos(), _quote(), "ex_div", hold, max_rolls=1)


def _update(data: str) -> MagicMock:
    update = MagicMock()
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


async def test_close_button_buys_back_the_exact_contract_as_defensive() -> None:
    from src.notify import approval_service as svc

    ctx = MagicMock()
    ctx.bot_data = {"ib_exec": MagicMock(), "ib_scan": MagicMock()}
    other = _pos().model_copy(update={"con_id": 1, "strike": 330.0})
    result = MagicMock(status="filled", filled_qty=2.0, avg_price=6.10, detail=None)
    with (
        patch.object(svc, "_is_authorized", return_value=True),
        patch("src.ibkr.portfolio.get_positions", return_value=[other, _pos()]),
        patch("src.execution.profit_take._quote_short", new=AsyncMock(return_value=(6.0, 6.2))),
        patch(
            "src.execution.position_manager.close_short_position",
            new=AsyncMock(return_value=result),
        ) as close,
    ):
        await svc.handle_close_short(_update("close_short:4242"), ctx)
    pos = close.await_args.args[1]
    assert pos.con_id == 4242 and close.await_args.kwargs["reason"] is CloseReason.DEFENSIVE


async def test_close_button_on_a_position_that_is_gone_places_nothing() -> None:
    from src.notify import approval_service as svc

    ctx = MagicMock()
    ctx.bot_data = {"ib_exec": MagicMock(), "ib_scan": MagicMock()}
    upd = _update("close_short:999")
    with (
        patch.object(svc, "_is_authorized", return_value=True),
        patch("src.ibkr.portfolio.get_positions", return_value=[_pos()]),
        patch("src.execution.position_manager.close_short_position", new=AsyncMock()) as close,
    ):
        await svc.handle_close_short(upd, ctx)
    close.assert_not_awaited()
    assert "no longer open" in upd.callback_query.edit_message_text.await_args.args[0]
