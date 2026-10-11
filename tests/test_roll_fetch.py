"""Targeted roll chain fetch (roll redesign Task 4).

The scan fetch builds only OTM contracts inside the 7-28 DTE entry window, so an ITM short or a
short at ≤ 6 DTE was never priced and every roll candidate was skipped (54 alerts, 0 rolls). The
roll fetch asks for the alerted contract itself plus a handful of later, same-or-better strikes.
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.schemas import OptionQuote, OptionRight, PositionSnapshot

_TODAY = date(2026, 10, 12)


def _exp(days: int) -> str:
    return f"{_TODAY + timedelta(days=days):%Y%m%d}"


_EXPIRATIONS = [_exp(d) for d in (5, 12, 19, 26, 33, 40, 47)]
_STRIKES = [float(s) for s in range(300, 371, 5)]


def _pos(right: OptionRight, strike: float, days: int) -> PositionSnapshot:
    return PositionSnapshot(
        symbol="GOOGL x",
        sec_type="OPT",
        position=-2,
        avg_cost=1.0,
        right=right,
        strike=strike,
        expiry=_TODAY + timedelta(days=days),
        underlying="GOOGL",
        con_id=42,
    )


def _specs(pos: PositionSnapshot, **kw: int) -> list[tuple[date, float]]:
    from src.ibkr.market_data import _roll_contract_specs

    args = {"max_expiries": 3, "target_dte_max": 35, "strikes_outward": 5} | kw
    return _roll_contract_specs(_EXPIRATIONS, _STRIKES, pos, _TODAY, **args)


def test_the_alerted_contract_is_included_even_itm_and_inside_a_week() -> None:
    pos = _pos(OptionRight.PUT, 335.0, 5)
    assert (pos.expiry, 335.0) in _specs(pos)


def test_put_strikes_go_down_and_call_strikes_go_up() -> None:
    put = _pos(OptionRight.PUT, 335.0, 5)
    call = _pos(OptionRight.CALL, 335.0, 5)
    later_put = {k for e, k in _specs(put) if e != put.expiry}
    later_call = {k for e, k in _specs(call) if e != call.expiry}
    assert later_put == {335.0, 330.0, 325.0, 320.0, 315.0, 310.0}
    assert later_call == {335.0, 340.0, 345.0, 350.0, 355.0, 360.0}


def test_only_later_expirations_up_to_the_cap() -> None:
    pos = _pos(OptionRight.PUT, 335.0, 5)
    later = sorted({e for e, _ in _specs(pos) if e != pos.expiry})
    assert later == [_TODAY + timedelta(days=d) for d in (12, 19, 26)]
    capped = sorted({e for e, _ in _specs(pos, target_dte_max=20) if e != pos.expiry})
    assert capped == [_TODAY + timedelta(days=d) for d in (12, 19)]


def test_contract_count_is_bounded() -> None:
    pos = _pos(OptionRight.PUT, 335.0, 5)
    assert len(_specs(pos)) <= 1 + 3 * (5 + 1)


async def test_the_async_fetch_quotes_in_roll_sized_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.ibkr.market_data as md

    monkeypatch.setattr(md, "today_et", lambda: _TODAY)
    stock = SimpleNamespace(symbol="GOOGL", secType="STK", conId=1)
    monkeypatch.setattr(md, "qualify_stock_async", AsyncMock(return_value=stock))
    chain = SimpleNamespace(
        tradingClass="GOOGL", exchange="SMART", expirations=_EXPIRATIONS, strikes=_STRIKES
    )
    built: list[object] = []

    async def _qualify(ib, contracts, **kw):  # noqa: ANN001, ANN003
        built.extend(contracts)
        return contracts

    batches: list[int] = []

    async def _quotes(ib, contracts, batch_size, throttle):  # noqa: ANN001
        batches.append(batch_size)
        return [
            OptionQuote(
                underlying="GOOGL",
                right=OptionRight.PUT,
                strike=c.strike,
                expiry=date(
                    int(c.lastTradeDateOrContractMonth[:4]),
                    int(c.lastTradeDateOrContractMonth[4:6]),
                    int(c.lastTradeDateOrContractMonth[6:]),
                ),
                bid=1.0,
                ask=1.2,
                delta=-0.4,
            )
            for c in contracts
        ]

    monkeypatch.setattr(md, "qualify_options_async", _qualify)
    monkeypatch.setattr(md, "_batch_quotes_async", _quotes)
    ib = MagicMock()
    ib.reqSecDefOptParamsAsync = AsyncMock(return_value=[chain])

    pos = _pos(OptionRight.PUT, 335.0, 5)
    quotes = await md.get_roll_chain_quotes_async(
        ib, pos, max_expiries=3, target_dte_max=35, strikes_outward=5, batch_size=10
    )
    assert batches == [10]
    assert all(c.right == "P" for c in built)
    assert any(q.strike == 335.0 and q.expiry == pos.expiry for q in quotes)
    assert len(quotes) == len(built) <= 19
