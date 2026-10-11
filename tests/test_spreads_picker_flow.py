from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from src.common.schemas import (
    SpreadBriefResult,
    SpreadDayPlan,
    SpreadLlmCall,
    SpreadMarketSnapshot,
    SpreadPick,
)
from src.spreads.executor import SpreadExecutor
from tests.test_spreads_service import (  # noqa: F401 — spreads_db is a fixture
    CFG,
    MOVE,
    ONE_A_DAY,
    T0931,
    T0945,
    T1005,
    T1100,
    FakeBroker,
    FakeNotifier,
    _flush,
    o,
    spreads_db,
)

# Claude's menu on the FakeBroker day: A = 680/675 (inside), B = 679/674 (the baseline pick),
# C = 678/673 (outer). The call side has no strike beyond its boundary.
EXTRA = [
    o(680, "P", 1.00, 1.06, delta=-0.14),
    o(675, "P", 0.25, 0.29),
    o(678, "P", 0.70, 0.76, delta=-0.11),
    o(673, "P", 0.15, 0.19),
]


def ai(cfg, **ai_kw):
    return cfg.model_copy(
        update={
            "ai": cfg.ai.model_copy(update={"enabled": True, **ai_kw}),
            "selection": cfg.selection.model_copy(update={"menu_size": 4}),
        }
    )


AI = ai(ONE_A_DAY)


class MenuBroker(FakeBroker):
    def __init__(self, clock):
        super().__init__(clock)
        for q in EXTRA:
            self.leg_quotes[(float(q.strike), q.right)] = q

    async def fetch_chain(self, **kw):
        snap = await super().fetch_chain(**kw)
        if kw["symbol"] == "SPY":
            snap = snap.model_copy(update={"options": [*snap.options, *EXTRA]})
        return snap


NEUTRAL = SpreadDayPlan(bias="neutral")


class FakePicker:
    def __init__(self, choice="C", *, fallback=None, delay=0.0, plan=NEUTRAL):
        self.choice, self.fallback, self.delay, self.plan = choice, fallback, delay, plan
        self.briefs: list = []
        self.picks: list = []

    async def brief(self, req):
        self.briefs.append(req)
        return SpreadBriefResult(
            plan=self.plan,
            market=SpreadMarketSnapshot(),
            call=SpreadLlmCall(model="fake", effort="", prompt_text="B"),
        )

    async def pick(self, req):
        self.picks.append(req)
        if self.delay:
            await asyncio.sleep(self.delay)
        return SpreadPick(
            choice=self.choice,
            reason="because",
            fallback_reason=self.fallback,
            market=SpreadMarketSnapshot(vix=17.0),
            call=SpreadLlmCall(model="fake", effort="", prompt_text="P"),
        )


async def settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


def make(tmp_path, clock, cfg=AI, picker=None, broker=None):
    from src.spreads.service import SpreadsService

    broker = broker or MenuBroker(clock)
    notifier = FakeNotifier()
    picker = picker or FakePicker()
    ex = SpreadExecutor(None, broker, cfg, now=lambda: clock[0])
    svc = SpreadsService(
        broker, ex, notifier, cfg, halt_path=tmp_path / "halt", now=lambda: clock[0], picker=picker
    )
    return svc, broker, notifier, picker


async def _decide(svc, clock):
    """09:45 map + brief; 10:05 menu (baseline opens); 10:05:30 the pick resolves."""
    clock[0] = T0945
    await svc.tick()
    await settle()
    clock[0] = T1005
    await svc.tick()
    await settle()
    clock[0] = T1005 + timedelta(seconds=30)
    await svc.tick()


async def test_claude_takes_an_outer_strike_and_the_baseline_takes_its_own(
    tmp_path,
    spreads_db,  # noqa: F811
) -> None:
    clock = [T0945]
    svc, _, notifier, picker = make(tmp_path, clock)
    await _decide(svc, clock)
    (main,) = spreads_db.open_positions("shadow")
    (base,) = spreads_db.open_positions("baseline")
    assert (main.short_strike, base.short_strike) == (678.0, 679.0)
    assert base.spread_id.endswith("-BL") and base.episode_key == main.episode_key
    (rec,) = spreads_db.picks()
    assert main.pick_id == rec.pick_id
    assert [(i.letter, i.position) for i in rec.menu] == [
        ("A", "inside"),
        ("B", "baseline"),
        ("C", "outer"),
    ]
    assert (rec.choice, rec.executed_letter, rec.filled, rec.fallback_reason) == (
        "C",
        "C",
        True,
        None,
    )
    assert rec.market.vix == 17.0 and rec.snapshot.plan_bias == "neutral"
    assert picker.picks[0].plan == SpreadDayPlan(bias="neutral")  # the brief fed the pick
    assert any("DAY PLAN" in m for m in notifier.sent)
    assert any(
        "Claude chose C (outer)" in m and "baseline: sold 679/674" in m for m in notifier.sent
    )


