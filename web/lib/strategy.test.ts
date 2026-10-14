import { describe, expect, it } from "vitest";
import { kindOf, matchesFilter, parseStrategyFilter } from "./strategy";

describe("kindOf", () => {
  it("maps the backend's strategy names", () => {
    expect(kindOf("cash_secured_put", "P")).toBe("csp");
    expect(kindOf("covered_call", "C")).toBe("cc");
    expect(kindOf("credit_spread", null)).toBe("spread");
  });
  it("files a roll under the side it rolls", () => {
    expect(kindOf("roll", "P")).toBe("csp");
    expect(kindOf("roll", "C")).toBe("cc");
    expect(kindOf("roll", null)).toBeNull();
  });
  it("returns null for anything it does not know", () => {
    expect(kindOf("iron_condor", "P")).toBeNull();
    expect(kindOf(undefined, undefined)).toBeNull();
  });
});

describe("parseStrategyFilter", () => {
  it("treats a junk or missing value as All", () => {
    expect(parseStrategyFilter("foo")).toBe("all");
    expect(parseStrategyFilter(null)).toBe("all");
  });
  it("keeps real values", () => {
    expect(parseStrategyFilter("csp")).toBe("csp");
    expect(parseStrategyFilter("spread")).toBe("spread");
  });
});

describe("matchesFilter", () => {
  it("All matches everything, even an unknown kind", () => {
    expect(matchesFilter(null, "all")).toBe(true);
    expect(matchesFilter("cc", "all")).toBe(true);
  });
  it("a specific filter matches only its kind", () => {
    expect(matchesFilter("cc", "csp")).toBe(false);
    expect(matchesFilter(null, "csp")).toBe(false);
    expect(matchesFilter("csp", "csp")).toBe(true);
  });
});
