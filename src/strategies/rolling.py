"""Roll candidates for existing short option positions.

``construct_roll`` (2026-10-11 roll redesign) is the policy-driven builder: nearest later expiry
first, then the most favourable strike (lowest put / highest call) that clears the net-credit
floor without raising |delta|, with every rejection counted by reason code. Its inputs and
limits come from ``config/settings.yaml → roll:`` (``RollCfg``), the same object the Rules
Engine and the roll executor read. ``generate_roll_candidates`` is the pre-redesign generator,
kept only until its last callers move to ``roll_pipeline.evaluate_roll``.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from src.analytics.fair_value import compute_ideal_zone, zone_for_contract
from src.analytics.liquidity import liquidity_failures, passes_liquidity_gates, score_liquidity
from src.common.config import RollCfg, get_config
from src.common.market_hours import today_et
from src.common.schemas import (
    FundamentalStats,
    IdealZone,
    IVStats,
    OptionQuote,
    OptionRight,
    PositionSnapshot,
    RollOrigin,
    ScoreCard,
    Strategy,
    TechnicalStats,
    TradeCandidate,
)
from src.storage.roll_chains import RollChainState
from src.strategies._scoring import make_candidate_id, technical_score


def generate_roll_candidates(
    position: PositionSnapshot,
    quotes: list[OptionQuote],
    iv_stats: IVStats,
    tech_stats: TechnicalStats,
    *,
    defensive: bool = False,
) -> list[TradeCandidate]:
    """Return ranked roll candidates for the given short option *position*.

    Rolls are only generated when DTE <= 21 (nearing expiry) or |delta| > 0.40
    (delta drift). The intraday monitor (Phase 8) handles real-time triggering;
    this function just produces the candidates when asked.

    Two economics, deliberately separated (D4). An **income** roll rolls an unchallenged
    position forward for a credit and must clear the ROC/yield gates. A **defensive** roll
    rescues a challenged short and is judged on risk reduction instead: it may cost a bounded
    debit and must materially reduce |delta|. Requiring 1% ROC from a defensive roll meant the
    candidate list was empty exactly when the monitor fired, because a 0.60-delta short cannot
    be rolled to a 0.30-delta strike for a credit.
    """
    if position.position >= 0:
        return []
    if position.right is None or position.expiry is None or position.strike is None:
        return []

    pos_dte = (position.expiry - today_et()).days
    # get_positions carries no greeks, so fall back to the existing short's own chain quote —
    # with |delta| unknown, the defensive branch below rejected every candidate (2026-10-02).
    pos_delta = (
        position.delta if position.delta is not None else _infer_current_delta(position, quotes)
    )
    pos_delta_abs = abs(pos_delta) if pos_delta is not None else None

    should_roll = (pos_dte <= 21) or (pos_delta_abs is not None and pos_delta_abs > 0.40)
    if not should_roll:
        return []

    risk = get_config().risk
    leg_cfg = (
        risk["covered_call"] if position.right == OptionRight.CALL else risk["cash_secured_put"]
    )
    income_cfg = risk["income"]
    roll_cfg: dict[str, float | bool] = {}  # replaced by RollCfg in the Task 5 rewrite
    # Task 9 fix round 1 (R7): same treatment as the CSP/CC generators — a missing IV rank
    # already passes the IV gate as "data unavailable"; scoring it 0 under IV's weight
    # silently misrepresents the card. Neutral value from config (default 50), tagged so the
    # gap stays visible. Display-only here (rolls sort by roc_pct, never pass through
    # score_candidates or the score floor) but the ScoreCard line still misled the operator.
    missing_iv_rank_score: float = get_config().weights.get("missing_iv_rank_score", 50.0)

    delta_min: float = leg_cfg["delta_min"]
    delta_max: float = leg_cfg["delta_max"]
    dte_min: int = leg_cfg["dte_min"]
    dte_max: int = leg_cfg["dte_max"]

    contracts = abs(int(position.position))
    if contracts < 1:
        return []

    current_mid = _infer_current_mid(position, quotes)
    underlying = position.underlying or position.symbol

    candidates: list[TradeCandidate] = []
    # The ideal zone depends on (symbol, right, DTE) — not on the strike — so memoize per
    # expiry rather than recomputing it for every quote, matching the CSP/CC generators.
    zones: dict[int, IdealZone] = {}

    for quote in quotes:
        if quote.right != position.right:
            continue
        if quote.expiry <= position.expiry:
            continue
        if quote.delta is None:
            continue
        delta_abs = abs(quote.delta)
        if not (delta_min <= delta_abs <= delta_max):
            continue
        new_dte = quote.dte
        if not (dte_min <= new_dte <= dte_max):
            continue
        new_mid = quote.mid
        if new_mid is None or new_mid <= 0:
            continue
        if not passes_liquidity_gates(quote):
            continue

        if current_mid is None:
            continue
        roll_credit = new_mid - current_mid

        if defensive:
            max_debit = float(roll_cfg.get("max_debit", 0.50))
            min_reduction = float(roll_cfg.get("min_delta_reduction", 0.10))
            require_be = bool(roll_cfg.get("require_breakeven_improvement", True))
            if roll_credit < -max_debit:
                continue
            if pos_delta_abs is None or (pos_delta_abs - delta_abs) < min_reduction:
                continue
            if require_be and position.strike is not None:
                improves = (
                    quote.strike < position.strike
                    if position.right == OptionRight.PUT
                    else quote.strike > position.strike
                )
                if not improves and roll_credit <= 0:
                    continue
            roc_pct = 0.0
            annualized_yield_pct = 0.0
        else:
            if roll_credit <= 0:
                continue
            roc_basis = quote.strike
            roc_pct = (roll_credit / roc_basis) * 100 if roc_basis > 0 else 0.0
            annualized_yield_pct = roc_pct * (365 / new_dte) if new_dte > 0 else 0.0
            if roc_pct < income_cfg["min_roc_pct"]:
                continue
            if annualized_yield_pct < income_cfg["min_annualized_yield_pct"]:
                continue

        # Collateral = strike price × 100 × contracts (the cash actually at risk, not the
        # entry premium received which is ~100× smaller and produces fictitious 60%+ ROC
        # figures). Uses strike as the basis for both PUT and CALL rolls — for a covered-call
        # roll the underlying's actual cost basis is not available in this function.
        collateral = quote.strike * contracts * 100

        # D2 follow-up: populate `ideal` so a roll card shows the same fair-value context every
        # other candidate carries. It is DISPLAY/AUDIT for a roll — the risk engine's
        # variance-risk-premium gate is scoped to the income strategies, because a defensive
        # roll pays a debit to move a challenged short and is priced under the new strike's
        # fair value by design; leaving it inside that gate rejected every defensive roll at
        # the approval-queue re-gate. The defensive bounds above (max_debit /
        # min_delta_reduction / require_breakeven_improvement) are a roll's real economics.
        # No fundamentals are available in this function (no `FundamentalStats` input), so a
        # minimal symbol-only instance is used — `zone_for_contract`'s min_credit depends only
        # on `zone.spot`/`zone.dte`/`zone.right` (set from this call's own args, never touched
        # by `fund`) and the strike passed in below, never on fundamentals.
        zone = zones.get(new_dte)
        if zone is None:
            zone = compute_ideal_zone(
                symbol=underlying,
                right=position.right,
                dte=new_dte,
                spot=tech_stats.price,
                tech=tech_stats,
                iv=iv_stats,
                fund=FundamentalStats(symbol=underlying),
            )
            zones[new_dte] = zone
        # No cost_basis: this function has no access to the underlying's stock cost basis for
        # a covered-call roll (same limitation as `roc_basis` above), so `min_credit_for` falls
        # back to strike for both PUT and CALL rolls, consistent with the ROC treatment above.
        contract_zone = zone_for_contract(zone, quote.strike, iv_stats)

        breakeven = (
            quote.strike - roll_credit
            if position.right == OptionRight.PUT
            else quote.strike + roll_credit
        )

        scores = ScoreCard(
            symbol=underlying,
            iv_score=iv_stats.iv_rank if iv_stats.iv_rank is not None else missing_iv_rank_score,
            technical_score=technical_score(quote, tech_stats),
            fundamental_score=0.0,
            liquidity_score=score_liquidity(quote),
            assignment_safety_score=(1 - delta_abs) * 100,
        )

        candidates.append(
            TradeCandidate(
                candidate_id=make_candidate_id(
                    Strategy.ROLL, underlying, quote.right, quote.strike, quote.expiry
                ),
                strategy=Strategy.ROLL,
                underlying=underlying,
                right=quote.right,
                strike=quote.strike,
                expiry=quote.expiry,
                contracts=contracts,
                premium=round(roll_credit, 4),
                collateral=collateral,
                roc_pct=round(roc_pct, 4),
                annualized_yield_pct=round(annualized_yield_pct, 4),
                breakeven=round(breakeven, 4),
                prob_otm=round(1 - delta_abs, 4),
                delta=quote.delta,
                iv_rank=iv_stats.iv_rank,
                dte=new_dte,
                ideal=contract_zone,
                scores=scores,
                price_source=tech_stats.price_source,
                greeks_source=quote.greeks_source,
                # Merged into whatever tags this candidate already carries (currently none of
                # its own), matching the merge-not-replace contract `decision_engine.py`
                # applies downstream — never a bare replace.
                rationale_tags=["iv_rank_unavailable"] if iv_stats.iv_rank is None else [],
            )
        )

    candidates.sort(key=lambda c: c.roc_pct, reverse=True)
    return candidates


def _infer_current_mid(position: PositionSnapshot, quotes: list[OptionQuote]) -> float | None:
    """Find the current mid of the existing short by matching its contract in the chain.

    Returns None when no live quote is found — the caller must skip the candidate
    rather than use the stale entry cost, which would produce a misleadingly high
    roll credit on a challenged position.
    """
    for q in quotes:
        if (
            q.right == position.right
            and q.strike == position.strike
            and q.expiry == position.expiry
        ):
            m = q.mid
            if m is not None:
                return m
    return None


def _infer_current_delta(position: PositionSnapshot, quotes: list[OptionQuote]) -> float | None:
    """The existing short's delta from its own contract in the chain, or None."""
    for q in quotes:
        if (
            q.right == position.right
            and q.strike == position.strike
            and q.expiry == position.expiry
            and q.delta is not None
        ):
            return q.delta
    return None


