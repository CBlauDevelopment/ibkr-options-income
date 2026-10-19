import type { ApprovalRollFrom } from "@/components/options/types";
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

export type RollFields = {
  underlying: string;
  strike: number; // the new leg
  expiry: string | null; // the new leg
  right: string;
  contracts: number;
  premium: number | null; // the net per share: the new leg's mid less the old leg's
  roll_from?: ApprovalRollFrom | null;
};

const md = (iso: string) => SHORT_DATE.format(new Date(`${iso}T00:00:00Z`));
const rightWord = (r: string) => (r === "C" ? "call" : "put");

/** "NVDA · Roll $250 put Oct 23 → Oct 28"; the strike and the date each show a move only when they move. */
export function rollTitle(a: RollFields): string {
  const from = a.roll_from;
  if (!from) return `${a.underlying} · Roll`;
  const strikes = from.strike === a.strike ? `$${from.strike}` : `$${from.strike} → $${a.strike}`;
  const dates = !a.expiry || a.expiry === from.expiry ? md(from.expiry) : `${md(from.expiry)} → ${md(a.expiry)}`;
  return `${a.underlying} · Roll ${strikes} ${rightWord(from.right)} ${dates}`;
}

/** What the roll does, then the net at the quotes it was priced at (never presented as a fill). */
export function rollSentence(a: RollFields): string {
  const from = a.roll_from;
  if (!from) return "This rolls a position you already hold. Its legs were not recorded on this proposal.";
  const sells = a.expiry ? `the $${a.strike} ${rightWord(a.right)} expiring ${md(a.expiry)}` : `the $${a.strike} ${rightWord(a.right)}`;
  const head = `Buys back the $${from.strike} ${rightWord(from.right)} expiring ${md(from.expiry)} and sells ${sells}.`;
  if (a.premium === null) return `${head} The net is not known.`;
  const net = a.premium * 100 * a.contracts;
  return `${head} At the quotes it was priced at, that is a net ${net < 0 ? "debit" : "credit"} of ${formatMoneyCell(Math.abs(net))}.`;
}

/** Buy back, Sell, then the net: the roll's own arithmetic at the quotes it was priced at. */
export function rollStub(a: RollFields): StubLineData[] {
  const from = a.roll_from;
  if (!from) return [];
  const n = a.contracts;
  const leg = (mid: number | null, sign: 1 | -1) => (mid === null ? null : sign * mid * 100 * n);
  const net = a.premium === null ? null : a.premium * 100 * n;
  const per = (mid: number | null, what: string) =>
    mid === null
      ? `No quote was recorded for ${what}.`
      : `${n} contract${n === 1 ? "" : "s"} × $${mid.toFixed(2)} per share × 100 shares, the quote when the roll was proposed.`;
  return [
    {
      label: `Buy back $${from.strike} ${rightWord(from.right)} ${md(from.expiry)}`,
      value: leg(from.old_mid, -1),
      format: "signed-money",
      explain: per(from.old_mid, "the leg bought back"),
    },
    {
      label: `Sell $${a.strike} ${rightWord(a.right)}${a.expiry ? ` ${md(a.expiry)}` : ""}`,
      value: leg(from.new_mid, 1),
      format: "signed-money",
      explain: per(from.new_mid, "the new leg"),
    },
    {
      label: net !== null && net < 0 ? "Net debit" : "Net credit",
      value: net,
      format: "signed-money",
      total: true,
      explain: "What the roll takes in after buying back the old leg, before commissions. The fill can differ from the quote.",
    },
  ];
}

export type DecidedBy = "system" | "web" | "telegram";

const WHO: Record<DecidedBy, string> = {
  system: "by the system",
  web: "by you, on the web",
  telegram: "by you, in Telegram",
};

/** The decision in words, naming who decided only when that was recorded. Null while pending. */
export function decisionWords(status: string, decidedBy?: DecidedBy | null): string | null {
  if (status === "approved" || status === "rejected") {
    const verb = status === "approved" ? "Approved" : "Rejected";
    return decidedBy ? `${verb} ${WHO[decidedBy]}` : verb;
  }
  if (status === "expired") return "Expired unanswered";
  return null;
}
