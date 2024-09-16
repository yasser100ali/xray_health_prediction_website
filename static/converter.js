const dropZone = document.getElementById('drop-zone');
const fileInput = dropZone.querySelector('input[type="file"]');
const resultDiv = document.getElementById('result');
const progressDiv = document.getElementById('progress');
let filesList = [];

dropZone.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', () => {
    filesList = Array.from(fileInput.files);
    updateDropZoneText();
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    filesList = Array.from(e.dataTransfer.files);
    updateDropZoneText();
});

function updateDropZoneText() {
    if (filesList.length > 0) {
        dropZone.querySelector('p').textContent = `${filesList.length} file(s) selected`;
    } else {
        dropZone.querySelector('p').textContent = 'Drag and drop DICOM files here, or click to select files.';
    }
}

document.getElementById('upload-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData();
    filesList.forEach((file) => {
        formData.append('files[]', file);
    });

    // Initialize progress
    let totalFiles = filesList.length;
    let convertedFiles = 0;

    progressDiv.textContent = `Converted ${convertedFiles}/${totalFiles} files (0%)`;

    fetch('/convert_dicom', {
        method: 'POST',
        body: formData
    }).then(response => {
        if(response.headers.get('Content-Type').includes('application/json')) {
            return response.json();
        } else {
            // Handle ZIP file download
            return response.blob();
        }
    }).then(data => {
        if(data.error) {
            resultDiv.innerHTML = '<p id="error-message">' + data.error + '</p>';
            progressDiv.textContent = '';
        } else if(data instanceof Blob) {
            // Handle ZIP file download
            const blob = data;
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'converted_images.zip';

            // Programmatically click the link to trigger the download
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            // Revoke the URL after a delay to ensure the download has started
            setTimeout(() => {
                window.URL.revokeObjectURL(url);
            }, 100);

            resultDiv.innerHTML = '<p>Conversion completed. Your download should start shortly.</p>';
            progressDiv.textContent = `Converted ${totalFiles}/${totalFiles} files (100%)`;
        } else if(data.success) {
            // Handle single image conversion
            resultDiv.innerHTML = '<p>Conversion completed.</p>';
            progressDiv.textContent = `Converted ${totalFiles}/${totalFiles} files (100%)`;
        }
    }).catch(error => {
        resultDiv.innerHTML = '<p id="error-message">An error occurred: ' + error.message + '</p>';
        progressDiv.textContent = '';
    });

    // Simulate progress updates (client-side only)
    const progressInterval = setInterval(() => {
        convertedFiles++;
        if (convertedFiles >= totalFiles) {
            clearInterval(progressInterval);
            convertedFiles = totalFiles;
        }
        const percentage = Math.round((convertedFiles / totalFiles) * 100);
        progressDiv.textContent = `Converted ${convertedFiles}/${totalFiles} files (${percentage}%)`;
    }, 1000);
});