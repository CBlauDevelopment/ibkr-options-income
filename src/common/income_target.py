"""The monthly income target: stored form, fallback and arithmetic (web, 2026-10-15).

Pure and storage-free, so the API (which reads ``system_settings`` through its own read-only
session) and ``src.storage.system_settings`` (which the drain writes through) share one reading of
the stored JSON. Display only: nothing in the trading path imports this.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import ValidationError

from src.common.schemas import IncomeTarget

# The system_settings key the drained ``set_income_target`` command writes.
INCOME_TARGET_KEY = "income_target"

# Where the answer came from: the operator's web setting, the legacy
# ``web.monthly_income_target_pct`` config value, or nowhere.
TargetSource = Literal["web", "config", "none"]


def dump_income_target(target: IncomeTarget) -> str:
    return json.dumps(target.model_dump(exclude_none=True), sort_keys=True)


def parse_income_target(raw: str | None) -> IncomeTarget | None:
    """The stored target, or None for a missing or unreadable row (never raises)."""
    if not raw:
        return None
    try:
        return IncomeTarget.model_validate(json.loads(raw))
    except (ValueError, TypeError, ValidationError):
        return None


def resolve_income_target(
    stored: str | None, config_pct: float | None
) -> tuple[IncomeTarget, TargetSource]:
    """The target in force. A web row wins, including an explicit ``off`` (the operator
    cleared it on purpose); with no row, the legacy config percentage still applies."""
    target = parse_income_target(stored)
    if target is not None:
        return target, "web"
    if config_pct is not None:
        return IncomeTarget(mode="pct_of_account", pct=config_pct), "config"
    return IncomeTarget(mode="off"), "none"


def target_value(target: IncomeTarget, month_start_value: float | None) -> float | None:
    """The dollar target for a month, or None when it cannot be worked out - never 0.0."""
    if target.mode == "fixed":
        return target.amount
    if target.mode == "pct_of_amount":
        return target.base * target.pct / 100 if target.base and target.pct else None
    if target.mode == "pct_of_account":
        if month_start_value is None or month_start_value <= 0 or target.pct is None:
            return None
        return month_start_value * target.pct / 100
    return None
