import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithQuery } from "@/lib/test-query";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

import { BotCard } from "./BotCard";
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
});

describe("BotCard", () => {
  it("states running, mode and rung in words", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls() });
    expect(await screen.findByText("Bot running · paper")).toBeInTheDocument();
    expect(screen.getByText("Approve each trade")).toBeInTheDocument();
  });
  it("states halted in words", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls({ halted: true }) });
    expect(await screen.findByText("Halted · paper")).toBeInTheDocument();
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
    expect(alert).toHaveTextContent("Trading is halted");
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
  // Moved from ControlsStrip.test.tsx with the banner (Task 6): the banner says what a
  // halt stops, not only that one is in force.
  it("says what a halt stops", async () => {
    renderWithQuery(<HaltedBanner />, {
      "/options/controls": controls({
        halted: true,
        halt_reason: "spread blew out",
        halted_at: "2026-09-07T09:41:00Z",
      }),
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No new orders will be queued or transmitted");
  });
});
