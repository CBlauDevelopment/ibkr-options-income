"use client";

import Link from "next/link";
import { Card } from "@/components/ui/Card";
import type { StrategyFilter } from "@/lib/strategy";
import { usePendingApprovals } from "./NeedsYou";

/** Below 1024px the needs-you column becomes this one line (DESIGN.md Layout). */
export function ProposalsBanner({ strategy }: { strategy: StrategyFilter }) {
  const { visible } = usePendingApprovals(strategy);
  if (strategy === "spread" || visible.length === 0) return null;
  const names = visible
    .slice(0, 3)
    .map((a) => `${a.underlying} ${a.right === "C" ? "call" : "put"}`)
    .join(" · ");
  return (
    <Card as="div" className="mt-4 flex items-center justify-between gap-3">
      <div>
        <div className="font-bold">
          {visible.length} proposal{visible.length === 1 ? "" : "s"} need{visible.length === 1 ? "s" : ""} you
        </div>
        <div className="text-[0.8125rem] text-muted">{names}</div>
      </div>
      <Link
        href="/trades"
        aria-label="Open Trades"
        className="inline-flex min-h-11 flex-none items-center rounded-full bg-primary px-[18px] font-bold text-on-primary transition-transform duration-[90ms] hover:bg-primary-deep active:scale-[0.98]"
      >
        Open
      </Link>
    </Card>
  );
}
