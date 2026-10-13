import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { THEME_STORAGE_KEY } from "./theme";
import { useThemePref } from "./useThemePref";

afterEach(() => {
  delete document.documentElement.dataset.theme;
});

describe("useThemePref", () => {
  it("starts from the stored preference", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    const { result } = renderHook(() => useThemePref());
    expect(result.current[0]).toBe("dark");
  });
  it("persists and applies a new choice", () => {
    const { result } = renderHook(() => useThemePref());
    act(() => result.current[1]("dark"));
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(result.current[0]).toBe("dark");
  });
});
