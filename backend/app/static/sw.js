// Service Worker: App-Gerüst offline, Daten "erst Netz, sonst letzter Stand".
// Bei Änderungen an index.html, Schriften oder Icons VERSION hochzählen.
const VERSION = "v1";
const SHELL = `shell-${VERSION}`;
const DATA = "data";
const SHELL_FILES = [
  "/",
  "/manifest.webmanifest",
  "/static/fonts/bricolage-grotesque-latin.woff2",
  "/static/fonts/caveat-latin.woff2",
  "/static/icons/icon-192.png",
  "/static/icons/apple-touch-icon.png",
];
const DATA_URLS = ["/api/fridge", "/api/shopping", "/api/receipts"];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== SHELL && k !== DATA).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

const NETWORK_TIMEOUT_MS = 4000;

function withTimeout(promise, ms) {
  return Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms))]);
}

self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin) return;

  if (DATA_URLS.includes(url.pathname)) {
    // Erst Netz (max. 4 s, im Markt ist das Netz oft zäh), sonst der zuletzt
    // geladene Stand, markiert per Header X-Offline.
    const network = fetch(event.request).then(res => {
      if (res.ok) {
        const copy = res.clone();
        caches.open(DATA).then(c => c.put(url.pathname, copy));
      }
      return res;
    });
    event.respondWith(
      withTimeout(network, NETWORK_TIMEOUT_MS).catch(async () => {
        const cached = await caches.match(url.pathname, { cacheName: DATA });
        if (!cached) return network; // nichts gespeichert: doch aufs Netz warten
        const headers = new Headers(cached.headers);
        headers.set("X-Offline", "1");
        return new Response(cached.body, { status: 200, headers });
      })
    );
    return;
  }

  if (url.pathname === "/" || url.pathname.startsWith("/static/") || url.pathname === "/manifest.webmanifest") {
    // Gerüst: sofort aus dem Cache, im Hintergrund auffrischen.
    const update = fetch(event.request).then(res => {
      if (res.ok) {
        const copy = res.clone();
        caches.open(SHELL).then(c => c.put(event.request, copy));
      }
      return res;
    });
    event.waitUntil(update.catch(() => {}));
    event.respondWith(caches.match(event.request, { cacheName: SHELL }).then(hit => hit || update));
  }
});
