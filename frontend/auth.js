function getApiBase() {
    const base = localStorage.getItem("api_base");
  
    if (base && base.startsWith("http")) {
      return base.replace(/\/+$/, "");
    }
  
    // Hard fallback (Render backend)
    return "https://makwande-auto-apply.onrender.com";
  }
  