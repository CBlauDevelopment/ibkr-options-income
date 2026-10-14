import { describe, expect, it } from "vitest";
import { heroFigures } from "./hero";
import type { AccountValueSeries } from "./types";

const series: AccountValueSeries = {
  range: "1m",
  points: [
    { at: "2026-10-01T20:00:00Z", value: 100_000 },
    { at: "2026-10-12T20:00:00Z", value: 101_000 },
    { at: "2026-10-13T18:00:00Z", value: 101_500 },
  ],
  latest: 101_500,
  latest_at: "2026-10-13T18:00:00Z",
  previous_close: 101_000,
  change_today: 500,
  change_today_pct: 0.495,
};

describe("heroFigures", () => {
  it("shows the latest value and today's change when not scrubbing", () => {
    expect(heroFigures(series, null)).toEqual({ value: 101_500, delta: 500, deltaPct: 0.495, caption: "today" });
  });
  it("shows the scrubbed point and its change since the range start", () => {
    const f = heroFigures(series, 1);
    expect(f.value).toBe(101_000);
    expect(f.delta).toBe(1_000);
    expect(f.deltaPct).toBeCloseTo(1);
    expect(f.caption).toBe("Oct 12, 2026");
  });
  it("keeps unknowns unknown", () => {
    const empty = { ...series, points: [], latest: null, change_today: null, change_today_pct: null };
    expect(heroFigures(empty, null)).toEqual({ value: null, delta: null, deltaPct: null, caption: "today" });
  });
});
