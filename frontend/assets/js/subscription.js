requireAuth();

document.getElementById("statusBtn").addEventListener("click", async () => {
  try{
    const res = await API.subscriptionStatus();
    document.getElementById("statusOut").textContent = `Status: ${res.status || "unknown"}`;
    toast("Status updated ✅", "ok");
  }catch(err){
    toast("Billing status not available on API yet.", "warn");
  }
});
