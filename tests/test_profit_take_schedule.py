"""DTE-keyed profit-take schedule and close-reason labelling (2026-10-11).

`scheduler.profit_take_schedule` overrides the flat `profit_take_pct` per strategy and entry
DTE; an empty schedule must behave exactly like the flat threshold. Every buy-to-close carries
a `CloseReason`, so a loss exit is never recorded as a profit-take.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from src.common.config import ProfitTakeTier, SchedulerCfg
from src.common.schemas import CloseReason, OptionRight, PositionSnapshot, VerdictOutcome
from src.execution.profit_take import resolve_profit_take_pct


def _sched(*tiers: dict, flat: float = 50.0) -> SchedulerCfg:
    return SchedulerCfg(
        profit_take_pct=flat, profit_take_schedule=[ProfitTakeTier(**t) for t in tiers]
    )


# --- resolve_profit_take_pct ------------------------------------------------------------


def test_empty_schedule_is_the_flat_threshold() -> None:
    s = _sched()
    assert resolve_profit_take_pct(s, OptionRight.PUT, 7) == 50.0
    assert resolve_profit_take_pct(s, OptionRight.CALL, 45) == 50.0


def test_first_matching_row_wins() -> None:
    s = _sched(
        {"strategy": "covered_call", "max_entry_dte": 60, "pct": 75},
        {"strategy": "any", "max_entry_dte": 14, "pct": 70},
        {"strategy": "any", "max_entry_dte": 28, "pct": 60},
    )
    assert resolve_profit_take_pct(s, OptionRight.CALL, 7) == 75.0  # CC row is first
    assert resolve_profit_take_pct(s, OptionRight.PUT, 7) == 70.0
    assert resolve_profit_take_pct(s, OptionRight.PUT, 14) == 70.0  # max_entry_dte inclusive
    assert resolve_profit_take_pct(s, OptionRight.PUT, 15) == 60.0
    assert resolve_profit_take_pct(s, OptionRight.PUT, 40) == 50.0  # no match → flat


def test_strategy_is_inferred_from_the_right() -> None:
    s = _sched({"strategy": "cash_secured_put", "max_entry_dte": 30, "pct": 70})
    assert resolve_profit_take_pct(s, OptionRight.PUT, 10) == 70.0
    assert resolve_profit_take_pct(s, OptionRight.CALL, 10) == 50.0


def test_unknown_entry_dte_falls_back_to_flat() -> None:
    s = _sched({"strategy": "any", "max_entry_dte": 999, "pct": 80})
    assert resolve_profit_take_pct(s, OptionRight.PUT, None) == 50.0


@pytest.mark.parametrize(
    "tier",
    [
        {"strategy": "any", "max_entry_dte": 14, "pct": 100},
        {"strategy": "any", "max_entry_dte": 14, "pct": 0},
        {"strategy": "any", "max_entry_dte": -1, "pct": 70},
        {"strategy": "csp", "max_entry_dte": 14, "pct": 70},  # typo'd strategy
    ],
)
def test_bad_tiers_fail_at_config_load(tier: dict) -> None:
    with pytest.raises(ValidationError):
        ProfitTakeTier(**tier)


def test_example_config_ships_an_empty_schedule() -> None:
    from src.common.config import get_config

    assert get_config().scheduler.profit_take_schedule == []


# --- check_profit_takes -----------------------------------------------------------------


def _short_put(days_to_expiry: int = 10) -> PositionSnapshot:
    return PositionSnapshot(
        symbol="AAPL  261120P00185000",
        sec_type="OPT",
        position=-1,
        avg_cost=100.0,
        right=OptionRight.PUT,
        strike=185.0,
        expiry=date.today() + timedelta(days=days_to_expiry),
        underlying="AAPL",
    )


async def _run_check(
    scheduler: SchedulerCfg, *, entry: float, bid: float, ask: float, entry_dte: int
) -> AsyncMock:
    """Run check_profit_takes on one short put sold `entry_dte` days before expiry."""
    from src.execution.profit_take import check_profit_takes

    pos = _short_put(days_to_expiry=entry_dte - 2)  # sold two days ago
    cfg = MagicMock()
    cfg.scheduler = scheduler
    cfg.automation.auto_close_enabled = True
    with (
        patch("src.execution.profit_take.get_config", return_value=cfg),
        patch("src.ibkr.portfolio.get_positions", return_value=[pos]),
        patch("src.execution.profit_take.chain_entry_credit_per_share", return_value=entry),
        patch(
            "src.execution.profit_take.position_opened_at",
            return_value=datetime.now(UTC) - timedelta(days=2),
        ),
        patch("src.execution.profit_take._quote_short", new=AsyncMock(return_value=(bid, ask))),
        patch("src.execution.profit_take._auto_close_position", new=AsyncMock()) as close,
    ):
        await check_profit_takes(MagicMock(), MagicMock(), AsyncMock(), "chat")
    return close


async def test_flat_threshold_closes_at_50pct() -> None:
    close = await _run_check(_sched(), entry=1.00, bid=0.44, ask=0.46, entry_dte=10)
    close.assert_awaited_once()  # 55% captured ≥ 50%


async def test_schedule_raises_the_bar_for_a_matching_entry_dte() -> None:
    s = _sched({"strategy": "cash_secured_put", "max_entry_dte": 14, "pct": 70})
    close = await _run_check(s, entry=1.00, bid=0.44, ask=0.46, entry_dte=10)
    close.assert_not_awaited()  # 55% captured < 70%
    close = await _run_check(s, entry=1.00, bid=0.24, ask=0.26, entry_dte=10)
    close.assert_awaited_once()  # 75% captured ≥ 70%


async def test_schedule_row_does_not_apply_outside_its_dte_range() -> None:
    s = _sched({"strategy": "cash_secured_put", "max_entry_dte": 14, "pct": 70})
    close = await _run_check(s, entry=1.00, bid=0.44, ask=0.46, entry_dte=21)
    close.assert_awaited_once()  # entry DTE 21 > 14 → flat 50%


async def test_profit_take_close_is_labelled_profit_take() -> None:
    from src.execution.profit_take import _auto_close_position

    result = MagicMock(status="skipped", detail="already_working")
    with patch(
        "src.execution.position_manager.close_short_position",
        new=AsyncMock(return_value=result),
    ) as close:
        await _auto_close_position(MagicMock(), _short_put(), 0.2, 0.3, AsyncMock(), "chat")
    assert close.await_args.kwargs["reason"] is CloseReason.PROFIT_TAKE


# --- P&L legs ---------------------------------------------------------------------------


def test_closed_early_leg_reports_its_close_reason(db, seed_leg) -> None:
    from src.reporting.pnl import build_legs
    from src.storage.models import FillRow

    seed_leg(candidate_id="c-loss", sold=(1, 2.98), bought=(1, 7.00))
    seed_leg(candidate_id="c-old", sold=(1, 1.00), bought=(1, 0.50))  # pre-stamp close
    seed_leg(candidate_id="c-open", sold=(1, 1.00))
    with db() as s:
        s.query(FillRow).filter_by(
            candidate_id="c-loss", action="BUY"
        ).one().close_reason = "loss_exit"

    legs = {leg.candidate_id: leg for leg in build_legs(db)}
    assert legs["c-loss"].outcome == VerdictOutcome.CLOSED_EARLY
    assert legs["c-loss"].close_reason is CloseReason.LOSS_EXIT
    assert legs["c-old"].close_reason is None
    assert legs["c-open"].close_reason is None
