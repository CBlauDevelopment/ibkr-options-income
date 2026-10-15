/** The realised-P&L calendar's dates and figures. Months are New York months ("YYYY-MM"). */

const NY_MONTH = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York", year: "numeric", month: "2-digit" });
const TITLE = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" });
const DAY = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });

const MINUS = "−";

/** The New York month `now` falls in, "YYYY-MM". */
export function currentMonth(now: Date = new Date()): string {
  return NY_MONTH.format(now).slice(0, 7);
}

export function shiftMonth(month: string, by: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + by, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

export function monthTitle(month: string): string {
  return TITLE.format(new Date(`${month}-01T00:00:00Z`));
}

/** "Fri, Oct 9" for a "YYYY-MM-DD" date. */
export function dayLabel(date: string): string {
  return DAY.format(new Date(`${date}T00:00:00Z`));
}

export type Cell = { date: string; day: number } | null;

/** The month as weeks of seven, Monday first, with null padding either end. */
export function monthWeeks(month: string): Cell[][] {
  const [y, m] = month.split("-").map(Number);
  const first = new Date(Date.UTC(y, m - 1, 1));
  const length = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const lead = (first.getUTCDay() + 6) % 7; // Monday = 0
  const cells: Cell[] = Array.from({ length: lead }, () => null);
  for (let day = 1; day <= length; day++) cells.push({ date: `${month}-${String(day).padStart(2, "0")}`, day });
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks: Cell[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}

/** A day's result as it fits a calendar cell: always signed, whole dollars, K from $10,000. */
export function compactMoney(v: number): string {
  if (v === 0) return "$0";
  const sign = v > 0 ? "+" : MINUS;
  const a = Math.abs(v);
  if (a < 1) return `${sign}$${a.toFixed(2)}`;
  if (a >= 10_000) return `${sign}$${(a / 1000).toFixed(1)}K`;
  return `${sign}$${Math.round(a).toLocaleString("en-US")}`;
}
