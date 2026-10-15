"""``claude_cli_then_ollama``: the summary falls back to the local model when claude -p fails."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.common.config import ResearchSummaryCfg, get_config
from src.research.summary import chain
from src.research.summary.factory import get_summary_provider
from src.research.summary.protocol import Summary

SUMMARY = Summary(
    thesis="t",
    bull_points=[],
    bear_points=[],
    watch_items=[],
    caveats=[],
    model="m",
    data_as_of=datetime(2026, 10, 15, tzinfo=UTC),
)


def _provider(monkeypatch, cli_result):
    seen = []
    monkeypatch.setattr(
        chain.ClaudeCliSummaryProvider, "generate_with_error", lambda self, ctx: cli_result
    )
    monkeypatch.setattr(
        chain.OllamaSummaryProvider, "generate", lambda self, ctx: seen.append(1) or SUMMARY
    )
    return chain.ClaudeCliThenOllamaSummaryProvider(), seen


def test_a_claude_summary_never_touches_ollama(monkeypatch) -> None:
    p, seen = _provider(monkeypatch, (SUMMARY, None))
    assert p.generate(None) is SUMMARY and seen == []  # type: ignore[arg-type]


@pytest.mark.parametrize("error", ["cli_error", "cli_missing", "bad_envelope"])
def test_a_claude_failure_falls_back_to_ollama(monkeypatch, error) -> None:
    p, seen = _provider(monkeypatch, (None, error))
    assert p.generate(None) is SUMMARY and seen == [1]  # type: ignore[arg-type]


@pytest.mark.parametrize("error", ["timeout", "disabled"])
def test_a_timeout_or_disabled_claude_does_not_fall_back(monkeypatch, error) -> None:
    p, seen = _provider(monkeypatch, (None, error))
    assert p.generate(None) is None and seen == []  # type: ignore[arg-type]


def test_the_factory_and_validator_know_the_backend(monkeypatch) -> None:
    monkeypatch.setattr(get_config().research.summary, "backend", "claude_cli_then_ollama")
    get_summary_provider.cache_clear()
    try:
        assert isinstance(get_summary_provider(), chain.ClaudeCliThenOllamaSummaryProvider)
    finally:
        get_summary_provider.cache_clear()
    assert ResearchSummaryCfg(backend="claude_cli_then_ollama").backend == "claude_cli_then_ollama"
    with pytest.raises(ValueError):
        ResearchSummaryCfg(backend="nope")
