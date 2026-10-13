"""Campaign storage — wheel-strategy P&L threads (C6).

A campaign groups all option legs on one symbol under one P&L thread so the
operator can see cumulative income, adjusted cost basis after assignment, and
total return across a CSP→assignment→CC→roll→close sequence.

Public API:
  attach_fill_to_campaign  — called after every fill; opens or updates the campaign
  mark_campaign_assigned   — called by EOD reconciler when assignment is detected
  load_campaigns           — read-side for /campaigns Telegram command
  adjusted_cost_basis_for  — read-side for the covered-call gate (D5)
  repair_assigned_bases    — init_db: rebuild bases the per-100 formula wrote (2026-10-13)
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select

from src.storage.db import session_scope
from src.storage.models import CampaignRow, CandidateRow, FillRow

log = logging.getLogger(__name__)


def _generate_campaign_id(symbol: str) -> str:
    return f"{symbol}-{uuid.uuid4().hex[:8]}"


def _rollup(session, row: CampaignRow) -> None:
    """Recompute financial totals from all FillRow entries for the campaign's legs.

    Gross of commissions: this sums avg_price * filled_qty * 100 and never reads
    FillRow.commission, so total_premium_collected/total_debit_paid/net_premium exclude it by
    design (pinned by tests/test_campaign_rollup_semantics.py). src/reporting/ (from M4)
    reports the same trades net of commissions, the same way src/reporting/legs.py's
    classify_outcome does (credit - debit - commissions) — see CampaignRow's docstring for the
    fuller explanation of the gap between the two.
    """
    candidate_ids = list(row.leg_candidate_ids or [])
    if not candidate_ids:
        return

    fills = (
        session.execute(select(FillRow).where(FillRow.candidate_id.in_(candidate_ids)))
        .scalars()
        .all()
    )

    collected = 0.0
    paid = 0.0
    for f in fills:
        value = float(f.avg_price or 0.0) * float(f.filled_qty or 0.0) * 100
        if (f.action or "SELL").upper() == "SELL":
            collected += value
        else:
            paid += value

    row.total_premium_collected = round(collected, 2)
    row.total_debit_paid = round(paid, 2)
    row.net_premium = round(collected - paid, 2)


def _auto_close(session, row: CampaignRow) -> None:
    """Close the campaign when all entered contracts have been bought back (net flat)."""
    candidate_ids = list(row.leg_candidate_ids or [])
    if not candidate_ids:
        return

    fills = (
        session.execute(select(FillRow).where(FillRow.candidate_id.in_(candidate_ids)))
        .scalars()
        .all()
    )

    sell_qty = sum(
        float(f.filled_qty or 0) for f in fills if (f.action or "SELL").upper() == "SELL"
    )
    buy_qty = sum(float(f.filled_qty or 0) for f in fills if (f.action or "SELL").upper() == "BUY")

    if sell_qty > 0 and buy_qty >= sell_qty and not row.assigned:
        row.status = "closed"
        row.closed_date = datetime.now(UTC).date()


def attach_fill_to_campaign(
    symbol: str,
    candidate_id: str,
    strategy: str,
    action: str,
    avg_price: float,
    filled_qty: float,
) -> None:
    """Open or update the campaign for *symbol* after a fill is recorded.

    On a SELL fill (opening leg): find the open campaign for this symbol or create one.
    On a BUY fill (closing leg): attach to the open campaign (if any) for rollup.
    Always re-rolls the financials and checks for auto-close.

    Never raises — campaign failures are non-fatal relative to the fill record.
    """
    try:
        with session_scope() as session:
            # Find an open campaign for this symbol.
            row = session.execute(
                select(CampaignRow)
                .where(CampaignRow.symbol == symbol, CampaignRow.status == "open")
                .order_by(CampaignRow.opened_date.desc())
                .limit(1)
            ).scalar_one_or_none()

            if row is None:
                if action.upper() != "SELL":
                    # BUY with no open campaign — orphaned close, skip.
                    return
                # Open a new campaign on the first SELL (entry) fill.
                row = CampaignRow(
                    campaign_id=_generate_campaign_id(symbol),
                    symbol=symbol,
                    status="open",
                    opened_date=datetime.now(UTC).date(),
                    leg_candidate_ids=[candidate_id],
                    payload={"first_strategy": strategy},
                )
                session.add(row)
                session.flush()  # assigns row.id before rollup
            else:
                # Add this candidate to the leg list (deduplicated).
                legs = list(row.leg_candidate_ids or [])
                if candidate_id not in legs:
                    legs.append(candidate_id)
                    row.leg_candidate_ids = legs
                    payload = dict(row.payload or {})
                    payload["last_strategy"] = strategy
                    row.payload = payload

            _rollup(session, row)
            _auto_close(session, row)
    except Exception:
        log.warning(
            "attach_fill_to_campaign failed for %s candidate=%s",
            symbol,
            candidate_id,
            exc_info=True,
        )


def _leg_totals(session, candidate_id: str) -> tuple[float, float]:
    """(net short contracts, net premium in dollars) of one leg, from its fills."""
    contracts = premium = 0.0
    for f in session.execute(select(FillRow).where(FillRow.candidate_id == candidate_id)).scalars():
        qty = float(f.filled_qty or 0.0)
        sign = 1.0 if (f.action or "SELL").upper() == "SELL" else -1.0
        contracts += sign * qty
        premium += sign * float(f.avg_price or 0.0) * qty * 100
    return contracts, premium


def _record_assignment(
    session, row: CampaignRow, candidate_id: str | None, strike: float | None
) -> bool:
    """Freeze the assignment on *row*: the assigned leg's shares, its strike, and the premium
    of the legs before it. Returns False (row untouched) when the leg can't be found.

    adjusted_cost_basis = strike − (premium of the legs up to and including the assigned one)
    / assigned shares. ``prior_legs_premium`` is the part IBKR's own average cost does not
    already net: IBKR books assigned shares at the strike less the assigned put's premium."""
    legs = list(row.leg_candidate_ids or [])
    if candidate_id is None:
        # The newest leg still short is the one that was assigned.
        candidate_id = next((c for c in reversed(legs) if _leg_totals(session, c)[0] > 0), None)
    if candidate_id is None or candidate_id not in legs:
        return False
    contracts, leg_premium = _leg_totals(session, candidate_id)
    if strike is None:
        strike = session.execute(
            select(CandidateRow.strike).where(CandidateRow.candidate_id == candidate_id)
        ).scalar()
    if contracts <= 0 or strike is None:
        return False
    prior = sum(_leg_totals(session, c)[1] for c in legs[: legs.index(candidate_id)])
    shares = contracts * 100
    row.adjusted_cost_basis = round(float(strike) - (prior + leg_premium) / shares, 4)
    row.payload = {
        **(row.payload or {}),
        "assigned_candidate_id": candidate_id,
        "assignment_price": float(strike),
        "assigned_shares": shares,
        "prior_legs_premium": round(prior, 2),
    }
    return True


