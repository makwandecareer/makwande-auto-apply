requireAuth();

let lastOutput = "";

document.getElementById("uploadBtn").addEventListener("click", async ()=>{
  const btn = document.getElementById("uploadBtn");
  const file = document.getElementById("cvFile").files[0];
  if(!file){
    toast("Please choose a file first.", "warn");
    return;
  }
  setLoading(btn, true);
  try{
    const res = await API.uploadCv(file);
    // expected response: { cv_text: "..." } OR { text: "..." }
    const text = res.cv_text || res.text || "";
    if(!text){
      toast("Upload succeeded but no text returned.", "warn");
      return;
    }
    document.querySelector("[name=cv_text]").value = text;
    toast("CV text extracted ✅", "ok");
  }catch(err){
    toast("Upload not supported on this API (or failed). Use paste instead.", "warn");
  }finally{
    setLoading(btn, false);
  }
});

document.getElementById("revampForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("revampBtn");
  setLoading(btn, true);

  const payload = Object.fromEntries(new FormData(e.target).entries());

  try{
    const res = await API.revamp(payload);
    lastOutput = res.revamped_cv || res.output || "";
    document.getElementById("revampOut").value = lastOutput;

    const score = res.ats_score ?? res.score ?? "—";
    const fb = res.feedback ? ` • ${res.feedback}` : "";
    document.getElementById("revampMeta").textContent = `ATS Score: ${score}${fb}`;
    toast("CV revamped ✅", "ok");
  }catch(err){
    toast(err.message, "err");
  }finally{
    setLoading(btn, false);
  }
});

document.getElementById("downloadBtn").addEventListener("click", ()=>{
  if(!lastOutput){
    toast("Nothing to download yet.", "warn");
    return;
  }
  downloadText("revamped_cv.txt", lastOutput);
});
