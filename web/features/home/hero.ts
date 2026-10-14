import { formatDateTime, relativeAge } from "@/lib/format";
import { formatMoneyCell, isStale } from "@/lib/money";
import { FRESH_FOR_MINUTES } from "./positions";
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

const NY_CLOCK = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  weekday: "short",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** Monday to Friday, 09:30 to 16:00 New York time. The web does not know market holidays. */
export function inMarketHours(now: Date): boolean {
  const part = (type: string) => NY_CLOCK.formatToParts(now).find((p) => p.type === type)?.value;
  if (part("weekday") === "Sat" || part("weekday") === "Sun") return false;
  const minutes = Number(part("hour")) * 60 + Number(part("minute"));
  return minutes >= 9 * 60 + 30 && minutes < 16 * 60;
}

/**
 * The headline's age ("4h ago") when the hero should flag it Delayed, else null. The rule is the
 * positions card's (older than FRESH_FOR_MINUTES, read from the same snapshot table), applied
 * only in market hours: the monitor snapshots every ~15 minutes while the market is open, and
 * after the close or at a weekend the headline is the last close, which is right, not degraded.
 * An unknown or unreadable headline is never flagged; it already reads n/a.
 */
export function heroDelay(series: AccountValueSeries, now: Date): string | null {
  const at = series.latest_at;
  if (series.latest === null || !at || Number.isNaN(Date.parse(at))) return null;
  if (!inMarketHours(now) || !isStale(at, FRESH_FOR_MINUTES, now.getTime())) return null;
  return relativeAge(at, now.getTime());
}
