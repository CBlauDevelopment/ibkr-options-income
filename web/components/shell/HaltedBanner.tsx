"use client";

import { formatDateTime } from "@/lib/format";
import { useControls } from "./BotCard";

/**
 * Global: a halted wheel is unmissable on every page, in words, not colour. Scoped to the
 * wheel on purpose: this is the wheel's kill switch (`system_settings`), and the credit-spreads
 * service honours only its own halt file, so the copy must not claim every order stops.
 */
export function HaltedBanner() {
  const { data } = useControls();
  if (!data?.halted) return <span data-testid="halted-banner-probe" hidden />;
  return (
    <div role="alert" className="bg-flag px-4 py-2.5 text-sm text-on-flag md:px-7">
      <span className="font-bold">Wheel trading is halted</span>
      {data.halt_reason && <span>: {data.halt_reason}</span>}
      {data.halted_at && <span> (since {formatDateTime(data.halted_at)})</span>}
      <span>
        . No new CSP or covered-call orders will be queued or sent. Credit spreads have their own halt and
        are not stopped by this one. Open Bot controls to resume.
      </span>
    </div>
  );
}
