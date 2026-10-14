import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

describe("THEME_INIT_SCRIPT follow-OS listener", () => {
  // The storage-throws test above leaves its getItem spy installed; these tests need real storage.
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  /** Stub matchMedia, run the script, and hand back the "change" listeners it registered. */
  function runAndCapture(systemDark: boolean): Array<(e: { matches: boolean }) => void> {
    const listeners: Array<(e: { matches: boolean }) => void> = [];
    vi.stubGlobal("matchMedia", (q: string) => ({
      matches: systemDark && q === "(prefers-color-scheme: dark)",
      media: q,
      addEventListener: (type: string, fn: (e: { matches: boolean }) => void) => {
        if (type === "change") listeners.push(fn);
      },
      removeEventListener: () => {},
    }));
    runInitScript();
    return listeners;
  }

  it("re-applies the theme app-wide when the OS flips and the preference is system", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "system");
    const listeners = runAndCapture(false);
    expect(listeners).toHaveLength(1);
    expect(document.documentElement.dataset.theme).toBe("light");
    listeners[0]({ matches: true });
    expect(document.documentElement.dataset.theme).toBe("dark");
    listeners[0]({ matches: false });
    expect(document.documentElement.dataset.theme).toBe("light");
  });
  it("ignores an OS flip when the preference is light or dark", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "light");
    const light = runAndCapture(false);
    expect(light).toHaveLength(1);
    light[0]({ matches: true });
    expect(document.documentElement.dataset.theme).toBe("light");

    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    const dark = runAndCapture(true);
    expect(dark).toHaveLength(1);
    dark[0]({ matches: false });
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
  it("re-reads the stored preference at flip time, not at load time", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "system");
    const listeners = runAndCapture(false);
    localStorage.setItem(THEME_STORAGE_KEY, "light");
    expect(listeners).toHaveLength(1);
    listeners[0]({ matches: true });
    expect(document.documentElement.dataset.theme).toBe("light");
  });
  it("survives storage throwing inside the listener", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "system");
    const listeners = runAndCapture(false);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(listeners).toHaveLength(1);
    expect(() => listeners[0]({ matches: true })).not.toThrow();
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
