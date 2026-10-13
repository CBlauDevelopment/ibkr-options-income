"use client";

import clsx from "clsx";
import { ChevronDown } from "lucide-react";
import { useId, useState, type ReactNode } from "react";

export function Disclosure({
  summary,
  children,
  defaultOpen = false,
  tone = "sunk",
}: {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  tone?: "sunk" | "plain";
}) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  return (
    <div className={clsx("rounded-xl", tone === "sunk" && "bg-sunk px-3 py-2.5")}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2.5 text-left"
      >
        <span className="min-w-0 flex-1">{summary}</span>
        <span
          aria-hidden="true"
          className={clsx(
            "grid h-[22px] w-[22px] flex-none place-items-center rounded-full",
            "transition-transform duration-[180ms] ease-out motion-reduce:transition-none",
            tone === "sunk" ? "bg-surface" : "bg-sunk",
            open && "rotate-180",
          )}
        >
          <ChevronDown size={14} strokeWidth={2.25} />
        </span>
      </button>
      {/* The panel appears in place: no height animation (DESIGN.md Motion). */}
      <div id={panelId} hidden={!open} className="pt-2">
        {children}
      </div>
    </div>
  );
}
