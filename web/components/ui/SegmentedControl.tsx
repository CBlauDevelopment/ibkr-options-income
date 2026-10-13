import clsx from "clsx";

export type SegmentOption<T extends string> = {
  value: T;
  label: string;
  /** null/undefined hides the count; 0 is a real count and shows. */
  count?: number | null;
};

type Appearance = "track" | "chips" | "quiet";

const TRACK: Record<Appearance, string> = {
  track: "rounded-full bg-surface p-1",
  chips: "",
  quiet: "",
};

const BUTTON: Record<Appearance, string> = {
  track: "px-3.5 py-[7px] text-[0.84375rem]",
  chips: "px-[11px] py-1 text-xs",
  quiet: "px-[11px] py-1 text-xs",
};

const UNSELECTED: Record<Appearance, string> = {
  track: "text-muted hover:text-content",
  chips: "bg-sunk text-muted hover:text-content",
  quiet: "text-muted hover:text-content",
};

export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
  appearance = "track",
  className,
}: {
  label: string;
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  appearance?: Appearance;
  className?: string;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className={clsx("inline-flex max-w-full flex-wrap gap-1.5", TRACK[appearance], className)}
    >
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(o.value)}
            className={clsx(
              "rounded-full font-semibold",
              BUTTON[appearance],
              // Selected is an ink fill - never lime, never green - so it cannot read as "up".
              on ? "bg-content text-background" : UNSELECTED[appearance],
            )}
          >
            {o.label}
            {o.count !== null && o.count !== undefined && (
              <span className="ml-1 font-medium opacity-75"> {o.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
