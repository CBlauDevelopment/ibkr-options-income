"""The deterministic roll policy (2026-10-11 roll redesign). Pure Python, no LLM, no I/O.

Two questions, kept separate (docs/research/2026-10-11-rolling-short-options.md):

* **When** — ``roll_trigger``: a short is acted on only when its strike is breached (spot
  through the strike, or |delta| ≥ ``roll.trigger.breach_delta``) *and* it is near the end
  (DTE ≤ ``evaluate_within_dte`` or extrinsic ≤ ``min_extrinsic``) — a tested short with weeks
  of time value left often recovers. A short call is also acted on before an ex-dividend date
  when its extrinsic no longer covers the dividend (early assignment becomes rational). The
  calendar timers are informational elsewhere; they never reach this module.
* **What** — ``decide``: a would-own put rolls for a net credit when one exists
  (``csp.when_assignable: roll_if_credit``), else is assigned; a put on a name the operator
  would not own rolls if it can and is closed only when no roll qualifies; a covered call rolls
  up-and-out (``cc.keep_shares``, debit capped), else is called away above basis or held below
  it. Leveraged ETFs follow the same tree (operator ruling 2026-10-14, replacing "never roll").
  ``on_no_roll="close"`` is the loss-line variant: roll if one qualifies, otherwise close —
  "prefer rolling over closing in a loss; if there are no viable rolls, reluctantly close".

``RollDecision.reason`` is a stable code and ``rejections`` counts every construction
rejection, so a decision that proposes nothing still says why.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from typing import Literal

from src.common.config import RollCfg
from src.common.schemas import (
    FundamentalStats,
    IVStats,
    OptionQuote,
    OptionRight,
    PositionSnapshot,
    RollDecision,
    TechnicalStats,
)
from src.strategies.rolling import RollContext, construct_roll


def extrinsic(quote: OptionQuote, spot: float | None) -> float | None:
    """Time value per share: two-sided mid minus intrinsic. None without a mid or a spot."""
    mid = quote.strict_mid
    if mid is None or spot is None:
        return None
    if quote.right == OptionRight.PUT:
        intrinsic = max(0.0, quote.strike - spot)
    else:
        intrinsic = max(0.0, spot - quote.strike)
    return mid - intrinsic


def roll_trigger(
    pos: PositionSnapshot,
    quote: OptionQuote,
    fund: FundamentalStats | None,
    cfg: RollCfg,
    *,
    ex_div_guard: bool,
    today: date,
) -> str | None:
    """``"strike_breach"``, ``"ex_div"`` or None for one short and its live quote."""
    if pos.position >= 0 or pos.strike is None or pos.expiry is None or pos.right is None:
        return None
    spot = quote.underlying_price
    dte = (pos.expiry - today).days
    ext = extrinsic(quote, spot)
    t = cfg.trigger

    if pos.right == OptionRight.PUT:
        through = spot is not None and spot < pos.strike
    else:
        through = spot is not None and spot > pos.strike
    breached = through or (quote.delta is not None and abs(quote.delta) >= t.breach_delta)
    near = dte <= t.evaluate_within_dte or (ext is not None and ext <= t.min_extrinsic)
    if breached and near:
        return "strike_breach"

    if (
        ex_div_guard
        and pos.right == OptionRight.CALL
        and fund is not None
        and fund.ex_dividend_date is not None
        and fund.dividend_per_share is not None
        and ext is not None
        and spot is not None
        and spot > pos.strike  # an OTM call is never exercised for a dividend
    ):
        days_to_ex = (fund.ex_dividend_date - today).days
        if (
            0 <= days_to_ex <= cfg.ex_div.days_ahead
            and fund.ex_dividend_date <= pos.expiry
            and ext < fund.dividend_per_share + cfg.ex_div.buffer
        ):
            return "ex_div"
    return None


def _top(rejections: dict[str, int], default: str) -> str:
    if not rejections:
        return default
    return min(rejections, key=lambda k: (-rejections[k], k))


def _rej_text(rejections: dict[str, int]) -> str:
    if not rejections:
        return "no roll targets were priced"
    return ", ".join(f"{k.replace('_', ' ')} ×{n}" for k, n in sorted(rejections.items()))


def decide(
    ctx: RollContext,
    quotes: list[OptionQuote],
    iv_stats: IVStats,
    tech_stats: TechnicalStats,
    cfg: RollCfg,
    *,
    would_own: bool,
    cc_basis: float | None,
    on_no_roll: Literal["policy", "close"] = "policy",
) -> RollDecision:
    """Roll, assign, let called away, close, hold or defer — see the module docstring.

    *on_no_roll* ``"close"`` (the loss line) skips assignment and keeping shares: a qualifying
    roll is taken, anything else becomes a close.
    """
    pos = ctx.position
    strike = pos.strike or 0.0
    if ctx.current.strict_mid is None:
        return RollDecision(
            action="defer",
            reason="current_unpriced",
            detail="No two-sided quote for the short itself — retrying next cycle.",
        )

    if on_no_roll == "close":
        cand, rej = construct_roll(
            dataclasses.replace(
                ctx, allow_debit=pos.right == OptionRight.CALL and cfg.cc.keep_shares
            ),
            quotes,
            iv_stats,
            tech_stats,
            cfg,
        )
        if cand is not None:
            kind = "debit" if cand.premium < 0 else "credit"
            return RollDecision(
                action="roll",
                reason="loss_line_roll",
                candidate=cand,
                rejections=rej,
                detail=f"At the loss line: roll for a ${abs(cand.premium):.2f}/sh net {kind} "
                "instead of buying back.",
            )
        return RollDecision(
            action="close",
            reason=_top(rej, "no_qualifying_roll"),
            rejections=rej,
            detail=f"At the loss line and no roll qualifies ({_rej_text(rej)}) — buying back.",
        )

    if pos.right == OptionRight.PUT:
        if not would_own:
            cand, rej = construct_roll(ctx, quotes, iv_stats, tech_stats, cfg)
            if cand is not None:
                return RollDecision(
                    action="roll",
                    reason="credit_roll",
                    candidate=cand,
                    rejections=rej,
                    detail=f"Not on the would-own list — rolling for a ${cand.premium:.2f}/sh "
                    "net credit rather than closing.",
                )
            return RollDecision(
                action="close",
                reason="not_would_own",
                rejections=rej,
                detail=f"Not on the would-own list and no roll qualifies ({_rej_text(rej)}) — "
                f"close rather than take shares at ${strike:g}.",
            )
        if cfg.csp.when_assignable == "assign":
            return RollDecision(
                action="assign",
                reason="assign_preferred",
                detail=f"Would-own name: letting it assign at ${strike:g} (roll.csp: assign).",
            )
        cand, rej = construct_roll(ctx, quotes, iv_stats, tech_stats, cfg)
        if cand is not None:
            return RollDecision(
                action="roll",
                reason="credit_roll",
                candidate=cand,
                rejections=rej,
                detail=f"Roll for a ${cand.premium:.2f}/sh net credit.",
            )
        return RollDecision(
            action="assign",
            reason=_top(rej, "no_qualifying_roll"),
            rejections=rej,
            detail=f"No credit roll ({_rej_text(rej)}) — letting it assign at ${strike:g}.",
        )

    above_basis = cc_basis is None or strike >= cc_basis
    if not cfg.cc.keep_shares and above_basis:
        return RollDecision(
            action="let_called_away",
            reason="keep_shares_off",
            detail=f"Strike ${strike:g} is at/above basis — letting the shares be called away.",
        )
    cand, rej = construct_roll(
        dataclasses.replace(ctx, allow_debit=cfg.cc.keep_shares),
        quotes,
        iv_stats,
        tech_stats,
        cfg,
    )
    if cand is not None:
        kind = "debit" if cand.premium < 0 else "credit"
        return RollDecision(
            action="roll",
            reason="keep_shares_roll" if cand.premium < 0 else "credit_roll",
            candidate=cand,
            rejections=rej,
            detail=f"Roll up and out for a ${abs(cand.premium):.2f}/sh net {kind}.",
        )
    if above_basis:
        return RollDecision(
            action="let_called_away",
            reason=_top(rej, "no_qualifying_roll"),
            rejections=rej,
            detail=f"No roll within limits ({_rej_text(rej)}) — letting the shares go at "
            f"${strike:g}.",
        )
    return RollDecision(
        action="hold",
        reason="below_basis_no_roll",
        rejections=rej,
        detail=f"Strike ${strike:g} is below cost basis and no roll fits ({_rej_text(rej)}) — "
        "holding; buying back deep ITM is the most expensive exit.",
    )
