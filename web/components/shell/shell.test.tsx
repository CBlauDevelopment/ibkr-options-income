import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ControlsResponse } from "@/components/options/types";
import { renderWithQuery } from "@/lib/test-query";

const path = vi.hoisted(() => ({ current: "/" }));
vi.mock("next/navigation", () => ({ usePathname: () => path.current }));

import { BotCard } from "./BotCard";
import { BotSheet } from "./BotSheet";
import { HaltedBanner } from "./HaltedBanner";
import { TabBar } from "./TabBar";

function controls(over: Record<string, unknown> = {}) {
  return {
    as_of: new Date().toISOString(),
    autonomy: { level: "approve", label: "Approve each trade" },
    rungs: [{ level: "approve", label: "Approve each trade" }],
    halted: false,
    halt_reason: null,
    halted_at: null,
    mode: "paper",
    drain_healthy: true,
    drain_last_seen: null,
    pending_commands: 0,
    ...over,
  };
}

describe("TabBar", () => {
  it("has the five phone destinations with Home current", () => {
    renderWithQuery(<TabBar />, {});
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(5);
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
  });
  it.each(["/research", "/research/universe", "/stock/AAPL", "/news", "/news/AAPL"])(
    "marks More current on %s, which lives under More on a phone",
    (p) => {
      path.current = p;
      try {
        renderWithQuery(<TabBar />, {});
        expect(screen.getByRole("link", { name: "More" })).toHaveAttribute("aria-current", "page");
      } finally {
        path.current = "/";
      }
    },
  );
});

describe("BotCard", () => {
  it("states running, mode and rung in words", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls() });
    expect(await screen.findByText("Bot running · paper")).toBeInTheDocument();
    expect(screen.getByText("Approve each trade")).toBeInTheDocument();
  });
  it("states halted in words", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls({ halted: true }) });
    // The web halt is the wheel's switch; credit spreads have their own (I1).
    expect(await screen.findByText("Wheel halted · paper")).toBeInTheDocument();
  });
  it("says so when the trading service is not draining commands", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls({ drain_healthy: false }) });
    expect(await screen.findByText("The trading service is not draining commands")).toBeInTheDocument();
  });
  it("opens the bot sheet with the halt control", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls() });
    fireEvent.click(await screen.findByRole("button", { name: /Bot running/ }));
    expect(screen.getByRole("dialog", { name: "Bot controls" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Halt/ })).toBeInTheDocument();
  });
  it("tells assistive tech that it opens a dialog", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls() });
    expect(await screen.findByRole("button", { name: /Bot running/ })).toHaveAttribute("aria-haspopup", "dialog");
  });
  it("holds its place with a labelled loading state until the controls answer", () => {
    renderWithQuery(<BotCard />, { "/options/controls": new Promise(() => {}) });
    expect(screen.getByRole("status", { name: "Loading bot status" })).toBeInTheDocument();
  });
  it("says the status is unavailable when the controls fetch fails", async () => {
    renderWithQuery(<BotCard />, {});
    expect(await screen.findByText("Bot status unavailable")).toBeInTheDocument();
  });
});

