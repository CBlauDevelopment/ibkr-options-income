"""The strategist prompt's "YOUR PRIOR RECOMMENDATIONS" block holds only the reviewed
candidates' own tickers. It used to carry the memory of every scanned symbol: in the AVGO review
of 2026-10-15 that was 47 rows over 18 other tickers (0 AVGO), 48% of the prompt, the same prose
sent again with every call."""

from __future__ import annotations

from datetime import date

from src.claude.prompts.strategist import build_prompt
from src.storage.models import ClaudeMemoryRow
from tests.test_claude import _make_account, _make_candidate


def _row(underlying: str, rationale: str = "x") -> ClaudeMemoryRow:
    return ClaudeMemoryRow(
        scan_date=date(2026, 10, 14),
        underlying=underlying,
        strategy_type="cash_secured_put",
        recommendation="sell",
        confidence=0.8,
        rationale=f"{rationale} {underlying}-only-text",
        outcome=None,
    )


def _history_block(prompt: str) -> str:
    if "=== YOUR PRIOR RECOMMENDATIONS" not in prompt:
        return ""
    block = prompt.split("=== YOUR PRIOR RECOMMENDATIONS", 1)[1]
    return block.split("--- Candidate 1 ---", 1)[0]


def test_history_keeps_only_the_candidates_own_ticker() -> None:
    prompt = build_prompt(
        [_make_candidate(underlying="AVGO")],
        _make_account(),
        history=[_row("AAPL"), _row("AVGO"), _row("MSFT")],
    )
    block = _history_block(prompt)
    assert "AVGO-only-text" in block
    assert "AAPL-only-text" not in block and "MSFT-only-text" not in block


def test_history_covers_every_candidate_ticker() -> None:
    prompt = build_prompt(
        [_make_candidate("a", underlying="AVGO"), _make_candidate("b", underlying="AMD")],
        _make_account(),
        history=[_row("AVGO"), _row("AMD"), _row("PLTR")],
    )
    block = _history_block(prompt)
    assert "AVGO-only-text" in block and "AMD-only-text" in block
    assert "PLTR-only-text" not in block


def test_no_history_block_when_nothing_matches_the_candidates() -> None:
    prompt = build_prompt(
        [_make_candidate(underlying="AVGO")], _make_account(), history=[_row("AAPL"), _row("MSFT")]
    )
    assert "PRIOR RECOMMENDATIONS" not in prompt
