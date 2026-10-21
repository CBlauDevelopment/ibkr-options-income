"""SSRN-grounded CSP screener.

Ports csp_engine.py (7 peer-reviewed filters, BS delta, fractional-Kelly sizing, EV gate)
onto this fork's live ib_async chain data — bypassing the brain's original yfinance snapshot.

Research anchors (see knowledge-base/csp-single-stock-methodology.md):
  - arxiv 2609.01183 — 0.30-delta / 45-DTE target
  - arxiv 2508.16598 — Kelly sizing on put-writing
  - CBOE PutWrite / Bondarenko 2019 — 32-yr Sharpe 0.65 vs SPY 0.49
  - Chen-Hong-Stein 2001, Amihud, Novy-Marx 2013, Dubinsky RFS 2019, Johnson 2017,
    Battalio 2016, MacLean-Thorp-Ziemba 2011 — individual filter citations in run_filters

Routed into screen_csp_candidates when config.strategy.csp.engine == "ssrn".
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.common.schemas import (
    AccountSnapshot,
    FundamentalStats,
    IVStats,
    OptionQuote,
    OptionRight,
    PositionSnapshot,
    ScoreCard,
    Strategy,
    TechnicalStats,
    TradeCandidate,
)
from src.strategies._evaluation import ScreenResult
from src.strategies._scoring import make_candidate_id
from src.strategies.csp_engine_brain import (
    DEFAULT_RISK_FREE,
    TIER_DELTA,
    FilterResult,
    StockSnapshot,
    StrikeChoice,
    expected_value,
    run_filters,
    size_position,
)


def _snapshot_from_fork(
    symbol: str,
    spot: float,
    iv_stats: IVStats,
    tech_stats: TechnicalStats,
    fund_stats: FundamentalStats,
) -> StockSnapshot:
    """Fork's pre-fetched state → brain's StockSnapshot shape.

    IV30/IV90 term structure: fork carries current_iv but not a near/far split; the brain's
    iv_term filter degrades to UNKNOWN when either leg is None, which is correct (no
    fabricated contango signal). When the fork's chain-fetch later yields multiple
    expirations we can backfill from option quotes directly — see _derive_term_from_quotes.
    """
    return StockSnapshot(
        ticker=symbol.upper(),
        spot=spot,
        market_cap=getattr(fund_stats, "market_cap", None),
        adv_dollars=getattr(fund_stats, "adv_dollars", None),
        gross_profit=getattr(fund_stats, "gross_profit", None),
        total_assets=getattr(fund_stats, "total_assets", None),
        fcf=getattr(fund_stats, "free_cash_flow", None) or getattr(fund_stats, "fcf", None),
        earnings_date=getattr(fund_stats, "next_earnings", None)
        or getattr(fund_stats, "earnings_date", None),
        expirations=[],
        iv30=(iv_stats.current_iv / 100.0) if iv_stats.current_iv else None,
        iv90=None,
        fetch_errors=[],
    )


def _derive_term_from_quotes(quotes: list[OptionQuote]) -> tuple[float | None, float | None]:
    """Pick ATM-ish IV at ~30 and ~90 DTE from the chain the fork already fetched.

    No new network calls — pure walk of what ib_async already handed us.
    """
    today = datetime.now(timezone.utc).date()
    puts = [q for q in quotes if q.right == OptionRight.PUT and q.iv]
    if not puts:
        return None, None
    by_dte: dict[int, list[OptionQuote]] = {}
    for q in puts:
        d = (q.expiry - today).days
        by_dte.setdefault(d, []).append(q)

    def pick(target: int) -> float | None:
        if not by_dte:
            return None
        nearest_dte = min(by_dte, key=lambda d: abs(d - target))
        bucket = by_dte[nearest_dte]
        spot = next((q.underlying_price for q in bucket if q.underlying_price), None)
        if not spot:
            return None
        atm = min(bucket, key=lambda q: abs(q.strike - spot))
        return atm.iv

    return pick(30), pick(90)


def _pick_strike_from_quotes(
    quotes: list[OptionQuote],
    delta_target: float,
    delta_lo: float,
    delta_hi: float,
    dte_min: int,
    dte_max: int,
) -> StrikeChoice | None:
    """Walk live chain for the put closest to delta_target within [dte_min, dte_max]."""
    cands: list[StrikeChoice] = []
    for q in quotes:
        if q.right != OptionRight.PUT:
            continue
        if not (dte_min <= q.dte <= dte_max):
            continue
        if q.delta is None or q.mid is None or q.bid is None or q.ask is None:
            continue
        abs_delta = abs(q.delta)
        if not (delta_lo <= abs_delta <= delta_hi):
            continue
        spread_pct = (q.ask - q.bid) / q.mid if q.mid > 0 else 1.0
        pop = 1.0 - abs_delta  # P(OTM) ≈ 1 − |Δ|
        pop_hull = max(0.0, min(1.0, pop - 0.03))  # mild Hull adjustment
        cands.append(
            StrikeChoice(
                expiration=q.expiry.isoformat(),
                dte=q.dte,
                strike=q.strike,
                bid=q.bid,
                ask=q.ask,
                mid=q.mid,
                iv=q.iv or 0.0,
                delta=abs_delta,
                open_interest=q.open_interest or 0,
                volume=q.volume or 0,
                spread_pct=spread_pct,
                pop_approx=pop,
                pop_hull_adj=pop_hull,
            )
        )
    if not cands:
        return None
    return min(cands, key=lambda s: abs(s.delta - delta_target))


def _as_trade_candidate(
    symbol: str,
    strike: StrikeChoice,
    contracts: int,
    account: AccountSnapshot,
    iv_stats: IVStats,
    filters: list[FilterResult],
    ev_per: float,
) -> TradeCandidate:
    collateral = strike.strike * 100.0
    credit = strike.mid * 100.0
    roc_pct = (credit / collateral * 100.0) if collateral else 0.0
    annualized = roc_pct * (365.0 / max(strike.dte, 1))
    tags = [f"{f.name}:{f.status}" for f in filters]
    tags.append(f"ssrn_ev={ev_per:.2f}")
    expiry = datetime.strptime(strike.expiration, "%Y-%m-%d").date()
    return TradeCandidate(
        candidate_id=make_candidate_id(
            Strategy.CASH_SECURED_PUT, symbol, OptionRight.PUT, strike.strike, expiry
        ),
        strategy=Strategy.CASH_SECURED_PUT,
        underlying=symbol.upper(),
        right=OptionRight.PUT,
        strike=strike.strike,
        expiry=expiry,
        contracts=max(contracts, 1),
        premium=strike.mid,
        collateral=collateral,
        roc_pct=roc_pct,
        annualized_yield_pct=annualized,
        breakeven=strike.strike - strike.mid,
        prob_otm=strike.pop_hull_adj,
        delta=-strike.delta,
        iv_rank=iv_stats.iv_rank,
        current_iv=iv_stats.current_iv,
        vrp=iv_stats.vrp,
        iv_rv_ratio=iv_stats.iv_rv_ratio,
        dte=strike.dte,
        scores=ScoreCard(technical=0.0, fundamental=0.0, relative_strength=0.0, blended=0.0),
        blended_score=max(0.0, ev_per),
        rationale_tags=tags,
        price_source="ibkr",
        greeks_source="ibkr",
        quote_bid=strike.bid,
        quote_ask=strike.ask,
        open_interest=strike.open_interest,
        option_volume=strike.volume,
    )


def evaluate_ssrn(
    symbol: str,
    quotes: list[OptionQuote],
    account: AccountSnapshot,
    iv_stats: IVStats,
    tech_stats: TechnicalStats,
    fund_stats: FundamentalStats,
    *,
    positions: list[PositionSnapshot] | None = None,
    tier: str = "balanced",
    dte_min: int = 30,
    dte_max: int = 45,
    risk_free: float = DEFAULT_RISK_FREE,
) -> ScreenResult:
    """SSRN-grounded CSP screener on fork's live chain data.

    Returns ScreenResult; .passed non-empty iff all hard SSRN gates pass AND a strike exists
    at target delta/DTE AND fractional-Kelly size ≥ 1 contract AND EV > 0.
    """
    if tier not in TIER_DELTA:
        raise ValueError(f"tier must be one of {list(TIER_DELTA)}")
    delta_lo, delta_hi, delta_target = TIER_DELTA[tier]

    put_count = sum(1 for q in quotes if q.right == OptionRight.PUT)
    if put_count == 0:
        return ScreenResult(evaluated=0, skipped="no put quotes available")

    snap = _snapshot_from_fork(symbol, tech_stats.price, iv_stats, tech_stats, fund_stats)
    iv30, iv90 = _derive_term_from_quotes(quotes)
    if iv30:
        snap.iv30 = iv30
    if iv90:
        snap.iv90 = iv90

    strike = _pick_strike_from_quotes(quotes, delta_target, delta_lo, delta_hi, dte_min, dte_max)
    filters = run_filters(snap, strike, (dte_min, dte_max))

    hard_fail = any(f.status == "FAIL" for f in filters)
    equity = getattr(account, "net_liquidation", None) or getattr(account, "equity", 0.0)

    if strike is None:
        return ScreenResult(
            evaluated=put_count,
            skipped=f"no viable strike in Δ[{delta_lo:.2f},{delta_hi:.2f}] × DTE[{dte_min},{dte_max}]",
        )

    if hard_fail:
        reasons = [f"ssrn:{f.name}" for f in filters if f.status == "FAIL"]
        dummy = _as_trade_candidate(symbol, strike, 0, account, iv_stats, filters, 0.0)
        return ScreenResult(evaluated=put_count, rejected=[(dummy, reasons)])

    contracts = size_position(equity, strike.strike)
    if contracts < 1:
        dummy = _as_trade_candidate(symbol, strike, 0, account, iv_stats, filters, 0.0)
        return ScreenResult(evaluated=put_count, rejected=[(dummy, ["ssrn:kelly_size_zero"])])

    credit_per = strike.mid * 100.0
    collateral_per = strike.strike * 100.0
    ev_per = expected_value(credit_per, strike.pop_hull_adj, collateral_per)
    if ev_per <= 0:
        dummy = _as_trade_candidate(symbol, strike, contracts, account, iv_stats, filters, ev_per)
        return ScreenResult(evaluated=put_count, rejected=[(dummy, ["ssrn:ev_negative"])])

    cand = _as_trade_candidate(symbol, strike, contracts, account, iv_stats, filters, ev_per)
    return ScreenResult(evaluated=put_count, passed=[cand])
