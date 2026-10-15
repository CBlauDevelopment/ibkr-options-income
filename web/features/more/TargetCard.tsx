"use client";

import clsx from "clsx";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useState, type ReactNode } from "react";
import { CommandReceipt } from "@/components/options/CommandReceipt";
import type { ControlsResponse } from "@/components/options/types";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { MonthPayResponse } from "@/features/home/types";
import { ApiError, apiFetch } from "@/lib/api";
import { submitCommand, useCommandStatus, type CommandStatus } from "@/lib/commands";
import {
  draftOf,
  payloadOf,
  previewSentence,
  sameTarget,
  type FieldName,
  type IncomeTarget,
  type TargetDraft,
  type TargetMode,
} from "./target";

type TargetResponse = { as_of: string; target: IncomeTarget; source: "web" | "config" | "none" };

const MODES: { value: TargetMode; label: string }[] = [
  { value: "off", label: "None" },
  { value: "fixed", label: "Fixed" },
  { value: "pct_of_account", label: "% of account" },
  { value: "pct_of_amount", label: "% of amount" },
];

const MONTH = new Intl.DateTimeFormat("en-US", { month: "long", timeZone: "UTC" });

function Field({
  label,
  value,
  onChange,
  error,
  prefix,
  suffix,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  prefix?: string;
  suffix?: string;
  disabled: boolean;
}) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div>
      <label htmlFor={id} className="block text-[0.8125rem] font-semibold">
        {label}
      </label>
      <div
        className={clsx(
          "mt-1 flex items-center gap-1.5 rounded-xl border bg-surface px-3",
          error ? "border-loss" : "border-control",
          // The field is the wrapper (prefix, input, suffix): its ring shows when the input has
          // keyboard focus, in ink like every focus ring here.
          "has-[input:focus-visible]:outline has-[input:focus-visible]:outline-2",
          "has-[input:focus-visible]:outline-offset-2 has-[input:focus-visible]:outline-focus",
        )}
      >
        {prefix && <span className="text-muted">{prefix}</span>}
        <input
          id={id}
          inputMode="decimal"
          autoComplete="off"
          value={value}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          onChange={(e) => onChange(e.target.value)}
          // 16px: below that, iOS zooms the page when the field takes focus.
          className="tabular min-h-11 w-full bg-transparent py-2 text-base outline-none disabled:text-muted"
        />
        {suffix && <span className="text-muted">{suffix}</span>}
      </div>
      {error && (
        <p id={errorId} role="alert" className="mt-1 text-[0.8125rem] text-loss">
          {error}
        </p>
      )}
    </div>
  );
}

function describeError(e: unknown): string {
  if (e instanceof ApiError && e.status === 403) return "You do not have permission to do this. Nothing was changed.";
  return "The target could not be saved. Nothing was changed.";
}

/**
 * The monthly income target behind Home's pay card (More). A fixed amount, a percent of the
 * account's value when the month began, or a percent of an amount the operator names. Saving
 * posts the drained `set_income_target` command and shows its receipt; the target is display
 * only, so there is no confirmation step and nothing here can reach an order.
 */
