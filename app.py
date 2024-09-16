from flask import Flask, request, render_template, jsonify, url_for, send_file
import tensorflow as tf
from tensorflow.keras.models import load_model
from PIL import Image
import numpy as np
import os
import pydicom
from time import sleep
from werkzeug.utils import secure_filename
import zipfile
import io

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
DICOM_UPLOAD_FOLDER = 'dicom_uploads'
CONVERTED_FOLDER = 'static/dicom_images'
ALLOWED_EXTENSIONS_DICOM = {'dcm', 'dicom'}
ALLOWED_EXTENSIONS_IMAGE = {'png', 'jpeg', 'jpg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DICOM_UPLOAD_FOLDER'] = DICOM_UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB limit

# Ensure upload and converted directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DICOM_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# Load your pre-trained model
MODEL_PATH = 'saved_model/best_model.h5'  # Adjust the path as needed
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
    confidence = preds[0][0]  # Assuming the model outputs a probability between 0 and 1

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

# Global variable to store progress (Not thread-safe)
progress = {}

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
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'})
    files = request.files.getlist('files[]')
    if not files:
        return jsonify({'error': 'No files selected'})
    dicom_files = [f for f in files if allowed_file(f.filename, ALLOWED_EXTENSIONS_DICOM)]
    if not dicom_files:
        return jsonify({'error': 'No valid DICOM files found. Allowed extensions: .dcm, .dicom'})

    saved_paths = []

    # Save uploaded DICOM files
    for file in dicom_files:
        filename = secure_filename(file.filename)
        dicom_filepath = os.path.join(app.config['DICOM_UPLOAD_FOLDER'], filename)
        file.save(dicom_filepath)
        saved_paths.append(dicom_filepath)

    # Determine if single or multiple files
    if len(saved_paths) == 1:
        single_file = saved_paths[0]
        png_filename = os.path.splitext(os.path.basename(single_file))[0] + '.png'
        png_filepath = os.path.join(app.config['CONVERTED_FOLDER'], png_filename)

        try:
            # Simulate processing time and update progress
            total_steps = 5
            progress_key = f'convert_{png_filename}'
            progress[progress_key] = 0
            for i in range(1, total_steps + 1):
                sleep(1)
                progress[progress_key] = int((i / total_steps) * 100)

            dicom_to_png(single_file, png_filepath)
            # Remove the uploaded DICOM file after conversion
            os.remove(single_file)
            # Remove progress tracking
            del progress[progress_key]
            # Return the converted image path
            return jsonify({'success': True, 'image_url': url_for('static', filename='dicom_images/' + png_filename)})
        except Exception as e:
            if progress_key in progress:
                del progress[progress_key]
            return jsonify({'error': f'Conversion failed: {str(e)}'})
    else:
        # Multiple files: convert each and zip them
        png_filenames = []
        try:
            for single_file in saved_paths:
                png_filename = os.path.splitext(os.path.basename(single_file))[0] + '.png'
                png_filepath = os.path.join(app.config['CONVERTED_FOLDER'], png_filename)

                # Simulate processing time and update progress
                total_steps = 5
                progress_key = f'convert_{png_filename}'
                progress[progress_key] = 0
                for i in range(1, total_steps + 1):
                    sleep(1)
                    progress[progress_key] = int((i / total_steps) * 100)

                dicom_to_png(single_file, png_filepath)
                png_filenames.append(png_filename)
                # Remove the uploaded DICOM file after conversion
                os.remove(single_file)
                # Remove individual progress tracking
                if progress_key in progress:
                    del progress[progress_key]

            # Create a ZIP of all converted PNGs
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for png_filename in png_filenames:
                    png_path = os.path.join(app.config['CONVERTED_FOLDER'], png_filename)
                    zipf.write(png_path, arcname=png_filename)
            zip_buffer.seek(0)

            # Optionally, remove PNG files after zipping
            for png_filename in png_filenames:
                os.remove(os.path.join(app.config['CONVERTED_FOLDER'], png_filename))

            # Send the ZIP file
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name='converted_images.zip'
            )
        except Exception as e:
            # Clean up any remaining files in case of error
            for png_filename in png_filenames:
                png_path = os.path.join(app.config['CONVERTED_FOLDER'], png_filename)
                if os.path.exists(png_path):
                    os.remove(png_path)
            return jsonify({'error': f'Batch conversion failed: {str(e)}'})

@app.route('/progress')
def get_progress():
    filename = request.args.get('filename')
    return jsonify({'progress': progress.get(filename, 0)})

if __name__ == '__main__':
    app.run(debug=True)
