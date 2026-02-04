/**
 * Advanced API config:
 * - If user saved an API base URL in Settings, use it.
 * - Else, try same-origin /api (works when frontend is served behind a reverse proxy).
 * - Else, fall back to a placeholder that you can replace at deploy time.
 */
(function(){
  const STORAGE_KEY = "maa_api_base_url";

  function normalize(url){
    if(!url) return "";
    return url.replace(/\/+$/,"");
  }

  function getDefault(){
    // Try same-origin assumption (frontend + backend share domain)
    // Example: https://makwandecareer.co.za -> https://makwandecareer.co.za
    // And API routes are /api/...
    return normalize(window.location.origin);
  }

  const saved = normalize(localStorage.getItem(STORAGE_KEY));
  const base = saved || getDefault() || "https://YOUR-LIVE-API-DOMAIN";
  window.APP_CONFIG = {
    API_BASE_URL: base,
    APP_NAME: "Makwande Auto Apply",
    STORAGE_KEYS: {
      token: "maa_token",
      user: "maa_user",
      apiBase: STORAGE_KEY
    },
    DEFAULT_PAGE_SIZE: 20
  };
})();