async def test_a_skip_trades_nothing_but_the_baseline_still_trades(tmp_path, spreads_db) -> None:  # noqa: F811
    clock = [T0945]
    svc, _, notifier, _ = make(tmp_path, clock, picker=FakePicker("skip"))
    await _decide(svc, clock)
    assert (
        spreads_db.open_positions("shadow") == []
        and len(spreads_db.open_positions("baseline")) == 1
    )
    (rec,) = spreads_db.picks()
    assert (rec.choice, rec.executed_letter) == ("skip", None)
    assert any("Claude SKIPPED" in m for m in notifier.sent)


async def test_an_off_menu_letter_falls_back_to_the_baseline_item(tmp_path, spreads_db) -> None:  # noqa: F811
    clock = [T0945]
    svc, _, notifier, _ = make(tmp_path, clock, picker=FakePicker("Z"))
    await _decide(svc, clock)
    (main,) = spreads_db.open_positions("shadow")
    assert main.short_strike == 679.0
    (rec,) = spreads_db.picks()
    assert (rec.fallback_reason, rec.executed_letter) == ("off_menu", "B")
    assert any("picker failed (off_menu)" in m for m in notifier.sent)


async def test_a_picker_failure_falls_back_to_the_baseline_item(tmp_path, spreads_db) -> None:  # noqa: F811
    clock = [T0945]
    svc, _, _, _ = make(tmp_path, clock, picker=FakePicker("skip", fallback="unparseable"))
    await _decide(svc, clock)
    assert spreads_db.open_positions("shadow")[0].short_strike == 679.0
    assert spreads_db.picks()[0].fallback_reason == "unparseable"


async def test_a_hung_pick_times_out_without_holding_up_exits(tmp_path, spreads_db) -> None:  # noqa: F811
    clock = [T0945]
    svc, broker, _, _ = make(tmp_path, clock, picker=FakePicker(delay=3600))
    clock[0] = T0945
    await svc.tick()
    await settle()
    clock[0] = T1005
    await svc.tick()  # baseline opens at 679/674; the pick hangs
    assert svc._pending is not None
    broker.leg_quotes[(679.0, "P")] = o(679, "P", 0.30, 0.34)
    broker.leg_quotes[(674.0, "P")] = o(674, "P", 0.03, 0.05)
    clock[0] = T1005 + timedelta(seconds=40)
    await svc.tick()  # still waiting — but the baseline's profit take runs
    assert spreads_db.closed_results("baseline")[0][1] == "profit_take" and svc._pending is not None
    clock[0] = T1005 + timedelta(seconds=80)  # past 45 s + 30 s grace
    await svc.tick()
    assert svc._pending is None
    (rec,) = spreads_db.picks()
    assert (rec.fallback_reason, rec.executed_letter) == ("timeout", "B")


async def test_a_pick_resolving_after_entry_end_is_regated_and_not_sent(
    tmp_path,
    spreads_db,  # noqa: F811
) -> None:
    clock = [T0945]
    svc, _, _, _ = make(tmp_path, clock)
    await svc.tick()
    await settle()
    clock[0] = datetime(2026, 10, 7, 17, 29, 30, tzinfo=UTC)  # 13:29:30 ET, last check before 13:30
    await svc.tick()
    await settle()
    clock[0] = datetime(2026, 10, 7, 17, 30, 20, tzinfo=UTC)  # 13:30:20 ET
    await svc.tick()
    (rec,) = spreads_db.picks()
    assert rec.send_rejected and "outside_entry_window" in rec.send_reasons and not rec.filled
    assert spreads_db.open_positions("shadow") == []


