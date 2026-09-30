// Types mirror backend/app/schemas.py; every call goes through the Vite proxy.
import { useCallback, useEffect, useState } from 'react'

export type Status = 'new' | 'confirmed' | 'sheet_sent' | 'fixed' | 'rejected'

export interface Report {
  report_id: string
  ref: string
  device_report_id: string
  device_id: string | null
  lat: number
  lon: number
  address: string | null
  score: number | null
  confidence: number | null
  status: Status
  source: 'manual' | 'driving_mode'
  cluster_id: string | null
  cluster_size: number
  target_office: string | null
  sheet_text: string | null
  photo_url: string | null
  created_at: string
  updated_at: string
  due_at: string | null
  overdue: boolean
  priority: number
}

export interface Stats {
  reports_total: number
  potholes_total: number
  open: number
  urgent_open: number
  overdue: number
  fixed: number
  rejected: number
  median_repair_days: number | null
  by_status: Partial<Record<Status, number>>
  by_severity: Record<string, number>
  by_office: Record<string, number>
  top_zones: [string, number][]
  weekly: { week: string; reported: number; fixed: number }[]
}

export interface Message {
  message_id: string
  device_id: string
  sender: 'citizen' | 'authority'
  body: string
  created_at: string
}

export interface Conversation {
  device_id: string
  last_body: string
  last_sender: 'citizen' | 'authority'
  last_at: string
  count: number
  reports: number
}

export interface AssistantReply {
  answer: string
  refs: Report[]
  source: 'llm' | 'fallback'
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
  })
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? res.statusText)
  return res.json()
}

export const api = {
  reports: () => call<Report[]>('/reports'),
  stats: () => call<Stats>('/stats'),
  conversations: () => call<Conversation[]>('/conversations'),
  messages: (deviceId: string) => call<Message[]>(`/messages?device_id=${encodeURIComponent(deviceId)}`),
  reply: (deviceId: string, body: string) =>
    call<Message>('/messages', { method: 'POST', body: JSON.stringify({ device_id: deviceId, sender: 'authority', body }) }),
  setStatus: (reportId: string, status: Status) =>
    call(`/reports/${reportId}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  ask: (question: string, history: { role: 'user' | 'assistant'; content: string }[]) =>
    call<AssistantReply>('/assistant', { method: 'POST', body: JSON.stringify({ question, history }) }),
}

/** Fetch on mount and every `everyMs` (the "live" dashboard is just polling). */
export function usePoll<T>(load: () => Promise<T>, everyMs = 15000, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const refresh = useCallback(() => load().then((d) => (setData(d), setError(null)), (e) => setError(String(e.message ?? e))), deps)
  useEffect(() => {
    refresh()
    const t = setInterval(refresh, everyMs)
    return () => clearInterval(t)
  }, [refresh, everyMs])
  return { data, error, refresh }
}

// ---- Display helpers shared by every page ----

/** Navigate: go('map', id) -> "#/map/<id>" (App's useHash is the router). */
export const go = (page: string, id?: string) => (location.hash = `/${page}${id ? `/${id}` : ''}`)

export const STATUS: Record<Status, { label: string; tone: string }> = {
  new: { label: 'Nouveau', tone: 'info' },
  confirmed: { label: 'Confirmé', tone: 'warn' },
  sheet_sent: { label: 'Fiche envoyée', tone: 'serious' },
  fixed: { label: 'Réparé', tone: 'good' },
  rejected: { label: 'Rejeté', tone: 'muted' },
}

/** The next step an agent can take from each status (mirrors backend/app/status.py). */
export const NEXT: Partial<Record<Status, Status>> = { new: 'confirmed', confirmed: 'sheet_sent', sheet_sent: 'fixed' }
export const OPEN: Status[] = ['new', 'confirmed', 'sheet_sent']

/** Severity 1-5 -> marker colour; unscored reports stay grey until triaged. */
export const severityColor = (score: number | null) =>
  score == null ? '#8A8F98' : ['#3E9E6B', '#3E9E6B', '#E0A21A', '#E36A1B', '#C8322B'][score - 1]

const rtf = new Intl.RelativeTimeFormat('fr', { numeric: 'auto' })
export function ago(iso: string) {
  const mins = (new Date(iso).getTime() - Date.now()) / 60000
  if (Math.abs(mins) < 60) return rtf.format(Math.round(mins), 'minute')
  if (Math.abs(mins) < 1440) return rtf.format(Math.round(mins / 60), 'hour')
  return rtf.format(Math.round(mins / 1440), 'day')
}

export const date = (iso: string) =>
  new Date(iso).toLocaleDateString('fr-TN', { day: '2-digit', month: 'short', year: 'numeric' })

/** Citizens are anonymous: "Citoyen ·7F3A" from their device id. */
export const citizen = (deviceId: string) => `Citoyen #${initials(deviceId)}`
/** Last 4 letters/digits of a device id, e.g. "seed-citizen-04" -> "EN04". */
export const initials = (deviceId: string) => deviceId.replace(/[^0-9a-z]/gi, '').slice(-4).toUpperCase()

/** Newest report per cluster: one row per physical pothole (backend: latest_per_pothole). */
export function potholes(reports: Report[]) {
  const seen = new Map<string, Report>()
  for (const r of [...reports].sort((a, b) => b.created_at.localeCompare(a.created_at)))
    if (!seen.has(r.cluster_id ?? r.report_id)) seen.set(r.cluster_id ?? r.report_id, r)
  return [...seen.values()]
}
