// The frozen candidate's rationale tags, rendered as words rather than snake_case codes.
// `iv_rank_unavailable` is the one that matters most: the name has no IV history, so its
// IV component was scored neutral (`missing_iv_rank_score` in scoring_weights.yaml) rather
// than zero. The score is therefore partly a placeholder, and that is an unknown state -
// so it carries the hatch texture as well as the unknown colour, never colour alone.

const LABELS: Record<string, { text: string; unknown: boolean }> = {
  iv_rank_unavailable: {
    text: "IV rank unavailable - IV part of the score is a neutral placeholder",
    unknown: true,
  },
};

export function rationaleTagLabel(tag: string): string {
  return LABELS[tag]?.text ?? tag.replace(/_/g, " ");
}

export function RationaleTags({ tags }: { tags: string[] | undefined }) {
  if (!tags || tags.length === 0) return null;
  return (
    <ul className="flex flex-wrap gap-2 text-xs">
      {tags.map((tag) => {
        const unknown = LABELS[tag]?.unknown ?? false;
        return (
          <li
            key={tag}
            className={
              unknown
                ? "rounded-[6px] bg-sunk px-2 py-px text-xs font-semibold text-unknown"
                : "rounded-[6px] bg-sunk px-2 py-px text-xs font-semibold text-muted"
            }
          >
            {/* The texture is a mark beside the words, never over them: hatching the sentence drew
                same-coloured lines through every letter. */}
            {unknown && <span aria-hidden="true" className="hatch mr-1.5 inline-block h-2.5 w-5 rounded-[6px] align-middle" />}
            {rationaleTagLabel(tag)}
          </li>
        );
      })}
    </ul>
  );
}
