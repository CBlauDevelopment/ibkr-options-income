"""Tests for two-leg combo roll execution (IMPROVEMENT_PLAN Phase 4).

A roll is sent as a single BAG combo: BUY-to-close the old short + SELL-to-open the new
short, atomically. These tests cover the combo builder's pricing convention, short
resolution, the new-leg re-gate + net-credit floor, the two-FillRow accounting, and
cancel-on-timeout. All IB calls are mocked; the DB uses a tmp_path SQLite.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.schemas import (
    OptionRight,
    OrderState,
    PositionSnapshot,
    RollOrigin,
    ScoreCard,
    Strategy,
    TradeCandidate,
)
from src.execution.order_builder import build_combo_roll_order
from src.execution.roll_executor import (
    _resolve_short_to_close,
    execute_roll,
)
from src.storage.models import CandidateRow, FillRow, OrderRow

_TODAY = date.today()
_OLD_EXPIRY = _TODAY + timedelta(days=14)
_NEW_EXPIRY = _TODAY + timedelta(days=42)


# --------------------------------------------------------------------------- #
# Fixtures / mock builders
# --------------------------------------------------------------------------- #
def _db_setup(tmp_path, monkeypatch) -> None:
    import src.storage.db as dbmod
    from src.common.config import Config

    monkeypatch.setattr(dbmod, "_engine", None)
    monkeypatch.setattr(dbmod, "_SessionLocal", None)
    monkeypatch.setattr(Config, "db_url_abs", lambda self: f"sqlite:///{tmp_path / 't.db'}")
    dbmod.init_db()


def _no_sleep(monkeypatch) -> None:
    import src.execution.roll_executor as rx

    monkeypatch.setattr(rx.asyncio, "sleep", AsyncMock())


def _short() -> PositionSnapshot:
    return PositionSnapshot(
        symbol="AAPL  PUT",
        sec_type="OPT",
        position=-2.0,
        avg_cost=1.50,
        right=OptionRight.PUT,
        strike=185.0,
        expiry=_OLD_EXPIRY,
        underlying="AAPL",
    )


def _roll_candidate(premium: float = 1.00) -> TradeCandidate:
    return TradeCandidate(
        candidate_id="roll:AAPL:P:180:x",
        strategy=Strategy.ROLL,
        underlying="AAPL",
        right=OptionRight.PUT,
        strike=180.0,
        expiry=_NEW_EXPIRY,
        contracts=2,
        premium=premium,  # approved NET credit per share
        collateral=180.0 * 2 * 100,
        roc_pct=0.55,
        annualized_yield_pct=14.0,
        breakeven=179.0,
        delta=-0.25,
        dte=(_NEW_EXPIRY - _TODAY).days,
        scores=ScoreCard(symbol="AAPL"),
        roll_from=RollOrigin(
            con_id=None,
            candidate_id=None,
            strike=185.0,
            expiry=_OLD_EXPIRY,
            right=OptionRight.PUT,
            contracts=2,
            chain_id="c",
            seq=1,
            original_expiry=_OLD_EXPIRY,
            old_mid=0.80,
            new_mid=1.80,
        ),
    )


def _ticker(bid: float, ask: float, delta: float, iv: float = 0.30) -> MagicMock:
    t = MagicMock()
    t.bid = bid
    t.ask = ask
    g = MagicMock()
    g.delta = delta
    g.impliedVol = iv
    t.modelGreeks = g
    return t


def _leg_fill(conid: int, action: str, price: float, shares: float, commission: float) -> MagicMock:
    f = MagicMock()
    f.contract.conId = conid
    f.execution.shares = shares
    f.execution.price = price
    f.execution.execId = f"{action}.{conid}"
    f.commissionReport.commission = commission
    return f


_OPEN_CONID = 1001  # new short (sell-to-open) — qualified first in execute_roll
_CLOSE_CONID = 1002  # old short (buy-to-close) — qualified second


def _make_ib(
    new_mid: tuple[float, float],
    old_mid: tuple[float, float],
    *,
    filled: bool = True,
    fill_qty: float = 2.0,
) -> MagicMock:
    """Build a mock IB. _fetch_leg is called new-first then old-first, so qualify/reqMktData
    side_effects are ordered [open, close]."""
    ib = MagicMock()
    open_qual = MagicMock()
    open_qual.conId = _OPEN_CONID
    close_qual = MagicMock()
    close_qual.conId = _CLOSE_CONID
    ib.qualifyContractsAsync = AsyncMock(side_effect=[[open_qual], [close_qual]])

    new_t = _ticker(new_mid[0], new_mid[1], delta=-0.25)
    old_t = _ticker(old_mid[0], old_mid[1], delta=-0.55)
    ib.reqMktData = MagicMock(side_effect=[new_t, old_t])
    ib.cancelMktData = MagicMock()

    trade = MagicMock()
    trade.isDone.return_value = filled
    trade.order.orderId = 555
    trade.orderStatus.filled = fill_qty if filled else 0.0
    trade.orderStatus.avgFillPrice = -(new_mid[0] + new_mid[1]) / 2 + (old_mid[0] + old_mid[1]) / 2
    trade.orderStatus.status = "Filled" if filled else "Submitted"
    if filled:
        nm = (new_mid[0] + new_mid[1]) / 2
        om = (old_mid[0] + old_mid[1]) / 2
        trade.fills = [
            _leg_fill(_OPEN_CONID, "SELL", nm, fill_qty, 0.65),
            _leg_fill(_CLOSE_CONID, "BUY", om, fill_qty, 0.65),
        ]
    else:
        trade.fills = []
    ib.placeOrder.return_value = trade
    ib.cancelOrder = MagicMock()
    return ib


def _seed_order(candidate: TradeCandidate) -> int:
    from src.storage.db import session_scope

    with session_scope() as s:
        row = OrderRow(
            candidate_id=candidate.candidate_id,
            approval_id=None,
            state=OrderState.SUBMITTED,
            is_live=False,
            detail="queued for roll",
        )
        s.add(row)
        s.flush()
        return row.id


# --------------------------------------------------------------------------- #
# Pure-function units
# --------------------------------------------------------------------------- #
def test_combo_builder_credit_is_negative_limit():
    combo, order = build_combo_roll_order("AAPL", _CLOSE_CONID, _OPEN_CONID, 2, net_credit=1.00)
    assert combo.secType == "BAG"
    assert len(combo.comboLegs) == 2
    buy, sell = combo.comboLegs
    assert (buy.conId, buy.action) == (_CLOSE_CONID, "BUY")
    assert (sell.conId, sell.action) == (_OPEN_CONID, "SELL")
    assert order.action == "BUY"
    assert order.totalQuantity == 2
    assert order.lmtPrice == -1.00  # credit → negative net debit


def test_combo_builder_rejects_bad_inputs():
    with pytest.raises(ValueError):
        build_combo_roll_order("AAPL", 0, _OPEN_CONID, 2, net_credit=1.0)
    with pytest.raises(ValueError):
        build_combo_roll_order("AAPL", _CLOSE_CONID, _OPEN_CONID, 0, net_credit=1.0)


def test_resolve_short_matches_the_exact_alerted_contract():
    """GOOGL 330P (nearer) and 335P (alerted) open together: the roll closes 335P."""
    near = _short().model_copy(update={"strike": 180.0, "con_id": 11})
    alerted = _short().model_copy(
        update={"expiry": _OLD_EXPIRY + timedelta(days=7), "strike": 190.0, "con_id": 22}
    )
    origin = _roll_candidate().roll_from.model_copy(
        update={"con_id": 22, "strike": 190.0, "expiry": alerted.expiry}
    )
    cand = _roll_candidate().model_copy(update={"roll_from": origin})
    assert _resolve_short_to_close([near, alerted], cand) is alerted


def test_resolve_falls_back_to_the_exact_contract_without_a_conid():
    other_strike = _short().model_copy(update={"strike": 180.0})
    assert _resolve_short_to_close([other_strike, _short()], _roll_candidate()) == _short()
    assert _resolve_short_to_close([other_strike], _roll_candidate()) is None


def test_resolve_refuses_a_roll_without_its_origin():
    cand = _roll_candidate().model_copy(update={"roll_from": None})
    assert _resolve_short_to_close([_short()], cand) is None


def test_walk_limits_concede_toward_natural_but_never_past_the_floor():
    from src.execution.roll_executor import _walk_targets

    assert _walk_targets(0.40, natural_net=0.10, floor=0.05, steps=3) == pytest.approx(
        [0.30, 0.20, 0.10]
    )
    assert _walk_targets(0.40, natural_net=-0.50, floor=0.25, steps=3) == pytest.approx(
        [0.35, 0.30, 0.25]
    )
    assert _walk_targets(0.40, natural_net=0.10, floor=0.05, steps=0) == []
    assert _walk_targets(0.20, natural_net=0.10, floor=0.30, steps=3) == []


# --------------------------------------------------------------------------- #
# Full execute_roll path
# --------------------------------------------------------------------------- #
async def test_roll_fills_writes_two_legs(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    import src.execution.roll_executor as rx

    monkeypatch.setattr(rx, "get_positions", lambda ib: [_short()])

    cand = _roll_candidate(premium=1.00)
    order_id = _seed_order(cand)
    # new mid 1.80, old mid 0.80 → net credit 1.00 (>= 0.80 floor).
    ib = _make_ib(new_mid=(1.78, 1.82), old_mid=(0.78, 0.82))
    bot = MagicMock()
    bot.send_message = AsyncMock()

    await execute_roll(ib, bot, "chat", order_id, cand)

    ib.placeOrder.assert_called_once()
    from src.storage.db import session_scope

    with session_scope() as s:
        order = s.get(OrderRow, order_id)
        fills = s.query(FillRow).order_by(FillRow.action).all()
        assert order.state == OrderState.FILLED
        assert len(fills) == 2
        buy = next(f for f in fills if f.action == "BUY")
        sell = next(f for f in fills if f.action == "SELL")
        assert sell.candidate_id == cand.candidate_id
        assert sell.entry_iv == pytest.approx(0.30)
        # No original CandidateRow → synthetic close attribution.
        assert buy.candidate_id.startswith("roll-close:AAPL:")
        assert buy.close_reason == "roll" and sell.close_reason is None


async def test_roll_close_leg_attributed_to_original_short(tmp_path, monkeypatch):
    """When the short was opened by the system, the BUY-close fill is recorded under the
    original candidate_id so the verdict ledger labels it closed_early."""
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    import src.execution.roll_executor as rx

    monkeypatch.setattr(rx, "get_positions", lambda ib: [_short()])

    from src.storage.db import session_scope

    orig_id = "cash_secured_put:AAPL:P:185:orig"
    with session_scope() as s:
        s.add(
            CandidateRow(
                candidate_id=orig_id,
                run_id="r1",
                strategy="cash_secured_put",
                underlying="AAPL",
                right="P",
                strike=185.0,
                expiry=_OLD_EXPIRY,
                payload={},
            )
        )
        s.add(
            FillRow(
                order_id=1,
                candidate_id=orig_id,
                action="SELL",
                filled_qty=2.0,
                avg_price=1.50,
            )
        )

    cand = _roll_candidate()
    order_id = _seed_order(cand)
    ib = _make_ib(new_mid=(1.78, 1.82), old_mid=(0.78, 0.82))
    bot = MagicMock()
    bot.send_message = AsyncMock()

    await execute_roll(ib, bot, "chat", order_id, cand)

    with session_scope() as s:
        buy = s.query(FillRow).filter(FillRow.action == "BUY").one()
        assert buy.candidate_id == orig_id


async def test_roll_rejected_on_credit_collapse(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    import src.execution.roll_executor as rx

    monkeypatch.setattr(rx, "get_positions", lambda ib: [_short()])

    cand = _roll_candidate(premium=1.00)
    order_id = _seed_order(cand)
    # new mid 1.80, old mid 1.20 → net 0.60 < 0.80 * 1.00 floor → collapse.
    ib = _make_ib(new_mid=(1.78, 1.82), old_mid=(1.18, 1.22))
    bot = MagicMock()
    bot.send_message = AsyncMock()

    await execute_roll(ib, bot, "chat", order_id, cand)

    ib.placeOrder.assert_not_called()
    from src.storage.db import session_scope

    with session_scope() as s:
        order = s.get(OrderRow, order_id)
        assert order.state == OrderState.REJECTED
        assert "collapse" in (order.detail or "")
        assert s.query(FillRow).count() == 0


async def test_roll_rejected_on_net_debit(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    import src.execution.roll_executor as rx

    monkeypatch.setattr(rx, "get_positions", lambda ib: [_short()])

    cand = _roll_candidate(premium=1.00)
    order_id = _seed_order(cand)
    # new mid 0.80 < old mid 1.00 → net debit.
    ib = _make_ib(new_mid=(0.78, 0.82), old_mid=(0.98, 1.02))
    bot = MagicMock()
    bot.send_message = AsyncMock()

    await execute_roll(ib, bot, "chat", order_id, cand)

    ib.placeOrder.assert_not_called()
    from src.storage.db import session_scope

    with session_scope() as s:
        assert s.get(OrderRow, order_id).state == OrderState.REJECTED


async def test_roll_rejected_when_no_matching_short(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    import src.execution.roll_executor as rx

    monkeypatch.setattr(rx, "get_positions", lambda ib: [])  # no positions

    cand = _roll_candidate()
    order_id = _seed_order(cand)
    ib = _make_ib(new_mid=(1.78, 1.82), old_mid=(0.78, 0.82))
    bot = MagicMock()
    bot.send_message = AsyncMock()

    await execute_roll(ib, bot, "chat", order_id, cand)

    ib.placeOrder.assert_not_called()
    ib.qualifyContractsAsync.assert_not_called()
    from src.storage.db import session_scope

    with session_scope() as s:
        assert s.get(OrderRow, order_id).state == OrderState.REJECTED


async def test_roll_cancels_on_timeout(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    import src.execution.roll_executor as rx

    monkeypatch.setattr(rx, "get_positions", lambda ib: [_short()])
    # Force the fill deadline to be already past.
    real_cfg = rx.get_config()
    cfg = MagicMock()
    cfg.is_live = False
    cfg.execution.fill_timeout_minutes = 0.0
    cfg.risk = real_cfg.risk
    cfg.roll = real_cfg.roll
    monkeypatch.setattr(rx, "get_config", lambda: cfg)

    cand = _roll_candidate()
    order_id = _seed_order(cand)
    ib = _make_ib(new_mid=(1.78, 1.82), old_mid=(0.78, 0.82), filled=False)
    bot = MagicMock()
    bot.send_message = AsyncMock()

    await execute_roll(ib, bot, "chat", order_id, cand)

    ib.cancelOrder.assert_called_once()
    from src.storage.db import session_scope

    with session_scope() as s:
        assert s.get(OrderRow, order_id).state == OrderState.CANCELLED
        assert s.query(FillRow).count() == 0


def _cfg(monkeypatch, *, steps: int = 3, ratio: float = 0.0, timeout: float = 1.0, **roll):
    import src.execution.roll_executor as rx
    from src.common.config import RollCfg

    cfg = MagicMock()
    cfg.is_live = False
    cfg.execution.fill_timeout_minutes = timeout
    cfg.execution.reprice_interval_seconds = 0.0
    cfg.risk = {"live_execution": {"min_live_premium_ratio": ratio}}
    cfg.roll = RollCfg(exec={"reprice_steps": steps}, **roll)
    monkeypatch.setattr(rx, "get_config", lambda: cfg)
    return cfg


async def _run(monkeypatch, cand, ib, positions):
    import src.execution.roll_executor as rx

    monkeypatch.setattr(rx, "get_positions", lambda ib_: positions)
    order_id = _seed_order(cand)
    bot = MagicMock()
    bot.send_message = AsyncMock()
    await execute_roll(ib, bot, "chat", order_id, cand)
    from src.storage.db import session_scope

    with session_scope() as s:
        row = s.get(OrderRow, order_id)
        return row.state, row.detail, row.limit_price


async def test_a_changed_position_size_is_refused(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    _cfg(monkeypatch)
    ib = _make_ib(new_mid=(1.78, 1.82), old_mid=(0.78, 0.82))
    one_left = _short().model_copy(update={"position": -1.0})
    state, detail, _ = await _run(monkeypatch, _roll_candidate(), ib, [one_left])
    assert state == OrderState.REJECTED and "position_size_changed" in detail
    ib.placeOrder.assert_not_called()


def _call_roll(net: float):
    short = _short().model_copy(update={"right": OptionRight.CALL})
    origin = _roll_candidate().roll_from.model_copy(
        update={"right": OptionRight.CALL, "allow_debit": True}
    )
    cand = _roll_candidate(premium=net).model_copy(
        update={"right": OptionRight.CALL, "strike": 190.0, "delta": 0.45, "roll_from": origin}
    )
    return short, cand


async def test_a_keep_shares_call_roll_within_the_debit_cap_is_placed(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    _cfg(monkeypatch, steps=0)
    short, cand = _call_roll(-0.20)
    # new mid 1.00, old mid 1.20 → net −0.20 (cap 0.25)
    ib = _make_ib(new_mid=(0.98, 1.02), old_mid=(1.18, 1.22))
    state, _, limit = await _run(monkeypatch, cand, ib, [short])
    assert state == OrderState.FILLED and limit == pytest.approx(0.20)


async def test_a_call_roll_beyond_the_debit_cap_is_refused(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    _cfg(monkeypatch, steps=0)
    short, cand = _call_roll(-0.20)
    ib = _make_ib(new_mid=(0.88, 0.92), old_mid=(1.18, 1.22))  # net −0.30
    state, detail, _ = await _run(monkeypatch, cand, ib, [short])
    assert state == OrderState.REJECTED and "roll_net_below_floor" in detail


async def test_a_csp_debit_roll_is_refused_at_send_time(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    _cfg(monkeypatch, steps=0)
    ib = _make_ib(new_mid=(0.78, 0.82), old_mid=(0.80, 0.84))  # net −0.02
    state, detail, _ = await _run(monkeypatch, _roll_candidate(premium=0.40), ib, [_short()])
    assert state == OrderState.REJECTED and "roll_net_below_floor" in detail


async def test_a_breached_roll_leg_is_not_held_to_the_entry_delta_band(tmp_path, monkeypatch):
    """New leg at |Δ| 0.50 (entry band is 0.20-0.35) but below the old leg's 0.55: placed."""
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    _cfg(monkeypatch, steps=0)
    ib = _make_ib(new_mid=(1.78, 1.82), old_mid=(0.78, 0.82))
    ib.reqMktData.side_effect = [_ticker(1.78, 1.82, -0.50), _ticker(0.78, 0.82, -0.55)]
    state, _, _ = await _run(monkeypatch, _roll_candidate(), ib, [_short()])
    assert state == OrderState.FILLED


