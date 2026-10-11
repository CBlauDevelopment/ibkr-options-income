"""Strict parsing of Claude's replies. Shape only: whether a letter is on the menu is the
spreads service's check, so an off-menu letter is caught where it matters."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from src.common.schemas import SpreadDayPlan

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def clean(text: str, limit: int = 500) -> str:
    """One line, bounded: model text and headlines never carry newlines into a card or prompt."""
    return " ".join(str(text).split())[:limit]


def extract_json(text: str) -> dict[str, Any] | None:
    t = _FENCE.sub("", (text or "").strip())
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(t[start : end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def parse_pick(text: str) -> tuple[str, str] | None:
    obj = extract_json(text)
    if obj is None:
        return None
    choice, reason = obj.get("choice"), obj.get("reason", "")
    if not isinstance(choice, str) or not isinstance(reason, str):
        return None
    c = choice.strip()
    if c.lower() == "skip":
        c = "skip"
    elif len(c) == 1 and c.isalpha():
        c = c.upper()
    else:
        return None
    return c, clean(reason)


def parse_day_plan(text: str) -> SpreadDayPlan | None:
    obj = extract_json(text)
    if obj is None:
        return None

    def strings(key: str) -> list[str]:
        v = obj.get(key) or []
        return [clean(x, 200) for x in v if isinstance(x, str)] if isinstance(v, list) else []

    try:
        return SpreadDayPlan(
            bias=obj.get("bias"),  # type: ignore[arg-type]  # validated by the Literal
            risk_flags=strings("risk_flags"),
            skip_conditions=strings("skip_conditions"),
            preferred_distance=clean(obj.get("preferred_distance") or "", 200),
            summary=clean(obj.get("summary") or "", 600),
        )
    except ValidationError:
        return None
