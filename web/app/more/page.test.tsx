import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithQuery } from "@/lib/test-query";
import { THEME_STORAGE_KEY } from "@/lib/theme";
import MorePage from "./page";

const status = { as_of: new Date().toISOString(), rows: [] };

const controls = {
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
};

describe("More page", () => {
  it("offers light, dark and follow-OS themes and persists the choice", () => {
    renderWithQuery(<MorePage />, { "/system/status": status, "/options/controls": controls });
    const group = screen.getByRole("group", { name: "Theme" });
    expect(group).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Follow OS" }));
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("system");
  });
  it("links to the pages that have no tab on a phone", () => {
    renderWithQuery(<MorePage />, { "/system/status": status, "/options/controls": controls });
    expect(screen.getByRole("link", { name: /How it works/ })).toHaveAttribute("href", "/explain");
    expect(screen.getByRole("link", { name: /Research/ })).toHaveAttribute("href", "/research");
    expect(screen.getByRole("link", { name: /News/ })).toHaveAttribute("href", "/news");
    expect(screen.getByRole("link", { name: /Import a statement/ })).toHaveAttribute("href", "/ledger/import");
  });
  it("links to Universe and Ledger, which have no tab or rail entry", () => {
    renderWithQuery(<MorePage />, { "/system/status": status, "/options/controls": controls });
    expect(screen.getByRole("link", { name: /^Universe/ })).toHaveAttribute("href", "/research/universe");
    expect(screen.getByRole("link", { name: /^Ledger/ })).toHaveAttribute("href", "/ledger");
  });
  it("reaches the bot controls on a phone, where the rail is hidden", async () => {
    renderWithQuery(<MorePage />, { "/system/status": status, "/options/controls": controls });
    expect(await screen.findByRole("button", { name: /Bot running/ })).toBeInTheDocument();
  });
});
