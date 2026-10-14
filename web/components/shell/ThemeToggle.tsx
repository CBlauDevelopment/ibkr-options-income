"use client";

import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { ThemePref } from "@/lib/theme";
import { useThemePref } from "@/lib/useThemePref";

const OPTIONS: { value: ThemePref; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "Follow OS" },
];

export function ThemeToggle() {
  const [pref, setPref] = useThemePref();
  return <SegmentedControl label="Theme" options={OPTIONS} value={pref} onChange={setPref} />;
}
