/** Mirrors src/api/models (portfolio.py AccountValueResponse, pnl.py MonthPayResponse,
 *  spreads.py SpreadPositionsResponse). Hand-written like components/<domain>/types.ts. */

export type RangeKey = "1d" | "1w" | "1m" | "3m" | "ytd" | "all";

export type AccountValuePoint = { at: string; value: number };

export type AccountValueSeries = {
  range: RangeKey;
  points: AccountValuePoint[];
  latest: number | null;
  latest_at: string | null;
  previous_close: number | null;
  /** Null whenever the headline value is not from today (weekend, before the first snapshot). */
  change_today: number | null;
  change_today_pct: number | null;
};

export type AccountValueResponse = { as_of: string; series: AccountValueSeries };

export type MonthPay = {
  month: string;
  strategy: "all" | "csp" | "cc" | "spread";
  premium_collected: number;
  bought_back: number;
  commissions: number;
  commissions_complete: boolean;
  net: number;
  n_opened: number;
  n_closed: number;
  month_start_value: number | null;
  target_pct: number | null;
  target: number | null;
  progress_pct: number | null;
  days_left: number;
};

export type MonthPayResponse = {
  as_of: string;
  book: "paper" | "live";
  pay: MonthPay;
  /** False when a spreads book is in scope but data/spreads.db could not be read. */
  spreads_available: boolean;
};

export type SpreadPosition = {
  as_of: string;
  spread_id: string;
  mode: string;
  side: "put" | "call";
  expiry: string;
  short_strike: number;
  long_strike: number;
  width: number;
  contracts_opened: number;
  contracts: number;
  entry_credit: number;
  entry_commission: number;
  opened_at: string;
  status: string;
  exit_debit: number | null;
  exit_commission: number | null;
  exit_reason: string | null;
  closed_at: string | null;
  realized_pnl_usd: number | null;
};

export type SpreadPositionsResponse = {
  as_of: string;
  available: boolean;
  underlying: string;
  mode: string;
  positions: SpreadPosition[];
};
