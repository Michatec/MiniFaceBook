const CACHE_NAME = "minifb-v1";
const urlsToCache = [
  "/",
  "/static/css/styles.css",
  "/static/js/theme.js",
  "/static/manifest.json"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});