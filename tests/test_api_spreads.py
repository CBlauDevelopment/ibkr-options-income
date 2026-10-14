"""GET /spreads/positions — a read-only window onto data/spreads.db.

The API may not import src.spreads (tests/test_spreads_fence.py::NOT_SPREADS); it reads the
file through its own mode=ro engine with plain SQL. The tests may import the spreads models
to build a real schema - test files are not fenced.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from tests.conftest import OWNER


@pytest.fixture()
def spreads_file(tmp_path, monkeypatch):
    import src.api.spreads_db as sdb

    path = tmp_path / "spreads.db"
    monkeypatch.setattr(sdb, "_resolve_path", lambda: str(path))
    sdb.reset_engine()
    yield path
    sdb.reset_engine()


def _make_db(path, rows: list[dict]) -> None:
    from src.spreads.store import SpreadPositionRow, SpreadsBase

    eng = create_engine(f"sqlite:///{path}")
    SpreadsBase.metadata.create_all(eng)
    with Session(eng) as s:
        for r in rows:
            s.add(SpreadPositionRow(**r))
        s.commit()
    eng.dispose()


def _row(**over) -> dict:
    base = dict(
        spread_id="s1",
        mode="paper",
        side="put",
        expiry=date(2026, 10, 13),
        short_strike=580.0,
        long_strike=575.0,
        width=5.0,
        contracts_opened=1,
        contracts=1,
        entry_credit=0.42,
        entry_commission=1.3,
        opened_at=datetime(2026, 10, 13, 14, 0),
        status="open",
    )
    base.update(over)
    return base


def test_no_file_is_unavailable_not_an_error(client, spreads_file) -> None:
    r = client.get("/spreads/positions", headers=OWNER)
    assert r.status_code == 200
    assert r.json()["available"] is False
    assert r.json()["positions"] == []


def test_open_paper_positions_are_listed(client, spreads_file) -> None:
    _make_db(spreads_file, [_row(), _row(spread_id="s2", mode="shadow")])
    body = client.get("/spreads/positions?status=open", headers=OWNER).json()
    assert body["available"] is True
    assert body["mode"] == "paper"
    assert [p["spread_id"] for p in body["positions"]] == ["s1"]
    p = body["positions"][0]
    assert p["side"] == "put" and p["short_strike"] == 580.0 and p["entry_credit"] == 0.42
    assert p["exit_debit"] is None


def test_closed_filter_excludes_open(client, spreads_file) -> None:
    _make_db(
        spreads_file, [_row(), _row(spread_id="s3", status="closed", contracts=0, exit_debit=0.1)]
    )
    body = client.get("/spreads/positions?status=closed", headers=OWNER).json()
    assert [p["spread_id"] for p in body["positions"]] == ["s3"]


def test_the_engine_cannot_write(spreads_file) -> None:
    from sqlalchemy import text

    import src.api.spreads_db as sdb

    _make_db(spreads_file, [_row()])
    with sdb.spreads_read_session() as s:
        assert s is not None
        with pytest.raises(OperationalError):
            s.execute(text("DELETE FROM spread_positions"))
            s.commit()


def test_an_unreadable_file_is_unavailable_not_an_error(client, spreads_file) -> None:
    """A file that is not a SQLite database reads as unavailable, never a 500 or an empty book."""
    spreads_file.write_bytes(b"this is not a sqlite database " * 200)
    r = client.get("/spreads/positions", headers=OWNER)
    assert r.status_code == 200
    assert r.json()["available"] is False
    assert r.json()["positions"] == []


def test_timestamps_are_served_as_utc(client, spreads_file) -> None:
    """spreads.db stores naive UTC; raw SQL hands back strings, which must still leave with an
    offset (a naive timestamp is read by the browser as local time)."""
    _make_db(
        spreads_file,
        [
            _row(
                status="closed",
                contracts=0,
                exit_debit=0.1,
                closed_at=datetime(2026, 10, 13, 19, 30),
                realized_pnl_usd=30.7,
            )
        ],
    )
    p = client.get("/spreads/positions?status=all", headers=OWNER).json()["positions"][0]
    assert datetime.fromisoformat(p["opened_at"]) == datetime.fromisoformat(
        "2026-10-13T14:00:00+00:00"
    )
    assert datetime.fromisoformat(p["closed_at"]) == datetime.fromisoformat(
        "2026-10-13T19:30:00+00:00"
    )
    assert p["realized_pnl_usd"] == 30.7
