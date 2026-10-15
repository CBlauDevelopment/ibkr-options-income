import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CommandStatus } from "@/lib/commands";
import { renderWithQuery } from "@/lib/test-query";
import { TargetCard } from "./TargetCard";

const submitCommand = vi.fn();
vi.mock("@/lib/commands", async () => {
  const actual = await vi.importActual("@/lib/commands");
  return { ...(actual as object), submitCommand: (...args: unknown[]) => submitCommand(...args) };
});

afterEach(cleanup);
afterEach(() => submitCommand.mockReset());

const NOW = "2026-10-15T10:00:00Z";
const target = (t: object, source = "web") => ({
  as_of: NOW,
  source,
  target: { mode: "off", amount: null, pct: null, base: null, ...t },
});
const month = (start: number | null) => ({
  as_of: NOW,
  book: "paper",
  spreads_available: true,
  pay: { month: "2026-10-01", month_start_value: start },
});
const controls = { drain_healthy: true };

const serve = (t: object, source = "web", start: number | null = 200_000) => ({
  "/pnl/target": target(t, source),
  "/pnl/month": month(start),
  "/options/controls": controls,
});

function applied(): CommandStatus {
  return {
    id: 9,
    kind: "set_income_target",
    status: "applied",
    result: {},
    needs_confirmation: false,
    confirm_token: null,
    created_at: NOW,
    applied_at: NOW,
    as_of: NOW,
  };
}

describe("TargetCard", () => {
  it("starts on the stored mode and says where a config value comes from", async () => {
    renderWithQuery(<TargetCard />, serve({ mode: "pct_of_account", pct: 1.5 }, "config"));
    expect(await screen.findByRole("button", { name: "% of account", pressed: true })).toBeInTheDocument();
    expect(screen.getByLabelText("Percent of the account a month")).toHaveValue("1.5");
    expect(screen.getByText(/comes from the config file/)).toBeInTheDocument();
  });

  it("previews a percent of the account against the month's opening value", async () => {
    renderWithQuery(<TargetCard />, serve({ mode: "pct_of_account", pct: 1.5 }));
    expect(
      await screen.findByText("1.5% of $200,000, the account's value when October began, is $3,000 for October."),
    ).toBeInTheDocument();
  });

  it("offers each mode's own fields and no others", async () => {
    renderWithQuery(<TargetCard />, serve({}));
    await screen.findByRole("button", { name: "None", pressed: true });
    expect(screen.queryByRole("textbox")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Fixed" }));
    expect(screen.getByLabelText("Amount a month")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "% of amount" }));
    expect(screen.getByLabelText("Percent a month")).toBeInTheDocument();
    expect(screen.getByLabelText("Of this amount")).toBeInTheDocument();
    expect(screen.queryByLabelText("Amount a month")).toBeNull();
  });

  it("keeps Save off until the draft differs from what is stored", async () => {
    renderWithQuery(<TargetCard />, serve({ mode: "fixed", amount: 2000 }));
    const save = await screen.findByRole("button", { name: "Save target" });
    expect(save).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Amount a month"), { target: { value: "2500" } });
    expect(save).toBeEnabled();
  });

  it("saves only the fields of the chosen mode, then shows the receipt", async () => {
    submitCommand.mockResolvedValue(applied());
    renderWithQuery(<TargetCard />, serve({}));
    await screen.findByRole("button", { name: "None", pressed: true });
    fireEvent.click(screen.getByRole("button", { name: "% of amount" }));
    fireEvent.change(screen.getByLabelText("Percent a month"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Of this amount"), { target: { value: "100,000" } });
    expect(screen.getByText("2% of $100,000 is $2,000 a month.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save target" }));
    await waitFor(() =>
      expect(submitCommand).toHaveBeenCalledWith("set_income_target", { mode: "pct_of_amount", pct: 2, base: 100000 }),
    );
    expect(await screen.findByTestId("command-receipt")).toBeInTheDocument();
  });

  it("names a bad field and sends nothing", async () => {
    renderWithQuery(<TargetCard />, serve({ mode: "fixed", amount: 2000 }));
    await screen.findByRole("button", { name: "Save target" });
    fireEvent.change(screen.getByLabelText("Amount a month"), { target: { value: "0" } });
    fireEvent.click(screen.getByRole("button", { name: "Save target" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Enter an amount above $0");
    expect(screen.getByLabelText("Amount a month")).toHaveAttribute("aria-invalid", "true");
    expect(submitCommand).not.toHaveBeenCalled();
  });

  it("says in words when the command could not be created", async () => {
    submitCommand.mockRejectedValue(new Error("boom"));
    renderWithQuery(<TargetCard />, serve({}));
    await screen.findByRole("button", { name: "None", pressed: true });
    fireEvent.click(screen.getByRole("button", { name: "Fixed" }));
    fireEvent.change(screen.getByLabelText("Amount a month"), { target: { value: "1000" } });
    fireEvent.click(screen.getByRole("button", { name: "Save target" }));
    expect(await screen.findByTestId("command-error")).toHaveTextContent("Nothing was changed");
  });

  it("saves 'None' as an explicit off, so the config fallback no longer applies", async () => {
    submitCommand.mockResolvedValue(applied());
    renderWithQuery(<TargetCard />, serve({ mode: "pct_of_account", pct: 1 }, "config"));
    await screen.findByRole("button", { name: "% of account", pressed: true });
    fireEvent.click(screen.getByRole("button", { name: "None" }));
    fireEvent.click(screen.getByRole("button", { name: "Save target" }));
    await waitFor(() => expect(submitCommand).toHaveBeenCalledWith("set_income_target", { mode: "off" }));
  });

  it("tells the pct-of-account preview when the opening value is not on record", async () => {
    renderWithQuery(<TargetCard />, serve({ mode: "pct_of_account", pct: 1.5 }, "web", null));
    expect(await screen.findByText(/opening value is not on record yet/)).toBeInTheDocument();
  });
});
