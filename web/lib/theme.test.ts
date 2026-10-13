import { afterEach, describe, expect, it, vi } from "vitest";
import {
  THEME_INIT_SCRIPT,
  THEME_STORAGE_KEY,
  applyTheme,
  parsePref,
  resolveTheme,
} from "./theme";

function runInitScript() {
  // The script is shipped as a string into <head>; run it the same way the browser does.
  new Function(THEME_INIT_SCRIPT)();
}

function stubSystemDark(dark: boolean) {
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: dark && q === "(prefers-color-scheme: dark)",
    media: q,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  delete document.documentElement.dataset.theme;
  delete document.documentElement.dataset.themePref;
});

describe("parsePref", () => {
  it("defaults anything unknown to light", () => {
    expect(parsePref(null)).toBe("light");
    expect(parsePref("purple")).toBe("light");
  });
  it("keeps the three real values", () => {
    expect(parsePref("light")).toBe("light");
    expect(parsePref("dark")).toBe("dark");
    expect(parsePref("system")).toBe("system");
  });
});

describe("resolveTheme", () => {
  it("follows the OS only for system", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });
});

describe("THEME_INIT_SCRIPT", () => {
  it("paints light when nothing is stored", () => {
    stubSystemDark(true);
    runInitScript();
    expect(document.documentElement.dataset.theme).toBe("light");
  });
  it("paints dark when dark is stored", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    runInitScript();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
  it("paints dark for system on a dark OS", () => {
    stubSystemDark(true);
    localStorage.setItem(THEME_STORAGE_KEY, "system");
    runInitScript();
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(document.documentElement.dataset.themePref).toBe("system");
  });
  it("falls back to light when storage throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    runInitScript();
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});

describe("applyTheme", () => {
  it("writes the resolved theme and the preference onto <html>", () => {
    stubSystemDark(false);
    expect(applyTheme("system")).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement.dataset.themePref).toBe("system");
  });
});
