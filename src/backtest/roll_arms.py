"""Offline comparison of what to do at a strike breach: assign, roll or close (2026-10-11).

The roll redesign's policy rests on thin, index-only evidence (docs/research/2026-10-11-
rolling-short-options.md). This harness measures the three arms on a symbol's own price history
so a human can judge the policy — it never feeds it (eval fence: thresholds stay human-edited).

Per non-overlapping cycle: sell a ``target_delta`` short at ``dte`` days, priced by
Black-Scholes at trailing HV30. If the stock goes through the strike within ``breach_dte`` days
of expiry, the cycle is a breach and all three arms are valued to the same horizon — the old
expiry plus ``roll_dte`` days:

* ``assign`` — hold to expiry. A put that finishes ITM is assigned at the strike and a call at
  the same delta is sold to the horizon (the wheel's own repair); a call that finishes ITM is
  called away (shares sold at the strike, cash to the horizon).
* ``roll`` — at the breach, buy back and sell the same strike to the horizon (the roll the
  evidence favours), when the net clears ``min_net_credit`` (``-max_debit`` for a call).
  Otherwise it falls back to ``assign``, flagged ``fell_back``.
* ``close`` — buy back at the breach; flat (cash, or for a call, just the shares) to the horizon.

Calls carry the shares bought at the cycle's entry, so every call arm includes the stock's P&L.
European Black-Scholes at HV30, no skew, no early exercise, no bid/ask: indicative only.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field, replace
from datetime import date

from src.analytics.black_scholes import bs_price
from src.backtest.engine import _HV_WINDOW, _find_expiry_idx, _strike_for_delta, _trailing_hv

_ARMS = ("assign", "roll", "close")


@dataclass(frozen=True)
class ArmOutcome:
    entry_date: date
    breach_date: date
    horizon_date: date
    pnl: float  # dollars per contract, net of commissions
    strike: float
    entry_premium: float
    buyback: float  # BS value of the short at the breach
    spot_at_breach: float
    days_left_at_breach: int
    iv_at_breach: float
    fell_back: bool = False  # roll arm only: no qualifying roll, valued as assign


@dataclass
class RollArmsResult:
    cycles: int = 0
    breaches: int = 0
    arms: dict[str, list[ArmOutcome]] = field(default_factory=lambda: {a: [] for a in _ARMS})

    def summary(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for arm, rows in self.arms.items():
            pnls = sorted(r.pnl for r in rows)
            if not pnls:
                out[arm] = {"n": 0.0}
                continue
            tail = pnls[: max(1, len(pnls) // 20)]
            out[arm] = {
                "n": float(len(pnls)),
                "mean": statistics.fmean(pnls),
                "median": statistics.median(pnls),
                "cvar5": statistics.fmean(tail),
                "win_rate": sum(p > 0 for p in pnls) / len(pnls),
            }
        return out


def _price(spot: float, strike: float, days: int, iv: float, right: str, r: float) -> float:
    if days <= 0:
        return max(0.0, strike - spot) if right == "P" else max(0.0, spot - strike)
    return bs_price(spot, strike, days, iv, right, r) or 0.0


def simulate_breach_arms(
    closes: list[float],
    dates: list[date],
    *,
    right: str,
    target_delta: float,
    dte: int,
    roll_dte: int,
    breach_dte: int,
    min_net_credit: float,
    max_debit: float,
    risk_free_rate: float,
    commission: float,
) -> RollArmsResult:
    """Walk *closes* in non-overlapping cycles and value every breach under all three arms."""
    res = RollArmsResult()
    r = risk_free_rate
    i = _HV_WINDOW
    n = len(closes)
    while i < n:
        iv = _trailing_hv(closes, i)
        if iv is None:
            i += 1
            continue
        s0 = closes[i]
        strike = _strike_for_delta(s0, dte, iv, right, target_delta, r)
        e = _find_expiry_idx(dates, i, dte)
        if strike is None or e is None:
            break
        prem0 = _price(s0, strike, dte, iv, right, r)
        res.cycles += 1

        def _itm(spot: float, k: float = strike) -> bool:
            return spot < k if right == "P" else spot > k

        b = next(
            (
                j
                for j in range(i + 1, e + 1)
                if (dates[e] - dates[j]).days <= breach_dte and _itm(closes[j])
            ),
            None,
        )
        if b is None:
            i = e + 1
            continue
        h = _find_expiry_idx(dates, e, roll_dte)
        if h is None:
            break
        res.breaches += 1
        sb, se, sh = closes[b], closes[e], closes[h]
        iv_b = _trailing_hv(closes, b) or iv
        iv_e = _trailing_hv(closes, e) or iv
        left_b = (dates[e] - dates[b]).days
        to_h_b = (dates[h] - dates[b]).days
        to_h_e = (dates[h] - dates[e]).days
        buyback = _price(sb, strike, left_b, iv_b, right, r)

        base = ArmOutcome(
            entry_date=dates[i],
            breach_date=dates[b],
            horizon_date=dates[h],
            pnl=0.0,
            strike=strike,
            entry_premium=prem0,
            buyback=buyback,
            spot_at_breach=sb,
            days_left_at_breach=left_b,
            iv_at_breach=iv_b,
        )

        stock = (sh - s0) * 100 if right == "C" else 0.0
        # close: buy back at the breach
        close_pnl = (prem0 - buyback) * 100 - 2 * commission + stock
        # assign / let called away
        if right == "P":
            if se < strike:
                kc = _strike_for_delta(se, to_h_e, iv_e, "C", target_delta, r) or se
                call = _price(se, kc, to_h_e, iv_e, "C", r)
                assign_pnl = (
                    prem0 * 100
                    + (sh - strike) * 100
                    + (call - max(0.0, sh - kc)) * 100
                    - 2 * commission
                )
            else:
                assign_pnl = prem0 * 100 - commission
        else:
            if se > strike:
                assign_pnl = (strike - s0) * 100 + prem0 * 100 - commission
            else:
                assign_pnl = prem0 * 100 - commission + stock
        # roll: same strike out to the horizon, if the net clears the floor
        prem1 = _price(sb, strike, to_h_b, iv_b, right, r)
        floor = -max_debit if right == "C" else min_net_credit
        if prem1 - buyback >= floor:
            intrinsic_h = max(0.0, strike - sh) if right == "P" else max(0.0, sh - strike)
            roll = replace(
                base, pnl=(prem0 - buyback + prem1 - intrinsic_h) * 100 - 3 * commission + stock
            )
        else:
            roll = replace(base, pnl=assign_pnl, fell_back=True)
        res.arms["assign"].append(replace(base, pnl=assign_pnl))
        res.arms["roll"].append(roll)
        res.arms["close"].append(replace(base, pnl=close_pnl))
        i = h + 1
    return res


def format_arms_summary(res: RollArmsResult, *, symbol: str) -> str:
    """Plain-text table of the three arms for the CLI."""
    lines = [
        f"{symbol}: {res.cycles} cycles, {res.breaches} breaches",
        f"{'arm':<8}{'n':>5}{'mean $':>10}{'median $':>10}{'CVaR5 $':>10}{'win %':>8}",
    ]
    for arm, s in res.summary().items():
        if not s.get("n"):
            lines.append(f"{arm:<8}{0:>5}")
            continue
        lines.append(
            f"{arm:<8}{int(s['n']):>5}{s['mean']:>10.0f}{s['median']:>10.0f}"
            f"{s['cvar5']:>10.0f}{s['win_rate'] * 100:>7.0f}%"
        )
    fell = sum(o.fell_back for o in res.arms["roll"])
    lines.append(f"roll fell back to assign on {fell} of {len(res.arms['roll'])} breaches")
    lines.append(
        "European Black-Scholes at trailing HV30 — no skew, no early exercise, no spreads: "
        "indicative only, a reading aid for a human, never an input to the policy."
    )
    return "\n".join(lines)
