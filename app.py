from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import torch
from PIL import Image
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import re
import time
from pymongo import MongoClient
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import csv
import io

# Load environment variables
load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------------------------
# MONGODB CONNECTION
# --------------------------------------
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'invoxia_db')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'invoices')

# --------------------------------------
# EMAIL CONFIGURATION
# --------------------------------------
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL', '')

try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    invoices_collection = db[COLLECTION_NAME]
    # Test connection
    client.admin.command('ping')
    print(f"✓ Connected to MongoDB: {DATABASE_NAME}")
except Exception as e:
    print(f"✗ MongoDB connection failed: {e}")
    print("  Running without database - data will not persist")
    invoices_collection = None

# --------------------------------------
# LOAD MODEL & PROCESSOR
# --------------------------------------
print("Loading LayoutLMv3 model...")
MODEL_PATH = "models"
processor = LayoutLMv3Processor.from_pretrained(MODEL_PATH, apply_ocr=True)
model = LayoutLMv3ForTokenClassification.from_pretrained(MODEL_PATH)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()
print(f"Model loaded successfully on {device}")

# No longer using in-memory list - using MongoDB instead


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
    if invoices_collection is None:
        # Fallback if MongoDB is not connected
        return render_template(
            "analytic.html",
            invoice_count=0,
            total_amount="0.00",
            pending_count=0,
            recent_invoices=[],
            avg_processing_time=0
        )
    
    # Get all invoices from MongoDB
    all_invoices = list(invoices_collection.find())
    
    invoice_count = len(all_invoices)
    total_amount = sum(inv.get("total", 0) for inv in all_invoices)
    pending_count = sum(1 for inv in all_invoices if inv.get("status") == "Pending")
    
    # Get 5 most recent invoices (sorted by _id descending)
    recent_invoices = list(invoices_collection.find().sort("_id", -1).limit(5))
    
    avg_processing_time = (
        sum(inv.get("processing_time", 0) for inv in all_invoices) / invoice_count
        if invoice_count > 0 else 0
    )

    return render_template(
        "analytic.html",
        invoice_count=invoice_count,
        total_amount=f"{total_amount:,.2f}",
        pending_count=pending_count,
        recent_invoices=recent_invoices,
        avg_processing_time=round(avg_processing_time, 2)
    )



# --------------------------------------
# EXTRACT INVOICE DATA USING OCR & MODEL
# --------------------------------------
def extract_invoice_data(image_path):
    """
    Extract key information from invoice image using LayoutLMv3
    """
    try:
        # Load and process image
        image = Image.open(image_path).convert("RGB")
        
        # Process with OCR - the processor automatically runs Tesseract OCR
        encoding = processor(image, return_tensors="pt", padding="max_length", truncation=True)
        
        # Decode the tokens to get the actual text
        # Get the input_ids and decode them (skip special tokens)
        input_ids = encoding['input_ids'][0]  # First sequence in batch
        
        # Decode tokens to text
        ocr_text = processor.tokenizer.decode(input_ids, skip_special_tokens=True)
        
        # If no text extracted, the OCR might not have worked
        if not ocr_text or ocr_text.strip() == "":
            ocr_text = "No text detected in image"
        
        print(f"========== OCR TEXT ==========")
        print(ocr_text)
        print(f"==============================")
        
        # Extract information using regex patterns
        extracted_data = {
            "vendor": extract_vendor(ocr_text),
            "date": extract_date(ocr_text),
            "total": extract_total(ocr_text),
            "invoice_number": extract_invoice_number(ocr_text),
            "raw_text": ocr_text
        }
        
        return extracted_data
    except Exception as e:
        print(f"Error extracting invoice data: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "vendor": "Unknown",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total": 0.0,
            "invoice_number": "",
            "raw_text": "",
            "error": str(e)
        }

def extract_vendor(text):
    """Extract vendor name from text"""
    # Look for common vendor patterns
    patterns = [
        r"(?:from|vendor|seller|company|bill\s+to|billed\s+by)\s*:?\s*([A-Z][A-Za-z\s&\.,]+(?:Inc|LLC|Ltd|Corp|Corporation|Company|Co\.|Pty)?)",
        r"^([A-Z][A-Z\s&\.,]{3,}(?:Inc|LLC|Ltd|Corp|Corporation|Company|Co\.|Pty)?)",  # All caps company name at start
        r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+(?:\s+(?:Inc|LLC|Ltd|Corp|Corporation|Company|Co\.|Pty))?)",  # Title case multi-word
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            vendor = match.group(1).strip()
            # Clean up the vendor name
            vendor = re.sub(r'\s+', ' ', vendor)  # Remove extra spaces
            if len(vendor) > 3 and not any(word in vendor.lower() for word in ['invoice', 'receipt', 'bill', 'date', 'total', 'amount']):
                return vendor
    
    # Try to find any capitalized words at the beginning
    lines = text.split('\n')
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if len(line) > 3 and line[0].isupper():
            # Skip if it contains common non-vendor words
            if not any(word in line.lower() for word in ['invoice', 'receipt', 'tax', 'date', 'total', 'amount', 'abn', 'acn', 'gst']):
                words = line.split()
                if len(words) >= 2:  # At least 2 words
                    return ' '.join(words[:4])  # Take first 4 words max
    
    return "Unknown Vendor"

