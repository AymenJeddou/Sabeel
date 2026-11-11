// Typed client for the Core API (backend/app/routers). Officer calls carry the
// office token; public calls (map, stats, report, track) need none.
import { useCallback, useEffect, useState } from 'react'

export type Status = 'new' | 'confirmed' | 'sheet_sent' | 'fixed' | 'rejected' | 'reopened'
export type SheetStatus = 'queued' | 'generated' | 'approved' | 'failed'
export type SlaLevel = 'ok' | 'warning' | 'overdue' | null

/** A pothole as the officer queue, map and export see it (serialize.queue_row). */
export interface Pothole {
  pothole_id: string
  ref: string
  lat: number
  lon: number
  status: Status
  severity: number | null
  report_count: number
  device_count: number
  confirm_count: number
  fixed_ok_count: number
  not_fixed_count: number
  not_pothole_count: number
  road_name: string | null
  road_ref: string | null
  road_type: string | null
  road_class: string | null
  address_label: string | null
  municipality: string | null
  region: string | null
  target_office: string | null
  target_office_id: string | null
  sheet_status: SheetStatus | null
  sla_due_at: string | null
  sla_level: SlaLevel
  overdue: boolean
  overdue_by_hours: number
  fix_verified: boolean
  needs_review: boolean
  priority_score: number
  priority_components: Record<string, number>
  max_confidence: number | null
  rain_mm_48h: number | null
  escalated_at: string | null
  created_at: string
  updated_at: string
  confirmed_at: string | null
  fixed_at: string | null
  age_days: number
}

export interface Box { x: number; y: number; w: number; h: number; conf: number | null }

export interface ReportBrief {
  report_id: string
  device_report_id: string
  device_id: string | null
  photo_url: string | null
  lat: number
  lon: number
  gps_accuracy_m: number | null
  speed_kmh: number | null
  source: 'manual' | 'driving_mode' | 'web'
  score: number | null
  confidence: number | null
  detected: boolean
  boxes: Box[]
  captured_at: string
  created_at: string
}

export interface PotholeEvent {
  kind: string
  actor: string
  from_status: string | null
  to_status: string | null
  note: string | null
  data: Record<string, unknown> | null
  created_at: string
}

export interface Citation { rule_id: string; source: string; excerpt: string }

export interface PotholeDetail extends Pothole {
  sheet_text: string | null
  sheet_edited: boolean
  sheet_citations: Citation[]
  sheet_generated_at: string | null
  sheet_approved_at: string | null
  sheet_approved_by: string | null
  sheet_hash: string | null
  sheet_job: { status: string; attempts: number; last_error: string | null; next_attempt_at: string } | null
  fixed_proof_url: string | null
  fixed_note: string | null
  fix_check: { detected: boolean; confidence: number | null; score: number | null; boxes: Box[] } | null
  repair_method: string | null
  enrichment_source: string | null
  reports: ReportBrief[]
  events: PotholeEvent[]
}

export interface Office {
  office_id: string
  code: string
  name: string
  kind: 'Municipality' | 'DGPC' | 'Ministry of Equipment'
  region: string | null
  lat: number | null
  lon: number | null
  is_ministry: boolean
  parent: string | null
  offices: { office_id: string; code: string; name: string; kind: string; region: string | null }[]
}

export interface MedP90 { median: number | null; p90: number | null; n: number }

export interface Summary {
  potholes_total: number
  reports_total: number
  by_status: Partial<Record<Status, number>>
  open: number
  new: number
  confirmed: number
  sheet_sent: number
  fixed: number
  rejected: number
  reopened: number
  urgent_open: number
  needs_review: number
  overdue: number
  warning: number
  overdue_rate: number | null
  escalated: number
  rain_at_risk: number
  time_to_fix_days: MedP90
  sheet_approval_hours: MedP90
  fix_verified: number
  false_positive_rate: number | null
  by_severity: Record<string, number>
}

export interface TrendWeek { week: string; reported: number; confirmed: number; fixed: number }
export interface Group extends MedP90 { key: string; open: number }
export interface Road { road: string; municipality: string | null; open: number; severity_sum: number; max_severity: number; health: number }
export interface Hotspots { roads: Road[]; points: [number, number, number][] }

export interface RoutePlan {
  engine: 'osrm' | 'fallback' | 'none'
  distance_km: number
  duration_min: number
  geometry: { type: 'LineString'; coordinates: [number, number][] } | null
  start: { lat: number; lon: number }
  stops: (Pothole & { stop: number; method: string | null })[]
}

export interface Weather {
  available: boolean
  rain_mm_48h: number | null
  alert: boolean
  threshold_mm: number
  days: { date: string; rain_mm: number; probability: number }[]
  at_risk: number
  at_risk_refs: string[]
}

