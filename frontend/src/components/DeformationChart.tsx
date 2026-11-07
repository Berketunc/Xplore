import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { SeriesKey } from "./ui";

export interface ChartSeries {
  id: string;
  label: string;
  color: string;
  t: number[];
  y: number[];
}

interface Props {
  series: ChartSeries[];
  target: number | null;
  metricLabel: string;
  timeLabel: string;
}

const HEIGHT = 300;
const M = { top: 16, right: 92, bottom: 40, left: 48 };
const LABEL_GAP = 14;

function niceStep(range: number, count: number) {
  const raw = range / Math.max(count, 1);
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  const norm = raw / mag;
  return (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10) * mag;
}

function ticks(max: number, count: number) {
  const step = niceStep(max, count);
  const top = Math.ceil(max / step - 1e-9) * step;
  const out: number[] = [];
  for (let v = 0; v <= top + 1e-9; v += step) out.push(Math.round(v * 1000) / 1000);
  return { values: out, max: top || step };
}

function nearestIndex(values: number[], x: number) {
  let best = 0;
  for (let i = 1; i < values.length; i++) if (Math.abs(values[i] - x) < Math.abs(values[best] - x)) best = i;
  return best;
}

const fmt = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1));

export function DeformationChart({ series, target, metricLabel, timeLabel }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [hover, setHover] = useState<number | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(320, entry.contentRect.width)));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const reference = useMemo(() => series.reduce<number[]>((acc, s) => (s.t.length > acc.length ? s.t : acc), []), [series]);
  const plotW = width - M.left - M.right;
  const plotH = HEIGHT - M.top - M.bottom;

  const xMax = Math.max(...series.flatMap((s) => s.t), 0) || 1;
  const yDataMax = Math.max(...series.flatMap((s) => s.y), target ?? 0, 1);
  const yTicks = ticks(yDataMax * 1.08, 5);
  const xTicks = ticks(xMax, Math.max(2, Math.floor(plotW / 90)));
  const x = (v: number) => M.left + (v / xMax) * plotW;
  const y = (v: number) => M.top + plotH - (v / yTicks.max) * plotH;

  // Direct end labels, de-collided with leader lines rather than detached nudges.
  const endLabels = useMemo(() => {
    type Item = { key: string; text: string; color: string | null; dotX: number; dotY: number; labelY: number };
    const items: Item[] = series
      .filter((s) => s.t.length)
      .map((s) => {
        const dotY = y(s.y[s.y.length - 1]);
        return { key: s.id, text: s.label, color: s.color, dotX: x(s.t[s.t.length - 1]), dotY, labelY: dotY };
      });
    if (target !== null && target <= yTicks.max) {
      items.push({ key: "__target", text: `Target ${fmt(target)}%`, color: null, dotX: M.left + plotW, dotY: y(target), labelY: y(target) });
    }
    items.sort((a, b) => a.dotY - b.dotY);
    for (let i = 1; i < items.length; i++) {
      if (items[i].labelY - items[i - 1].labelY < LABEL_GAP) items[i].labelY = items[i - 1].labelY + LABEL_GAP;
    }
    return items;
  }, [series, target, yTicks.max, plotH, plotW]);

  const hoverT = hover !== null ? reference[hover] : null;
  const readout =
    hoverT === null
      ? []
      : series
          .map((s) => ({ s, value: s.y[nearestIndex(s.t, hoverT)] }))
          .sort((a, b) => b.value - a.value);

  const onPointerMove = (e: PointerEvent<SVGRectElement>) => {
    const rect = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
    const t = ((e.clientX - rect.left - M.left) / plotW) * xMax;
    setHover(nearestIndex(reference, Math.min(Math.max(t, 0), xMax)));
  };

  const onKeyDown = (e: KeyboardEvent<SVGSVGElement>) => {
    if (!reference.length) return;
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      const delta = e.key === "ArrowRight" ? 1 : -1;
      setHover((h) => Math.min(Math.max((h ?? reference.length - 1) + delta, 0), reference.length - 1));
    } else if (e.key === "Escape") setHover(null);
  };

  const tooltipLeft = hoverT !== null ? x(hoverT) : 0;
  const flip = tooltipLeft > width - 200;

  return (
    <div>
      {series.length >= 2 && (
        <ul className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2" aria-label="Legend">
          {series.map((s) => (
            <li key={s.id} className="flex items-center gap-1.5">
              <SeriesKey color={s.color} />
              {s.label}
            </li>
          ))}
          {target !== null && (
            <li className="flex items-center gap-1.5">
              <span aria-hidden className="inline-block h-px w-4 bg-ink-2" />
              Target ≤ {fmt(target)}%
            </li>
          )}
        </ul>
      )}
      <div ref={containerRef} className="relative" style={{ height: HEIGHT }}>
        <svg
          width={width}
          height={HEIGHT}
          role="img"
          aria-label={`${metricLabel} over ${timeLabel} for ${series.map((s) => s.label).join(", ")}. Use left and right arrow keys to read values.`}
          tabIndex={0}
          onKeyDown={onKeyDown}
          onFocus={() => setHover((h) => h ?? (reference.length ? reference.length - 1 : null))}
          onBlur={() => setHover(null)}
          className="overflow-visible rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ink/40"
        >
          {/* Grid + y ticks */}
          {yTicks.values.map((v) => (
            <g key={`y${v}`}>
              <line x1={M.left} x2={M.left + plotW} y1={y(v)} y2={y(v)} stroke={v === 0 ? "var(--axis)" : "var(--grid)"} strokeWidth={1} />
              <text x={M.left - 8} y={y(v)} dy="0.32em" textAnchor="end" className="tabular fill-ink-muted text-[11px]">
                {fmt(v)}%
              </text>
            </g>
          ))}
          {xTicks.values
            .filter((v) => v <= xMax + 1e-9)
            .map((v) => (
              <text key={`x${v}`} x={x(v)} y={M.top + plotH + 18} textAnchor="middle" className="tabular fill-ink-muted text-[11px]">
                {fmt(v)}
              </text>
            ))}
          <text x={M.left + plotW / 2} y={HEIGHT - 4} textAnchor="middle" className="fill-ink-muted text-[11px]">
            {timeLabel}
          </text>

          {/* Target reference (labelled in the end-label column) */}
          {target !== null && target <= yTicks.max && (
            <line x1={M.left} x2={M.left + plotW} y1={y(target)} y2={y(target)} stroke="var(--ink-2)" strokeWidth={1} />
          )}

          {/* Series lines */}
          {series.map((s) => (
            <path
              key={s.id}
              d={s.t.map((t, i) => `${i ? "L" : "M"}${x(t).toFixed(1)},${y(s.y[i]).toFixed(1)}`).join("")}
              fill="none"
              stroke={s.color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ))}

          {/* End dots with surface ring + direct labels */}
          {endLabels.map(({ key, text, color, dotX, dotY, labelY }) => {
            const moved = Math.abs(labelY - dotY) > 2;
            return (
              <g key={`end-${key}`}>
                {moved && <line x1={dotX + 5} y1={dotY} x2={dotX + 12} y2={labelY} stroke="var(--axis)" strokeWidth={1} />}
                {color && <circle cx={dotX} cy={dotY} r={4} fill={color} stroke="var(--surface)" strokeWidth={2} />}
                <text x={dotX + 14} y={labelY} dy="0.32em" className={`text-[11px] ${color ? "fill-ink-2 font-medium" : "fill-ink-muted"}`}>
                  {text}
                </text>
              </g>
            );
          })}

          {/* Crosshair */}
          {hoverT !== null && (
            <g pointerEvents="none">
              <line x1={x(hoverT)} x2={x(hoverT)} y1={M.top} y2={M.top + plotH} stroke="var(--ink-muted)" strokeWidth={1} />
              {readout.map(({ s, value }) => (
                <circle key={`h-${s.id}`} cx={x(hoverT)} cy={y(value)} r={4} fill={s.color} stroke="var(--surface)" strokeWidth={2} />
              ))}
            </g>
          )}

          <rect
            x={M.left}
            y={M.top}
            width={plotW}
            height={plotH}
            fill="transparent"
            onPointerMove={onPointerMove}
            onPointerLeave={() => setHover(null)}
          />
        </svg>

        {hoverT !== null && (
          <div
            className="pointer-events-none absolute top-2 z-10 min-w-40 rounded-lg border border-hairline bg-surface px-3 py-2 text-xs shadow-lg"
            style={flip ? { right: width - tooltipLeft + 12 } : { left: tooltipLeft + 12 }}
            role="status"
            aria-live="polite"
          >
            <p className="mb-1 text-ink-muted">
              t = {fmt(hoverT)} ({timeLabel.toLowerCase()})
            </p>
            {readout.map(({ s, value }) => (
              <p key={`r-${s.id}`} className="flex items-center justify-between gap-4">
                <span className="flex items-center gap-1.5 text-ink-2">
                  <SeriesKey color={s.color} />
                  {s.label}
                </span>
                <strong className="tabular font-semibold text-ink">{value.toFixed(1)}%</strong>
              </p>
            ))}
          </div>
        )}
      </div>

      <details className="mt-3 text-xs">
        <summary className="cursor-pointer text-ink-2 hover:text-ink">Show data table</summary>
        <div className="mt-2 max-h-64 overflow-auto rounded-lg border border-hairline">
          <table className="tabular w-full text-right">
            <thead className="sticky top-0 bg-surface-2 text-ink-2">
              <tr>
                <th className="px-3 py-1.5 text-left font-medium">{timeLabel}</th>
                {series.map((s) => (
                  <th key={s.id} className="px-3 py-1.5 font-medium">
                    {s.label} (%)
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {reference.map((t, i) => (
                <tr key={t} className="border-t border-hairline">
                  <td className="px-3 py-1 text-left text-ink-2">{fmt(t)}</td>
                  {series.map((s) => (
                    <td key={s.id} className="px-3 py-1 text-ink">
                      {s.y[i] !== undefined ? s.y[i].toFixed(2) : "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
