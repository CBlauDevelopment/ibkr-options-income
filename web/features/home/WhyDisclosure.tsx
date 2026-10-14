import { Disclosure } from "@/components/ui/Disclosure";
import type { ClaudeReviewPayload } from "@/components/options/types";

/**
 * Claude's view, collapsed, labelled as Claude's. Renders nothing for an empty review.
 *
 * The panel is prose only: nothing focusable lives inside it, so a closed panel can never
 * hold the last focusable element of the review sheet's focus trap.
 */
export function WhyDisclosure({ review }: { review: ClaudeReviewPayload | null }) {
  if (!review) return null;
  const items = [
    { label: "In short", text: review.summary ?? "" },
    { label: "For", text: review.why_attractive },
    { label: "Against", text: review.risks },
    { label: "If challenged", text: review.rolling_considerations || review.assignment_considerations },
  ].filter((i) => i.text.trim() !== "");
  if (items.length === 0) return null;
  return (
    <div className="mt-3">
      <Disclosure
        summary={
          <span className="text-[0.8125rem] font-bold">
            Why this trade <span className="font-medium text-muted">· Claude's review</span>
          </span>
        }
      >
        <ul className="list-disc space-y-1 pl-[18px] text-[0.8125rem]">
          {items.map((i) => (
            <li key={i.label}>
              <span className="font-bold">{i.label}:</span> {i.text}
            </li>
          ))}
        </ul>
      </Disclosure>
    </div>
  );
}
