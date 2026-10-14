"""Response models for the read-only spreads routes (web overhaul Part 1, Task 8)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from src.api.models.common import Envelope


class SpreadPositionOut(Envelope):
    spread_id: str
    mode: str
    side: Literal["put", "call"]
    expiry: date
    short_strike: float
    long_strike: float
    width: float
    contracts_opened: int
    contracts: int  # still open
    entry_credit: float  # per share
    entry_commission: float
    opened_at: datetime
    status: str  # open | expiring | closed
    exit_debit: float | None = None  # per share, qty-weighted; None while open
    exit_commission: float | None = None
    exit_reason: str | None = None
    closed_at: datetime | None = None
    realized_pnl_usd: float | None = None  # None while open, never 0.0


class SpreadPositionsResponse(Envelope):
    available: bool  # False when data/spreads.db does not exist or cannot be read
    underlying: str
    mode: str
    positions: list[SpreadPositionOut] = Field(default_factory=list)
