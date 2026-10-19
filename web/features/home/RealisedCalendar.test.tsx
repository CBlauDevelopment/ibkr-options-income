import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { apiFetchMock, renderWithQuery } from "@/lib/test-query";
import { RealisedCalendarButton } from "./RealisedCalendar";

afterEach(cleanup);

const NOW = new Date("2026-10-15T16:00:00Z");

const cal = (month: string, days: Array<[string, number, number]>, over: object = {}) => ({
  as_of: "",
  book: "paper",
  spreads_available: true,
  calendar: {
    month: `${month}-01`,
    strategy: "all",
    days: days.map(([date, realized, n]) => ({ date, realized, n_closed: n, complete: true })),
    total: days.reduce((a, d) => a + d[1], 0),
    n_closed: days.reduce((a, d) => a + d[2], 0),
    complete: true,
    ...over,
  },
});

const octDays: Array<[string, number, number]> = [
  ["2026-10-09", 1717.88, 3],
  ["2026-10-13", -1603.7, 1],
  ["2026-10-14", 12400, 2],
];

const dayDetail = {
  as_of: "",
  date: "2026-10-09",
  book: "paper",
  strategy: "all",
  spreads_available: true,
  trades: [
    {
      key: "a:closed", action: "closed", how: "bought_back", kind: "csp", source: "wheel", underlying: "AMZN", right: "P",
      strike: 252.5, long_strike: null, expiry: "2026-10-23", contracts: 1, at: "2026-10-09T15:00:00Z", is_live: false,
      premium: 400, bought_back: 40, commissions: 1, commissions_complete: true, net_pnl: 359, capital: 25250, roc_pct: 1.6,
      annualized_pct: null, pct_kept: 90, dte_at_open: 14, days_held: 5, reason: "Closed for a profit: the position reached its profit target.",
      facts: [], approval_id: 1, review: null, rolled_to: null,
    },
    {
      key: "b:opened", action: "opened", how: null, kind: "csp", source: "wheel", underlying: "AAPL", right: "P",
      strike: 330, long_strike: null, expiry: "2026-11-20", contracts: 1, at: "2026-10-09T14:00:00Z", is_live: false,
      premium: 300, bought_back: null, commissions: 1, commissions_complete: true, net_pnl: null, capital: 33000, roc_pct: 0.9,
      annualized_pct: 8, pct_kept: null, dte_at_open: 42, days_held: null, reason: null, facts: [], approval_id: 2, review: null, rolled_to: null,
    },
  ],
};

const serve = (extra: Record<string, unknown> = {}) => ({
  "/pnl/calendar?month=2026-10": cal("2026-10", octDays),
  "/pnl/calendar?month=2026-09": cal("2026-09", []),
  "/pnl/day?date=2026-10-09": dayDetail,
  ...extra,
});

async function openIt(responses: Record<string, unknown> = serve()) {
  renderWithQuery(<RealisedCalendarButton now={NOW} />, responses);
  fireEvent.click(screen.getByRole("button", { name: "Daily realised P&L calendar" }));
  return screen.findByRole("dialog", { name: "Realised P&L" });
}

