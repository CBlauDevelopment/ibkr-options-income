"use client";

import { useCallback, useEffect, useState } from "react";
import { loadAllPersistedCommands, type CommandStatus } from "@/lib/commands";

export type SubmittedApprovals = {
  /** Approval id -> the Approve command in flight for it. */
  submitted: Map<number, CommandStatus>;
  markSubmitted: (id: number, command: CommandStatus) => void;
  clearSubmitted: (id: number) => void;
};

/**
 * Approvals whose Approve command is in flight. An approval's own status stays "pending" until
 * the trading service applies the command, so this client-side map is what moves a card from
 * Proposals to History's In flight the instant Approve is confirmed. Seeded from localStorage after mount
 * (never in a useState initializer, which runs during SSR and would break hydration), so a
 * reload mid-command keeps the card in flight.
 *
 * Both callbacks are stable: DecideControls lists onApprovalSettled in an effect's dependencies,
 * and a new function every render would re-run that effect on every render.
 */
export function useSubmittedApprovals(): SubmittedApprovals {
  const [submitted, setSubmitted] = useState<Map<number, CommandStatus>>(() => new Map());

  useEffect(() => {
    const persisted = loadAllPersistedCommands();
    if (persisted.size > 0) setSubmitted(persisted);
  }, []);

  const markSubmitted = useCallback(
    (id: number, command: CommandStatus) => setSubmitted((prev) => new Map(prev).set(id, command)),
    [],
  );
  const clearSubmitted = useCallback(
    (id: number) =>
      setSubmitted((prev) => {
        if (!prev.has(id)) return prev;
        const next = new Map(prev);
        next.delete(id);
        return next;
      }),
    [],
  );

  return { submitted, markSubmitted, clearSubmitted };
}
