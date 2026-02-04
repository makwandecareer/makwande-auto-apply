function renderNav() {
  const root = document.getElementById("navMount");
  if (!root) return;

  const logged = isLoggedIn();
  const user = getUser();

  root.innerHTML = `
    <nav class="navbar navbar-expand-lg nav-glass sticky-top">
      <div class="container">
        <a class="navbar-brand d-flex align-items-center gap-2" href="/index.html">
          <img src="/assets/img/logo.svg" class="brand-logo" alt="logo" />
          <span class="fw-bold">${window.APP_CONFIG.APP_NAME}</span>
        </a>

        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navx">
          <span class="navbar-toggler-icon"></span>
        </button>

        <div class="collapse navbar-collapse" id="navx">
          <ul class="navbar-nav ms-auto align-items-lg-center gap-lg-2">
            <li class="nav-item"><a class="nav-link" href="/jobs.html">Jobs</a></li>
            <li class="nav-item"><a class="nav-link" href="/revamp.html">CV Revamp</a></li>
            <li class="nav-item"><a class="nav-link" href="/cover_letter.html">Cover Letter</a></li>
            <li class="nav-item"><a class="nav-link" href="/dashboard.html">Dashboard</a></li>
            <li class="nav-item"><a class="nav-link" href="/subscription.html">Subscription</a></li>
            <li class="nav-item"><a class="nav-link" href="/settings.html">Settings</a></li>
            ${
              logged
                ? `<li class="nav-item ms-lg-2">
                     <button class="btn btn-outline-light btn-sm" id="logoutBtn">Logout</button>
                   </li>`
                : `<li class="nav-item ms-lg-2"><a class="btn btn-light btn-sm" href="/login.html">Login</a></li>`
            }
          </ul>
        </div>
      </div>
    </nav>
  `;

  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) logoutBtn.addEventListener("click", logout);

  // show API base hint quickly
  const hint = document.getElementById("apiBaseHint");
  if(hint){
    hint.textContent = window.APP_CONFIG.API_BASE_URL;
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  renderNav();
  await safeMeSync();
});
