/**
 * Theme preference: light is the default, dark and "follow the OS" are choices.
 * The resolved theme lands on <html data-theme>, which globals.css keys every token off.
 * Every storage access is wrapped: a private window or blocked storage falls back to
 * light rather than breaking the page.
 */
export type ThemePref = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "ibkr-theme";

export function parsePref(raw: string | null | undefined): ThemePref {
  return raw === "dark" || raw === "system" || raw === "light" ? raw : "light";
}

export function resolveTheme(pref: ThemePref, systemDark: boolean): ResolvedTheme {
  if (pref === "system") return systemDark ? "dark" : "light";
  return pref;
}

export function readPref(): ThemePref {
  try {
    return parsePref(localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return "light";
  }
}

export function writePref(pref: ThemePref): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, pref);
  } catch {
    // Storage blocked: the choice still applies for this page view.
  }
}

export function systemPrefersDark(): boolean {
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  } catch {
    return false;
  }
}

export function applyTheme(pref: ThemePref): ResolvedTheme {
  const resolved = resolveTheme(pref, systemPrefersDark());
  document.documentElement.dataset.theme = resolved;
  document.documentElement.dataset.themePref = pref;
  return resolved;
}

/**
 * Runs in <head> before first paint so a dark preference never flashes light.
 * Kept as a string because it must execute before React; mirrors parsePref/resolveTheme.
 */
export const THEME_INIT_SCRIPT = `(function(){try{var p=localStorage.getItem("${THEME_STORAGE_KEY}");if(p!=="dark"&&p!=="system")p="light";var d=p==="dark"||(p==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.theme=d?"dark":"light";document.documentElement.dataset.themePref=p;}catch(e){document.documentElement.dataset.theme="light";}})();`;
