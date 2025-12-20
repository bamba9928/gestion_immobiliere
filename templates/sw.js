const CACHE_NAME = 'mada-immo-v1';
const urlsToCache = [
  '/',
  '/static/css/dist/styles.css', // Correction du nom du fichier
  '/static/img/mada.png',        // Ajout du logo indispensable
  '/static/manifest.json'

];

// INSTALLATION
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache ouvert');
        return cache.addAll(urlsToCache);
      })
      .then(() => self.skipWaiting())
  );
});

// ACTIVATION
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// FETCH - Stratégie : Network First avec fallback sur Cache
// C'est mieux pour une application de gestion (données à jour)
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .catch(() => {
        return caches.match(event.request);
      })
  );
});