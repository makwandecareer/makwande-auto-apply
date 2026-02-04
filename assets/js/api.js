async function apiFetch(path, {
  method = "GET",
  body = null,
  auth = true,
  headers = {},
  isFormData = false,
  timeoutMs = 25000,
  retry = 1
} = {}) {
  const base = window.APP_CONFIG.API_BASE_URL.replace(/\/$/, "");
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const finalHeaders = { ...headers };

  if (!isFormData) {
    finalHeaders["Content-Type"] = finalHeaders["Content-Type"] || "application/json";
  }

  if (auth) {
    const token = localStorage.getItem(window.APP_CONFIG.STORAGE_KEYS.token);
    if (token) finalHeaders["Authorization"] = `Bearer ${token}`;
  }

  const payload = isFormData ? body : (body ? JSON.stringify(body) : null);

  try {
    const res = await fetch(url, {
      method,
      headers: finalHeaders,
      body: payload,
      signal: controller.signal
    });

    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }

    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) ? (data.detail || data.message) : `Request failed (${res.status})`;
      const err = new Error(msg);
      err.status = res.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (err) {
    if (retry > 0 && (err.name === "AbortError" || (err.status && err.status >= 500))) {
      await new Promise(r => setTimeout(r, 600));
      return apiFetch(path, { method, body, auth, headers, isFormData, timeoutMs, retry: retry - 1 });
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

const API = {
  // Auth
  signup: (payload) => apiFetch("/api/auth/signup", { method: "POST", body: payload, auth: false }),
  login:  (payload) => apiFetch("/api/auth/login",  { method: "POST", body: payload, auth: false }),
  me:     () => apiFetch("/api/auth/me"),

  // Jobs
  jobs: (params) => {
    const q = new URLSearchParams(params || {}).toString();
    return apiFetch(`/api/jobs${q ? `?${q}` : ""}`, { method: "GET" });
  },
  jobById: (jobId) => apiFetch(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "GET" }),


  applyJob: (payload) => apiFetch("/api/apply_job", { method: "POST", body: payload }),
  applications: () => apiFetch("/api/applications", { method: "GET" }),
  saveJob: (payload) => apiFetch("/api/saved_jobs", { method: "POST", body: payload }),
  savedJobs: () => apiFetch("/api/saved_jobs", { method: "GET" }),

  // AI
  revamp: (payload) => apiFetch("/api/cv/revamp", { method: "POST", body: payload }),
  coverLetter: (payload) => apiFetch("/api/cover_letter", { method: "POST", body: payload }),

  // Optional: upload CV file (if your backend supports it)
  uploadCv: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch("/api/cv/upload", { method: "POST", body: fd, isFormData: true });
  },

  // Billing
  subscriptionStatus: () => apiFetch("/api/billing/status", { method: "GET" }),
  verifyPayment: (payload) => apiFetch("/api/billing/verify", { method: "POST", body: payload }),

  // Health check
  health: () => apiFetch("/health", { method: "GET", auth: false }).catch(() => null)
};
