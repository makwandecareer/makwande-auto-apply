// service-worker.js (multi-page safe)

const CACHE_NAME = "makwande-cache-v2";
const CORE_ASSETS = [
  "/",
  "/index.html",
  "/app.css",
  "/config.js",
  "/api.js",
  "/auth.js",
  "/ui.js",
  "/app.js",
  "/jobs.html",
  "/results.html",
  "/dashboard.html",
  "/login.html",
  "/signup.html",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Only handle same-origin
  if (url.origin !== self.location.origin) return;

  // ✅ If it's an actual file (has extension like .html, .js, .css, .svg), fetch normally
  const hasExtension = /\.[a-zA-Z0-9]+$/.test(url.pathname);
  if (hasExtension) {
    event.respondWith(
      caches.match(req).then((cached) => cached || fetch(req))
    );
    return;
  }

  // ✅ Navigation requests with no extension: fallback to index.html
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).catch(() => caches.match("/index.html"))
    );
    return;
  }

  // Default: cache-first
  event.respondWith(
    caches.match(req).then((cached) => cached || fetch(req))
  );
});