async def test_a_roll_leg_with_more_delta_than_the_old_one_is_refused(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    _cfg(monkeypatch, steps=0)
    ib = _make_ib(new_mid=(1.78, 1.82), old_mid=(0.78, 0.82))
    ib.reqMktData.side_effect = [_ticker(1.78, 1.82, -0.70), _ticker(0.78, 0.82, -0.55)]
    state, detail, _ = await _run(monkeypatch, _roll_candidate(), ib, [_short()])
    assert state == OrderState.REJECTED and "roll_delta_increases" in detail


async def test_the_combo_walks_toward_natural_in_bounded_steps(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    _cfg(monkeypatch, steps=3)
    # new 1.60/1.80 (mid 1.70), old 1.20/1.40 (mid 1.30): net mid 0.40, natural 0.20
    ib = _make_ib(new_mid=(1.60, 1.80), old_mid=(1.20, 1.40))
    calls = {"n": 0}

    def _isdone() -> bool:
        calls["n"] += 1
        return calls["n"] > 7  # isDone is read twice per loop: three walk steps, then filled

    trade = ib.placeOrder.return_value
    trade.isDone.side_effect = _isdone
    limits: list[float] = []

    def _place(contract, order):  # noqa: ANN001
        limits.append(order.lmtPrice)  # the Order object is mutated in place; record now
        return trade

    ib.placeOrder.side_effect = _place
    state, _, limit = await _run(monkeypatch, _roll_candidate(premium=0.40), ib, [_short()])
    assert limits == pytest.approx([-0.40, -0.33, -0.27, -0.20])
    assert limits[0] == pytest.approx(-0.40)
    assert limit == pytest.approx(-0.20)  # ends at natural, never past it
    assert all(lim <= -0.05 + 1e-9 for lim in limits)  # never below the 0.05 floor credit


async def test_both_roll_fills_join_the_campaign(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    _no_sleep(monkeypatch)
    _cfg(monkeypatch, steps=0)
    seen: list[tuple] = []
    monkeypatch.setattr("src.storage.campaigns.attach_fill_to_campaign", lambda *a: seen.append(a))
    ib = _make_ib(new_mid=(1.78, 1.82), old_mid=(0.78, 0.82))
    await _run(monkeypatch, _roll_candidate(), ib, [_short()])
    assert sorted(a[3] for a in seen) == ["BUY", "SELL"]
    assert {a[2] for a in seen} == {"roll"}
