import type { CampaignSummary, OptionLeg, StockLeg } from "@/components/portfolio/types";
import type { DayTrade } from "@/features/home/types";

/** Mirrors src/api/models/portfolio.py PositionDetailResponse. Hand-written like the rest. */
export type SpreadRow = {
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
  status: string;
  closed_at: string | null;
  realized_pnl_usd: number | null;
};

export type PositionDetail = {
  as_of: string;
  underlying: string;
  slug: string;
  kind: "option" | "shares" | "spread";
  held: boolean;
  source: "monitor" | "refresh" | "eod" | "none";
  degraded: boolean;
  option: OptionLeg | null;
  stock: StockLeg | null;
  campaign: CampaignSummary | null;
  spread: SpreadRow | null;
  opened: DayTrade | null;
  closed: DayTrade | null;
  spreads_available: boolean;
};

export type Bar = { time: string; open: number; high: number; low: number; close: number; volume: number };
export type BarsResponse = { as_of: string; bars: Bar[] };

export type Headline = {
  title: string;
  url: string | null;
  published_at: string | null;
  source: string | null;
  sentiment: number | null;
};
export type HeadlinesResponse = { as_of: string; symbol: string; items: Headline[] };

