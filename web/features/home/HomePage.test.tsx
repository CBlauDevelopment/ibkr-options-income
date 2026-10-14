import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithQuery } from "@/lib/test-query";

const nav = vi.hoisted(() => ({ replace: vi.fn(), params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => nav.params,
  usePathname: () => "/",
}));
vi.mock("./HeroChart", () => ({ HeroChart: () => <div data-testid="chart" /> }));

import { HomePage } from "./HomePage";

const responses = {
  "/portfolio/value": {
    as_of: "",
    series: { range: "1m", points: [], latest: 248310.42, latest_at: null, previous_close: null, change_today: null, change_today_pct: null },
  },
  "/pnl/month": {
    as_of: "",
    book: "paper",
    spreads_available: true,
    pay: { month: "2026-10-01", strategy: "all", premium_collected: 0, bought_back: 0, commissions: 0, commissions_complete: true, net: 0, n_opened: 0, n_closed: 0, month_start_value: null, target_pct: null, target: null, progress_pct: null, days_left: 18 },
  },
  "/portfolio/positions": { as_of: "", source: "none", degraded: true, groups: [] },
  "/spreads/positions": { as_of: "", available: false, underlying: "SPY", mode: "paper", positions: [] },
  "/options/approvals": { as_of: "", approvals: [] },
  "/options/controls": { as_of: "", autonomy: { level: "a", label: "A" }, rungs: [], halted: false, halt_reason: null, halted_at: null, mode: "paper", drain_healthy: true, drain_last_seen: null, pending_commands: 0 },
};

describe("HomePage", () => {
  it("puts the strategy switcher first, then the hero, pay and positions", async () => {
    renderWithQuery(<HomePage />, responses);
    const switcher = await screen.findByRole("group", { name: "Strategy" });
    const hero = await screen.findByRole("region", { name: "Account value" });
    const pay = await screen.findByRole("button", { name: /October pay/ });
    const positions = await screen.findByRole("heading", { name: "Positions" });
    const order = [switcher, hero, pay, positions];
    for (let i = 1; i < order.length; i++) {
      expect(order[i - 1].compareDocumentPosition(order[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });
  it("names the page with one level-1 heading, so the card headings sit under it", async () => {
    renderWithQuery(<HomePage />, responses);
    expect(await screen.findByRole("heading", { level: 1, name: "Home" })).toBeInTheDocument();
  });
  it("writes the strategy into the URL", async () => {
    renderWithQuery(<HomePage />, responses);
    // Scoped to the page's switcher: the positions card carries a "CSPs" chip of its own.
    const switcher = await screen.findByRole("group", { name: "Strategy" });
    fireEvent.click(within(switcher).getByRole("button", { name: "CSPs" }));
    expect(nav.replace).toHaveBeenCalledWith("/?strategy=csp", { scroll: false });
  });
});
