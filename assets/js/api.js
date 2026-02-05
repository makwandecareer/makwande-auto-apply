/ assets/js/api.js

(function () {
  const DEFAULT_TIMEOUT_MS = 20000;

  function withTimeout(promise, timeoutMs = DEFAULT_TIMEOUT_MS) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    const wrapped = Promise.resolve(promise(controller.signal))
      .finally(() => clearTimeout(timer));

    return wrapped;
  }

  async function parseResponse(res) {
    const contentType = res.headers.get("content-type") || "";
    let body = null;

    if (contentType.includes("application/json")) {
      body = await res.json().catch(() => null);
    } else {
      body = await res.text().catch(() => null);
    }

    if (!res.ok) {
      const msg =
        (body && body.detail) ||
        (typeof body === "string" && body) ||
        `Request failed (${res.status})`;
      const err = new Error(msg);
      err.status = res.status;
      err.body = body;
      throw err;
    }
    return body;
  }

  function getToken() {
    return localStorage.getItem("token") || "";
  }

  async function request(path, options = {}) {
    const url = `${getApiBase()}${path.startsWith("/") ? "" : "/"}${path}`;
    const token = getToken();

    return withTimeout(async (signal) => {
      const headers = new Headers(options.headers || {});
      // For JSON calls
      if (!headers.has("Content-Type") && options.body && typeof options.body === "string") {
        headers.set("Content-Type", "application/json");
      }
      if (token) headers.set("Authorization", `Bearer ${token}`);

      const res = await fetch(url, {
        ...options,
        headers,
        signal,
      });

      return parseResponse(res);
    }, options.timeoutMs || DEFAULT_TIMEOUT_MS);
  }

  // Special: login uses x-www-form-urlencoded
  async function login(email, password) {
    const url = `${getApiBase()}/api/auth/login`;
    const payload = new URLSearchParams({
      username: email,
      password: password,
    });

    return withTimeout(async (signal) => {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: payload.toString(),
        signal,
      });
      return parseResponse(res);
    });
  }

  async function signup(full_name, email, password) {
    return request("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ full_name, email, password }),
    });
  }

  window.API = {
    request,
    login,
    signup,

    me: () => request("/api/auth/me", { method: "GET" }),

    listApplications: () => request("/jobs/applications", { method: "GET" }),
    updateApplicationStatus: (application_id, status) =>
      request("/jobs/applications/status", {
        method: "POST",
        body: JSON.stringify({ application_id, status }),
      }),

    plans: () => request("/billing/plans", { method: "GET" }),
  };
})();
