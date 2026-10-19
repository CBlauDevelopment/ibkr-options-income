import { describe, expect, it } from "vitest";
import type { ApprovalSummary } from "@/components/options/types";
import { notTradedRows, orderContract } from "./history";

const a = (over: Partial<ApprovalSummary>): ApprovalSummary => ({
  as_of: "", id: 1, candidate_id: "c1", status: "expired", underlying: "AAPL", strategy: "cash_secured_put",
  right: "P", strike: 180, expiry: "2026-11-20", contracts: 1, premium: 2.35, blended_score: 70,
  created_at: "2026-10-15T15:00:00Z", expires_at: null, decided_at: null, order_state: null,
  source: "scan", review: null, rationale_tags: [], ...over,
});

describe("notTradedRows", () => {
  it("keeps what ended without a fill: expired, rejected, or an order cancelled or rejected", () => {
    const rows = notTradedRows(
      [
        a({ id: 1, status: "expired" }),
        a({ id: 2, status: "rejected", decided_by: "telegram" }),
        a({ id: 3, status: "approved", order_state: "cancelled", decided_by: "system" }),
        a({ id: 4, status: "approved", order_state: "rejected" }),
        a({ id: 5, status: "approved", order_state: "filled" }),
        a({ id: 6, status: "approved", order_state: "submitted" }),
        a({ id: 7, status: "pending" }),
        a({ id: 8, status: "approved", order_state: null }),
      ],
      "2026-10-15",
      "all",
    );
    expect(rows.map((r) => [r.id, r.word, r.decision])).toEqual([
      [1, "Expired", "Expired unanswered"],
      [2, "Rejected", "Rejected by you, in Telegram"],
      [3, "Order cancelled", "Approved by the system"],
      [4, "Order rejected", "Approved"],
    ]);
  });
  it("keeps only the New York day asked for", () => {
    const rows = notTradedRows(
      [
        a({ id: 1, created_at: "2026-10-16T02:00:00Z" }), // 22:00 on the 15th in New York
        a({ id: 2, created_at: "2026-10-15T03:00:00Z" }), // 23:00 on the 14th in New York
      ],
      "2026-10-15",
      "all",
    );
    expect(rows.map((r) => r.id)).toEqual([1]);
  });
  it("follows the strategy, a roll under the side it rolls", () => {
    const rows = notTradedRows(
      [a({ id: 1 }), a({ id: 2, strategy: "covered_call", right: "C" }), a({ id: 3, strategy: "roll", right: "C", source: "roll" })],
      "2026-10-15",
      "cc",
    );
    expect(rows.map((r) => r.id)).toEqual([2, 3]);
  });
  it("puts the newest first and keeps an unknown premium unknown", () => {
    const rows = notTradedRows(
      [a({ id: 1, created_at: "2026-10-15T14:00:00Z", premium: null }), a({ id: 2, created_at: "2026-10-15T16:00:00Z" })],
      "2026-10-15",
      "all",
    );
    expect(rows.map((r) => r.id)).toEqual([2, 1]);
    expect(rows[1].value).toBeNull();
    expect(rows[0].value).toBeCloseTo(235);
  });
});

describe("orderContract", () => {
  it("names the contract from the strategy, since an order carries no right", () => {
    expect(orderContract({ strategy: "cash_secured_put", strike: 190 })).toBe("$190 cash-secured put");
    expect(orderContract({ strategy: "roll", strike: 250 })).toBe("$250 roll");
  });
});
