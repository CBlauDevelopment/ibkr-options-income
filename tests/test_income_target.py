"""The monthly income target (web, 2026-10-15): the schema, the stored form, the resolution
order, the drained command and the two routes that read it."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.api.models.commands import (
    CommandKind,
    SetIncomeTargetPayload,
    dedupe_key_for,
    validate_payload,
)
from src.common.income_target import (
    dump_income_target,
    parse_income_target,
    resolve_income_target,
    target_value,
)
from src.common.schemas import IncomeTarget
from tests.conftest import OWNER

# --- the schema ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        {"mode": "off"},
        {"mode": "fixed", "amount": 2_000},
        {"mode": "pct_of_account", "pct": 1.5},
        {"mode": "pct_of_amount", "pct": 2, "base": 100_000},
        {"mode": "pct_of_account", "pct": 20},
    ],
)
def test_a_target_that_fits_its_mode_parses(fields) -> None:
    assert IncomeTarget(**fields).mode == fields["mode"]


@pytest.mark.parametrize(
    "fields",
    [
        {"mode": "fixed"},  # needs an amount
        {"mode": "fixed", "amount": 0},
        {"mode": "fixed", "amount": -5},
        {"mode": "fixed", "amount": 2_000_001},
        {"mode": "fixed", "amount": 2_000, "pct": 1},  # takes no pct
        {"mode": "pct_of_account"},
        {"mode": "pct_of_account", "pct": 0},
        {"mode": "pct_of_account", "pct": 20.5},  # the config's own bound
        {"mode": "pct_of_account", "pct": 1, "base": 100_000},  # takes no base
        {"mode": "pct_of_amount", "pct": 2},  # needs a base
        {"mode": "pct_of_amount", "base": 100_000},  # needs a pct
        {"mode": "pct_of_amount", "pct": 2, "base": 0},
        {"mode": "off", "amount": 100},
        {"mode": "weekly", "amount": 100},
    ],
)
def test_a_target_that_does_not_fit_its_mode_is_refused(fields) -> None:
    with pytest.raises(ValidationError):
        IncomeTarget(**fields)


def test_the_payload_is_the_same_schema_and_refuses_unknown_keys() -> None:
    parsed = validate_payload(CommandKind.SET_INCOME_TARGET, {"mode": "fixed", "amount": 1_000})
    assert isinstance(parsed, SetIncomeTargetPayload)
    with pytest.raises(ValidationError):
        validate_payload(CommandKind.SET_INCOME_TARGET, {"mode": "fixed", "amount": 1, "x": 1})


def test_a_target_is_repeatable_so_it_has_no_dedupe_key() -> None:
    payload = SetIncomeTargetPayload(mode="off")
    assert dedupe_key_for(CommandKind.SET_INCOME_TARGET, payload) is None


# --- the stored form and the arithmetic ---------------------------------------------------


def test_the_stored_form_round_trips_and_junk_reads_as_nothing() -> None:
    t = IncomeTarget(mode="pct_of_amount", pct=2.0, base=50_000.0)
    assert parse_income_target(dump_income_target(t)) == t
    for junk in (
        None,
        "",
        "not json",
        "[]",
        '{"mode": "fixed"}',
        '{"mode": "fixed", "amount": -1}',
    ):
        assert parse_income_target(junk) is None


def test_a_web_row_beats_the_config_and_off_beats_it_too() -> None:
    web = dump_income_target(IncomeTarget(mode="fixed", amount=900))
    assert resolve_income_target(web, 1.0) == (IncomeTarget(mode="fixed", amount=900), "web")
    off = dump_income_target(IncomeTarget(mode="off"))
    assert resolve_income_target(off, 1.0) == (IncomeTarget(mode="off"), "web")


def test_no_row_falls_back_to_the_config_percentage_then_to_nothing() -> None:
    assert resolve_income_target(None, 1.5) == (
        IncomeTarget(mode="pct_of_account", pct=1.5),
        "config",
    )
    assert resolve_income_target("junk", None) == (IncomeTarget(mode="off"), "none")


def test_target_value_per_mode() -> None:
    assert target_value(IncomeTarget(mode="fixed", amount=750), None) == 750
    assert target_value(IncomeTarget(mode="pct_of_account", pct=1), 200_000) == 2_000
    assert target_value(IncomeTarget(mode="pct_of_account", pct=1), None) is None
    assert target_value(IncomeTarget(mode="pct_of_account", pct=1), 0) is None
    assert target_value(IncomeTarget(mode="pct_of_amount", pct=2, base=100_000), None) == 2_000
    assert target_value(IncomeTarget(mode="off"), 200_000) is None


# --- the setting and the drained command --------------------------------------------------


def test_the_setting_round_trips_through_system_settings(db) -> None:
    from src.storage.system_settings import get_income_target, set_income_target

    assert get_income_target() is None
    set_income_target(IncomeTarget(mode="fixed", amount=1_250))
    assert get_income_target() == IncomeTarget(mode="fixed", amount=1_250)


def test_the_drain_handler_stores_the_target_and_reports_the_previous(db) -> None:
    from src.notify.command_drain import HANDLERS

    first = HANDLERS["set_income_target"](
        command=SimpleNamespace(
            id=1, payload={"mode": "fixed", "amount": 1_000}, requested_by="owner"
        ),
    )
    assert first == {"target": {"mode": "fixed", "amount": 1000.0}, "previous": None}
    second = HANDLERS["set_income_target"](
        command=SimpleNamespace(
            id=2,
            payload={"mode": "pct_of_amount", "pct": 2, "base": 100_000},
            requested_by="owner",
        ),
    )
    assert second["previous"] == {"mode": "fixed", "amount": 1000.0}
    assert second["target"] == {"mode": "pct_of_amount", "pct": 2.0, "base": 100000.0}


# --- the routes ---------------------------------------------------------------------------


@pytest.fixture()
def db(api_db):
    return api_db


@pytest.fixture(autouse=True)
def _no_real_spreads_db(tmp_path, monkeypatch):
    import src.api.spreads_db as sdb

    monkeypatch.setattr(sdb, "_resolve_path", lambda: str(tmp_path / "no-spreads.db"))
    sdb.reset_engine()
    yield
    sdb.reset_engine()


def test_get_target_reports_nothing_by_default(client) -> None:
    body = client.get("/pnl/target", headers=OWNER).json()
    assert body["source"] == "none"
    assert body["target"] == {"mode": "off", "amount": None, "pct": None, "base": None}


def test_get_target_reports_the_web_setting(client, db) -> None:
    from src.storage.system_settings import set_income_target

    set_income_target(IncomeTarget(mode="pct_of_amount", pct=2.0, base=100_000.0))
    body = client.get("/pnl/target", headers=OWNER).json()
    assert body["source"] == "web"
    assert body["target"]["mode"] == "pct_of_amount"
    assert body["target"]["base"] == 100_000.0


def test_get_target_needs_the_owner(client) -> None:
    assert client.get("/pnl/target").status_code in (401, 403)


def test_the_month_pay_uses_a_fixed_web_target_without_a_month_start_value(client, db) -> None:
    from src.storage.system_settings import set_income_target

    set_income_target(IncomeTarget(mode="fixed", amount=1_500.0))
    pay = client.get("/pnl/month", headers=OWNER).json()["pay"]
    assert pay["month_start_value"] is None
    assert pay["target"] == 1_500.0
    assert pay["target_mode"] == "fixed"
    assert pay["target_amount"] == 1_500.0


def test_an_off_row_beats_the_config_percentage(client, db, monkeypatch) -> None:
    from src.common.config import get_config
    from src.storage.system_settings import set_income_target

    monkeypatch.setattr(get_config().web, "monthly_income_target_pct", 1.0)
    assert client.get("/pnl/target", headers=OWNER).json()["source"] == "config"
    set_income_target(IncomeTarget(mode="off"))
    pay = client.get("/pnl/month", headers=OWNER).json()["pay"]
    assert pay["target"] is None and pay["target_mode"] == "off"


def test_posting_the_command_creates_a_pending_row(client) -> None:
    resp = client.post(
        "/commands",
        json={"kind": "set_income_target", "payload": {"mode": "fixed", "amount": 2_000}},
        headers=OWNER,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["kind"] == "set_income_target"
    assert resp.json()["status"] == "pending"
    assert resp.json()["needs_confirmation"] is False


def test_posting_a_target_that_does_not_fit_is_a_422(client) -> None:
    resp = client.post(
        "/commands",
        json={"kind": "set_income_target", "payload": {"mode": "fixed"}},
        headers=OWNER,
    )
    assert resp.status_code == 422
