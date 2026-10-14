import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { apiFetchMock } from "@/lib/test-query";
import { NeedsYou } from "./NeedsYou";

/**
 * The real flow, nothing stubbed but the network: NeedsYou -> Review -> the sheet ->
 * DecideControls -> ConfirmAction (nested in the sheet) -> the command. These pin the
 * safety friction the plan promises: nothing is sent before the confirmation, the
 * confirmation owns its own keys inside the sheet, and the LIVE second step survives.
 */

const review = {
  why_attractive: "IV rank 62, premium 18% above fair value.",
  risks: "Earnings Oct 30 sits inside the window.",
  tradeoffs: "",
  assignment_considerations: "",
  rolling_considerations: "Roll down and out.",
  summary: "",
};

const approval = {
  as_of: "",
  id: 1,
  candidate_id: "c1",
  status: "pending",
  underlying: "AAPL",
  strategy: "cash_secured_put",
  right: "P",
  strike: 180,
  expiry: "2099-11-21",
  contracts: 2,
  premium: 2.35,
  blended_score: 0.7,
  created_at: "2026-10-13T13:00:00Z",
  expires_at: null,
  decided_at: null,
  order_state: null,
  source: "scan",
  review,
  rationale_tags: [],
};

const controls = {
  as_of: "",
  autonomy: { level: "approve", label: "Approve each trade" },
  rungs: [],
  halted: false,
  halt_reason: null,
  halted_at: null,
  mode: "paper",
  drain_healthy: true,
  drain_last_seen: null,
  pending_commands: 0,
};

const command = (over: Record<string, unknown> = {}) => ({
  id: 7,
  kind: "approve",
  status: "pending",
  result: null,
  needs_confirmation: false,
  confirm_token: null,
  created_at: "",
  applied_at: null,
  as_of: "",
  created: true,
  ...over,
});

type World = { live?: boolean; applyOnPoll?: boolean; kind?: string };

/** The set of requests a test saw: [path, method] for everything that is not a plain GET. */
function writes(): Array<[string, unknown]> {
  return apiFetchMock.mock.calls
    .filter((c) => (c[1] as RequestInit | undefined)?.method === "POST")
    .map((c) => [c[0] as string, JSON.parse(String((c[1] as RequestInit).body))]);
}

