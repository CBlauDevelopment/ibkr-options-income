from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from src.claude.cli import CliResult
from src.common.config import get_config
from src.common.schemas import (
    GexLevels,
    SpreadBriefRequest,
    SpreadCandidate,
    SpreadExitRules,
    SpreadMarketSnapshot,
    SpreadMenuItem,
    SpreadPickRequest,
    SpreadTapeStats,
)
from src.spreads_ai.picker import ClaudePicker

NOW = datetime(2026, 10, 7, 15, 5, tzinfo=UTC)
LEVELS = GexLevels(as_of=NOW, spot=663.05, net_gex=1e9, regime="positive", expected_move=6.7)
EXITS = SpreadExitRules(
    profit_take_pct=50,
    stop_debit_multiple=2,
    close_on_short_strike_touch=True,
    max_hold_minutes=150,
    force_close="15:45",
)
CAND = SpreadCandidate(
    spread_id="x",
    side="put",
    expiry=date(2026, 10, 7),
    short_strike=656,
    long_strike=651,
    width=5,
    credit_mid=0.42,
    credit_natural=0.38,
    short_delta=-0.14,
    spot=663.05,
    quote_time=NOW,
)
ITEM = SpreadMenuItem(
    letter="A",
    position="baseline",
    candidate=CAND,
    contracts=1,
    credit_after_costs=0.31,
    cost_pct_of_credit=0.25,
    max_loss_per_contract_usd=458,
    dist_spot_pts=7.05,
    dist_em_multiple=1.05,
    beyond_wall_pts=None,
    dist_flip_pts=None,
    be_full_loss=0.94,
    be_nominal_exits=0.83,
)
PICK_REQ = SpreadPickRequest(
    now=NOW,
    levels=LEVELS,
    tape=SpreadTapeStats(),
    exits=EXITS,
    sides=["put"],
    menu=[ITEM],
    round_trip_cost_per_share=0.106,
)
BRIEF_REQ = SpreadBriefRequest(now=NOW, levels=LEVELS, tape=SpreadTapeStats(), exits=EXITS)


def picker(reply: CliResult, calls: list | None = None, snapshot=None) -> ClaudePicker:
    async def run(prompt: str, **kw):
        if calls is not None:
            calls.append((prompt, kw))
        return reply

    return ClaudePicker(
        get_config().spreads,
        cli_command="claude",
        disallowed_tools="Bash",
        workdir=Path("/tmp/x"),
        run=run,
        snapshot=snapshot or (lambda now, **kw: SpreadMarketSnapshot(vix=18.0)),
    )


async def test_a_clean_pick_uses_the_pick_model_and_returns_the_letter() -> None:
    calls: list = []
    p = picker(CliResult('{"choice": "a", "reason": "fine"}', None, 1600, 0.02, "{}"), calls)
    pick = await p.pick(PICK_REQ)
    assert (pick.choice, pick.reason, pick.fallback_reason) == ("A", "fine", None)
    assert pick.market.vix == 18.0 and pick.call.latency_ms == 1600 and pick.call.cost_usd == 0.02
    ((prompt, kw),) = calls
    assert (
        kw["model"] == "claude-opus-5-5"
        and kw["effort"] == "high"
        and kw["timeout_seconds"] == 45.0
    )
    assert "A [baseline]" in prompt and pick.call.prompt_text == prompt


async def test_cli_failures_and_garbage_become_fallbacks() -> None:
    assert (
        await picker(CliResult(None, "timeout", 45000)).pick(PICK_REQ)
    ).fallback_reason == "timeout"
    assert (
        await picker(CliResult(None, "cli_error", 10)).pick(PICK_REQ)
    ).fallback_reason == "cli_error"
    bad = await picker(CliResult("B.", None, 10)).pick(PICK_REQ)
    assert (bad.choice, bad.fallback_reason) == ("skip", "unparseable")


