"use client";

import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StatusWord } from "@/components/ui/StatusWord";
import { formatStubValue } from "@/components/ui/Stub";
import { FreshnessLabel } from "@/components/portfolio/FreshnessLabel";
import type { PositionsResponse } from "@/components/portfolio/types";
import { apiFetch } from "@/lib/api";
import { UNKNOWN } from "@/lib/format";
import { formatMoneyCell, isStale } from "@/lib/money";
import { STRATEGY_LABEL, type StrategyFilter } from "@/lib/strategy";
import { buildPositionRows, type PositionRow } from "./positions";
import type { SpreadPositionsResponse } from "./types";

type PositionsFilter = StrategyFilter | "shares";

const FILTERS: PositionsFilter[] = ["all", "csp", "cc", "spread", "shares"];
const LABEL: Record<PositionsFilter, string> = { ...STRATEGY_LABEL, shares: "Shares" };
const EMPTY: Record<PositionsFilter, string> = {
  all: "No open positions.",
  csp: "No cash-secured puts open.",
  cc: "No covered calls open.",
  spread: "No credit spreads open.",
  shares: "No shares held.",
};

/** Same threshold as PositionsPanel / SummaryPanel: twice the snapshot interval. */
const FRESH_FOR_MINUTES = 30;

function matches(row: PositionRow, f: PositionsFilter): boolean {
  return f === "all" || row.kind === f;
}

function todayNewYork(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
}

export function PositionsCard({ strategy }: { strategy: StrategyFilter }) {
  const [filter, setFilter] = useState<PositionsFilter>(strategy);
  // The page's strategy switcher wins whenever it changes; the card's own chips narrow from there.
  const [seen, setSeen] = useState<StrategyFilter>(strategy);
  if (seen !== strategy) {
    setSeen(strategy);
    setFilter(strategy);
  }

  // Same key as <PositionsPanel/> on /portfolio: one request when both are mounted.
  const positions = useQuery({
    queryKey: ["portfolio", "positions"],
    queryFn: () => apiFetch<PositionsResponse>("/portfolio/positions"),
    refetchInterval: 60_000,
  });
  const spreads = useQuery({
    queryKey: ["spreads", "positions", "open"],
    queryFn: () => apiFetch<SpreadPositionsResponse>("/spreads/positions?status=open"),
    refetchInterval: 60_000,
  });

  // Unknown is never none: an unreadable spreads book is not an empty one.
  const spreadsKnown = spreads.data?.available === true;
  const spreadsOut = spreads.isError || spreads.data?.available === false;
  const spreadRows = spreadsKnown ? spreads.data!.positions : [];
  const rows = positions.data
    ? buildPositionRows(positions.data.groups, spreadRows, todayNewYork(), spreads.data?.underlying)
    : [];
  const visible = rows.filter((r) => matches(r, filter));
  const options = FILTERS.map((f) => ({
    value: f,
    label: LABEL[f],
    count: !positions.data || (f === "spread" && !spreadsKnown) ? null : rows.filter((r) => matches(r, f)).length,
  }));

  let message: string | null = null;
  if (positions.isError && !positions.data) message = "Positions unavailable right now.";
  else if (positions.data && visible.length === 0) {
    if (filter === "spread" && spreadsOut) message = "Credit spreads are unavailable right now.";
    else if (filter === "spread" && spreads.isPending) message = "Loading credit spreads.";
    else if (positions.data.source === "none" && filter !== "spread") message = "No positions captured yet.";
    else message = EMPTY[filter];
  }
  const loading = !positions.data && !positions.isError;
  const delayed =
    positions.data !== undefined &&
    positions.data.source !== "none" &&
    (positions.data.degraded || isStale(positions.data.as_of, FRESH_FOR_MINUTES));

  return (
    <Card className="mt-4" aria-labelledby="positions-title">
      <div className="flex items-baseline justify-between">
        <h2 id="positions-title" className="text-[1.0625rem] font-bold">
          Positions
        </h2>
        <span className="text-[0.8125rem] text-muted">Sorted by expiry</span>
      </div>
      <SegmentedControl
        label="Position type"
        appearance="chips"
        options={options}
        value={filter}
        onChange={setFilter}
        className="mb-1 mt-2"
      />
      {delayed && (
        <p className="mt-2 flex flex-wrap items-center gap-2">
          <StatusWord tone="flag">Delayed</StatusWord>
          <FreshnessLabel asOf={positions.data!.as_of} freshForMinutes={FRESH_FOR_MINUTES} />
        </p>
      )}
      {loading ? (
        <div role="status" aria-busy="true" aria-label="Loading positions" className="space-y-3 py-3">
          <div className="h-9 rounded-xl bg-sunk" />
          <div className="h-9 rounded-xl bg-sunk" />
        </div>
      ) : message !== null ? (
        <p className="py-3 text-sm text-muted">{message}</p>
      ) : (
        <ul>
          {visible.map((r) => {
            const pnl = r.valueLabel === "open P&L";
            return (
              <li
                key={r.key}
                className="grid grid-cols-[1fr_auto] gap-x-2.5 border-t border-border py-[11px] text-sm first:border-t-0"
              >
                <div className="min-w-0">
                  <span className="font-bold">{r.title}</span>
                  {r.status && (
                    <span className="ml-1.5 align-[1px]">
                      <StatusWord tone={r.status.tone}>{r.status.word}</StatusWord>
                    </span>
                  )}
                  <div className="text-[0.8125rem] text-muted">{r.sub}</div>
                </div>
                <div className="tabular text-right font-semibold">
                  <span
                    className={clsx(
                      r.value === null && "hatch text-unknown",
                      r.value !== null && pnl && r.value < 0 && "text-loss",
                      r.value !== null && pnl && r.value > 0 && "text-gain",
                    )}
                  >
                    {r.value === null
                      ? UNKNOWN
                      : pnl
                        ? formatStubValue(r.value, "signed-money")
                        : formatMoneyCell(r.value)}
                  </span>
                  <div className="text-[0.8125rem] font-normal text-muted">{r.valueLabel}</div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {filter === "all" && spreadsOut && positions.data && (
        <p className="border-t border-border pt-2.5 text-[0.8125rem] text-muted">
          Credit spreads are unavailable right now, so they are not listed.
        </p>
      )}
    </Card>
  );
}
