"""The reviewer reviews the system's proposal, not a guess (roll redesign Task 12)."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.common.schemas import (
    OptionQuote,
    OptionRight,
    PositionSnapshot,
    RollAlert,
    RollDecision,
    RollReview,
)

_EXP = date.today() + timedelta(days=5)


def _pos() -> PositionSnapshot:
    return PositionSnapshot(
        symbol="GOOGL x",
        sec_type="OPT",
        position=-1,
        avg_cost=1.0,
        right=OptionRight.PUT,
        strike=335.0,
        expiry=_EXP,
        underlying="GOOGL",
        con_id=3,
    )


def _quote() -> OptionQuote:
    return OptionQuote(
        underlying="GOOGL",
        right=OptionRight.PUT,
        strike=335.0,
        expiry=_EXP,
        bid=5.9,
        ask=6.1,
        delta=-0.62,
        underlying_price=329.0,
    )


def _alert() -> RollAlert:
    return RollAlert(
        position_symbol="GOOGL x", underlying="GOOGL", trigger="strike_breach", detail="breached"
    )


def test_the_prompt_carries_the_system_proposal() -> None:
    from src.claude.prompts.roll import build_roll_prompt

    text = build_roll_prompt(_alert(), _pos(), _quote(), proposal="ROLL 335P → 330P for +$0.06")
    assert "=== SYSTEM PROPOSAL ===" in text and "ROLL 335P → 330P for +$0.06" in text
    assert "may not change" in text
    assert "SYSTEM PROPOSAL" not in build_roll_prompt(_alert(), _pos(), _quote())


def test_the_cli_runner_forwards_the_proposal() -> None:
    from src.claude import runner

    with (
        patch.object(runner, "get_config") as cfg,
        patch.object(runner, "_run_cli", return_value=None) as run,
    ):
        cfg.return_value.claude.backend = "cli"
        cfg.return_value.claude.enabled = True
        runner.review_roll(_alert(), _pos(), _quote(), proposal="ROLL it")
    assert "ROLL it" in run.call_args.args[0]


def test_the_ollama_runner_forwards_the_proposal() -> None:
    from src.claude import ollama_runner

    with (
        patch.object(ollama_runner, "get_config") as cfg,
        patch.object(ollama_runner, "_generate", return_value=None) as gen,
        patch.object(ollama_runner, "_circuit_open", False),
        patch.object(ollama_runner, "_record_failure"),
    ):
        cfg.return_value.claude.enabled = True
        ollama_runner.review_roll(_alert(), _pos(), _quote(), proposal="ROLL it")
    assert "ROLL it" in gen.call_args.args[0]


async def test_the_decision_card_is_reviewed_with_the_proposal(db) -> None:
    from src.common.config import get_config
    from src.monitor import intraday

    cfg = get_config().model_copy(deep=True)
    cfg.claude.enabled = True
    decision = RollDecision(
        action="assign", reason="net_below_floor", detail="Let it assign at $335."
    )
    review = RollReview(
        position_symbol="GOOGL x",
        recommendation="hold",
        roll_target="",
        rationale="Agree.",
        risks="Gap risk.",
        confidence=0.7,
    )
    seen: dict = {}

    def _review(alert, pos, quote, *, proposal=None):  # noqa: ANN001
        seen["proposal"] = proposal
        return review

    bot = AsyncMock()
    with (
        patch.object(intraday, "_alert_window_open", return_value=True),
        patch.object(intraday, "is_leveraged_etf", return_value=False),
        patch.object(intraday, "review_roll", side_effect=_review),
        patch(
            "src.execution.roll_pipeline.evaluate_roll",
            new=AsyncMock(return_value=(decision, None)),
        ),
    ):
        await intraday.handle_roll_trigger(
            _pos(),
            _quote(),
            ib=MagicMock(),
            bot=bot,
            chat_id="1",
            cfg=cfg,
            fund=None,
            state=intraday.RollEvalState(),
            now=0.0,
        )
    assert seen["proposal"] == "Let it assign at $335."
    assert "Agree" in bot.send_message.await_args.kwargs["text"]
