import { useEffect, useId, useRef, useState } from "react";

export interface Bar {
  label: string;
  value: number;
  color?: string;
  tip?: string;
}

interface Props {
  bars: Bar[];
  orientation?: "horizontal" | "vertical";
  valueLabel: string;
  title: string;
  maxValue?: number;
  ticks?: number[];
  height?: number;
  formatValue?: (v: number) => string;
  refLine?: { value: number; label: string };
}

/** Accessible SVG bar chart with hover/focus tooltip and a table view. */
export default function BarChart({
  bars, orientation = "vertical", valueLabel, title, maxValue, ticks, height, formatValue = (v) => String(v), refLine,
}: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const [width, setWidth] = useState(640);
  const wrap = useRef<HTMLDivElement>(null);
  const id = useId();
  // Size the SVG to its container so one unit = one CSS pixel: text stays readable on phones.
  useEffect(() => {
    const el = wrap.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(260, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [table]);
  const max = maxValue ?? (Math.max(...bars.map((b) => b.value), refLine?.value ?? 0) * 1.08 || 1);
  const tickVals = ticks ?? niceTicks(max, bars.every((b) => Number.isInteger(b.value)));

  if (table) {
    return (
      <figure className="chart">
        <div className="chart__bar"><button className="link-btn" onClick={() => setTable(false)}>View as chart</button></div>
        <table className="data-table">
          <caption className="sr-only">{title}</caption>
          <thead><tr><th scope="col">Item</th><th scope="col">{valueLabel}</th></tr></thead>
          <tbody>{bars.map((b) => <tr key={b.label}><td>{b.label}</td><td>{formatValue(b.value)}</td></tr>)}</tbody>
        </table>
      </figure>
    );
  }

  const horiz = orientation === "horizontal";
  const rowH = 22;
  const W = width;
  const H = height ?? (horiz ? bars.length * rowH + 36 : 220);
  const longest = Math.max(...bars.map((b) => b.label.length));
  const padL = horiz ? Math.min(W * 0.45, longest * 6.4 + 14) : 40;
  const padB = horiz ? 26 : 34;
  const padT = 10;
  const padR = 12;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const scale = (v: number) => (v / max) * (horiz ? plotW : plotH);
  const band = (horiz ? plotH : plotW) / bars.length;
  const thick = Math.max(3, Math.min(band * 0.68, horiz ? 14 : 28));

  return (
    <figure className="chart" aria-labelledby={`${id}-t`}>
      <div className="chart__bar">
        <span id={`${id}-t`} className="sr-only">{title}</span>
        <button className="link-btn" onClick={() => setTable(true)}>View as table</button>
      </div>
      <div className="chart__svgwrap" ref={wrap}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} className="chart__svg">
          {tickVals.map((t) => {
            const p = scale(t);
            return horiz ? (
              <g key={t}>
                <line x1={padL + p} x2={padL + p} y1={padT} y2={padT + plotH} className="grid" />
                <text x={padL + p} y={H - 8} className="tick" textAnchor="middle">{formatValue(t)}</text>
              </g>
            ) : (
              <g key={t}>
                <line x1={padL} x2={W - padR} y1={padT + plotH - p} y2={padT + plotH - p} className="grid" />
                <text x={padL - 6} y={padT + plotH - p + 4} className="tick" textAnchor="end">{formatValue(t)}</text>
              </g>
            );
          })}
          {bars.map((b, i) => {
            const len = Math.max(scale(b.value), b.value > 0 ? 2 : 0);
            const c = padT + band * i + (band - thick) / 2;
            const cx = padL + band * i + (band - thick) / 2;
            const active = hover === i;
            return (
              <g key={b.label}
                 tabIndex={0}
                 onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
                 onFocus={() => setHover(i)} onBlur={() => setHover(null)}
                 aria-label={`${b.label}: ${formatValue(b.value)} ${valueLabel}`}>
                {horiz ? (
                  <>
                    <rect x={padL} y={padT + band * i} width={plotW} height={band} className="hit" />
                    <rect x={padL} y={c} width={len} height={thick} rx={Math.min(4, thick / 2)}
                          fill={b.color ?? "var(--series-1)"} opacity={hover === null || active ? 1 : 0.55} />
                    <text x={padL - 6} y={c + thick / 2 + 4} className="tick tick--label" textAnchor="end">{b.label}</text>
                  </>
                ) : (
                  <>
                    <rect x={padL + band * i} y={padT} width={band} height={plotH} className="hit" />
                    <rect x={cx} y={padT + plotH - len} width={thick} height={len} rx={Math.min(4, thick / 2)}
                          fill={b.color ?? "var(--series-1)"} opacity={hover === null || active ? 1 : 0.55} />
                    {i % Math.max(1, Math.ceil((longest * 6.6 + 8) / band)) === 0 && (
                      <text x={cx + thick / 2} y={H - 14} className="tick tick--label" textAnchor="middle">{b.label}</text>
                    )}
                  </>
                )}
              </g>
            );
          })}
          {refLine && (horiz ? (
            <line x1={padL + scale(refLine.value)} x2={padL + scale(refLine.value)} y1={padT} y2={padT + plotH} className="ref" />
          ) : (
            <g>
              <line x1={padL} x2={W - padR} y1={padT + plotH - scale(refLine.value)} y2={padT + plotH - scale(refLine.value)} className="ref" />
              <text x={W - padR} y={padT + plotH - scale(refLine.value) - 5} className="tick" textAnchor="end">{refLine.label}</text>
            </g>
          ))}
          <line x1={padL} x2={horiz ? padL : W - padR} y1={padT + plotH} y2={horiz ? padT : padT + plotH} className="axis" />
        </svg>
        {hover !== null && (
          <div className="tooltip" role="status">
            <strong>{bars[hover].label}</strong>
            <span>{bars[hover].tip ?? `${formatValue(bars[hover].value)} ${valueLabel}`}</span>
          </div>
        )}
      </div>
    </figure>
  );
}

function niceTicks(max: number, integer: boolean): number[] {
  const raw = max / 4;
  const mag = 10 ** Math.floor(Math.log10(raw));
  let step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  if (integer) step = Math.max(1, Math.ceil(step)); // counts get whole-number ticks
  const out: number[] = [];
  for (let t = 0; t <= max; t += step) out.push(Math.round(t * 100) / 100);
  return out;
}
