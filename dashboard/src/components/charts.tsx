import { useEffect, useRef, useState } from 'react'

// Colours validated with the dataviz palette checker (light background, CVD-safe).
export const SERIES = { reported: '#2F6DB5', confirmed: '#E0A21A', fixed: '#1A9E8F' }

export function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [w, setW] = useState(600)
  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width))
    if (ref.current) ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  return [ref, w] as const
}

export interface Line { key: string; label: string; color: string }

/** Line chart over buckets (weeks or months), one shared y-axis, crosshair tooltip. */
export function LineChart<T extends object>({ rows: data, x, lines, label, height = 230 }: {
  rows: T[]
  x: keyof T & string
  lines: Line[]
  label: (v: string) => string
  height?: number
}) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)
  const rows = data as unknown as Record<string, number | string>[]
  if (rows.length < 2) return <p className="muted">Pas encore assez de données.</p>
  const H = height, L = 34, R = 70, T = 12, B = 26
  const max = Math.max(4, ...rows.flatMap((r) => lines.map((l) => Number(r[l.key]))))
  const step = Math.ceil(max / 4)
  const top = step * 4
  const xs = (i: number) => L + (i * (width - L - R)) / (rows.length - 1)
  const ys = (v: number) => T + (1 - v / top) * (H - T - B)
  const path = (k: string) => rows.map((r, i) => `${i ? 'L' : 'M'}${xs(i)},${ys(Number(r[k]))}`).join('')
  const last = rows.length - 1
  const ends = lines.map((l) => ({ ...l, y: ys(Number(rows[last][l.key])) })).sort((a, b) => a.y - b.y)
  for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 14)

  return (
    <div ref={ref} className="chart" onMouseLeave={() => setHover(null)}>
      <svg width={width} height={H} role="img" aria-label={lines.map((l) => l.label).join(', ')}>
        {[0, 1, 2, 3, 4].map((k) => (
          <g key={k}>
            <line x1={L} x2={width - R} y1={ys(k * step)} y2={ys(k * step)} className="grid" />
            <text x={L - 8} y={ys(k * step) + 4} textAnchor="end" className="axis">{k * step}</text>
          </g>
        ))}
        {rows.map((r, i) => (i % 2 === last % 2 ? (
          <text key={String(r[x])} x={xs(i)} y={H - 6} textAnchor="middle" className="axis">{label(String(r[x]))}</text>
        ) : null))}
        {hover != null && <line x1={xs(hover)} x2={xs(hover)} y1={T} y2={H - B} className="crosshair" />}
        {lines.map((l) => <path key={l.key} d={path(l.key)} stroke={l.color} className="series" />)}
        {ends.map((l) => <text key={l.key} x={xs(last) + 8} y={l.y + 4} className="end-label">{l.label}</text>)}
        {hover != null && lines.map((l) => (
          <circle key={l.key} cx={xs(hover)} cy={ys(Number(rows[hover][l.key]))} r={5} fill={l.color} className="dot" />
        ))}
        {rows.map((r, i) => (
          <rect key={String(r[x])} x={xs(i) - (width - L - R) / last / 2} y={T} width={(width - L - R) / last} height={H - T - B}
            fill="transparent" onMouseEnter={() => setHover(i)} />
        ))}
      </svg>
      {hover != null && (
        <div className="tooltip" style={{ left: Math.min(xs(hover) + 12, width - 170), top: 8 }}>
          <b>{label(String(rows[hover][x]))}</b>
          {lines.map((l) => <span key={l.key}><i style={{ background: l.color }} />{l.label} <b>{rows[hover][l.key]}</b></span>)}
        </div>
      )}
    </div>
  )
}

export const Legend = ({ lines }: { lines: Line[] }) => (
  <span className="legend">{lines.map((l) => <span key={l.key}><i style={{ background: l.color }} />{l.label}</span>)}</span>
)

/** Horizontal bars: label, bar, value. */
export function Bars({ rows, tone, format = (v) => String(v) }: {
  rows: { label: string; value: number; hint?: string }[]
  tone?: (i: number) => string
  format?: (v: number) => string
}) {
  const max = Math.max(1, ...rows.map((r) => r.value))
  return (
    <ul className="bars">
      {rows.map((r, i) => (
        <li key={r.label} title={r.hint}>
          <span className="ellipsis">{r.label}</span>
          <span className="bar"><span className={`fill ${tone?.(i) ?? ''}`} style={{ width: `${(r.value / max) * 100}%` }} /></span>
          <b>{format(r.value)}</b>
        </li>
      ))}
    </ul>
  )
}

export const weekLabel = (iso: string) => new Date(iso).toLocaleDateString('fr-TN', { day: 'numeric', month: 'short' })
export const monthLabel = (ym: string) => new Date(`${ym}-01`).toLocaleDateString('fr-TN', { month: 'short' })
