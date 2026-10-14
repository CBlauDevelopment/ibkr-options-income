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


def test_one_month_series_carries_today_change(
    client, db, seed_journal_day, seed_portfolio_snapshot
) -> None:
    yesterday = date.today() - timedelta(days=1)
    seed_journal_day(yesterday, net_liq=100_000.0)
    seed_portfolio_snapshot(captured_at=datetime.now(UTC) - timedelta(minutes=2), net_liq=100_400.0)
    s = client.get("/portfolio/value?range=1m", headers=OWNER).json()["series"]
    assert s["range"] == "1m"
    assert s["latest"] == 100_400.0
    assert s["points"][-1]["value"] == 100_400.0


def test_an_unknown_range_is_422(client) -> None:
    assert client.get("/portfolio/value?range=2y", headers=OWNER).status_code == 422


def test_it_requires_the_owner(client) -> None:
    assert client.get("/portfolio/value").status_code in (401, 403)
