import { formatDateTime } from "@/lib/format";
import { formatMoneyCell } from "@/lib/money";
import type { AccountValuePoint, AccountValueSeries } from "./types";

const DATE_ONLY = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "America/New_York",
});

/** "Oct 12, 2026" in New York time (the market's day). Empty for an unparseable timestamp. */
export function formatDay(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : DATE_ONLY.format(d);
}

/** One point as the chart takes it: whole-second time, plus the row of `points` it came from. */
export type ChartPoint = { time: number; value: number; index: number };

/**
 * lightweight-charts wants strictly ascending whole-second times and throws on a tie, and
 * snapshot rows can share a captured_at (a refresh moments after a monitor write). So: one point
 * per second, the one with the later instant (the later row wins an exact tie), sorted ascending,
 * and unreadable timestamps left out. `index` maps a plotted point back to `series.points`, which
 * is what the hover figures read.
 */
export function chartPoints(points: AccountValuePoint[]): ChartPoint[] {
  const bySecond = new Map<number, ChartPoint & { ms: number }>();
  points.forEach((p, index) => {
    const ms = Date.parse(p.at);
    if (!Number.isFinite(ms)) return;
    const time = Math.floor(ms / 1000);
    const kept = bySecond.get(time);
    if (kept === undefined || ms >= kept.ms) bySecond.set(time, { time, value: p.value, index, ms });
  });
  return [...bySecond.values()]
    .sort((a, b) => a.time - b.time)
    .map(({ time, value, index }) => ({ time, value, index }));
}

/** The words a screen reader hears for one chart point (the chart itself is a canvas). */
export function pointLabel(p: AccountValuePoint): string {
  return `${formatDateTime(p.at)}, ${formatMoneyCell(p.value)}`;
}

export function heroFigures(
  series: AccountValueSeries,
  hoverIndex: number | null,
): { value: number | null; delta: number | null; deltaPct: number | null; caption: string } {
  if (hoverIndex === null || !series.points[hoverIndex]) {
    return {
      value: series.latest,
      delta: series.change_today,
      deltaPct: series.change_today_pct,
      caption: "today",
    };
  }
  const p = series.points[hoverIndex];
  const base = series.points[0].value;
  const delta = p.value - base;
  const intraday = series.range === "1d" || series.range === "1w";
  return {
    value: p.value,
    delta,
    deltaPct: base ? (delta / base) * 100 : null,
    caption: intraday ? formatDateTime(p.at) : formatDay(p.at),
  };
}
