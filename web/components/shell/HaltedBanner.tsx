"use client";

import { formatDateTime } from "@/lib/format";
import { useControls } from "./BotCard";

/** Global: a halted system is unmissable on every page, in words, not colour. */
export function HaltedBanner() {
  const { data } = useControls();
  if (!data?.halted) return <span data-testid="halted-banner-probe" hidden />;
  return (
    <div role="alert" className="bg-flag px-4 py-2.5 text-sm text-on-flag md:px-7">
      <span className="font-bold">Trading is halted</span>
      {data.halt_reason && <span>: {data.halt_reason}</span>}
      {data.halted_at && <span> (since {formatDateTime(data.halted_at)})</span>}
      <span>
        . No new orders will be queued or transmitted; profit-take closes still run. Open Bot controls to
        resume.
      </span>
    </div>
  );
}