async def test_a_fallback_without_a_baseline_item_trades_nothing(tmp_path, spreads_db) -> None:  # noqa: F811
    clock = [T0945]
    broker = MenuBroker(clock)
    wide = o(674, "P", 0.10, 0.30)  # 100% leg spread: the gate drops the baseline item B
    broker.leg_quotes[(674.0, "P")] = wide

    async def fetch(**kw):
        snap = await MenuBroker.fetch_chain(broker, **kw)
        if kw["symbol"] == "SPY":
            snap = snap.model_copy(
                update={
                    "options": [
                        wide if (x.strike, x.right) == (674, "P") else x for x in snap.options
                    ]
                }
            )
        return snap

    broker.fetch_chain = fetch  # type: ignore[method-assign]
    svc, _, _, _ = make(
        tmp_path, clock, picker=FakePicker("skip", fallback="timeout"), broker=broker
    )
    await _decide(svc, clock)
    (rec,) = spreads_db.picks()
    assert [i.position for i in rec.menu] == ["inside", "outer"]
    assert rec.executed_letter is None and rec.send_reasons == ["no_baseline_item"]
    assert spreads_db.open_positions("shadow") == [] and spreads_db.open_positions("baseline") == []


async def test_the_daily_cap_stops_main_entries_and_alerts_once(tmp_path, spreads_db) -> None:  # noqa: F811
    cfg = ai(CFG, max_pick_calls_per_day=1)  # CFG: every check is its own episode, 2 trades/day
    clock = [T0945]
    svc, _, notifier, picker = make(tmp_path, clock, cfg=cfg, picker=FakePicker("skip"))
    await _decide(svc, clock)
    clock[0] = T1100
    await svc.tick()
    await settle()
    assert len(picker.picks) == 1
    assert sum("pick calls used today" in m for m in notifier.sent) == 1
    assert len(spreads_db.open_positions("baseline")) == 2  # the baseline is not capped


async def test_a_skip_stands_for_its_episode_even_across_a_restart(tmp_path, spreads_db) -> None:  # noqa: F811
    cfg = ai(MOVE)
    clock = [T0931]
    svc, broker, _, picker = make(tmp_path, clock, cfg=cfg, picker=FakePicker("skip"))
    await _flush(svc, broker, clock)  # low 689.80 at 09:36, holding
    clock[0] = datetime(2026, 10, 7, 13, 47, tzinfo=UTC)  # armed: stalled 11 min
    await svc.tick()
    await settle()
    clock[0] = datetime(2026, 10, 7, 13, 47, 30, tzinfo=UTC)
    await svc.tick()
    assert len(picker.picks) == 1 and spreads_db.picks()[0].choice == "skip"
    clock[0] = datetime(2026, 10, 7, 13, 53, tzinfo=UTC)  # next check, same low: no new call
    await svc.tick()
    await settle()
    assert len(picker.picks) == 1
    # Restart: a fresh service rebuilds the tape from the session stats, same 689.80 low.
    svc2, _, _, picker2 = make(tmp_path, clock, cfg=cfg, picker=FakePicker("C"), broker=broker)
    for minute in (54, 59, 65):
        clock[0] = datetime(2026, 10, 7, 13, 0, tzinfo=UTC) + timedelta(minutes=minute)
        await svc2.tick()
        await settle()
    assert picker2.picks == []  # the episode was already decided before the restart


async def test_the_brief_runs_once_a_day(tmp_path, spreads_db) -> None:  # noqa: F811
    clock = [T0945]
    svc, _, _, picker = make(tmp_path, clock)
    await svc.tick()
    await settle()
    clock[0] = T0945 + timedelta(minutes=61)  # map refresh
    await svc.tick()
    await settle()
    assert len(picker.briefs) == 1 and spreads_db.day_plan(T0945.date()) == SpreadDayPlan(
        bias="neutral"
    )


async def test_a_halt_during_the_pick_records_it_without_trading(tmp_path, spreads_db) -> None:  # noqa: F811
    clock = [T0945]
    svc, _, _, _ = make(tmp_path, clock)
    await svc.tick()
    await settle()
    clock[0] = T1005
    await svc.tick()
    await settle()
    (tmp_path / "halt").touch()
    clock[0] = T1005 + timedelta(seconds=30)
    await svc.tick()
    (rec,) = spreads_db.picks()
    assert rec.send_reasons == ["halted"] and spreads_db.open_positions("shadow") == []
