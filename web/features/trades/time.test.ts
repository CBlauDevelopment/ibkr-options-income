import { describe, expect, it } from "vitest";
import { dayLabel, isCalendarDay, newYorkDay, shiftDay, timeET, todayInNewYork } from "./time";

describe("time", () => {
  it("shows a time in New York", () => {
    expect(timeET("2026-10-15T14:17:30Z")).toBe("10:17 AM ET");
    expect(timeET("nope")).toBe("time n/a");
  });
  it("accepts only a real calendar date", () => {
    expect(isCalendarDay("2026-10-15")).toBe(true);
    expect(isCalendarDay("2028-02-29")).toBe(true);
    for (const bad of ["2026-13-45", "2026-02-30", "2025-02-29", "2026-00-10", "2026-10-00", "2026-1-5", "today", ""]) {
      expect(isCalendarDay(bad), bad).toBe(false);
    }
  });
  it("labels a day without shifting it", () => {
    expect(dayLabel("2026-10-15")).toBe("Thu, Oct 15");
  });
  it("puts an instant on its New York day", () => {
    expect(newYorkDay("2026-10-16T02:00:00Z")).toBe("2026-10-15");
    expect(newYorkDay("2026-10-15T14:00:00Z")).toBe("2026-10-15");
    expect(newYorkDay("nope")).toBeNull();
  });
  it("knows today in New York, not in UTC", () => {
    expect(todayInNewYork(new Date("2026-10-16T02:00:00Z"))).toBe("2026-10-15");
  });
  it("shifts a day across a month end", () => {
    expect(shiftDay("2026-10-31", 1)).toBe("2026-11-01");
    expect(shiftDay("2026-11-01", -1)).toBe("2026-10-31");
  });
});
