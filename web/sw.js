/* Caches the app shell so it opens instantly and offline. API responses (health data) are never cached. */
const SHELL = "riaya-shell-v22";
const FILES = ["/", "/index.html", "/chat.html", "/fabric.html", "/partner.html", "/css/app.css?v=2", "/css/premium.css?v=8", "/js/common.js?v=2", "/js/i18n.js?v=2",
  "/js/app.js?v=9", "/js/lock.js?v=2", "/js/disguise.js?v=1", "/calc.html", "/manifest-calc.webmanifest", "/icons/calc-192.png", "/icons/apple-touch-icon.png", "/js/wellbeing.js?v=1", "/js/connect.js?v=1", "/js/scan.js?v=2", "/js/watch.js?v=1", "/js/companion.js?v=7", "/js/forecast.js?v=2", "/js/sharepreview.js?v=1", "/js/tour.js?v=9", "/js/chat.js?v=8", "/js/nlu.js?v=5", "/js/voice.js?v=4", "/manifest.webmanifest", "/icons/icon-192.png",
  "/fonts/ibm-plex-sans-latin-400-normal.woff2", "/fonts/ibm-plex-sans-arabic-arabic-400-normal.woff2", "/fonts/noto-kufi-arabic-arabic-500-normal.woff2"];
self.addEventListener("install", e => e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== SHELL).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(SHELL).then(c => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request)));
});
