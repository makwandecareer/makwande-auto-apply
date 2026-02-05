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


(function () {
  const meta = document.querySelector('meta[name="api-base"]');
  const metaBase = meta ? meta.getAttribute("content") : "";

  // Priority: localStorage override > meta tag > fallback
  const fallback = "https://makwande-auto-apply.onrender.com";

  window.getApiBase = function getApiBase() {
    return (
      localStorage.getItem("API_BASE") ||
      metaBase ||
      fallback
    ).replace(/\/+$/, "");
  };
})();
