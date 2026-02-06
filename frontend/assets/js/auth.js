// /assets/js/auth.js
(() => {
  const STORAGE_KEYS = window.STORAGE_KEYS || { TOKEN: "token", USER: "user" };

  function getToken() {
    try { return localStorage.getItem(STORAGE_KEYS.TOKEN); } catch { return null; }
  }

  function setToken(token) {
    try { localStorage.setItem(STORAGE_KEYS.TOKEN, token); } catch {}
  }

  function clearAuth() {
    try {
      localStorage.removeItem(STORAGE_KEYS.TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USER);
    } catch {}
  }

  function isLoggedIn() {
    return !!getToken();
  }

  function requireAuth() {
    if (!isLoggedIn()) window.location.href = "login.html";
  }

  window.Auth = { getToken, setToken, clearAuth, isLoggedIn, requireAuth };
})();
