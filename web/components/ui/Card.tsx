import clsx from "clsx";
import type { HTMLAttributes } from "react";

type CardElement = "section" | "div" | "article" | "aside";

export function Card({
  as: Tag = "section",
  className,
  ...rest
}: HTMLAttributes<HTMLElement> & { as?: CardElement }) {
  // Tonal elevation: white on sage paper, no border, no shadow (DESIGN.md Elevation).
  return <Tag className={clsx("rounded-[18px] bg-surface px-4 py-4 sm:px-[18px]", className)} {...rest} />;
}
