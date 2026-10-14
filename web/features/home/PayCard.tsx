"use client";

import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Disclosure } from "@/components/ui/Disclosure";
import { Meter } from "@/components/ui/Meter";
import { StatusWord } from "@/components/ui/StatusWord";
import { Stub, formatStubValue, type StubLineData } from "@/components/ui/Stub";
import { apiFetch } from "@/lib/api";
import { UNKNOWN } from "@/lib/format";
import { formatMoneyCell } from "@/lib/money";
import type { StrategyFilter } from "@/lib/strategy";
import type { MonthPay, MonthPayResponse } from "./types";

const MONTH = new Intl.DateTimeFormat("en-US", { month: "long", timeZone: "UTC" });

/** `unknown` blanks every figure: a month whose only income source could not be read. */
export function payStubLines(pay: MonthPay, unknown = false): StubLineData[] {
  return [
    {
      label: "Premium collected",
      value: unknown ? null : pay.premium_collected,
      format: "signed-money",
      explain: `Credit from ${pay.n_opened} position${pay.n_opened === 1 ? "" : "s"} sold this month.`,
    },
    {
      label: "Bought back",
      value: unknown ? null : -pay.bought_back,
      format: "signed-money",
      explain: `What it cost to close ${pay.n_closed} position${pay.n_closed === 1 ? "" : "s"} this month.`,
    },
    {
      label: pay.commissions_complete ? "Commissions" : "Commissions (incomplete)",
      value: unknown ? null : -pay.commissions,
      format: "signed-money",
      explain: pay.commissions_complete
        ? "IBKR commissions on every fill that touched this month."
        : "Some fills have no commission recorded yet, so this is a lower bound.",
    },
    { label: "Net so far", value: unknown ? null : pay.net, format: "signed-money", total: true },
  ];
}

export function PayCard({ strategy }: { strategy: StrategyFilter }) {
  const { data, isError } = useQuery({
    queryKey: ["pnl", "month", strategy],
    queryFn: () => apiFetch<MonthPayResponse>(`/pnl/month?strategy=${strategy}`),
    refetchInterval: 60_000,
  });

  if (isError && !data) {
    return (
      <Card className="mt-4">
        <p className="text-sm text-muted">Could not load this month's pay.</p>
        <p className="mt-1 text-[0.8125rem] text-muted">It tries again every minute.</p>
      </Card>
    );
  }
  if (!data) {
    return (
      <Card as="div" className="mt-4 h-[104px]" role="status" aria-busy="true" aria-label="Loading this month's pay" />
    );
  }

  const pay = data.pay;
  const month = MONTH.format(new Date(pay.month));
  // A spreads book is in scope but data/spreads.db could not be read. Never show the wheel's
  // total as the whole month, and never show an unread spreads-only month as $0.
  const spreadsOut = data.spreads_available === false && (pay.strategy === "all" || pay.strategy === "spread");
  const wholeUnknown = spreadsOut && pay.strategy === "spread";
  const net = wholeUnknown ? null : pay.net;
  const pace =
    wholeUnknown || pay.target === null
      ? `No target set · ${pay.days_left} days left`
      : pay.progress_pct === null
        ? `${UNKNOWN} of target · ${pay.days_left} days left`
        : `${Math.round(Math.max(0, pay.progress_pct))}% of target · ${pay.days_left} days left`;

  return (
    <Card className="mt-4">
      <Disclosure
        tone="plain"
        summary={
          <span className="block">
            <span className="flex items-baseline justify-between gap-2.5">
              <span className="text-base font-bold">{month} pay</span>
              <span className="tabular font-mono font-semibold">
                <span className={clsx(net === null && "hatch text-unknown")}>{formatStubValue(net, "signed-money")}</span>
                {!wholeUnknown && pay.target !== null && (
                  <span className="ml-1 font-normal text-muted">of {formatMoneyCell(pay.target)}</span>
                )}
              </span>
            </span>
            <span className="mt-2.5 block">
              <Meter value={net} max={wholeUnknown ? null : pay.target} label={`${month} target`} />
            </span>
            <span className="mt-1.5 block text-[0.8125rem] text-muted">{pace}</span>
          </span>
        }
      >
        <Stub label={`${month} pay stub`} lines={payStubLines(pay, wholeUnknown)} />
      </Disclosure>
      {spreadsOut && (
        <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.8125rem] text-muted">
          <StatusWord tone="flag">Spreads unavailable</StatusWord>
          <span>
            {wholeUnknown
              ? "Spread income is unavailable because the spreads database could not be read."
              : "Spread income is unavailable because the spreads database could not be read, so this total leaves it out."}
          </span>
        </p>
      )}
    </Card>
  );
}
