import { describe, expect, it } from 'vitest'
import { ago, qs, utcIso } from './api'
import { priorityExplanation } from './i18n'
import { reportFields } from './public/report'

describe('web report request (frozen contract)', () => {
  const fix = { lat: 36.8065012, lon: 10.1815, accuracy: 7.24, speed: 2, heading: null }
  const at = new Date(Date.UTC(2026, 10, 7, 9, 30, 15, 456))

  it('uses the exact field names and formats of the mobile app', () => {
    const f = reportFields(fix, at, 'dr-1', 'dev-1')
    expect(f).toEqual({
      device_report_id: 'dr-1',
      device_id: 'dev-1',
      lat: '36.806501',
      lon: '10.181500',
      gps_accuracy_m: '7.2',
      speed_kmh: '7.2',
      captured_at: '2026-11-07T09:30:15Z',
      source: 'web',
    })
  })

  it('omits direction without a compass and adds force only when asked', () => {
    expect(reportFields(fix, at, 'a', 'b')).not.toHaveProperty('direction_deg')
    const f = reportFields({ ...fix, heading: 271.04 }, at, 'a', 'b', true)
    expect(f.direction_deg).toBe('271.0')
    expect(f.force).toBe('true')
  })
})

describe('helpers', () => {
  it('formats UTC timestamps with a trailing Z and no milliseconds', () => {
    expect(utcIso(new Date(Date.UTC(2026, 0, 2, 3, 4, 5, 999)))).toBe('2026-01-02T03:04:05Z')
  })

  it('builds query strings without empty values', () => {
    expect(qs({ status: 'open', sev: '', region: undefined, overdue: false, limit: 50 })).toBe('?status=open&overdue=false&limit=50')
    expect(qs({})).toBe('')
  })

  it('explains a priority score with only the non-zero parts', () => {
    expect(priorityExplanation({ severity: 40, road: 15, confirmations: 2.5, age: 0, rain: 10 }))
      .toBe('Sévérité +40 · Type de route +15 · Citoyens +2.5 · Pluie prévue +10')
  })
})

describe('relative times', () => {
  it('never prints NaN', () => {
    expect(ago(null)).toBe('—')
    expect(ago('not a date')).toBe('—')
    expect(ago(new Date(Date.now() - 3 * 86400000).toISOString())).toBe('il y a 3 jours')
  })
})
