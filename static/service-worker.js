// static/service-worker.js
const CACHE_NAME = 'mada-immo-v1';
const urlsToCache = [
  '/',
  '/static/css/output.css',
  '/static/js/alpine.min.js',
  '/static/manifest.json'
];

// INSTALLATION - Mise en cache
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting()) // Activate immédiatement après l'install
  );
});

// ACTIVATION - Nettoyage anciens caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(name => name !== CACHE_NAME)
                  .map(name => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// FETCH - Stratégie Cache First
self.addEventListener('fetch', event => {
  // Ne pas gérer les requêtes non-GET
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request)
      .then(cached => cached || fetch(event.request))
      // En cas d'échec réseau, alternative offline
      .catch(() => caches.match('/offline.html'))
  );
});