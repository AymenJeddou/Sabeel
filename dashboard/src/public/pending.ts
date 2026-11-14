// Offline queue for the web report page: reports that could not be sent are
// kept in IndexedDB and retried on the `online` event and on the next visit
// (Background Sync does not exist on iOS, so it is not relied on).
// device_report_id never changes between retries, so the API deduplicates.

export interface PendingReport {
  device_report_id: string
  fields: Record<string, string>
  photo: Blob
  saved_at: string
}

const DB = 'sabeel'
const STORE = 'pending_reports'

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1)
    req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: 'device_report_id' })
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function tx<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await open()
  return new Promise((resolve, reject) => {
    const req = fn(db.transaction(STORE, mode).objectStore(STORE))
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export const savePending = (r: PendingReport) => tx('readwrite', (s) => s.put(r))
export const removePending = (id: string) => tx('readwrite', (s) => s.delete(id))
export const listPending = () => tx<PendingReport[]>('readonly', (s) => s.getAll() as IDBRequest<PendingReport[]>)

export function toForm(r: PendingReport): FormData {
  const form = new FormData()
  for (const [k, v] of Object.entries(r.fields)) form.set(k, v)
  form.set('photo', r.photo, 'photo.jpg')
  return form
}

/** Sends every pending report; returns how many went through. Stops on the first network error. */
export async function flushPending(
  send: (f: FormData) => Promise<unknown>,
  store: { list: () => Promise<PendingReport[]>; remove: (id: string) => Promise<unknown> } = {
    list: listPending,
    remove: removePending,
  },
): Promise<number> {
  let sent = 0
  let pending: PendingReport[] = []
  try {
    pending = await store.list()
  } catch {
    return 0 // IndexedDB unavailable (private mode)
  }
  for (const r of pending) {
    try {
      await send(toForm(r))
    } catch (e) {
      const status = (e as { status?: number }).status
      if (!status || status >= 500 || status === 429) break // offline or server trouble: keep it
    }
    await store.remove(r.device_report_id) // sent, or rejected for good (4xx)
    sent++
  }
  return sent
}
