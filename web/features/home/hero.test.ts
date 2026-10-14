import { describe, expect, it } from "vitest";
import { chartPoints, heroFigures } from "./hero";
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

describe("chartPoints", () => {
  const at = (iso: string) => Math.floor(Date.parse(iso) / 1000);
  it("keeps the last point of a second and remembers which input row it was", () => {
    expect(
      chartPoints([
        { at: "2026-10-13T14:00:00.100Z", value: 1 },
        { at: "2026-10-13T14:00:00.900Z", value: 2 },
        { at: "2026-10-13T14:00:05Z", value: 3 },
      ]),
    ).toEqual([
      { time: at("2026-10-13T14:00:00Z"), value: 2, index: 1 },
      { time: at("2026-10-13T14:00:05Z"), value: 3, index: 2 },
    ]);
  });
  it("sorts rows that arrive out of order and lets the later instant win a tie", () => {
    const out = chartPoints([
      { at: "2026-10-13T14:00:09Z", value: 9 },
      { at: "2026-10-13T14:00:01.800Z", value: 18 },
      { at: "2026-10-13T14:00:01.200Z", value: 12 },
    ]);
    expect(out.map((p) => p.value)).toEqual([18, 9]);
    expect(out.map((p) => p.index)).toEqual([1, 0]);
  });
  it("leaves out a point whose timestamp cannot be read instead of handing the chart NaN", () => {
    expect(chartPoints([{ at: "not a date", value: 1 }, { at: "2026-10-13T14:00:00Z", value: 2 }])).toEqual([
      { time: at("2026-10-13T14:00:00Z"), value: 2, index: 1 },
    ]);
    expect(chartPoints([])).toEqual([]);
  });
});
