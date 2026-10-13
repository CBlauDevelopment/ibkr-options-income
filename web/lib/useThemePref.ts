"use client";

import { useCallback, useEffect, useState } from "react";
import { type ThemePref, applyTheme, readPref, writePref } from "./theme";

/**
 * The current theme preference and a setter that persists and applies it. "Follow the OS"
 * itself is handled app-wide by THEME_INIT_SCRIPT's change listener, so it keeps working on
 * every page, not only while a component using this hook is mounted.
 *
 * The first render is always "light", the same value the server rendered, and the stored
 * preference is read in an effect right after hydration. Reading storage during the first
 * render instead would hand React a tree that differs from the server HTML, which React 19
 * does not patch up: the page would be dark while the wrong segment looked selected.
 */
export function useThemePref(): [ThemePref, (p: ThemePref) => void] {
  const [pref, setPrefState] = useState<ThemePref>("light");

  useEffect(() => {
    setPrefState(readPref());
  }, []);

  const setPref = useCallback((p: ThemePref) => {
    writePref(p);
    applyTheme(p);
    setPrefState(p);
  }, []);

  return [pref, setPref];
}
