import { describe, expect, it } from "vitest";
import type { PositionGroupData } from "@/components/portfolio/types";
import { buildPositionRows } from "./positions";

const group = {
  as_of: "",
  underlying: "AAPL",
  stock: null,
  options: [
    {
      as_of: "", symbol: "AAPL  261121P00180000", right: "P", strike: 180, expiry: "2026-11-21", dte: 33,
      contracts: 1, short: true, delta: -0.2, delta_source: "ibkr", market_price: 0.6, market_value: -60,
      unrealized_pnl: 175, moneyness: "otm", assignment_risk: false,
    },
  ],
} as unknown as PositionGroupData;

describe("the Roll alert flag", () => {
  it("is set for a contract whose OCC symbol has an alert", () => {
    const [row] = buildPositionRows([group], [], "2026-10-19", "SPY", new Set(["AAPL  261121P00180000"]));
    expect(row.alert).toBe(true);
  });
  it("is off by default and for any other contract", () => {
    expect(buildPositionRows([group], [], "2026-10-19")[0].alert).toBe(false);
    expect(buildPositionRows([group], [], "2026-10-19", "SPY", new Set(["MSFT  261121C00420000"]))[0].alert).toBe(false);
  });
});
