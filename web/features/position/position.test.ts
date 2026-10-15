import { describe, expect, it } from "vitest";
import { chartLines, keptSoFar, nowLines, openedOn, positionTitle, rangeChange, sliceBars, strikeDistance, subline } from "./position";
import type { Bar, PositionDetail } from "./types";

const bar = (time: string, close: number): Bar => ({ time, open: close, high: close, low: close, close, volume: 1 });

function detail(over: Partial<PositionDetail> = {}): PositionDetail {
  return {
    as_of: "",
    underlying: "AAPL",
    slug: "2099-01-15_P180",
    kind: "option",
    held: true,
    source: "monitor",
    degraded: false,
    option: {
      as_of: "", symbol: "x", right: "P", strike: 180, expiry: "2099-01-15", dte: 39, contracts: 1, short: true,
      delta: -0.2, delta_source: "ibkr", market_price: 0.62, market_value: -62, unrealized_pnl: 173,
      moneyness: "otm", assignment_risk: false,
    },
    stock: null,
    campaign: null,
    spread: null,
    opened: {
      key: "c1:opened", action: "opened", how: null, kind: "csp", source: "wheel", underlying: "AAPL", right: "P", strike: 180,
      long_strike: null, expiry: "2099-01-15", contracts: 1, at: "2026-10-03T14:42:00Z", is_live: false, premium: 235,
      bought_back: null, commissions: 1.3, commissions_complete: true, net_pnl: null, capital: 18000, roc_pct: 1.3,
      annualized_pct: 12.2, pct_kept: null, dte_at_open: 42, days_held: null, reason: null, facts: [], approval_id: 7,
      review: null, rolled_to: null,
    },
    closed: null,
    spreads_available: true,
    ...over,
  } as PositionDetail;
}

describe("sliceBars", () => {
  const bars = ["2026-04-14", "2026-07-14", "2026-09-14", "2026-10-01", "2026-10-14"].map((t, i) => bar(t, 100 + i));
  it("keeps calendar months back from the last bar", () => {
    expect(sliceBars(bars, 1).map((b) => b.time)).toEqual(["2026-09-14", "2026-10-01", "2026-10-14"]);
    expect(sliceBars(bars, 3).map((b) => b.time)).toEqual(["2026-07-14", "2026-09-14", "2026-10-01", "2026-10-14"]);
    expect(sliceBars(bars, 12)).toHaveLength(5);
  });
  it("is empty for no bars", () => expect(sliceBars([], 3)).toEqual([]));
});

describe("rangeChange", () => {
  it("is the first close to the last", () => {
    const c = rangeChange([bar("a", 100), bar("b", 110)]);
    expect(c).toEqual({ delta: 10, pct: 10 });
  });
  it("is null when there is nothing to compare, never 0", () => {
    expect(rangeChange([bar("a", 100)])).toBeNull();
    expect(rangeChange([])).toBeNull();
  });
});

describe("titles and lines", () => {
  it("names the contract", () => {
    expect(positionTitle(detail())).toBe("AAPL $180 put");
    expect(positionTitle(detail({ option: null }))).toBe("AAPL $180 put"); // a closed contract: from its opening
    expect(positionTitle(detail({ kind: "shares", stock: { shares: 100 } as never }))).toBe("AAPL · 100 shares");
    expect(positionTitle(detail({ kind: "spread", underlying: "SPY", spread: { short_strike: 580, long_strike: 575, side: "put" } as never }))).toBe("SPY 580/575 put spread");
  });
  it("draws the strike across the chart", () => {
    expect(chartLines(detail())).toEqual([{ price: 180, title: "Strike $180" }]);
  });
  it("draws a cost basis for shares, and the adjusted one only when it differs", () => {
    const stock = { shares: 100, avg_cost: 181, adjusted_cost_basis: 176.5 } as never;
    expect(chartLines(detail({ kind: "shares", stock }))).toEqual([
      { price: 181, title: "Avg cost $181" },
      { price: 176.5, title: "Adjusted $176.5" },
    ]);
    expect(chartLines(detail({ kind: "shares", stock: { shares: 100, avg_cost: 181, adjusted_cost_basis: null } as never }))).toHaveLength(1);
  });
  it("draws both strikes of a spread", () => {
    const spread = { short_strike: 580, long_strike: 575, side: "put" } as never;
    expect(chartLines(detail({ kind: "spread", spread })).map((l) => l.price)).toEqual([580, 575]);
  });
});

describe("openedOn", () => {
  it("is the New York day it was sold", () => {
    expect(openedOn(detail())).toBe("2026-10-03");
    expect(openedOn(detail({ opened: { ...detail().opened!, at: "2026-10-04T02:00:00Z" } }))).toBe("2026-10-03");
  });
  it("is unknown when the system never opened it", () => expect(openedOn(detail({ opened: null }))).toBeNull());
});

describe("how it stands", () => {
  it("says where the stock is against the strike, in words", () => {
    expect(strikeDistance(184.2, 180)).toBe("2.3% above the strike");
    expect(strikeDistance(170, 180)).toBe("5.6% below the strike");
    expect(strikeDistance(180, 180)).toBe("at the strike");
    expect(strikeDistance(null, 180)).toBeNull();
  });
  it("works out the premium kept from what it sold for and what it costs to close", () => {
    // sold at $2.35 a share, closes at $0.62 now
    expect(keptSoFar(detail())).toBeCloseTo(73.6, 1);
    expect(keptSoFar(detail({ option: { ...detail().option!, market_price: null } }))).toBeNull();
    expect(keptSoFar(detail({ opened: null }))).toBeNull();
  });
  it("lists the now figures, signed, with unknowns left unknown", () => {
    const lines = nowLines(detail(), 184.2);
    expect(lines.map((l) => l.label)).toEqual(["Open P&L", "Premium kept so far", "Time left", "Last close"]);
    expect(lines[0]).toEqual({ label: "Open P&L", value: "+$173.00", tone: "gain" });
    expect(lines[2].value).toBe("39 days");
    expect(lines[3].value).toBe("$184.20, 2.3% above the strike");
    const unknown = nowLines(detail({ option: { ...detail().option!, unrealized_pnl: null, dte: 0, market_price: null } }), null);
    expect(unknown[0].tone).toBe("unknown");
    expect(unknown.map((l) => l.label)).toEqual(["Open P&L", "Time left"]);
    expect(unknown[1].value).toBe("Expires today");
  });
  it("has no now figures for a contract that is no longer held", () => {
    expect(nowLines(detail({ held: false, option: null }), 184)).toEqual([]);
  });
});

describe("subline", () => {
  it("says when it expires and when it was sold", () => {
    expect(subline(detail())).toBe("Expires Thu, Jan 15 · sold Sat, Oct 3");
  });
  it("says it is no longer held, and when it was rolled", () => {
    const closed = { ...detail().opened!, action: "closed", how: "bought_back" } as never;
    expect(subline(detail({ held: false, option: null, closed }))).toBe("Expired Thu, Jan 15 · sold Sat, Oct 3 · no longer held");
    expect(subline(detail({ held: false, option: null, closed: { ...(closed as object), how: "rolled" } as never }))).toContain("rolled");
  });
});
