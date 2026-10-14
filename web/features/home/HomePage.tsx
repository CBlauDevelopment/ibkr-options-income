"use client";

import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { STRATEGY_FILTERS, STRATEGY_LABEL, kindOf } from "@/lib/strategy";
import { useStrategyFilter } from "@/lib/useStrategyFilter";
import { AccountHero } from "./AccountHero";
import { NeedsYou, usePendingApprovals } from "./NeedsYou";
import { PayCard } from "./PayCard";
import { PositionsCard } from "./PositionsCard";
import { ProposalsBanner } from "./ProposalsBanner";

export function HomePage() {
  const [strategy, setStrategy] = useStrategyFilter();
  const { data } = usePendingApprovals("all");
  // Counts on the switcher are pending proposals per kind: what each tab has waiting.
  const pending = data?.approvals.filter((a) => a.status === "pending") ?? null;
  const options = STRATEGY_FILTERS.map((f) => ({
    value: f,
    label: STRATEGY_LABEL[f],
    count:
      pending === null || f === "all" || f === "spread"
        ? null
        : pending.filter((a) => kindOf(a.strategy, a.right) === f).length || null,
  }));

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-5 md:px-7 md:py-6">
      {/* The page's name for heading navigation; the hero number is the visual title. */}
      <h1 className="sr-only">Home</h1>
      <SegmentedControl label="Strategy" options={options} value={strategy} onChange={setStrategy} />
      <div className="mt-5 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0">
          <AccountHero />
          <div className="lg:hidden">
            <ProposalsBanner strategy={strategy} />
          </div>
          <PayCard strategy={strategy} />
          <PositionsCard strategy={strategy} />
        </div>
        <aside className="hidden lg:block">
          <NeedsYou strategy={strategy} />
        </aside>
      </div>
    </div>
  );
}
