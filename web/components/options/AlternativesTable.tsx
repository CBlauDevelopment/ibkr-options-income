import { UNKNOWN } from "@/lib/format";
import { StageBadge } from "./StageBadge";
import type { AlternativeStrike } from "./types";

const money = (v: number | null) =>
  v == null ? <span className="hatch text-unknown">{UNKNOWN}</span> : <span>${v.toFixed(2)}</span>;

export function AlternativesTable({ alternatives }: { alternatives: AlternativeStrike[] }) {
  if (alternatives.length === 0) return null;
  return (
    <div>
      <h2 className="text-[1.0625rem] font-bold">Other contracts assessed on this run</h2>
      <ul className="mt-1">
        {alternatives.map((a) => (
          <li key={a.candidate_id} className="flex items-center justify-between gap-3 border-t border-border py-2.5 text-sm first:border-t-0">
            <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-bold">${a.strike}</span>
              {a.expiry && <span className="text-muted">{a.expiry}</span>}
              {a.stage && <StageBadge stage={a.stage as never} />}
            </p>
            <p className="tabular text-right font-mono text-[0.8125rem]">
              <span className="text-muted">score </span>
              {a.blended_score != null ? a.blended_score.toFixed(1) : <span className="hatch text-unknown">{UNKNOWN}</span>}
              <span className="text-muted"> · premium </span>
              {money(a.premium)}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
