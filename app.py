from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import torch
from PIL import Image
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import re
import time

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    
    # Create invoice entry with extracted data
    new_invoice = {
        "id": extracted_data.get("invoice_number") or f"INV-{1000 + len(invoices_db) + 1}",
        "vendor": extracted_data.get("vendor", "Unknown Vendor"),
        "date": extracted_data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "total": extracted_data.get("total", 0.0),
        "status": "Processed",
        "processing_time": processing_time,
        "raw_text": extracted_data.get("raw_text", "")
    }

    invoices_db.append(new_invoice)

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