# ---------------------------------------------------------------------------
# Policy-driven construction (2026-10-11 roll redesign)
# ---------------------------------------------------------------------------

_EPS = 1e-9  # float noise must not reject a roll sitting exactly on a floor


@dataclass(frozen=True)
class RollContext:
    """Everything ``construct_roll`` needs to know about the short being rolled."""

    position: PositionSnapshot
    current: OptionQuote  # live quote of the alerted contract itself
    spot: float | None
    chain: RollChainState
    closed_candidate_id: str | None  # the system candidate that sold the short, for the ledger
    next_earnings: date | None
    ex_div_date: date | None
    dividend: float | None  # next cash dividend $/sh
    allow_debit: bool  # a keep-shares covered-call roll may pay up to roll.cc.max_debit
    today: date


def construct_roll(
    ctx: RollContext,
    quotes: list[OptionQuote],
    iv_stats: IVStats,
    tech_stats: TechnicalStats,
    cfg: RollCfg,
) -> tuple[TradeCandidate | None, dict[str, int]]:
    """Return the roll to propose (or None) and a count of every rejection by reason code.

    Selection is lexicographic: the nearest later expiry that yields any qualifying strike
    wins; within it the most favourable strike does. A qualifying strike is same-or-better
    (put ≤ old, call ≥ old), liquid, priced, nets at least the floor (``min_net_credit``, or
    ``-cc.max_debit`` for a keep-shares call roll), does not raise |delta|, and — for a call
    expiring after an ex-date — keeps more extrinsic than the dividend plus the buffer. The
    expiry must stay before earnings, inside ``new_leg.target_dte_max`` and inside the chain's
    extension cap. A chain already at ``limits.max_rolls_per_chain`` inspects nothing.
    """
    rej: Counter[str] = Counter()
    pos = ctx.position
    assert pos.expiry is not None and pos.strike is not None and pos.right is not None
    if ctx.chain.seq >= cfg.limits.max_rolls_per_chain:
        return None, {"roll_limit_reached": 1}
    old_mid = ctx.current.strict_mid
    if old_mid is None or old_mid <= 0:
        return None, {"current_unpriced": 1}
    old_delta = abs(ctx.current.delta) if ctx.current.delta is not None else None
    floor = -cfg.cc.max_debit if ctx.allow_debit else cfg.new_leg.min_net_credit
    is_put = pos.right == OptionRight.PUT
    latest = ctx.chain.original_expiry + timedelta(days=cfg.limits.max_extension_days)

    by_expiry: dict[date, list[OptionQuote]] = defaultdict(list)
    for quote in quotes:
        if quote.right == pos.right and quote.expiry > pos.expiry:
            by_expiry[quote.expiry].append(quote)

    for expiry in sorted(by_expiry):
        group = by_expiry[expiry]
        if expiry > latest:
            rej["extension_cap"] += len(group)
            continue
        if (expiry - ctx.today).days > cfg.new_leg.target_dte_max:
            rej["dte_cap"] += len(group)
            continue
        if ctx.next_earnings is not None and ctx.next_earnings <= expiry:
            rej["earnings_before_expiry"] += len(group)
            continue
        for quote in sorted(group, key=lambda x: x.strike, reverse=not is_put):
            reason = _reject_reason(quote, ctx, old_mid, old_delta, floor, cfg)
            if reason is not None:
                rej[reason] += 1
                continue
            return _roll_candidate(quote, ctx, old_mid, iv_stats, tech_stats), dict(rej)
    return None, dict(rej)


