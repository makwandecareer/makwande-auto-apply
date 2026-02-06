const CACHE = "maa-cache-v2";
const ASSETS = [
  "/",
  "/index.html",
  "/login.html",
  "/signup.html",
  "/jobs.html",
  "/dashboard.html",
  "/revamp.html",
  "/cover_letter.html",
  "/subscription.html",
  "/pay.html",
  "/settings.html",
  "/offline.html",
  "/assets/css/app.css",
  "/assets/js/config.js",
  "/assets/js/api.js",
  "/assets/js/auth.js",
  "/assets/js/ui.js",
  "/assets/js/app.js",
  "/assets/js/jobs.js",
  "/assets/js/dashboard.js",
  "/assets/js/revamp.js",
  "/assets/js/cover_letter.js",
  "/assets/js/subscription.js",
  "/assets/js/pay.js",
  "/assets/img/logo.svg"
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => k !== CACHE ? caches.delete(k) : null)))
  );
});

// Network-first for API, cache-first for assets
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  if (url.pathname.startsWith("/api/") || url.pathname === "/health") {
    e.respondWith(
      fetch(e.request).catch(() => caches.match(e.request).then(r => r || caches.match("/offline.html")))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return res;
    }).catch(() => caches.match("/offline.html")))
  );
});
