import { describe, expect, it } from "vitest";
import { buildPositionRows } from "./positions";

const TODAY = "2026-10-13";

const optionLeg = (over: Record<string, unknown> = {}) => ({
  as_of: "",
  symbol: "AMD 261024P00150000",
  right: "P",
  strike: 150,
  expiry: "2026-10-24",
  dte: 11,
  contracts: 1,
  short: true,
  delta: -0.4,
  delta_source: "ibkr",
  market_price: 3.1,
  market_value: -310,
  unrealized_pnl: -212,
  moneyness: "itm",
  assignment_risk: true,
  ...over,
});

const group = (underlying: string, options: unknown[], stock: unknown = null) => ({
  as_of: "",
  underlying,
  stock,
  options,
});

describe("buildPositionRows", () => {
  it("names a short put a CSP and flags assignment risk in words", () => {
    const [row] = buildPositionRows([group("AMD", [optionLeg()])] as never, [], TODAY);
    expect(row.kind).toBe("csp");
    expect(row.title).toBe("AMD $150 put");
    expect(row.status).toEqual({ word: "Assignment likely", tone: "flag" });
    expect(row.value).toBe(-212);
    expect(row.valueLabel).toBe("open P&L");
  });
  it("says Expires today on expiry day, ahead of any other status", () => {
    const [row] = buildPositionRows(
      [group("MSFT", [optionLeg({ right: "C", strike: 430, dte: 0, expiry: TODAY, assignment_risk: true })])] as never,
      [],
      TODAY,
    );
    expect(row.kind).toBe("cc");
    expect(row.status).toEqual({ word: "Expires today", tone: "today" });
  });
  it("states moneyness only when it is known", () => {
    const rows = buildPositionRows(
      [
        group("KO", [optionLeg({ moneyness: "otm", assignment_risk: false })]),
        group("PEP", [optionLeg({ moneyness: null, assignment_risk: false })]),
      ] as never,
      [],
      TODAY,
    );
    expect(rows.find((r) => r.title.startsWith("KO"))!.status).toEqual({ word: "Out of the money", tone: "neutral" });
    expect(rows.find((r) => r.title.startsWith("PEP"))!.status).toBeNull();
  });
  it("notes a covered call's cover only when the shares are really held", () => {
    const stock = { as_of: "", shares: 100, avg_cost: 60, adjusted_cost_basis: null, market_price: 70, market_value: 7000, unrealized_pnl: 1000, unrealized_pnl_adjusted: null };
    const rows = buildPositionRows([group("KO", [optionLeg({ right: "C", strike: 72 })], stock)] as never, [], TODAY);
    expect(rows.find((r) => r.kind === "cc")!.sub).toContain("covered by 100 shares");
    expect(rows.find((r) => r.kind === "shares")!.title).toBe("KO · 100 shares");
  });
  it("keeps an unknown P&L unknown", () => {
    const [row] = buildPositionRows([group("AMD", [optionLeg({ unrealized_pnl: null })])] as never, [], TODAY);
    expect(row.value).toBeNull();
  });
  it("adds spreads with what they were sold for", () => {
    const rows = buildPositionRows([], [
      { spread_id: "s1", mode: "paper", side: "put", expiry: TODAY, short_strike: 580, long_strike: 575, width: 5, contracts_opened: 1, contracts: 1, entry_credit: 0.42, entry_commission: 1.3, opened_at: "", status: "open", exit_debit: null, realized_pnl_usd: null },
    ] as never, TODAY, "SPY");
    expect(rows[0]).toMatchObject({ kind: "spread", title: "SPY 580/575 put spread", value: 42, valueLabel: "sold for" });
    expect(rows[0].status).toEqual({ word: "Expires today", tone: "today" });
  });
  it("sorts by expiry, shares last", () => {
    const stock = { as_of: "", shares: 100, avg_cost: 60, adjusted_cost_basis: null, market_price: 70, market_value: 7000, unrealized_pnl: 1000, unrealized_pnl_adjusted: null };
    const rows = buildPositionRows(
      [group("A", [optionLeg({ expiry: "2026-11-21" })], stock), group("B", [optionLeg({ expiry: "2026-10-24" })])] as never,
      [],
      TODAY,
    );
    expect(rows.map((r) => r.kind)).toEqual(["csp", "csp", "shares"]);
    expect(rows[0].title.startsWith("B")).toBe(true);
  });
  it("does not invent a strike or a right the API left out", () => {
    const [row] = buildPositionRows(
      [group("AMD", [optionLeg({ strike: null, right: null })])] as never,
      [],
      TODAY,
    );
    expect(row.kind).toBe("other");
    expect(row.title).toBe("AMD strike n/a option");
  });
});
