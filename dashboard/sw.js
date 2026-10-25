// Service Worker for NBA Israelis Tracker PWA
const CACHE_NAME = 'nba-israelis-v2';
const ASSETS_TO_CACHE = [
  './index.html',
  './favicon.svg',
  './manifest.json'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {});
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = event.request.url;

  // CRITICAL: Dynamic data files (games.json, games_data.js) MUST NEVER be cached by Service Worker!
  // Always fetch fresh from network directly to ensure live boxscores, game statuses and broadcasts.
  if (url.includes('/data/') || url.includes('.json') || url.includes('games_data.js')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Network first, fallback to cache for shell assets
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request);
      })
  );
});
