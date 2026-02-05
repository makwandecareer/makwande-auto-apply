// /assets/js/config.js

const DEFAULT_API_BASE = "https://makwande-auto-apply.onrender.com";

function getApiBase() {
  // Priority:
  // 1) LocalStorage override (Settings page)
  // 2) Cloudflare Pages env injected into build (optional)
  // 3) Default Render API
  const saved = localStorage.getItem("API_BASE");
  if (saved && saved.startsWith("http")) return saved.replace(/\/+$/, "");

  // If you inject API_BASE during build, it may be available like this:
  // (If not, it will be undefined and we fall back)
  const envBase = (window.__ENV__ && window.__ENV__.API_BASE) || null;
  if (envBase && envBase.startsWith("http")) return envBase.replace(/\/+$/, "");

  return DEFAULT_API_BASE;
}