async def test_the_picker_never_raises() -> None:
    def boom(now, **kw):
        raise RuntimeError("snapshot exploded")

    pick = await picker(CliResult('{"choice":"A","reason":"x"}', None, 1), snapshot=boom).pick(
        PICK_REQ
    )
    assert pick.fallback_reason is None and pick.market.unavailable == ["snapshot"]


async def test_the_brief_parses_a_plan_or_reports_why_not() -> None:
    ok = await picker(CliResult('{"bias": "neutral", "summary": "calm"}', None, 20000)).brief(
        BRIEF_REQ
    )
    assert ok.plan is not None and ok.plan.bias == "neutral" and ok.call.effort == "high"
    bad = await picker(CliResult("nope", None, 20000)).brief(BRIEF_REQ)
    assert bad.plan is None and bad.call.error == "unparseable"


def scripted(replies: list[CliResult], calls: list, **ai_overrides) -> ClaudePicker:
    """A picker whose runner answers each call with the next scripted reply."""
    queue = list(replies)

    async def run(prompt: str, **kw):
        calls.append(kw)
        return queue.pop(0)

    cfg = get_config().spreads
    cfg = cfg.model_copy(update={"ai": cfg.ai.model_copy(update=ai_overrides)})
    return ClaudePicker(
        cfg,
        cli_command="claude",
        disallowed_tools="Bash",
        workdir=Path("/tmp/x"),
        run=run,
        snapshot=lambda now, **kw: SpreadMarketSnapshot(),
    )


async def test_a_cli_error_retries_once_on_the_fallback_model_inside_the_same_timeout() -> None:
    calls: list = []
    p = scripted(
        [
            CliResult(None, "cli_error", 800, 0.01),
            CliResult('{"choice": "A", "reason": "ok"}', None, 9000, 0.03, "{}"),
        ],
        calls,
    )
    pick = await p.pick(PICK_REQ)
    assert (pick.choice, pick.fallback_reason) == ("A", None)
    assert [c["model"] for c in calls] == ["claude-opus-5-5", "claude-sonnet-5-5"]
    assert calls[1]["effort"] == "high" and calls[1]["timeout_seconds"] == 45.0 - 0.8
    assert (pick.call.model, pick.call.effort, pick.call.latency_ms) == (
        "claude-sonnet-5-5",
        "high",
        9800,
    )
    assert pick.call.cost_usd == 0.04


async def test_the_fallback_failing_too_is_still_a_cli_error_fallback() -> None:
    calls: list = []
    p = scripted([CliResult(None, "cli_error", 500), CliResult(None, "cli_error", 400)], calls)
    pick = await p.pick(PICK_REQ)
    assert (pick.choice, pick.fallback_reason, pick.call.model) == (
        "skip",
        "cli_error",
        "claude-sonnet-5-5",
    )
    assert len(calls) == 2 and pick.call.cost_usd is None


async def test_no_retry_on_other_errors_when_disabled_or_when_time_is_short() -> None:
    for first, overrides in [
        (CliResult(None, "timeout", 45000), {}),
        (CliResult(None, "cli_missing", 5), {}),
        (CliResult(None, "bad_envelope", 900), {}),
        (CliResult(None, "cli_error", 500), {"fallback_model": ""}),
        (CliResult(None, "cli_error", 500), {"fallback_model": "claude-opus-5-5"}),
        (CliResult(None, "cli_error", 40_500), {}),  # 4.5 s left < 5 s
    ]:
        calls: list = []
        pick = await scripted([first], calls, **overrides).pick(PICK_REQ)
        assert len(calls) == 1, (first, overrides)
        assert pick.fallback_reason == first.error and pick.call.model == "claude-opus-5-5"


async def test_the_brief_falls_back_too() -> None:
    calls: list = []
    p = scripted(
        [
            CliResult(None, "cli_error", 1000),
            CliResult('{"bias": "neutral", "summary": "calm"}', None, 20000),
        ],
        calls,
    )
    res = await p.brief(BRIEF_REQ)
    assert res.plan is not None and res.call.model == "claude-sonnet-5-5"
    assert calls[1]["timeout_seconds"] == 120.0 - 1.0
