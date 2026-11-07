// Sabeel service worker: makes the report page installable and usable on a
// flaky connection. App shell: network first, cache fallback. API calls are
// never cached here (the page keeps unsent reports in IndexedDB instead).
const CACHE = 'sabeel-shell-v1'
const SHELL = ['./', './index.html', './manifest.webmanifest', './favicon.svg', './icon-192.png']
const API = /^\/(reports|potholes|public|map|authorities|analytics|export|messages|conversations|auth|weather|assistant|static|devices|detect|health)/

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (e.request.method !== 'GET' || url.origin !== location.origin || API.test(url.pathname)) return
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone()
          caches.open(CACHE).then((c) => c.put(e.request, copy))
        }
        return res
      })
      .catch(() => caches.match(e.request).then((hit) => hit || caches.match('./index.html'))),
  )
})
