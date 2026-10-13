"""Wheel-adjusted cost basis: per share, per campaign, and across the whole stock position.

2026-10-13: ``mark_campaign_assigned`` subtracted ``net_premium / 100`` — per share only on a
one-contract wheel. MARA (10 puts at $0.37, $370 in all) was stored at an $8.30 basis instead
of $11.63, and the covered-call gate would have passed strikes below the real cost. The gate
also read only the newest campaign's basis and applied it to every share held.
"""

from __future__ import annotations

import pytest

from tests.test_phase6 import _db_setup, _seed_fill


def _seed_candidate(session, candidate_id: str, strike: float, right: str = "P") -> None:
    from datetime import date

    from src.storage.models import CandidateRow

    session.add(
        CandidateRow(
            candidate_id=candidate_id,
            run_id="r",
            strategy="cash_secured_put" if right == "P" else "covered_call",
            underlying="MARA",
            right=right,
            strike=strike,
            expiry=date(2026, 7, 17),
            payload={},
        )
    )
    session.flush()


def _wheel(candidate_id: str, price: float, qty: float, *, strike: float = 12.0) -> None:
    from src.storage.campaigns import attach_fill_to_campaign
    from src.storage.db import session_scope

    with session_scope() as s:
        _seed_fill(s, candidate_id, "SELL", price, qty)
        _seed_candidate(s, candidate_id, strike)
    attach_fill_to_campaign("MARA", candidate_id, "cash_secured_put", "SELL", price, qty)


def test_a_ten_contract_assignment_spreads_the_premium_over_a_thousand_shares(
    tmp_path, monkeypatch
):
    from src.storage.campaigns import load_campaigns, mark_campaign_assigned

    _db_setup(tmp_path, monkeypatch)
    _wheel("mara-csp", 0.37, 10)
    mark_campaign_assigned("MARA", assignment_price=12.0, right="P", candidate_id="mara-csp")

    (c,) = load_campaigns()
    assert c["adjusted_cost_basis"] == pytest.approx(11.63)  # 12 − 370 / 1000, not 12 − 3.70


def test_the_gate_basis_is_ibkrs_cost_less_only_the_premium_ibkr_has_not_counted(
    tmp_path, monkeypatch
):
    """IBKR's avg cost on assigned shares already nets the assigned put's premium (MARA:
    11.6375 = 12 − 0.37 + commission), so only earlier legs of the wheel — a put bought back
    or rolled before the one that was assigned — lower the basis further."""
    from src.storage.campaigns import (
        adjusted_cost_basis_for,
        attach_fill_to_campaign,
        mark_campaign_assigned,
    )
    from src.storage.db import session_scope

    _db_setup(tmp_path, monkeypatch)
    _wheel("csp-1", 0.50, 10, strike=13.0)  # $500 in
    _wheel("csp-2", 0.37, 10)  # rolled into the put that was assigned: $370
    with session_scope() as s:
        _seed_fill(s, "csp-1", "BUY", 0.20, 10)  # the roll's buy-back: $200 out → $300 kept
    attach_fill_to_campaign("MARA", "csp-1", "cash_secured_put", "BUY", 0.20, 10)
    mark_campaign_assigned("MARA", assignment_price=12.0, right="P", candidate_id="csp-2")

    # Only the rolled leg's $300 is beyond IBKR's cost: 11.6375 − 300 / 1000.
    basis = adjusted_cost_basis_for("MARA", shares_held=1000, avg_cost=11.6375)
    assert basis == pytest.approx(11.3375)
    # Shares bought outright beside the wheel's shares dilute that $300 across all of them.
    assert adjusted_cost_basis_for("MARA", shares_held=1500, avg_cost=11.0) == pytest.approx(10.8)


def test_no_assigned_campaign_leaves_the_gate_on_ibkrs_cost(tmp_path, monkeypatch):
    from src.storage.campaigns import adjusted_cost_basis_for

    _db_setup(tmp_path, monkeypatch)
    _wheel("csp-1", 0.37, 10)  # sold, never assigned
    assert adjusted_cost_basis_for("MARA", shares_held=1000, avg_cost=11.0) is None


def test_init_repairs_a_basis_written_by_the_per_100_formula(tmp_path, monkeypatch):
    """The live MARA row: assigned, basis 8.30, no assignment record. Startup rebuilds it from
    the assigned leg's own strike and contracts."""
    import src.storage.db as dbmod
    from src.storage.campaigns import adjusted_cost_basis_for, load_campaigns
    from src.storage.db import session_scope
    from src.storage.models import CampaignRow

    _db_setup(tmp_path, monkeypatch)
    _wheel("aae7b9b105f85bee", 0.37, 10)
    with session_scope() as s:
        row = s.query(CampaignRow).one()
        row.assigned = True
        row.adjusted_cost_basis = 8.30  # what the old formula stored
    dbmod.init_db()
    dbmod.init_db()  # idempotent

    (c,) = load_campaigns()
    assert c["adjusted_cost_basis"] == pytest.approx(11.63)
    assert adjusted_cost_basis_for("MARA", shares_held=1000, avg_cost=11.6375) == pytest.approx(
        11.6375
    )
