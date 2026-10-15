"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { ColorType, CrosshairMode, createChart, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import { chartPoints, pointLabel } from "./hero";
import type { AccountValuePoint } from "./types";

function cssVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

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
  // `index` is a row of `points` (what the hero figures read); `plotted` is what the chart
  // draws: one point per second, ascending, each remembering its row.
  const [index, setIndex] = useState<number | null>(null);
  const plotted = useMemo(() => chartPoints(points), [points]);

  useEffect(() => {
    const el = ref.current;
    if (!el || plotted.length === 0) return;
    const chart: IChartApi = createChart(el, {
      autoSize: true,
      height: 160,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: cssVar("--text-muted"),
        // The library's logo sat on the line's first points. Its licence asks for a link to
        // tradingview.com somewhere users can reach: the Credits card on More carries it.
        attributionLogo: false,
      },
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
    series.setData(plotted.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    chart.timeScale().fitContent();

    chart.subscribeCrosshairMove((param: { time?: unknown }) => {
      const hit = param.time === undefined ? undefined : plotted.find((p) => p.time === param.time);
      const next = hit ? hit.index : null;
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
  }, [plotted]);

  const last = plotted.length - 1;
  function move(next: number | null) {
    setIndex(next);
    onHoverRef.current(next);
  }
  // Position of the scrub among the plotted points; at rest it sits on the last one.
  const at = index === null ? last : Math.max(0, plotted.findIndex((p) => p.index === index));
  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "ArrowLeft") move(plotted[Math.max(0, at - 1)].index);
    else if (e.key === "ArrowRight") move(plotted[Math.min(last, at + 1)].index);
    else if (e.key === "Home") move(plotted[0].index);
    else if (e.key === "End" || e.key === "Escape") move(null);
    else return;
    e.preventDefault();
  }

  if (plotted.length === 0) return null;
  const shown = points[plotted[at].index];
  return (
    <div
      role="slider"
      tabIndex={0}
      aria-label="Account value history, use the arrow keys to move along it"
      aria-valuemin={0}
      aria-valuemax={last}
      aria-valuenow={at}
      aria-valuetext={shown ? pointLabel(shown) : undefined}
      onKeyDown={onKeyDown}
      onBlur={() => move(null)}
      className="mt-3 rounded-xl"
    >
      <div ref={ref} className="h-[160px] w-full" aria-hidden="true" />
    </div>
  );
}
