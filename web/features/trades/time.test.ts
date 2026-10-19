import { describe, expect, it } from "vitest";
import { dayLabel, newYorkDay, shiftDay, timeET, todayInNewYork } from "./time";

describe("time", () => {
  it("shows a time in New York", () => {
    expect(timeET("2026-10-15T14:17:30Z")).toBe("10:17 AM ET");
    expect(timeET("nope")).toBe("time n/a");
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
