import { Suspense } from "react";
import { TradesPage } from "@/features/trades/TradesPage";

// useSearchParams (the strategy switcher, the view and the day) needs a Suspense boundary under the App Router.
export default function Page() {
  return (
    <Suspense>
      <TradesPage />
    </Suspense>
  );
}
