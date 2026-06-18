const CACHE_NAME = 'smartwrite-v1';
const STATIC_ASSETS = ['/', '/app.js', '/manifest.json', '/icon.svg'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .catch(() => {}) // don't block install if a CDN asset is unavailable
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // API calls always go to network — never serve stale auth or correction data.
  if (event.request.url.includes('/api/')) return;

  // Static assets: cache-first with network fallback.
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
