import type { StubLineData } from "@/components/ui/Stub";
import { formatMoneyCell } from "@/lib/money";
import { kindOf } from "@/lib/strategy";

export type ProposalFields = {
  underlying: string;
  strategy: string;
  right: string;
  strike: number;
  contracts: number;
  premium: number | null; // per share
  expiry: string | null;
};

const SHORT_DATE = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
/** en-CA formats as YYYY-MM-DD: the New York calendar date, which is the market's day. */
const NEW_YORK_DAY = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" });

const dollars = (v: number) => `$${v.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;

/** Calendar days from today (New York) to the expiry date. */
export function daysToExpiry(expiry: string | null, today: Date): number | null {
  if (!expiry) return null;
  const end = Date.parse(`${expiry}T00:00:00Z`);
  const start = Date.parse(`${NEW_YORK_DAY.format(today)}T00:00:00Z`);
  return Math.round((end - start) / 86_400_000);
}

export function proposalSentence(a: ProposalFields): string {
  const shares = 100 * a.contracts;
  const when = a.expiry ? SHORT_DATE.format(new Date(`${a.expiry}T00:00:00Z`)) : "expiry";
  const collect =
    a.premium === null ? "Premium not known yet." : `You collect ${formatMoneyCell(a.premium * 100 * a.contracts)}.`;
  const k = kindOf(a.strategy, a.right);
  if (k === "cc") {
    return `${collect} If ${a.underlying} closes over ${dollars(a.strike)} on ${when}, your ${shares} shares are sold at ${dollars(a.strike)}.`;
  }
  return `${collect} If ${a.underlying} closes under ${dollars(a.strike)} on ${when}, you buy ${shares} shares at ${dollars(a.strike)}.`;
}

export function proposalStub(a: ProposalFields, today: Date): StubLineData[] {
  const premium = a.premium === null ? null : a.premium * 100 * a.contracts;
  const basis = a.strike * 100 * a.contracts;
  const dte = daysToExpiry(a.expiry, today);
  const ret = premium === null || basis <= 0 ? null : (premium / basis) * 100;
  const annual = ret === null || dte === null || dte <= 0 ? null : ret * (365 / dte);
  const isCall = kindOf(a.strategy, a.right) === "cc";
  return [
    {
      label: "Premium",
      value: premium,
      format: "signed-money",
      explain:
        a.premium === null
          ? "No premium has been quoted for this contract yet."
          : `${a.contracts} contract${a.contracts === 1 ? "" : "s"} × $${a.premium.toFixed(2)} per share × 100 shares.`,
    },
    isCall
      ? {
          label: "If called, you sell for",
          value: basis,
          explain: "The strike × 100 shares per contract: what you receive if the shares are called away.",
        }
      : {
          label: "Cash held aside",
          value: basis,
          explain: "What IBKR sets aside: the strike × 100 shares, so you can buy them if assigned.",
        },
    {
      label: dte === null ? "Return" : `Return in ${dte} day${dte === 1 ? "" : "s"}`,
      value: ret,
      format: "percent",
      explain: isCall ? "Premium ÷ the strike value." : "Premium ÷ cash held aside.",
    },
    {
      label: "A year",
      value: annual,
      format: "percent",
      total: true,
      explain: "The return scaled to 365 days. A yardstick, not a forecast.",
    },
  ];
}