describe("RealisedCalendar", () => {
  it("opens a dialog on the current New York month with the month's total", async () => {
    const dialog = await openIt();
    expect(await within(dialog).findByRole("heading", { name: "October 2026" })).toBeInTheDocument();
    expect(within(dialog).getByText("Realised in October")).toBeInTheDocument();
    expect(within(dialog).getByText("+$12,514.18")).toBeInTheDocument(); // 1717.88 - 1603.70 + 12400 = 12514.18
    expect(within(dialog).getByText("from 6 closes")).toBeInTheDocument();
  });

  it("shows each day with a close as a signed figure and leaves the rest blank", async () => {
    const dialog = await openIt();
    const nine = await within(dialog).findByRole("button", { name: /Fri, Oct 9: \+\$1,717\.88 realised from 3 closes/ });
    expect(nine).toHaveTextContent("+1.7K");
    expect(within(dialog).getByRole("button", { name: /Tue, Oct 13: −\$1,603\.70 realised from 1 close$/ })).toHaveTextContent("−1.6K");
    expect(within(dialog).getByRole("button", { name: /Wed, Oct 14: \+\$12,400\.00/ })).toBeInTheDocument();
    // a day nothing closed is plain text, not a button, and never "$0"
    expect(within(dialog).getAllByRole("button", { name: /realised from/ })).toHaveLength(3);
    expect(within(dialog).queryByText("$0")).toBeNull();
  });

  it("is a labelled table, Monday first", async () => {
    const dialog = await openIt();
    await within(dialog).findByRole("table", { name: "Realised P&L by day, October 2026" });
    const heads = within(dialog).getAllByRole("columnheader").map((h) => h.textContent);
    expect(heads).toEqual(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]);
  });

  it("a tapped day lists what closed that day, with the reason and the result, not what opened", async () => {
    const dialog = await openIt();
    fireEvent.click(await within(dialog).findByRole("button", { name: /Fri, Oct 9/ }));
    const section = await within(dialog).findByRole("region", { name: "What closed on Fri, Oct 9" });
    expect(await within(section).findByText("AMZN · Bought back $252.5 put")).toBeInTheDocument();
    expect(within(section).getByText("Closed for a profit: the position reached its profit target.")).toBeInTheDocument();
    expect(within(section).getByText("+$359.00")).toBeInTheDocument();
    expect(within(section).queryByText(/AAPL/)).toBeNull();
    expect(within(dialog).getByRole("button", { name: /Fri, Oct 9/ })).toHaveAttribute("aria-pressed", "true");
    // tapping it again closes the detail
    fireEvent.click(within(dialog).getByRole("button", { name: /Fri, Oct 9/ }));
    expect(within(dialog).queryByRole("region", { name: /What closed on/ })).toBeNull();
  });

  it("links a tapped day to that day in History", async () => {
    const dialog = await openIt();
    fireEvent.click(await within(dialog).findByRole("button", { name: /Fri, Oct 9/ }));
    const section = await within(dialog).findByRole("region", { name: "What closed on Fri, Oct 9" });
    expect(within(section).getByRole("link", { name: "Open this day in History" })).toHaveAttribute(
      "href",
      "/trades?view=history&day=2026-10-09",
    );
  });

  it("walks back a month and cannot walk past the current one", async () => {
    const dialog = await openIt();
    await within(dialog).findByRole("heading", { name: "October 2026" });
    expect(within(dialog).getByRole("button", { name: "Next month" })).toBeDisabled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Previous month" }));
    expect(await within(dialog).findByRole("heading", { name: "September 2026" })).toBeInTheDocument();
    expect(await within(dialog).findByText("Nothing closed in September.")).toBeInTheDocument();
    expect(apiFetchMock.mock.calls.some((c) => c[0] === "/pnl/calendar?month=2026-09")).toBe(true);
    expect(within(dialog).getByRole("button", { name: "Next month" })).toBeEnabled();
  });

  it("says when commissions are incomplete or spreads could not be read, in words", async () => {
    const dialog = await openIt(
      serve({
        "/pnl/calendar?month=2026-10": { ...cal("2026-10", octDays, { complete: false }), spreads_available: false },
      }),
    );
    expect(await within(dialog).findByText("Commissions incomplete")).toBeInTheDocument();
    expect(within(dialog).getByText("Spreads unavailable")).toBeInTheDocument();
  });

  it("states what is and is not counted, so a blank day is not read as flat", async () => {
    const dialog = await openIt();
    expect(await within(dialog).findByText(/Share sales are not included, and a day nothing closed is blank/)).toBeInTheDocument();
  });

  it("says in words when the month could not be loaded", async () => {
    const dialog = await openIt({});
    expect(await within(dialog).findByText(/could not be loaded/)).toBeInTheDocument();
  });

  it("closes on Escape and gives focus back to the button", async () => {
    const dialog = await openIt();
    await within(dialog).findByRole("heading", { name: "October 2026" });
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
