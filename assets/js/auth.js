// /assets/js/auth.js

function setSession(data) {
  // data should look like: { access_token, token_type, user? }
  if (!data || !data.access_token) throw new Error("Missing access token");

  localStorage.setItem("ACCESS_TOKEN", data.access_token);
  localStorage.setItem("TOKEN_TYPE", data.token_type || "bearer");

  if (data.user) {
    localStorage.setItem("USER", JSON.stringify(data.user));
  }
}

function clearSession() {
  localStorage.removeItem("ACCESS_TOKEN");
  localStorage.removeItem("TOKEN_TYPE");
  localStorage.removeItem("USER");
}

function getToken() {
  return localStorage.getItem("ACCESS_TOKEN");
}

function authHeader() {
  const token = getToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

function isLoggedIn() {
  return !!getToken();
}

// /assets/js/auth.js

function getToken() {
  return localStorage.getItem("token");
}

function setToken(token) {
  localStorage.setItem("token", token);
}

function clearToken() {
  localStorage.removeItem("token");
}

async function login(email, password, apiBase) {
  const res = await fetch(`${apiBase}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      username: email,
      password: password
    })
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed");

  // backend returns { access_token, token_type }
  setToken(data.access_token);
  return data;
}

async function me(apiBase) {
  const token = getToken();
  if (!token) throw new Error("No token found");

  const res = await fetch(`${apiBase}/api/auth/me`, {
    headers: { Authorization: "Bearer " + token }
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Auth check failed");
  return data;
}

// Protect page: redirect to login if no token
function requireAuth() {
  const token = getToken();
  if (!token) {
    const next = encodeURIComponent(window.location.pathname);
    window.location.href = `/login.html?next=${next}`;
  }
}

(function () {
  const TOKEN_KEY = "token";

  function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  }

  // If not logged in, redirect to login page
  function requireAuth() {
    const t = getToken();
    if (!t) {
      window.location.href = "/login.html";
      return false;
    }
    return true;
  }

  // On 401, clear and redirect
  function handleAuthError(err) {
    if (err && err.status === 401) {
      clearToken();
      window.location.href = "/login.html?next=/dashboard.html";
      return true;
    }
    return false;
  }

  window.Auth = {
    setToken,
    getToken,
    clearToken,
    requireAuth,
    handleAuthError,
  };
})();
