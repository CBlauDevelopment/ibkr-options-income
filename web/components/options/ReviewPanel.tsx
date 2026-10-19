import type { ClaudeReviewPayload } from "./types";

// The five review fields render as five labelled entries, never one paragraph, so the bull case,
// the risk case and the mechanical notes read as distinct ideas. A null review, or one with every
// field empty, renders nothing at all. The plain-English `summary` leads, as the verdict, and the
// `evidence` ids it cites follow.

type Section = { label: string; tag: string; text: string };

function sectionsOf(review: ClaudeReviewPayload): Section[] {
  return [
    { label: "Why attractive", tag: "Bull case", text: review.why_attractive },
    { label: "Risks", tag: "Bear case", text: review.risks },
    { label: "Tradeoffs", tag: "Balance", text: review.tradeoffs },
    { label: "Assignment considerations", tag: "Watch for", text: review.assignment_considerations },
    { label: "Rolling considerations", tag: "If challenged", text: review.rolling_considerations },
  ].filter((s) => s.text);
}

/** Whether ReviewPanel would render anything, so a caller can leave out the card around it. */
export function hasReviewContent(review: ClaudeReviewPayload | null): boolean {
  return review !== null && (sectionsOf(review).length > 0 || Boolean(review.summary));
}

export function ReviewPanel({ review }: { review: ClaudeReviewPayload | null }) {
  if (!review || !hasReviewContent(review)) return null;
  const present = sectionsOf(review);
  const summary = review.summary ?? "";
  const evidence = review.evidence ?? [];
  return (
    <div className="space-y-3">
      {summary && (
        <div className="rounded-xl bg-sunk px-3 py-2.5">
          <p className="text-xs font-semibold tracking-[0.04em] text-muted">
            {review.recommendation ? `Verdict: ${review.recommendation}` : "Verdict"}
          </p>
          <p className="mt-0.5 text-sm font-bold">Summary</p>
          <p className="mt-1 text-sm">{summary}</p>
        </div>
      )}
      {present.length > 0 && (
        <dl className="grid gap-x-6 sm:grid-cols-2">
          {present.map((s) => (
            <div key={s.label} className="border-t border-border py-2.5">
              <dt>
                <span className="block text-xs font-semibold tracking-[0.04em] text-muted">{s.tag}</span>
                <span className="text-sm font-bold">{s.label}</span>
              </dt>
              <dd className="mt-1 text-sm">{s.text}</dd>
            </div>
          ))}
        </dl>
      )}
      {evidence.length > 0 && <EvidenceList ids={evidence} />}
    </div>
  );
}

// The ids the verdict cites. The FACTS and NEWS blocks they point into live only in that scan's
// prompt, not in the stored review, so each id is shown with what kind of source it is rather
// than pretending to link to text the console does not have.
function EvidenceList({ ids }: { ids: string[] }) {
  return (
    <div className="text-xs text-muted">
      <span>Cited: </span>
      <ul className="inline-flex flex-wrap gap-2 align-middle">
        {ids.map((id) => (
          <li key={id} className="rounded-[6px] bg-sunk px-1.5 py-0.5">
            <span className="font-mono text-content">{id}</span> <span>{evidenceKind(id)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function evidenceKind(id: string): string {
  if (/^F\d+$/.test(id)) return "computed fact";
  if (/^N\d+$/.test(id)) return "news headline";
  return "source";
}
