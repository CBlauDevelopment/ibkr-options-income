"""The pick menu's economics — what Claude is shown about each gate-approved spread.

Pure and deterministic: no IBKR, no I/O, no LLM. Every number on the menu comes from here; the
prompt (src/spreads_ai/prompts.py) only formats them. Costs are per share and round trip: two
legs opened and two closed, each paying ``shadow_slippage_per_leg`` and the per-contract
commission (SPY settles in shares, so every spread is closed, never left to expire).
"""

from __future__ import annotations

from src.common.config import SpreadsCfg
from src.common.schemas import GexLevels, SpreadCandidate, SpreadMenuItem, SpreadMenuPosition

LETTERS = "ABCDEFGH"


def round_trip_cost(cfg: SpreadsCfg) -> float:
    x = cfg.execution
    return round(4 * x.shadow_slippage_per_leg + 4 * x.commission_per_contract / 100.0, 4)


def breakeven(win: float, loss: float) -> float | None:
    """The win rate at which wins of *win* and losses of *loss* (per share) break even."""
    if win <= 0 or loss <= 0:
        return None
    return round(loss / (win + loss), 4)


def _distance(c: SpreadCandidate, spot: float) -> float:
    return spot - c.short_strike if c.side == "put" else c.short_strike - spot


def build_menu(
    items: list[tuple[SpreadCandidate, SpreadMenuPosition, int]],
    levels: GexLevels,
    cfg: SpreadsCfg,
) -> list[SpreadMenuItem]:
    """Gate-approved (candidate, position, contracts) → lettered items. Puts first, then calls;
    within a side, closest to spot first."""
    cost = round_trip_cost(cfg)
    ex = cfg.exits
    ordered = sorted(
        items, key=lambda it: (0 if it[0].side == "put" else 1, _distance(it[0], levels.spot))
    )
    out: list[SpreadMenuItem] = []
    for letter, (c, position, contracts) in zip(LETTERS, ordered, strict=False):
        credit = c.credit_mid
        dist = _distance(c, levels.spot)
        wall = levels.put_wall if c.side == "put" else levels.call_wall
        beyond = (
            None
            if wall is None
            else (wall - c.short_strike if c.side == "put" else c.short_strike - wall)
        )
        full_loss = c.width - credit
        nominal_loss = min(full_loss, (ex.stop_debit_multiple - 1.0) * credit)
        out.append(
            SpreadMenuItem(
                letter=letter,
                position=position,
                candidate=c,
                contracts=contracts,
                credit_after_costs=round(credit - cost, 4),
                cost_pct_of_credit=round(cost / credit, 4) if credit > 0 else None,
                max_loss_per_contract_usd=round(c.max_loss_per_contract, 2),
                dist_spot_pts=round(dist, 2),
                dist_em_multiple=(
                    round(dist / levels.expected_move, 2) if levels.expected_move else None
                ),
                beyond_wall_pts=None if beyond is None else round(beyond, 2),
                be_full_loss=breakeven(credit - cost, full_loss + cost),
                be_nominal_exits=breakeven(
                    ex.profit_take_pct / 100.0 * credit - cost, nominal_loss + cost
                ),
            )
        )
    return out
