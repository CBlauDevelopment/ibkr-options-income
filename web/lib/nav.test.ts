import { describe, expect, it } from "vitest";
import { NAV, activeKey } from "./nav";

describe("activeKey", () => {
  it("matches Home only exactly", () => {
    expect(activeKey("/")).toBe("home");
    expect(activeKey("/unknown")).toBeNull();
  });
  it("matches a section and its children", () => {
    expect(activeKey("/trades")).toBe("trades");
    expect(activeKey("/trades/41")).toBe("trades");
    expect(activeKey("/ledger/trades")).toBe("activity");
    expect(activeKey("/stock/AAPL")).toBe("research");
    expect(activeKey("/explain")).toBe("more");
  });
  it("does not match a prefix that is not a path segment", () => {
    expect(activeKey("/tradesman")).toBeNull();
  });
});

describe("NAV", () => {
  it("puts exactly five destinations on the phone tab bar", () => {
    expect(NAV.filter((n) => n.phone).map((n) => n.key)).toEqual([
      "home",
      "trades",
      "portfolio",
      "activity",
      "more",
    ]);
  });
});
