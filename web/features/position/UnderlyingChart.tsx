"use client";

import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  CrosshairMode,
  LineStyle,
  createChart,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { apiFetch } from "@/lib/api";
import { formatMoneyCell } from "@/lib/money";
import { RANGES, rangeChange, sliceBars, type RangeKey } from "./position";
import type { BarsResponse } from "./types";

function cssVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const MINUS = "−";
const DAY = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });

const asTime = (iso: string) => (Date.parse(`${iso}T00:00:00Z`) / 1000) as UTCTimestamp;

/**
 * The underlying's closing price as one ink line, with the position's own levels drawn across it
 * as dashed rules (a strike, a cost basis) and a marker on the day it was opened. Colours come
 * from the tokens at mount and again when the theme changes; the data never animates in.
 * The number above the chart follows the pointer; the canvas itself is invisible to a screen
 * reader, so a sentence stands in for it.
 */
export function UnderlyingChart({
  symbol,
  lines,
  openedOn,
  onLastClose,
}: {
  symbol: string;
  lines: { price: number; title: string }[];
  openedOn: string | null;
  onLastClose?: (close: number | null) => void;
}) {
  const [range, setRange] = useState<RangeKey>("3m");
  const [hover, setHover] = useState<{ time: string; value: number } | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  // The same request and key as the stock page's chart: one fetch when both have been opened.
  const { data, isError } = useQuery({
    queryKey: ["bars", symbol],
    queryFn: () => apiFetch<BarsResponse>(`/research/${symbol}/bars?range=1y`),
  });

  const months = RANGES.find((r) => r.value === range)!.months;
  const bars = useMemo(() => sliceBars(data?.bars ?? [], months), [data, months]);
  const lastClose = bars.length > 0 ? bars[bars.length - 1].close : null;
  const lineKey = lines.map((l) => `${l.price}:${l.title}`).join("|");

  useEffect(() => {
    onLastClose?.(lastClose);
  }, [lastClose, onLastClose]);

  useEffect(() => {
    const el = ref.current;
    if (!el || bars.length === 0) return;
    const chart: IChartApi = createChart(el, {
      autoSize: true,
      height: 240,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: cssVar("--text-muted"),
        fontFamily: "var(--font-sans), system-ui, sans-serif",
        // The licence link is the Credits card on More; the logo would sit on the line.
        attributionLogo: false,
      },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.12 } },
      timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
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
    series.setData(bars.map((b) => ({ time: asTime(b.time), value: b.close })));
    const priceLines = lines.map((l) =>
      series.createPriceLine({
        price: l.price,
        color: cssVar("--text-muted"),
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: l.title,
      }),
    );
    if (openedOn && openedOn >= bars[0].time && openedOn <= bars[bars.length - 1].time) {
      const near = bars.find((b) => b.time >= openedOn);
      if (near) {
        series.setMarkers([
          { time: asTime(near.time), position: "belowBar", color: cssVar("--chart-line"), shape: "arrowUp", text: "Sold" },
        ]);
      }
    }
    chart.timeScale().fitContent();
    chart.subscribeCrosshairMove((param: { time?: unknown; seriesData?: Map<unknown, unknown> }) => {
      const point = param.seriesData?.get(series) as { value?: number } | undefined;
      if (param.time === undefined || point?.value === undefined) setHover(null);
      else setHover({ time: new Date(Number(param.time) * 1000).toISOString().slice(0, 10), value: point.value });
    });

    const observer = new MutationObserver(() => {
      series.applyOptions({ color: cssVar("--chart-line") });
      chart.applyOptions({ layout: { textColor: cssVar("--text-muted") } });
      priceLines.forEach((pl) => pl.applyOptions({ color: cssVar("--text-muted") }));
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      observer.disconnect();
      chart.remove();
    };
    // `lines` is compared by value through lineKey: a new array with the same levels must not rebuild the chart.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bars, lineKey, openedOn]);

  const change = rangeChange(bars);
  const shown = hover?.value ?? lastClose;
  const first = bars[0];
  const rangeLabel = RANGES.find((r) => r.value === range)!.label;
  const flat = change === null || change.delta === 0;

  return (
    <section aria-label={`${symbol} price chart`}>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
        <span className="text-[0.8125rem] text-muted">{symbol} close</span>
        <span className="tabular text-[1.5rem] font-extrabold tracking-[-0.015em]">
          {shown === null ? "n/a" : formatMoneyCell(shown)}
        </span>
        <span className={clsx("tabular text-sm font-semibold", flat ? "text-muted" : change.delta < 0 ? "text-loss" : "text-gain")}>
          {hover
            ? DAY.format(new Date(`${hover.time}T00:00:00Z`))
            : change === null
              ? ""
              : `${change.delta < 0 ? MINUS : "+"}${formatMoneyCell(Math.abs(change.delta))} (${Math.abs(change.pct).toFixed(2)}%) over ${rangeLabel}`}
        </span>
      </div>
      {isError && !data ? (
        <p className="mt-4 text-sm text-muted">The price chart could not be loaded. It tries again when you reopen this page.</p>
      ) : !data ? (
        <div role="status" aria-busy="true" aria-label="Loading the price chart" className="mt-3 h-[240px] rounded-xl bg-sunk" />
      ) : bars.length === 0 ? (
        <p className="mt-4 text-sm text-muted">{`No price history for ${symbol} yet.`}</p>
      ) : (
        <div
          role="img"
          aria-label={`${symbol} closing price over ${rangeLabel}, from ${formatMoneyCell(first.close)} to ${formatMoneyCell(lastClose)}${lines.map((l) => `; ${l.title}`).join("")}`}
          className="mt-3"
        >
          <div ref={ref} className="h-[240px] w-full" aria-hidden="true" />
        </div>
      )}
      <div className="mt-2">
        <SegmentedControl label="Chart range" appearance="quiet" options={RANGES} value={range} onChange={setRange} />
      </div>
    </section>
  );
}
