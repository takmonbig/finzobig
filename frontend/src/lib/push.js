import { api } from "@/lib/api";

const LATER_KEY = "push_later_at";
export const supported = () => "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
export const permission = () => (supported() ? Notification.permission : "unsupported");
export const laterActive = () => Date.now() - Number(localStorage.getItem(LATER_KEY) || 0) < 3 * 3600 * 1000;

export function remindLater() {
  localStorage.setItem(LATER_KEY, String(Date.now()));
  return api.post("/push/permission", { state: "later" });
}

function b64ToBytes(v) {
  const pad = "=".repeat((4 - (v.length % 4)) % 4);
  const raw = atob((v + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export async function enablePush() {
  if (!supported()) {
    await api.post("/push/permission", { state: "unsupported" });
    throw new Error("This browser does not support push notifications");
  }
  if (Notification.permission === "denied") throw new Error("Notifications are blocked in your browser settings");
  const perm = await Notification.requestPermission();
  await api.post("/push/permission", { state: perm });
  if (perm !== "granted") throw new Error("Notification permission was not granted");
  const reg = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;
  const { data } = await api.get("/push/public-key");
  let sub = await reg.pushManager.getSubscription();
  if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(data.publicKey) });
  await api.post("/push/subscribe", sub.toJSON());
  return sub;
}

export async function disablePush() {
  if (!supported()) return;
  const reg = await navigator.serviceWorker.getRegistration("/sw.js");
  const sub = await reg?.pushManager.getSubscription();
  if (!sub) return;
  await api.post("/push/unsubscribe", sub.toJSON());
  await sub.unsubscribe();
}
