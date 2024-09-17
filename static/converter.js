const dropZone = document.getElementById('drop-zone');
const fileInput = dropZone.querySelector('input[type="file"]');
const resultDiv = document.getElementById('result');
const progressDiv = document.getElementById('progress');
let filesList = [];

// Handle click on drop zone to open file dialog
dropZone.addEventListener('click', () => {
    fileInput.click();
});

// Update filesList when files are selected via dialog
fileInput.addEventListener('change', () => {
    filesList = Array.from(fileInput.files);
    updateDropZoneText();
});

// Handle drag over event
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

// Handle drag leave event
dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

// Handle drop event
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    filesList = Array.from(e.dataTransfer.files);
    updateDropZoneText();
});

// Update drop zone text based on selected files
function updateDropZoneText() {
    if (filesList.length > 0) {
        const hasZip = filesList.some(file => file.type === 'application/zip' || file.type === 'application/x-zip-compressed');
        if (hasZip) {
            dropZone.querySelector('p').textContent = `${filesList.length} ZIP file(s) selected`;
        } else {
            dropZone.querySelector('p').textContent = `${filesList.length} DICOM file(s) selected`;
        }
    } else {
        dropZone.querySelector('p').textContent = 'Drag and drop DICOM files or a ZIP file here, or click to select files.';
    }
}

// Handle form submission
document.getElementById('upload-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData();

    // Append files to FormData
    filesList.forEach((file) => {
        if (file.type === 'application/zip' || file.type === 'application/x-zip-compressed') {
            formData.append('zip_file', file);
        } else {
            formData.append('files[]', file);
        }
    });

    // Reset result and progress
    resultDiv.innerHTML = '';
    progressDiv.textContent = '';

    // Initialize progress
    let totalFiles = 0;
    let convertedFiles = 0;
    const hasZip = filesList.some(file => file.type === 'application/zip' || file.type === 'application/x-zip-compressed');

    if (hasZip) {
        progressDiv.textContent = `Processing ZIP file...`;
    } else {
        totalFiles = filesList.length;
        progressDiv.textContent = `Converted ${convertedFiles}/${totalFiles} files (0%)`;
    }

    fetch('/convert_dicom', {
        method: 'POST',
        body: formData
    }).then(response => response.json())
      .then(data => {
          if(data.error) {
              resultDiv.innerHTML = '<p id="error-message">' + data.error + '</p>';
              progressDiv.textContent = '';
          } else if(data.success && data.download_url) {
              // Display 'Conversion completed' message and download button
              resultDiv.innerHTML = `
                  <p id="conversion-message">Conversion completed.</p>
                  <a href="${data.download_url}" class="button">Download Converted Images</a>
              `;
              if (!hasZip && totalFiles > 0) {
                  progressDiv.textContent = `Converted ${totalFiles}/${totalFiles} files (100%)`;
              } else {
                  progressDiv.textContent = 'Conversion completed.';
              }
          }
      })
      .catch(error => {
          resultDiv.innerHTML = '<p id="error-message">An error occurred: ' + error.message + '</p>';
          progressDiv.textContent = '';
      });

    // Simulate progress updates (client-side only)
    if (!hasZip && totalFiles > 0) {
        const progressInterval = setInterval(() => {
            convertedFiles++;
            if (convertedFiles >= totalFiles) {
                clearInterval(progressInterval);
                convertedFiles = totalFiles;
            }
            const percentage = Math.round((convertedFiles / totalFiles) * 100);
            progressDiv.textContent = `Converted ${convertedFiles}/${totalFiles} files (${percentage}%)`;
        }, 500);
    }
});
