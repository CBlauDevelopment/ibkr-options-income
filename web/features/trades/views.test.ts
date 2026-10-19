import { describe, expect, it } from "vitest";
import { defaultView, explicitView, tickerCounts, viewsFor } from "./views";

describe("viewsFor", () => {
  it("gives the wheel three views, under All too", () => {
    expect(viewsFor("all")).toEqual(["proposals", "history", "assessed"]);
    expect(viewsFor("csp")).toEqual(["proposals", "history", "assessed"]);
    expect(viewsFor("cc")).toEqual(["proposals", "history", "assessed"]);
  });
  it("offers only Spreads for credit spreads, which trade on their own", () => {
    expect(viewsFor("spread")).toEqual(["spreads"]);
  });
});

describe("explicitView", () => {
  it("keeps a view the strategy has", () => {
    expect(explicitView("assessed", "cc")).toBe("assessed");
    expect(explicitView("history", "all")).toBe("history");
  });
  it("opens History for the retired Working and Decided, so old links still land", () => {
    expect(explicitView("working", "all")).toBe("history");
    expect(explicitView("decided", "csp")).toBe("history");
  });
  it("is null for a junk or missing view, or one the strategy lacks", () => {
    expect(explicitView("foo", "all")).toBeNull();
    expect(explicitView(null, "all")).toBeNull();
    expect(explicitView(undefined, "csp")).toBeNull();
    expect(explicitView("spreads", "all")).toBeNull();
    expect(explicitView("history", "spread")).toBeNull();
  });
});

describe("defaultView", () => {
  it("opens Proposals when something waits on you, History when nothing does", () => {
    expect(defaultView("all", 2)).toBe("proposals");
    expect(defaultView("csp", 0)).toBe("history");
  });
  it("is unknown until the pending count is, except for credit spreads", () => {
    expect(defaultView("all", null)).toBeNull();
    expect(defaultView("spread", null)).toBe("spreads");
  });
  it("falls back to History when the pending count failed to load, and prefers a known count", () => {
    expect(defaultView("all", null, true)).toBe("history");
    expect(defaultView("all", 2, true)).toBe("proposals");
  });
});

describe("tickerCounts", () => {
  it("counts each underlying once, alphabetically", () => {
    expect(tickerCounts([{ underlying: "NVDA" }, { underlying: "AAPL" }, { underlying: "NVDA" }])).toEqual([
      { ticker: "AAPL", count: 1 },
      { ticker: "NVDA", count: 2 },
    ]);
  });
  it("is empty for no proposals", () => {
    expect(tickerCounts([])).toEqual([]);
  });
});
