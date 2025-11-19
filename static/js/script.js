// Upload preview and fake recognition result
const fileInput = document.getElementById('formImage');
const previewDiv = document.getElementById('preview');
const resultDiv = document.getElementById('result');

if (fileInput) {
    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewDiv.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
            };
            reader.readAsDataURL(file);
        }
    });
}

const uploadForm = document.getElementById('uploadForm');
if (uploadForm) {
    uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();

        // Simulate processing delay
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `<p>Processing form... Please wait ⏳</p>`;

        setTimeout(() => {
            const fakeData = {
                Name: "Somavatey Sorn",
                ID: "2024026",
                Phone: "099123456",
                Email: "somavatey@aupp.edu.kh"
            };
            let output = `<h3>Recognized Data:</h3>`;
            for (let key in fakeData) {
                output += `<p><strong>${key}:</strong> ${fakeData[key]}</p>`;
            }
            resultDiv.innerHTML = output;
        }, 1500);
    });
}