describe("HaltedBanner", () => {
  it("renders nothing while trading runs", async () => {
    const { container } = renderWithQuery(<HaltedBanner />, { "/options/controls": controls() });
    await screen.findByTestId("halted-banner-probe");
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });
  it("states the halt, its reason and its time as text", async () => {
    renderWithQuery(<HaltedBanner />, {
      "/options/controls": controls({
        halted: true,
        halt_reason: "daily loss limit",
        halted_at: "2026-10-13T14:05:00Z",
      }),
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Wheel trading is halted");
    expect(alert).toHaveTextContent("daily loss limit");
    expect(alert).toHaveTextContent("Oct 13, 2026");
  });
  it("omits the time for a breaker halt with no command row", async () => {
    renderWithQuery(<HaltedBanner />, {
      "/options/controls": controls({ halted: true, halt_reason: "breaker", halted_at: null }),
    });
    const alert = await screen.findByRole("alert");
    expect(alert).not.toHaveTextContent(/since/);
  });
  // Moved from ControlsStrip.test.tsx with the banner (Task 6), then scoped (Section B
  // review I1): this halt is the wheel's switch only. The spreads service honours its own
  // halt file, so a global "no new orders" would overstate it.
  it("says what the wheel halt stops, and that credit spreads have their own halt", async () => {
    renderWithQuery(<HaltedBanner />, {
      "/options/controls": controls({
        halted: true,
        halt_reason: "spread blew out",
        halted_at: "2026-09-07T09:41:00Z",
      }),
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No new CSP or covered-call orders will be queued or sent");
    expect(alert).toHaveTextContent("Credit spreads have their own halt");
    expect(alert).not.toHaveTextContent(/No new orders will be queued/);
    expect(alert).not.toHaveTextContent(/profit-take/i);
  });
});

function renderSheet(initial: ControlsResponse) {
  const onClose = vi.fn();
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const ui = (c: ControlsResponse) => (
    <QueryClientProvider client={qc}>
      <BotSheet open onClose={onClose} controls={c} />
    </QueryClientProvider>
  );
  const result = render(ui(initial));
  return { onClose, rerenderWith: (c: ControlsResponse) => result.rerender(ui(c)) };
}

describe("BotSheet", () => {
  it("warns beside the controls when the trading service is not draining commands", () => {
    renderSheet(controls({ drain_healthy: false, drain_last_seen: null }) as ControlsResponse);
    const sheet = screen.getByRole("dialog", { name: "Bot controls" });
    const warning = screen.getByTestId("drain-dead-warning");
    expect(sheet).toContainElement(warning);
    expect(warning).toHaveTextContent("the trading service is not draining commands");
    expect(warning).toHaveTextContent("it will not be applied until the drain is back");
  });
  it("shows no drain warning while commands drain", () => {
    renderSheet(controls() as ControlsResponse);
    expect(screen.queryByTestId("drain-dead-warning")).toBeNull();
  });
  it("shows the drain warning if the drain dies while the sheet is open", () => {
    const { rerenderWith } = renderSheet(controls() as ControlsResponse);
    expect(screen.queryByTestId("drain-dead-warning")).toBeNull();
    rerenderWith(controls({ drain_healthy: false }) as ControlsResponse);
    expect(screen.getByTestId("drain-dead-warning")).toBeInTheDocument();
  });
  it("keeps the sheet open and the keys in the RESUME dialog when focus lands on the sheet panel", () => {
    // A click on the confirm dialog's prose or padding focuses the nearest focusable
    // ancestor: the sheet panel (Section B review I3).
    const { onClose } = renderSheet(controls({ halted: true, halt_reason: "manual" }) as ControlsResponse);
    const panel = screen.getByRole("dialog", { name: "Bot controls" });

    fireEvent.click(screen.getByTestId("resume-button"));
    expect(screen.getByRole("dialog", { name: "Resume execution" })).toBeInTheDocument();
    panel.focus();
    fireEvent.keyDown(panel, { key: "Escape" });
    // Escape cancels the RESUME dialog only; the bot sheet stays open.
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog", { name: "Resume execution" })).toBeNull();
    expect(screen.getByRole("dialog", { name: "Bot controls" })).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("resume-button"));
    const confirm = screen.getByRole("dialog", { name: "Resume execution" });
    panel.focus();
    fireEvent.keyDown(panel, { key: "Tab" });
    expect(confirm).toContainElement(document.activeElement as HTMLElement);
    panel.focus();
    fireEvent.keyDown(panel, { key: "Tab", shiftKey: true });
    expect(confirm).toContainElement(document.activeElement as HTMLElement);
    expect(onClose).not.toHaveBeenCalled();
  });
});
