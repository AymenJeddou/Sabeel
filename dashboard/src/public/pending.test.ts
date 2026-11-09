import { describe, expect, it } from 'vitest'
import { flushPending, type PendingReport } from './pending'

const report = (id: string): PendingReport => ({
  device_report_id: id,
  fields: { device_report_id: id },
  photo: new Blob(['x']),
  saved_at: '2026-11-09T10:00:00Z',
})

function fakeStore(ids: string[]) {
  const left = new Set(ids)
  return { left, list: async () => [...left].map(report), remove: async (id: string) => void left.delete(id) }
}

describe('offline report queue', () => {
  it('sends everything when online', async () => {
    const store = fakeStore(['a', 'b'])
    expect(await flushPending(async () => ({}), store)).toBe(2)
    expect(store.left.size).toBe(0)
  })

  it('keeps reports on network errors, 5xx and 429, and stops there', async () => {
    for (const err of [new TypeError('offline'), { status: 503 }, { status: 429 }]) {
      const store = fakeStore(['a', 'b'])
      expect(await flushPending(async () => Promise.reject(err), store)).toBe(0)
      expect([...store.left]).toEqual(['a', 'b'])
    }
  })

  it('drops a report the API rejected for good (4xx)', async () => {
    const store = fakeStore(['bad', 'ok'])
    const send = async (f: FormData) => (f.get('device_report_id') === 'bad' ? Promise.reject({ status: 422 }) : {})
    expect(await flushPending(send, store)).toBe(2)
    expect(store.left.size).toBe(0)
  })

  it('does nothing when IndexedDB is unavailable', async () => {
    const store = { list: async () => Promise.reject(new Error('blocked')), remove: async () => {} }
    expect(await flushPending(async () => ({}), store)).toBe(0)
  })
})
