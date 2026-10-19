"""Response shapes for the P&L surfaces (P3-P4 M5).

Every route is a thin renderer over `src/reporting/pnl.py` — no figure is
computed here. Filters are echoed back on every response so a client can prove
what it is looking at, and `marks_as_of` names the snapshot backing every
unrealised figure (null when no snapshot exists — never a zero).
"""

from __future__ import annotations

import datetime as dt
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from src.api.models.common import Envelope
from src.common.income_target import TargetSource
from src.common.schemas import (
    CampaignPnl,
    DayTrade,
    EquityCurve,
    IncomeTarget,
    MonthCalendar,
    MonthPay,
    PnlSummary,
    ScoreOutcomeReport,
)


class LedgerFilters(Envelope):
    """Echoed back on every response so the client can prove what it is looking at."""

    symbol: str | None = None
    strategy: str | None = None
    outcome: str | None = None
    since: date | None = None
    until: date | None = None
    book: Literal["paper", "live", "all"] = "all"


class LedgerResponse(Envelope):
    filters: LedgerFilters
    campaigns: list[CampaignPnl]
    marks_as_of: datetime | None = None  # the snapshot backing every unrealised figure
    n_legs: int  # every leg, across every campaign; the client checks the sum


class SummaryResponse(Envelope):
    filters: LedgerFilters
    summary: PnlSummary
    marks_as_of: datetime | None = None


class EquityResponse(Envelope):
    filters: LedgerFilters
    curve: EquityCurve


class VerdictAgreement(BaseModel):
    """How often Claude's verdict matched the deterministic baseline, and how each did."""

    n_closed: int
    n_agreed: int
    agreement_rate: float | None = None  # None when n_closed is 0, never 0.0
    claude_win_rate: float | None = None
    baseline_win_rate: float | None = None


class SystemPerformanceResponse(Envelope):
    """The score-vs-outcome report plus verdict agreement — P3-P4 M6's fenced read (Task 6.1)."""

    report: ScoreOutcomeReport
    agreement: VerdictAgreement
    since: date | None = None
    until: date | None = None


class MonthPayResponse(Envelope):
    book: Literal["paper", "live"]
    pay: MonthPay
    # False only when a spreads book is in scope (strategy all or spread) and data/spreads.db
    # could not be read (absent, not a database, locked, no table): the spread part of `pay`
    # is then unknown, not $0, and an "all" total is the wheel alone.
    spreads_available: bool


class IncomeTargetResponse(Envelope):
    """The monthly income target in force and where it came from (web setting, the legacy
    `web.monthly_income_target_pct`, or none)."""

    target: IncomeTarget
    source: TargetSource


class DayTradesResponse(Envelope):
    """The trades opened, closed or rolled on one New York day (Home's "Done today")."""

    date: date
    book: Literal["paper", "live"]
    strategy: Literal["all", "csp", "cc", "spread"]
    trades: list[DayTrade]
    # False only when a spreads book is in scope and data/spreads.db could not be read: the
    # spreads cards are then missing, not absent, and the card says so.
    spreads_available: bool
    # Web overhaul Part 2: the nearest New York days with wheel activity (a trade or a proposal)
    # in this scope, for History's day navigation; None at either end. (`dt.date`: the `date`
    # field above shadows the type inside this class body.)
    previous_day: dt.date | None = None
    next_day: dt.date | None = None


class RealisedCalendarResponse(Envelope):
    """A month of daily realised P&L."""

    book: Literal["paper", "live"]
    calendar: MonthCalendar
    spreads_available: bool
