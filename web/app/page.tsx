import { Suspense } from "react";
import { HomePage } from "@/features/home/HomePage";

// useSearchParams (the strategy switcher) needs a Suspense boundary under the App Router.
export default function Page() {
  return (
    <Suspense>
      <HomePage />
    </Suspense>
  );
}
