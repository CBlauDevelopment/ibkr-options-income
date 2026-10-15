import { formatStubValue } from "@/components/ui/Stub";
import { formatMoneyCell } from "@/lib/money";
import type { Bar, PositionDetail } from "./types";

export type RangeKey = "1m" | "3m" | "6m" | "1y";
export const RANGES: { value: RangeKey; label: string; months: number }[] = [
  { value: "1m", label: "1M", months: 1 },
  { value: "3m", label: "3M", months: 3 },
  { value: "6m", label: "6M", months: 6 },
  { value: "1y", label: "1Y", months: 12 },
];

const NY_DAY = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" });
const dollars = (v: number) => `$${v.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
const LONG_DAY = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });

/** The bars from `months` back from the last bar. Calendar months, so 1M is a month, not 21 bars. */
export function sliceBars(bars: Bar[], months: number): Bar[] {
  if (bars.length === 0) return [];
  const last = new Date(`${bars[bars.length - 1].time}T00:00:00Z`);
  last.setUTCMonth(last.getUTCMonth() - months);
  const cut = last.toISOString().slice(0, 10);
  return bars.filter((b) => b.time >= cut);
}

/** Change from the first to the last close of the slice, or null when there is nothing to compare. */
export function rangeChange(bars: Bar[]): { delta: number; pct: number } | null {
  if (bars.length < 2 || bars[0].close <= 0) return null;
  const delta = bars[bars.length - 1].close - bars[0].close;
  return { delta, pct: (delta / bars[0].close) * 100 };
}

const wordOf = (right: string | null) => (right === "P" ? "put" : right === "C" ? "call" : "option");

export function positionTitle(d: PositionDetail): string {
  if (d.kind === "shares") return `${d.underlying} · ${d.stock?.shares ?? 0} shares`;
  if (d.kind === "spread" && d.spread) {
    return `${d.underlying} ${d.spread.short_strike}/${d.spread.long_strike} ${d.spread.side} spread`;
  }
  const strike = d.option?.strike ?? d.opened?.strike ?? d.closed?.strike ?? null;
  const right = d.option?.right ?? d.opened?.right ?? d.closed?.right ?? null;
  return `${d.underlying} ${strike === null ? "strike n/a" : `$${strike}`} ${wordOf(right)}`;
}

/** The levels drawn across the chart: a strike, a cost basis. */
export function chartLines(d: PositionDetail): { price: number; title: string }[] {
  if (d.kind === "shares" && d.stock) {
    const lines = [{ price: d.stock.avg_cost, title: `Avg cost ${dollars(d.stock.avg_cost)}` }];
    const adj = d.stock.adjusted_cost_basis;
    if (adj !== null && Math.abs(adj - d.stock.avg_cost) > 0.005) lines.push({ price: adj, title: `Adjusted ${dollars(adj)}` });
    return lines;
  }
  if (d.kind === "spread" && d.spread) {
    return [
      { price: d.spread.short_strike, title: `Short ${dollars(d.spread.short_strike)}` },
      { price: d.spread.long_strike, title: `Long ${dollars(d.spread.long_strike)}` },
    ];
  }
  const strike = d.option?.strike ?? d.opened?.strike ?? null;
  return strike === null ? [] : [{ price: strike, title: `Strike ${dollars(strike)}` }];
}

/** The New York day the position was opened, "YYYY-MM-DD", for the chart's marker. */
export function openedOn(d: PositionDetail): string | null {
  if (d.kind === "shares") return d.campaign?.opened_date ?? null;
  const at = d.opened?.at;
  if (!at || Number.isNaN(Date.parse(at))) return null;
  return NY_DAY.format(new Date(at));
}

/** How the stock stands against the strike, in words: "2.3% above the strike". */
export function strikeDistance(lastClose: number | null, strike: number | null): string | null {
  if (lastClose === null || strike === null || strike <= 0) return null;
  const pct = ((lastClose - strike) / strike) * 100;
  if (Math.abs(pct) < 0.05) return "at the strike";
  return `${Math.abs(pct).toFixed(1)}% ${pct > 0 ? "above" : "below"} the strike`;
}

/** Share of the premium kept so far, from what it sold for and what it costs to close now. */
export function keptSoFar(d: PositionDetail): number | null {
  const sold = d.opened?.premium;
  const n = d.opened?.contracts ?? 0;
  const mark = d.option?.market_price;
  if (!d.option?.short || sold == null || mark == null || n <= 0) return null;
  const perShare = sold / (100 * n);
  return perShare > 0 ? ((perShare - mark) / perShare) * 100 : null;
}

export type NowLine = { label: string; value: string; tone: "gain" | "loss" | "plain" | "unknown" };

export function nowLines(d: PositionDetail, lastClose: number | null): NowLine[] {
  const o = d.option;
  if (!o) return [];
  const pnl = o.unrealized_pnl;
  const lines: NowLine[] = [
    {
      label: "Open P&L",
      value: formatStubValue(pnl, "signed-money"),
      tone: pnl === null ? "unknown" : pnl > 0 ? "gain" : pnl < 0 ? "loss" : "plain",
    },
  ];
  const kept = keptSoFar(d);
  if (kept !== null) lines.push({ label: "Premium kept so far", value: `${kept.toFixed(0)}%`, tone: "plain" });
  if (o.dte !== null) {
    lines.push({ label: "Time left", value: o.dte === 0 ? "Expires today" : `${o.dte} day${o.dte === 1 ? "" : "s"}`, tone: "plain" });
  }
  const dist = strikeDistance(lastClose, o.strike ?? null);
  if (lastClose !== null && dist !== null) {
    lines.push({ label: "Last close", value: `${formatMoneyCell(lastClose)}, ${dist}`, tone: "plain" });
  }
  return lines;
}

/** One line under the title: when it expires and, for a contract, when it was sold. */
export function subline(d: PositionDetail): string {
  const day = (iso: string) => LONG_DAY.format(new Date(`${iso}T00:00:00Z`));
  if (d.kind === "shares") return d.campaign ? `Held since ${day(d.campaign.opened_date)}` : "Shares held in the account";
  const expiry = d.option?.expiry ?? d.opened?.expiry ?? d.closed?.expiry ?? null;
  const parts: string[] = [];
  if (expiry) parts.push(`${d.held ? "Expires" : "Expired"} ${day(expiry)}`);
  const opened = openedOn(d);
  if (opened) parts.push(`sold ${day(opened)}`);
  if (!d.held && d.closed) parts.push(d.closed.how === "rolled" ? "rolled" : "no longer held");
  return parts.join(" · ");
}
