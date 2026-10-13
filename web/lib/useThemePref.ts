"use client";

import { useCallback, useEffect, useState } from "react";
import { type ThemePref, applyTheme, readPref, writePref } from "./theme";

/**
 * The current theme preference and a setter that persists and applies it. While the
 * preference is "system", an OS switch (e.g. sunset on the phone) re-applies live.
 */
export function useThemePref(): [ThemePref, (p: ThemePref) => void] {
  const [pref, setPrefState] = useState<ThemePref>(() =>
    typeof window === "undefined" ? "light" : readPref(),
  );

  useEffect(() => {
    if (pref !== "system") return;
    let mq: MediaQueryList;
    try {
      mq = window.matchMedia("(prefers-color-scheme: dark)");
    } catch {
      return;
    }
    const onChange = () => applyTheme("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [pref]);

  const setPref = useCallback((p: ThemePref) => {
    writePref(p);
    applyTheme(p);
    setPrefState(p);
  }, []);

  return [pref, setPref];
}