def _reject_reason(
    quote: OptionQuote,
    ctx: RollContext,
    old_mid: float,
    old_delta: float | None,
    floor: float,
    cfg: RollCfg,
) -> str | None:
    pos = ctx.position
    assert pos.strike is not None
    is_put = pos.right == OptionRight.PUT
    if (quote.strike > pos.strike) if is_put else (quote.strike < pos.strike):
        return "strike_worse"
    new_mid = quote.strict_mid
    if new_mid is None or new_mid <= 0:
        return "unpriced"
    # Volume is an entry-quality filter; a roll re-places existing exposure, so only the
    # quote and open-interest gates apply to the new leg.
    failures = liquidity_failures(quote, enforce_volume=False)
    if failures:
        return failures[0]
    if new_mid - old_mid < floor - _EPS:
        return "net_below_floor"
    if quote.delta is None:
        return "delta_missing"
    if old_delta is not None and abs(quote.delta) > old_delta + _EPS:
        return "delta_increases"
    if (
        not is_put
        and ctx.ex_div_date is not None
        and ctx.dividend is not None
        and ctx.ex_div_date <= quote.expiry
    ):
        intrinsic = max(0.0, (ctx.spot or 0.0) - quote.strike)
        if new_mid - intrinsic < ctx.dividend + cfg.ex_div.buffer - _EPS:
            return "ex_div_assignment_risk"
    return None


