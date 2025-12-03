const uploadBtn = document.getElementById('uploadBtn');
const invoiceFile = document.getElementById('invoiceFile');
const resultSection = document.getElementById('resultSection');
const resultTable = document.getElementById('resultTable');
const progressBar = document.querySelector('.progress-bar');

uploadBtn.addEventListener('click', () => {
  const file = invoiceFile.files[0];
  if (!file) {
    alert('Please select a file first');
    return;
  }

  progressBar.style.width = '50%';

  // Simulate API call (replace with your Flask endpoint)
  setTimeout(() => {
    progressBar.style.width = '100%';
    resultSection.classList.remove('d-none');

    // Example data, replace with actual OCR results
    const data = {
      Name: "John Doe",
      Date: "2025-11-26",
      Amount: "$1,250",
      Email: "john@example.com"
    };

    resultTable.innerHTML = '';
    for (let field in data) {
      const row = `<tr><td>${field}</td><td>${data[field]}</td></tr>`;
      resultTable.innerHTML += row;
    }
  }, 1500);
});
