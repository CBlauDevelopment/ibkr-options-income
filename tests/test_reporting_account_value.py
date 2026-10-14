"""Account value over time: daily from the journal, intraday from portfolio snapshots."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from src.reporting.account_value import account_value_series, month_start_value
from tests.conftest import _account_dict

NOW = datetime(2026, 10, 13, 18, 0, tzinfo=UTC)  # 14:00 ET, a Tuesday


def _journal(db, day: date, net_liq: float) -> None:
    from src.storage.models import JournalRow

    with db() as s:
        s.add(
            JournalRow(
                entry_date=day,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                payload={"fills": [], "eod_summary": {"account": _account_dict(net_liq, 80_000.0)}},
            )
        )


def _snap(db, at: datetime, net_liq: float) -> None:
    from src.storage.models import PortfolioSnapshotRow

    with db() as s:
        s.add(
            PortfolioSnapshotRow(
                captured_at=at,
                source="monitor",
                account=_account_dict(net_liq, 80_000.0),
                positions=[],
            )
        )


def test_empty_history_is_empty_not_zero(db) -> None:
    series = account_value_series(db, "1m", now=NOW)
    assert series.points == []
    assert series.latest is None
    assert series.change_today is None


def test_daily_ranges_read_the_journal_and_end_at_the_latest_snapshot(db) -> None:
    _journal(db, date(2026, 10, 9), 100_000.0)
    _journal(db, date(2026, 10, 12), 101_000.0)
    _snap(db, NOW - timedelta(minutes=5), 101_500.0)

    series = account_value_series(db, "1m", now=NOW)
    assert [p.value for p in series.points] == [100_000.0, 101_000.0, 101_500.0]
    assert series.latest == 101_500.0
    assert series.previous_close == 101_000.0
    assert series.change_today == 500.0
    assert round(series.change_today_pct or 0, 4) == round(500 / 101_000 * 100, 4)


def test_one_month_drops_older_journal_days(db) -> None:
    _journal(db, date(2026, 8, 1), 90_000.0)
    _journal(db, date(2026, 10, 12), 101_000.0)
    series = account_value_series(db, "1m", now=NOW)
    assert [p.value for p in series.points] == [101_000.0]


def test_intraday_ranges_read_snapshots(db) -> None:
    _snap(db, NOW - timedelta(days=2), 99_000.0)
    _snap(db, NOW - timedelta(hours=3), 100_000.0)
    _snap(db, NOW - timedelta(minutes=5), 100_200.0)
    assert [p.value for p in account_value_series(db, "1d", now=NOW).points] == [
        100_000.0,
        100_200.0,
    ]
    assert len(account_value_series(db, "1w", now=NOW).points) == 3


def test_an_unreadable_payload_is_skipped_not_zeroed(db) -> None:
    from src.storage.models import JournalRow

    with db() as s:
        s.add(
            JournalRow(
                entry_date=date(2026, 10, 12),
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                payload={"x": 1},
            )
        )
    _journal(db, date(2026, 10, 9), 100_000.0)
    series = account_value_series(db, "1m", now=NOW)
    assert [p.value for p in series.points] == [100_000.0]


def test_a_newer_journal_close_beats_a_stale_snapshot(db) -> None:
    """A monitor that stopped days ago must not pose as today's value (or today's change)."""
    _snap(db, NOW - timedelta(days=5), 95_000.0)
    _journal(db, date(2026, 10, 9), 100_000.0)
    _journal(db, date(2026, 10, 12), 101_000.0)
    series = account_value_series(db, "1m", now=NOW)
    assert series.latest == 101_000.0
    assert series.points[-1].value == 101_000.0
    assert series.previous_close == 101_000.0
    assert series.change_today == 0.0


def test_a_same_day_snapshot_still_wins_over_that_days_close(db) -> None:
    """Only a journal day after the snapshot's New York day replaces it, never a same-day close."""
    _journal(db, date(2026, 10, 12), 101_000.0)
    _journal(db, date(2026, 10, 13), 101_200.0)  # plotted at 16:00 ET, after NOW
    _snap(db, NOW - timedelta(minutes=5), 101_500.0)
    series = account_value_series(db, "1m", now=NOW)
    assert series.latest == 101_500.0
    assert series.change_today == 500.0


def test_month_start_value_is_the_last_close_before_the_month(db) -> None:
    _journal(db, date(2026, 9, 29), 98_000.0)
    _journal(db, date(2026, 9, 30), 99_000.0)
    _journal(db, date(2026, 10, 1), 99_500.0)
    assert month_start_value(db, date(2026, 10, 1)) == 99_000.0
    assert month_start_value(db, date(2026, 9, 1)) is None
