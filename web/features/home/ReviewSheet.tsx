"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { DecideControls } from "@/components/options/DecideControls";
import type { ApprovalDetail, ApprovalSummary } from "@/components/options/types";
import { useControls } from "@/components/shell/BotCard";
import { Sheet } from "@/components/ui/Sheet";
import { apiFetch } from "@/lib/api";
import type { CommandStatus } from "@/lib/commands";
import { ProposalBody, proposalTitle } from "./ProposalCard";

/** How often the open sheet asks the server whether the approval is still pending. */
export const DETAIL_POLL_MS = 5_000;

/**
 * Step 1 of the decide flow: the trade, its Why and its stub. Approve/Reject are the existing
 * DecideControls, so step 2 (ConfirmAction) and step 3 (the LIVE confirmation) and the receipt
 * are exactly the flows the options console already ships.
 */
export function ReviewSheet({
  approval,
  open,
  onClose,
  onSubmitted,
  onSettled,
}: {
  approval: ApprovalSummary | null;
  open: boolean;
  onClose: () => void;
  /** Passed to DecideControls: fired the instant Approve is confirmed (Trades moves the card to History's In flight). */
  onSubmitted?: (id: number, command: CommandStatus) => void;
  /** Passed to DecideControls: fired when that command fails or expires (the card goes back). */
  onSettled?: (id: number) => void;
}) {
  if (!approval) return null;
  return (
    <Sheet open={open} onClose={onClose} title="Review trade">
      <ReviewBody approval={approval} onSubmitted={onSubmitted} onSettled={onSettled} />
    </Sheet>
  );
}

/**
 * True once a command exists that this sheet's own DecideControls created. DecideControls reads
 * its command through useCommandStatus, a query keyed ["command", id], and the id is null until
 * a command exists; so the first non-null one to appear while the sheet is open is ours.
 */
function useSentFromHere(): boolean {
  const queryClient = useQueryClient();
  const [sent, setSent] = useState(false);
  useEffect(
    () =>
      queryClient.getQueryCache().subscribe((event) => {
        const key = event.query.queryKey;
        // Deferred: the cache announces a new query while DecideControls is still rendering.
        if (event.type === "added" && key[0] === "command" && key[1] != null) {
          queueMicrotask(() => setSent(true));
        }
      }),
    [queryClient],
  );
  return sent;
}

/** Mounted only while the sheet is open, so these queries run only then. */
function ReviewBody({
  approval,
  onSubmitted,
  onSettled,
}: {
  approval: ApprovalSummary;
  onSubmitted?: (id: number, command: CommandStatus) => void;
  onSettled?: (id: number) => void;
}) {
  const controls = useControls();
  const sentFromHere = useSentFromHere();
  // The sheet outlives its card: once the approval is decided it leaves the pending list and the
  // card unmounts, but the receipt must stay. The approval's own status is read from the same
  // key the detail page uses, which DecideControls invalidates when its command settles, so
  // Approve and Reject give way to the decision instead of coming back enabled. It is also
  // polled: a decision made in another tab or from Telegram, or an expiry, changes the server's
  // status with no command from here, and the sheet must stop offering a decision then. The
  // server's status is the only source; the client clock is never asked.
  const detail = useQuery({
    queryKey: ["options", "approval", String(approval.id)],
    queryFn: () => apiFetch<ApprovalDetail>(`/options/approvals/${approval.id}`),
    refetchInterval: (query) => (query.state.data && query.state.data.status !== "pending" ? false : DETAIL_POLL_MS),
  });
  const status = detail.data?.status ?? approval.status;
  const elsewhere = status !== "pending" && !sentFromHere;
  return (
    <>
      <h3 className="text-[1.0625rem] font-extrabold">{proposalTitle(approval)}</h3>
      <ProposalBody approval={approval} />
      {elsewhere && (
        <p role="status" className="mt-4 rounded-xl bg-flag px-3 py-2.5 text-[0.8125rem] font-semibold text-on-flag">
          {status === "expired" ? "This proposal has expired." : "This proposal was decided elsewhere."}
        </p>
      )}
      <div className="mt-5">
        {/* Once decided, DecideControls replaces Approve and Reject with "Decision: <status>". */}
        <DecideControls
          approval={{ ...approval, status }}
          drainHealthy={controls.data?.drain_healthy ?? true}
          onApprovalSubmitted={onSubmitted}
          onApprovalSettled={onSettled}
        />
      </div>
    </>
  );
}
