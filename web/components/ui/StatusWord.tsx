import clsx from "clsx";
import type { ReactNode } from "react";

export type StatusTone = "neutral" | "flag" | "today";

const TONE: Record<StatusTone, string> = {
  neutral: "bg-sunk text-muted",
  flag: "bg-flag text-on-flag",
  today: "bg-primary text-on-primary",
};

export function StatusWord({ tone = "neutral", children }: { tone?: StatusTone; children: ReactNode }) {
  return (
    <span
      data-tone={tone}
      className={clsx(
        "inline-block whitespace-nowrap rounded-[6px] px-2 py-px text-xs font-semibold tracking-[0.04em]",
        TONE[tone],
      )}
    >
      {children}
    </span>
  );
}
