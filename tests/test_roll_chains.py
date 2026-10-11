"""Roll-chain state and chain-credit profit-take (roll redesign Task 3)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.schemas import OptionRight, PositionSnapshot, RollOrigin

_OLD_EXP = date.today() + timedelta(days=2)
_NEW_EXP = date.today() + timedelta(days=9)


def _pos(strike: float = 330.0, expiry: date = _NEW_EXP, qty: float = -1) -> PositionSnapshot:
    return PositionSnapshot(
        symbol=f"GOOGL {expiry:%y%m%d}P{int(strike * 1000):08d}",
        sec_type="OPT",
        position=qty,
        avg_cost=100.0,
        right=OptionRight.PUT,
        strike=strike,
        expiry=expiry,
        underlying="GOOGL",
    )


def _seed(db, cid: str, strike: float, expiry: date, fills, payload: dict | None = None) -> None:
    from src.storage.models import CandidateRow, FillRow

    t0 = datetime.now(UTC) - timedelta(days=5)
    with db() as s:
        s.add(
            CandidateRow(
                candidate_id=cid,
                run_id="r",
                strategy="roll" if payload else "cash_secured_put",
                underlying="GOOGL",
                right="P",
                strike=strike,
                expiry=expiry,
                payload=payload or {},
            )
        )
        for i, (action, qty, price, comm) in enumerate(fills):
            s.add(
                FillRow(
                    order_id=1,
                    candidate_id=cid,
                    action=action,
                    filled_qty=qty,
                    avg_price=price,
                    commission=comm,
                    filled_at=t0 + timedelta(days=i),
                )
            )


def _origin() -> dict:
    return RollOrigin(
        con_id=1,
        candidate_id="c-old",
        strike=335.0,
        expiry=_OLD_EXP,
        right=OptionRight.PUT,
        contracts=1,
        chain_id="c-old",
        seq=1,
        original_expiry=_OLD_EXP,
        old_mid=3.00,
        new_mid=3.20,
    ).model_dump(mode="json")


def _rolled(db) -> None:
    _seed(db, "c-old", 335.0, _OLD_EXP, [("SELL", 1, 1.00, 1.0), ("BUY", 1, 3.00, 1.0)])
    _seed(db, "c-new", 330.0, _NEW_EXP, [("SELL", 1, 3.20, 1.0)], payload={"roll_from": _origin()})


def test_a_plain_short_is_seq_zero_with_its_own_credit(db) -> None:
    from src.execution.profit_take import net_entry_credit_per_share
    from src.storage.roll_chains import chain_entry_credit_per_share, chain_state

    _seed(db, "c-plain", 330.0, _NEW_EXP, [("SELL", 1, 1.50, 1.0)])
    with db() as s:
        state = chain_state(s, _pos())
        credit = chain_entry_credit_per_share(s, _pos())
        leg = net_entry_credit_per_share(s, "GOOGL", 330.0, _NEW_EXP, "P")
    assert (state.seq, state.chain_id, state.original_expiry) == (0, "c-plain", _NEW_EXP)
    assert credit == pytest.approx(leg)


def test_a_rolled_short_reports_its_chain(db) -> None:
    from src.storage.roll_chains import chain_entry_credit_per_share, chain_state

    _rolled(db)
    with db() as s:
        state = chain_state(s, _pos())
        credit = chain_entry_credit_per_share(s, _pos())
    assert (state.seq, state.chain_id, state.original_expiry) == (1, "c-old", _OLD_EXP)
    assert state.current_candidate_id == "c-new"
    # (1.00 − 3.00 + 3.20) per share, less $3 of commissions over 100 shares
    assert credit == pytest.approx(1.20 - 0.03)


def test_a_short_opened_outside_the_system_has_no_chain_credit(db) -> None:
    from src.storage.roll_chains import chain_entry_credit_per_share, chain_state

    with db() as s:
        state = chain_state(s, _pos(strike=300.0))
        assert chain_entry_credit_per_share(s, _pos(strike=300.0)) is None
    assert state.seq == 0 and state.current_candidate_id is None
    assert state.chain_id.startswith("chain:GOOGL:")


def test_a_self_referencing_payload_does_not_loop(db) -> None:
    from src.storage.roll_chains import chain_entry_credit_per_share

    loop = _origin() | {"candidate_id": "c-self"}
    _seed(db, "c-self", 330.0, _NEW_EXP, [("SELL", 1, 1.00, 0.0)], payload={"roll_from": loop})
    with db() as s:
        assert chain_entry_credit_per_share(s, _pos()) == pytest.approx(1.00)


async def test_profit_take_measures_the_chain_not_the_new_legs_gross_premium(db) -> None:
    """New leg sold at 3.20, chain credit 1.17: at mid 1.00 the leg alone shows 69% profit,
    the chain only 15% — the roll's buyback is not secured gain."""
    from src.common.config import SchedulerCfg
    from src.execution.profit_take import check_profit_takes

    _rolled(db)
    cfg = MagicMock()
    cfg.scheduler = SchedulerCfg()
    cfg.automation.auto_close_enabled = True
    with (
        patch("src.execution.profit_take.get_config", return_value=cfg),
        patch("src.ibkr.portfolio.get_positions", return_value=[_pos()]),
        patch("src.execution.profit_take._quote_short", new=AsyncMock(return_value=(0.98, 1.02))),
        patch("src.execution.profit_take._auto_close_position", new=AsyncMock()) as close,
    ):
        await check_profit_takes(MagicMock(), MagicMock(), AsyncMock(), "chat")
        close.assert_not_awaited()
        with patch(
            "src.execution.profit_take._quote_short", new=AsyncMock(return_value=(0.48, 0.52))
        ):
            await check_profit_takes(MagicMock(), MagicMock(), AsyncMock(), "chat")
    close.assert_awaited_once()  # 1 − 0.50/1.17 ≥ 50%
