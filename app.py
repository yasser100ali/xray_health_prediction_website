from flask import Flask, request, render_template, jsonify, url_for, send_file
import tensorflow as tf
from tensorflow.keras.models import load_model
from PIL import Image
import numpy as np
import os
import pydicom
from werkzeug.utils import secure_filename
import zipfile
import io
import tempfile
import concurrent.futures
import shutil
import uuid

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
DICOM_UPLOAD_FOLDER = 'dicom_uploads'
CONVERTED_FOLDER = 'static/dicom_images'
CONVERTED_ZIPS_FOLDER = 'converted_zips'
ALLOWED_EXTENSIONS_DICOM = {'dcm', 'dicom'}
ALLOWED_EXTENSIONS_IMAGE = {'png', 'jpeg', 'jpg'}
ALLOWED_EXTENSIONS_ZIP = {'zip'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DICOM_UPLOAD_FOLDER'] = DICOM_UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['CONVERTED_ZIPS_FOLDER'] = CONVERTED_ZIPS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB limit

# Ensure upload and converted directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DICOM_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_ZIPS_FOLDER, exist_ok=True)

# Load your pre-trained model
MODEL_PATH = '/Users/yasserali/Documents/website_projects/xray_reader_and_converter/saved_model/best_model.h5'  # Adjust the path as needed
model = load_model(MODEL_PATH)

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def model_predict(img_path, model):
    # Load and preprocess the image
    img = Image.open(img_path).convert('RGB')
    img = img.resize((512, 512))  # Adjust to your model's input size
    x = np.array(img)
    x = x / 255.0  # Normalize
    x = np.expand_dims(x, axis=0)  # Batch dimension

    # Make prediction
    preds = model.predict(x)
    confidence = float(preds[0][0])  # Assuming the model outputs a probability between 0 and 1

    # Interpret prediction
    if confidence <= 0.4:
        result = 'Healthy'
        confidence = 1 - confidence  # Confidence for 'Healthy'
    else:
        result = 'Potentially unhealthy'
        confidence = confidence  # Confidence for 'Unhealthy'

    return result, confidence

def dicom_to_png(dicom_file_path, output_filepath):
    try:
        # Read the DICOM file
        ds = pydicom.dcmread(dicom_file_path)
        # Check if 'PixelData' is in the DICOM file
        if 'PixelData' not in ds:
            raise ValueError("DICOM file does not contain pixel data.")
        new_image = ds.pixel_array.astype(float)

        # Scale the pixel values to the range [0, 255] and convert to uint8
        scaled_image = (np.maximum(new_image, 0) / new_image.max()) * 255.0
        scaled_image = np.uint8(scaled_image)

        # Convert to PIL image
        final_image = Image.fromarray(scaled_image)

        # Resize
        resize_image = final_image.resize((512, 512))

        # Save image
        resize_image.save(output_filepath)
        return output_filepath
    except Exception as e:
        raise e

def convert_file(dicom_path, output_dir):
    try:
        png_filename = os.path.splitext(os.path.basename(dicom_path))[0] + '.png'
        png_filepath = os.path.join(output_dir, png_filename)
        dicom_to_png(dicom_path, png_filepath)
        return png_filename
    except Exception as e:
        return str(e)

@app.route('/')
def index():
    # Home page with file upload form
    return render_template('index.html')

@app.route('/converter')
def converter():
    # DICOM to PNG converter page
    return render_template('converter.html')

@app.route('/about')
def about():
    # About page
    return render_template('about.html')

@app.route('/predict', methods=['POST'])
def predict():
    # Handle the image upload and prediction
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_IMAGE):
        # Save the uploaded image
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        # Make prediction
        result, confidence = model_predict(upload_path, model)

        # Remove the uploaded file after prediction
        os.remove(upload_path)

        # Return the result as JSON
        return jsonify({'prediction': result, 'confidence': float(confidence)})
    else:
        return jsonify({'error': 'Invalid file format. Please upload a PNG or JPEG image.'})

