requireAuth();

let STATE = {
  page: 1,
  pageSize: window.APP_CONFIG.DEFAULT_PAGE_SIZE,
  results: []
};

function getScore(job){
  const raw = job.match_score ?? job.score ?? job.matchScore ?? 0;
  // raw may be 0-1 or 0-100
  const v = raw <= 1 ? Math.round(raw * 100) : Math.round(raw);
  return isFinite(v) ? v : 0;
}

function jobCard(job, idx){
  const score = getScore(job);
  const company = job.company || "Company";
  const title = job.title || "Job Title";
  const location = job.location || job.city || job.country || "Location";
  const url = job.url || job.apply_url || "";
  const id = job.id || job.job_id || job.jobId || String(idx);

  const badge = score >= 80 ? "badge-soft" : (score >= 60 ? "badge-soft badge-warn" : "badge-soft badge-danger");

  return `
    <div class="col-lg-6">
      <div class="cardx h-100">
        <div class="cardx-body">
          <div class="d-flex justify-content-between align-items-start gap-2">
            <div style="min-width:0;">
              <div class="small-muted">${escapeHtml(company)}</div>
              <h5 class="fw-bold mb-1 text-truncate">${escapeHtml(title)}</h5>
              <div class="small-muted text-truncate">${escapeHtml(location)}</div>
            </div>
            <span class="${badge}">${score}% match</span>
          </div>

          <hr class="soft my-3"/>

          <div class="d-flex gap-2 flex-wrap">
            <button class="btn btn-brand btn-sm" data-apply="${escapeHtml(id)}">Apply</button>
            <button class="btn btn-outline-light btn-sm" data-save="${escapeHtml(id)}">Save</button>
            <button class="btn btn-outline-light btn-sm" data-view="${escapeHtml(id)}">View</button>
            ${url ? `<a class="btn btn-outline-light btn-sm" href="${url}" target="_blank" rel="noreferrer">Open Source</a>` : ""}
          </div>

          <div class="small-muted mt-3">${escapeHtml((job.summary || job.description || "").slice(0, 180))}${(job.summary || job.description || "").length > 180 ? "…" : ""}</div>

          <textarea class="d-none" id="payload_${escapeHtml(id)}">${JSON.stringify(job)}</textarea>
        </div>
      </div>
    </div>
  `;
}

function showSkeleton(){
  const grid = document.getElementById("jobsGrid");
  grid.innerHTML = `
    <div class="col-lg-6"><div class="cardx"><div class="cardx-body"><div class="skeleton" style="width:40%;"></div><div class="skeleton mt-2" style="width:70%; height:18px;"></div><div class="skeleton mt-3" style="width:92%;"></div><div class="skeleton mt-2" style="width:88%;"></div></div></div></div>
    <div class="col-lg-6"><div class="cardx"><div class="cardx-body"><div class="skeleton" style="width:35%;"></div><div class="skeleton mt-2" style="width:76%; height:18px;"></div><div class="skeleton mt-3" style="width:92%;"></div><div class="skeleton mt-2" style="width:88%;"></div></div></div></div>
  `;
}

function getParams(){
  const params = {
    q: document.getElementById("q").value.trim(),
    country: document.getElementById("country").value.trim(),
    min_score: document.getElementById("min_score").value.trim(),
    company: document.getElementById("company").value.trim(),
    location: document.getElementById("location").value.trim(),
    sort: document.getElementById("sort").value,
    page: String(STATE.page),
    page_size: String(STATE.pageSize)
  };
  Object.keys(params).forEach(k => params[k] === "" && delete params[k]);
  return params;
}

function clientSidePostProcess(jobs){
  // If backend doesn't support company/location/sort, we apply locally as a fallback.
  const company = document.getElementById("company").value.trim().toLowerCase();
  const location = document.getElementById("location").value.trim().toLowerCase();
  const sort = document.getElementById("sort").value;

  let out = jobs.slice();

  if(company){
    out = out.filter(j => String(j.company||"").toLowerCase().includes(company));
  }
  if(location){
    const loc = (j)=>`${j.location||""} ${j.city||""} ${j.country||""}`.toLowerCase();
    out = out.filter(j => loc(j).includes(location));
  }

  if(sort === "score_desc"){
    out.sort((a,b)=>getScore(b)-getScore(a));
  } else if(sort === "date_desc"){
    out.sort((a,b)=> new Date(b.posted_date||b.post_advertised_date||b.created_at||0) - new Date(a.posted_date||a.post_advertised_date||a.created_at||0));
  } else if(sort === "date_asc"){
    out.sort((a,b)=> new Date(a.posted_date||a.post_advertised_date||a.created_at||0) - new Date(b.posted_date||b.post_advertised_date||b.created_at||0));
  }
  return out;
}

