const uploadBtn = document.getElementById('uploadBtn');
const invoiceFile = document.getElementById('invoiceFile');
const resultSection = document.getElementById('resultSection');
const resultTable = document.getElementById('resultTable');
const progressBar = document.querySelector('.progress-bar');

uploadBtn.addEventListener('click', async () => {
  const file = invoiceFile.files[0];
  if (!file) {
    alert('Please select a file first');
    return;
  }

  // Reset progress bar
  progressBar.style.width = '0%';
  
  // Create form data
  const formData = new FormData();
  formData.append('formImage', file);

  try {
    // Show progress
    progressBar.style.width = '30%';
    
    // Upload to Flask backend
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });

    progressBar.style.width = '70%';
    
    if (!response.ok) {
      throw new Error('Upload failed');
    }

    const result = await response.json();
    progressBar.style.width = '100%';
    
    // Display extracted invoice data
    resultSection.classList.remove('d-none');
    
    const invoice = result.invoice;
    const data = {
      "Invoice ID": invoice.id,
      "Vendor": invoice.vendor,
      "Date": invoice.date,
      "Total Amount": `$${invoice.total.toFixed(2)}`,
      "Status": invoice.status,
      "Processing Time": `${invoice.processing_time}s`
    };

    // Populate result table
    resultTable.innerHTML = '';
    for (let field in data) {
      const row = `<tr><td>${field}</td><td>${data[field]}</td></tr>`;
      resultTable.innerHTML += row;
    }
    
    // Show success message
    alert('Invoice processed successfully!');
    
  } catch (error) {
    console.error('Error:', error);
    alert('Error uploading file. Please try again.');
    progressBar.style.width = '0%';
  }
});
