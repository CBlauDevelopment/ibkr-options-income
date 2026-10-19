"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";
import {
  confirmCommand,
  loadPersistedCommand,
  savePersistedCommand,
  submitCommand,
  useCommandStatus,
  type CommandStatus,
} from "@/lib/commands";
import { CommandReceipt } from "./CommandReceipt";
import { ConfirmAction } from "./ConfirmAction";

/**
 * The roll-proposal flow (P2 M5 Task 5.2), lifted out of ShortsRow unchanged so the Shorts table
 * and the position page's Roll card run one state machine: a `confirming` state gates a
 * ConfirmAction before any request, `roll_request` fires once on confirm, a live-mode response
 * routes through a second LIVE confirmation, and the result is polled until terminal. The
 * in-flight command persists under `short:{position_symbol}` (lib/commands.ts), namespaced so it
 * never collides with an approval id or a `promote:` entry.
 */
export type RollProposal = {
  confirming: boolean;
  openConfirm: () => void;
  cancelConfirm: () => void;
  onConfirm: () => Promise<void>;
  liveStep: CommandStatus | null;
  onLiveConfirm: () => Promise<void>;
  cancelLive: () => void;
  current: CommandStatus | null;
  error: string | null;
  /** True while a request is out, the live confirmation is open, or the command is pending. */
  inFlight: boolean;
  /** The failed command's reason code, when it failed. */
  reason: string | undefined;
  successApprovalId: number | null;
  workingApprovalId: number | null;
};

