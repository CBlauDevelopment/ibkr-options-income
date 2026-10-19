"""GET /spreads/picks - one New York day of the spreads picker (web overhaul Part 2, Task 1).

Read-only over data/spreads.db through src/api/spreads_db.py (the API may not import
src.spreads). The tests may import the spreads models to build a real schema: test files are
not fenced.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine
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


@pytest.fixture()
def frozen_now(monkeypatch):
    """The route's clock: 2026-10-15 15:00 UTC, 11:00 in New York."""
    import src.api.routers.spreads as routes

    now = datetime(2026, 10, 15, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(routes, "_now", lambda: now)
    return now


def _menu_item(letter: str, position: str, short: float, long: float, contracts: int = 2) -> dict:
    from src.common.schemas import SpreadCandidate, SpreadMenuItem

    candidate = SpreadCandidate(
        spread_id=f"20261015-P{short:g}-{long:g}",
        side="put",
        expiry=date(2026, 10, 15),
        short_strike=short,
        long_strike=long,
        width=short - long,
        credit_mid=0.25,
        credit_natural=0.24,
        short_delta=-0.14,
        spot=767.29,
        quote_time=datetime(2026, 10, 15, 14, 17, tzinfo=UTC),
    )
    return SpreadMenuItem(
        letter=letter,
        position=position,
        candidate=candidate,
        contracts=contracts,
        credit_after_costs=0.144,
        cost_pct_of_credit=0.424,
        max_loss_per_contract_usd=475.0,
        dist_spot_pts=5.29,
        dist_em_multiple=1.49,
        beyond_wall_pts=2.73,
        be_full_loss=0.9712,
        be_nominal_exits=0.9493,
    ).model_dump(mode="json")


def _pick(**over) -> dict:
    base = dict(
        created_at=datetime(2026, 10, 15, 14, 17, 30),  # naive UTC, as the service writes it
        day=date(2026, 10, 15),
        episode_key="2026-10-15:put:765.25",
        book_mode="paper",
        menu=[_menu_item("A", "inside", 763.0, 758.0), _menu_item("B", "baseline", 762.0, 757.0)],
        choice="B",
        reason="B sits past the put wall.",
        executed_letter="B",
        model="claude-sonnet-5-5",
        effort="low",
        snapshot={"regime": "negative", "side": "put"},
        market={},
        regime="negative",
        side="put",
    )
    base.update(over)
    return base


def _position(**over) -> dict:
    base = dict(
        spread_id="20261015-P762-757-101726",
        mode="paper",
        side="put",
        expiry=date(2026, 10, 15),
        short_strike=762.0,
        long_strike=757.0,
        width=5.0,
        contracts_opened=2,
        contracts=2,
        entry_credit=0.25,
        entry_commission=2.6,
        opened_at=datetime(2026, 10, 15, 14, 18),
        status="open",
    )
    base.update(over)
    return base


def _make_db(path, *, picks=(), positions=(), with_picks_table: bool = True) -> None:
    from src.spreads.store import SpreadPickRow, SpreadPositionRow, SpreadsBase

    eng = create_engine(f"sqlite:///{path}")
    if with_picks_table:
        SpreadsBase.metadata.create_all(eng)
    else:
        SpreadPositionRow.__table__.create(eng)
    with Session(eng) as s:
        for p in picks:
            s.add(SpreadPickRow(**p))
        for p in positions:
            s.add(SpreadPositionRow(**p))
        s.commit()
    eng.dispose()


def test_no_file_is_unavailable_not_an_error(client, spreads_file, frozen_now) -> None:
    r = client.get("/spreads/picks", headers=OWNER)
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert body["picks"] == [] and body["positions"] == []
    assert body["day"] == "2026-10-15"
    assert isinstance(body["ai_enabled"], bool)


def test_the_default_day_is_today_in_new_york(client, spreads_file, monkeypatch) -> None:
    import src.api.routers.spreads as routes

    # 02:00 UTC on the 16th is still the evening of the 15th in New York.
    monkeypatch.setattr(routes, "_now", lambda: datetime(2026, 10, 16, 2, 0, tzinfo=UTC))
    _make_db(spreads_file, picks=[_pick()])
    body = client.get("/spreads/picks", headers=OWNER).json()
    assert body["day"] == "2026-10-15"
    assert len(body["picks"]) == 1


def test_a_pick_carries_its_menu_choice_and_outcome(client, spreads_file, frozen_now) -> None:
    _make_db(spreads_file, picks=[_pick(filled=True)])
    body = client.get("/spreads/picks?day=2026-10-15", headers=OWNER).json()
    assert body["available"] is True
    (p,) = body["picks"]
    assert (p["choice"], p["executed_letter"], p["filled"]) == ("B", "B", True)
    assert p["reason"] == "B sits past the put wall."
    assert p["menu_readable"] is True
    assert [i["letter"] for i in p["menu"]] == ["A", "B"]
    b = p["menu"][1]
    assert b["position"] == "baseline"
    assert (b["side"], b["short_strike"], b["long_strike"], b["contracts"]) == ("put", 762.0, 757.0, 2)
    assert (b["credit_mid"], b["credit_after_costs"], b["be_nominal_exits"]) == (0.25, 0.144, 0.9493)
    # Stored naive UTC leaves the API with an offset, so a browser never reads it as local time.
    assert p["created_at"].endswith(("Z", "+00:00"))


def test_send_reasons_and_flags_read_back(client, spreads_file, frozen_now) -> None:
    _make_db(spreads_file, picks=[_pick(send_rejected=True, send_reasons=["stale_pick"])])
    (p,) = client.get("/spreads/picks", headers=OWNER).json()["picks"]
    assert p["send_rejected"] is True and p["filled"] is False
    assert p["send_reasons"] == ["stale_pick"]


def test_an_unreadable_menu_is_flagged_and_the_other_picks_still_render(
    client, spreads_file, frozen_now
) -> None:
    bad = _pick(menu=[{"letter": "A"}], choice="A", executed_letter="A")
    good = _pick(created_at=datetime(2026, 10, 15, 15, 0), episode_key="2026-10-15:call:770")
    _make_db(spreads_file, picks=[bad, good])
    picks = client.get("/spreads/picks", headers=OWNER).json()["picks"]
    # Newest first: the good pick (15:00) leads.
    assert [p["menu_readable"] for p in picks] == [True, False]
    assert len(picks[0]["menu"]) == 2
    assert picks[1]["menu"] == []


def test_a_pick_names_the_spread_it_opened(client, spreads_file, frozen_now) -> None:
    _make_db(spreads_file, picks=[_pick(filled=True)], positions=[_position(pick_id=1)])
    body = client.get("/spreads/picks", headers=OWNER).json()
    assert body["picks"][0]["spread_id"] == "20261015-P762-757-101726"


def test_the_day_lists_every_book_opened_that_new_york_day(client, spreads_file, frozen_now) -> None:
    _make_db(
        spreads_file,
        positions=[
            _position(),
            _position(spread_id="base-1", mode="baseline"),
            _position(spread_id="yesterday", opened_at=datetime(2026, 10, 14, 15, 0)),
        ],
    )
    body = client.get("/spreads/picks?day=2026-10-15", headers=OWNER).json()
    assert sorted((p["spread_id"], p["mode"]) for p in body["positions"]) == [
        ("20261015-P762-757-101726", "paper"),
        ("base-1", "baseline"),
    ]


def test_previous_and_next_skip_days_with_nothing(client, spreads_file, frozen_now) -> None:
    _make_db(
        spreads_file,
        picks=[_pick(day=date(2026, 10, 9), created_at=datetime(2026, 10, 9, 14, 0), episode_key="a")],
        positions=[_position(spread_id="later", opened_at=datetime(2026, 10, 20, 14, 0))],
    )
    body = client.get("/spreads/picks?day=2026-10-15", headers=OWNER).json()
    assert body["previous_day"] == "2026-10-09"
    assert body["next_day"] == "2026-10-20"
    assert body["picks"] == [] and body["positions"] == []


def test_an_old_file_without_the_picks_table_is_available_with_no_picks(
    client, spreads_file, frozen_now
) -> None:
    _make_db(spreads_file, positions=[_position()], with_picks_table=False)
    body = client.get("/spreads/picks", headers=OWNER).json()
    assert body["available"] is True
    assert body["picks"] == []
    assert len(body["positions"]) == 1


def test_an_older_positions_table_without_pick_id_still_reads(client, spreads_file, frozen_now) -> None:
    con = sqlite3.connect(spreads_file)
    con.execute(
        "CREATE TABLE spread_positions (id INTEGER PRIMARY KEY, spread_id TEXT, mode TEXT, "
        "side TEXT, expiry DATE, short_strike FLOAT, long_strike FLOAT, width FLOAT, "
        "contracts_opened INTEGER, contracts INTEGER, entry_credit FLOAT, entry_commission FLOAT, "
        "opened_at DATETIME, status TEXT, exit_debit FLOAT, exit_commission FLOAT, "
        "exit_reason TEXT, closed_at DATETIME, realized_pnl_usd FLOAT)"
    )
    con.execute(
        "INSERT INTO spread_positions (spread_id, mode, side, expiry, short_strike, long_strike, "
        "width, contracts_opened, contracts, entry_credit, entry_commission, opened_at, status, "
        "exit_commission, realized_pnl_usd) VALUES ('s1', 'paper', 'put', '2026-10-15', 762, 757, "
        "5, 2, 2, 0.25, 2.6, '2026-10-15 14:18:00.000000', 'open', 0, 0)"
    )
    con.commit()
    con.close()
    body = client.get("/spreads/picks", headers=OWNER).json()
    assert body["available"] is True
    assert body["picks"] == []
    assert [p["spread_id"] for p in body["positions"]] == ["s1"]


def test_a_bad_day_is_a_422(client, spreads_file) -> None:
    assert client.get("/spreads/picks?day=2026-13-01", headers=OWNER).status_code == 422


def test_it_needs_the_owner(client, spreads_file) -> None:
    assert client.get("/spreads/picks").status_code in (401, 403)
