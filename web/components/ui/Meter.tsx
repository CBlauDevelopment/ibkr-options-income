import clsx from "clsx";
import { UNKNOWN } from "@/lib/format";

export function Meter({ value, max, label }: { value: number | null; max: number | null; label: string }) {
  const known = value !== null && max !== null && max > 0;
  const pct = known ? Math.max(0, Math.min(100, (value / max) * 100)) : null;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct === null ? undefined : Math.round(pct)}
      aria-valuetext={pct === null ? UNKNOWN : `${Math.round(pct)}%`}
      className={clsx("h-2 overflow-hidden rounded-full bg-sunk", pct === null && "hatch")}
    >
      {pct !== null && <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />}
    </div>
  );
}
