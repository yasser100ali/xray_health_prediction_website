X-ray Predictor and DICOM Converter

Project Overview

This Flask application serves as a dual-purpose tool for both predicting health statuses from X-ray images and converting DICOM files to PNG format. It allows users to upload X-ray images to assess their health status and to convert DICOM files into a more universally usable format (PNG). The project is designed to provide medical professionals and radiologists with a quick, reliable tool to assist in diagnostics and file management.

Features

	•	Health Prediction: Users can upload X-ray images to predict if they indicate a healthy or potentially unhealthy status. The application returns a prediction along with a confidence score.
	•	DICOM to PNG Conversion: Users can upload one or multiple DICOM files and convert them to PNG format. The tool handles multiple files efficiently, providing a downloadable ZIP file containing all the converted images.
	•	Interactive Interface: The application features a drag-and-drop interface for uploading files, real-time progress updates during conversions, and automatic downloads of converted files.

Technical Stack

	•	Backend: Flask (Python)
	•	Machine Learning Model: TensorFlow/Keras
	•	Frontend: HTML, CSS, JavaScript
	•	Data Handling: Pydicom for DICOM file manipulation
