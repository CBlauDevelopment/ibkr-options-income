import type { SpreadPosition } from "@/features/home/types";

/** Mirrors src/api/models/spreads.py SpreadMenuItemOut, SpreadPickOut and SpreadPicksResponse.
 *  Hand-written like components/<domain>/types.ts. Credits are per share. */

export type SpreadMenuItem = {
  letter: string;
  position: "inside" | "baseline" | "outer";
  side: "put" | "call";
  short_strike: number;
  long_strike: number;
  width: number;
  contracts: number;
  credit_mid: number;
  credit_after_costs: number;
  max_loss_per_contract_usd: number;
  short_delta: number | null;
  spot: number;
  dist_spot_pts: number;
  dist_em_multiple: number | null;
  /** Break-even win rate (0-1) under the configured exits; null when it cannot be computed. */
  be_nominal_exits: number | null;
};

export type SpreadPick = {
  pick_id: number;
  created_at: string;
  book_mode: string;
  /** A menu letter, or "skip". */
  choice: string;
  /** Claude's reason; "" when it gave none. */
  reason: string;
  fallback_reason: string | null;
  executed_letter: string | null;
  /** True when it did not trade: refused at send time, or sent and not filled. */
  send_rejected: boolean;
  send_reasons: string[];
  filled: boolean;
  model: string;
  regime: string;
  side: string | null;
  plan_bias: string | null;
  event_flag: boolean;
  /** False when the stored menu no longer parses; `menu` is then empty. */
  menu_readable: boolean;
  menu: SpreadMenuItem[];
  spread_id: string | null;
};

export type SpreadPicksResponse = {
  as_of: string;
  available: boolean;
  underlying: string;
  mode: string;
  ai_enabled: boolean;
  day: string;
  previous_day: string | null;
  next_day: string | null;
  /** Newest first. */
  picks: SpreadPick[];
  /** Every book's spreads opened that day, oldest first. */
  positions: SpreadPosition[];
};
