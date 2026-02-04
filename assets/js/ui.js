function $(sel) { return document.querySelector(sel); }
function $all(sel) { return Array.from(document.querySelectorAll(sel)); }

function toast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toastx toastx-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.classList.add("show"), 10);
  setTimeout(() => { el.classList.remove("show"); setTimeout(() => el.remove(), 250); }, 3200);
}

function setLoading(btn, isLoading, originalText = null) {
  if (!btn) return;
  if (!btn.dataset.orig) btn.dataset.orig = originalText || btn.innerHTML;
  btn.disabled = isLoading;
  btn.innerHTML = isLoading ? `Processing…` : btn.dataset.orig;
}

function escapeHtml(s){
  return String(s ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

function fmtDate(s){
  if(!s) return "";
  try { return new Date(s).toLocaleDateString(); } catch { return s; }
}

function downloadText(filename, text){
  const blob = new Blob([text], {type:"text/plain;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}

function downloadCSV(filename, rows){
  // rows: array of objects
  if(!rows || !rows.length){
    toast("Nothing to export.", "warn");
    return;
  }
  const cols = Array.from(new Set(rows.flatMap(r => Object.keys(r))));
  const esc = (v) => {
    const s = String(v ?? "");
    if(/[,"\n]/.test(s)) return `"${s.replace(/"/g,'""')}"`;
    return s;
  };
  const lines = [
    cols.join(","),
    ...rows.map(r => cols.map(c => esc(r[c])).join(","))
  ];
  const csv = lines.join("\n");
  const blob = new Blob([csv], {type:"text/csv;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}

async function safeMeSync(){
  if(!isLoggedIn()) return null;
  try {
    const me = await API.me();
    if(me) localStorage.setItem(window.APP_CONFIG.STORAGE_KEYS.user, JSON.stringify(me.user || me));
    return me.user || me;
  } catch(e){
    // token invalid => logout
    if(e.status === 401){
      clearSession();
    }
    return null;
  }
}
