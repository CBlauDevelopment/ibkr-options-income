import { fireEvent, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { renderWithQuery } from "@/lib/test-query";
import type { StrategyFilter } from "@/lib/strategy";
import { PositionsCard } from "./PositionsCard";

const positions = {
  as_of: new Date().toISOString(),
  source: "monitor",
  degraded: false,
  groups: [
    {
      as_of: "",
      underlying: "AMD",
      stock: null,
      options: [
        { as_of: "", symbol: "x", right: "P", strike: 150, expiry: "2099-10-24", dte: 11, contracts: 1, short: true, delta: null, delta_source: null, market_price: null, market_value: null, unrealized_pnl: -212, moneyness: "itm", assignment_risk: true },
      ],
    },
    {
      as_of: "",
      underlying: "KO",
      stock: null,
      options: [
        { as_of: "", symbol: "y", right: "C", strike: 72, expiry: "2099-11-14", dte: 32, contracts: 1, short: true, delta: null, delta_source: null, market_price: null, market_value: null, unrealized_pnl: 30, moneyness: "otm", assignment_risk: false },
      ],
    },
  ],
};

const spreadsOff = { as_of: "", available: false, underlying: "SPY", mode: "paper", positions: [] };
const spreadsOn = { as_of: "", available: true, underlying: "SPY", mode: "paper", positions: [] };

/** renderWithQuery's own `rerender` would drop the QueryClientProvider, so the page's
 *  strategy switcher is stood in for by a harness that holds the prop in state. */
function Harness() {
  const [s, setS] = useState<StrategyFilter>("cc");
  return (
    <>
      <button onClick={() => setS("csp")}>to csp</button>
      <PositionsCard strategy={s} />
    </>
  );
}

describe("PositionsCard", () => {
  it("lists rows and counts per strategy chip", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, { "/portfolio/positions": positions, "/spreads/positions": spreadsOn });
    expect(await screen.findByText("AMD $150 put")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All 2" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "CSPs 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CCs 1" })).toBeInTheDocument();
  });
  it("follows the page's strategy switcher, and its own chips narrow further", async () => {
    renderWithQuery(<Harness />, { "/portfolio/positions": positions, "/spreads/positions": spreadsOn });
    expect(await screen.findByText("KO $72 call")).toBeInTheDocument();
    expect(screen.queryByText("AMD $150 put")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "All 2" }));
    expect(screen.getByText("AMD $150 put")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "to csp" }));
    expect(screen.queryByText("KO $72 call")).toBeNull();
    expect(screen.getByText("AMD $150 put")).toBeInTheDocument();
  });
  it("renders option rows when spreads are unavailable", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, { "/portfolio/positions": positions });
    expect(await screen.findByText("AMD $150 put")).toBeInTheDocument();
  });
  it("says nothing is open for an empty filter, in words", async () => {
    renderWithQuery(<PositionsCard strategy="spread" />, { "/portfolio/positions": positions, "/spreads/positions": spreadsOn });
    expect(await screen.findByText("No credit spreads open.")).toBeInTheDocument();
  });
  it("names the filter in its empty copy", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, { "/portfolio/positions": positions, "/spreads/positions": spreadsOn });
    await screen.findByText("AMD $150 put");
    fireEvent.click(screen.getByRole("button", { name: /^Shares/ }));
    expect(screen.getByText("No shares held.")).toBeInTheDocument();
    expect(screen.queryByText("AMD $150 put")).toBeNull();
  });
  it("tells no snapshot apart from no positions", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, {
      "/portfolio/positions": { ...positions, source: "none", groups: [] },
      "/spreads/positions": spreadsOn,
    });
    expect(await screen.findByText("No positions captured yet.")).toBeInTheDocument();
  });
  it("does not say no spreads are open when the spreads book cannot be read", async () => {
    renderWithQuery(<PositionsCard strategy="spread" />, { "/portfolio/positions": positions, "/spreads/positions": spreadsOff });
    expect(await screen.findByText("Credit spreads are unavailable right now.")).toBeInTheDocument();
    expect(screen.queryByText("No credit spreads open.")).toBeNull();
  });
  it("lists the options and notes what is missing under All when spreads cannot be read", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, { "/portfolio/positions": positions, "/spreads/positions": spreadsOff });
    expect(await screen.findByText("AMD $150 put")).toBeInTheDocument();
    expect(await screen.findByText("Credit spreads are unavailable right now, so they are not listed.")).toBeInTheDocument();
  });
  it("shows no count on the spreads chip until the spreads book has answered", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, { "/portfolio/positions": positions, "/spreads/positions": spreadsOff });
    await screen.findByText("AMD $150 put");
    expect(screen.getByRole("button", { name: "Credit spreads" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Credit spreads 0" })).toBeNull();
  });
  it("signs the open P&L in words and symbols", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, { "/portfolio/positions": positions, "/spreads/positions": spreadsOn });
    expect(await screen.findByText("−$212.00")).toBeInTheDocument();
    expect(screen.getByText("+$30.00")).toBeInTheDocument();
    expect(screen.getAllByText("open P&L")).toHaveLength(2);
  });
  it("flags a delayed snapshot in words rather than passing it off as live", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, {
      "/portfolio/positions": { ...positions, source: "eod", degraded: true, as_of: "2020-01-01T00:00:00Z" },
      "/spreads/positions": spreadsOn,
    });
    expect(await screen.findByText("Delayed")).toBeInTheDocument();
    expect(screen.getByText(/stale/)).toBeInTheDocument();
  });
  it("says so in a sentence when positions cannot load", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, {});
    expect(await screen.findByText("Positions unavailable right now.")).toBeInTheDocument();
  });
});
