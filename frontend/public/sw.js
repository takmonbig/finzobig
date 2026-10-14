const CACHE = "finzo-offline-v1";
self.addEventListener("install", (e) => { self.skipWaiting(); e.waitUntil(caches.open(CACHE).then((c) => c.addAll(["/offline.html", "/img/logo.png", "/img/favicon-192.png"]))); });
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.mode === "navigate") e.respondWith(fetch(e.request).catch(() => caches.match("/offline.html")));
  else if (u.origin === self.location.origin && ["/img/logo.png", "/img/favicon-192.png"].includes(u.pathname)) e.respondWith(fetch(e.request).catch(() => caches.match(u.pathname)));
});

function safe(url) {
  try {
    const u = new URL(url || "/app/notifications", self.location.origin);
    return ["http:", "https:"].includes(u.protocol) ? u.href : self.location.origin + "/app/notifications";
  } catch (_) {
    return self.location.origin + "/app/notifications";
  }
}

self.addEventListener("push", (event) => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch (_) { d = { body: event.data && event.data.text() }; }
  const opts = { body: d.body || "", icon: "/img/favicon-192.png", data: { url: safe(d.url), nid: d.nid }, tag: d.nid || "app-notification" };
  if (d.image) opts.image = d.image;
  event.waitUntil(self.registration.showNotification(d.title || "Notification", opts));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const { url, nid } = event.notification.data || {};
  const track = nid ? fetch(`/api/notifications/${nid}/click`, { method: "POST", credentials: "include" }).catch(() => {}) : Promise.resolve();
  event.waitUntil(Promise.all([track, self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
    const same = list.find((c) => c.url === url);
    return same ? same.focus() : self.clients.openWindow(url);
  })]));
});
