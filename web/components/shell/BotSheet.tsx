"use client";

import { AutonomyControl } from "@/components/options/AutonomyControl";
import { HaltControl } from "@/components/options/HaltControl";
import type { ControlsResponse } from "@/components/options/types";
import { Sheet } from "@/components/ui/Sheet";

/** Halt is one tap, resume needs RESUME, rung changes confirm: all unchanged, only relocated. */
export function BotSheet({
  open,
  onClose,
  controls,
}: {
  open: boolean;
  onClose: () => void;
  controls: ControlsResponse;
}) {
  return (
    <Sheet open={open} onClose={onClose} title="Bot controls">
      <p className="text-sm text-muted">
        Mode: <span className="font-semibold text-content">{controls.mode}</span>
      </p>
      <div className="mt-4 grid gap-5">
        <HaltControl
          halted={controls.halted}
          haltReason={controls.halt_reason}
          haltedAt={controls.halted_at}
          drainHealthy={controls.drain_healthy}
        />
        <AutonomyControl autonomy={controls.autonomy} rungs={controls.rungs} drainHealthy={controls.drain_healthy} />
      </div>
    </Sheet>
  );
}
