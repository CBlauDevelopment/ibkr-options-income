import { describe, expect, it } from "vitest";
import { daysToExpiry, decisionWords, proposalSentence, proposalStub, rollSentence, rollStub, rollTitle } from "./proposal";

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

const roll = {
  underlying: "NVDA", strike: 250, expiry: "2026-10-28", right: "P", contracts: 1, premium: 1.175,
  roll_from: { strike: 250, expiry: "2026-10-23", right: "P", contracts: 1, old_mid: 2.1, new_mid: 3.275 },
};

describe("rolls", () => {
  it("titles a roll with both legs", () => {
    expect(rollTitle(roll)).toBe("NVDA · Roll $250 put Oct 23 → Oct 28");
    expect(rollTitle({ ...roll, strike: 245, expiry: "2026-11-20" })).toBe("NVDA · Roll $250 → $245 put Oct 23 → Nov 20");
    expect(rollTitle({ ...roll, expiry: "2026-10-23", strike: 255 })).toBe("NVDA · Roll $250 → $255 put Oct 23");
  });
  it("keeps the plain title for a roll frozen before its legs were recorded", () => {
    expect(rollTitle({ ...roll, roll_from: null })).toBe("NVDA · Roll");
  });
  it("says what it buys back and sells, and the net at the quotes it was priced at", () => {
    expect(rollSentence(roll)).toBe(
      "Buys back the $250 put expiring Oct 23 and sells the $250 put expiring Oct 28. At the quotes it was priced at, that is a net credit of $117.50.",
    );
    expect(rollSentence({ ...roll, premium: -0.4 })).toMatch(/a net debit of \$40\.00\.$/);
    expect(rollSentence({ ...roll, premium: null })).toMatch(/The net is not known\.$/);
  });
  it("sums the two legs to the net", () => {
    const lines = rollStub(roll);
    expect(lines.map((l) => l.label)).toEqual(["Buy back $250 put Oct 23", "Sell $250 put Oct 28", "Net credit"]);
    expect(lines[0].value).toBeCloseTo(-210);
    expect(lines[1].value).toBeCloseTo(327.5);
    expect(lines[2].value).toBeCloseTo(117.5);
    expect(lines[2].total).toBe(true);
    expect(rollStub({ ...roll, premium: -0.4 })[2].label).toBe("Net debit");
  });
  it("leaves an unknown leg unknown, never zero", () => {
    expect(rollStub({ ...roll, roll_from: { ...roll.roll_from, old_mid: null } })[0].value).toBeNull();
    expect(rollStub({ ...roll, premium: null })[2].value).toBeNull();
  });
});

describe("decisionWords", () => {
  it("names who decided, from the record only", () => {
    expect(decisionWords("approved", "system")).toBe("Approved by the system");
    expect(decisionWords("approved", "web")).toBe("Approved by you, on the web");
    expect(decisionWords("rejected", "telegram")).toBe("Rejected by you, in Telegram");
    expect(decisionWords("approved", null)).toBe("Approved");
    expect(decisionWords("approved")).toBe("Approved");
    expect(decisionWords("expired", null)).toBe("Expired unanswered");
    expect(decisionWords("pending", null)).toBeNull();
  });
});
