// assets/js/dashboard.js

(async function () {
  if (!Auth.requireAuth()) return;

  // ===== Elements
  const elUserName = document.getElementById("userName");
  const elUserEmail = document.getElementById("userEmail");
  const elLastSync = document.getElementById("lastSync");

  const elStatApps = document.getElementById("statApps");
  const elAppsMeta = document.getElementById("appsMeta");
  const elStatQueue = document.getElementById("statQueue");
  const elStatPlan = document.getElementById("statPlan");
  const elPlanMeta = document.getElementById("planMeta");

  const btnLogout = document.getElementById("btnLogout");
  const btnRefresh = document.getElementById("btnRefresh");
  const btnExport = document.getElementById("btnExport");

  // Auto-apply
  const jobQuery = document.getElementById("jobQuery");
  const jobCountry = document.getElementById("jobCountry");
  const btnSearchJobs = document.getElementById("btnSearchJobs");
  const jobResults = document.getElementById("jobResults");

  const queueList = document.getElementById("queueList");
  const queueMeta = document.getElementById("queueMeta");
  const btnRunAuto = document.getElementById("btnRunAuto");
  const btnClearQueue = document.getElementById("btnClearQueue");

  // Applications
  const tbody = document.getElementById("appsTbody");
  const elAppsCount = document.getElementById("appsCount");
  const btnPrev = document.getElementById("btnPrev");
  const btnNext = document.getElementById("btnNext");

  // ===== State
  let user = null;
  let applications = [];
  let filtered = [];
  let page = 1;
  const pageSize = 8;

  // ===== Queue (localStorage, safe for now)
  const QUEUE_KEY = "AUTO_APPLY_QUEUE_V1";

  function loadQueue() {
    try { return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]"); }
    catch { return []; }
  }
  function saveQueue(q) {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
    renderQueue();
  }

  function nowText() {
    return new Date().toLocaleString();
  }

  function setLoadingTable() {
    tbody.innerHTML = `
      <tr><td colspan="6">
        <div class="p-3 skeleton glass">Loading applications securely from API…</div>
      </td></tr>
    `;
  }

  function statusBadge(status) {
    const map = { Draft:"secondary", Applied:"primary", Interview:"warning", Offer:"success", Rejected:"danger" };
    const cls = map[status] || "secondary";
    return `<span class="badge text-bg-${cls}">${UI.escapeHtml(status)}</span>`;
  }

  function normalizeApp(app) {
    return {
      application_id: app.application_id || app.id || "",
      job_id: app.job_id || "",
      job_title: app.job_title || app.title || "",
      company: app.company || "",
      location: app.location || "",
      job_url: app.job_url || "",
      status: app.status || "Draft",
      notes: app.notes || "",
    };
  }

  function renderApps() {
    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    if (page > totalPages) page = totalPages;

    const start = (page - 1) * pageSize;
    const slice = filtered.slice(start, start + pageSize);

    elStatApps.textContent = String(applications.length);
    elAppsCount.textContent = `Showing ${slice.length} of ${total} • Page ${page}/${totalPages}`;

    if (!slice.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-3 muted">No applications yet. Use Auto Apply Center to create them.</td></tr>`;
      return;
    }

    tbody.innerHTML = slice.map(a => {
      const id = UI.escapeHtml(a.application_id);
      return `
        <tr>
          <td>
            <div class="fw-semibold">${UI.escapeHtml(a.job_title || "—")}</div>
            <div class="small muted mono">${id}</div>
          </td>
          <td>${UI.escapeHtml(a.company || "—")}</td>
          <td>${UI.escapeHtml(a.location || "—")}</td>
          <td>${statusBadge(a.status)}</td>
          <td class="small">${UI.escapeHtml(a.notes || "")}</td>
          <td>
            <div class="d-flex gap-2 flex-wrap">
              <select class="form-select form-select-sm" data-action="status" data-id="${id}">
                ${["Draft","Applied","Interview","Offer","Rejected"].map(s => `<option ${a.status===s?"selected":""}>${s}</option>`).join("")}
              </select>
              <button class="btn btn-soft btn-sm" data-action="save" data-id="${id}">Save</button>
            </div>
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll("[data-action='save']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        const sel = tbody.querySelector(`[data-action="status"][data-id="${CSS.escape(id)}"]`);
        const newStatus = sel ? sel.value : "Draft";

        btn.disabled = true; btn.textContent = "Saving…";
        try {
          await API.updateApplicationStatus(id, newStatus);
          const idx = applications.findIndex(x => x.application_id === id);
          if (idx >= 0) applications[idx].status = newStatus;
          applyAppFilters();
          UI.showAlert("success", "Status updated.");
          setTimeout(UI.clearAlert, 1500);
        } catch (err) {
          if (Auth.handleAuthError(err)) return;
          UI.showAlert("danger", err.message || "Failed to update status.");
        } finally {
          btn.disabled = false; btn.textContent = "Save";
        }
      });
    });

    btnPrev.disabled = page <= 1;
    btnNext.disabled = page >= totalPages;
  }

  function applyAppFilters() {
    // For now: no UI filters on this page; keep it simple & clean like LiveCareer sections
    filtered = applications.slice();
    page = 1;
    renderApps();
  }

  // ===== Auto Apply UI
  function renderQueue() {
    const q = loadQueue();
    elStatQueue.textContent = String(q.length);
    queueMeta.textContent = `Updated: ${nowText()}`;

    if (!q.length) {
      queueList.innerHTML = `<div class="muted small">Queue is empty. Search jobs and add them to the queue.</div>`;
      return;
    }

    queueList.innerHTML = q.map((j, idx) => `
      <div class="glass p-2 mb-2 d-flex justify-content-between align-items-center">
        <div>
          <div class="fw-semibold">${UI.escapeHtml(j.job_title || "—")}</div>
          <div class="small muted">${UI.escapeHtml(j.company || "—")} • ${UI.escapeHtml(j.location || "—")}</div>
        </div>
        <button class="btn btn-danger btn-sm" data-remove="${idx}">Remove</button>
      </div>
    `).join("");

    queueList.querySelectorAll("[data-remove]").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = Number(btn.getAttribute("data-remove"));
        const copy = loadQueue();
        copy.splice(idx, 1);
        saveQueue(copy);
      });
    });
  }

  async function searchJobs() {
    const q = (jobQuery.value || "").trim();
    const country = jobCountry.value || "South Africa";
    if (!q) {
      UI.showAlert("warning", "Type a job title first (e.g. HR Officer).");
      return;
    }

    jobResults.innerHTML = `<div class="p-2 skeleton glass">Searching…</div>`;

    try {
      const res = await API.request(`/jobs/search?q=${encodeURIComponent(q)}&country=${encodeURIComponent(country)}`, { method: "GET" });

      // Backend currently returns placeholder; we support both placeholder + real array
      const jobs = Array.isArray(res) ? res : (res.jobs || []);
      if (!jobs.length) {
        jobResults.innerHTML = `<div class="muted small">No results returned yet. Next step is to connect real job sources.</div>`;
        return;
      }

      jobResults.innerHTML = jobs.map((j, i) => `
        <div class="glass p-3 mb-2">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <div class="fw-semibold">${UI.escapeHtml(j.job_title || j.title || "Job")}</div>
              <div class="small muted">${UI.escapeHtml(j.company || "Company")} • ${UI.escapeHtml(j.location || country)}</div>
              <div class="small muted">${UI.escapeHtml(j.job_url || j.url || "")}</div>
            </div>
            <button class="btn btn-success btn-sm" data-queue="${i}">Queue</button>
          </div>
        </div>
      `).join("");

      jobResults.querySelectorAll("[data-queue]").forEach(btn => {
        btn.addEventListener("click", () => {
          const idx = Number(btn.getAttribute("data-queue"));
          const picked = jobs[idx];

          const item = {
            job_id: picked.job_id || picked.id || picked.job_url || picked.url || `${Date.now()}`,
            job_title: picked.job_title || picked.title || "Job",
            company: picked.company || "",
            location: picked.location || country,
            job_url: picked.job_url || picked.url || "",
            notes: "Queued by Auto Apply Center",
          };

          const qNow = loadQueue();
          // avoid duplicates by job_id
          if (qNow.some(x => x.job_id === item.job_id)) {
            UI.showAlert("info", "Already in queue.");
            return;
          }
          qNow.unshift(item);
          saveQueue(qNow);
          UI.showAlert("success", "Added to queue.");
          setTimeout(UI.clearAlert, 1200);
        });
      });

    } catch (err) {
      if (Auth.handleAuthError(err)) return;
      jobResults.innerHTML = "";
      UI.showAlert("danger", err.message || "Job search failed.");
    }
  }

  async function runAutoApply() {
    const q = loadQueue();
    if (!q.length) {
      UI.showAlert("info", "Queue is empty.");
      return;
    }

    btnRunAuto.disabled = true;
    btnRunAuto.textContent = "Running…";

    UI.showAlert("info", `Auto applying to ${q.length} queued job(s)…`);

    const successes = [];
    const failures = [];

    for (const job of q) {
      try {
        await API.request("/jobs/apply", {
          method: "POST",
          body: JSON.stringify({
            job_id: String(job.job_id || ""),
            job_title: String(job.job_title || ""),
            company: String(job.company || ""),
            location: String(job.location || ""),
            job_url: String(job.job_url || ""),
            notes: String(job.notes || ""),
            status: "Applied",
          }),
        });
        successes.push(job);
      } catch (err) {
        failures.push({ job, err: err.message || "Failed" });
      }
    }

    // Remove successfully applied from queue, keep failures
    const remaining = q.filter(j => !successes.some(s => s.job_id === j.job_id));
    saveQueue(remaining);

    // Reload applications tracker
    await loadApplications();

    if (failures.length) {
      UI.showAlert("warning", `Auto Apply complete: ${successes.length} success, ${failures.length} failed. (Some job entries may be missing required fields).`);
    } else {
      UI.showAlert("success", `Auto Apply complete: ${successes.length} applied ✅`);
    }

    btnRunAuto.disabled = false;
    btnRunAuto.textContent = "Run Auto Apply";
  }

  // ===== Loaders
  async function loadUser() {
    user = await API.me();
    elUserName.textContent = user.full_name || "User";
    elUserEmail.textContent = user.email || "";
  }

  async function loadPlans() {
    const data = await API.plans();
    elStatPlan.textContent = "Pro";
    elPlanMeta.textContent = `${data.currency} • Plans loaded`;
  }

  async function loadApplications() {
    setLoadingTable();
    const raw = await API.listApplications();
    applications = Array.isArray(raw) ? raw.map(normalizeApp) : [];
    elAppsMeta.textContent = `Updated: ${nowText()}`;
    elLastSync.textContent = nowText();
    applyAppFilters();
  }

  // ===== Events
  function wireEvents() {
    btnLogout.addEventListener("click", () => {
      Auth.clearToken();
      window.location.href = "/login.html";
    });

    btnRefresh.addEventListener("click", async () => {
      UI.clearAlert();
      try {
        await boot();
        UI.showAlert("success", "Dashboard refreshed.");
        setTimeout(UI.clearAlert, 1200);
      } catch (err) {
        if (Auth.handleAuthError(err)) return;
        UI.showAlert("danger", err.message || "Refresh failed.");
      }
    });

    btnExport.addEventListener("click", () => {
      const rows = filtered.map(a => ({
        application_id: a.application_id,
        job_title: a.job_title,
        company: a.company,
        location: a.location,
        status: a.status,
        notes: a.notes,
      }));
      const csv = UI.toCsv(rows, ["application_id","job_title","company","location","status","notes"]);
      UI.downloadFile(`applications_${new Date().toISOString().slice(0,10)}.csv`, csv);
    });

    btnPrev.addEventListener("click", () => { page = Math.max(1, page - 1); renderApps(); });
    btnNext.addEventListener("click", () => { page = page + 1; renderApps(); });

    btnSearchJobs.addEventListener("click", searchJobs);
    btnRunAuto.addEventListener("click", runAutoApply);
    btnClearQueue.addEventListener("click", () => {
      saveQueue([]);
      UI.showAlert("info", "Queue cleared.");
      setTimeout(UI.clearAlert, 1000);
    });
  }

  async function boot() {
    renderQueue();
    await loadUser();
    await loadPlans();
    await loadApplications();
  }

  // ===== Start
  try {
    wireEvents();
    await boot();
  } catch (err) {
    if (Auth.handleAuthError(err)) return;
    UI.showAlert("danger", err.message || "Failed to load dashboard.");
  }
})();
