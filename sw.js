/* 解禁の畑 — service worker
   ゲームを更新したら、次行の版番号を1つ上げてから push すること。
   版番号を上げないと、端末側は古いキャッシュを返し続ける。 */
const CACHE = 'kaikin-v23';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon-512.png',
  './icon-192.png',
  './icon-maskable-512.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(ASSETS))
      .then(() => self.skipWaiting())
      .catch(() => {})
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
      .catch(() => {})
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request))
  );
});