export function TargetCard() {
  const qc = useQueryClient();
  const target = useQuery({
    queryKey: ["pnl", "target"],
    queryFn: () => apiFetch<TargetResponse>("/pnl/target"),
  });
  // The pay card's own query: one request when both are on screen, and the month-start value
  // the "% of account" preview works from.
  const month = useQuery({
    queryKey: ["pnl", "month", "all"],
    queryFn: () => apiFetch<MonthPayResponse>("/pnl/month?strategy=all"),
  });
  const controls = useQuery({
    queryKey: ["options", "controls"],
    queryFn: () => apiFetch<ControlsResponse>("/options/controls"),
  });

  const [edited, setEdited] = useState<TargetDraft | null>(null);
  const [touched, setTouched] = useState(false);
  const [command, setCommand] = useState<CommandStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const stored = target.data?.target ?? null;
  const draft: TargetDraft = edited ?? (stored ? draftOf(stored) : { mode: "off", amount: "", pct: "", base: "" });

  const commandQuery = useCommandStatus(command?.id ?? null);
  const current = (commandQuery.data ?? command) as CommandStatus | null;
  const pending = submitting || (current !== null && current.status === "pending");

  // Once the change lands, show the server's truth again rather than the draft.
  useEffect(() => {
    if (current?.status === "applied") {
      void qc.invalidateQueries({ queryKey: ["pnl"] });
      setEdited(null);
      setTouched(false);
    }
  }, [current?.status, qc]);

  if (target.isError && !target.data) {
    return (
      <Card className="mt-4">
        <h2 className="text-[1.0625rem] font-bold">Monthly income target</h2>
        <p className="mt-1 text-sm text-muted">The current target could not be loaded. Try again in a moment.</p>
      </Card>
    );
  }
  if (!target.data) {
    return (
      <Card as="div" className="mt-4 h-[200px]" role="status" aria-busy="true" aria-label="Loading the income target" />
    );
  }

  const parsed = payloadOf(draft);
  const errors: Partial<Record<FieldName, string>> = touched && !parsed.ok ? parsed.errors : {};
  const monthName = month.data ? MONTH.format(new Date(month.data.pay.month)) : MONTH.format(new Date());
  const preview = previewSentence(draft, month.data?.pay.month_start_value ?? null, monthName);
  const unchanged = sameTarget(draft, target.data.target);

  const set = (patch: Partial<TargetDraft>) => {
    setEdited({ ...draft, ...patch });
    setTouched(false);
  };

  async function save() {
    setTouched(true);
    if (!parsed.ok) return;
    setError(null);
    setSubmitting(true);
    try {
      setCommand(await submitCommand("set_income_target", parsed.payload));
    } catch (e) {
      setError(describeError(e));
    } finally {
      setSubmitting(false);
    }
  }

  const source: ReactNode =
    target.data.source === "config"
      ? "Right now this comes from the config file (web.monthly_income_target_pct). Saving here replaces it."
      : target.data.source === "none"
        ? "No target is set yet."
        : null;

  return (
    <Card as="section" className="mt-4" aria-labelledby="target-title">
      <h2 id="target-title" className="text-[1.0625rem] font-bold">
        Monthly income target
      </h2>
      <p className="mt-1 text-sm text-muted">
        The goal the pay card on Home measures each month against. It changes nothing about trading.
      </p>
      {source && <p className="mt-1 text-[0.8125rem] text-muted">{source}</p>}

      <SegmentedControl
        label="Target type"
        appearance="chips"
        options={MODES}
        value={draft.mode}
        onChange={(mode) => set({ mode })}
        className="mt-3"
      />

      {draft.mode !== "off" && (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {draft.mode === "fixed" && (
            <Field
              label="Amount a month"
              prefix="$"
              value={draft.amount}
              onChange={(amount) => set({ amount })}
              error={errors.amount}
              disabled={pending}
            />
          )}
          {draft.mode !== "fixed" && (
            <Field
              label={draft.mode === "pct_of_account" ? "Percent of the account a month" : "Percent a month"}
              suffix="%"
              value={draft.pct}
              onChange={(pct) => set({ pct })}
              error={errors.pct}
              disabled={pending}
            />
          )}
          {draft.mode === "pct_of_amount" && (
            <Field
              label="Of this amount"
              prefix="$"
              value={draft.base}
              onChange={(base) => set({ base })}
              error={errors.base}
              disabled={pending}
            />
          )}
        </div>
      )}

      {preview && <p className="mt-3 text-sm">{preview}</p>}

      <div className="mt-3.5">
        <Button variant="primary" block disabled={pending || unchanged} onClick={save}>
          {pending ? "Saving…" : "Save target"}
        </Button>
      </div>

      {error && (
        <p role="alert" data-testid="command-error" className="mt-2 text-[0.8125rem] text-loss">
          {error}
        </p>
      )}
      {current && (
        <CommandReceipt command={current} order={null} drainHealthy={controls.data?.drain_healthy ?? true} />
      )}
    </Card>
  );
}
