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
