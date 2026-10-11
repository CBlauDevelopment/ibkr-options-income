"""roll_pipeline.evaluate_roll (roll redesign Task 8): fetch → decide → gate → approval."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.schemas import (
    AccountSnapshot,
    FundamentalStats,
    IVStats,
    OptionQuote,
    OptionRight,
    PositionSnapshot,
    TechnicalStats,
)

_TODAY = date.today()
_OLD = _TODAY + timedelta(days=4)
_NEW = _TODAY + timedelta(days=11)


def _pos() -> PositionSnapshot:
    return PositionSnapshot(
        symbol="AAPL x",
        sec_type="OPT",
        position=-1,
        avg_cost=1.0,
        right=OptionRight.PUT,
        strike=200.0,
        expiry=_OLD,
        underlying="AAPL",
        con_id=555,
    )


def _q(expiry: date, mid: float, delta: float) -> OptionQuote:
    return OptionQuote(
        underlying="AAPL",
        right=OptionRight.PUT,
        strike=200.0,
        expiry=expiry,
        bid=round(mid - 0.05, 2),
        ask=round(mid + 0.05, 2),
        delta=delta,
        open_interest=900,
        volume=90,
        underlying_price=195.0,
    )


@pytest.fixture()
def wired(db, monkeypatch: pytest.MonkeyPatch):
    """Patch the IBKR/network boundary evaluate_roll consults; return the knobs."""
    import src.execution.roll_pipeline as rp

    state = {
        "quotes": [_q(_OLD, 5.50, -0.70), _q(_NEW, 5.90, -0.62)],
        "fund": FundamentalStats(symbol="AAPL"),
        "would_own": ["AAPL"],
    }

    async def _fetch(ib, pos, **kw):  # noqa: ANN001, ANN003
        return list(state["quotes"])

    monkeypatch.setattr(rp, "get_roll_chain_quotes_async", _fetch)
    monkeypatch.setattr(rp, "get_iv_stats", lambda sym, quotes=None: IVStats(symbol=sym))
    monkeypatch.setattr(
        rp, "get_technical_stats", lambda sym, *a, **k: TechnicalStats(symbol=sym, price=195.0)
    )
    monkeypatch.setattr(rp, "get_fundamental_stats", lambda sym: state["fund"])
    monkeypatch.setattr(rp, "get_positions", lambda ib: [_pos()])
    monkeypatch.setattr(
        rp,
        "get_account_snapshot_async",
        AsyncMock(
            return_value=AccountSnapshot(
                account="DU1",
                net_liquidation=500_000.0,
                total_cash=400_000.0,
                buying_power=800_000.0,
                maintenance_margin=10_000.0,
                excess_liquidity=400_000.0,
            )
        ),
    )
    monkeypatch.setattr(rp, "effective_universe", lambda: {"would_own": state["would_own"]})
    cfg = rp.get_config().model_copy(deep=True)
    cfg.roll.csp.when_assignable = "roll_if_credit"
    monkeypatch.setattr(rp, "get_config", lambda: cfg)
    return state


async def _evaluate(**kw):  # noqa: ANN003
    from src.execution.roll_pipeline import evaluate_roll

    return await evaluate_roll(MagicMock(), _pos(), chat_id="1", ttl_minutes=30, **kw)


async def test_a_breached_csp_with_a_credit_roll_raises_one_pending_approval(wired, db) -> None:
    from src.storage.models import ApprovalRow

    decision, approval_id = await _evaluate()
    assert decision.action == "roll" and approval_id is not None
    with db() as s:
        row = s.get(ApprovalRow, approval_id)
        assert row.status == "pending"
        assert row.snapshot["roll_from"]["con_id"] == 555


async def test_a_rules_engine_reject_falls_back_to_assignment(
    wired, db, monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.execution.roll_pipeline as rp
    from src.common.schemas import RiskVerdict, Verdict

    def _reject(cands, *a, **k):  # noqa: ANN001, ANN002, ANN003
        return [
            RiskVerdict(
                candidate_id=cands[0].candidate_id, verdict=Verdict.REJECT, reasons=["margin_limit"]
            )
        ]

    monkeypatch.setattr(rp, "validate_candidates", _reject)
    decision, approval_id = await _evaluate()
    assert (decision.action, decision.reason, approval_id) == (
        "assign",
        "rules_engine:margin_limit",
        None,
    )


async def test_a_second_evaluation_while_pending_proposes_nothing_new(wired, db) -> None:
    from src.storage.models import ApprovalRow

    first, first_id = await _evaluate()
    second, second_id = await _evaluate()
    assert first.action == "roll"
    assert (second.action, second.reason, second_id) == ("defer", "roll_pending", first_id)
    with db() as s:
        assert s.query(ApprovalRow).count() == 1


async def test_an_empty_fetch_defers(wired) -> None:
    wired["quotes"] = []
    decision, approval_id = await _evaluate()
    assert (decision.action, decision.reason, approval_id) == ("defer", "chain_unavailable", None)


async def test_a_missing_quote_for_the_short_itself_defers(wired) -> None:
    wired["quotes"] = [_q(_NEW, 5.90, -0.62)]
    decision, _ = await _evaluate()
    assert (decision.action, decision.reason) == ("defer", "current_unpriced")


async def test_a_put_we_would_not_own_is_closed_without_an_approval(wired) -> None:
    wired["would_own"] = []
    decision, approval_id = await _evaluate()
    assert (decision.action, approval_id) == ("close", None)
