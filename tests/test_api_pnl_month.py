"""GET /pnl/month — a thin render of build_month_pay."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from tests.conftest import OWNER

ET = ZoneInfo("America/New_York")


@pytest.fixture()
def db(api_db):
    return api_db


@pytest.fixture(autouse=True)
def _no_real_spreads_db(tmp_path, monkeypatch):
    """strategy=all reads the spreads book: never let a test read the operator's data/spreads.db."""
    import src.api.spreads_db as sdb

    monkeypatch.setattr(sdb, "_resolve_path", lambda: str(tmp_path / "no-spreads.db"))
    sdb.reset_engine()
    yield
    sdb.reset_engine()


def this_month() -> str:
    return datetime.now(ET).strftime("%Y-%m")


def fill_month() -> str:
    """The New York month a fill `seed_leg` writes now lands in. seed_leg stamps naive LOCAL
    time, which the builder reads as UTC like every stored fill, so on a machine far from New
    York the two months differ for a few hours after a month turns; ask for the fill's month."""
    return datetime.now().replace(tzinfo=UTC).astimezone(ET).strftime("%Y-%m")


def test_an_empty_month_is_zero_income_and_no_target(client) -> None:
    r = client.get(f"/pnl/month?month={this_month()}", headers=OWNER)
    assert r.status_code == 200
    pay = r.json()["pay"]
    assert pay["premium_collected"] == 0.0
    assert pay["target"] is None
    assert r.json()["book"] == "paper"


def test_a_put_sold_today_counts(client, db, seed_leg) -> None:
    seed_leg(candidate_id="c1", sold=(1, 2.35, 1.3), days_held=0)
    pay = client.get(f"/pnl/month?month={fill_month()}&strategy=csp", headers=OWNER).json()["pay"]
    assert pay["premium_collected"] == pytest.approx(235.0)
    assert pay["commissions"] == pytest.approx(1.3)
    assert pay["strategy"] == "csp"


def test_a_bad_month_is_422(client) -> None:
    assert client.get("/pnl/month?month=2026-13", headers=OWNER).status_code == 422
    assert client.get("/pnl/month?strategy=iron_condor", headers=OWNER).status_code == 422


def test_spreads_unavailable_still_answers(client, monkeypatch, tmp_path) -> None:
    import src.api.spreads_db as sdb

    monkeypatch.setattr(sdb, "_resolve_path", lambda: str(tmp_path / "absent.db"))
    sdb.reset_engine()
    r = client.get(f"/pnl/month?month={this_month()}&strategy=spread", headers=OWNER)
    assert r.status_code == 200
    assert r.json()["pay"]["premium_collected"] == 0.0
    # A spreads book in scope that could not be read is not a real $0: the response says so.
    assert r.json()["spreads_available"] is False


def _point_spreads_at(monkeypatch, path) -> None:
    import src.api.spreads_db as sdb

    monkeypatch.setattr(sdb, "_resolve_path", lambda: str(path))
    sdb.reset_engine()


def _healthy_spreads_db(path) -> None:
    from sqlalchemy import create_engine

    from src.spreads.store import SpreadsBase

    eng = create_engine(f"sqlite:///{path}")
    SpreadsBase.metadata.create_all(eng)
    eng.dispose()


@pytest.mark.parametrize("strategy", ["spread", "all"])
def test_an_unreadable_spreads_book_is_flagged_not_zeroed(
    client, monkeypatch, tmp_path, strategy
) -> None:
    garbage = tmp_path / "spreads.db"
    garbage.write_bytes(b"this is not a sqlite database " * 200)
    _point_spreads_at(monkeypatch, garbage)
    r = client.get(f"/pnl/month?month={this_month()}&strategy={strategy}", headers=OWNER)
    assert r.status_code == 200
    assert r.json()["spreads_available"] is False


@pytest.mark.parametrize("strategy", ["csp", "cc"])
@pytest.mark.parametrize("healthy", [True, False])
def test_a_wheel_only_strategy_never_needs_the_spreads_book(
    client, monkeypatch, tmp_path, strategy, healthy
) -> None:
    path = tmp_path / "spreads.db"
    if healthy:
        _healthy_spreads_db(path)
    _point_spreads_at(monkeypatch, path)
    r = client.get(f"/pnl/month?month={this_month()}&strategy={strategy}", headers=OWNER)
    assert r.json()["spreads_available"] is True


def test_only_the_books_own_spreads_count(client, monkeypatch, tmp_path) -> None:
    """Shadow and baseline spreads are simulations: they never enter the paper book's pay."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    import src.api.spreads_db as sdb
    from src.spreads.store import SpreadPositionRow, SpreadsBase

    path = tmp_path / "spreads.db"
    eng = create_engine(f"sqlite:///{path}")
    SpreadsBase.metadata.create_all(eng)
    opened = datetime.now(UTC).replace(tzinfo=None)  # spreads.db stores naive UTC
    with Session(eng) as s:
        for spread_id, mode in (("p1", "paper"), ("s1", "shadow"), ("b1", "baseline")):
            s.add(
                SpreadPositionRow(
                    spread_id=spread_id,
                    mode=mode,
                    side="put",
                    expiry=date.today(),
                    short_strike=580.0,
                    long_strike=575.0,
                    width=5.0,
                    contracts_opened=2,
                    contracts=2,
                    entry_credit=0.42,
                    entry_commission=2.6,
                    opened_at=opened,
                    status="open",
                )
            )
        s.commit()
    eng.dispose()
    monkeypatch.setattr(sdb, "_resolve_path", lambda: str(path))
    sdb.reset_engine()

    body = client.get(f"/pnl/month?month={this_month()}&strategy=spread", headers=OWNER).json()
    assert body["spreads_available"] is True
    pay = body["pay"]
    assert pay["premium_collected"] == pytest.approx(84.0)
    assert pay["commissions"] == pytest.approx(2.6)
    assert pay["n_opened"] == 1


def test_the_target_is_the_web_setting_of_the_month_start_value(
    client, db, seed_journal_day, monkeypatch
) -> None:
    from datetime import timedelta

    from src.common.config import get_config

    first = datetime.now(ET).date().replace(day=1)
    seed_journal_day(first - timedelta(days=3), net_liq=200_000.0)
    url = f"/pnl/month?month={this_month()}"

    unset = client.get(url, headers=OWNER).json()["pay"]
    assert unset["month_start_value"] == 200_000.0
    assert unset["target_pct"] is None and unset["target"] is None  # "No target set", not $0

    monkeypatch.setattr(get_config().web, "monthly_income_target_pct", 1.0)
    pay = client.get(url, headers=OWNER).json()["pay"]
    assert pay["target_pct"] == 1.0
    assert pay["target"] == pytest.approx(2_000.0)


def test_the_income_target_setting_is_bounded() -> None:
    from pydantic import ValidationError

    from src.common.config import WebCfg, get_config

    assert get_config().web.monthly_income_target_pct is None  # the committed example ships unset
    assert WebCfg(monthly_income_target_pct=1.5).monthly_income_target_pct == 1.5
    assert WebCfg(monthly_income_target_pct=20).monthly_income_target_pct == 20
    for bad in (0, -1, 20.5):
        with pytest.raises(ValidationError):
            WebCfg(monthly_income_target_pct=bad)