async function loadJobs(){
  const btn = document.getElementById("searchBtn");
  setLoading(btn, true);
  showSkeleton();

  try{
    const params = getParams();
    const data = await API.jobs(params);

    // allow shapes: array OR {jobs, total, page, page_size}
    let jobs = Array.isArray(data) ? data : (data.jobs || []);
    const total = data.total ?? jobs.length;

    jobs = clientSidePostProcess(jobs);

    STATE.results = jobs;

    document.getElementById("countOut").textContent = `${jobs.length} jobs loaded${(total && total !== jobs.length) ? ` (server total: ${total})` : ""}`;
    document.getElementById("pageOut").textContent = `Page ${STATE.page}`;

    const grid = document.getElementById("jobsGrid");
    if(!jobs.length){
      grid.innerHTML = `<div class="col-12"><div class="cardx"><div class="cardx-body">No jobs found. Try a different keyword or lower the match score.</div></div></div>`;
      return;
    }

    grid.innerHTML = jobs.map(jobCard).join("");

  }catch(err){
    toast(err.message, "err");
    document.getElementById("jobsGrid").innerHTML = `<div class="col-12"><div class="cardx"><div class="cardx-body">Error loading jobs. Check Settings → API Base URL.</div></div></div>`;
  }finally{
    setLoading(btn, false);
  }
}

function getJobPayload(id){
  const el = document.getElementById(`payload_${CSS.escape(id)}`);
  if(!el) return null;
  try { return JSON.parse(el.value); } catch { return null; }
}

async function apply(job, id){
  try{
    await API.applyJob({ job_id: job.id || job.job_id || id, job });
    toast("Application submitted ✅", "ok");
  }catch(err){
    toast(err.message, "err");
  }
}

async function save(job, id){
  try{
    await API.saveJob({ job_id: job.id || job.job_id || id, job });
    toast("Saved ✅", "ok");
  }catch(err){
    toast(err.message, "err");
  }
}

function openModal(job, id){
  const title = job.title || "Job";
  const company = job.company || "Company";
  const location = job.location || job.city || job.country || "Location";
  const score = getScore(job);

  document.getElementById("jobModalTitle").textContent = title;
  document.getElementById("jobModalMeta").textContent = `${company} • ${location} • ${score}% match`;

  const body = (job.description || job.summary || "").trim();
  document.getElementById("jobModalBody").innerHTML = body ? `<pre class="mono" style="white-space:pre-wrap; color:rgba(255,255,255,.82);">${escapeHtml(body)}</pre>` : `<div class="small-muted">No description provided.</div>`;

  const saveBtn = document.getElementById("modalSaveBtn");
  const applyBtn = document.getElementById("modalApplyBtn");

  saveBtn.onclick = () => save(job, id);
  applyBtn.onclick = () => apply(job, id);

  const modal = new bootstrap.Modal(document.getElementById("jobModal"));
  modal.show();
}

function bindEvents(){
  document.getElementById("searchBtn").addEventListener("click", ()=>{
    STATE.page = 1;
    STATE.pageSize = parseInt(document.getElementById("page_size").value, 10) || window.APP_CONFIG.DEFAULT_PAGE_SIZE;
    loadJobs();
  });

  document.getElementById("prevBtn").addEventListener("click", ()=>{
    if(STATE.page > 1){
      STATE.page -= 1;
      loadJobs();
    }
  });

  document.getElementById("nextBtn").addEventListener("click", ()=>{
    STATE.page += 1;
    loadJobs();
  });

  document.getElementById("exportBtn").addEventListener("click", ()=>{
    // Export minimal columns
    const rows = STATE.results.map(j => ({
      title: j.title || "",
      company: j.company || "",
      location: j.location || j.city || j.country || "",
      match_score: getScore(j),
      url: j.url || j.apply_url || ""
    }));
    downloadCSV(`makwande_jobs_${new Date().toISOString().slice(0,10)}.csv`, rows);
  });

  // Delegated actions
  document.getElementById("jobsGrid").addEventListener("click", async (e)=>{
    const t = e.target;
    const applyId = t.getAttribute("data-apply");
    const saveId  = t.getAttribute("data-save");
    const viewId  = t.getAttribute("data-view");

    const id = applyId || saveId || viewId;
    if(!id) return;

    const job = getJobPayload(id);
    if(!job){
      toast("Job payload missing.", "err");
      return;
    }

    if(applyId) return apply(job, id);
    if(saveId)  return save(job, id);
    if(viewId)  return openModal(job, id);
  });

  // Debounced search on enter
  $all("#q,#company,#location").forEach(inp => {
    inp.addEventListener("keydown", (e)=>{
      if(e.key === "Enter"){
        e.preventDefault();
        STATE.page = 1;
        loadJobs();
      }
    });
  });
}

window.addEventListener("DOMContentLoaded", ()=>{
  bindEvents();
  loadJobs();
});
