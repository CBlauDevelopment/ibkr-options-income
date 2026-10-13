"""Candidate credit verticals placed beyond the day's action zone.

A put spread's short strike sits below BOTH the expected-move floor (spot − em × em_multiple)
and the put wall less a buffer; a call spread's short strike above both the expected-move
ceiling and the call wall plus a buffer. Per side, the closest strike that clears the delta cap
and the minimum credit wins. Further out of the money only gets cheaper, so the walk stops at
the first strike whose credit is too thin. Pure: no IBKR, no I/O, and no gating — that is
``risk.validate``'s job.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from datetime import date, datetime

from src.common.config import SpreadsCfg
from src.common.schemas import (
    ChainOption,
    ChainSnapshot,
    GexLevels,
    SpreadCandidate,
    SpreadMenuPosition,
    SpreadSide,
)
from src.spreads.pricing import ET


def short_boundary(side: SpreadSide, levels: GexLevels, cfg: SpreadsCfg) -> float | None:
    """Furthest-in strike a short leg may use. None (no trade) without an expected move."""
    if levels.expected_move is None:
        return None
    s = cfg.selection
    move = levels.expected_move * s.em_multiple
    buffer = levels.spot * s.wall_buffer_pct
    if side == "put":
        floor = levels.spot - move
        if levels.put_wall is not None:
            floor = min(floor, levels.put_wall - buffer)
        return floor
    ceiling = levels.spot + move
    if levels.call_wall is not None:
        ceiling = max(ceiling, levels.call_wall + buffer)
    return ceiling


def make_spread_id(
    side: SpreadSide, expiry: date, short_strike: float, long_strike: float, now: datetime
) -> str:
    return (
        f"{expiry:%Y%m%d}-{side[0].upper()}{short_strike:g}-{long_strike:g}"
        f"-{now.astimezone(ET):%H%M%S}"
    )


def _build(
    spread_id: str,
    side: SpreadSide,
    short_q: ChainOption,
    long_q: ChainOption,
    width: float,
    spot: float,
    quote_time: datetime,
) -> SpreadCandidate | None:
    short_mid, long_mid = short_q.mid, long_q.mid
    if short_mid is None or long_mid is None or short_q.bid is None or long_q.ask is None:
        return None
    return SpreadCandidate(
        spread_id=spread_id,
        side=side,
        expiry=short_q.expiry,
        short_strike=short_q.strike,
        long_strike=long_q.strike,
        width=width,
        short_con_id=short_q.con_id,
        long_con_id=long_q.con_id,
        credit_mid=round(short_mid - long_mid, 4),
        credit_natural=round(short_q.bid - long_q.ask, 4),
        short_delta=short_q.delta,
        short_leg_spread_pct=short_q.spread_pct,
        long_leg_spread_pct=long_q.spread_pct,
        spot=spot,
        quote_time=quote_time,
    )


def _legs(chain: ChainSnapshot, side: SpreadSide, today: date) -> dict[float, ChainOption]:
    right = "P" if side == "put" else "C"
    return {round(o.strike, 2): o for o in chain.options if o.right == right and o.expiry == today}


def _qualify_why(
    side: SpreadSide,
    k: float,
    legs: dict[float, ChainOption],
    chain: ChainSnapshot,
    cfg: SpreadsCfg,
    now: datetime,
) -> tuple[SpreadCandidate | None, str | None]:
    """``_qualify``, plus why not: (candidate, None) or (None, reason)."""
    s = cfg.selection
    long_k = round(k - s.width if side == "put" else k + s.width, 2)
    long_q = legs.get(long_k)
    if long_q is None:
        return None, "no long leg"
    short_q = legs[k]
    if short_q.delta is not None and abs(short_q.delta) > s.short_delta_max:
        return None, "over the delta cap"
    today = now.astimezone(ET).date()
    cand = _build(
        make_spread_id(side, today, k, long_k, now),
        side,
        short_q,
        long_q,
        s.width,
        chain.spot,
        chain.as_of,  # when the quotes were taken: the gate's stale_quote input
    )
    if cand is None:
        return None, "no quote"
    if cand.credit_mid <= 0:
        return None, "no credit"
    return cand, None


def _qualify(
    side: SpreadSide,
    k: float,
    legs: dict[float, ChainOption],
    chain: ChainSnapshot,
    cfg: SpreadsCfg,
    now: datetime,
) -> SpreadCandidate | None:
    """The spread shorting *k*, or None when it can't be built: no long leg, short over the
    delta cap, a missing quote, or no credit. The credit floor is the caller's check."""
    return _qualify_why(side, k, legs, chain, cfg, now)[0]


def _walk(
    side: SpreadSide, chain: ChainSnapshot, levels: GexLevels, cfg: SpreadsCfg, now: datetime
) -> Iterator[SpreadCandidate]:
    """Qualifying spreads on *side* from the action-zone boundary outward. Stops at the first
    whose credit is under the floor: further out of the money only gets cheaper."""
    s = cfg.selection
    boundary = short_boundary(side, levels, cfg)
    if boundary is None:
        return
    legs = _legs(chain, side, now.astimezone(ET).date())
    if side == "put":
        shorts = sorted((k for k in legs if k <= boundary), reverse=True)
    else:
        shorts = sorted(k for k in legs if k >= boundary)
    for k in shorts:
        cand = _qualify(side, k, legs, chain, cfg, now)
        if cand is None:
            continue
        if cand.credit_mid < s.min_credit_pct_of_width * s.width:
            return
        yield cand


