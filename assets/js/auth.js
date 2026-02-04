function setSession({ token, user }) {
  if (token) localStorage.setItem(window.APP_CONFIG.STORAGE_KEYS.token, token);
  if (user) localStorage.setItem(window.APP_CONFIG.STORAGE_KEYS.user, JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem(window.APP_CONFIG.STORAGE_KEYS.token);
  localStorage.removeItem(window.APP_CONFIG.STORAGE_KEYS.user);
}

function getUser() {
  const raw = localStorage.getItem(window.APP_CONFIG.STORAGE_KEYS.user);
  try { return raw ? JSON.parse(raw) : null; } catch { return null; }
}

function isLoggedIn() {
  return !!localStorage.getItem(window.APP_CONFIG.STORAGE_KEYS.token);
}

function requireAuth() {
  if (!isLoggedIn()) {
    const next = encodeURIComponent(window.location.pathname);
    window.location.href = `/login.html?next=${next}`;
  }
}

function logout() {
  clearSession();
  window.location.href = "/login.html";
}
