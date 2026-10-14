"use client";

import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StatusWord } from "@/components/ui/StatusWord";
import { apiFetch } from "@/lib/api";
import { UNKNOWN } from "@/lib/format";
import { formatMoneyCell } from "@/lib/money";
import { HeroChart } from "./HeroChart";
import { formatDay, heroDelay, heroFigures } from "./hero";
import type { AccountValueResponse, RangeKey } from "./types";

const RANGES: { value: RangeKey; label: string }[] = [
  { value: "1d", label: "1D" },
  { value: "1w", label: "1W" },
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "ytd", label: "YTD" },
  { value: "all", label: "All" },
];

const MINUS = "−";

function signedMoney(v: number): string {
  if (v === 0) return "$0";
  return `${v > 0 ? "+" : MINUS}${formatMoneyCell(Math.abs(v))}`;
}

/** `now` is injectable for tests; the page passes nothing and each render reads the clock. */
export function AccountHero({ now }: { now?: Date } = {}) {
  const [range, setRange] = useState<RangeKey>("1m");
  const [hover, setHover] = useState<number | null>(null);
  const { data, isError } = useQuery({
    queryKey: ["portfolio", "value", range],
    queryFn: () => apiFetch<AccountValueResponse>(`/portfolio/value?range=${range}`),
    refetchInterval: 60_000,
  });

  if (isError && !data) {
    return <p className="text-sm text-muted">Account value is unavailable right now. This page keeps retrying.</p>;
  }
  if (!data) {
    // Shaped like the loaded hero (label, number, delta, chart) so nothing jumps when it lands.
    return (
      <div aria-busy="true" aria-label="Loading account value" role="status">
        <div className="h-4 w-28 rounded bg-sunk" />
        <div className="mt-2 h-10 w-56 rounded-xl bg-sunk md:h-12" />
        <div className="mt-2 h-4 w-40 rounded bg-sunk" />
        <div className="mt-3 h-[160px] w-full rounded-xl bg-sunk" />
      </div>
    );
  }

  const series = data.series;
  const f = heroFigures(series, hover);
  const flat = f.delta === null || f.delta === 0;
  // The day's change is null when the headline value is not from today (weekend, before the
  // first snapshot): keep the value, say so, and name the day the value is from.
  const lastValueFrom =
    f.value !== null && f.delta === null && hover === null && series.latest_at
      ? ` · last value ${formatDay(series.latest_at)}`
      : "";
  // A degraded source says so in words (DESIGN.md flag amber): the positions card's Delayed
  // rule, in market hours only, so a legitimate last close is never flagged.
  const delay = heroDelay(series, now ?? new Date());
  return (
    <section aria-label="Account value">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.8125rem] text-muted">
        <span>Account value</span>
        {delay !== null && (
          <>
            <StatusWord tone="flag">Delayed</StatusWord>
            <span>{delay}</span>
          </>
        )}
      </div>
      <div
        className={clsx(
          "tabular mt-0.5 text-[2.375rem] font-extrabold leading-[1.05] tracking-[-0.025em] md:text-[2.875rem]",
          f.value === null && "hatch w-fit text-unknown",
        )}
      >
        {f.value === null ? UNKNOWN : formatMoneyCell(f.value)}
      </div>
      <div
        className={clsx(
          "tabular mt-1 text-sm font-semibold",
          flat ? "text-muted" : f.delta! < 0 ? "text-loss" : "text-gain",
        )}
      >
        {f.delta === null ? (
          <>
            {/* Unknown carries the hatch as well as the word (DESIGN.md Words First). */}
            <span className="hatch">{UNKNOWN}</span>
            {` ${f.caption}${lastValueFrom}`}
          </>
        ) : (
          `${signedMoney(f.delta)} (${f.deltaPct === null ? UNKNOWN : `${Math.abs(f.deltaPct).toFixed(2)}%`}) ${f.caption}`
        )}
      </div>
      {series.points.length === 0 ? (
        <p className="mt-6 text-sm text-muted">No account history yet.</p>
      ) : (
        <HeroChart points={series.points} onHover={setHover} />
      )}
      {/* The 10px row gap clears the chips' 44px phone hit areas when the credit wraps below. */}
      <div className="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-2.5">
        <SegmentedControl
          label="Chart range"
          appearance="quiet"
          options={RANGES}
          value={range}
          onChange={(r) => {
            setHover(null);
            setRange(r);
          }}
          className="max-md:flex max-md:w-full max-md:justify-between"
        />
        {series.points.length > 0 && (
          // The chart library's licence asks for a link to tradingview.com on the page; the
          // chart's own logo is off so it never covers the line.
          <a
            href="https://www.tradingview.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-6 items-center text-xs text-muted underline-offset-2 hover:underline max-md:ml-auto"
          >
            Chart by TradingView<span className="sr-only"> (opens in a new tab)</span>
          </a>
        )}
      </div>
    </section>
  );
}
