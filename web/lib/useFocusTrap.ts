"use client";

import { useEffect, useRef, type RefObject } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Traps Tab inside `ref`, calls onEscape on Escape, focuses the first control on
 * activation and returns focus to the previous element on deactivation.
 *
 * Keys pressed inside a NESTED dialog (e.g. ConfirmAction opened from inside a sheet) are
 * left to that dialog: the listener is on the container itself and ignores any event whose
 * nearest [role="dialog"] is not this container.
 *
 * onEscape is read through a ref, so a parent that re-renders with a fresh inline callback
 * (Home polls) does not re-run the effect and pull focus back to the first control.
 */
export function useFocusTrap(
  ref: RefObject<HTMLElement | null>,
  active: boolean,
  onEscape: () => void,
): void {
  const onEscapeRef = useRef(onEscape);
  useEffect(() => {
    onEscapeRef.current = onEscape;
  });

  useEffect(() => {
    const el = ref.current;
    if (!active || !el) return;
    const previous = document.activeElement;
    el.querySelector<HTMLElement>(FOCUSABLE)?.focus();

    function onKeyDown(e: KeyboardEvent) {
      const target = e.target as Element | null;
      if (target?.closest('[role="dialog"]') !== el) return;
      if (e.key === "Escape") {
        e.stopPropagation();
        onEscapeRef.current();
        return;
      }
      if (e.key !== "Tab" || !el) return;
      const items = Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (n) => n.closest('[role="dialog"]') === el,
      );
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const current = document.activeElement;
      // Focus on the panel itself (after a click on prose) enters the loop at the near end.
      if (current === el) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
      } else if (e.shiftKey && current === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && current === last) {
        e.preventDefault();
        first.focus();
      }
    }

    el.addEventListener("keydown", onKeyDown);
    return () => {
      el.removeEventListener("keydown", onKeyDown);
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, [ref, active]);
}
