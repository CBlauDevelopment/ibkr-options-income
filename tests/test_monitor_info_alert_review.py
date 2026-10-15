"""Info alerts (delta drift, loss multiple, DTE, assignment risk...) carry no buttons: the roll
decision card is the actionable one. A strike breach used to fire both, and each got its own
`claude -p` call (2026-10-15: 24 billed roll reviews in a week, two per breach). With
`claude.review_info_alerts` off (the default) the info alert is the deterministic facts only."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.schemas import RollAlert
from src.notify.formatters import format_assignment_alert, format_roll_alert
from tests.test_monitor import _make_quote, _make_short_call


@pytest.fixture(autouse=True)
def _alert_window_always_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests exercise what an alert contains, not the RTH gate (tests/test_monitor_roll_eval.py)."""
    import src.monitor.intraday as intraday

    monkeypatch.setattr(intraday, "_alert_window_open", lambda cfg, now=None: True)


def _cfg(*, enabled: bool = True, review_info_alerts: bool = False) -> MagicMock:
    cfg = MagicMock()
    cfg.monitor.alert_cooldown_minutes = 30
    cfg.claude.enabled = enabled
    cfg.claude.review_info_alerts = review_info_alerts
    return cfg


def _alert(trigger: str = "delta_drift") -> RollAlert:
    pos = _make_short_call()
    return RollAlert(
        position_symbol=pos.symbol,
        underlying=pos.underlying,
        trigger=trigger,
        detail="delta=0.48 > ceiling=0.45",
        current_delta=0.48,
        dte=30,
    )


async def _fire(cfg: MagicMock, alert: RollAlert, review_mock: MagicMock) -> AsyncMock:
    from src.monitor.intraday import fire_alerts

    bot = AsyncMock()
    with (
        patch("src.monitor.intraday._select_fresh", side_effect=lambda a, **_k: a),
        patch("src.monitor.intraday._persist_alert") as persist,
        patch("src.monitor.intraday.review_roll", review_mock),
        ThreadPoolExecutor(max_workers=1) as ex,
    ):
        await fire_alerts([alert], _make_short_call(), _make_quote(), bot, "chat", cfg, ex)
    bot.persist = persist  # type: ignore[attr-defined]
    return bot


@pytest.mark.asyncio
async def test_info_alert_makes_no_claude_call_by_default() -> None:
    review = MagicMock(return_value=None)
    bot = await _fire(_cfg(), _alert(), review)
    review.assert_not_called()
    bot.send_message.assert_called_once()  # the alert itself still goes out
    bot.persist.assert_called_once()  # ...and is still recorded (its cooldown depends on it)


@pytest.mark.asyncio
async def test_info_alert_reviews_when_the_switch_is_on() -> None:
    review = MagicMock(return_value=None)
    await _fire(_cfg(review_info_alerts=True), _alert(), review)
    review.assert_called_once()


@pytest.mark.asyncio
async def test_info_alert_text_does_not_claim_the_review_failed() -> None:
    bot = await _fire(_cfg(), _alert(), MagicMock())
    text = bot.send_message.call_args.kwargs["text"]
    assert "unavailable" not in text and "Claude" not in text


@pytest.mark.asyncio
async def test_assignment_risk_alert_is_also_facts_only_by_default() -> None:
    review = MagicMock(return_value=None)
    bot = await _fire(_cfg(), _alert("assignment_risk"), review)
    review.assert_not_called()
    text = bot.send_message.call_args.kwargs["text"]
    assert "Assignment Risk" in text and "unavailable" not in text


def test_formatters_keep_the_unavailable_line_by_default() -> None:
    pos, quote, alert = _make_short_call(), _make_quote(), _alert()
    assert "unavailable" in format_roll_alert(pos, quote, [alert], None)
    assert "unavailable" in format_assignment_alert(pos, quote, [alert], None)


def test_formatters_omit_the_claude_section_when_skipped_on_purpose() -> None:
    pos, quote, alert = _make_short_call(), _make_quote(), _alert()
    for text in (
        format_roll_alert(pos, quote, [alert], None, review_skipped=True),
        format_assignment_alert(pos, quote, [alert], None, review_skipped=True),
    ):
        assert "unavailable" not in text and "Claude" not in text
