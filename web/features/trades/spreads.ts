import type { SpreadPosition } from "@/features/home/types";
import { dayLabel, timeET } from "./time";
import type { SpreadMenuItem, SpreadPick } from "./types";

// Shared with History; re-exported so this module's callers and tests keep one import.
export { dayLabel, timeET };

const FALLBACK: Record<string, string> = {
  timeout: "Claude did not answer in time",
  off_menu: "Claude named a letter that was not on the menu",
  unparseable: "Claude's answer could not be read",
  picker_error: "the picker failed",
};

/** A stored reason code in words: "stale_pick" becomes "stale pick". */
export function codeWords(code: string): string {
  return code.replace(/_/g, " ");
}

/** Why Claude's answer was not used. An unknown code stays visible rather than being guessed at. */
export function fallbackWords(code: string): string {
  return FALLBACK[code] ?? `the picker failed (${codeWords(code)})`;
}

const capitalise = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

export function itemLabel(i: { short_strike: number; long_strike: number; side: string }): string {
  return `${i.short_strike}/${i.long_strike} ${i.side}`;
}

export function itemDetail(i: SpreadMenuItem): string {
  const distance =
    `${i.dist_spot_pts.toFixed(2)} pts from spot` +
    (i.dist_em_multiple === null ? "" : ` (${i.dist_em_multiple.toFixed(2)} expected moves)`);
  return [plural(i.contracts, "contract"), distance, `$${i.credit_after_costs.toFixed(2)} a share after costs`].join(" · ");
}

/** The win rate the item needs to break even under the configured exits; null when unknown. */
export function breakEven(i: SpreadMenuItem): string | null {
  return i.be_nominal_exits === null ? null : `break-even at ${(i.be_nominal_exits * 100).toFixed(1)}% wins`;
}

export function pickTitle(p: SpreadPick, underlying: string): string {
  if (p.fallback_reason !== null) return `${underlying} · Claude's pick not used`;
  if (p.choice === "skip") return `${underlying} · Claude skipped`;
  return `${underlying} · Claude picked ${p.choice}`;
}

/**
 * What happened, from the stored flags only. A result the service has not recorded yet is said
 * to be unrecorded, never guessed as a fill or a refusal. `send_rejected` covers both a refusal
 * before sending and an order that did not fill, so it reads "did not trade".
 */
export function pickSentence(p: SpreadPick): string {
  const letter = p.executed_letter;
  let head = "";
  if (p.fallback_reason !== null) {
    head = `${capitalise(fallbackWords(p.fallback_reason))}, so ${
      letter === null ? "there was no baseline pick to fall back on" : `the baseline pick ${letter} was taken`
    }. `;
  } else if (p.choice === "skip") {
    head = "Claude chose not to trade this menu. ";
  }
  if (letter === null) return `${head}Nothing was sent.`;
  const item = p.menu.find((i) => i.letter === letter);
  const what = item ? `${letter}, the ${itemLabel(item)} spread, ${plural(item.contracts, "contract")}` : letter;
  if (p.filled) return `${head}Sent ${what}. It filled.`;
  if (p.send_rejected) {
    const why = p.send_reasons.length > 0 ? p.send_reasons.map(codeWords).join(", ") : "no reason recorded";
    return `${head}${letter} did not trade: ${why}.`;
  }
  return `${head}Sent ${what}. No result is recorded yet.`;
}

/**
 * What to say beside the menu item the service tried to send, from the stored flags only.
 * `executed_letter` is the item chosen for sending, set before anything is sent, so it is never
 * proof of an order: "Sent" is said only when the spread filled. A did-not-trade pick covers both
 * a refusal before sending (a stale pick, a halted day, the re-gate) and an order that went out and
 * did not fill, which the flags do not tell apart, so the words are true of both. Null for any
 * other letter.
 */
export function itemOutcome(p: SpreadPick, letter: string): { word: string; why: string | null } | null {
  if (p.executed_letter !== letter) return null;
  if (p.filled) return { word: "Sent", why: null };
  if (p.send_rejected) {
    return {
      word: "Chosen, did not trade",
      why: p.send_reasons.length > 0 ? p.send_reasons.map(codeWords).join(", ") : null,
    };
  }
  return { word: "Chosen, no result recorded yet", why: null };
}

/** The position page reads the running (paper) book only; shadow and baseline spreads have none. */
export function positionHref(p: SpreadPosition, underlying: string): string | null {
  return p.mode === "paper" ? `/positions/${encodeURIComponent(underlying)}/spread-${p.spread_id}` : null;
}

export const BOOK_LABEL: Record<string, string> = {
  paper: "Paper book",
  shadow: "Shadow book · simulated fills",
  baseline: "Baseline book · simulated, always the deterministic pick",
};

export type BookRow = {
  key: string;
  href: string | null;
  title: string;
  word: string;
  sub: string;
  value: number | null;
  signed: boolean;
  valueLabel: string;
};

export function bookRow(p: SpreadPosition, underlying: string): BookRow {
  const closed = p.status === "closed";
  return {
    key: p.spread_id,
    href: positionHref(p, underlying),
    title: `${underlying} ${itemLabel(p)} spread`,
    word: closed ? "Closed" : p.status === "expiring" ? "Expiring" : "Open",
    sub: `${plural(p.contracts_opened, "contract")} · credit $${p.entry_credit.toFixed(2)} a share · opened ${timeET(p.opened_at)}`,
    value: closed ? p.realized_pnl_usd : p.entry_credit * 100 * p.contracts_opened,
    signed: closed,
    valueLabel: closed ? "realised" : "credit taken",
  };
}
