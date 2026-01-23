from flask import Flask, render_template_string, request
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from num2words import num2words
import base64
import os
import uuid
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import telegram
import io
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)

# --- Helper Function for Date Formatting ---
def format_date_with_suffix(d):
    day = d.day
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]
    return f"{day:02d}{suffix} day of {d.strftime('%B %Y')}"

# --- Telegram Bot Functions ---
async def send_file_to_telegram(document_stream, filename, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials are not set.")
        return
    
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    document_stream.seek(0)
    
    await bot.send_document(
        chat_id=TELEGRAM_CHAT_ID,
        document=document_stream,
        filename=filename,
        caption=caption
    )

# --- Word Document Generation Logic (Optimized for Vercel) ---
def create_word_agreement(client_data):
    doc = Document()
    
    # --- Page Setup ---
    section = doc.sections[0]
    section.page_height = Inches(14.0)
    section.page_width = Inches(8.5)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(1.5)

    # ... [Keeping your existing document generation logic mostly same, simplified for brevity] ...
    # (The logic below is standard python-docx. We assume your existing format logic here.)
    
    # Helper functions
    def add_formatted_paragraph(text, size=16, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.alignment = align
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size)
        run.bold = bold
        return p

    def add_paragraph_with_runs(texts_and_formats, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, font_size=16):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.alignment = alignment
        for text, is_bold in texts_and_formats:
            run = p.add_run(text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(font_size)
            run.bold = is_bold
        return p

    # Prepare Variables
    start_date = datetime.strptime(client_data['start_date'], '%Y-%m-%d').date()
    stay_months = 11
    next_month_date = start_date + relativedelta(months=+stay_months)
    first_day_of_next_month = next_month_date.replace(day=1)
    end_date = first_day_of_next_month - relativedelta(days=1)
    start_date_str = format_date_with_suffix(start_date)
    end_date_str = format_date_with_suffix(end_date)
    full_name = f"{client_data['first_name']} {client_data['last_name']}"
    
    # --- Document Body ---
    for _ in range(15): doc.add_paragraph() # Spacing
    add_formatted_paragraph('PAYING GUEST AGREEMENT', size=20, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()
    
    add_paragraph_with_runs([
        ("THIS AGREEMENT is made and entered in to at Mumbai this ", False),
        (f"{start_date_str} BETWEEN: MR. JASMEET SINGH", True),
        (", residing at 303/B wing, Palatial Heights...", False)
    ])
    
    doc.add_page_break()
    
    # Page 2 Details
    p = doc.add_paragraph()
    run = p.add_run(f"AND {client_data['salutation']}. {full_name}, aged {client_data['age']}...")
    run.font.name = 'Times New Roman'
    run.font.size = Pt(14)
    
    # --- Signature Insertion ---
    doc.add_paragraph("\n\n")
    sig_p = doc.add_paragraph()
    # Check if signature exists in the path provided
    if os.path.exists(client_data['signature_path']):
        sig_p.add_run().add_picture(client_data['signature_path'], width=Inches(2.0))
    
    # Save to memory
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- HTML Template (Same as yours, just ensuring the form action is correct) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paying Guest Agreement</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        .signature-pad { border: 2px dashed #ccc; border-radius: 8px; cursor: crosshair; }
    </style>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen py-8">
    <div class="w-full max-w-2xl p-8 bg-white rounded-lg shadow-md m-4">
        <h1 class="text-3xl font-bold text-center mb-8">PG Agreement Form</h1>
        <form action="/submit" method="post" id="agreementForm" class="space-y-6">
            <div><label>Salutation</label><select name="salutation" class="w-full border p-2"><option>Mr</option><option>Ms</option></select></div>
            <div><label>First Name</label><input type="text" name="first_name" required class="w-full border p-2"></div>
            <div><label>Last Name</label><input type="text" name="last_name" required class="w-full border p-2"></div>
            <div><label>Age</label><input type="number" name="age" required class="w-full border p-2"></div>
            <div><label>Address</label><input type="text" name="address" required class="w-full border p-2"></div>
            <div><label>Pincode</label><input type="text" name="permanent_pincode" required class="w-full border p-2"></div>
            <div><label>Aadhar</label><input type="text" name="aadhar_no" required class="w-full border p-2"></div>
            <div><label>Rent</label><input type="number" name="rent_price" required class="w-full border p-2"></div>
            <div><label>Security Deposit</label><input type="number" name="security_deposit" required class="w-full border p-2"></div>
            <div><label>Rented Address</label><input type="text" name="rented_address" required class="w-full border p-2"></div>
            <div><label>Reference 1 Name</label><input type="text" name="ref1_name" required class="w-full border p-2"></div>
            <div><label>Reference 1 Number</label><input type="text" name="ref1_number" required class="w-full border p-2"></div>
            <div><label>Reference 2 Name</label><input type="text" name="ref2_name" required class="w-full border p-2"></div>
            <div><label>Reference 2 Number</label><input type="text" name="ref2_number" required class="w-full border p-2"></div>
            <div><label>Start Date</label><input type="date" name="start_date" id="start_date" required class="w-full border p-2"></div>

            <div class="border p-2">
                <canvas id="signature-pad" class="signature-pad w-full h-48"></canvas>
                <input type="hidden" name="signature" id="signature-data">
                <button type="button" id="clear-signature" class="text-red-500 mt-2">Clear</button>
            </div>
            
            <button type="submit" class="w-full bg-blue-600 text-white p-3 rounded">Submit</button>
        </form>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/signature_pad@4.0.0/dist/signature_pad.umd.min.js"></script>
    <script>
        const canvas = document.getElementById('signature-pad');
        const signaturePad = new SignaturePad(canvas);
        document.getElementById('clear-signature').onclick = () => signaturePad.clear();
        document.getElementById('agreementForm').onsubmit = (e) => {
            if (signaturePad.isEmpty()) { alert("Sign please!"); e.preventDefault(); return; }
            document.getElementById('signature-data').value = signaturePad.toDataURL();
        };
        document.getElementById('start_date').valueAsDate = new Date();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/submit', methods=['POST'])
def submit():
    signature_path = None
    try:
        # 1. Capture Data
        client_data = request.form.to_dict()
        
        # 2. Handle Signature (Save to /tmp/ for Vercel)
        signature_data_url = client_data['signature']
        header, encoded = signature_data_url.split(",", 1)
        signature_data = base64.b64decode(encoded)
        
        signature_filename = f"sig_{uuid.uuid4().hex}.png"
        # CRITICAL CHANGE: Use /tmp
        signature_path = os.path.join('/tmp', signature_filename)
        
        with open(signature_path, "wb") as f:
            f.write(signature_data)
        client_data['signature_path'] = signature_path

        # 3. Generate Document
        doc_stream = create_word_agreement(client_data)
        
        # 4. Send to Telegram (Synchronously wait for it)
        filename = f"Agreement_{client_data['first_name']}.docx"
        caption = f"New Agreement: {client_data['first_name']} {client_data['last_name']}"
        
        # We use asyncio.run to execute the async telegram function within this sync route
        asyncio.run(send_file_to_telegram(doc_stream, filename, caption))

        return """
            <div style="text-align:center; padding:50px; font-family:sans-serif;">
                <h1 style="color:green;">Agreement Sent Successfully!</h1>
                <p>The document has been generated and forwarded to the admin.</p>
                <a href="/">Back</a>
            </div>
        """

    except Exception as e:
        return f"Error: {str(e)}", 500
    finally:
        # Cleanup
        if signature_path and os.path.exists(signature_path):
            os.remove(signature_path)

if __name__ == '__main__':
    app.run(debug=True)