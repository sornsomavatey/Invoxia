from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from pymongo import MongoClient

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------------------------
# MONGODB SETUP (NEW)
# --------------------------------------
# Use env var if set, otherwise default to local MongoDB
MONGO_URI = "mongodb+srv://mrznak88k_db_user:Naknak11@cluster0.vymj79i.mongodb.net/invoice_app?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["invoice_app"]
invoices_col = db["invoices"]  # collection name


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
# ANALYTICS PAGE (CHANGED TO USE MONGO)
# --------------------------------------
@app.route('/analytic')
def analytic_page():
    # Get all invoices from MongoDB
    invoices = list(invoices_col.find({}))

    # Optional: convert _id to string so templates / JSON don’t show ObjectId(...)
    for inv in invoices:
        inv["_id"] = str(inv["_id"])

    invoice_count = len(invoices)
    total_amount_value = sum(inv.get("total", 0) for inv in invoices)
    pending_count = sum(1 for inv in invoices if inv.get("status") == "Pending")
    recent_invoices = invoices[-5:]

    avg_processing_time = (
        sum(inv.get("processing_time", 0) for inv in invoices) / invoice_count
        if invoice_count > 0 else 0
    )

    return render_template(
        "analytic.html",
        invoice_count=invoice_count,
        total_amount=f"{total_amount_value:,.2f}",
        pending_count=pending_count,
        recent_invoices=recent_invoices,
        avg_processing_time=round(avg_processing_time, 2)
    )

@app.route("/db-test")
def db_test():
    try:
        count = invoices_col.count_documents({})
        return f"DB OK. invoices count = {count}"
    except Exception as e:
        return f"DB ERROR: {e}", 500


# --------------------------------------
# IMAGE UPLOAD + CREATE NEW INVOICE (CHANGED TO USE MONGO)
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

    # Count existing invoices to generate a simple incremental ID similar to before
    existing_count = invoices_col.count_documents({})
    invoice_id = f"INV-{1000 + existing_count + 1}"

    new_invoice = {
        "id": invoice_id,
        "filename": filename,
        "file_path": file_path,
        "vendor": "Unknown Vendor",                 # TODO: replace with OCR output
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total": 12.50,                             # TODO: replace with OCR amount
        "status": "Processed",
        "processing_time": 2.5,                     # example seconds
        "created_at": datetime.now()
    }

    result = invoices_col.insert_one(new_invoice)
    new_invoice["_id"] = str(result.inserted_id)

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