def _roll_candidate(
    quote: OptionQuote,
    ctx: RollContext,
    old_mid: float,
    iv_stats: IVStats,
    tech_stats: TechnicalStats,
) -> TradeCandidate:
    pos = ctx.position
    assert pos.expiry is not None and pos.strike is not None and pos.right is not None
    new_mid = quote.strict_mid
    assert new_mid is not None
    underlying = pos.underlying or pos.symbol
    contracts = abs(int(pos.position))
    net = round(new_mid - old_mid, 4)
    new_dte = (quote.expiry - ctx.today).days
    delta_abs = abs(quote.delta) if quote.delta is not None else 0.0
    missing_iv_rank_score: float = get_config().weights.get("missing_iv_rank_score", 50.0)
    # Display/audit only for a roll (the Rules Engine scopes the fair-value gate to income
    # strategies); the card shows the new strike's zone like every other candidate.
    zone = compute_ideal_zone(
        symbol=underlying,
        right=pos.right,
        dte=new_dte,
        spot=tech_stats.price,
        tech=tech_stats,
        iv=iv_stats,
        fund=FundamentalStats(symbol=underlying),
    )
    breakeven = quote.strike - net if pos.right == OptionRight.PUT else quote.strike + net
    return TradeCandidate(
        candidate_id=make_candidate_id(
            Strategy.ROLL, underlying, quote.right, quote.strike, quote.expiry
        ),
        strategy=Strategy.ROLL,
        underlying=underlying,
        right=quote.right,
        strike=quote.strike,
        expiry=quote.expiry,
        contracts=contracts,
        premium=net,
        collateral=quote.strike * contracts * 100,
        roc_pct=0.0,
        annualized_yield_pct=0.0,
        breakeven=round(breakeven, 4),
        prob_otm=round(1 - delta_abs, 4),
        delta=quote.delta,
        iv_rank=iv_stats.iv_rank,
        dte=new_dte,
        next_earnings=ctx.next_earnings,
        ideal=zone_for_contract(zone, quote.strike, iv_stats),
        scores=ScoreCard(
            symbol=underlying,
            iv_score=iv_stats.iv_rank if iv_stats.iv_rank is not None else missing_iv_rank_score,
            technical_score=technical_score(quote, tech_stats),
            fundamental_score=0.0,
            liquidity_score=score_liquidity(quote),
            assignment_safety_score=(1 - delta_abs) * 100,
        ),
        price_source=tech_stats.price_source,
        greeks_source=quote.greeks_source,
        quote_bid=quote.bid,
        quote_ask=quote.ask,
        open_interest=quote.open_interest,
        option_volume=quote.volume,
        rationale_tags=["iv_rank_unavailable"] if iv_stats.iv_rank is None else [],
        roll_from=RollOrigin(
            con_id=pos.con_id,
            candidate_id=ctx.closed_candidate_id,
            strike=pos.strike,
            expiry=pos.expiry,
            right=pos.right,
            contracts=contracts,
            chain_id=ctx.chain.chain_id,
            seq=ctx.chain.seq + 1,
            original_expiry=ctx.chain.original_expiry,
            old_mid=old_mid,
            new_mid=new_mid,
            allow_debit=ctx.allow_debit,
        ),
    )
