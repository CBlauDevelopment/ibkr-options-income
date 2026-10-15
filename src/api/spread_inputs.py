"""The book's spread rows as the plain inputs the reporting builders take (web, 2026-10-15).

`src/api/` may not import `src.spreads` (the spreads fence), so the rows come through
`src/api/spreads_db.py`'s read-only SQL. Each function returns None when spreads.db could not be
read (absent, not a database, locked, or no spread_positions table), which the routes turn into
`spreads_available: false` rather than a quiet $0.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.api.models.common import as_utc, as_utc_opt
from src.api.models.spreads import SpreadPositionOut
from src.api.spreads_db import spreads_read_session, try_read_spread_rows
from src.common.config import get_config
from src.reporting.day import SpreadDayInput
from src.reporting.pay import SpreadPayInput


def spread_rows(book: str) -> list[dict[str, Any]] | None:
    """Spread rows of the running book; None when spreads.db could not be read (absent, not a
    database, locked, or no spread_positions table)."""
    with spreads_read_session() as s:
        if s is None:
            return None
        return try_read_spread_rows(s, mode=book, status="all", limit=5000)


def _dt(v: object) -> datetime | None:
    if v is None:
        return None
    return v if isinstance(v, datetime) else datetime.fromisoformat(str(v))


def spread_pay_inputs(book: str) -> list[SpreadPayInput] | None:
    """Spread positions of the running book as plain inputs; None when spreads.db could not be
    read (absent, not a database, locked, or no spread_positions table)."""
    rows = spread_rows(book)
    if rows is None:
        return None
    return [
        SpreadPayInput(
            opened_at=_dt(r["opened_at"]) or datetime.now(UTC),
            closed_at=_dt(r["closed_at"]),
            entry_credit=float(r["entry_credit"]),
            exit_debit=None if r["exit_debit"] is None else float(r["exit_debit"]),
            contracts_opened=int(r["contracts_opened"]),
            contracts_open=int(r["contracts"]),
            entry_commission=float(r["entry_commission"] or 0.0),
            exit_commission=float(r["exit_commission"] or 0.0),
        )
        for r in rows
    ]


def spread_day_inputs(book: str) -> list[SpreadDayInput] | None:
    """The same rows with the identity and the exit reason the day's cards and the calendar
    need; None when spreads.db could not be read."""
    rows = spread_rows(book)
    if rows is None:
        return None
    underlying = get_config().spreads.underlying
    return [
        SpreadDayInput(
            spread_id=str(r["spread_id"]),
            underlying=underlying,
            side=r["side"],
            expiry=r["expiry"],
            short_strike=float(r["short_strike"]),
            long_strike=float(r["long_strike"]),
            width=float(r["width"]),
            contracts_opened=int(r["contracts_opened"]),
            contracts_open=int(r["contracts"]),
            entry_credit=float(r["entry_credit"]),
            entry_commission=float(r["entry_commission"] or 0.0),
            opened_at=_dt(r["opened_at"]) or datetime.now(UTC),
            closed_at=_dt(r["closed_at"]),
            exit_debit=None if r["exit_debit"] is None else float(r["exit_debit"]),
            exit_commission=float(r["exit_commission"] or 0.0),
            exit_reason=r["exit_reason"],
            status=str(r["status"]),
            realized_pnl_usd=None
            if r["realized_pnl_usd"] is None
            else float(r["realized_pnl_usd"]),
            is_live=book == "live",
        )
        for r in rows
    ]


def spread_position_out(row: dict[str, Any], now: datetime) -> SpreadPositionOut:
    """One spread_positions row as the API model, as `GET /spreads/positions` renders it."""
    return SpreadPositionOut(
        as_of=now,
        **{
            **row,
            "opened_at": as_utc(row["opened_at"])
            if isinstance(row["opened_at"], datetime)
            else row["opened_at"],
            "closed_at": as_utc_opt(row["closed_at"])
            if isinstance(row["closed_at"], datetime)
            else row["closed_at"],
            "realized_pnl_usd": row["realized_pnl_usd"] if row["status"] == "closed" else None,
        },
    )
