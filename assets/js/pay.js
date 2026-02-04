requireAuth();

const params = new URLSearchParams(window.location.search);
const prefill = params.get("reference");
if(prefill) document.getElementById("ref").value = prefill;

document.getElementById("verifyBtn").addEventListener("click", async ()=>{
  const btn = document.getElementById("verifyBtn");
  setLoading(btn, true);

  const reference = document.getElementById("ref").value.trim();
  if(!reference){
    toast("Please enter a reference.", "warn");
    setLoading(btn, false);
    return;
  }

  try{
    const res = await API.verifyPayment({ reference });
    document.getElementById("payOut").textContent = `Verified: ${res.status || "ok"} • Ref: ${reference}`;
    toast("Payment verified ✅", "ok");
  }catch(err){
    toast("Payment verification failed (or endpoint not available).", "warn");
  }finally{
    setLoading(btn, false);
  }
});
