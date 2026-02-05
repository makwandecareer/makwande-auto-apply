// assets/js/dashboard.js

(async function () {
  // Protect route
  if (!Auth.requireAuth()) return;

  // UI elements
  const elUserName = document.getElementById("userName");
  const elUserEmail = document.getElementById("userEmail");
  const elStatApps = document.getElementById("statApps");
  const elStatSaved = document.getElementById("statSaved");
  const elStatPlan = document.getElementById("statPlan");
  const elAppsMeta = document.getElementById("appsMeta");
  const elPlanMeta = document.getElementById("planMeta");
  const elLastSync = document.getElementById("lastSync");

  const tbody = document.getElementById("appsTbody");
  const elAppsCount = document.getElementById("appsCount");

  const qSearch = document.getElementById("qSearch");
  const qStatus = document.getElementById("qStatus");
  const qSort = document.getElementById("qSort");

  const btnLogout = document.getElementById("btnLogout");
  const btnRefresh = document.getElementById("btnRefresh");
  const btnExport = document.getElementById("btnExport");
  const btnPrev = document.getElementById("btnPrev");
  const btnNext = document.getElementById("btnNext");

  // State
  let user = null;
  let applications = [];
  let filtered = [];
  let page = 1;
  const pageSize = 8;

  function setLoadingTable(isLoading) {
    if (!tbody) return;
    if (isLoading) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6">
            <div class="p-3 skeleton glass">Loading applications securely from API…</div>
          </td>
        </tr>
      `;
    }
  }

  function normalizeApp(app) {
    // Your backend structure may differ; normalize gracefully
    return {
      application_id: app.application_id || app.id || "",
      job_title: app.job_title || app.title || "",
      company: app.company || "",
      location: app.location || "",
      status: app.status || "Draft",
      notes: app.notes || "",
    };
  }

  function applyFilters() {
    const s = (qSearch.value || "").trim().toLowerCase();
    const st = qStatus.value || "";
    const sort = qSort.value || "newest";

    let list = applications.slice();

    if (s) {
      list = list.filter((a) => {
        const blob = `${a.job_title} ${a.company} ${a.location} ${a.notes}`.toLowerCase();
        return blob.includes(s);
      });
    }

    if (st) {
      list = list.filter((a) => a.status === st);
    }

    // Sorting
    if (sort === "company") list.sort((a, b) => a.company.localeCompare(b.company));
    if (sort === "title") list.sort((a, b) => a.job_title.localeCompare(b.job_title));

    // newest/oldest only possible if backend gives dates; otherwise keep stable
    filtered = list;
    page = 1;
    render();
  }

  function statusBadge(status) {
    const map = {
      Draft: "secondary",
      Applied: "primary",
      Interview: "warning",
      Offer: "success",
      Rejected: "danger",
    };
    const cls = map[status] || "secondary";
    return `<span class="badge text-bg-${cls}">${UI.escapeHtml(status)}</span>`;
  }

  function render() {
    UI.clearAlert();

    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    if (page > totalPages) page = totalPages;

    const start = (page - 1) * pageSize;
    const slice = filtered.slice(start, start + pageSize);

    elAppsCount.textContent = `Showing ${slice.length} of ${total} applications • Page ${page}/${totalPages}`;
    elStatApps.textContent = String(applications.length);

    if (!slice.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="p-3 muted">
            No applications found. Apply to a job to see it here.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = slice.map((a) => {
      const id = UI.escapeHtml(a.application_id);
      return `
        <tr>
          <td><div class="fw-semibold">${UI.escapeHtml(a.job_title || "—")}</div><div class="small muted mono">${id}</div></td>
          <td>${UI.escapeHtml(a.company || "—")}</td>
          <td>${UI.escapeHtml(a.location || "—")}</td>
          <td>${statusBadge(a.status)}</td>
          <td class="small">${UI.escapeHtml(a.notes || "")}</td>
          <td>
            <div class="d-flex gap-2 flex-wrap">
              <select class="form-select form-select-sm" data-action="status" data-id="${id}">
                ${["Draft","Applied","Interview","Offer","Rejected"].map(s => `
                  <option ${a.status===s ? "selected":""}>${s}</option>
                `).join("")}
              </select>
              <button class="btn btn-soft btn-sm" data-action="save" data-id="${id}">Save</button>
            </div>
          </td>
        </tr>
      `;
    }).join("");

    // Hook actions
    tbody.querySelectorAll("[data-action='save']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        const sel = tbody.querySelector(`[data-action="status"][data-id="${CSS.escape(id)}"]`);
        const newStatus = sel ? sel.value : "Draft";

        btn.disabled = true;
        btn.textContent = "Saving…";

        try {
          await API.updateApplicationStatus(id, newStatus);
          const idx = applications.findIndex(x => x.application_id === id);
          if (idx >= 0) applications[idx].status = newStatus;
          applyFilters();
          UI.showAlert("success", "Status updated successfully.");
          setTimeout(UI.clearAlert, 2000);
        } catch (err) {
          if (Auth.handleAuthError(err)) return;
          UI.showAlert("danger", err.message || "Failed to update status.");
        } finally {
          btn.disabled = false;
          btn.textContent = "Save";
        }
      });
    });

    btnPrev.disabled = page <= 1;
    btnNext.disabled = page >= totalPages;
  }

  async function loadUser() {
    user = await API.me();
    elUserName.textContent = user.full_name || "User";
    elUserEmail.textContent = user.email || "";
  }

  async function loadPlans() {
    const data = await API.plans();
    // For now we don’t have user plan in backend; show Pro as default until billing is implemented
    elStatPlan.textContent = "Pro (R300/mo)";
    elPlanMeta.textContent = `${data.currency} • Plans loaded from API`;
  }

  async function loadApplications() {
    setLoadingTable(true);
    const raw = await API.listApplications();
    applications = Array.isArray(raw) ? raw.map(normalizeApp) : [];
    elAppsMeta.textContent = `Last update: ${UI.formatNow()}`;
    elLastSync.textContent = `Last sync: ${UI.formatNow()}`;
    setLoadingTable(false);
    applyFilters();
  }

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
        setTimeout(UI.clearAlert, 2000);
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

    qSearch.addEventListener("input", applyFilters);
    qStatus.addEventListener("change", applyFilters);
    qSort.addEventListener("change", applyFilters);

    btnPrev.addEventListener("click", () => { page = Math.max(1, page - 1); render(); });
    btnNext.addEventListener("click", () => { page = page + 1; render(); });
  }

  async function boot() {
    UI.clearAlert();
    try {
      // minor placeholders
      elStatSaved.textContent = "0";

      await loadUser();
      await loadPlans();
      await loadApplications();
    } catch (err) {
      if (Auth.handleAuthError(err)) return;
      UI.showAlert("danger", err.message || "Failed to load dashboard.");
      setLoadingTable(false);
    }
  }

  wireEvents();
  await boot();
})();
