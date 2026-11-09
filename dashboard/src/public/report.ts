// Builds the POST /reports request exactly like the mobile app does
// (frozen contract: field names, UTC timestamps with a trailing Z).
import { utcIso } from '../api'

export interface Fix {
  lat: number
  lon: number
  accuracy: number
  speed: number | null // m/s, from the browser
  heading: number | null // degrees, often null in browsers
}

const DEVICE_KEY = 'sabeel.device_id'

/** Stable per-browser id (roadmap decision 2), created once. */
export function deviceId(): string {
  try {
    let id = localStorage.getItem(DEVICE_KEY)
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem(DEVICE_KEY, id)
    }
    return id
  } catch {
    return crypto.randomUUID() // storage blocked: one id per page load
  }
}

export function reportFields(fix: Fix, capturedAt: Date, deviceReportId: string, device: string, force = false): Record<string, string> {
  const fields: Record<string, string> = {
    device_report_id: deviceReportId,
    device_id: device,
    lat: fix.lat.toFixed(6),
    lon: fix.lon.toFixed(6),
    gps_accuracy_m: fix.accuracy.toFixed(1),
    speed_kmh: ((fix.speed ?? 0) * 3.6).toFixed(1),
    captured_at: utcIso(capturedAt),
    source: 'web',
  }
  // Decision 3: direction is optional, omitted when the browser has no compass.
  if (fix.heading != null && !Number.isNaN(fix.heading)) fields.direction_deg = fix.heading.toFixed(1)
  if (force) fields.force = 'true'
  return fields
}

/** Downscales a camera photo to at most `max` px (JPEG 0.8) before upload. */
export async function downscale(file: Blob, max = 1600): Promise<Blob> {
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  bitmap.close() // a 12 MP photo holds ~48 MB until released; phones run out on the second shot
  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('encode failed'))), 'image/jpeg', 0.8))
}

/** Remembers which reports this browser sent, for the tracker list. */
const MINE_KEY = 'sabeel.my_reports'
export function rememberReport(id: string) {
  try {
    const mine = JSON.parse(localStorage.getItem(MINE_KEY) ?? '[]') as string[]
    localStorage.setItem(MINE_KEY, JSON.stringify([id, ...mine.filter((x) => x !== id)].slice(0, 50)))
  } catch { /* ignore */ }
}
export function myReports(): string[] {
  try { return JSON.parse(localStorage.getItem(MINE_KEY) ?? '[]') } catch { return [] }
}
