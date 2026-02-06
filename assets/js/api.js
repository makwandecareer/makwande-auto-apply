// /assets/js/api.js
(() => {
  const STORAGE_KEYS = window.STORAGE_KEYS || { TOKEN: "token" };

  function getBase() {
    const fallback = "https://makwande-auto-apply.onrender.com";
    const b = (window.getApiBase ? window.getApiBase() : fallback) || fallback;
    return String(b).trim().replace(/\/+$/, "");
  }

  function getToken() {
    try { return localStorage.getItem(STORAGE_KEYS.TOKEN) || ""; } catch { return ""; }
  }

  async function request(path, opts = {}) {
    const url = getBase() + path;

    const headers = Object.assign(
      { "Accept": "application/json" },
      opts.headers || {}
    );

    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    if (opts.json) {
      headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.json);
      delete opts.json;
    }

    const res = await fetch(url, { ...opts, headers });

    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }

    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) ? (data.detail || data.message) : `HTTP ${res.status}`;
      throw new Error(msg);
    }

    return data;
  }

  // ✅ ONE source of truth: AUTH “me”
  window.API = {
    health: () => request("/health", { method: "GET" }),

    // ✅ This is the working one in your Swagger screenshot
    me: () => request("/api/auth/me", { method: "GET" }),

    // keep others if you already use them
    jobs: (qs = "") => request("/api/jobs" + qs, { method: "GET" }),
  };
})();
