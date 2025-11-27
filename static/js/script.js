// ---------------------------
// Smooth Scroll Animation
// ---------------------------
document.addEventListener("DOMContentLoaded", () => {
  const scrollLinks = document.querySelectorAll("a[href^='#']");
  scrollLinks.forEach(link => {
    link.addEventListener("click", e => {
      e.preventDefault();
      const section = document.querySelector(link.getAttribute("href"));
      if (section) {
        section.scrollIntoView({ behavior: "smooth" });
      }
    });
  });
});


// ---------------------------
// Navbar Shadow on Scroll
// ---------------------------
window.addEventListener("scroll", () => {
  const navbar = document.querySelector(".aksor-navbar");
  if (window.scrollY > 20) {
    navbar.classList.add("shadow-sm");
  } else {
    navbar.classList.remove("shadow-sm");
  }
});


// ---------------------------
// Upload Preview (Image/File)
// ---------------------------
function previewInvoice(event) {
  const file = event.target.files[0];

  if (!file) return;

  const previewBox = document.getElementById("invoicePreview");
  const reader = new FileReader();

  reader.onload = () => {
    previewBox.src = reader.result;
    previewBox.style.display = "block";
  };

  reader.readAsDataURL(file);
}


// ---------------------------
// Toast Notification
// ---------------------------
function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `custom-toast ${type}`;
  toast.textContent = message;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("show");
  }, 50);

  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}


// ---------------------------
// Subscription Popup if > 30 invoices
// ---------------------------
function checkInvoiceLimit() {
  let count = localStorage.getItem("invoice_count") || 0;

  if (count > 30) {
    document.getElementById("subscriptionModal").classList.add("active");
  }
}

function closeSubscription() {
  document.getElementById("subscriptionModal").classList.remove("active");
}

function incrementInvoiceCount() {
  let count = localStorage.getItem("invoice_count") || 0;
  count++;
  localStorage.setItem("invoice_count", count);

  if (count === 31) {
    showToast("Limit reached! Please subscribe to continue.", "warning");
    checkInvoiceLimit();
  }
}


// ---------------------------
// Dark Focus Mode (User stays focused)
// ---------------------------
const focusToggle = document.getElementById("focusModeToggle");

if (focusToggle) {
  focusToggle.addEventListener("click", () => {
    document.body.classList.toggle("focus-mode");

    const enabled = document.body.classList.contains("focus-mode");
    localStorage.setItem("focusMode", enabled ? "on" : "off");

    showToast(enabled ? "Focus Mode Enabled" : "Focus Mode Disabled");
  });
}

// Load focus mode on startup
if (localStorage.getItem("focusMode") === "on") {
  document.body.classList.add("focus-mode");
}


// ---------------------------
// Example function: Upload Invoice to Backend
// ---------------------------
async function uploadInvoice() {
  const fileInput = document.getElementById("invoiceFile");
  if (!fileInput.files[0]) {
    showToast("Please upload a file first", "error");
    return;
  }

  const formData = new FormData();
  formData.append("invoice", fileInput.files[0]);

  showToast("Uploading invoice...");

  try {
    const res = await fetch("/upload-invoice", {
      method: "POST",
      body: formData
    });

    if (res.ok) {
      showToast("Invoice uploaded successfully!");

      incrementInvoiceCount();
    } else {
      showToast("Upload failed. Try again.", "error");
    }

  } catch (err) {
    showToast("Connection error.", "error");
    console.error(err);
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
