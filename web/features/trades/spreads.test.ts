import { describe, expect, it } from "vitest";
import type { SpreadPosition } from "@/features/home/types";
import {
  bookRow,
  breakEven,
  codeWords,
  dayLabel,
  fallbackWords,
  itemDetail,
  itemOutcome,
  pickSentence,
  pickTitle,
  positionHref,
  timeET,
} from "./spreads";
import type { SpreadMenuItem, SpreadPick } from "./types";

const item = (over: Partial<SpreadMenuItem> = {}): SpreadMenuItem => ({
  letter: "B", position: "baseline", side: "put", short_strike: 762, long_strike: 757, width: 5,
  contracts: 21, credit_mid: 0.25, credit_after_costs: 0.144, max_loss_per_contract_usd: 475,
  short_delta: -0.14, spot: 767.29, dist_spot_pts: 5.29, dist_em_multiple: 1.49,
  be_nominal_exits: 0.9493, ...over,
});

const pick = (over: Partial<SpreadPick> = {}): SpreadPick => ({
  pick_id: 1, created_at: "2026-10-15T14:17:30Z", book_mode: "paper", choice: "B",
  reason: "B sits past the put wall.", fallback_reason: null, executed_letter: "B",
  send_rejected: false, send_reasons: [], filled: true, model: "claude-sonnet-5-5",
  regime: "negative", side: "put", plan_bias: null, event_flag: false, menu_readable: true,
  menu: [item({ letter: "A", position: "inside", short_strike: 763, long_strike: 758 }), item()],
  spread_id: "s1", ...over,
});

const position = (over: Partial<SpreadPosition> = {}): SpreadPosition => ({
  as_of: "", spread_id: "s1", mode: "paper", side: "put", expiry: "2026-10-15", short_strike: 762,
  long_strike: 757, width: 5, contracts_opened: 21, contracts: 21, entry_credit: 0.25,
  entry_commission: 27.3, opened_at: "2026-10-15T14:18:00Z", status: "open", exit_debit: null,
  exit_commission: null, exit_reason: null, closed_at: null, realized_pnl_usd: null, ...over,
});

describe("codeWords and fallbackWords", () => {
  it("turns a stored code into words", () => {
    expect(codeWords("stale_pick")).toBe("stale pick");
  });
  it("says what each known fallback means, and keeps an unknown code visible", () => {
    expect(fallbackWords("timeout")).toBe("Claude did not answer in time");
    expect(fallbackWords("off_menu")).toBe("Claude named a letter that was not on the menu");
    expect(fallbackWords("nonzero_exit")).toBe("the picker failed (nonzero exit)");
  });
});

describe("pickTitle", () => {
  it("names Claude's pick, a skip, and a pick that could not be used", () => {
    expect(pickTitle(pick(), "SPY")).toBe("SPY · Claude picked B");
    expect(pickTitle(pick({ choice: "skip", executed_letter: null }), "SPY")).toBe("SPY · Claude skipped");
    expect(pickTitle(pick({ choice: "skip", fallback_reason: "timeout" }), "SPY")).toBe("SPY · Claude's pick not used");
  });
});

describe("itemOutcome", () => {
  it("says Sent only for an item whose spread filled", () => {
    expect(itemOutcome(pick(), "B")).toEqual({ word: "Sent", why: null });
  });
  it("says a chosen item that did not trade did not trade, with the stored reasons in words", () => {
    const refused = pick({ filled: false, send_rejected: true, send_reasons: ["stale_pick", "entries_blocked"] });
    expect(itemOutcome(refused, "B")).toEqual({ word: "Chosen, did not trade", why: "stale pick, entries blocked" });
  });
  it("does not invent a reason when none was recorded", () => {
    expect(itemOutcome(pick({ filled: false, send_rejected: true, send_reasons: [] }), "B")).toEqual({
      word: "Chosen, did not trade",
      why: null,
    });
  });
  it("calls a chosen item with no result yet unrecorded, never Sent", () => {
    expect(itemOutcome(pick({ filled: false }), "B")).toEqual({ word: "Chosen, no result recorded yet", why: null });
  });
  it("marks nothing on a letter that was not the one chosen", () => {
    expect(itemOutcome(pick(), "A")).toBeNull();
    expect(itemOutcome(pick({ executed_letter: null, filled: false }), "B")).toBeNull();
  });
});