def why_nothing(
    side: SpreadSide, chain: ChainSnapshot, levels: GexLevels, cfg: SpreadsCfg, now: datetime
) -> str:
    """Why ``_walk`` yields nothing on *side*, in one line for the log and Telegram: the
    boundary and what it was built from, then the nearest strike's credit against the floor,
    or which checks every strike past the boundary failed."""
    s = cfg.selection
    boundary = short_boundary(side, levels, cfg)
    if boundary is None:
        return f"{side}: no expected move, so no strike boundary"
    put = side == "put"
    wall = levels.put_wall if put else levels.call_wall
    where = (
        f"short {'≤' if put else '≥'} {boundary:.2f} (spot {levels.spot:.2f}, "
        f"EM {levels.expected_move:.2f} × {s.em_multiple:g}, "
        f"{side} wall {'n/a' if wall is None else f'{wall:.2f}'})"
    )
    legs = _legs(chain, side, now.astimezone(ET).date())
    shorts = (
        sorted((k for k in legs if k <= boundary), reverse=True)
        if put
        else sorted(k for k in legs if k >= boundary)
    )
    if not shorts:
        return f"{side}: {where} — no listed strike there"
    floor = s.min_credit_pct_of_width * s.width
    skipped: dict[str, int] = {}
    for k in shorts:
        cand, why = _qualify_why(side, k, legs, chain, cfg, now)
        if cand is None:
            skipped[why or "?"] = skipped.get(why or "?", 0) + 1
            continue
        delta = "n/a" if cand.short_delta is None else f"{abs(cand.short_delta):.2f}"
        past = "" if not skipped else f" (nearer: {_counts(skipped)})"
        if cand.credit_mid < floor:
            return (
                f"{side}: {where} — nearest {k:g}/{cand.long_strike:g} pays "
                f"${cand.credit_mid:.2f} mid (Δ {delta}), under the ${floor:.2f} credit floor"
                f"{past}"
            )
        return f"{side}: {where} — {k:g}/{cand.long_strike:g} qualifies"
    return f"{side}: {where} — no buildable spread ({_counts(skipped)})"


def _counts(skipped: dict[str, int]) -> str:
    return ", ".join(f"{n} {why}" for why, n in skipped.items())


def _inside(
    baseline: SpreadCandidate, chain: ChainSnapshot, cfg: SpreadsCfg, now: datetime
) -> SpreadCandidate | None:
    """The listed strike one step closer to spot than *baseline*. It ignores the action-zone
    boundary on purpose (the gate doesn't check it) but still clears the delta cap and the
    credit floor, so Claude can sell more premium than the baseline on a calm day."""
    s = cfg.selection
    side = baseline.side
    legs = _legs(chain, side, now.astimezone(ET).date())
    closer = [
        k
        for k in legs
        if (k > baseline.short_strike if side == "put" else k < baseline.short_strike)
    ]
    if not closer:
        return None
    k = min(closer) if side == "put" else max(closer)
    cand = _qualify(side, k, legs, chain, cfg, now)
    if cand is None or cand.credit_mid < s.min_credit_pct_of_width * s.width:
        return None
    return cand


def _sides(cfg: SpreadsCfg, sides: list[SpreadSide] | None) -> list[SpreadSide]:
    s = cfg.selection
    return list(s.sides) if sides is None else [x for x in s.sides if x in sides]


def select_candidates(
    chain: ChainSnapshot,
    levels: GexLevels,
    cfg: SpreadsCfg,
    now: datetime,
    sides: list[SpreadSide] | None = None,
) -> list[SpreadCandidate]:
    """At most one candidate per side (the baseline rule). *sides* (the entry trigger's choice)
    narrows the walk."""
    out: list[SpreadCandidate] = []
    for side in _sides(cfg, sides):
        first = next(_walk(side, chain, levels, cfg, now), None)
        if first is not None:
            out.append(first)
    return out


def select_menu(
    chain: ChainSnapshot,
    levels: GexLevels,
    cfg: SpreadsCfg,
    now: datetime,
    sides: list[SpreadSide] | None = None,
) -> list[tuple[SpreadCandidate, SpreadMenuPosition]]:
    """Per side, closest to spot first: the inside strike (menu_size >= 2), the baseline pick,
    then up to menu_size - 2 strikes further out. Ungated: ``risk.validate`` decides which
    items reach Claude."""
    n = cfg.selection.menu_size
    out: list[tuple[SpreadCandidate, SpreadMenuPosition]] = []
    for side in _sides(cfg, sides):
        walk = _walk(side, chain, levels, cfg, now)
        baseline = next(walk, None)
        if baseline is None:
            continue
        if n >= 2:
            inside = _inside(baseline, chain, cfg, now)
            if inside is not None:
                out.append((inside, "inside"))
        out.append((baseline, "baseline"))
        out.extend((c, "outer") for c in itertools.islice(walk, max(0, n - 2)))
    return out


def refresh_candidate(
    c: SpreadCandidate,
    short_q: ChainOption,
    long_q: ChainOption,
    now: datetime,
    spot: float | None = None,
) -> SpreadCandidate | None:
    """The same spread repriced on fresh leg quotes and, when known, a fresh spot (the
    send-time re-gate's input)."""
    return _build(c.spread_id, c.side, short_q, long_q, c.width, spot or c.spot, now)
