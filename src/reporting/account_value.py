"""Account value over time — read-only, like the rest of src/reporting/.

Two sources, one shape: the EOD journal (one net-liquidation point per trading day) and the
intraday `portfolio_snapshots` table (every ~15 minutes, 30-day retention). Imports nothing
from the enrichment layer or the API package (tests/test_web_fence.py greps for the names).
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.common.schemas import (
    AccountSnapshot,
    AccountValuePoint,
    AccountValueRange,
    AccountValueSeries,
)
from src.reporting.pnl import _net_liquidation_from_payload
from src.storage.models import JournalRow, PortfolioSnapshotRow

_ET = ZoneInfo("America/New_York")
_SessionFactory = Callable[[], AbstractContextManager[Session]]
_INTRADAY_DAYS = {"1d": 1, "1w": 7}
_DAILY_DAYS = {"1m": 31, "3m": 92}


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _naive_utc(dt: datetime) -> datetime:
    return _as_utc(dt).replace(tzinfo=None)


def _snap_value(row: PortfolioSnapshotRow) -> float | None:
    try:
        return AccountSnapshot.model_validate(row.account).net_liquidation
    except Exception:
        return None


def _close_at(day: date) -> datetime:
    """A journal day plotted at that day's 16:00 ET close."""
    return datetime.combine(day, time(16, 0), tzinfo=_ET).astimezone(UTC)


def account_value_series(
    session: _SessionFactory, range_key: AccountValueRange, *, now: datetime
) -> AccountValueSeries:
    today_et = _as_utc(now).astimezone(_ET).date()
    with session() as sess:
        journal = (
            sess.execute(select(JournalRow).order_by(JournalRow.entry_date.asc())).scalars().all()
        )
        latest_row = sess.execute(
            select(PortfolioSnapshotRow)
            .order_by(PortfolioSnapshotRow.captured_at.desc(), PortfolioSnapshotRow.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        snaps: list[PortfolioSnapshotRow] = []
        if range_key in _INTRADAY_DAYS:
            start = _naive_utc(now - timedelta(days=_INTRADAY_DAYS[range_key]))
            snaps = list(
                sess.execute(
                    select(PortfolioSnapshotRow)
                    .where(PortfolioSnapshotRow.captured_at >= start)
                    .order_by(PortfolioSnapshotRow.captured_at.asc(), PortfolioSnapshotRow.id.asc())
                ).scalars()
            )

    daily = [(r.entry_date, _net_liquidation_from_payload(r.payload)) for r in journal]
    daily_known = [(d, v) for d, v in daily if v is not None]

    # The latest snapshot, unless the journal has a close from a later New York day (a monitor
    # that stopped days ago must not pose as today's value or today's change).
    latest: float | None = None
    latest_at: datetime | None = None
    if latest_row is not None and (v := _snap_value(latest_row)) is not None:
        latest, latest_at = v, _as_utc(latest_row.captured_at)
    if daily_known and (latest_at is None or daily_known[-1][0] > latest_at.astimezone(_ET).date()):
        latest, latest_at = daily_known[-1][1], _close_at(daily_known[-1][0])

    points: list[AccountValuePoint] = []
    if range_key in _INTRADAY_DAYS:
        for row in snaps:
            if (v := _snap_value(row)) is not None:
                points.append(AccountValuePoint(at=_as_utc(row.captured_at), value=v))
    else:
        if range_key == "ytd":
            start_day: date | None = date(today_et.year, 1, 1)
        elif range_key == "all":
            start_day = None
        else:
            start_day = today_et - timedelta(days=_DAILY_DAYS[range_key])
        for d, v in daily_known:
            if start_day is None or d >= start_day:
                points.append(AccountValuePoint(at=_close_at(d), value=v))
        if (
            latest is not None
            and latest_at is not None
            and (not points or latest_at > points[-1].at)
        ):
            points.append(AccountValuePoint(at=latest_at, value=latest))

    before_today = [v for d, v in daily_known if d < today_et]
    previous_close = before_today[-1] if before_today else None
    change = latest - previous_close if latest is not None and previous_close is not None else None
    change_pct = change / previous_close * 100 if change is not None and previous_close else None

    return AccountValueSeries(
        range=range_key,
        points=points,
        latest=latest,
        latest_at=latest_at,
        previous_close=previous_close,
        change_today=change,
        change_today_pct=change_pct,
    )


def month_start_value(session: _SessionFactory, first_day: date) -> float | None:
    """Net liquidation at the last journal close before `first_day`; None when there is none."""
    with session() as sess:
        rows = sess.execute(
            select(JournalRow)
            .where(JournalRow.entry_date < first_day)
            .order_by(JournalRow.entry_date.desc())
        ).scalars()
        for r in rows:
            v = _net_liquidation_from_payload(r.payload)
            if v is not None:
                return v
    return None