describe("pickSentence", () => {
  it("a filled pick says what was sent and that it filled", () => {
    expect(pickSentence(pick())).toBe("Sent B, the 762/757 put spread, 21 contracts. It filled.");
  });
  it("a pick that did not trade says why, in words", () => {
    expect(pickSentence(pick({ filled: false, send_rejected: true, send_reasons: ["stale_pick", "halted"] }))).toBe(
      "B did not trade: stale pick, halted.",
    );
    expect(pickSentence(pick({ filled: false, send_rejected: true, send_reasons: [] }))).toBe(
      "B did not trade: no reason recorded.",
    );
  });
  it("a skip says nothing was sent", () => {
    expect(pickSentence(pick({ choice: "skip", executed_letter: null, filled: false }))).toBe(
      "Claude chose not to trade this menu. Nothing was sent.",
    );
  });
  it("a fallback says why Claude's answer was not used and what was taken instead", () => {
    expect(pickSentence(pick({ choice: "skip", fallback_reason: "timeout" }))).toBe(
      "Claude did not answer in time, so the baseline pick B was taken. Sent B, the 762/757 put spread, 21 contracts. It filled.",
    );
    expect(
      pickSentence(pick({ choice: "skip", fallback_reason: "timeout", executed_letter: null, filled: false, send_rejected: true, send_reasons: ["no_baseline_item"] })),
    ).toBe("Claude did not answer in time, so there was no baseline pick to fall back on. Nothing was sent.");
  });
  it("a result the service has not recorded yet is said to be unrecorded, never guessed", () => {
    expect(pickSentence(pick({ filled: false }))).toBe("Sent B, the 762/757 put spread, 21 contracts. No result is recorded yet.");
  });
  it("an executed letter missing from an unreadable menu is named by its letter alone", () => {
    expect(pickSentence(pick({ menu: [], menu_readable: false }))).toBe("Sent B. It filled.");
  });
});

describe("menu figures", () => {
  it("describes an item's size and distance", () => {
    expect(itemDetail(item())).toBe("21 contracts · 5.29 pts from spot (1.49 expected moves) · $0.14 a share after costs");
    expect(itemDetail(item({ contracts: 1, dist_em_multiple: null }))).toBe("1 contract · 5.29 pts from spot · $0.14 a share after costs");
  });
  it("gives the break-even win rate, or null when it is unknown", () => {
    expect(breakEven(item())).toBe("break-even at 94.9% wins");
    expect(breakEven(item({ be_nominal_exits: null }))).toBeNull();
  });
});

describe("times and days", () => {
  it("shows a pick's time in New York", () => {
    expect(timeET("2026-10-15T14:17:30Z")).toBe("10:17 AM ET");
  });
  it("labels a day without shifting it", () => {
    expect(dayLabel("2026-10-15")).toBe("Thu, Oct 15");
  });
});

describe("the book's rows", () => {
  it("an open spread shows the credit taken, unsigned", () => {
    const r = bookRow(position(), "SPY");
    expect(r.title).toBe("SPY 762/757 put spread");
    expect(r.word).toBe("Open");
    expect(r.value).toBeCloseTo(525);
    expect(r.signed).toBe(false);
    expect(r.valueLabel).toBe("credit taken");
  });
  it("a closed spread shows its realised P&L, signed", () => {
    const r = bookRow(position({ status: "closed", realized_pnl_usd: -231.5 }), "SPY");
    expect(r.word).toBe("Closed");
    expect(r.value).toBe(-231.5);
    expect(r.signed).toBe(true);
    expect(r.valueLabel).toBe("realised");
  });
  it("links only the paper book, the one the position page reads", () => {
    expect(positionHref(position(), "SPY")).toBe("/positions/SPY/spread-s1");
    expect(positionHref(position({ mode: "baseline" }), "SPY")).toBeNull();
    expect(positionHref(position({ mode: "shadow" }), "SPY")).toBeNull();
  });
});
