import { describe, expect, it } from "vitest";
import { draftOf, parseNumber, payloadOf, previewSentence, sameTarget, type TargetDraft } from "./target";

const draft = (over: Partial<TargetDraft>): TargetDraft => ({
  mode: "fixed",
  amount: "",
  pct: "",
  base: "",
  ...over,
});

describe("parseNumber", () => {
  it("reads plain, comma and symbol-decorated numbers", () => {
    expect(parseNumber("2000")).toBe(2000);
    expect(parseNumber(" $2,000.50 ")).toBe(2000.5);
    expect(parseNumber("1.5%")).toBe(1.5);
  });
  it("refuses empty, words and non-finite values", () => {
    for (const bad of ["", "  ", "abc", "1e999", "1.2.3", "--4", "NaN"]) expect(parseNumber(bad)).toBeNull();
  });
});

describe("draftOf", () => {
  it("turns a stored target into the form's text", () => {
    expect(draftOf({ mode: "pct_of_amount", amount: null, pct: 2, base: 100000 })).toEqual({
      mode: "pct_of_amount",
      amount: "",
      pct: "2",
      base: "100000",
    });
    expect(draftOf({ mode: "off", amount: null, pct: null, base: null }).mode).toBe("off");
  });
});

describe("payloadOf", () => {
  it("sends only the fields that belong to the mode", () => {
    expect(payloadOf(draft({ mode: "fixed", amount: "1,500", pct: "9", base: "9" }))).toEqual({
      ok: true,
      payload: { mode: "fixed", amount: 1500 },
    });
    expect(payloadOf(draft({ mode: "pct_of_account", pct: "1.5", amount: "9" }))).toEqual({
      ok: true,
      payload: { mode: "pct_of_account", pct: 1.5 },
    });
    expect(payloadOf(draft({ mode: "pct_of_amount", pct: "2", base: "100000" }))).toEqual({
      ok: true,
      payload: { mode: "pct_of_amount", pct: 2, base: 100000 },
    });
    expect(payloadOf(draft({ mode: "off" }))).toEqual({ ok: true, payload: { mode: "off" } });
  });
  it("names each field that is missing or out of range, in words", () => {
    const r = payloadOf(draft({ mode: "pct_of_amount", pct: "25", base: "" }));
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.errors.pct).toMatch(/above 0 and up to 20/);
      expect(r.errors.base).toMatch(/amount/i);
    }
    const f = payloadOf(draft({ mode: "fixed", amount: "0" }));
    expect(f.ok).toBe(false);
    const big = payloadOf(draft({ mode: "fixed", amount: "2000000" }));
    expect(big.ok).toBe(false);
  });
});

describe("previewSentence", () => {
  it("states each mode as a sum the operator can check", () => {
    expect(previewSentence(draft({ mode: "fixed", amount: "2000" }), null, "October")).toBe(
      "The pay card aims for $2,000 a month.",
    );
    expect(previewSentence(draft({ mode: "pct_of_amount", pct: "2", base: "100000" }), null, "October")).toBe(
      "2% of $100,000 is $2,000 a month.",
    );
    expect(previewSentence(draft({ mode: "pct_of_account", pct: "1.5" }), 200000, "October")).toBe(
      "1.5% of $200,000, the account's value when October began, is $3,000 for October.",
    );
    expect(previewSentence(draft({ mode: "off" }), null, "October")).toBe(
      "No target. The pay card shows the month's income without a goal.",
    );
  });
  it("says so when a percent of the account has no opening value to work from", () => {
    expect(previewSentence(draft({ mode: "pct_of_account", pct: "1.5" }), null, "October")).toBe(
      "1.5% of the account's value when each month begins. October's opening value is not on record yet, so the pay card will say target n/a until it is.",
    );
  });
  it("is silent while the inputs are not a valid target", () => {
    expect(previewSentence(draft({ mode: "fixed", amount: "" }), null, "October")).toBeNull();
    expect(previewSentence(draft({ mode: "pct_of_account", pct: "50" }), 1000, "October")).toBeNull();
  });
});

describe("sameTarget", () => {
  it("compares the draft to the stored target by value", () => {
    const stored = { mode: "fixed" as const, amount: 2000, pct: null, base: null };
    expect(sameTarget(draft({ mode: "fixed", amount: "2,000" }), stored)).toBe(true);
    expect(sameTarget(draft({ mode: "fixed", amount: "2001" }), stored)).toBe(false);
    expect(sameTarget(draft({ mode: "off" }), { mode: "off", amount: null, pct: null, base: null })).toBe(true);
    expect(sameTarget(draft({ mode: "pct_of_account", pct: "1" }), stored)).toBe(false);
  });
});
