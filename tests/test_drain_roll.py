"""M5 Task 5.1 + roll redesign Task 13: a roll request proposes. It never rolls.

The handler is a thin resolver around ``roll_pipeline.evaluate_roll`` — the same decision path
the intraday monitor runs, with ``manual=True``: it resolves the position from a live portfolio
read and maps the policy's decision onto the five reasons in ``docs/web/commands.md``'s
roll_request table. ``evaluate_roll`` (fetch → policy → Rules Engine → approval) has its own
tests (tests/test_roll_evaluate.py); here it is the mocked boundary.
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.schemas import (
    ApprovalStatus,
    OptionRight,
    PositionSnapshot,
    RollDecision,
    ScoreCard,
    Strategy,
    TradeCandidate,
)


def _db_setup(tmp_path, monkeypatch) -> None:
    import src.storage.db as dbmod
    from src.common.config import Config

    monkeypatch.setattr(dbmod, "_engine", None)
    monkeypatch.setattr(dbmod, "_SessionLocal", None)
    monkeypatch.setattr(
        Config, "db_url_abs", lambda self: f"sqlite:///{tmp_path / 'roll_drain.db'}"
    )
    dbmod.init_db()


@pytest.fixture
def drain_env(monkeypatch, tmp_path):
    """A temp trading DB + fake bot + position/approval/order helpers, roll_request registered only."""
    _db_setup(tmp_path, monkeypatch)

    from src.notify.command_drain import HANDLERS
    from src.storage.app_commands import enqueue_command
    from src.storage.db import session_scope
    from src.storage.models import AppCommandRow, ApprovalRow, CandidateRow, OrderRow

    saved_handlers = dict(HANDLERS)
    HANDLERS.clear()
    HANDLERS.update({k: v for k, v in saved_handlers.items() if k == "roll_request"})

    bot = AsyncMock()
    positions: list[PositionSnapshot] = []

    # The handler resolves the position from a live portfolio read, not a stored snapshot —
    # patching the source module the deferred import resolves from at call time.
    monkeypatch.setattr("src.ibkr.portfolio.get_positions", lambda ib: list(positions))

    def seed_short(
        position_symbol: str,
        *,
        underlying: str = "NVDA",
        delta: float = -0.45,
        dte: int = 9,
        strike: float = 180.0,
        right: str = "C",
        contracts: int = 1,
    ) -> PositionSnapshot:
        pos = PositionSnapshot(
            symbol=position_symbol,
            sec_type="OPT",
            position=-float(contracts),
            avg_cost=1.50,
            right=OptionRight.CALL if right == "C" else OptionRight.PUT,
            strike=strike,
            expiry=date.today() + timedelta(days=dte),
            delta=delta,
            underlying=underlying,
        )
        positions.append(pos)
        return pos

    def seed_long(
        position_symbol: str,
        *,
        underlying: str = "NVDA",
        strike: float = 180.0,
        dte: int = 9,
    ) -> PositionSnapshot:
        pos = PositionSnapshot(
            symbol=position_symbol,
            sec_type="OPT",
            position=1.0,
            avg_cost=1.50,
            right=OptionRight.CALL,
            strike=strike,
            expiry=date.today() + timedelta(days=dte),
            delta=0.30,
            underlying=underlying,
        )
        positions.append(pos)
        return pos

    def enqueue(kind: str, payload: dict) -> int:
        with session_scope() as s:
            row, _ = enqueue_command(s, kind=kind, payload=payload, requested_by="test")
            return row.id

    def status(cid: int) -> str:
        with session_scope() as s:
            row = s.get(AppCommandRow, cid)
            assert row is not None
            return row.status

    def result(cid: int) -> dict:
        with session_scope() as s:
            row = s.get(AppCommandRow, cid)
            assert row is not None
            return row.result or {}

    def approval_status(approval_id: int) -> str:
        with session_scope() as s:
            row = s.get(ApprovalRow, approval_id)
            assert row is not None
            return row.status

    def order_for_approval(approval_id: int) -> OrderRow | None:
        with session_scope() as s:
            row = s.query(OrderRow).filter(OrderRow.approval_id == approval_id).one_or_none()
            if row is None:
                return None
            s.expunge(row)
            return row

    def approval(approval_id: int) -> ApprovalRow:
        with session_scope() as s:
            row = s.get(ApprovalRow, approval_id)
            assert row is not None
            s.expunge(row)
            return row

    def pending_approval_count(*, underlying: str) -> int:
        with session_scope() as s:
            return (
                s.query(ApprovalRow)
                .join(CandidateRow, CandidateRow.candidate_id == ApprovalRow.candidate_id)
                .filter(
                    CandidateRow.underlying == underlying,
                    ApprovalRow.status == ApprovalStatus.PENDING.value,
                )
                .count()
            )

    def total_order_count() -> int:
        with session_scope() as s:
            return s.query(OrderRow).count()

    def seed_working_roll(
        candidate_id: str, *, approval_id: int | None = None, state: str = "queued"
    ) -> int:
        """Seed an ApprovalRow (the working order's origin) + its active OrderRow."""
        with session_scope() as s:
            approval = ApprovalRow(
                candidate_id=candidate_id,
                status=ApprovalStatus.APPROVED,
                snapshot={"underlying": "NVDA", "strategy": "roll"},
                expires_at=None,
                decided_at=None,
            )
            s.add(approval)
            s.flush()
            order = OrderRow(
                candidate_id=candidate_id,
                approval_id=approval_id if approval_id is not None else approval.id,
                state=state,
                snapshot={"underlying": "NVDA", "strategy": "roll"},
            )
            s.add(order)
            s.flush()
            return approval.id

    env = SimpleNamespace(
        bot=bot,
        ib=MagicMock(),  # a non-None sentinel; the fake chain mocks every real call
        enqueue=enqueue,
        status=status,
        result=result,
        approval_status=approval_status,
        order_for_approval=order_for_approval,
        approval=approval,
        pending_approval_count=pending_approval_count,
        total_order_count=total_order_count,
        seed_short=seed_short,
        seed_long=seed_long,
        seed_working_roll=seed_working_roll,
    )

    yield env

    HANDLERS.clear()
    HANDLERS.update(saved_handlers)


_SYM = "NVDA  261017C00180000"


def _candidate() -> TradeCandidate:
    return TradeCandidate(
        candidate_id="roll-nvda-185",
        strategy=Strategy.ROLL,
        underlying="NVDA",
        right=OptionRight.CALL,
        strike=185.0,
        expiry=date.today() + timedelta(days=16),
        premium=-0.10,
        collateral=18_500.0,
        roc_pct=0.0,
        annualized_yield_pct=0.0,
        breakeven=184.9,
        dte=16,
        scores=ScoreCard(symbol="NVDA"),
    )


@pytest.fixture
def evaluate(monkeypatch):
    """Patch evaluate_roll; ``evaluate.returns(decision, approval_id)`` sets its answer."""
    mock = AsyncMock(return_value=(RollDecision(action="hold", reason="x"), None))
    monkeypatch.setattr("src.execution.roll_pipeline.evaluate_roll", mock)
    mock.returns = lambda d, a=None: setattr(mock, "return_value", (d, a))  # type: ignore[attr-defined]
    return mock


async def _drain(env, ib=...):  # noqa: ANN001
    from src.notify.command_drain import drain_once

    await drain_once(env.ib if ib is ... else ib, env.bot, "chat")


async def test_a_roll_decision_returns_its_pending_approval(drain_env, evaluate) -> None:
    drain_env.seed_short(_SYM)
    evaluate.returns(RollDecision(action="roll", reason="credit_roll", candidate=_candidate()), 41)
    cid = drain_env.enqueue("roll_request", {"position_symbol": _SYM})
    await _drain(drain_env)
    assert drain_env.status(cid) == "applied"
    assert drain_env.result(cid) == {"approval_id": 41, "candidate_id": "roll-nvda-185"}
    assert evaluate.await_args.kwargs["manual"] is True


async def test_a_roll_request_never_places_an_order(drain_env, evaluate) -> None:
    drain_env.seed_short(_SYM)
    evaluate.returns(RollDecision(action="roll", reason="credit_roll", candidate=_candidate()), 41)
    drain_env.enqueue("roll_request", {"position_symbol": _SYM})
    await _drain(drain_env)
    assert drain_env.total_order_count() == 0


@pytest.mark.parametrize("action", ["assign", "let_called_away", "hold", "close"])
async def test_a_no_roll_decision_is_no_qualifying_roll_with_the_decision(
    drain_env, evaluate, action
) -> None:
    drain_env.seed_short(_SYM)
    evaluate.returns(RollDecision(action=action, reason="net_below_floor"))
    cid = drain_env.enqueue("roll_request", {"position_symbol": _SYM})
    await _drain(drain_env)
    assert drain_env.status(cid) == "failed"
    res = drain_env.result(cid)
    assert res["reason"] == "no_qualifying_roll"
    assert res["detail"] == {"decision": action, "reason": "net_below_floor"}


async def test_a_pending_roll_is_roll_already_working(drain_env, evaluate) -> None:
    drain_env.seed_short(_SYM)
    evaluate.returns(RollDecision(action="defer", reason="roll_pending"), 17)
    cid = drain_env.enqueue("roll_request", {"position_symbol": _SYM})
    await _drain(drain_env)
    res = drain_env.result(cid)
    assert (res["reason"], res["detail"]) == ("roll_already_working", {"approval_id": 17})


@pytest.mark.parametrize("reason", ["chain_unavailable", "current_unpriced"])
async def test_a_data_deferral_is_chain_unavailable(drain_env, evaluate, reason) -> None:
    drain_env.seed_short(_SYM)
    evaluate.returns(RollDecision(action="defer", reason=reason, detail="no data"))
    cid = drain_env.enqueue("roll_request", {"position_symbol": _SYM})
    await _drain(drain_env)
    res = drain_env.result(cid)
    assert (res["reason"], res["detail"]) == ("chain_unavailable", {"detail": "no data"})


async def test_a_long_position_is_refused(drain_env, evaluate) -> None:
    drain_env.seed_long(_SYM)
    cid = drain_env.enqueue("roll_request", {"position_symbol": _SYM})
    await _drain(drain_env)
    assert drain_env.result(cid)["reason"] == "not_an_open_short"
    evaluate.assert_not_awaited()


async def test_a_position_not_held_is_refused(drain_env, evaluate) -> None:
    cid = drain_env.enqueue("roll_request", {"position_symbol": _SYM})
    await _drain(drain_env)
    assert drain_env.result(cid)["reason"] == "position_not_found"


async def test_a_roll_request_with_no_broker_fails_honestly(drain_env, evaluate) -> None:
    cid = drain_env.enqueue("roll_request", {"position_symbol": _SYM})
    await _drain(drain_env, ib=None)
    assert drain_env.result(cid)["reason"] == "broker_unavailable"


async def test_a_roll_that_could_not_be_queued_is_a_handler_error(drain_env, evaluate) -> None:
    drain_env.seed_short(_SYM)
    evaluate.returns(RollDecision(action="roll", reason="credit_roll", candidate=_candidate()))
    cid = drain_env.enqueue("roll_request", {"position_symbol": _SYM})
    await _drain(drain_env)
    assert drain_env.status(cid) == "failed"
    assert drain_env.result(cid)["reason"] not in ("no_qualifying_roll", "roll_already_working")
