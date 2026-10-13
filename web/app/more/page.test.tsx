import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithQuery } from "@/lib/test-query";
import { THEME_STORAGE_KEY } from "@/lib/theme";
import MorePage from "./page";

const status = { as_of: new Date().toISOString(), rows: [] };

describe("More page", () => {
  it("offers light, dark and follow-OS themes and persists the choice", () => {
    renderWithQuery(<MorePage />, { "/system/status": status });
    const group = screen.getByRole("group", { name: "Theme" });
    expect(group).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Follow OS" }));
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("system");
  });
  it("links to the pages that have no tab on a phone", () => {
    renderWithQuery(<MorePage />, { "/system/status": status });
    expect(screen.getByRole("link", { name: /How it works/ })).toHaveAttribute("href", "/explain");
    expect(screen.getByRole("link", { name: /Research/ })).toHaveAttribute("href", "/research");
    expect(screen.getByRole("link", { name: /News/ })).toHaveAttribute("href", "/news");
    expect(screen.getByRole("link", { name: /Import a statement/ })).toHaveAttribute("href", "/ledger/import");
  });
});
