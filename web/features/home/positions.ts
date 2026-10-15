import type { StatusTone } from "@/components/ui/StatusWord";
import type { PositionGroupData } from "@/components/portfolio/types";
import type { SpreadPosition } from "./types";

/**
 * When a portfolio snapshot reads as Delayed on Home: twice the monitor's 15-minute snapshot
 * interval, the same threshold as PositionsPanel / SummaryPanel. The positions card and the
 * account hero both use it, so the two never disagree about the same snapshot table.
 */
export const FRESH_FOR_MINUTES = 30;

export type PositionKind = "csp" | "cc" | "spread" | "shares" | "other";

export type PositionRow = {
  key: string;
  kind: PositionKind;
  underlying: string;
  /** The page behind the row (/positions/AAPL/2026-11-21_P180); null when the contract is not fully known. */
  href: string | null;
  title: string;
  status: { word: string; tone: StatusTone } | null;
  sub: string;
  value: number | null;
  valueLabel: string;
  /** ISO expiry, or "~" so expiry-less rows (shares) sort last. */
  sortKey: string;
};

const DAY = new Intl.DateTimeFormat("en-US", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });

function expiryLabel(iso: string | null, dte: number | null): string {
  if (!iso) return "expiry n/a";
  const d = DAY.format(new Date(`${iso}T00:00:00Z`));
  return dte === null ? d : `${d} · ${dte}d`;
}

const money = (v: number) => `$${v.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;

/** The slug the position page and API use for one option contract: expiry, right, strike. */
export function optionSlug(expiry: string, right: string, strike: number): string {
  return `${expiry}_${right}${strike}`;
}

const pageFor = (underlying: string, slug: string) => `/positions/${encodeURIComponent(underlying)}/${slug}`;

function words(query: string): string[][] {
  return query
    .toLowerCase()
    .split(",")
    .map((alt) => alt.split(/\s+/).filter(Boolean))
    .filter((alt) => alt.length > 0);
}

/**
 * Whether a row answers a search. Commas separate alternatives ("amzn, nvda" shows both names);
 * inside one alternative every word must appear ("amzn put"). Only the ticker and the contract's
 * own words are searched, so "sat" does not match every row that expires on a Saturday.
 */
export function matchesQuery(row: PositionRow, query: string): boolean {
  const alts = words(query);
  if (alts.length === 0) return true;
  const hay = `${row.underlying} ${row.title}`.toLowerCase();
  return alts.some((alt) => alt.every((w) => hay.includes(w)));
}

/** The status word for a held option, from API fields only; null when none of them is known. */
export function optionStatus(
  o: { expiry: string | null; dte: number | null; assignment_risk: boolean; moneyness: string | null },
  todayIso: string,
): PositionRow["status"] {
  if (o.expiry === todayIso || o.dte === 0) return { word: "Expires today", tone: "today" };
  if (o.assignment_risk) return { word: "Assignment likely", tone: "flag" };
  if (o.moneyness === "itm") return { word: "In the money", tone: "flag" };
  if (o.moneyness === "atm") return { word: "At the money", tone: "neutral" };
  if (o.moneyness === "otm") return { word: "Out of the money", tone: "neutral" };
  return null;
}

export function buildPositionRows(
  groups: PositionGroupData[],
  spreads: SpreadPosition[],
  todayIso: string,
  underlying = "SPY",
): PositionRow[] {
  const rows: PositionRow[] = [];
  for (const g of groups) {
    const shares = g.stock?.shares ?? 0;
    for (const o of g.options) {
      const kind: PositionKind = !o.short ? "other" : o.right === "P" ? "csp" : o.right === "C" ? "cc" : "other";
      const known = o.right && typeof o.strike === "number" && o.expiry;
      const word = o.right === "P" ? "put" : o.right === "C" ? "call" : "option";
      const strike = typeof o.strike === "number" ? money(o.strike) : "strike n/a";
      const status = optionStatus(o, todayIso);
      const parts = [expiryLabel(o.expiry, o.dte)];
      if (kind === "cc" && shares >= 100 * o.contracts) parts.push(`covered by ${100 * o.contracts} shares`);
      if (o.contracts > 1) parts.push(`${o.contracts} contracts`);
      rows.push({
        key: `${g.underlying}:${o.symbol}`,
        kind,
        underlying: g.underlying,
        href: known ? pageFor(g.underlying, optionSlug(o.expiry!, o.right!, o.strike as number)) : null,
        title: `${o.short ? "" : "Long "}${g.underlying} ${strike} ${word}`,
        status,
        sub: parts.join(" · "),
        value: o.unrealized_pnl,
        valueLabel: "open P&L",
        sortKey: o.expiry ?? "~",
      });
    }
    if (g.stock) {
      const s = g.stock;
      const basis = s.adjusted_cost_basis !== null ? ` · adjusted ${money(s.adjusted_cost_basis)}` : "";
      rows.push({
        key: `${g.underlying}:stock`,
        kind: "shares",
        underlying: g.underlying,
        href: pageFor(g.underlying, "shares"),
        title: `${g.underlying} · ${s.shares} shares`,
        status: null,
        sub: `avg ${money(s.avg_cost)}${basis}`,
        value: s.unrealized_pnl_adjusted ?? s.unrealized_pnl,
        valueLabel: "open P&L",
        sortKey: "~",
      });
    }
  }
  for (const p of spreads) {
    rows.push({
      key: `spread:${p.spread_id}`,
      kind: "spread",
      underlying,
      href: pageFor(underlying, `spread-${p.spread_id}`),
      title: `${underlying} ${p.short_strike}/${p.long_strike} ${p.side} spread`,
      status:
        p.expiry === todayIso
          ? { word: "Expires today", tone: "today" }
          : p.status === "expiring"
            ? { word: "Expiring", tone: "neutral" }
            : { word: "Open", tone: "neutral" },
      sub: `${expiryLabel(p.expiry, null)} · daily spreads book · ${p.mode}`,
      value: p.entry_credit * 100 * p.contracts,
      valueLabel: "sold for",
      sortKey: p.expiry,
    });
  }
  return rows.sort((a, b) => (a.sortKey < b.sortKey ? -1 : a.sortKey > b.sortKey ? 1 : a.title.localeCompare(b.title)));
}
