"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ColorType, CrosshairMode, createChart, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import { pointLabel } from "./hero";
import type { AccountValuePoint } from "./types";

function cssVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const toTime = (iso: string) => Math.floor(Date.parse(iso) / 1000) as UTCTimestamp;

/**
 * One ink line, no grid, no axes: the hero number above is the label. Scrubbing reports the
 * hovered point's index; leaving reports null. Colours are read from tokens at mount and
 * again whenever <html data-theme> changes. Data never animates in (lightweight-charts draws
 * it in place).
 *
 * The canvas is invisible to a keyboard and a screen reader, so the wrapper is a slider:
 * arrow keys step through the points (Home = first point, End or Escape = back to the latest
 * value), and the hero number rewrites exactly as it does for a pointer.
 */
export function HeroChart({
  points,
  onHover,
}: {
  points: AccountValuePoint[];
  onHover: (index: number | null) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const onHoverRef = useRef(onHover);
  onHoverRef.current = onHover;
  const [index, setIndex] = useState<number | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const chart: IChartApi = createChart(el, {
      autoSize: true,
      height: 160,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: cssVar("--text-muted") },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      rightPriceScale: { visible: false },
      timeScale: { visible: false, borderVisible: false },
      crosshair: { mode: CrosshairMode.Magnet, horzLine: { visible: false, labelVisible: false } },
      handleScale: false,
      handleScroll: false,
    });
    const series = chart.addLineSeries({
      color: cssVar("--chart-line"),
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerRadius: 4,
    });
    const times = points.map((p) => toTime(p.at));
    series.setData(points.map((p, i) => ({ time: times[i], value: p.value })));
    chart.timeScale().fitContent();

    chart.subscribeCrosshairMove((param: { time?: unknown }) => {
      if (param.time === undefined) {
        setIndex(null);
        return onHoverRef.current(null);
      }
      const i = times.indexOf(param.time as UTCTimestamp);
      const next = i >= 0 ? i : null;
      setIndex(next);
      onHoverRef.current(next);
    });

    const observer = new MutationObserver(() => {
      series.applyOptions({ color: cssVar("--chart-line") });
      chart.applyOptions({ layout: { textColor: cssVar("--text-muted") } });
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [points]);

  const last = points.length - 1;
  function move(next: number | null) {
    setIndex(next);
    onHoverRef.current(next);
  }
  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const current = index ?? last;
    if (e.key === "ArrowLeft") move(Math.max(0, current - 1));
    else if (e.key === "ArrowRight") move(Math.min(last, current + 1));
    else if (e.key === "Home") move(0);
    else if (e.key === "End" || e.key === "Escape") move(null);
    else return;
    e.preventDefault();
  }

  const shown = index ?? last;
  return (
    <div
      role="slider"
      tabIndex={0}
      aria-label="Account value history, use the arrow keys to move along it"
      aria-valuemin={0}
      aria-valuemax={last}
      aria-valuenow={shown}
      aria-valuetext={points[shown] ? pointLabel(points[shown]) : undefined}
      onKeyDown={onKeyDown}
      onBlur={() => move(null)}
      className="mt-3 rounded-xl"
    >
      <div ref={ref} className="h-[160px] w-full" aria-hidden="true" />
    </div>
  );
}
