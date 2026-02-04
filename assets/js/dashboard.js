requireAuth();

function itemRow(title, meta, right = "", actionsHtml = ""){
  return `
    <div class="d-flex justify-content-between align-items-start gap-2 py-2">
      <div style="min-width:0;">
        <div class="fw-semibold text-truncate">${escapeHtml(title)}</div>
        <div class="small-muted text-truncate">${escapeHtml(meta)}</div>
        ${actionsHtml ? `<div class="mt-2 d-flex gap-2 flex-wrap">${actionsHtml}</div>` : ""}
      </div>
      <div class="small-muted">${escapeHtml(right)}</div>
    </div>
    <hr class="soft my-1"/>
  `;
}

let savedCache = [];

async function loadDashboard(){
  try{
    const user = await safeMeSync() || getUser();
    document.getElementById("userTag").textContent = user?.full_name ? `Hello, ${user.full_name}` : "Hello";

    const [apps, saved, billing] = await Promise.all([
      API.applications().catch(() => []),
      API.savedJobs().catch(() => []),
      API.subscriptionStatus().catch(() => ({ status: "unknown" }))
    ]);

    const appsArr = Array.isArray(apps) ? apps : (apps.applications || []);
    const savedArr = Array.isArray(saved) ? saved : (saved.jobs || []);
    savedCache = savedArr;

    document.getElementById("kpiApps").textContent = appsArr.length;
    document.getElementById("kpiSaved").textContent = savedArr.length;
    document.getElementById("kpiSub").textContent = billing.status || "unknown";

    const appsList = document.getElementById("appsList");
    appsList.innerHTML = appsArr.length
      ? appsArr.slice(0, 30).map(a => itemRow(
          a.title || a.job_title || "Application",
          `${a.company || "—"} • ${a.status || "submitted"}`,
          a.created_at ? fmtDate(a.created_at) : "",
          (a.url || a.apply_url) ? `<a class="btn btn-outline-light btn-sm" target="_blank" rel="noreferrer" href="${a.url || a.apply_url}">Open</a>` : ""
        )).join("")
      : `<div class="small-muted">No applications yet. Go to Jobs and apply ✅</div>`;

    const savedList = document.getElementById("savedList");
    savedList.innerHTML = savedArr.length
      ? savedArr.slice(0, 30).map(j => itemRow(
          j.title || "Saved Job",
          `${j.company || "—"} • ${(j.location || j.city || j.country || "—")}`,
          "",
          (j.url || j.apply_url) ? `<a class="btn btn-outline-light btn-sm" target="_blank" rel="noreferrer" href="${j.url || j.apply_url}">Open</a>` : ""
        )).join("")
      : `<div class="small-muted">No saved jobs yet. Save jobs from the Jobs page ⭐</div>`;

  }catch(err){
    toast(err.message, "err");
  }
}

document.getElementById("exportSavedBtn").addEventListener("click", ()=>{
  const rows = savedCache.map(j => ({
    title: j.title || "",
    company: j.company || "",
    location: j.location || j.city || j.country || "",
    url: j.url || j.apply_url || ""
  }));
  downloadCSV(`makwande_saved_jobs_${new Date().toISOString().slice(0,10)}.csv`, rows);
});

window.addEventListener("DOMContentLoaded", loadDashboard);