export function useRollProposal(positionSymbol: string): RollProposal {
  const storageKey = `short:${positionSymbol}`;

  const [confirming, setConfirming] = useState(false);
  const [command, setCommand] = useState<CommandStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [liveStep, setLiveStep] = useState<CommandStatus | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Restore an in-flight roll proposal (including one awaiting the live second confirmation)
  // after a page reload. Mount-only, so it never clobbers a command this flow is progressing.
  useEffect(() => {
    const persisted = loadPersistedCommand(storageKey);
    if (!persisted) return;
    if (persisted.needs_confirmation) setLiveStep(persisted);
    else setCommand(persisted);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const qc = useQueryClient();

  // Poll every 2s while pending; stop once terminal (lib/commands.ts).
  const commandQuery = useCommandStatus(command?.id ?? null);
  const current = (commandQuery.data ?? command) as CommandStatus | null;

  // Mirror the in-flight command to localStorage.
  useEffect(() => {
    if (liveStep) {
      savePersistedCommand(storageKey, liveStep);
    } else if (current && current.status === "pending") {
      savePersistedCommand(storageKey, current);
    } else {
      savePersistedCommand(storageKey, null);
    }
  }, [storageKey, liveStep, current]);

  useEffect(() => {
    if (current && current.status !== "pending") {
      // A roll proposal raises an approval: refresh the approvals so the new card appears.
      qc.invalidateQueries({ queryKey: ["options", "approvals"] });
    }
  }, [current, qc]);

  // liveStep counts as in flight too: there is no command id to poll until the live
  // confirmation is released, so `current` alone would leave the button clickable meanwhile.
  const inFlight = submitting || liveStep != null || (current != null && current.status === "pending");

  async function onConfirm() {
    setConfirming(false);
    setError(null);
    setSubmitting(true);
    try {
      const resp = await submitCommand("roll_request", { position_symbol: positionSymbol });
      if (resp.needs_confirmation && resp.confirm_token) setLiveStep(resp);
      else setCommand(resp);
    } catch (e) {
      setError(describeError(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function onLiveConfirm() {
    const cmd = liveStep;
    setLiveStep(null);
    if (cmd === null) return;
    setSubmitting(true);
    try {
      await confirmCommand(cmd.id, cmd.confirm_token ?? "");
      setCommand({ ...cmd, needs_confirmation: false, confirm_token: null });
    } catch (e) {
      setError(describeError(e));
    } finally {
      setSubmitting(false);
    }
  }

  function cancelLive() {
    setCommand(liveStep);
    setLiveStep(null);
  }

  const result = current?.result as
    | { reason?: string; approval_id?: number | null; detail?: { approval_id?: number | null } }
    | null;
  const reason = current?.status === "failed" ? result?.reason : undefined;
  const successApprovalId = current?.status === "applied" ? (result?.approval_id ?? null) : null;
  const workingApprovalId = reason === "roll_already_working" ? (result?.detail?.approval_id ?? null) : null;

  return {
    confirming,
    openConfirm: () => setConfirming(true),
    cancelConfirm: () => setConfirming(false),
    onConfirm,
    liveStep,
    onLiveConfirm,
    cancelLive,
    current,
    error,
    inFlight,
    reason,
    successApprovalId,
    workingApprovalId,
  };
}

/** Whether there is anything for RollReceipt to show. */
export function hasRollReceipt(roll: RollProposal): boolean {
  return roll.current != null || roll.error != null || roll.workingApprovalId != null || roll.successApprovalId != null;
}

/**
 * The roll's receipt. `no_qualifying_roll` is a plain answer, not red failed chrome;
 * `roll_already_working` links to the approval already in flight; success links to the new one.
 */
export function RollReceipt({ roll, drainHealthy }: { roll: RollProposal; drainHealthy: boolean }) {
  if (!hasRollReceipt(roll)) return null;
  const { current, error, reason, workingApprovalId, successApprovalId } = roll;
  return (
    <div className="mt-3">
      {error && (
        <p className="text-[0.8125rem] text-loss" data-testid="command-error" role="alert">
          {error}
        </p>
      )}
      {current && reason === "no_qualifying_roll" ? (
        <div data-testid="command-receipt" data-state="answered" className="mt-2 rounded-xl bg-sunk px-3 py-2.5 text-[0.8125rem]">
          <p className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-semibold">No qualifying roll</span>
            <span className="text-muted">
              No roll on the current chain clears the roll&apos;s own bounds. That is a real answer, not an error.
            </span>
            <span className="ml-auto font-mono text-muted">intent {current.id}</span>
          </p>
        </div>
      ) : current ? (
        <CommandReceipt command={current} order={null} drainHealthy={drainHealthy} />
      ) : null}
      {workingApprovalId != null && (
        <p className="mt-1 text-[0.8125rem]">
          <Link href={`/trades/${workingApprovalId}`} className="font-semibold underline underline-offset-2">
            View the roll already in flight
          </Link>
        </p>
      )}
      {successApprovalId != null && (
        <p className="mt-1 text-[0.8125rem]">
          <Link href={`/trades/${successApprovalId}`} className="font-semibold underline underline-offset-2">
            View approval
          </Link>
        </p>
      )}
    </div>
  );
}

/** The two confirmations: the proposal itself, then (live mode only) the LIVE release. */
export function RollDialogs({
  roll,
  contract,
}: {
  roll: RollProposal;
  contract: { underlying: string; strike: number; right: string };
}) {
  return (
    <>
      {roll.liveStep && (
        <ConfirmAction
          title={`Confirm LIVE ${roll.liveStep.kind}`}
          summary={
            <span>
              This is the second, mandatory confirmation for live trading. The first confirmation queued the intent;
              releasing it now lets the trading service apply it. The execution-time [CONFIRM LIVE] Telegram step
              still fires afterwards.
            </span>
          }
          confirmLabel={`Release ${roll.liveStep.kind} intent`}
          onConfirm={roll.onLiveConfirm}
          onCancel={roll.cancelLive}
        />
      )}
      {roll.confirming && (
        <ConfirmAction
          title="Propose a roll"
          summary={
            <span>
              The system will price a roll for {contract.underlying} {contract.strike.toFixed(2)} {contract.right} and raise
              it as a pending approval. Nothing executes until you approve that proposal. The roll&apos;s own debit and
              delta-reduction bounds decide whether one qualifies.
            </span>
          }
          confirmLabel="Propose a roll"
          onConfirm={roll.onConfirm}
          onCancel={roll.cancelConfirm}
        />
      )}
    </>
  );
}

function describeError(e: unknown): string {
  if (e instanceof ApiError && e.status === 403) {
    return "You do not have permission to do this. Command not created.";
  }
  return "The command could not be created. Nothing was sent.";
}
