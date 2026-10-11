from __future__ import annotations

import pytest

from src.spreads_ai.parse import parse_day_plan, parse_pick


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ('{"choice": "B", "reason": "wall buffer"}', ("B", "wall buffer")),
        ('{"choice": "b", "reason": "x"}', ("B", "x")),
        ('```json\n{"choice": "C", "reason": "x"}\n```', ("C", "x")),
        ('Here you go: {"choice": "SKIP", "reason": "trend day"}', ("skip", "trend day")),
        ('{"choice": "A", "reason": "line one\\nline two"}', ("A", "line one line two")),
    ],
)
def test_accepts_a_letter_or_skip(text, want) -> None:
    assert parse_pick(text) == want


@pytest.mark.parametrize(
    "text",
    [
        '{"choice": "B.", "reason": "x"}',
        '{"choice": "Option B", "reason": "x"}',
        '{"choice": 2, "reason": "x"}',
        '{"reason": "x"}',
        "B",
        "",
        "[1, 2]",
    ],
)
def test_rejects_anything_else(text) -> None:
    assert parse_pick(text) is None


def test_day_plan_parses_and_rejects_an_unknown_bias() -> None:
    plan = parse_day_plan(
        '{"bias": "bearish", "risk_flags": ["CPI tomorrow"], "skip_conditions": ["spot < 655"],'
        ' "preferred_distance": ">=1.2x EM", "summary": "Weak tape."}'
    )
    assert plan is not None and plan.bias == "bearish" and plan.skip_conditions == ["spot < 655"]
    assert parse_day_plan('{"bias": "sideways"}') is None
    assert parse_day_plan("no json here") is None