def mark_campaign_assigned(
    symbol: str,
    assignment_price: float | None = None,
    right: str | None = None,
    candidate_id: str | None = None,
) -> None:
    """Mark the open campaign for *symbol* as assigned and compute adjusted cost basis.

    adjusted_cost_basis = assignment_price − (premium of the campaign's legs up to the assigned
    one) / assigned shares — per share across every contract assigned (2026-10-13: it divided
    by 100, right only for a one-contract wheel). *candidate_id* names the assigned leg; without
    it the newest leg still short is taken.

    The ACB is only meaningful when shares are *acquired* — i.e. a short **put** assignment
    (``right`` is ``"P"`` or unknown). For a short **call** assignment (``right == "C"``) the
    shares are called *away*, so we flag the campaign assigned but leave the basis untouched.

    Called by the EOD reconciler (``orchestrator/eod_report.py``) for each assigned short.
    """
    try:
        with session_scope() as session:
            row = session.execute(
                select(CampaignRow)
                .where(CampaignRow.symbol == symbol, CampaignRow.status == "open")
                .order_by(CampaignRow.opened_date.desc())
                .limit(1)
            ).scalar_one_or_none()

            if row is None:
                return

            row.assigned = True
            acquires_shares = (right or "P").upper() != "C"
            if acquires_shares and assignment_price is not None:
                if not _record_assignment(session, row, candidate_id, assignment_price):
                    log.warning(
                        "mark_campaign_assigned: no assigned leg found for %s — basis not set",
                        symbol,
                    )
    except Exception:
        log.warning("mark_campaign_assigned failed for %s", symbol, exc_info=True)


