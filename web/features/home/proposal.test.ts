import { describe, expect, it } from "vitest";
import { daysToExpiry, proposalSentence, proposalStub } from "./proposal";

const TODAY = new Date("2026-10-13T12:00:00Z");
const csp = { underlying: "AAPL", strategy: "cash_secured_put", right: "P", strike: 180, contracts: 1, premium: 2.35, expiry: "2026-11-21" };

describe("daysToExpiry", () => {
  it("counts calendar days", () => {
    expect(daysToExpiry("2026-11-21", TODAY)).toBe(39);
    expect(daysToExpiry(null, TODAY)).toBeNull();
  });
  it("counts from today in New York, the market's day, not today in UTC", () => {
    // 01:00 UTC on Oct 14 is 21:00 on Oct 13 in New York (09:00 in Singapore, the operator's
    // morning check): an Oct 14 expiry is still one day away, not today.
    const morningInSingapore = new Date("2026-10-14T01:00:00Z");
    expect(daysToExpiry("2026-10-14", morningInSingapore)).toBe(1);
    expect(daysToExpiry("2026-10-13", morningInSingapore)).toBe(0);
  });
});

describe("proposalSentence", () => {
  it("states a put's consequence first", () => {
    expect(proposalSentence(csp)).toBe(
      "You collect $235.00. If AAPL closes under $180 on Nov 21, you buy 100 shares at $180.",
    );
  });
  it("states a call's consequence first", () => {
    expect(proposalSentence({ ...csp, strategy: "covered_call", right: "C", strike: 72, premium: 0.64, underlying: "KO", expiry: "2026-11-14" })).toBe(
      "You collect $64.00. If KO closes over $72 on Nov 14, your 100 shares are sold at $72.",
    );
  });
  it("never invents a premium", () => {
    expect(proposalSentence({ ...csp, premium: null })).toBe(
      "Premium not known yet. If AAPL closes under $180 on Nov 21, you buy 100 shares at $180.",
    );
  });
});

describe("proposalStub", () => {
  it("shows the put's math line by line", () => {
    const lines = proposalStub(csp, TODAY);
    expect(lines.map((l) => [l.label, l.value])).toEqual([
      ["Premium", 235],
      ["Cash held aside", 18000],
      ["Return in 39 days", (235 / 18000) * 100],
      ["A year", (235 / 18000) * 100 * (365 / 39)],
    ]);
    expect(lines[3].total).toBe(true);
  });
  it("uses the strike value for a call", () => {
    const lines = proposalStub({ ...csp, strategy: "covered_call", right: "C", strike: 72, premium: 0.64 }, TODAY);
    expect(lines[1]).toMatchObject({ label: "If called, you sell for", value: 7200 });
  });
  it("turns every derived line to n/a when the premium is unknown", () => {
    const lines = proposalStub({ ...csp, premium: null }, TODAY);
    expect(lines.map((l) => l.value)).toEqual([null, 18000, null, null]);
  });
  it("says 1 day, not 1 days", () => {
    const lines = proposalStub({ ...csp, expiry: "2026-10-14" }, TODAY);
    expect(lines[2].label).toBe("Return in 1 day");
  });
  it("has no annual figure on expiry day", () => {
    const lines = proposalStub({ ...csp, expiry: "2026-10-13" }, TODAY);
    expect(lines[3].value).toBeNull();
  });
});
