import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CommandStatus } from "@/lib/commands";
import { RollModeControl } from "./RollModeControl";

function withClient(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const submitCommand = vi.fn();
vi.mock("@/lib/commands", async () => {
  const actual = await vi.importActual("@/lib/commands");
  return {
    ...(actual as object),
    submitCommand: (...args: unknown[]) => submitCommand(...args),
  };
});

afterEach(cleanup);
afterEach(() => submitCommand.mockReset());

function command(overrides: Partial<CommandStatus> = {}): CommandStatus {
  return {
    id: 7,
    kind: "set_roll_mode",
    status: "applied",
    result: { mode: "propose", previous: "auto" },
    needs_confirmation: false,
    confirm_token: null,
    created_at: "2026-10-15T10:00:00Z",
    applied_at: "2026-10-15T10:00:02Z",
    as_of: "2026-10-15T10:00:02Z",
    ...overrides,
  };
}

describe("RollModeControl", () => {
  it("offers the two handlings and shows the current one", () => {
    withClient(<RollModeControl mode="auto" />);
    const select = screen.getByTestId("roll-mode-select") as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.value)).toEqual(["auto", "propose"]);
    expect(select.value).toBe("auto");
  });

  it("switching to Propose only applies at once, with no dialog", async () => {
    submitCommand.mockResolvedValue(command());
    withClient(<RollModeControl mode="auto" />);
    fireEvent.change(screen.getByTestId("roll-mode-select"), { target: { value: "propose" } });
    expect(screen.queryByTestId("confirm-dialog")).toBeNull();
    await waitFor(() =>
      expect(submitCommand).toHaveBeenCalledWith("set_roll_mode", { mode: "propose" }),
    );
    await waitFor(() => expect(screen.getByTestId("command-receipt")).toBeTruthy());
  });

  it("switching to Auto-execute is click-through confirmed first", async () => {
    submitCommand.mockResolvedValue(command({ result: { mode: "auto", previous: "propose" } }));
    withClient(<RollModeControl mode="propose" />);
    fireEvent.change(screen.getByTestId("roll-mode-select"), { target: { value: "auto" } });
    expect(submitCommand).not.toHaveBeenCalled();
    expect(screen.getByTestId("confirm-dialog").textContent).toContain("without asking you");
    fireEvent.click(screen.getByRole("button", { name: "Set Auto-execute" }));
    await waitFor(() =>
      expect(submitCommand).toHaveBeenCalledWith("set_roll_mode", { mode: "auto" }),
    );
  });

  it("cancelling the dialog sends nothing, and the current mode sends nothing", () => {
    withClient(<RollModeControl mode="propose" />);
    fireEvent.change(screen.getByTestId("roll-mode-select"), { target: { value: "propose" } });
    expect(submitCommand).not.toHaveBeenCalled();
    fireEvent.change(screen.getByTestId("roll-mode-select"), { target: { value: "auto" } });
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(submitCommand).not.toHaveBeenCalled();
  });

  it("is disabled while its command is pending", async () => {
    submitCommand.mockResolvedValue(command({ status: "pending", applied_at: null }));
    withClient(<RollModeControl mode="auto" />);
    fireEvent.change(screen.getByTestId("roll-mode-select"), { target: { value: "propose" } });
    await waitFor(() => expect(screen.getByTestId("command-receipt")).toBeTruthy());
    expect((screen.getByTestId("roll-mode-select") as HTMLSelectElement).disabled).toBe(true);
  });

  it("says in words when the command could not be created", async () => {
    submitCommand.mockRejectedValue(new Error("boom"));
    withClient(<RollModeControl mode="auto" />);
    fireEvent.change(screen.getByTestId("roll-mode-select"), { target: { value: "propose" } });
    await waitFor(() => expect(screen.getByTestId("command-error")).toBeTruthy());
    expect(screen.getByTestId("command-error").textContent).toContain("Nothing was sent");
  });
});
