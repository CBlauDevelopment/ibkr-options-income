"use client";

import { UNKNOWN, relativeAge } from "@/lib/format";
import { RollDialogs, RollReceipt, hasRollReceipt, useRollProposal } from "./RollProposal";
import type { ShortPosition } from "./types";

/**
 * One open short option position's table row. The roll control's flow lives in RollProposal.tsx
 * (shared with the position page's Roll card); this file is only the row. Not mounted since web
 * overhaul Part 2 (the Shorts tab left Trades); kept, with ShortsTable, because
 * ShortsTable.test.tsx is the roll flow's full regression suite until Part 4 ports it.
 *
 * The control is labelled "Propose a roll", not "Roll": the button does not roll the position.
 */
export function ShortsRow({ short, drainHealthy = true }: { short: ShortPosition; drainHealthy?: boolean }) {
  const roll = useRollProposal(short.position_symbol);
  return (
    <>
      <tr key={short.position_symbol}>
        <td className="py-2">
          <div className="font-mono text-xs text-content">
            {short.underlying} {short.strike.toFixed(2)} {short.right}
          </div>
          <div className="text-xs text-muted">{short.position_symbol}</div>
        </td>
        <td className="py-2 tabular text-content">{short.dte != null ? short.dte : UNKNOWN}</td>
        <td className="py-2 tabular text-content">{short.contracts}</td>
        <td className="py-2 tabular">{short.mark != null ? `$${short.mark.toFixed(2)}` : UNKNOWN}</td>
        <td className="py-2 tabular">
          {short.unrealized_pnl != null ? `$${short.unrealized_pnl.toFixed(0)}` : UNKNOWN}
        </td>
        <td className="py-2 tabular text-xs">
          {short.delta != null ? (
            <span className="text-content">
              {short.delta.value != null ? short.delta.value.toFixed(2) : UNKNOWN}
              <span className="ml-1 text-muted">{short.delta.source}</span>
            </span>
          ) : (
            UNKNOWN
          )}
        </td>
        <td className="py-2 text-xs text-muted">
          {short.alerts.length > 0 ? (
            <ul className="space-y-0.5">
              {short.alerts.map((a) => (
                <li key={a.id}>
                  <span className="text-content">{a.trigger_label}</span>
                  <span className="text-muted"> {a.detail}</span>
                  <span className="text-muted"> {relativeAge(a.created_at)} ago</span>
                  {a.claude_recommendation && (
                    <span className="text-muted"> Model opinion (Claude): {a.claude_recommendation}</span>
                  )}
                </li>
              ))}
            </ul>
          ) : null}
        </td>
        <td className="py-2">
          <button
            type="button"
            disabled={roll.inFlight}
            onClick={roll.openConfirm}
            className="rounded-sm border border-border bg-background px-3 py-1.5 text-sm text-content enabled:hover:bg-elevated disabled:cursor-default disabled:opacity-50 focus-visible:ring-focus"
          >
            Propose a roll
          </button>
        </td>
      </tr>
      {hasRollReceipt(roll) && (
        <tr>
          <td colSpan={8} className="pb-3">
            <RollReceipt roll={roll} drainHealthy={drainHealthy} />
          </td>
        </tr>
      )}
      <RollDialogs roll={roll} contract={short} />
    </>
  );
}
