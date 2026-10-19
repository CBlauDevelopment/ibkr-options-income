"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { StrategyFilter } from "@/lib/strategy";
import { type TradesView, defaultView, explicitView } from "./views";

/**
 * The Trades view, kept in `?view=` beside `?strategy=` so a reload or a shared link keeps both.
 * With no view in the URL the default (ruling 2) is decided once per visit and strategy, when the
 * pending count first loads, so approving the last proposal never moves the page under you.
 * Null only while that count is still loading. A page using this must render inside <Suspense>
 * (Next's useSearchParams rule).
 */
export function useTradesView(
  strategy: StrategyFilter,
  pending: number | null,
): [TradesView | null, (v: TradesView) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const explicit = explicitView(params.get("view"), strategy);
  const fresh = defaultView(strategy, pending);
  const [decided, setDecided] = useState<Partial<Record<StrategyFilter, TradesView>>>({});

  useEffect(() => {
    if (fresh === null) return;
    setDecided((d) => (d[strategy] === undefined ? { ...d, [strategy]: fresh } : d));
  }, [fresh, strategy]);

  const set = useCallback(
    (v: TradesView) => {
      const next = new URLSearchParams(params.toString());
      next.set("view", v);
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [params, router, pathname],
  );

  return [explicit ?? decided[strategy] ?? fresh, set];
}

const DAY = /^\d{4}-\d{2}-\d{2}$/;

/** History's day in `?day=YYYY-MM-DD`; null (the parameter left out) is today in New York. */
export function useTradesDay(): [string | null, (day: string | null) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const raw = params.get("day");
  const value = raw !== null && DAY.test(raw) ? raw : null;

  const set = useCallback(
    (day: string | null) => {
      const next = new URLSearchParams(params.toString());
      if (day === null) next.delete("day");
      else next.set("day", day);
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, router, pathname],
  );

  return [value, set];
}
