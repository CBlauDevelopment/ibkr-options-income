"use client";

import { useSyncExternalStore } from "react";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { STRATEGY_FILTERS, STRATEGY_LABEL, kindOf } from "@/lib/strategy";
import { useStrategyFilter } from "@/lib/useStrategyFilter";
import { AccountHero } from "./AccountHero";
import { NeedsYou, usePendingApprovals } from "./NeedsYou";
import { PayCard } from "./PayCard";
import { PositionsCard } from "./PositionsCard";
import { ProposalsBanner } from "./ProposalsBanner";

const noSubscribe = () => () => {};

/**
 * False for the server render and for the hydration pass, true from then on. Home sits inside a
 * Suspense boundary (useSearchParams), which React hydrates after the rail; by then the rail's
 * approvals query, which shares Home's key, may already have landed, so Home's cards and counts
 * would render from data the server never had and hydration would fail. Rendering the bare page
 * until hydration is over keeps the two passes identical; production prerenders this page with
 * the boundary's empty fallback anyway, so nothing is lost there.
 */
function useHydrated(): boolean {
  return useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
}

export function HomePage() {
  const hydrated = useHydrated();
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

  const heading = (
    // The page's name for heading navigation; the hero number is the visual title.
    <h1 className="sr-only">Home</h1>
  );
  if (!hydrated) return <div className="mx-auto max-w-[1200px] px-4 py-5 md:px-7 md:py-6">{heading}</div>;

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-5 md:px-7 md:py-6">
      {heading}
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
