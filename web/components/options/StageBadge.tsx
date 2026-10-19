import { StatusWord } from "@/components/ui/StatusWord";

type Stage = "generator" | "risk_gate" | "score_floor" | "dedupe" | "top_n" | "passed";

export const STAGE_LABEL: Record<Stage, string> = {
  generator: "Filtered",
  risk_gate: "Gate rejected",
  score_floor: "Below score floor",
  dedupe: "Lost dedupe",
  top_n: "Capped out",
  passed: "Passed",
};

// A word on every stage, never colour alone; the flag fill only where the Rules Engine said no.
export function StageBadge({ stage }: { stage: Stage }) {
  return <StatusWord tone={stage === "risk_gate" ? "flag" : "neutral"}>{STAGE_LABEL[stage] ?? stage}</StatusWord>;
}
