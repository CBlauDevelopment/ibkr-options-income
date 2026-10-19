"use client";

import { useEffect } from "react";
import { savePersistedCommand, useCommandStatus, type CommandStatus } from "@/lib/commands";

/**
 * Follows one Approve this browser sent, whatever view is open, and renders nothing. The review
 * sheet's DecideControls polls its command only while the sheet is open, and History's sent card
 * only while History is mounted; once the sheet is closed on Proposals nothing else would notice a
 * command that ended failed or expired, and the proposal would stay hidden (and its persisted
 * entry would hide it again on the next visit) until History was opened.
 *
 * This shares DecideControls' query (["command", id]), so it adds no request while the sheet is
 * open. A terminal command clears the persisted entry; a failed or expired one also hands the card
 * back. A command still waiting on the LIVE confirmation is "pending", so it is left alone. Both
 * callbacks are idempotent: History's sent card may hand the same card back first.
 */
export function SubmittedWatcher({
  approvalId,
  commandId,
  onSettled,
}: {
  approvalId: number;
  commandId: number;
  onSettled: (approvalId: number) => void;
}) {
  const status: CommandStatus["status"] | undefined = useCommandStatus(commandId).data?.status;
  useEffect(() => {
    if (status === undefined || status === "pending") return;
    savePersistedCommand(approvalId, null);
    if (status === "failed" || status === "expired") onSettled(approvalId);
  }, [status, approvalId, onSettled]);
  return null;
}
