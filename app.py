from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------------------------
# TEMPORARY IN-MEMORY "DATABASE"
# --------------------------------------
invoices_db = []   # list of dicts: {id, vendor, date, total, status, processing_time}


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


# --------------------------------------
# ANALYTICS PAGE
# --------------------------------------
@app.route('/analytic')
def analytic_page():

    invoice_count = len(invoices_db)
    total_amount = sum(inv["total"] for inv in invoices_db)
    pending_count = sum(1 for inv in invoices_db if inv["status"] == "Pending")
    recent_invoices = invoices_db[-5:]

    avg_processing_time = (
        sum(inv["processing_time"] for inv in invoices_db) / invoice_count
        if invoice_count > 0 else 0
    )

    return render_template(
        "analytic.html",          # 👈 correct file name
        invoice_count=invoice_count,
        total_amount=f"{total_amount:,.2f}",
        pending_count=pending_count,
        recent_invoices=recent_invoices,
        avg_processing_time=round(avg_processing_time, 2)
    )



# --------------------------------------
# IMAGE UPLOAD + CREATE NEW INVOICE
# --------------------------------------
@app.route('/api/upload', methods=['POST'])
def api_upload_file():
    if 'formImage' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['formImage']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # --------------------------------------------------------------
    # TODO: Replace this with OCR extraction
    # For now, we generate a fake invoice entry
    # --------------------------------------------------------------
    new_invoice = {
        "id": f"INV-{1000 + len(invoices_db) + 1}",
        "vendor": "Unknown Vendor",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total": 12.50,          # <-- replace with OCR amount
        "status": "Processed",
        "processing_time": 2.5   # example seconds
    }

    invoices_db.append(new_invoice)

    return jsonify({
        'message': 'File uploaded successfully',
        'file_url': f"/uploads/{filename}",
        'invoice': new_invoice
    }), 200


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/pricing')
def pricing_page():
    return render_template('pricing.html')


if __name__ == '__main__':
    app.run(debug=True)
