// static/js/upload.js

document.addEventListener("DOMContentLoaded", () => {
  const uploadBtn = document.getElementById("uploadBtn");
  const invoiceFile = document.getElementById("invoiceFile");
  const resultSection = document.getElementById("resultSection");
  const resultTable = document.getElementById("resultTable");
  const progressBar = document.querySelector(".progress-bar");
  const uploadBox = document.querySelector(".upload-box");

  console.log("upload.js loaded");

  if (!uploadBtn || !invoiceFile || !resultSection || !resultTable || !progressBar) {
    console.warn("Upload elements not found on this page.");
    return;
  }

  // CLICK HANDLER
  uploadBtn.addEventListener("click", async () => {
    console.log("Upload button clicked");

    const file = invoiceFile.files[0];
    if (!file) {
      showToast("Please select a file first", "danger");
      return;
    }

    // Show progress
    progressBar.style.width = "30%";
    uploadBtn.disabled = true;
    uploadBtn.textContent = "Processing...";

    try {
      const formData = new FormData();
      // MUST match Flask: request.files['formImage']
      formData.append("formImage", file);

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      console.log("Upload response:", data);

      if (!response.ok || data.error) {
        throw new Error(data.error || "Upload failed");
      }

      // Success: backend returns { message, file_url, invoice }
      const inv = data.invoice;
      progressBar.style.width = "100%";
      showToast("Invoice processed successfully!", "success");

      // Show result section
      if (inv) {
        resultTable.innerHTML = `
          <tr><td><strong>Invoice ID</strong></td><td>${inv.id}</td></tr>
          <tr><td><strong>Vendor</strong></td><td>${inv.vendor}</td></tr>
          <tr><td><strong>Date</strong></td><td>${inv.date}</td></tr>
          <tr><td><strong>Total</strong></td><td>${inv.total}</td></tr>
          <tr><td><strong>Status</strong></td><td>${inv.status}</td></tr>
        `;
        resultSection.classList.remove("d-none");
      }

    } catch (err) {
      console.error("Upload error:", err);
      showToast("Error processing invoice: " + err.message, "danger");
      progressBar.style.width = "0%";
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.textContent = "Upload & Process";
      setTimeout(() => {
        progressBar.style.width = "0%";
      }, 2000);
    }
  });

  // SIMPLE BOOTSTRAP TOAST/ALERT
  function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = "top: 20px; right: 20px; z-index: 9999; min-width: 300px;";
    toast.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 5000);
  }

  // DRAG & DROP (optional but nice)
  if (uploadBox) {
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      uploadBox.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
      e.preventDefault();
      e.stopPropagation();
    }

    ["dragenter", "dragover"].forEach((eventName) => {
      uploadBox.addEventListener(eventName, () => {
        uploadBox.classList.add("bg-warning", "bg-opacity-25");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      uploadBox.addEventListener(eventName, () => {
        uploadBox.classList.remove("bg-warning", "bg-opacity-25");
      });
    });

    uploadBox.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      invoiceFile.files = files;
    });
  }
});