function mount(world: World = {}) {
  let settled = false;
  apiFetchMock.mockImplementation(async (path: string) => {
    if (path === "/options/approvals/1") return { ...approval, status: settled ? "approved" : "pending" };
    if (path.startsWith("/options/approvals")) return { as_of: "", approvals: settled ? [] : [approval] };
    if (path === "/options/controls") return controls;
    if (path === "/commands/7") {
      if (world.applyOnPoll) settled = true;
      return command({ kind: world.kind ?? "approve", status: world.applyOnPoll ? "applied" : "pending" });
    }
    if (path === "/commands/7/confirm") return {};
    if (path === "/commands") {
      return command({
        kind: world.kind ?? "approve",
        needs_confirmation: Boolean(world.live),
        confirm_token: world.live ? "tok-1" : null,
      });
    }
    throw new Error(`no mocked response for ${path}`);
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <NeedsYou strategy="all" />
    </QueryClientProvider>,
  );
}

async function openSheet() {
  const card = await screen.findByRole("article", { name: "AAPL · Sell $180 put" });
  const trigger = within(card).getByRole("button", { name: "Review" });
  trigger.focus();
  fireEvent.click(trigger);
  return { trigger, sheet: screen.getByRole("dialog", { name: "Review trade" }) };
}

function openConfirm(sheet: HTMLElement, name: "Approve" | "Reject") {
  const trigger = within(sheet).getByRole("button", { name });
  trigger.focus(); // a real click focuses its button; fireEvent.click alone does not
  fireEvent.click(trigger);
  return within(sheet).getByRole("dialog", { name: `${name} this contract` });
}

beforeEach(() => {
  // calls from the previous test must not count as writes in this one
  (apiFetchMock as unknown as { mockClear: () => void }).mockClear();
});

describe("the review sheet, with the real decide flow inside it", () => {
  it("shows the trade, Claude's review and the stub, then Approve and Reject", async () => {
    mount();
    const { sheet } = await openSheet();
    expect(within(sheet).getByRole("heading", { name: "AAPL · Sell $180 put" })).toBeInTheDocument();
    expect(within(sheet).getByRole("button", { name: /Why this trade/ })).toHaveAttribute("aria-expanded", "false");
    expect(within(sheet).getByRole("group", { name: "AAPL put math" })).toBeInTheDocument();
    expect(within(sheet).getByRole("button", { name: "Approve" })).toBeEnabled();
    expect(within(sheet).getByRole("button", { name: "Reject" })).toBeEnabled();
  });

  it("sends nothing until the confirmation, which names the exact contract and count", async () => {
    mount();
    const { sheet } = await openSheet();
    const confirm = openConfirm(sheet, "Approve");
    expect(within(confirm).getByTestId("confirm-summary")).toHaveTextContent(
      "Approve exactly 2 contracts of AAPL 180.00 P",
    );
    expect(writes()).toEqual([]);
  });

  it("Escape inside the confirmation cancels only the confirmation: the sheet stays and nothing is sent", async () => {
    mount();
    const { sheet } = await openSheet();
    const confirm = openConfirm(sheet, "Approve");
    fireEvent.keyDown(within(confirm).getByRole("button", { name: "Cancel" }), { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Approve this contract" })).toBeNull();
    expect(screen.getByRole("dialog", { name: "Review trade" })).toBeInTheDocument();
    expect(document.activeElement).toBe(within(sheet).getByRole("button", { name: "Approve" }));
    expect(writes()).toEqual([]);
  });

  it("Tab inside the confirmation wraps within it and never leaves for the sheet behind", async () => {
    mount();
    const { sheet } = await openSheet();
    const confirm = openConfirm(sheet, "Approve");
    const cancel = within(confirm).getByRole("button", { name: "Cancel" });
    const go = within(confirm).getByRole("button", { name: "Approve" });
    expect(document.activeElement).toBe(cancel);
    go.focus();
    fireEvent.keyDown(go, { key: "Tab" });
    expect(document.activeElement).toBe(cancel);
    fireEvent.keyDown(cancel, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(go);
    expect(confirm.contains(document.activeElement)).toBe(true);
    expect(screen.getByRole("dialog", { name: "Review trade" })).toBeInTheDocument();
  });

  it("confirming sends one approve intent for this approval and keeps the receipt in the sheet", async () => {
    mount();
    const { sheet } = await openSheet();
    const confirm = openConfirm(sheet, "Approve");
    fireEvent.click(within(confirm).getByRole("button", { name: "Approve" }));
    expect(await within(sheet).findByTestId("command-receipt")).toBeInTheDocument();
    expect(writes()).toEqual([["/commands", { kind: "approve", payload: { approval_id: 1 } }]]);
    expect(within(sheet).getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(within(sheet).getByRole("button", { name: "Reject" })).toBeDisabled();
  });

  it("Reject goes through the same confirmation", async () => {
    mount({ kind: "reject" });
    const { sheet } = await openSheet();
    const confirm = openConfirm(sheet, "Reject");
    expect(writes()).toEqual([]);
    fireEvent.click(within(confirm).getByRole("button", { name: "Reject" }));
    await within(sheet).findByTestId("command-receipt");
    expect(writes()).toEqual([["/commands", { kind: "reject", payload: { approval_id: 1 } }]]);
  });

  it("once the approval is applied the sheet shows the decision and the buttons are gone", async () => {
    mount({ applyOnPoll: true });
    const { sheet } = await openSheet();
    const confirm = openConfirm(sheet, "Approve");
    fireEvent.click(within(confirm).getByRole("button", { name: "Approve" }));
    // The card has left the pending list by now; the sheet keeps the outcome.
    expect(await within(sheet).findByTestId("approval-decision")).toHaveTextContent("Decision: approved");
    expect(within(sheet).queryByRole("button", { name: "Approve" })).toBeNull();
    expect(within(sheet).queryByRole("button", { name: "Reject" })).toBeNull();
    expect(within(sheet).getByTestId("command-receipt")).toBeInTheDocument();
  });

  it("in live mode the second confirmation still appears, inside the sheet, and Escape leaves the intent unreleased", async () => {
    mount({ live: true });
    const { sheet } = await openSheet();
    const confirm = openConfirm(sheet, "Approve");
    fireEvent.click(within(confirm).getByRole("button", { name: "Approve" }));
    const live = await within(sheet).findByRole("dialog", { name: "Confirm LIVE approve" });
    fireEvent.keyDown(within(live).getByRole("button", { name: "Cancel" }), { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Confirm LIVE approve" })).toBeNull();
    expect(screen.getByRole("dialog", { name: "Review trade" })).toBeInTheDocument();
    expect(writes()).toEqual([["/commands", { kind: "approve", payload: { approval_id: 1 } }]]);
  });

  it("releasing the live intent sends the confirm token once", async () => {
    mount({ live: true });
    const { sheet } = await openSheet();
    const confirm = openConfirm(sheet, "Approve");
    fireEvent.click(within(confirm).getByRole("button", { name: "Approve" }));
    const live = await within(sheet).findByRole("dialog", { name: "Confirm LIVE approve" });
    fireEvent.click(within(live).getByRole("button", { name: "Release approve intent" }));
    await within(sheet).findByTestId("command-receipt");
    expect(writes().filter(([path]) => path === "/commands/7/confirm")).toEqual([
      ["/commands/7/confirm", { confirm_token: "tok-1" }],
    ]);
  });
});

describe("the sheet's own keys", () => {
  it("puts focus on the first control, Escape closes it and focus returns to Review", async () => {
    mount();
    const { trigger, sheet } = await openSheet();
    expect(document.activeElement).toBe(within(sheet).getByRole("button", { name: "Close" }));
    fireEvent.keyDown(within(sheet).getByRole("button", { name: "Close" }), { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Review trade" })).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it("Tab from the last control wraps to Close and Shift+Tab from Close wraps to the last, with Why closed", async () => {
    mount();
    const { sheet } = await openSheet();
    // Nothing focusable hides inside a closed disclosure panel, so the last control is Reject.
    const close = within(sheet).getByRole("button", { name: "Close" });
    const reject = within(sheet).getByRole("button", { name: "Reject" });
    reject.focus();
    fireEvent.keyDown(reject, { key: "Tab" });
    expect(document.activeElement).toBe(close);
    fireEvent.keyDown(close, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(reject);
    const hidden = sheet.querySelectorAll("[hidden] a[href], [hidden] button, [hidden] input, [hidden] [tabindex]");
    expect(hidden).toHaveLength(0);
  });

  it("reopens Why inside the sheet without breaking the wrap", async () => {
    mount();
    const { sheet } = await openSheet();
    fireEvent.click(within(sheet).getByRole("button", { name: /Why this trade/ }));
    expect(within(sheet).getByText("IV rank 62, premium 18% above fair value.")).toBeVisible();
    const reject = within(sheet).getByRole("button", { name: "Reject" });
    reject.focus();
    fireEvent.keyDown(reject, { key: "Tab" });
    expect(document.activeElement).toBe(within(sheet).getByRole("button", { name: "Close" }));
  });
});
