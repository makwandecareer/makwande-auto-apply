// /assets/js/api.js

async function request(path, { method = "GET", headers = {}, body = null } = {}) {
  const base = getApiBase();
  const url = `${base}${path}`;

  const res = await fetch(url, {
    method,
    headers: {
      ...headers,
      ...authHeader(),
    },
    body,
  });

  // Try parse JSON when possible
  const contentType = res.headers.get("content-type") || "";
  let data = null;

  if (contentType.includes("application/json")) {
    data = await res.json().catch(() => null);
  } else {
    const text = await res.text().catch(() => "");
    data = text ? { detail: text } : null;
  }

  if (!res.ok) {
    const msg =
      (data && (data.detail || data.message)) ||
      `Request failed (${res.status})`;
    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}

const API = {
  // ✅ SIGNUP (JSON)
  async signup({ email, password, full_name }) {
    return await request("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json", accept: "application/json" },
      body: JSON.stringify({
        email,
        password,
        full_name: full_name || "",
      }),
    });
  },

  // ✅ LOGIN (OAuth2 password flow: x-www-form-urlencoded)
  async login({ email, password }) {
    const form = new URLSearchParams();
    form.append("username", email); // OAuth2PasswordRequestForm uses "username"
    form.append("password", password);

    const tokenRes = await request("/api/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        accept: "application/json",
      },
      body: form.toString(),
    });

    // tokenRes = { access_token, token_type }
    // Optional: fetch current user
    let user = null;
    try {
      localStorage.setItem("ACCESS_TOKEN", tokenRes.access_token);
      localStorage.setItem("TOKEN_TYPE", tokenRes.token_type || "bearer");
      user = await API.me();
    } catch (_) {
      // If /me not available yet, ignore
    }

    // Return combined object for setSession()
    return {
      access_token: tokenRes.access_token,
      token_type: tokenRes.token_type || "bearer",
      user,
    };
  },

  // ✅ ME (Bearer protected)
  async me() {
    return await request("/api/auth/me", {
      method: "GET",
      headers: { accept: "application/json" },
    });
  },
};
