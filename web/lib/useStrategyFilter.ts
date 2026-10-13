"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { type StrategyFilter, parseStrategyFilter } from "./strategy";

/**
 * The strategy switcher's value, kept in `?strategy=` so a reload or a shared link keeps it.
 * A page using this must render inside <Suspense> (Next's useSearchParams rule).
 */
export function useStrategyFilter(): [StrategyFilter, (f: StrategyFilter) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const value = parseStrategyFilter(params.get("strategy"));

  const set = useCallback(
    (f: StrategyFilter) => {
      const next = new URLSearchParams(params.toString());
      if (f === "all") next.delete("strategy");
      else next.set("strategy", f);
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, router, pathname],
  );

  return [value, set];
}
