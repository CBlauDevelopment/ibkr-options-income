import { act, renderHook } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
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

  it("hydrates a server-rendered toggle without a mismatch, then shows the stored preference", async () => {
    function Toggle() {
      const [pref, setPref] = useThemePref();
      return (
        <div>
          {(["light", "dark", "system"] as const).map((p) => (
            <button key={p} type="button" aria-pressed={pref === p} onClick={() => setPref(p)}>
              {p}
            </button>
          ))}
        </div>
      );
    }
    // The server has no storage, so it always renders light; the browser then has dark stored.
    const html = renderToString(<Toggle />);
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    const container = document.createElement("div");
    container.innerHTML = html;
    document.body.appendChild(container);
    const errors = vi.spyOn(console, "error").mockImplementation(() => {});
    try {
      await act(async () => {
        hydrateRoot(container, <Toggle />);
      });
      expect(errors).not.toHaveBeenCalled();
      const pressed = (name: string) =>
        [...container.querySelectorAll("button")].find((b) => b.textContent === name)?.getAttribute("aria-pressed");
      expect(pressed("dark")).toBe("true");
      expect(pressed("light")).toBe("false");
    } finally {
      errors.mockRestore();
      container.remove();
    }
  });
});
