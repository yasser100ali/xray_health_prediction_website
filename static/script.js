document.getElementById('file-input').addEventListener('change', function(e) {
    const predictButton = document.getElementById('predict-button');
    if (this.files.length > 0) {
        predictButton.disabled = false;
    } else {
        predictButton.disabled = true;
    }
});

document.getElementById('upload-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    fetch('/predict', {
        method: 'POST',
        body: formData
    }).then(response => response.json())
      .then(data => {
          const resultDiv = document.getElementById('result');
          if(data.error) {
              resultDiv.innerHTML = '<p id="error-message">' + data.error + '</p>';
          } else {
              const confidence = (data.confidence * 100).toFixed(2);
              let cssClass = 'healthy';
              if (data.prediction === 'Potentially unhealthy') {
                  cssClass = 'unhealthy';
              }
              resultDiv.innerHTML = `<p class="${cssClass}">${data.prediction}</p><p>Confidence: ${confidence}%</p>`;
          }
      });
});