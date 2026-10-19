import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { savePersistedCommand, type CommandStatus } from "@/lib/commands";
import { useSubmittedApprovals } from "./useSubmittedApprovals";

const command = {
  id: 7, kind: "approve", status: "pending", result: null, needs_confirmation: false,
  confirm_token: null, created_at: "", applied_at: null, as_of: "",
} as CommandStatus;

beforeEach(() => localStorage.clear());

describe("useSubmittedApprovals", () => {
  it("marks and clears an approval", () => {
    const { result } = renderHook(() => useSubmittedApprovals());
    act(() => result.current.markSubmitted(1, command));
    expect(result.current.submitted.get(1)).toEqual(command);
    act(() => result.current.clearSubmitted(1));
    expect(result.current.submitted.size).toBe(0);
  });
  it("clearing an id it does not hold keeps the same map, so nothing re-renders", () => {
    const { result } = renderHook(() => useSubmittedApprovals());
    const before = result.current.submitted;
    act(() => result.current.clearSubmitted(99));
    expect(result.current.submitted).toBe(before);
  });
  it("keeps its callbacks stable across renders", () => {
    const { result, rerender } = renderHook(() => useSubmittedApprovals());
    const { markSubmitted, clearSubmitted } = result.current;
    rerender();
    expect(result.current.markSubmitted).toBe(markSubmitted);
    expect(result.current.clearSubmitted).toBe(clearSubmitted);
  });
  it("is seeded after mount from a command persisted before a reload", () => {
    savePersistedCommand(1, command);
    const { result } = renderHook(() => useSubmittedApprovals());
    expect(result.current.submitted.has(1)).toBe(true);
  });
});
