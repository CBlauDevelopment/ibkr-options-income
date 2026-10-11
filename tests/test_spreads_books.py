from __future__ import annotations

import pytest

from src.common.schemas import (
    SpreadBriefResult,
    SpreadLlmCall,
    SpreadMarketSnapshot,
    SpreadPick,
)
from src.spreads.executor import SpreadExecutor
from tests.test_spreads_service import (  # noqa: F401 — spreads_db is a fixture
    ONE_A_DAY,
    T0945,
    T1100,
    T1610,
    FakeBroker,
    FakeNotifier,
    o,
    spreads_db,
)
from tests.test_spreads_store import cand


class QuietPicker:
    """Never has a plan and always skips — these tests are about the books, not the picks."""

    async def brief(self, req):
        return SpreadBriefResult(
            plan=None, market=SpreadMarketSnapshot(), call=SpreadLlmCall(model="f", effort="")
        )

    async def pick(self, req):
        return SpreadPick(
            choice="skip", market=SpreadMarketSnapshot(), call=SpreadLlmCall(model="f", effort="")
        )


def make_books(tmp_path, clock, cfg=ONE_A_DAY):
    from src.spreads.service import SpreadsService

    broker = FakeBroker(clock)
    notifier = FakeNotifier()
    ex = SpreadExecutor(None, broker, cfg, now=lambda: clock[0])
    svc = SpreadsService(
        broker,
        ex,
        notifier,
        cfg,
        halt_path=tmp_path / "halt",
        now=lambda: clock[0],
        picker=QuietPicker(),
    )
    (tmp_path / "halt").touch()  # no entries: these tests drive the books by hand
    return svc, broker, notifier


async def test_with_a_picker_there_are_two_books_and_the_baseline_is_simulated(
    tmp_path,
    spreads_db,  # noqa: F811
) -> None:
    clock = [T0945]
    svc, _, _ = make_books(tmp_path, clock)
    assert [m for m, _ in svc.books] == ["shadow", "baseline"]
    assert svc.baseline_executor is not None and svc.baseline_executor.cfg.mode == "shadow"


async def test_the_baseline_book_is_managed_and_sized_on_its_own(
    tmp_path,
    spreads_db,  # noqa: F811
) -> None:
    clock = [T0945]
    svc, broker, notifier = make_books(tmp_path, clock)
    await svc.tick()  # map
    spreads_db.open_position(
        cand("b1-BL"),
        mode="baseline",
        contracts=1,
        credit=0.57,
        commission=1.3,
        now=T0945,
        perm_id=None,
        episode_key="ep",
    )
    ctx = svc._context(T0945, svc.levels, 50_000.0, "baseline")
    assert ctx.trades_today == 1 and svc._context(T0945, svc.levels, 50_000.0).trades_today == 0
    broker.leg_quotes = {
        (679.0, "P"): o(679, "P", 0.30, 0.34),
        (674.0, "P"): o(674, "P", 0.03, 0.05),
    }
    clock[0] = T1100
    await svc.tick()  # profit take on the baseline book only
    ((_, reason, pnl),) = spreads_db.closed_results("baseline")
    assert reason == "profit_take" and spreads_db.closed_results("shadow") == []
    assert svc.capital("baseline") == pytest.approx(100_000.0 + pnl)
    assert svc.capital() == pytest.approx(100_000.0)
    assert any("[BASELINE] CLOSED b1-BL" in m for m in notifier.sent)


async def test_the_eod_summary_compares_the_books(
    tmp_path,
    spreads_db,  # noqa: F811
) -> None:
    clock = [T1610]
    svc, _, notifier = make_books(tmp_path, clock)
    await svc.tick()
    (eod,) = [m for m in notifier.sent if "trade(s)" in m]
    assert "Claude +$0.00 vs baseline +$0.00 today" in eod
