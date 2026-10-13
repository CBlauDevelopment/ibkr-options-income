"use client";

import clsx from "clsx";
import { useState } from "react";
import { UNKNOWN } from "@/lib/format";
import { formatMoneyCell } from "@/lib/money";

export type StubFormat = "money" | "signed-money" | "percent";

export type StubLineData = {
  label: string;
  value: number | null;
  format?: StubFormat;
  /** One sentence; when present the line becomes a button that reveals it. */
  explain?: string;
  /** The sum line: hairline above, bold. */
  total?: boolean;
};

const MINUS = "−";

export function formatStubValue(value: number | null, format: StubFormat = "money"): string {
  if (value === null || Number.isNaN(value)) return UNKNOWN;
  if (format === "percent") return `${value.toFixed(2)}%`;
  if (format === "signed-money") {
    if (value === 0) return "$0";
    return `${value > 0 ? "+" : MINUS}${formatMoneyCell(Math.abs(value))}`;
  }
  return formatMoneyCell(value);
}

function StubLine({ line }: { line: StubLineData }) {
  const [open, setOpen] = useState(false);
  const unknown = line.value === null || Number.isNaN(line.value);
  const row = (
    <>
      <span>{line.label}</span>
      <span className={clsx(unknown && "hatch text-unknown")}>{formatStubValue(line.value, line.format)}</span>
    </>
  );
  const rowClass = clsx(
    "flex w-full justify-between gap-2.5 text-left",
    line.total && "mt-1 border-t border-border pt-1.5 font-semibold",
  );
  if (!line.explain) return <div className={rowClass}>{row}</div>;
  return (
    <div>
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className={rowClass}>
        {row}
      </button>
      <p hidden={!open} className="pb-1 pt-0.5 font-sans text-xs text-muted">
        {line.explain}
      </p>
    </div>
  );
}

/** The payslip signature: a perforation, then a short line-by-line sum. */
export function Stub({ lines, label }: { lines: StubLineData[]; label: string }) {
  return (
    <div
      role="group"
      aria-label={label}
      className="tabular mt-3 grid gap-0.5 border-t-2 border-dashed border-perforation pt-2.5 font-mono text-[0.84375rem]"
    >
      {lines.map((l) => (
        <StubLine key={l.label} line={l} />
      ))}
    </div>
  );
}
