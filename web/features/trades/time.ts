const TIME_ET = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" });
const DAY = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
/** en-CA formats as YYYY-MM-DD. */
const NEW_YORK_DAY = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" });

export function timeET(iso: string): string {
  const t = Date.parse(iso);
  // Some ICU builds put a narrow no-break space before AM/PM; the label uses a plain one.
  return Number.isNaN(t) ? "time n/a" : `${TIME_ET.format(new Date(t)).replace(/[  ]/g, " ")} ET`;
}

/** "Thu, Oct 15" for a "YYYY-MM-DD" New York day (formatted in UTC so the date never shifts). */
export function dayLabel(isoDate: string): string {
  return DAY.format(new Date(`${isoDate}T00:00:00Z`));
}

/** The New York calendar day an instant falls on, or null for an unreadable one. */
export function newYorkDay(iso: string): string | null {
  const t = Date.parse(iso);
  return Number.isNaN(t) ? null : NEW_YORK_DAY.format(new Date(t));
}

export function todayInNewYork(now: Date = new Date()): string {
  return NEW_YORK_DAY.format(now);
}

export function shiftDay(isoDate: string, n: number): string {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
