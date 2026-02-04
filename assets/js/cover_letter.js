requireAuth();

let lastCL = "";

document.getElementById("clForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("clBtn");
  setLoading(btn, true);

  const payload = Object.fromEntries(new FormData(e.target).entries());

  try{
    const res = await API.coverLetter(payload);
    lastCL = res.cover_letter || res.output || "";
    document.getElementById("clOut").value = lastCL;
    toast("Cover letter generated ✅", "ok");
  }catch(err){
    toast(err.message, "err");
  }finally{
    setLoading(btn, false);
  }
});

document.getElementById("downloadCLBtn").addEventListener("click", ()=>{
  if(!lastCL){
    toast("Nothing to download yet.", "warn");
    return;
  }
  downloadText("cover_letter.txt", lastCL);
});