def repair_assigned_bases() -> int:
    """Rebuild every assigned campaign's basis that has no assignment record — the rows the
    per-100 formula wrote before 2026-10-13. Idempotent; returns how many rows it fixed.
    Called from ``init_db``. Never raises."""
    fixed = 0
    try:
        with session_scope() as session:
            rows = (
                session.execute(
                    select(CampaignRow).where(
                        CampaignRow.assigned, CampaignRow.adjusted_cost_basis.is_not(None)
                    )
                )
                .scalars()
                .all()
            )
            for row in rows:
                if "assigned_shares" in (row.payload or {}):
                    continue
                old = row.adjusted_cost_basis
                if _record_assignment(session, row, None, None):
                    fixed += 1
                    log.warning(
                        "campaign %s: adjusted cost basis repaired %.4f → %.4f",
                        row.campaign_id,
                        old,
                        row.adjusted_cost_basis,
                    )
                else:
                    log.warning(
                        "campaign %s: basis %.4f predates the assignment record and its "
                        "assigned leg can't be found — left as is (the gate ignores it)",
                        row.campaign_id,
                        old,
                    )
    except Exception:
        log.warning("repair_assigned_bases failed", exc_info=True)
    return fixed


def load_campaigns(
    limit: int = 20,
    *,
    open_only: bool = False,
    since: date | None = None,
) -> list[dict]:
    """Return a list of campaign dicts ordered by opened_date descending.

    Each dict contains: campaign_id, symbol, status, opened_date, closed_date,
    leg_candidate_ids, leg_count, total_premium_collected, total_debit_paid,
    net_premium, assigned, adjusted_cost_basis, realized_stock_pnl.
    """
    try:
        with session_scope() as session:
            stmt = select(CampaignRow).order_by(CampaignRow.opened_date.desc()).limit(limit)
            if open_only:
                stmt = stmt.where(CampaignRow.status == "open")
            if since is not None:
                stmt = stmt.where(CampaignRow.opened_date >= since)
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "campaign_id": r.campaign_id,
                    "symbol": r.symbol,
                    "status": r.status,
                    "opened_date": r.opened_date,
                    "closed_date": r.closed_date,
                    "leg_candidate_ids": list(r.leg_candidate_ids or []),
                    "leg_count": len(r.leg_candidate_ids or []),
                    "total_premium_collected": r.total_premium_collected,
                    "total_debit_paid": r.total_debit_paid,
                    "net_premium": r.net_premium,
                    "assigned": r.assigned,
                    "adjusted_cost_basis": r.adjusted_cost_basis,
                    "realized_stock_pnl": r.realized_stock_pnl,
                }
                for r in rows
            ]
    except Exception:
        log.warning("load_campaigns failed", exc_info=True)
        return []


def whole_position_basis(
    prior_premiums: list[float], shares_held: float, avg_cost: float | None
) -> float | None:
    """The wheel-adjusted basis of every share held: IBKR's average cost (which already nets
    each assigned put's own premium) less the premium of the legs before each assignment,
    spread over all shares held. None when there's nothing to adjust or no position. Pure —
    the API's read-only route calls it too."""
    if not prior_premiums or avg_cost is None or shares_held <= 0:
        return None
    return round(avg_cost - sum(prior_premiums) / shares_held, 4)


def prior_legs_premium(payload: dict | None) -> float | None:
    """A campaign's ``prior_legs_premium``, or None before its assignment was recorded."""
    p = payload or {}
    if "assigned_shares" not in p:
        return None
    return float(p.get("prior_legs_premium") or 0.0)


def adjusted_cost_basis_for(
    symbol: str, *, shares_held: float, avg_cost: float | None
) -> float | None:
    """The wheel-adjusted per-share basis of the whole *symbol* position, or None.

    Every open, assigned campaign counts, not just the newest (2026-10-13), and the result
    is share-weighted over everything held, shares bought outright included — see
    ``whole_position_basis``. Without this reader the covered-call gate compared strikes to
    IBKR's raw ``avg_cost``, which misses premium from legs rolled before the assignment
    (D5).

    Never raises — a storage failure here must not break a scan.
    """
    try:
        with session_scope() as session:
            payloads = session.execute(
                select(CampaignRow.payload).where(
                    CampaignRow.symbol == symbol,
                    CampaignRow.status == "open",
                    CampaignRow.assigned,
                )
            ).scalars()
            priors = [p for p in (prior_legs_premium(x) for x in payloads) if p is not None]
        return whole_position_basis(priors, shares_held, avg_cost)
    except Exception:
        log.warning("adjusted_cost_basis_for failed for %s", symbol, exc_info=True)
        return None
