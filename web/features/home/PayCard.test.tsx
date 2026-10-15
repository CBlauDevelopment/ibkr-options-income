import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiFetchMock, renderWithQuery } from "@/lib/test-query";
import { PayCard } from "./PayCard";

function pay(over: Record<string, unknown> = {}, spreadsAvailable = true) {
  return {
    as_of: new Date().toISOString(),
    book: "paper",
    spreads_available: spreadsAvailable,
    pay: {
      month: "2026-10-01",
      strategy: "all",
      premium_collected: 1642,
      bought_back: 210,
      commissions: 18.4,
      commissions_complete: true,
      net: 1413.6,
      n_opened: 9,
      n_closed: 3,
      month_start_value: 200000,
      target_pct: 1,
      target_mode: "pct_of_account",
      target_amount: null,
      target_base: null,
      target: 2000,
      progress_pct: 70.68,
      days_left: 18,
      ...over,
    },
  };
}

describe("PayCard", () => {
  it("is collapsed by default and shows net, target and pace on one line", async () => {
    renderWithQuery(<PayCard strategy="all" />, { "/pnl/month": pay() });
    const toggle = await screen.findByRole("button", { name: /October pay/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    // Scoped to the toggle: the closed stub's total ("Net so far") is in the DOM, hidden.
    expect(within(toggle).getByText("+$1,413.60")).toBeInTheDocument();
    expect(screen.getByText("of $2,000.00")).toBeInTheDocument();
    expect(screen.getByText("71% of target · 18 days left")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "October target" })).toHaveAttribute("aria-valuenow", "71");
  });
  it("opens to the month's stub", async () => {
    renderWithQuery(<PayCard strategy="all" />, { "/pnl/month": pay() });
    fireEvent.click(await screen.findByRole("button", { name: /October pay/ }));
    expect(screen.getByRole("group", { name: "October pay stub" })).toBeInTheDocument();
    expect(screen.getByText("+$1,642.00")).toBeInTheDocument();
    expect(screen.getByText("−$210.00")).toBeInTheDocument();
    expect(screen.getByText("−$18.40")).toBeInTheDocument();
  });
  it("says No target set rather than a zero target", async () => {
    renderWithQuery(<PayCard strategy="all" />, {
      "/pnl/month": pay({ target: null, target_pct: null, target_mode: "off", progress_pct: null }),
    });
    expect(await screen.findByText("No target set · 18 days left")).toBeInTheDocument();
    expect(screen.queryByText(/of \$0/)).toBeNull();
  });
  it("links to More from 'No target set', and from nowhere else", async () => {
    const { unmount } = renderWithQuery(<PayCard strategy="all" />, {
      "/pnl/month": pay({ target: null, target_pct: null, target_mode: "off", progress_pct: null }),
    });
    expect(await screen.findByRole("link", { name: "Set a target in More" })).toHaveAttribute("href", "/more");
    unmount();
    renderWithQuery(<PayCard strategy="all" />, { "/pnl/month": pay() });
    await screen.findByRole("button", { name: /October pay/ });
    expect(screen.queryByRole("link", { name: /Set a target/ })).toBeNull();
  });
  it("shows a fixed amount as a target even though it has no percent", async () => {
    renderWithQuery(<PayCard strategy="all" />, {
      "/pnl/month": pay({
        month_start_value: null,
        target_pct: null,
        target_mode: "fixed",
        target_amount: 1500,
        target: 1500,
        progress_pct: 94.24,
      }),
    });
    expect(await screen.findByText("of $1,500.00")).toBeInTheDocument();
    expect(screen.getByText("94% of target · 18 days left")).toBeInTheDocument();
    expect(screen.queryByText(/No target set/)).toBeNull();
  });
  // Final review m4: the setting can be set while the month-start account value is unknown
  // (the first month after install, a journal gap). "No target set" would read as a config that
  // did not load; the target is unknown, and the card says why.
  it("says the target needs the month's opening value when the setting is set but that value is unknown", async () => {
    renderWithQuery(<PayCard strategy="all" />, {
      "/pnl/month": pay({ month_start_value: null, target: null, progress_pct: null }),
    });
    const line = await screen.findByText(/needs the month's opening account value/);
    expect(line).toHaveTextContent("Target n/a · needs the month's opening account value · 18 days left");
    expect(within(line).getByText("n/a")).toHaveClass("hatch");
    expect(screen.queryByText(/No target set/)).toBeNull();
    expect(screen.queryByText(/of \$0/)).toBeNull();
    expect(screen.queryByText(/0% of target/)).toBeNull();
    expect(screen.getByRole("progressbar", { name: "October target" })).not.toHaveAttribute("aria-valuenow");
  });
  it("says 1 day left, not 1 days left", async () => {
    renderWithQuery(<PayCard strategy="all" />, { "/pnl/month": pay({ days_left: 1 }) });
    expect(await screen.findByText("71% of target · 1 day left")).toBeInTheDocument();
  });
  it("says 1 day left when no target is set", async () => {
    renderWithQuery(<PayCard strategy="all" />, {
      "/pnl/month": pay({ target: null, target_pct: null, target_mode: "off", progress_pct: null, days_left: 1 }),
    });
    expect(await screen.findByText("No target set · 1 day left")).toBeInTheDocument();
  });
  it("never turns an unknown progress into 0% of a known target", async () => {
    renderWithQuery(<PayCard strategy="all" />, { "/pnl/month": pay({ progress_pct: null }) });
    const line = await screen.findByText(/of target · 18 days left/);
    expect(line).toHaveTextContent("n/a of target · 18 days left");
    expect(within(line).getByText("n/a")).toHaveClass("hatch");
    expect(screen.queryByText(/^0% of target/)).toBeNull();
  });
  it("marks commissions gross when some are missing", async () => {
    renderWithQuery(<PayCard strategy="all" />, { "/pnl/month": pay({ commissions_complete: false }) });
    fireEvent.click(await screen.findByRole("button", { name: /October pay/ }));
    expect(screen.getByText("Commissions (incomplete)")).toBeInTheDocument();
  });
  it("asks for the selected strategy", async () => {
    renderWithQuery(<PayCard strategy="csp" />, { "/pnl/month": pay({ strategy: "csp" }) });
    await screen.findByRole("button", { name: /October pay/ });
    expect(apiFetchMock.mock.calls.some((c) => c[0] === "/pnl/month?strategy=csp")).toBe(true);
  });
  it("says so in a sentence when the fetch fails", async () => {
    renderWithQuery(<PayCard strategy="all" />, {});
    expect(await screen.findByText("Could not load this month's pay.")).toBeInTheDocument();
    expect(screen.getByText("It tries again every minute.")).toBeInTheDocument();
  });

  describe("when the spreads book cannot be read", () => {
    it("flags it on the closed card instead of presenting the wheel total as the whole month", async () => {
      renderWithQuery(<PayCard strategy="all" />, { "/pnl/month": pay({}, false) });
      expect(await screen.findByText(/Spread income is unavailable/)).toBeInTheDocument();
      // The wheel's own figures still show; the sentence is outside the closed disclosure.
      const toggle = screen.getByRole("button", { name: /October pay/ });
      expect(within(toggle).getByText("+$1,413.60")).toBeInTheDocument();
      expect(toggle).toHaveAttribute("aria-expanded", "false");
    });
    it("shows the spread-only month as n/a, never $0", async () => {
      renderWithQuery(<PayCard strategy="spread" />, {
        "/pnl/month": pay(
          { strategy: "spread", premium_collected: 0, bought_back: 0, commissions: 0, net: 0, n_opened: 0, n_closed: 0 },
          false,
        ),
      });
      expect(await screen.findByText(/Spread income is unavailable/)).toBeInTheDocument();
      const toggle = screen.getByRole("button", { name: /October pay/ });
      // The net and the progress are unknown (two n/a), the target is not.
      expect(within(toggle).getAllByText("n/a")).toHaveLength(2);
      expect(within(toggle).getByRole("progressbar")).not.toHaveAttribute("aria-valuenow");
      expect(screen.queryByText("$0")).toBeNull();
      fireEvent.click(toggle);
      const stub = screen.getByRole("group", { name: "October pay stub" });
      expect(within(stub).getAllByText("n/a")).toHaveLength(4);
      expect(screen.queryByText("$0")).toBeNull();
    });
    // Final review m4 (Section D M2): the spread-only month's income is unknown, but the
    // target is set and known, so the card must not say "No target set".
    it("keeps a known target for an unreadable spread-only month and says the progress is unknown", async () => {
      renderWithQuery(<PayCard strategy="spread" />, {
        "/pnl/month": pay(
          { strategy: "spread", premium_collected: 0, bought_back: 0, commissions: 0, net: 0, n_opened: 0, n_closed: 0 },
          false,
        ),
      });
      const line = await screen.findByText(/of target · 18 days left/);
      expect(line).toHaveTextContent("n/a of target · 18 days left");
      expect(within(line).getByText("n/a")).toHaveClass("hatch");
      expect(screen.getByText("of $2,000.00")).toBeInTheDocument();
      expect(screen.queryByText(/No target set/)).toBeNull();
      expect(screen.queryByText(/^0% of target/)).toBeNull();
    });
    it("stays quiet for a wheel strategy, which never needs the spreads book", async () => {
      renderWithQuery(<PayCard strategy="csp" />, { "/pnl/month": pay({ strategy: "csp" }, false) });
      await screen.findByRole("button", { name: /October pay/ });
      expect(screen.queryByText(/Spread income is unavailable/)).toBeNull();
    });
  });
});
