import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API, withCredentials: true });

let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const cfg = err.config || {};
    const url = cfg.url || "";
    if (err.response?.status === 401 && !cfg._retry && !url.includes("/auth/refresh") && !url.includes("/auth/login")) {
      cfg._retry = true;
      refreshing = refreshing || api.post("/auth/refresh").finally(() => { refreshing = null; });
      try {
        await refreshing;
        return api(cfg);
      } catch (e) {
        window.dispatchEvent(new Event("auth:expired"));
      }
    }
    return Promise.reject(err);
  }
);

export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (d == null) return e?.message || "Something went wrong. Please try again.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => (x?.msg ? `${x.loc?.slice(-1)[0] || ""}: ${x.msg}` : JSON.stringify(x))).join(" ");
  return d.msg || String(d);
}

export const coins = (minor, d = 2) => ((minor || 0) / 100).toLocaleString("en-IN", { maximumFractionDigits: d });
export const fdate = (s) => (s ? new Date(s).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—");
export const newKey = () => (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random()).replace(/-/g, "").slice(0, 32);

const ALLOWED = ["image/jpeg", "image/png", "image/webp"];

export function validateImage(file, maxMb = 5) {
  if (!file) return "Please choose a file";
  if (!ALLOWED.includes(file.type)) return "Only JPG, PNG or WEBP images are allowed";
  if (file.size > maxMb * 1024 * 1024) return `File must be under ${maxMb} MB`;
  return null;
}

export async function uploadImage(file, sigPath, sigBody, onProgress) {
  const bad = validateImage(file, sigPath.includes("admin") ? 8 : 5);
  if (bad) throw new Error(bad);
  const { data: sig } = await api.post(sigPath, sigBody);
  const form = new FormData();
  form.append("file", file);
  form.append("api_key", sig.api_key);
  form.append("timestamp", sig.timestamp);
  form.append("signature", sig.signature);
  form.append("folder", sig.folder);
  form.append("allowed_formats", sig.allowed_formats);
  const res = await axios.post(`https://api.cloudinary.com/v1_1/${sig.cloud_name}/image/upload`, form, {
    onUploadProgress: (p) => onProgress && p.total && onProgress(Math.round((p.loaded * 100) / p.total)),
  });
  return { public_id: res.data.public_id, secure_url: res.data.secure_url };
}

export function downloadCsv(path, filename) {
  return api.get(path, { responseType: "blob" }).then((r) => {
    const url = URL.createObjectURL(r.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  });
}