@app.route('/convert_dicom', methods=['POST'])
def convert_dicom():
    zip_file = request.files.get('zip_file', None)
    dicom_files = request.files.getlist('files[]')

    if not zip_file and not dicom_files:
        return jsonify({'error': 'No files uploaded'})

    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_extract_dir, tempfile.TemporaryDirectory() as temp_output_dir:
        dicom_file_paths = []

        # Handle ZIP file upload
        if zip_file and zip_file.filename != '':
            if not allowed_file(zip_file.filename, ALLOWED_EXTENSIONS_ZIP):
                return jsonify({'error': 'Invalid file format. Please upload a ZIP file.'})
            zip_path = os.path.join(temp_extract_dir, secure_filename(zip_file.filename))
            zip_file.save(zip_path)

            # Extract ZIP file
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)
            except zipfile.BadZipFile:
                return jsonify({'error': 'Invalid ZIP file.'})

            # Collect DICOM files from extracted contents
            for root, dirs, files in os.walk(temp_extract_dir):
                for file in files:
                    if allowed_file(file, ALLOWED_EXTENSIONS_DICOM):
                        dicom_path = os.path.join(root, file)
                        dicom_file_paths.append(dicom_path)

            if not dicom_file_paths:
                return jsonify({'error': 'No valid DICOM files found in the ZIP.'})

        # Handle individual DICOM file uploads
        if dicom_files:
            for file in dicom_files:
                if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_DICOM):
                    filename = secure_filename(file.filename)
                    dicom_path = os.path.join(temp_extract_dir, filename)
                    file.save(dicom_path)
                    dicom_file_paths.append(dicom_path)

        if not dicom_file_paths:
            return jsonify({'error': 'No valid DICOM files uploaded.'})

        # Convert DICOM files to PNG using ProcessPoolExecutor
        try:
            with concurrent.futures.ProcessPoolExecutor() as executor:
                # Prepare arguments for conversion
                tasks = [(dicom_path, temp_output_dir) for dicom_path in dicom_file_paths]
                # Launch parallel conversion
                results = [executor.submit(convert_file, dicom_path, temp_output_dir) for dicom_path in dicom_file_paths]

                # Collect conversion results
                png_filenames = []
                for future in concurrent.futures.as_completed(results):
                    result = future.result()
                    if isinstance(result, str) and not result.endswith('.png'):
                        # An error occurred during conversion
                        return jsonify({'error': f'Conversion failed: {result}'})
                    png_filenames.append(result)
        except Exception as e:
            return jsonify({'error': f'Conversion failed during multiprocessing: {str(e)}'})

        # Create a unique filename for the converted ZIP
        unique_zip_filename = f'converted_images_{uuid.uuid4().hex}.zip'
        zip_output_path = os.path.join(app.config['CONVERTED_ZIPS_FOLDER'], unique_zip_filename)

        # Create a ZIP file of the converted PNGs
        try:
            with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for png_filename in png_filenames:
                    png_path = os.path.join(temp_output_dir, png_filename)
                    zipf.write(png_path, arcname=png_filename)
        except Exception as e:
            return jsonify({'error': f'Failed to create ZIP file: {str(e)}'})

    # Generate the download URL
    download_url = url_for('download_zip', filename=unique_zip_filename)

    # Return the download URL as JSON
    return jsonify({'success': True, 'download_url': download_url})

@app.route('/download/<filename>')
def download_zip(filename):
    zip_path = os.path.join(app.config['CONVERTED_ZIPS_FOLDER'], filename)
    if not os.path.exists(zip_path):
        return jsonify({'error': 'File not found.'}), 404
    return send_file(
        zip_path,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )

@app.route('/progress')
def get_progress():
    filename = request.args.get('filename')
    return jsonify({'progress': progress.get(filename, 0)})

if __name__ == '__main__':
    app.run(debug=True)
