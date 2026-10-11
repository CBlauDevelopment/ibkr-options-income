"""Roll-chain bookkeeping read from candidates + fills (2026-10-11 roll redesign). Read-only.

A roll's new candidate carries ``payload["roll_from"]`` (a ``RollOrigin``) naming the short it
closed, so a chain is walked backwards through candidate ids. There is no table of its own: the
chain is derived from rows the executor already writes. Consumers: the roll policy (how many
rolls a chain has used, how far it has been extended) and the profit-take / loss line, which
measure the whole chain's net credit rather than the new leg's gross premium — a roll's buyback
is a realised loss, not secured gain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.common.schemas import PositionSnapshot, RollOrigin
from src.storage.models import CandidateRow, FillRow

_MAX_WALK = 20  # a malformed self-referencing payload must not loop forever


@dataclass(frozen=True)
class RollChainState:
    seq: int  # rolls already made in this chain (0 = never rolled)
    chain_id: str
    original_expiry: date  # the first leg's expiry — anchor for the extension cap
    current_candidate_id: str | None  # the system candidate that sold the open short


def synthetic_close_id(underlying: str, expiry: date, strike: float, right: str) -> str:
    """The candidate id a roll's BUY fill is booked under when the closed short was not sold by
    this system (opened by hand in TWS) — shared by the executor and the chain walk."""
    return f"roll-close:{underlying}:{expiry:%Y%m%d}:{strike:g}:{right}"


def _sold_candidate(session: Session, pos: PositionSnapshot) -> CandidateRow | None:
    """The candidate whose SELL fill opened *pos* (latest sale wins), or None."""
    assert pos.strike is not None and pos.expiry is not None and pos.right is not None
    rows = (
        session.execute(
            select(CandidateRow)
            .join(FillRow, FillRow.candidate_id == CandidateRow.candidate_id)
            .where(
                CandidateRow.underlying == (pos.underlying or pos.symbol),
                CandidateRow.right == pos.right.value,
                CandidateRow.expiry == pos.expiry,
                FillRow.action == "SELL",
            )
            .order_by(FillRow.filled_at.desc())
        )
        .scalars()
        .all()
    )
    return next((c for c in rows if abs((c.strike or 0.0) - pos.strike) < 1e-3), None)


def _origin(row: CandidateRow) -> RollOrigin | None:
    raw = (row.payload or {}).get("roll_from")
    return RollOrigin.model_validate(raw) if raw else None


def _by_id(session: Session, candidate_id: str) -> CandidateRow | None:
    return session.execute(
        select(CandidateRow).where(CandidateRow.candidate_id == candidate_id)
    ).scalar_one_or_none()


def chain_state(session: Session, pos: PositionSnapshot) -> RollChainState:
    """Where *pos* sits in its roll chain. A short with no system sale is seq 0, synthetic id."""
    assert pos.expiry is not None
    row = _sold_candidate(session, pos)
    if row is None:
        synthetic = f"chain:{pos.underlying or pos.symbol}:{pos.expiry:%Y%m%d}:{pos.strike:g}"
        return RollChainState(0, synthetic, pos.expiry, None)
    origin = _origin(row)
    if origin is None:
        return RollChainState(0, row.candidate_id, pos.expiry, row.candidate_id)
    return RollChainState(origin.seq, origin.chain_id, origin.original_expiry, row.candidate_id)


def chain_entry_credit_per_share(session: Session, pos: PositionSnapshot) -> float | None:
    """Net credit per share collected over the whole chain, spread over the open contracts.

    All SELL credits − all BUY debits − all commissions across every leg of the chain, divided
    by the open leg's sold quantity × 100. For a short that was never rolled this equals
    ``profit_take.net_entry_credit_per_share``. None when the short has no system SELL fill or
    the chain is net-debit (nothing left to take profit on).
    """
    row = _sold_candidate(session, pos)
    if row is None:
        return None
    ids: list[str] = []
    cur: CandidateRow | None = row
    while cur is not None and len(ids) < _MAX_WALK and cur.candidate_id not in ids:
        ids.append(cur.candidate_id)
        origin = _origin(cur)
        if origin is not None and not origin.candidate_id:
            # The first leg was sold outside the system; its buy-back is booked under the
            # synthetic id, and only that debit is known — the chain is the debit plus the new
            # credit, never the new leg's gross premium alone.
            ids.append(
                synthetic_close_id(cur.underlying, origin.expiry, origin.strike, origin.right.value)
            )
            break
        cur = _by_id(session, origin.candidate_id) if origin and origin.candidate_id else None
    fills = [
        f
        for f in session.execute(select(FillRow).where(FillRow.candidate_id.in_(ids))).scalars()
        # A BUY on the open leg itself is a partial close of this position, not a cost of the
        # chain: counting it shrank the remaining contracts' credit (review, 2026-10-11).
        if not ((f.action or "SELL").upper() == "BUY" and f.candidate_id == row.candidate_id)
    ]
    dollars = sum(
        (-1.0 if (f.action or "SELL").upper() == "BUY" else 1.0) * f.avg_price * f.filled_qty * 100
        for f in fills
    )
    dollars -= sum(f.commission or 0.0 for f in fills)
    qty = sum(
        f.filled_qty
        for f in fills
        if (f.action or "SELL").upper() == "SELL" and f.candidate_id == row.candidate_id
    )
    if qty <= 0:
        return None
    per_share = dollars / (qty * 100)
    return per_share if per_share > 0 else None
