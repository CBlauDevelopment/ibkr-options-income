import clsx from "clsx";
import { UNKNOWN } from "@/lib/format";
import type { IdealZonePayload } from "./types";

// Two questions, two lines: is the strike where it ought to be (a share price against the strike
// zone), and does the premium clear the least credit worth taking (an option price against the
// floor)? They are different units, so they never share an axis.

export function zoneWords(strike: number | null, lo: number | null, hi: number | null): string | null {
  if (strike == null || lo == null || hi == null) return null;
  if (strike < Math.min(lo, hi)) return "below the zone";
  if (strike > Math.max(lo, hi)) return "above the zone";
  return "inside the zone";
}

export function creditWords(premium: number | null, minCredit: number | null): string | null {
  if (premium == null || minCredit == null) return null;
  if (Math.abs(premium - minCredit) < 0.005) return "exactly at it";
  return premium > minCredit ? "above it" : "below it";
}

function Figure({ value }: { value: number | null }) {
  if (value == null) return <span className="hatch font-mono text-unknown">{UNKNOWN}</span>;
  // A debit roll's net is below zero: the minus sign leads the dollar sign, never "$-0.30".
  const text = value < 0 ? `−$${Math.abs(value).toFixed(2)}` : `$${value.toFixed(2)}`;
  return <span className="tabular font-mono">{text}</span>;
}

function StrikeBand({ lo, hi, strike }: { lo: number; hi: number; strike: number }) {
  const min = Math.min(lo, hi, strike);
  const max = Math.max(lo, hi, strike);
  const range = max - min || 1;
  // 5% to 95%, so a marker at either end stays inside the track.
  const pct = (v: number) => 5 + ((v - min) / range) * 90;
  return (
    <div aria-hidden="true" className="relative mt-2 h-2.5 rounded-full bg-sunk">
      <div
        className="absolute top-0 h-full rounded-full bg-sunk-deep"
        style={{ left: `${pct(Math.min(lo, hi))}%`, width: `${Math.abs(pct(hi) - pct(lo))}%` }}
      />
      <div className="absolute -top-1 h-[18px] w-0.5 -translate-x-1/2 rounded-full bg-content" style={{ left: `${pct(strike)}%` }} />
    </div>
  );
}

export function IdealZoneBar({
  ideal,
  premium,
  strike,
}: {
  ideal: IdealZonePayload;
  premium: number | null;
  strike: number | null;
}) {
  const { lo, hi, min_credit: minCredit } = ideal;
  if (lo == null && hi == null && minCredit == null) {
    return <p className="text-sm text-muted">No ideal zone derived.</p>;
  }
  const zone = zoneWords(strike, lo, hi);
  const credit = creditWords(premium, minCredit);
  return (
    <div className="grid gap-4 text-sm">
      <div>
        <p>
          Strike zone <Figure value={lo} /> to <Figure value={hi} />
          {strike != null && (
            <>
              {" · this strike "}
              <Figure value={strike} />
              {zone && <span className="text-muted">, {zone}</span>}
            </>
          )}
        </p>
        {lo != null && hi != null && strike != null && <StrikeBand lo={lo} hi={hi} strike={strike} />}
      </div>
      <p>
        Least credit worth taking <Figure value={minCredit} /> a share
        {premium != null && (
          <>
            {" · this one pays "}
            <Figure value={premium} />
            {credit && <span className={clsx("text-muted")}>, {credit}</span>}
          </>
        )}
      </p>
    </div>
  );
}
