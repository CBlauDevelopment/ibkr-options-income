import clsx from "clsx";
import { forwardRef, type ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "quiet";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  block?: boolean;
};

const VARIANT: Record<ButtonVariant, string> = {
  // Lime means act: only the primary variant may carry it.
  primary: "bg-primary text-on-primary enabled:hover:bg-primary-deep",
  secondary: "bg-sunk text-content enabled:hover:bg-sunk-deep",
  quiet: "bg-transparent text-content enabled:hover:bg-sunk",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", block = false, className, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      data-variant={variant}
      className={clsx(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-[18px]",
        "text-[0.9375rem] font-bold transition-transform duration-[90ms] enabled:active:scale-[0.98]",
        "disabled:cursor-default disabled:bg-sunk disabled:text-muted",
        VARIANT[variant],
        block && "w-full",
        className,
      )}
      {...rest}
    />
  );
});
