// /assets/js/api.js
(() => {
  function base() {
    return (window.getApiBase ? window.getApiBase() : "").replace(/\/+$/, "");
  }

  async function request(path, opts = {}) {
    const url = base() + path;

    const headers = Object.assign(
      { "Accept": "application/json" },
      opts.headers || {}
    );

    const token = window.Auth?.getToken?.();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    // JSON body helper
    if (opts.json) {
      headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.json);
      delete opts.json;
    }

    const res = await fetch(url, { ...opts, headers });

    // Handle non-JSON safely
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }

    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) ? (data.detail || data.message) : `HTTP ${res.status}`;
      throw new Error(msg);
    }

    return data;
  }

  const API = {
    // ✅ Permanent: use users/me as the canonical current user endpoint
    me: () => request("/api/users/me", { method: "GET" }),

    // Optional health
    health: () => request("/health", { method: "GET" }),

    // Your existing endpoints (examples)
    jobs: (params = "") => request("/api/jobs" + params, { method: "GET" }),
  };

  window.API = API;
})();