def extract_date(text):
    """Extract date from text"""
    # Common date patterns
    patterns = [
        r"(?:date|issued|dated)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        r"\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
        r"\b(\d{6})\b",  # DDMMYY or YYMMDD format like 281125
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            
            # Normalize all dates to DD/MM/YYYY format
            if len(date_str) == 6 and date_str.isdigit():
                # DDMMYY format
                day = date_str[:2]
                month = date_str[2:4]
                year = date_str[4:6]
                if int(day) <= 31 and int(month) <= 12:
                    full_year = "20" + year
                    return f"{day}/{month}/{full_year}"
            elif len(date_str) == 10 and date_str[4] in ['-', '/']:
                # YYYY-MM-DD or YYYY/MM/DD format
                parts = date_str.replace('-', '/').split('/')
                year = parts[0]
                month = parts[1].zfill(2)
                day = parts[2].zfill(2)
                return f"{day}/{month}/{year}"
            elif '/' in date_str or '-' in date_str:
                # DD/MM/YYYY or DD-MM-YYYY format
                parts = date_str.replace('-', '/').split('/')
                if len(parts) == 3:
                    day = parts[0].zfill(2)
                    month = parts[1].zfill(2)
                    year = parts[2]
                    # Handle 2-digit year
                    if len(year) == 2:
                        year = "20" + year
                    return f"{day}/{month}/{year}"
            
            return date_str
    
    # Return current date in DD/MM/YYYY format
    now = datetime.now()
    return now.strftime("%d/%m/%Y")

def extract_total(text):
    """Extract total amount from text"""
    # Look for total amount patterns
    patterns = [
        r"(?:total|amount|sum|balance|due|subtotal|grand\s*total)\s*:?\s*\$?\s*S?\$?\s*([\d,\s]+[.,]\s*\d{2})",  # Handles spaces and both . and , as decimal
        r"\$\s*([\d,]+[.,]\d{2})\b",
        r"([\d,]+[.,]\d{2})\s*(?:USD|SGD|AUD|usd|sgd|aud|dollars?)",
        r"(?:total|subtotal|grand\s*total)\s+Ai?\s*\)?\s*[.:]\s*([\d,\s]+[.,]\s*\d{2})",  # Handles "Total Ai). 00"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1)
            # Remove all spaces first
            amount_str = amount_str.replace(' ', '')
            
            # Handle European format (comma as decimal separator)
            # If last comma/dot is followed by exactly 2 digits, it's the decimal separator
            if ',' in amount_str and '.' in amount_str:
                # Both present - last one is decimal separator
                if amount_str.rindex(',') > amount_str.rindex('.'):
                    # Comma is decimal separator
                    amount_str = amount_str.replace('.', '').replace(',', '.')
                else:
                    # Dot is decimal separator
                    amount_str = amount_str.replace(',', '')
            elif ',' in amount_str:
                # Only comma - check if it's decimal or thousands separator
                parts = amount_str.split(',')
                if len(parts[-1]) == 2:  # Last part has 2 digits = decimal separator
                    amount_str = amount_str.replace(',', '.')
                else:  # Thousands separator
                    amount_str = amount_str.replace(',', '')
            
            try:
                return float(amount_str)
            except ValueError:
                continue
    return 0.0

def extract_invoice_number(text):
    """Extract invoice number from text"""
    # Try patterns in order of specificity - most specific first
    patterns = [
        r"(?:invoice|inv|bill|receipt|rept)\s*(?:number|no|num|#)?[\s:\.»\-]*#?\s*([0-9]{6,})",  # Numeric after INVOICE NO
        r"(?:invoice|inv|bill|receipt|rept)\s*(?:number|no|num|#)?[\s:\.»\-]*#?\s*([A-Z]{2,}[0-9\-]{3,})",  # Alphanumeric after INVOICE NO
        r"#\s*([0-9]{6,})\b",  # #123456
        r"\bNO[\.:»\s]+([0-9]{6,})\b",  # NO. 123456 or NO» 123456
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            inv_num = match.group(1).strip()
            # Clean up spaces in invoice number
            inv_num = re.sub(r'\s+', '', inv_num)
            # Skip if it looks like a date
            if re.match(r'^\d{6}$', inv_num) and int(inv_num[:2]) <= 31 and int(inv_num[2:4]) <= 12:
                # This looks like a date (DDMMYY), skip it
                continue
            # Skip if it contains common words (all letters)
            if inv_num.isalpha() and len(inv_num) < 8:
                continue
            if len(inv_num) >= 3:
                return inv_num
    
    return ""


# --------------------------------------
# CSV GENERATION FOR EMAIL ATTACHMENT
# --------------------------------------
def generate_invoice_csv():
    """Generate CSV file with all invoices and total sum"""
    if invoices_collection is None:
        return None
    
    # Get all invoices from MongoDB
    all_invoices = list(invoices_collection.find().sort("_id", 1))
    
    if not all_invoices:
        return None
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Invoice ID', 'Vendor', 'Date', 'Amount'])
    
    # Write invoice data and calculate total
    total_amount = 0.0
    for invoice in all_invoices:
        invoice_id = invoice.get('id', 'N/A')
        vendor = invoice.get('vendor', 'Unknown')
        date = invoice.get('date', 'N/A')
        amount = invoice.get('total', 0.0)
        total_amount += amount
        
        writer.writerow([invoice_id, vendor, date, f"${amount:.2f}"])
    
    # Write total row
    writer.writerow(['', '', 'TOTAL:', f"${total_amount:.2f}"])
    
    # Get CSV content as bytes
    csv_content = output.getvalue()
    output.close()
    
    return csv_content.encode('utf-8')


# --------------------------------------
# EMAIL NOTIFICATION
# --------------------------------------
def send_invoice_notification(new_invoice, total_all_invoices):
    """Send email notification when a new invoice is uploaded"""
    
    # Skip if email not configured
    if not SMTP_USERNAME or not SMTP_PASSWORD or not RECIPIENT_EMAIL:
        print("⚠ Email not configured - skipping notification")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"Invoxia Support <{SMTP_USERNAME}>"
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"New Invoice Uploaded - {new_invoice['id']}"
        
        # Email body
        body = f"""
Hello,

A new invoice has been uploaded and processed successfully.

📄 Invoice Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Invoice ID:      {new_invoice['id']}
Vendor:          {new_invoice['vendor']}
Date:            {new_invoice['date']}
Amount:          ${new_invoice['total']:.2f}
Status:          {new_invoice['status']}
Processing Time: {new_invoice['processing_time']}s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Total Amount (All Invoices): ${total_all_invoices:.2f}

📊 A complete invoice history CSV is attached to this email.

---
This is an automated notification from Invoxia Invoice Processing System.
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Generate and attach CSV
        csv_data = generate_invoice_csv()
        if csv_data:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(csv_data)
            encoders.encode_base64(attachment)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"invoice_history_{timestamp}.csv"
            attachment.add_header('Content-Disposition', f'attachment; filename={filename}')
            msg.attach(attachment)
        
        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✓ Email notification sent to {RECIPIENT_EMAIL}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to send email: {e}")
        return False

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

    # Process invoice with AI model
    start_time = time.time()
    extracted_data = extract_invoice_data(file_path)
    processing_time = round(time.time() - start_time, 2)
    
    # Get current count from MongoDB for ID generation
    if invoices_collection is not None:
        invoice_count = invoices_collection.count_documents({})
    else:
        invoice_count = 0
    
    # Generate auto-incrementing invoice ID (INV-001, INV-002, etc.)
    auto_invoice_id = f"INV-{str(invoice_count + 1).zfill(3)}"
    
    # Create invoice entry with extracted data
    new_invoice = {
        "id": auto_invoice_id,
        "vendor": extracted_data.get("vendor", "Unknown Vendor"),
        "date": extracted_data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "total": extracted_data.get("total", 0.0),
        "status": "Processed",
        "processing_time": processing_time,
        "raw_text": extracted_data.get("raw_text", ""),
        "filename": filename,
        "uploaded_at": datetime.now()
    }

    # Save to MongoDB
    if invoices_collection is not None:
        result = invoices_collection.insert_one(new_invoice)
        new_invoice['_id'] = str(result.inserted_id)  # Convert ObjectId to string for JSON
        print(f"✓ Invoice saved to MongoDB with ID: {result.inserted_id}")
        
        # Calculate total of all invoices
        all_invoices = list(invoices_collection.find())
        total_all_invoices = sum(inv.get("total", 0) for inv in all_invoices)
        
        # Send email notification
        send_invoice_notification(new_invoice, total_all_invoices)
    else:
        print("✗ MongoDB not available - invoice not saved")

    return jsonify({
        'message': 'File uploaded and processed successfully',
        'file_url': f"/uploads/{filename}",
        'invoice': new_invoice,
        'extracted_data': extracted_data
    }), 200


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/pricing')
def pricing_page():
    return render_template('pricing.html')


if __name__ == '__main__':
    app.run(debug=True)
