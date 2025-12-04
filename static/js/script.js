async function uploadInvoice() {
  const fileInput = document.getElementById("invoiceFile");
  if (!fileInput || !fileInput.files[0]) {
    showToast("Please upload a file first", "error");
    return;
  }

  const formData = new FormData();
  // MUST match Flask: request.files['formImage']
  formData.append("formImage", fileInput.files[0]);

  showToast("Uploading invoice...");

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    console.log("Upload response:", data);

    if (!res.ok || data.error || data.success === false) {
      const msg = data.error || "Upload failed";
      showToast("Error processing invoice: " + msg, "error");
      return;
    }

    // Success case
    const inv = data.invoice;
    showToast(
      `Uploaded ${inv.id} (total: ${inv.total})`,
      "success"
    );

    incrementInvoiceCount();

    // Optional: show results in the table
    const resultSection = document.getElementById("resultSection");
    const resultTable = document.getElementById("resultTable");
    if (resultSection && resultTable && inv) {
      resultTable.innerHTML = `
        <tr><td>Invoice ID</td><td>${inv.id}</td></tr>
        <tr><td>Vendor</td><td>${inv.vendor}</td></tr>
        <tr><td>Date</td><td>${inv.date}</td></tr>
        <tr><td>Total</td><td>${inv.total}</td></tr>
        <tr><td>Status</td><td>${inv.status}</td></tr>
      `;
      resultSection.classList.remove("d-none");
    }

  } catch (err) {
    console.error("Upload exception:", err);
    showToast("Error processing invoice: Upload failed", "error");
  }
}


// ---------------------------
// Pricing Plan Selection
// ---------------------------
function selectPlan(planName) {
  showToast(`You selected the ${planName} plan!`);
}





// ---------------------------
// Export functions globally
// ---------------------------
window.previewInvoice = previewInvoice;
window.uploadInvoice = uploadInvoice;
window.selectPlan = selectPlan;
window.closeSubscription = closeSubscription;