export interface Message { message_id: string; device_id: string; sender: 'citizen' | 'authority'; body: string; created_at: string }
export interface Conversation { device_id: string; last_body: string; last_sender: 'citizen' | 'authority'; last_at: string; count: number; reports: number }
export interface AssistantReply { answer: string; refs: Pothole[]; source: 'llm' | 'fallback' }

export interface PublicStats {
  reported: number
  confirmed: number
  open: number
  fixed: number
  fixed_last_7_days: number
  fixed_last_30_days: number
  fix_verified: number
  citizens_confirmations: number
  median_days_to_fix: number | null
  regions: { region: string; suppressed: boolean; reported: number | null; fixed: number | null; median_days_to_fix: number | null }[]
  monthly: { month: string; reported: number; fixed: number }[]
  worst_roads: { road: string; municipality: string | null; open: number; health: number }[]
}
export interface PublicPoint { lat: number; lon: number; severity: number | null; status: Status }
export interface PublicPothole {
  pothole_id: string; ref: string; lat: number; lon: number; status: Status; severity: number | null
  report_count: number; confirm_count: number; address_label: string | null; target_office: string | null
  sheet_status: SheetStatus | null; sla_level: SlaLevel; fix_verified: boolean
  created_on: string; confirmed_on: string | null; fixed_on: string | null
}
export interface Tracker {
  device_report_id: string; ref: string | null; status: Status; severity: number | null; detected: boolean
  sheet_status: SheetStatus | null; sheet_summary: string | null; target_office: string | null; address_label: string | null
  created_at: string; fixed_at: string | null; timeline: { status: string; at: string }[]
}
export interface CreatedReport {
  report_id: string; device_report_id: string; pothole_id: string | null; ref: string | null
  detected: boolean; needs_review: boolean; status: Status; score: number | null
}

// ---------------------------------------------------------------------------

/** Empty in dev (the Vite proxy forwards to the API); the API origin in production. */
export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
export const asset = (url: string | null | undefined) => (!url ? '' : url.startsWith('http') ? url : API_BASE + url)

const TOKEN_KEY = 'sabeel.office_token'
let token: string | null = (() => {
  try { return sessionStorage.getItem(TOKEN_KEY) } catch { return null }
})()
export const getToken = () => token
export function setToken(t: string | null) {
  token = t
  try { t ? sessionStorage.setItem(TOKEN_KEY, t) : sessionStorage.removeItem(TOKEN_KEY) } catch { /* private mode */ }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

export async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(API_BASE + path, { ...init, headers })
  if (res.status === 401 && token) window.dispatchEvent(new Event('sabeel:logout'))
  if (!res.ok) {
    const detail = (await res.json().catch(() => null))?.detail
    throw new ApiError(res.status, typeof detail === 'string' ? detail : res.statusText || `HTTP ${res.status}`)
  }
  return (res.headers.get('content-type') ?? '').includes('json') ? res.json() : (res as unknown as T)
}

const json = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) })
export const qs = (params: Record<string, string | number | boolean | null | undefined>) => {
  const s = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') s.set(k, String(v))
  const out = s.toString()
  return out ? `?${out}` : ''
}

export interface QueueFilters {
  status?: string; sev?: string; region?: string; needs_review?: boolean; sheet_status?: string
  overdue?: boolean; sort?: string; limit?: number; cursor?: number
}

