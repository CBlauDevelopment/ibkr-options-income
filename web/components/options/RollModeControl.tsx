"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";
import {
  loadPersistedCommand,
  savePersistedCommand,
  submitCommand,
  useCommandStatus,
  type CommandStatus,
} from "@/lib/commands";
import { ConfirmAction } from "./ConfirmAction";
import { CommandReceipt } from "./CommandReceipt";

// A singleton control (one per controls surface), so a fixed key is safe, as for
// AutonomyControl. Shares the `ibkr-options:command:` prefix (lib/commands.ts).
const STORAGE_KEY = "roll-mode";

type RollMode = "auto" | "propose";

const MODES: { value: RollMode; label: string }[] = [
  { value: "auto", label: "Auto-execute" },
  { value: "propose", label: "Propose only" },
];

/**
 * How a breach roll the policy has picked is handled (`set_roll_mode`).
 *
 * `auto`: the roll is approved and queued without a tap, when the autonomy rung allows it.
 * `propose`: it waits as a pending approval for an Approve tap. The Rules Engine gate, the
 * queue re-gate and the send-time check are identical either way; this only decides whether a
 * human taps first.
 *
 * Switching to `propose` is the conservative direction and applies at once, like Halt.
 * Switching to `auto` lets the system act without asking, so it is click-through confirmed
 * like an autonomy rung change. There is no live second confirmation: this intent cannot reach
 * an order by itself.
 */
export function RollModeControl({
  mode,
  drainHealthy = true,
}: {
  mode: RollMode;
  drainHealthy?: boolean;
}) {
  const [confirming, setConfirming] = useState(false);
  const [command, setCommand] = useState<CommandStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Restore an in-flight change after a reload; mount-only so it never clobbers a live one.
  useEffect(() => {
    const persisted = loadPersistedCommand(STORAGE_KEY);
    if (persisted) setCommand(persisted);
  }, []);

  const qc = useQueryClient();
  const commandQuery = useCommandStatus(command?.id ?? null);
  const current = (commandQuery.data ?? command) as CommandStatus | null;

  useEffect(() => {
    savePersistedCommand(STORAGE_KEY, current && current.status === "pending" ? current : null);
  }, [current]);

  useEffect(() => {
    if (current && current.status !== "pending") {
      qc.invalidateQueries({ queryKey: ["options", "controls"] });
    }
  }, [current, qc]);

  const inFlight = submitting || confirming || (current != null && current.status === "pending");

  async function apply(next: RollMode) {
    setError(null);
    setSubmitting(true);
    try {
      setCommand(await submitCommand("set_roll_mode", { mode: next }));
    } catch (e) {
      setError(describeError(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div data-testid="roll-mode-control">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted">Rolls</span>
        <select
          aria-label="Roll handling"
          value={mode}
          disabled={inFlight}
          onChange={(e) => {
            const next = e.target.value as RollMode;
            if (next === mode) return;
            if (next === "auto") setConfirming(true);
            else void apply(next);
          }}
          className="rounded-sm border border-border bg-background px-2 py-1 text-sm text-content focus-visible:ring-focus disabled:cursor-default disabled:opacity-50"
          data-testid="roll-mode-select"
        >
          {MODES.map((m) => (
            <option key={m.value} value={m.value} label={m.label} />
          ))}
        </select>
      </div>

      {error && (
        <p className="mt-2 text-xs text-loss" data-testid="command-error" role="alert">
          {error}
        </p>
      )}

      {current && <CommandReceipt command={current} order={null} drainHealthy={drainHealthy} />}

      {confirming && (
        <ConfirmAction
          title="Execute rolls automatically"
          summary={
            <span>
              When a short is breached and the roll policy finds a qualifying roll, the system
              will approve and send it without asking you first, on the Full rung (or for
              whitelisted names). Every roll still passes the Rules Engine and a fresh-quote
              check before it is sent. Choose Propose only to keep tapping Approve yourself.
            </span>
          }
          confirmLabel="Set Auto-execute"
          onConfirm={() => {
            setConfirming(false);
            void apply("auto");
          }}
          onCancel={() => setConfirming(false)}
        />
      )}
    </div>
  );
}

function describeError(e: unknown): string {
  if (e instanceof ApiError && e.status === 403) {
    return "You do not have permission to do this. Command not created.";
  }
  return "The command could not be created. Nothing was sent.";
}
