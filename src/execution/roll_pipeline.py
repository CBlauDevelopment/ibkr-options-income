"""Turn a roll trigger into an approvable roll candidate (N20), and the shared chain-fetch path.

The intraday monitor fires a `RollAlert` when a short option breaches its delta/DTE/IV limits.
Historically that was alert-only — `generate_roll_candidates` had no production caller and
`execute_roll` was unreachable. This module closes the gap: given the triggered position and a
fresh chain, it generates the best roll candidate, persists it as a `CandidateRow`, and raises a
PENDING `ApprovalRow` (with the frozen snapshot, N2a). The existing Telegram Approve handler then
creates a QUEUED ROLL `OrderRow`, which `process_queued_orders` → `execute_candidate` routes to
`execute_roll` (the two-leg BAG combo).

Since M5 Task 5.1, this module also owns `fetch_roll_inputs` — the single chain-fetch path shared
by the monitor's `_try_queue_roll` and the command drain's `roll_request` handler. The milestone
is explicit that the web path must not build a second chain-fetch path; the helper is the
structural expression of that. `queue_roll_for_approval` itself stays deterministic and
synchronous (the caller fetches via `fetch_roll_inputs` then calls it) — the DB write half is
unchanged. Returns the approval id + candidate so the caller can attach the inline keyboard.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from ib_async import IB

from src.analytics.fundamentals import get_fundamental_stats
from src.analytics.iv import get_iv_stats
from src.analytics.technicals import get_technical_stats
from src.common.config import get_config
from src.common.market_hours import today_et
from src.common.schemas import (
    ApprovalStatus,
    IVStats,
    OptionQuote,
    OptionRight,
    OrderState,
    PositionSnapshot,
    RollDecision,
    TechnicalStats,
    TradeCandidate,
    Verdict,
)
from src.common.universe import effective_universe, is_leveraged_etf
from src.engine.risk_engine import validate_candidates
from src.ibkr.market_data import get_roll_chain_quotes_async
from src.ibkr.portfolio import get_account_snapshot_async, get_positions
from src.storage.campaigns import adjusted_cost_basis_for
from src.storage.db import session_scope
from src.storage.models import ApprovalRow, CandidateRow, OrderRow
from src.storage.orders import has_active_order
from src.storage.roll_chains import chain_state
from src.strategies.roll_policy import decide
from src.strategies.rolling import RollContext, generate_roll_candidates

log = logging.getLogger(__name__)


async def fetch_roll_inputs(
    ib: IB, position: PositionSnapshot
) -> tuple[list[OptionQuote], IVStats, TechnicalStats]:
    """Fetch the chain + IV/technical stats a roll proposal is priced from.

    The one chain-fetch path for roll pricing, shared by the intraday monitor's
    ``_try_queue_roll`` and the command drain's ``roll_request`` handler (M5 Task 5.1:
    "Do not build a second chain-fetch path"). Composes the exact three helpers the monitor
    used to inline — ``get_option_chain_quotes_async`` (async, IBKR), ``get_iv_stats`` and
    ``get_technical_stats`` (blocking, yfinance-backed, so offloaded to the default executor
    to avoid stalling the event loop the drain runs on). Raises whatever the fetch raises;
    the caller decides how to report it (the monitor swallows into an alert-only fallback,
    the drain handler maps it to ``chain_unavailable``). An empty-but-successful chain is
    returned as ``([], iv, tech)`` — the caller treats that as a data outage, not an
    economic answer.
    """
    from src.analytics.iv import get_iv_stats
    from src.analytics.technicals import get_technical_stats
    from src.ibkr.market_data import get_option_chain_quotes_async

    underlying = position.underlying or position.symbol
    quotes = await get_option_chain_quotes_async(ib, underlying)
    loop = asyncio.get_running_loop()
    iv_stats = await loop.run_in_executor(None, get_iv_stats, underlying, quotes)
    tech_stats = await loop.run_in_executor(None, get_technical_stats, underlying)
    return quotes, iv_stats, tech_stats


def queue_roll_for_approval(
    position: PositionSnapshot,
    quotes: list[OptionQuote],
    iv_stats: IVStats,
    tech_stats: TechnicalStats,
    *,
    chat_id: str,
    ttl_minutes: int,
) -> tuple[int, TradeCandidate] | None:
    """Generate the best roll candidate for *position* and raise a PENDING approval for it.

    Returns ``(approval_id, candidate)`` so the caller can send an Approve/Reject message, or
    None when there is no qualifying roll or an order is already working for that candidate
    (idempotent against the monitor re-firing the same trigger). Never raises.
    """
    try:
        candidates = generate_roll_candidates(
            position, quotes, iv_stats, tech_stats, defensive=True
        )
        if not candidates:
            return None
        approval_id = queue_roll_candidate(candidates[0], chat_id=chat_id, ttl_minutes=ttl_minutes)
        return (approval_id, candidates[0]) if approval_id is not None else None
    except Exception:
        log.exception("roll: failed to queue roll candidate for %s", position.symbol)
        return None


def queue_roll_candidate(cand: TradeCandidate, *, chat_id: str, ttl_minutes: int) -> int | None:
    """Persist *cand* and raise a PENDING approval for it (frozen snapshot, N2a).

    None when an order is already working for the candidate. Never raises.
    """
    try:
        with session_scope() as s:
            if has_active_order(s, cand.candidate_id):
                log.info("roll: active order already exists for %s — skipping", cand.candidate_id)
                return None

            # Upsert the candidate payload (same semantics as the scan persister).
            existing = (
                s.query(CandidateRow).filter(CandidateRow.candidate_id == cand.candidate_id).first()
            )
            if existing is not None:
                s.delete(existing)
                s.flush()
            snapshot = cand.model_dump(mode="json")
            s.add(
                CandidateRow(
                    candidate_id=cand.candidate_id,
                    run_id=f"roll-{uuid.uuid4().hex[:8]}",
                    strategy=cand.strategy.value,
                    underlying=cand.underlying,
                    right=cand.right.value,
                    strike=cand.strike,
                    expiry=cand.expiry,
                    blended_score=cand.blended_score,
                    payload=snapshot,
                )
            )
            approval = ApprovalRow(
                candidate_id=cand.candidate_id,
                status=ApprovalStatus.PENDING,
                chat_id=chat_id,
                expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
                snapshot=snapshot,  # freeze the approved payload (N2a)
            )
            s.add(approval)
            s.flush()
            approval_id = approval.id
        log.info(
            "roll: queued candidate %s for approval (approval_id=%s)",
            cand.candidate_id,
            approval_id,
        )
        return approval_id
    except Exception:
        log.exception("roll: failed to queue roll candidate %s", cand.candidate_id)
        return None


# ---------------------------------------------------------------------------
# evaluate_roll (2026-10-11 roll redesign)
# ---------------------------------------------------------------------------


def _same_short(snapshot: dict | None, pos: PositionSnapshot) -> bool:
    """True when a frozen ROLL snapshot closes *pos* (by conId, else by contract)."""
    if not snapshot or snapshot.get("strategy") != "roll":
        return False
    origin = snapshot.get("roll_from") or {}
    if pos.con_id is not None and origin.get("con_id") is not None:
        return bool(origin["con_id"] == pos.con_id)
    return (
        snapshot.get("underlying") == (pos.underlying or pos.symbol)
        and origin.get("right") == (pos.right.value if pos.right else None)
        and abs(float(origin.get("strike") or 0.0) - (pos.strike or 0.0)) < 1e-3
        and origin.get("expiry") == (pos.expiry.isoformat() if pos.expiry else None)
    )


def pending_roll_approval_for(pos: PositionSnapshot) -> int | None:
    """Id of a PENDING roll approval — or the approval behind a working roll order — for *pos*.

    The monitor re-evaluates a breached short every ``roll.trigger.reevaluate_minutes``; this
    is what stops each re-evaluation from proposing the same roll again.
    """
    with session_scope() as s:
        pending = s.query(ApprovalRow).filter(ApprovalRow.status == ApprovalStatus.PENDING).all()
        for row in pending:
            if _same_short(row.snapshot, pos):
                return int(row.id)
        working = (
            s.query(OrderRow)
            .filter(
                OrderRow.state.in_([OrderState.QUEUED, OrderState.SUBMITTED, OrderState.PARTIAL])
            )
            .all()
        )
        for order in working:
            if _same_short(order.snapshot, pos):
                return int(order.approval_id) if order.approval_id is not None else -1
    return None


def _gate_fallback(
    decision: RollDecision, pos: PositionSnapshot, cc_basis: float | None, reasons: list[str]
) -> RollDecision:
    """The decision when the Rules Engine refuses a constructed roll: the no-roll branch."""
    reason = "rules_engine:" + ",".join(reasons)
    strike = pos.strike or 0.0
    if pos.right == OptionRight.PUT:
        action = "assign"
        detail = f"Rules Engine refused the roll ({', '.join(reasons)}) — letting it assign."
    elif cc_basis is None or strike >= cc_basis:
        action = "let_called_away"
        detail = f"Rules Engine refused the roll ({', '.join(reasons)}) — letting the shares go."
    else:
        action = "hold"
        detail = f"Rules Engine refused the roll ({', '.join(reasons)}) — holding below basis."
    return RollDecision(
        action=action,  # type: ignore[arg-type]
        reason=reason,
        rejections=decision.rejections,
        detail=detail,
    )


async def evaluate_roll(
    ib: IB,
    pos: PositionSnapshot,
    *,
    chat_id: str,
    ttl_minutes: int,
    manual: bool = False,
) -> tuple[RollDecision, int | None]:
    """Decide what to do with one breached short; queue an approval when the answer is a roll.

    Targeted fetch (the alerted contract + a few same-or-better later strikes) → chain state,
    fundamentals and basis → ``roll_policy.decide`` → for a ``roll``, a decision-time Rules
    Engine pass (the first of three: this one, the approval-queue re-gate, and the executor's
    send-time check) → a PENDING approval. Returns the decision and the approval id (or the
    id of the roll already pending for this short). *manual* marks an operator-requested
    evaluation (web ``roll_request``) in the log; the policy is the same. Never raises.
    """
    underlying = pos.underlying or pos.symbol
    existing = pending_roll_approval_for(pos)
    if existing is not None:
        decision = RollDecision(
            action="defer",
            reason="roll_pending",
            detail="A roll for this short is already awaiting approval or working.",
        )
        return decision, existing

    cfg = get_config()
    rc = cfg.roll
    approval_id: int | None = None
    try:
        quotes = await get_roll_chain_quotes_async(
            ib,
            pos,
            max_expiries=rc.new_leg.max_expiries,
            target_dte_max=rc.new_leg.target_dte_max,
            strikes_outward=rc.new_leg.strikes_outward,
            batch_size=rc.new_leg.max_quote_lines,
        )
    except Exception:
        log.exception("roll: chain fetch failed for %s", underlying)
        quotes = []
    if not quotes:
        decision = RollDecision(
            action="defer",
            reason="chain_unavailable",
            detail="The roll chain fetch returned nothing — retrying next cycle.",
        )
        _log_decision(pos, decision, manual)
        return decision, None
    current = next(
        (
            q
            for q in quotes
            if q.right == pos.right
            and q.expiry == pos.expiry
            and abs(q.strike - (pos.strike or 0)) < 1e-3
        ),
        None,
    )
    if current is None:
        decision = RollDecision(
            action="defer",
            reason="current_unpriced",
            detail="No quote for the short itself — retrying next cycle.",
        )
        _log_decision(pos, decision, manual)
        return decision, None

    loop = asyncio.get_running_loop()
    iv_stats = await loop.run_in_executor(None, get_iv_stats, underlying, quotes)
    tech_stats = await loop.run_in_executor(None, get_technical_stats, underlying)
    fund = await loop.run_in_executor(None, get_fundamental_stats, underlying)
    positions = get_positions(ib)
    with session_scope() as s:
        chain = chain_state(s, pos)
    stock = next(
        (p for p in positions if p.sec_type == "STK" and (p.underlying or p.symbol) == underlying),
        None,
    )
    cc_basis = adjusted_cost_basis_for(underlying) or (stock.avg_cost if stock else None)
    would_own = underlying.upper() in {
        str(x).upper() for x in (effective_universe().get("would_own") or [])
    }
    ctx = RollContext(
        position=pos,
        current=current,
        spot=current.underlying_price or tech_stats.price,
        chain=chain,
        closed_candidate_id=chain.current_candidate_id,
        next_earnings=fund.next_earnings,
        ex_div_date=fund.ex_dividend_date,
        dividend=fund.dividend_per_share,
        allow_debit=False,
        today=today_et(),
    )
    decision = decide(
        ctx,
        quotes,
        iv_stats,
        tech_stats,
        rc,
        is_leveraged=is_leveraged_etf(underlying),
        would_own=would_own,
        cc_basis=cc_basis,
    )

    cand = decision.candidate
    if decision.action == "roll" and cand is not None:
        account = await get_account_snapshot_async(ib, cfg.secrets.ibkr_account)
        verdict = validate_candidates([cand], account, positions)[0]
        if verdict.verdict != Verdict.PASS:
            decision = _gate_fallback(decision, pos, cc_basis, list(verdict.reasons))
        else:
            approval_id = queue_roll_candidate(cand, chat_id=chat_id, ttl_minutes=ttl_minutes)
    _log_decision(pos, decision, manual)
    return decision, approval_id


def _log_decision(pos: PositionSnapshot, decision: RollDecision, manual: bool) -> None:
    log.info(
        "roll decision: %s %s:%s%s rejections=%s",
        pos.symbol,
        decision.action,
        decision.reason,
        " (manual)" if manual else "",
        decision.rejections,
    )
