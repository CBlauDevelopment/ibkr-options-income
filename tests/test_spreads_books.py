from __future__ import annotations

from datetime import timedelta

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
    T1005,
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
    assert any("Closed</b> <code>b1-BL</code> <i>(baseline" in m for m in notifier.sent)


async def test_the_eod_summary_compares_the_books(
    tmp_path,
    spreads_db,  # noqa: F811
) -> None:
    clock = [T1610]
    svc, _, notifier = make_books(tmp_path, clock)
    await svc.tick()
    (eod,) = [m for m in notifier.sent if "📊" in m]
    assert "Claude +$0.00 vs baseline +$0.00 today" in eod


# ------------------------------------------------ paper mode: the baseline never reaches IBKR


class RecordingMainExecutor:
    """The paper main book's executor: records what it is asked to open, fills at the mid."""

    def __init__(self) -> None:
        self.opens: list[tuple[str, int, bool]] = []
        self.closes: list[str] = []

    async def open(self, c, contracts, recheck):
        from src.spreads.executor import FillResult

        verdict = recheck(c)  # the executor's own re-gate, as SpreadExecutor's paper path runs it
        self.opens.append((c.spread_id, contracts, verdict.approved))
        return FillResult(contracts, c.credit_mid, 2.6, perm_id=7, order_ref=f"CS:{c.spread_id}")

    async def close(self, pos, short_q, long_q, *, urgent):
        self.closes.append(pos.spread_id)
        raise AssertionError("the main book has nothing to close in this test")


async def test_in_paper_mode_only_claudes_choice_reaches_the_main_executor(
    tmp_path,
    spreads_db,  # noqa: F811
) -> None:
    from src.spreads.service import SpreadsService
    from tests.test_spreads_picker_flow import AI, FakePicker, MenuBroker, settle

    class PaperMenuBroker(MenuBroker):
        def working_refs(self):
            return set()

    paper = AI.model_copy(
        update={
            "mode": "paper",
            "risk": AI.risk.model_copy(update={"max_trades_per_day": 2}),
        }
    )
    clock = [T0945]
    broker = PaperMenuBroker(clock)
    main = RecordingMainExecutor()
    svc = SpreadsService(
        broker,
        main,
        FakeNotifier(),
        paper,
        halt_path=tmp_path / "halt",
        now=lambda: clock[0],
        picker=FakePicker("C"),
    )
    # The baseline book is simulated whatever the main book's mode: it holds no IBKR handle,
    # so any order it tried to place would raise instead of reaching the broker.
    assert svc.baseline_executor is not None and svc.baseline_executor.cfg.mode == "shadow"  # type: ignore[attr-defined]
    assert svc.baseline_executor.ib is None  # type: ignore[attr-defined]
    # A baseline spread already on the book when the process starts: IBKR knows nothing of it.
    spreads_db.open_position(
        cand("seed-BL"),
        mode="baseline",
        contracts=1,
        credit=0.57,
        commission=1.3,
        now=T0945,
        perm_id=None,
    )
    await svc.start()
    assert svc.entries_blocked is None
    await svc.tick()
    await settle()
    clock[0] = T1005
    await svc.tick()  # the baseline opens on the shadow executor
    await settle()
    (base,) = [p for p in spreads_db.open_positions("baseline") if p.spread_id != "seed-BL"]
    assert base.spread_id.endswith("-BL") and svc.entries_blocked is None
    assert main.opens == []  # nothing for the baseline went to the main executor
    clock[0] = T1005 + timedelta(seconds=30)
    await svc.tick()  # Claude's choice goes through the main executor
    assert [(sid.endswith("-BL"), approved) for sid, _, approved in main.opens] == [(False, True)]
    (pos,) = spreads_db.open_positions("paper")
    assert pos.short_strike == 678.0 and pos.mode == "paper"
    # The baseline row has no broker legs and never will: reconcile must not see it, so it
    # blocks nothing — only the main book's own unmatched position does (the broker shows none).
    assert "-BL" not in (svc.entries_blocked or "")
    clock[0] = T1005 + timedelta(minutes=1)
    await svc.tick()
    assert svc.entries_blocked and str(pos.short_con_id) in svc.entries_blocked
    assert str(base.short_con_id) not in svc.entries_blocked
    # A profit take on the baseline closes on the shadow executor; the main one is untouched.
    broker.leg_quotes[(679.0, "P")] = o(679, "P", 0.30, 0.34)
    broker.leg_quotes[(674.0, "P")] = o(674, "P", 0.03, 0.05)
    clock[0] = T1100
    await svc.tick()
    assert [r for _, r, _ in spreads_db.closed_results("baseline")] == ["profit_take"] * 2
    assert main.closes == []


class ExplodingCloseExecutor:
    async def open(self, c, contracts, recheck):
        raise AssertionError("no entries in this test")

    async def close(self, pos, short_q, long_q, *, urgent):
        raise RuntimeError("the main book's close blew up")


async def test_a_main_book_failure_does_not_starve_the_baseline_exits(
    tmp_path,
    spreads_db,  # noqa: F811
) -> None:
    clock = [T0945]
    svc, broker, notifier = make_books(tmp_path, clock)
    await svc.tick()  # map
    for mode, sid in (("shadow", "m1"), ("baseline", "b1-BL")):
        spreads_db.open_position(
            cand(sid),
            mode=mode,
            contracts=1,
            credit=0.57,
            commission=1.3,
            now=T0945,
            perm_id=None,
        )
    svc.executor = ExplodingCloseExecutor()
    broker.leg_quotes = {
        (679.0, "P"): o(679, "P", 0.30, 0.34),
        (674.0, "P"): o(674, "P", 0.03, 0.05),
    }
    clock[0] = T1100
    await svc.tick()  # both books want a profit take; the main book's close raises
    ((sid, reason, _),) = spreads_db.closed_results("baseline")
    assert reason == "profit_take" and len(spreads_db.open_positions("shadow")) == 1
    assert (
        sum("the manage phase failed" in m for m in notifier.sent) == 1
    )  # the main key, as before
    assert not any("manage:baseline" in m for m in notifier.sent)
