import type { StrategyFilter } from "@/lib/strategy";

/** The Trades page's views (web/DESIGN.md Surfaces → Trades). */
export type TradesView = "proposals" | "history" | "assessed" | "spreads";

export const VIEW_LABEL: Record<TradesView, string> = {
  proposals: "Proposals",
  history: "History",
  assessed: "Assessed",
  spreads: "Spreads",
};

/** Views retired in the 2026-10-19 revision. Old links open History, where their rows now live. */
const RETIRED: Record<string, TradesView> = { working: "history", decided: "history" };

/** Which views a strategy has. Credit spreads trade on their own: nothing to approve or assess. */
export function viewsFor(strategy: StrategyFilter): TradesView[] {
  return strategy === "spread" ? ["spreads"] : ["proposals", "history", "assessed"];
}

/** The view the URL asks for, when this strategy has it; null when it asks for none or one it lacks. */
export function explicitView(raw: string | null | undefined, strategy: StrategyFilter): TradesView | null {
  const name = raw ? (RETIRED[raw] ?? raw) : null;
  return name !== null && (viewsFor(strategy) as string[]).includes(name) ? (name as TradesView) : null;
}

/**
 * With no view asked for: Proposals when something waits on you, History otherwise (the account
 * runs on full autonomy, so most visits have nothing to approve). Null until the count is known.
 * When the pending proposals could not be loaded (`failed`), the count never arrives, so the
 * answer is History, the "nothing waits on you" default, rather than a skeleton that never ends.
 */
export function defaultView(strategy: StrategyFilter, pending: number | null, failed = false): TradesView | null {
  if (strategy === "spread") return "spreads";
  if (pending === null) return failed ? "history" : null;
  return pending > 0 ? "proposals" : "history";
}

export type TickerCount = { ticker: string; count: number };

/** One chip per underlying, alphabetical, with how many proposals each has. */
export function tickerCounts(items: { underlying: string }[]): TickerCount[] {
  const counts = new Map<string, number>();
  for (const i of items) counts.set(i.underlying, (counts.get(i.underlying) ?? 0) + 1);
  return [...counts]
    .map(([ticker, count]) => ({ ticker, count }))
    .sort((a, b) => a.ticker.localeCompare(b.ticker));
}
