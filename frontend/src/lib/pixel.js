let loaded = false;
let pixels = [];

export function initPixels(list) {
  if (loaded || !list?.length) return;
  loaded = true;
  pixels = list;
  /* eslint-disable */
  !function (f, b, e, v, n, t, s) { if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
    if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = "2.0"; n.queue = []; t = b.createElement(e); t.async = !0; t.src = v;
    s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s); }(window, document, "script", "https://connect.facebook.net/en_US/fbevents.js");
  /* eslint-enable */
  list.forEach((p) => window.fbq("init", p.pixel_id));
}

export function track(event, params) {
  if (!window.fbq) return;
  pixels.forEach((p) => { if (p.events.includes(event)) window.fbq("trackSingle", p.pixel_id, event, params || {}); });
}

export const pixelStatus = () => ({ loaded, scriptReady: !!(window.fbq && window.fbq.loaded), ids: pixels.map((p) => p.pixel_id) });
