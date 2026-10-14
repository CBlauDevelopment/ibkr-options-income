"use client";

import { X } from "lucide-react";
import { useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useFocusTrap } from "@/lib/useFocusTrap";
import { Button } from "./Button";

/**
 * Bottom sheet on phones, right-side sheet from 640px. The only element besides the
 * confirm dialog allowed a shadow (DESIGN.md Elevation & Depth).
 *
 * Portaled to <body>: Home opens the review sheet from a column hidden below 1024px and the bot
 * sheet from the rail, hidden below 768px, so a sheet rendered in place (and any confirmation
 * inside it) would vanish, still mounted and still holding focus, when the window crosses the
 * breakpoint. React events still bubble through the component tree, not the DOM tree.
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
  if (!open || typeof document === "undefined") return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-stretch sm:justify-end">
      <div data-testid="sheet-scrim" aria-hidden="true" className="absolute inset-0 bg-scrim" onClick={onClose} />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        // Focusable (but not tabbable) so a click on non-focusable prose lands focus on the
        // panel rather than <body>, where Escape and the Tab trap would never hear it.
        tabIndex={-1}
        className="animate-sheet-in relative outline-none max-h-[92vh] w-full overflow-y-auto rounded-t-[24px] bg-surface p-6 shadow-sheet motion-reduce:animate-none sm:h-full sm:max-h-none sm:w-[440px] sm:rounded-none sm:rounded-l-[24px]"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 id={titleId} className="text-2xl font-extrabold tracking-[-0.015em]">
            {title}
          </h2>
          <Button variant="quiet" aria-label="Close" onClick={onClose} className="w-11 !px-0">
            <X size={18} strokeWidth={2.25} />
          </Button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}
