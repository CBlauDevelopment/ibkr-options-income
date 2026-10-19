import { useSyncExternalStore } from "react";

const noSubscribe = () => () => {};

/**
 * False for the server render and for the hydration pass, true from then on. A page inside a
 * Suspense boundary (useSearchParams) hydrates after the rail; the rail's approvals query shares
 * the page's key and may already have landed, so the page would render from data the server never
 * had and hydration would fail. Rendering the bare page until hydration is over keeps the two
 * passes identical. Home and Trades both need it.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
}
