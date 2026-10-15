/** The monthly income target form: text in, a validated command payload out (mirrors
 *  src/common/schemas.py IncomeTarget and its bounds). Pure, so the rules are tested apart from the
 *  card that renders them. */

export type TargetMode = "off" | "fixed" | "pct_of_account" | "pct_of_amount";

export type IncomeTarget = {
  mode: TargetMode;
  amount: number | null;
  pct: number | null;
  base: number | null;
};

export type TargetDraft = { mode: TargetMode; amount: string; pct: string; base: string };

export type TargetPayload =
  | { mode: "off" }
  | { mode: "fixed"; amount: number }
  | { mode: "pct_of_account"; pct: number }
  | { mode: "pct_of_amount"; pct: number; base: number };

export type FieldName = "amount" | "pct" | "base";

export const MAX_AMOUNT = 1_000_000;
export const MAX_PCT = 20;
export const MAX_BASE = 1_000_000_000;

const NUMBER = /^\d+(\.\d+)?$|^\.\d+$/;

/** "$2,000.50", " 1.5% " and "2000" read as numbers; anything else is null (never 0). */
export function parseNumber(text: string): number | null {
  const cleaned = text.replace(/[$,%\s]/g, "");
  if (!NUMBER.test(cleaned)) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

const show = (n: number | null): string => (n === null ? "" : String(n));

export function draftOf(t: IncomeTarget): TargetDraft {
  return { mode: t.mode, amount: show(t.amount), pct: show(t.pct), base: show(t.base) };
}

const dollars = (n: number) => `$${n.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;

function amountError(n: number | null, max: number): string | undefined {
  if (n === null || n <= 0 || n > max) return `Enter an amount above $0 and up to ${dollars(max)}.`;
  return undefined;
}

function pctError(n: number | null): string | undefined {
  if (n === null || n <= 0 || n > MAX_PCT) return `Enter a percent above 0 and up to ${MAX_PCT}.`;
  return undefined;
}

export function payloadOf(
  d: TargetDraft,
): { ok: true; payload: TargetPayload } | { ok: false; errors: Partial<Record<FieldName, string>> } {
  const amount = parseNumber(d.amount);
  const pct = parseNumber(d.pct);
  const base = parseNumber(d.base);
  if (d.mode === "off") return { ok: true, payload: { mode: "off" } };
  const errors: Partial<Record<FieldName, string>> = {};
  if (d.mode === "fixed") {
    const e = amountError(amount, MAX_AMOUNT);
    if (e) errors.amount = e;
    else return { ok: true, payload: { mode: "fixed", amount: amount! } };
  } else if (d.mode === "pct_of_account") {
    const e = pctError(pct);
    if (e) errors.pct = e;
    else return { ok: true, payload: { mode: "pct_of_account", pct: pct! } };
  } else {
    const ep = pctError(pct);
    const eb = amountError(base, MAX_BASE);
    if (ep) errors.pct = ep;
    if (eb) errors.base = eb;
    if (!ep && !eb) return { ok: true, payload: { mode: "pct_of_amount", pct: pct!, base: base! } };
  }
  return { ok: false, errors };
}

/** One plain sentence saying what the draft means this month; null while it is not a valid target. */
export function previewSentence(d: TargetDraft, monthStartValue: number | null, month: string): string | null {
  const r = payloadOf(d);
  if (!r.ok) return null;
  const p = r.payload;
  if (p.mode === "off") return "No target. The pay card shows the month's income without a goal.";
  if (p.mode === "fixed") return `The pay card aims for ${dollars(p.amount)} a month.`;
  if (p.mode === "pct_of_amount") return `${p.pct}% of ${dollars(p.base)} is ${dollars((p.base * p.pct) / 100)} a month.`;
  if (monthStartValue === null || monthStartValue <= 0) {
    return `${p.pct}% of the account's value when each month begins. ${month}'s opening value is not on record yet, so the pay card will say target n/a until it is.`;
  }
  return `${p.pct}% of ${dollars(monthStartValue)}, the account's value when ${month} began, is ${dollars((monthStartValue * p.pct) / 100)} for ${month}.`;
}

/** True when the draft would save exactly what is already stored. */
export function sameTarget(d: TargetDraft, t: IncomeTarget): boolean {
  const r = payloadOf(d);
  if (!r.ok) return false;
  const p = r.payload;
  return (
    p.mode === t.mode &&
    ("amount" in p ? p.amount : null) === t.amount &&
    ("pct" in p ? p.pct : null) === t.pct &&
    ("base" in p ? p.base : null) === t.base
  );
}
