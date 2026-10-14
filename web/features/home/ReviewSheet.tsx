"use client";

import { useQuery } from "@tanstack/react-query";
import { DecideControls } from "@/components/options/DecideControls";
import type { ApprovalDetail, ApprovalSummary } from "@/components/options/types";
import { useControls } from "@/components/shell/BotCard";
import { Sheet } from "@/components/ui/Sheet";
import { apiFetch } from "@/lib/api";
import { ProposalBody, proposalTitle } from "./ProposalCard";

/**
 * Step 1 of the decide flow: the trade, its Why and its stub. Approve/Reject are the existing
 * DecideControls, so step 2 (ConfirmAction) and step 3 (the LIVE confirmation) and the receipt
 * are exactly the flows the options console already ships.
 */
export function ReviewSheet({
  approval,
  open,
  onClose,
}: {
  approval: ApprovalSummary | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!approval) return null;
  return (
    <Sheet open={open} onClose={onClose} title="Review trade">
      <ReviewBody approval={approval} />
    </Sheet>
  );
}

/** Mounted only while the sheet is open, so these two queries run only then. */
function ReviewBody({ approval }: { approval: ApprovalSummary }) {
  const controls = useControls();
  // The sheet outlives its card: once the approval is decided it leaves the pending list and the
  // card unmounts, but the receipt must stay. The approval's own status is read from the same
  // key the detail page uses, which DecideControls invalidates when its command settles, so
  // Approve and Reject give way to the decision instead of coming back enabled.
  const detail = useQuery({
    queryKey: ["options", "approval", String(approval.id)],
    queryFn: () => apiFetch<ApprovalDetail>(`/options/approvals/${approval.id}`),
  });
  const status = detail.data?.status ?? approval.status;
  return (
    <>
      <h3 className="text-[1.0625rem] font-extrabold">{proposalTitle(approval)}</h3>
      <ProposalBody approval={approval} />
      <div className="mt-5">
        <DecideControls approval={{ ...approval, status }} drainHealthy={controls.data?.drain_healthy ?? true} />
      </div>
    </>
  );
}
