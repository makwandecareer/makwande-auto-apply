// /assets/js/config.js

(() => {
  // 1) Default backend (Render)
  const DEFAULT_API_BASE = "https://makwande-auto-apply.onrender.com";

  // 2) Standard storage keys used across the whole frontend
  const STORAGE_KEYS = {
    TOKEN: "token",
    USER: "user",
    API_BASE: "API_BASE",      // keep your existing key name
    JOBS_CACHE: "jobs_cache",
    MATCHED_JOBS: "matched_jobs"
  };

  // 3) Optional meta tag override: <meta name="api-base" content="...">
  const meta = document.querySelector('meta[name="api-base"]');
  const metaBase = meta ? meta.getAttribute("content") : "";

  // 4) Optional injected env: window.__ENV__.API_BASE
  const envBase = (window.__ENV__ && window.__ENV__.API_BASE) ? window.__ENV__.API_BASE : "";

  function normalizeBase(u) {
    return (u || "").trim().replace(/\/+$/, "");
  }

  // Priority: localStorage override -> meta tag -> window.__ENV__ -> default
  function getApiBase() {
    let saved = "";
    try { saved = localStorage.getItem(STORAGE_KEYS.API_BASE) || ""; } catch {}
    const base =
      (saved && saved.startsWith("http") ? saved : "") ||
      (metaBase && metaBase.startsWith("http") ? metaBase : "") ||
      (envBase && envBase.startsWith("http") ? envBase : "") ||
      DEFAULT_API_BASE;

    return normalizeBase(base);
  }

  // Expose globally (so all scripts can use it)
  window.APP_CONFIG = { DEFAULT_API_BASE };
  window.STORAGE_KEYS = STORAGE_KEYS;
  window.getApiBase = getApiBase;
})();
