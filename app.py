from flask import Flask, render_template, request, jsonify, send_from_directory
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- FRONTEND ROUTES ----------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload')
def upload_page():
    return render_template('upload.html')

@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/uploads')
def show_uploads():
    files = os.listdir(UPLOAD_FOLDER)
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return render_template('uploads.html', files=image_files)

# ---------- API FOR IMAGE UPLOAD ----------
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'formImage' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['formImage']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    recognized_data = {
        "Name": "Example Name",
        "ID": "2024001",
        "Phone": "0123456789",
        "Email": "example@gmail.com"
    }

    return jsonify({
        'message': 'File uploaded successfully',
        'recognized_data': recognized_data
    })

# Serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
