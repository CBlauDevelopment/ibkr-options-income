"""csp_engine_brain — SSRN-grounded CSP decision primitives.

Pure math + dataclasses. No network, no yfinance, no I/O. Consumed by
`src.strategies.csp_ssrn.evaluate_ssrn`, which feeds this with fork's live ib_async chain.

Research anchors (full methodology in ozgur-claude-workspace/knowledge-base/csp-*):
  - arxiv 2609.01183 — 0.30-delta / 45-DTE target
  - arxiv 2508.16598 — Kelly sizing on put-writing
  - CBOE PutWrite / Bondarenko 2019 — Sharpe 0.65 vs SPY 0.49 (1990-2022)
  - Filter citations inline in run_filters: Chen-Hong-Stein 2001, Amihud, Novy-Marx 2013,
    Dubinsky RFS 2019, Johnson 2017, Battalio 2016, MacLean-Thorp-Ziemba 2011.

Original standalone yfinance CLI (fetch_snapshot, pick_strike, evaluate, _cli) deleted
on port into this fork — its data path violates the deterministic-tier fence
("analytics/strategies/engine never call yfinance.* directly"). The brain's job here is
to score a chain fetched upstream by src.ibkr.market_data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from scipy.stats import norm

TIER_DELTA: dict[str, tuple[float, float, float]] = {
    "conservative": (0.15, 0.20, 0.175),
    "balanced":     (0.20, 0.30, 0.25),
    "aggressive":   (0.30, 0.40, 0.35),
}

DEFAULT_RISK_FREE = 0.045  # FRED 3-mo T-bill fallback.


# ---------- Black-Scholes ----------

def bs_put_delta(S: float, K: float, T_years: float, r: float, sigma: float) -> float:
    """Black-Scholes put delta, [-1, 0]. Guards degenerate inputs."""
    if T_years <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T_years) / (sigma * math.sqrt(T_years))
    return norm.cdf(d1) - 1.0


# ---------- Dataclasses ----------

@dataclass
class StockSnapshot:
    ticker: str
    spot: float
    market_cap: float | None
    adv_dollars: float | None
    gross_profit: float | None
    total_assets: float | None
    fcf: float | None
    earnings_date: datetime | None
    expirations: list[str] = field(default_factory=list)
    iv30: float | None = None
    iv90: float | None = None
    fetch_errors: list[str] = field(default_factory=list)


@dataclass
class StrikeChoice:
    expiration: str
    dte: int
    strike: float
    bid: float
    ask: float
    mid: float
    iv: float
    delta: float
    open_interest: int
    volume: int
    spread_pct: float
    pop_approx: float
    pop_hull_adj: float


@dataclass
class FilterResult:
    name: str
    status: str  # PASS / FAIL / FLAG / UNKNOWN
    reason: str


# ---------- 7 SSRN filters ----------

def run_filters(
    snap: StockSnapshot,
    strike: StrikeChoice | None,
    dte_window: tuple[int, int],
) -> list[FilterResult]:
    r: list[FilterResult] = []

    # 1. Market cap
    if snap.market_cap is None:
        r.append(FilterResult("market_cap", "UNKNOWN", "market cap data missing"))
    elif snap.market_cap >= 10e9:
        r.append(FilterResult("market_cap", "PASS", f"${snap.market_cap/1e9:.1f}B"))
    else:
        r.append(FilterResult("market_cap", "FAIL",
                              f"${snap.market_cap/1e9:.2f}B < $10B [Chen-Hong-Stein 2001]"))

    # 2. ADV
    if snap.adv_dollars is None:
        r.append(FilterResult("adv", "UNKNOWN", "volume data missing"))
    elif snap.adv_dollars >= 50e6:
        r.append(FilterResult("adv", "PASS", f"${snap.adv_dollars/1e6:.0f}M"))
    else:
        r.append(FilterResult("adv", "FAIL",
                              f"${snap.adv_dollars/1e6:.0f}M < $50M [Amihud/Battalio]"))

    # 3. Quality: GP/A OR FCF positive
    quality_signal: list[str] = []
    quality_pass = False
    if snap.gross_profit and snap.total_assets and snap.total_assets > 0:
        gpa = snap.gross_profit / snap.total_assets
        quality_signal.append(f"GP/A {gpa:.2f}")
        quality_pass = gpa >= 0.15
    if snap.fcf and snap.fcf > 0:
        quality_signal.append(f"FCF +${snap.fcf/1e9:.1f}B")
        quality_pass = True
    if quality_pass:
        r.append(FilterResult("quality", "PASS", "; ".join(quality_signal) or "quality OK"))
    elif not quality_signal:
        r.append(FilterResult("quality", "UNKNOWN", "fundamentals missing"))
    else:
        r.append(FilterResult("quality", "FAIL",
                              "; ".join(quality_signal) + " [Novy-Marx 2013 / QMJ]"))

    # 4. Earnings in window
    if snap.earnings_date is None:
        r.append(FilterResult("earnings", "UNKNOWN", "earnings date not available"))
    else:
        today = datetime.now(timezone.utc).replace(tzinfo=None)
        ed = snap.earnings_date.replace(tzinfo=None) if snap.earnings_date.tzinfo else snap.earnings_date
        days_to_earn = (ed - today).days
        if dte_window[0] <= days_to_earn <= dte_window[1]:
            r.append(FilterResult("earnings", "FAIL",
                f"earnings in {days_to_earn}d (inside DTE window) [Dubinsky et al. RFS 2019]"))
        elif 0 <= days_to_earn < dte_window[0]:
            r.append(FilterResult("earnings", "FLAG",
                f"earnings in {days_to_earn}d (before window — IV may be elevated)"))
        else:
            r.append(FilterResult("earnings", "PASS",
                f"next earnings in {days_to_earn}d (outside window)"))

    # 5. IV term structure (contango = IV30 < IV90)
    if snap.iv30 and snap.iv90:
        if snap.iv30 < snap.iv90:
            r.append(FilterResult("iv_term", "PASS",
                f"IV30 {snap.iv30:.1%} < IV90 {snap.iv90:.1%} (contango) [Johnson 2017]"))
        else:
            r.append(FilterResult("iv_term", "FLAG",
                f"IV30 {snap.iv30:.1%} >= IV90 {snap.iv90:.1%} (backwardation — negative short-vol EV)"))
    else:
        r.append(FilterResult("iv_term", "UNKNOWN", "IV term structure incomplete"))

    # 6/7. Options liquidity (requires strike)
    if strike is None:
        r.append(FilterResult("options_liquidity", "FAIL", "no viable strike in DTE window"))
    else:
        if strike.spread_pct <= 0.05:
            r.append(FilterResult("spread", "PASS", f"{strike.spread_pct:.1%} of mid"))
        else:
            r.append(FilterResult("spread", "FAIL",
                                  f"{strike.spread_pct:.1%} > 5% [Battalio et al. 2016]"))
        if strike.open_interest >= 500:
            r.append(FilterResult("open_interest", "PASS", f"OI {strike.open_interest}"))
        else:
            r.append(FilterResult("open_interest", "FAIL", f"OI {strike.open_interest} < 500"))

    return r


# ---------- Sizing + EV ----------

def size_position(
    equity: float,
    strike_price: float,
    max_pos_pct: float = 0.05,
    tail_loss_pct: float = 0.15,
) -> int:
    """Fractional-Kelly with left-tail cap [MacLean-Thorp-Ziemba 2011]."""
    collateral_per_contract = strike_price * 100.0
    max_loss_per_contract = collateral_per_contract * tail_loss_pct
    if max_loss_per_contract <= 0:
        return 0
    allowable_loss = equity * max_pos_pct
    return max(0, int(allowable_loss // max_loss_per_contract))


def expected_value(
    credit: float,
    pop: float,
    collateral: float,
    tail_loss_pct: float = 0.15,
) -> float:
    """Expected value per contract (credit × P(win) − tail × collateral × P(loss))."""
    win = pop * credit
    loss = (1.0 - pop) * tail_loss_pct * collateral
    return win - loss
