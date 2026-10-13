"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV, activeKey } from "@/lib/nav";

export function TabBar() {
  const current = activeKey(usePathname());
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-border bg-surface px-1.5 pt-2 pb-[max(env(safe-area-inset-bottom),12px)] md:hidden"
    >
      {NAV.filter((n) => n.phone).map((item) => {
        const on = item.key === current;
        const Icon = item.icon;
        return (
          <Link
            key={item.key}
            href={item.href}
            aria-current={on ? "page" : undefined}
            className={clsx(
              "flex min-h-11 min-w-14 flex-col items-center justify-center gap-0.5 text-[11px]",
              on ? "font-bold text-content" : "text-muted",
            )}
          >
            <Icon aria-hidden="true" size={20} strokeWidth={on ? 2.4 : 2} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
