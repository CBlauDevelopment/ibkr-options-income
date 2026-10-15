import { describe, expect, it } from "vitest";
import { cellFigure, currentMonth, dayLabel, monthTitle, monthWeeks, shiftMonth } from "./calendar";

describe("months", () => {
  it("names the current month in New York time, not the viewer's", () => {
    expect(currentMonth(new Date("2026-10-15T07:00:00Z"))).toBe("2026-10");
    // 02:00 UTC on 1 Nov is still 22:00 on 31 Oct in New York.
    expect(currentMonth(new Date("2026-11-01T02:00:00Z"))).toBe("2026-10");
    expect(currentMonth(new Date("2026-11-01T05:00:00Z"))).toBe("2026-11");
  });
  it("steps across year ends", () => {
    expect(shiftMonth("2026-10", -1)).toBe("2026-09");
    expect(shiftMonth("2026-01", -1)).toBe("2025-12");
    expect(shiftMonth("2026-12", 1)).toBe("2027-01");
  });
  it("titles a month in words", () => {
    expect(monthTitle("2026-10")).toBe("October 2026");
  });
  it("labels a day in words", () => {
    expect(dayLabel("2026-10-09")).toBe("Fri, Oct 9");
  });
});

describe("monthWeeks", () => {
  it("lays October 2026 out Monday first, padding the ends with nothing", () => {
    const weeks = monthWeeks("2026-10");
    expect(weeks.every((w) => w.length === 7)).toBe(true);
    // 1 Oct 2026 is a Thursday: three blanks, then 1, 2, 3, 4.
    expect(weeks[0].map((c) => c?.day ?? null)).toEqual([null, null, null, 1, 2, 3, 4]);
    expect(weeks.at(-1)!.map((c) => c?.day ?? null)).toEqual([26, 27, 28, 29, 30, 31, null]);
    expect(weeks.flat().filter(Boolean)).toHaveLength(31);
    expect(weeks[0][3]).toEqual({ date: "2026-10-01", day: 1 });
  });
  it("handles a month that starts on Monday and one that ends on Sunday", () => {
    const june = monthWeeks("2027-02"); // 1 Feb 2027 is a Monday, 28 days
    expect(june).toHaveLength(4);
    expect(june[0][0]).toEqual({ date: "2027-02-01", day: 1 });
    expect(june.at(-1)!.at(-1)).toEqual({ date: "2027-02-28", day: 28 });
  });
});

describe("cellFigure", () => {
  it("signs every figure, with no currency sign, and keeps whole dollars under a thousand", () => {
    expect(cellFigure(412.5)).toBe("+413");
    expect(cellFigure(-230.04)).toBe("−230");
    expect(cellFigure(999.4)).toBe("+999");
  });
  it("shortens thousands so a cell never overflows", () => {
    expect(cellFigure(1717.88)).toBe("+1.7K");
    expect(cellFigure(-1603.7)).toBe("−1.6K");
    expect(cellFigure(12400)).toBe("+12K");
    expect(cellFigure(-10050)).toBe("−10K");
  });
  it("keeps cents under a dollar, so a real result never reads as zero", () => {
    expect(cellFigure(0.3)).toBe("+0.30");
    expect(cellFigure(-0.04)).toBe("−0.04");
  });
  it("a genuine zero is plain", () => {
    expect(cellFigure(0)).toBe("0");
  });
});
