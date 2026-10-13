"use client";

import { X } from "lucide-react";
import { useId, useRef, type ReactNode } from "react";
import { useFocusTrap } from "@/lib/useFocusTrap";
import { Button } from "./Button";

/**
 * Bottom sheet on phones, right-side sheet from 640px. The only element besides the
 * confirm dialog allowed a shadow (DESIGN.md Elevation & Depth).
 */
export function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useFocusTrap(panelRef, open, onClose);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-stretch sm:justify-end">
      <div data-testid="sheet-scrim" aria-hidden="true" className="absolute inset-0 bg-scrim" onClick={onClose} />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="animate-sheet-in relative max-h-[92vh] w-full overflow-y-auto rounded-t-[24px] bg-surface p-6 shadow-[0_-8px_40px_rgba(0,0,0,0.18)] motion-reduce:animate-none sm:h-full sm:max-h-none sm:w-[440px] sm:rounded-none sm:rounded-l-[24px]"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 id={titleId} className="text-2xl font-extrabold tracking-[-0.015em]">
            {title}
          </h2>
          <Button variant="quiet" aria-label="Close" onClick={onClose} className="!min-h-9 !px-2">
            <X size={18} strokeWidth={2.25} />
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}
