// auth.js

function getApiBase() {
    return window.API_BASE || "https://makwande-auto-apply.onrender.com";
  }
  
  async function login(email, password) {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);
  
    const res = await fetch(`${getApiBase()}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: formData
    });
  
    if (!res.ok) {
      throw new Error("Login failed");
    }
  
    const data = await res.json();
  
    // Save token
    localStorage.setItem("access_token", data.access_token);
  
    return data;
  }
  