"""GET /portfolio/value — the Home hero's series. Empty is empty, never zero."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from tests.conftest import OWNER


@pytest.fixture()
def db(api_db):
    return api_db


def test_empty_is_200_with_no_points(client) -> None:
    r = client.get("/portfolio/value?range=1m", headers=OWNER)
    assert r.status_code == 200
    s = r.json()["series"]
    assert s["points"] == [] and s["latest"] is None and s["change_today"] is None


# The route's clock, frozen: Tuesday 2026-10-13 13:00 EDT (01:00 Wednesday on a UTC+8 machine,
# the window where a local "yesterday" is New York's today). Nothing below reads the wall clock
# or the machine's timezone.
FROZEN_NOW = datetime(2026, 10, 13, 17, 0, tzinfo=UTC)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return FROZEN_NOW if tz is None else FROZEN_NOW.astimezone(tz)


def test_one_month_series_carries_today_change(
    client, db, seed_journal_day, seed_portfolio_snapshot, monkeypatch
) -> None:
    monkeypatch.setattr("src.api.routers.portfolio.datetime", _FrozenDatetime)
    seed_journal_day(date(2026, 10, 12), net_liq=100_000.0)
    # A row for today whose 16:00 ET close has not happened yet is not a close.
    seed_journal_day(date(2026, 10, 13), net_liq=100_900.0)
    seed_portfolio_snapshot(captured_at=FROZEN_NOW - timedelta(minutes=2), net_liq=100_400.0)
    s = client.get("/portfolio/value?range=1m", headers=OWNER).json()["series"]
    assert s["range"] == "1m"
    assert s["latest"] == 100_400.0
    assert s["points"][-1]["value"] == 100_400.0
    assert s["change_today"] == 400.0


def test_an_unknown_range_is_422(client) -> None:
    assert client.get("/portfolio/value?range=2y", headers=OWNER).status_code == 422


def test_it_requires_the_owner(client) -> None:
    assert client.get("/portfolio/value").status_code in (401, 403)
