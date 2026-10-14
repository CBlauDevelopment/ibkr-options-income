import type { StatusTone } from "@/components/ui/StatusWord";
import type { PositionGroupData } from "@/components/portfolio/types";
import type { SpreadPosition } from "./types";

export type PositionKind = "csp" | "cc" | "spread" | "shares" | "other";

export type PositionRow = {
  key: string;
  kind: PositionKind;
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
      const word = o.right === "P" ? "put" : o.right === "C" ? "call" : "option";
      const strike = typeof o.strike === "number" ? money(o.strike) : "strike n/a";
      let status: PositionRow["status"] = null;
      if (o.expiry === todayIso || o.dte === 0) status = { word: "Expires today", tone: "today" };
      else if (o.assignment_risk) status = { word: "Assignment likely", tone: "flag" };
      else if (o.moneyness === "itm") status = { word: "In the money", tone: "flag" };
      else if (o.moneyness === "atm") status = { word: "At the money", tone: "neutral" };
      else if (o.moneyness === "otm") status = { word: "Out of the money", tone: "neutral" };
      const parts = [expiryLabel(o.expiry, o.dte)];
      if (kind === "cc" && shares >= 100 * o.contracts) parts.push(`covered by ${100 * o.contracts} shares`);
      if (o.contracts > 1) parts.push(`${o.contracts} contracts`);
      rows.push({
        key: `${g.underlying}:${o.symbol}`,
        kind,
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
