import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { apiFetchMock, renderWithQuery } from "@/lib/test-query";
import { RollCard } from "./RollCard";

const SYMBOL = "AAPL  261121P00180000";

const controls = {
  as_of: "", autonomy: { level: "approve", label: "Approve each trade" }, rungs: [], halted: false,
  halt_reason: null, halted_at: null, mode: "paper", drain_healthy: true, drain_last_seen: null,
  pending_commands: 0,
};

const shorts = (alerts: unknown[]) => ({
  as_of: "",
  shorts: [
    {
      as_of: "", position_symbol: SYMBOL, underlying: "AAPL", right: "P", strike: 180, expiry: "2026-11-21",
      dte: 33, contracts: 1, avg_cost: 2.35, mark: 0.6, unrealized_pnl: 175, pnl_pct: 74, delta: null,
      assignment_risk: false, alerts,
    },
  ],
});

const alert = {
  id: 1, trigger: "delta_breach", trigger_label: "Delta breach", detail: "Delta reached -0.42.",
  claude_recommendation: "Roll down and out.", created_at: new Date(Date.now() - 3 * 3_600_000 - 60_000).toISOString(),
};

const command = (over: Record<string, unknown> = {}) => ({
  id: 51, kind: "roll_request", status: "pending", result: null, needs_confirmation: false,
  confirm_token: null, created_at: "x", applied_at: null, as_of: "x", created: true, ...over,
});

function writes(): Array<[unknown, unknown]> {
  return apiFetchMock.mock.calls
    .filter((c) => (c[1] as RequestInit | undefined)?.method === "POST")
    .map((c) => [c[0], JSON.parse(String((c[1] as RequestInit).body))]);
}

const card = <RollCard underlying="AAPL" symbol={SYMBOL} strike={180} right="P" />;

function confirmDialog() {
  const dialog = screen.getByRole("dialog");
  const buttons = dialog.querySelectorAll("button");
  fireEvent.click(buttons[buttons.length - 1]);
}

beforeEach(() => {
  (apiFetchMock as unknown as { mockClear: () => void }).mockClear();
  localStorage.clear();
});

describe("RollCard", () => {
  it("lists the alerts fired on this contract, with Claude's view labelled", async () => {
    renderWithQuery(card, { "/options/shorts": shorts([alert]), "/options/controls": controls });
    expect(await screen.findByText("Delta breach")).toBeInTheDocument();
    expect(screen.getByText("Delta reached -0.42.")).toBeInTheDocument();
    expect(screen.getByText("3h ago")).toBeInTheDocument();
    expect(screen.getByText("Claude's view:")).toBeInTheDocument();
    expect(screen.getByText(/Roll down and out\./)).toBeInTheDocument();
  });

  it("says so when no alert has fired", async () => {
    renderWithQuery(card, { "/options/shorts": shorts([]), "/options/controls": controls });
    expect(await screen.findByText("No roll alert has fired on this contract.")).toBeInTheDocument();
  });

  it("is a secondary button, never lime: it proposes, it does not trade", async () => {
    renderWithQuery(card, { "/options/shorts": shorts([]), "/options/controls": controls });
    expect(await screen.findByRole("button", { name: "Propose a roll" })).toHaveAttribute("data-variant", "secondary");
  });

  it("opens the confirmation before any request", async () => {
    renderWithQuery(card, { "/options/shorts": shorts([]), "/options/controls": controls });
    fireEvent.click(await screen.findByRole("button", { name: "Propose a roll" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(writes()).toEqual([]);
  });

  it("sends one roll_request with the contract's symbol on confirm, then shows the receipt", async () => {
    renderWithQuery(card, { "/options/shorts": shorts([]), "/options/controls": controls, "/commands": command() });
    fireEvent.click(await screen.findByRole("button", { name: "Propose a roll" }));
    confirmDialog();
    await waitFor(() => expect(writes()).toEqual([["/commands", { kind: "roll_request", payload: { position_symbol: SYMBOL } }]]));
    expect(await screen.findByTestId("command-receipt")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Propose a roll" })).toBeDisabled();
  });

  it("answers no_qualifying_roll in plain words, not as an error", async () => {
    renderWithQuery(card, {
      "/options/shorts": shorts([]),
      "/options/controls": controls,
      "/commands": command({ status: "failed", result: { reason: "no_qualifying_roll", detail: {} } }),
    });
    fireEvent.click(await screen.findByRole("button", { name: "Propose a roll" }));
    confirmDialog();
    const receipt = await screen.findByTestId("command-receipt");
    expect(receipt.getAttribute("data-state")).toBe("answered");
    expect(within(receipt).getByText(/real answer, not an error/)).toBeInTheDocument();
  });

  it("says the alerts could not be read, and still offers the roll", async () => {
    renderWithQuery(card, { "/options/controls": controls });
    expect(await screen.findByText("Roll alerts could not be loaded right now.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Propose a roll" })).toBeEnabled();
  });
});