export const api = {
  me: () => call<Office>('/auth/me'),
  queue: (f: QueueFilters = {}) => call<{ items: Pothole[]; total: number; next_cursor: number | null }>(`/authorities/me/queue${qs({ ...f })}`),
  pothole: (id: string) => call<PotholeDetail>(`/potholes/${id}`),
  setStatus: (id: string, status: 'confirmed' | 'rejected', note?: string) =>
    call(`/potholes/${id}`, { method: 'PATCH', body: JSON.stringify({ status, note }) }),
  fix: (id: string, proof: File, note: string) => {
    const form = new FormData()
    form.set('proof', proof)
    form.set('note', note)
    return call<{ fix_check: PotholeDetail['fix_check']; fix_verified: boolean }>(`/potholes/${id}/fix`, { method: 'POST', body: form })
  },
  feedback: (id: string, label: 'not_pothole' | 'confirmed_pothole', note?: string) => call(`/potholes/${id}/feedback`, json({ label, note })),
  editSheet: (id: string, sheet_text: string) => call(`/potholes/${id}/sheet`, { method: 'PATCH', body: JSON.stringify({ sheet_text }) }),
  approveSheet: (id: string) => call<{ fingerprint: string }>(`/potholes/${id}/sheet/approve`, { method: 'POST' }),
  retrySheet: (id: string) => call(`/potholes/${id}/sheet/retry`, { method: 'POST' }),
  /** Downloads an authenticated file (PDF, CSV, GeoJSON) through a blob link. */
  download: async (path: string, filename: string) => {
    const res = await call<Response>(path)
    const url = URL.createObjectURL(await res.blob())
    const a = Object.assign(document.createElement('a'), { href: url, download: filename })
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 2000)
  },
  summary: (office?: string) => call<Summary>(`/analytics/summary${qs({ office })}`),
  trend: (weeks = 12) => call<TrendWeek[]>(`/analytics/trend${qs({ weeks })}`),
  timeToFix: () => call<{ by_office: Group[]; by_region: Group[]; by_road_class: Group[] }>('/analytics/time-to-fix'),
  hotspots: () => call<Hotspots>('/analytics/hotspots'),
  channels: () => call<Record<string, number>>('/analytics/channels'),
  route: (p: { start_lat?: number; start_lon?: number; max_stops?: number; min_severity?: number }) =>
    call<RoutePlan>(`/authorities/me/route${qs(p)}`),
  weather: () => call<Weather>('/weather'),
  conversations: () => call<Conversation[]>('/conversations'),
  messages: (deviceId: string) => call<Message[]>(`/messages${qs({ device_id: deviceId })}`),
  reply: (deviceId: string, body: string) => call<Message>('/messages', json({ device_id: deviceId, sender: 'authority', body })),
  ask: (question: string, history: { role: 'user' | 'assistant'; content: string }[]) =>
    call<AssistantReply>('/assistant', json({ question, history })),
  // Public, no token needed
  publicStats: () => call<PublicStats>('/public/stats'),
  publicMap: (state: 'all' | 'open' | 'fixed' = 'all') => call<PublicPoint[]>(`/public/map${qs({ state })}`),
  publicPothole: (id: string) => call<PublicPothole>(`/public/potholes/${id}`),
  verify: (id: string, h: string) => call<{ ref: string; valid: boolean; approved_on: string | null; office: string | null }>(`/public/potholes/${id}/verify${qs({ h })}`),
  track: (deviceReportId: string) => call<Tracker>(`/reports/${encodeURIComponent(deviceReportId)}`),
  submitReport: (form: FormData) => call<CreatedReport>('/reports', { method: 'POST', body: form }),
}

/** Fetch on mount and every `everyMs` (the "live" dashboard is polling). */
export function usePoll<T>(load: () => Promise<T>, everyMs = 15000, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const refresh = useCallback(() => load().then((d) => (setData(d), setError(null)), (e) => setError(String(e.message ?? e))), deps)
  useEffect(() => {
    refresh()
    if (!everyMs) return
    // A background tab doesn't poll (it would spend the office's rate limit for nothing);
    // it catches up as soon as it is shown again.
    const t = setInterval(() => document.hidden || refresh(), everyMs)
    const onShow = () => document.hidden || refresh()
    document.addEventListener('visibilitychange', onShow)
    return () => (clearInterval(t), document.removeEventListener('visibilitychange', onShow))
  }, [refresh, everyMs])
  return { data, error, refresh }
}

// ---- Display helpers shared by every page ----

/** Navigate: go('map', id) -> "#/map/<id>" (App's useHash is the router). */
export const go = (page: string, id?: string) => (location.hash = `/${page}${id ? `/${id}` : ''}`)

export const OPEN: Status[] = ['new', 'confirmed', 'sheet_sent', 'reopened']

/** Severity 1-5 -> marker colour; unscored potholes stay grey until triaged. */
export const severityColor = (score: number | null) =>
  score == null ? '#8A8F98' : ['#3E9E6B', '#3E9E6B', '#E0A21A', '#E36A1B', '#C8322B'][score - 1]
export const FIXED_COLOR = '#1A9E8F'

const rtf = new Intl.RelativeTimeFormat('fr', { numeric: 'auto' })
export function ago(iso: string) {
  const mins = (new Date(iso).getTime() - Date.now()) / 60000
  if (Math.abs(mins) < 60) return rtf.format(Math.round(mins), 'minute')
  if (Math.abs(mins) < 1440) return rtf.format(Math.round(mins / 60), 'hour')
  return rtf.format(Math.round(mins / 1440), 'day')
}

export const date = (iso: string) =>
  new Date(iso).toLocaleDateString('fr-TN', { day: '2-digit', month: 'short', year: 'numeric' })
export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString('fr-TN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })

/** Citizens are anonymous: "Citoyen #EN04" from their device id. */
export const citizen = (deviceId: string) => `Citoyen #${initials(deviceId)}`
export const initials = (deviceId: string) => deviceId.replace(/[^0-9a-z]/gi, '').slice(-4).toUpperCase()

/** UTC ISO 8601 without milliseconds and with a trailing Z (frozen contract). */
export const utcIso = (d: Date) => d.toISOString().replace(/\.\d{3}Z$/, 'Z')
