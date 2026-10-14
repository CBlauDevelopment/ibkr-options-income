import { act, fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithQuery, apiFetchMock } from "@/lib/test-query";

const chart = vi.hoisted(() => ({ handlers: [] as Array<(p: { time?: number }) => void> }));

vi.mock("lightweight-charts", () => ({
  ColorType: { Solid: "solid" },
  CrosshairMode: { Magnet: 1 },
  LineType: { Simple: 0 },
  createChart: () => ({
    addLineSeries: () => ({ setData: vi.fn(), applyOptions: vi.fn() }),
    subscribeCrosshairMove: (h: (p: { time?: number }) => void) => chart.handlers.push(h),
    unsubscribeCrosshairMove: vi.fn(),
    timeScale: () => ({ fitContent: vi.fn() }),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  }),
}));

import { AccountHero } from "./AccountHero";
import type { AccountValueResponse, RangeKey } from "./types";

const body = (range: RangeKey): AccountValueResponse => ({
  as_of: new Date().toISOString(),
  series: {
    range,
    points: [
      { at: "2026-10-12T20:00:00Z", value: 101_000 },
      { at: "2026-10-13T18:00:00Z", value: 101_500 },
    ],
    latest: 101_500,
    latest_at: "2026-10-13T18:00:00Z",
    previous_close: 101_000,
    change_today: 500,
    change_today_pct: 0.496,
  },
});

describe("AccountHero", () => {
  it("shows the account value and today's signed change in words", async () => {
    renderWithQuery(<AccountHero />, { "/portfolio/value": body("1m") });
    expect(await screen.findByText("$101,500.00")).toBeInTheDocument();
    expect(screen.getByText("+$500.00 (0.50%) today")).toBeInTheDocument();
  });
  it("rewrites the number while scrubbing and restores it after", async () => {
    renderWithQuery(<AccountHero />, { "/portfolio/value": body("1m") });
    await screen.findByText("$101,500.00");
    const t = Math.floor(Date.parse("2026-10-12T20:00:00Z") / 1000);
    act(() => chart.handlers.at(-1)!({ time: t }));
    expect(screen.getByText("$101,000.00")).toBeInTheDocument();
    act(() => chart.handlers.at(-1)!({}));
    expect(screen.getByText("$101,500.00")).toBeInTheDocument();
  });
  it("refetches for a new range", async () => {
    renderWithQuery(<AccountHero />, { "/portfolio/value": body("1m") });
    await screen.findByText("$101,500.00");
    fireEvent.click(screen.getByRole("button", { name: "3M" }));
    expect(apiFetchMock.mock.calls.some((c) => c[0] === "/portfolio/value?range=3m")).toBe(true);
  });
  it("can be scrubbed from the keyboard and restores on Escape", async () => {
    renderWithQuery(<AccountHero />, { "/portfolio/value": body("1m") });
    await screen.findByText("$101,500.00");
    const slider = screen.getByRole("slider", { name: /Account value history/ });
    expect(slider).toHaveAttribute("tabindex", "0");
    fireEvent.keyDown(slider, { key: "ArrowLeft" });
    expect(screen.getByText("$101,000.00")).toBeInTheDocument();
    expect(slider).toHaveAttribute("aria-valuenow", "0");
    expect(slider.getAttribute("aria-valuetext")).toContain("$101,000.00");
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    expect(screen.getByText("$101,500.00")).toBeInTheDocument();
    fireEvent.keyDown(slider, { key: "Home" });
    expect(screen.getByText("$101,000.00")).toBeInTheDocument();
    fireEvent.keyDown(slider, { key: "Escape" });
    expect(screen.getByText("$101,500.00")).toBeInTheDocument();
  });
  it("leaves the keyboard scrub when the chart loses focus", async () => {
    renderWithQuery(<AccountHero />, { "/portfolio/value": body("1m") });
    await screen.findByText("$101,500.00");
    const slider = screen.getByRole("slider", { name: /Account value history/ });
    fireEvent.keyDown(slider, { key: "Home" });
    expect(screen.getByText("$101,000.00")).toBeInTheDocument();
    fireEvent.blur(slider);
    expect(screen.getByText("$101,500.00")).toBeInTheDocument();
  });
  it("shows neutral, not green, when the day's change is exactly zero", async () => {
    const flat = body("1m");
    flat.series = { ...flat.series, change_today: 0, change_today_pct: 0 };
    renderWithQuery(<AccountHero />, { "/portfolio/value": flat });
    const line = await screen.findByText("$0 (0.00%) today");
    expect(line.className).not.toMatch(/text-gain|text-loss/);
  });
  it("keeps the value and says when it is from when today's change is unknown", async () => {
    const weekend = body("1m");
    weekend.series = { ...weekend.series, change_today: null, change_today_pct: null };
    renderWithQuery(<AccountHero />, { "/portfolio/value": weekend });
    expect(await screen.findByText("$101,500.00")).toBeInTheDocument();
    expect(screen.getByText(/n\/a today/)).toBeInTheDocument();
    expect(screen.getByText(/last value Oct 13, 2026/)).toBeInTheDocument();
  });
  it("says there is no history yet instead of drawing an empty frame", async () => {
    const empty = body("1m");
    empty.series = { ...empty.series, points: [], latest: null, change_today: null, change_today_pct: null };
    renderWithQuery(<AccountHero />, { "/portfolio/value": empty });
    expect(await screen.findByText("No account history yet.")).toBeInTheDocument();
    expect(screen.getByText("n/a")).toBeInTheDocument();
  });
});
