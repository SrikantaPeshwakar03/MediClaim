"""
Create Mock Medical Documents for Testing

Generates realistic Indian medical documents (prescriptions, bills, lab reports)
as images for testing the OCR and document verification pipeline.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import random
from datetime import datetime, timedelta

# Create output directory
OUTPUT_DIR = Path(__file__).parent.parent.parent / "test_documents"
OUTPUT_DIR.mkdir(exist_ok=True)

# Try to load a font, fallback to default if not available
try:
    # Try to use a system font
    FONT_REGULAR = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    FONT_BOLD = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    FONT_SMALL = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    FONT_TITLE = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
except:
    # Fallback to default font
    FONT_REGULAR = ImageFont.load_default()
    FONT_BOLD = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    FONT_TITLE = ImageFont.load_default()


def create_prescription(
    doctor_name: str,
    registration_no: str,
    patient_name: str,
    age: int,
    gender: str,
    diagnosis: str,
    medicines: list,
    date: str,
    filename: str
):
    """Create a mock prescription image"""
    # Create image
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    y = 30
    
    # Header - Doctor details
    draw.text((50, y), f"Dr. {doctor_name}, MBBS, MD (Internal Medicine)", fill='black', font=FONT_BOLD)
    y += 30
    draw.text((50, y), f"Reg. No: {registration_no}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), "City Medical Centre, 12 MG Road, Bengaluru", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), "Ph: +91-80-12345678", fill='black', font=FONT_SMALL)
    y += 35
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Patient details
    draw.text((50, y), f"Patient: {patient_name}", fill='black', font=FONT_REGULAR)
    draw.text((500, y), f"Date: {date}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), f"Age: {age} years   Gender: {gender}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), f"Chief Complaint: Fever since 3 days, body ache", fill='black', font=FONT_SMALL)
    y += 35
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Diagnosis
    draw.text((50, y), f"Diagnosis: {diagnosis}", fill='black', font=FONT_BOLD)
    y += 40
    
    # Rx
    draw.text((50, y), "Rx:", fill='black', font=FONT_BOLD)
    y += 30
    
    for i, med in enumerate(medicines, 1):
        draw.text((50, y), f"{i}. {med}", fill='black', font=FONT_REGULAR)
        y += 25
    
    y += 20
    draw.text((50, y), "Investigations: CBC, Dengue NS1", fill='black', font=FONT_SMALL)
    y += 25
    draw.text((50, y), "Follow-up: After 5 days if no improvement", fill='black', font=FONT_SMALL)
    y += 80
    
    # Signature area
    draw.text((500, y), "[Doctor's Signature]", fill='gray', font=FONT_SMALL)
    y += 25
    draw.text((500, y), "[Registration Stamp]", fill='gray', font=FONT_SMALL)
    
    # Save
    img.save(OUTPUT_DIR / filename)
    print(f"✓ Created: {filename}")


def create_hospital_bill(
    hospital_name: str,
    patient_name: str,
    age: int,
    gender: str,
    bill_no: str,
    date: str,
    line_items: list,
    total: float,
    filename: str
):
    """Create a mock hospital bill image"""
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    y = 30
    
    # Header
    draw.text((300, y), hospital_name.upper(), fill='black', font=FONT_TITLE)
    y += 35
    draw.text((250, y), "12 MG Road, Bengaluru – 560001", fill='black', font=FONT_SMALL)
    y += 20
    draw.text((280, y), "GSTIN: 29XXXXX1234X1ZX", fill='black', font=FONT_SMALL)
    y += 20
    draw.text((310, y), "Ph: 080-12345678", fill='black', font=FONT_SMALL)
    y += 40
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Bill title
    draw.text((350, y), "BILL / RECEIPT", fill='black', font=FONT_BOLD)
    y += 30
    
    # Bill details
    draw.text((50, y), f"Bill No: {bill_no}", fill='black', font=FONT_REGULAR)
    draw.text((500, y), f"Date: {date}", fill='black', font=FONT_REGULAR)
    y += 35
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Patient details
    draw.text((50, y), f"Patient Name: {patient_name}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), f"Age/Gender: {age} / {gender}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), "Referring Doctor: Dr. Arun Sharma", fill='black', font=FONT_REGULAR)
    y += 35
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Table header
    draw.text((50, y), "DESCRIPTION", fill='black', font=FONT_BOLD)
    draw.text((400, y), "QTY", fill='black', font=FONT_BOLD)
    draw.text((500, y), "RATE", fill='black', font=FONT_BOLD)
    draw.text((650, y), "AMOUNT", fill='black', font=FONT_BOLD)
    y += 25
    
    # Line items
    for item in line_items:
        draw.text((50, y), item['description'], fill='black', font=FONT_REGULAR)
        draw.text((400, y), str(item['qty']), fill='black', font=FONT_REGULAR)
        draw.text((500, y), f"{item['rate']:.2f}", fill='black', font=FONT_REGULAR)
        draw.text((650, y), f"{item['amount']:.2f}", fill='black', font=FONT_REGULAR)
        y += 25
    
    y += 20
    
    # Subtotal and total
    draw.text((500, y), "Subtotal:", fill='black', font=FONT_REGULAR)
    draw.text((650, y), f"{total:.2f}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((500, y), "GST (0% on medical):", fill='black', font=FONT_SMALL)
    draw.text((650, y), "0.00", fill='black', font=FONT_SMALL)
    y += 25
    draw.text((500, y), "Total Amount:", fill='black', font=FONT_BOLD)
    draw.text((650, y), f"{total:.2f}", fill='black', font=FONT_BOLD)
    y += 40
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Payment details
    draw.text((50, y), "Payment Mode: Cash / UPI / Card", fill='black', font=FONT_SMALL)
    y += 25
    draw.text((50, y), "Received by: [Cashier Name]    [Cashier Stamp]", fill='gray', font=FONT_SMALL)
    
    # Save
    img.save(OUTPUT_DIR / filename)
    print(f"✓ Created: {filename}")


def create_pharmacy_bill(
    patient_name: str,
    doctor_name: str,
    bill_no: str,
    date: str,
    medicines: list,
    subtotal: float,
    discount: float,
    filename: str
):
    """Create a mock pharmacy bill image"""
    img = Image.new('RGB', (800, 900), color='white')
    draw = ImageDraw.Draw(img)
    
    y = 30
    
    # Header
    draw.text((280, y), "HEALTH FIRST PHARMACY", fill='black', font=FONT_TITLE)
    y += 35
    draw.text((270, y), "Drug Lic. No: KA-BLR-XXXX", fill='black', font=FONT_SMALL)
    y += 20
    draw.text((290, y), "22 Brigade Road, Bengaluru", fill='black', font=FONT_SMALL)
    y += 40
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Bill details
    draw.text((50, y), f"Bill No: {bill_no}", fill='black', font=FONT_REGULAR)
    draw.text((500, y), f"Date: {date}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), f"Patient: {patient_name}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), f"Dr: {doctor_name}", fill='black', font=FONT_REGULAR)
    y += 35
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Table header
    draw.text((50, y), "MEDICINE", fill='black', font=FONT_BOLD)
    draw.text((300, y), "BATCH", fill='black', font=FONT_BOLD)
    draw.text((400, y), "EXP", fill='black', font=FONT_BOLD)
    draw.text((500, y), "QTY", fill='black', font=FONT_BOLD)
    draw.text((580, y), "MRP", fill='black', font=FONT_BOLD)
    draw.text((680, y), "AMT", fill='black', font=FONT_BOLD)
    y += 25
    
    # Medicines
    for med in medicines:
        draw.text((50, y), med['name'], fill='black', font=FONT_REGULAR)
        draw.text((300, y), med['batch'], fill='black', font=FONT_SMALL)
        draw.text((400, y), med['exp'], fill='black', font=FONT_SMALL)
        draw.text((500, y), str(med['qty']), fill='black', font=FONT_REGULAR)
        draw.text((580, y), f"{med['mrp']:.2f}", fill='black', font=FONT_REGULAR)
        draw.text((680, y), f"{med['amount']:.2f}", fill='black', font=FONT_REGULAR)
        y += 25
    
    y += 20
    
    # Totals
    draw.text((580, y), "Subtotal:", fill='black', font=FONT_REGULAR)
    draw.text((680, y), f"{subtotal:.2f}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((580, y), f"Discount ({discount}%):", fill='black', font=FONT_SMALL)
    draw.text((680, y), f"-{subtotal * discount / 100:.2f}", fill='black', font=FONT_SMALL)
    y += 25
    net = subtotal - (subtotal * discount / 100)
    draw.text((580, y), "Net Amount:", fill='black', font=FONT_BOLD)
    draw.text((680, y), f"{net:.2f}", fill='black', font=FONT_BOLD)
    y += 40
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Footer
    draw.text((50, y), "Pharmacist: R. Sharma   [Stamp]", fill='gray', font=FONT_SMALL)
    
    # Save
    img.save(OUTPUT_DIR / filename)
    print(f"✓ Created: {filename}")


def create_lab_report(
    patient_name: str,
    age: int,
    gender: str,
    doctor_name: str,
    date: str,
    tests: list,
    filename: str
):
    """Create a mock lab report image"""
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    y = 30
    
    # Header
    draw.text((230, y), "PRECISION DIAGNOSTICS PVT LTD", fill='black', font=FONT_TITLE)
    y += 35
    draw.text((250, y), "NABL Accredited Lab   |   Lab ID: KA-NABL-1234", fill='black', font=FONT_SMALL)
    y += 20
    draw.text((280, y), "45 Jayanagar, Bengaluru   |  Ph: 080-12345678", fill='black', font=FONT_SMALL)
    y += 40
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Patient details
    draw.text((50, y), f"Patient: {patient_name}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), f"Age/Sex: {age} / {gender}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), f"Ref Doctor: {doctor_name}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), f"Sample Date: {date}   Report Date: {date}", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), f"Sample ID: PD-2024-{random.randint(10000, 99999)}", fill='black', font=FONT_REGULAR)
    y += 35
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Table header
    draw.text((50, y), "TEST NAME", fill='black', font=FONT_BOLD)
    draw.text((300, y), "RESULT", fill='black', font=FONT_BOLD)
    draw.text((450, y), "UNIT", fill='black', font=FONT_BOLD)
    draw.text((550, y), "NORMAL RANGE", fill='black', font=FONT_BOLD)
    y += 25
    
    # Tests
    for test in tests:
        draw.text((50, y), test['name'], fill='black', font=FONT_REGULAR)
        draw.text((300, y), test['result'], fill='black', font=FONT_REGULAR)
        draw.text((450, y), test.get('unit', '—'), fill='black', font=FONT_SMALL)
        draw.text((550, y), test.get('normal', '—'), fill='black', font=FONT_SMALL)
        y += 25
    
    y += 30
    
    # Horizontal line
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 20
    
    # Remarks
    draw.text((50, y), "Remarks: All values within normal limits.", fill='black', font=FONT_SMALL)
    y += 25
    draw.text((50, y), "Clinical correlation advised.", fill='black', font=FONT_SMALL)
    y += 50
    
    # Signature
    draw.text((50, y), "Dr. Meena Pillai, MD (Pathology)", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), "Reg. No: KA/89012/2018    [Signature & Stamp]", fill='gray', font=FONT_SMALL)
    
    # Save
    img.save(OUTPUT_DIR / filename)
    print(f"✓ Created: {filename}")


def main():
    """Generate all mock documents"""
    print("Creating mock medical documents...\n")
    
    today = datetime.now().strftime("%d-%b-%Y")
    
    # 1. Create prescriptions for different test cases
    print("📄 Creating Prescriptions...")
    
    # TC004 - Clean consultation
    create_prescription(
        doctor_name="Arun Sharma",
        registration_no="KA/45678/2015",
        patient_name="Rajesh Kumar",
        age=39,
        gender="Male",
        diagnosis="Viral Fever",
        medicines=[
            "Tab Paracetamol 650mg — 1-1-1 x 5 days",
            "Tab Vitamin C 500mg — 0-0-1 x 7 days"
        ],
        date=today,
        filename="tc004_prescription.jpg"
    )
    
    # TC005 - Diabetes (waiting period)
    create_prescription(
        doctor_name="Sunil Mehta",
        registration_no="GJ/56789/2014",
        patient_name="Vikram Joshi",
        age=45,
        gender="Male",
        diagnosis="Type 2 Diabetes Mellitus",
        medicines=[
            "Tab Metformin 500mg — 1-0-1 after meals",
            "Tab Glimepiride 1mg — 1-0-0 before breakfast"
        ],
        date="15-Oct-2024",
        filename="tc005_prescription.jpg"
    )
    
    # TC006 - Dental (partial approval)
    create_prescription(
        doctor_name="Priya Nair",
        registration_no="KA/67890/2016",
        patient_name="Priya Singh",
        age=34,
        gender="Female",
        diagnosis="Dental Caries, Aesthetic Consultation",
        medicines=[
            "Tab Amoxicillin 500mg — 1-1-1 x 5 days",
            "Tab Ibuprofen 400mg — 1-1-1 after meals SOS"
        ],
        date="15-Oct-2024",
        filename="tc006_prescription.jpg"
    )
    
    # 2. Create hospital bills
    print("\n💰 Creating Hospital Bills...")
    
    # TC004 - Clean consultation bill
    create_hospital_bill(
        hospital_name="City Medical Centre",
        patient_name="Rajesh Kumar",
        age=39,
        gender="Male",
        bill_no="CMC/2024/08321",
        date=today,
        line_items=[
            {"description": "Consultation Fee (OPD)", "qty": 1, "rate": 1000.00, "amount": 1000.00},
            {"description": "CBC (Complete Blood Count)", "qty": 1, "rate": 300.00, "amount": 300.00},
            {"description": "Dengue NS1 Test", "qty": 1, "rate": 200.00, "amount": 200.00}
        ],
        total=1500.00,
        filename="tc004_hospital_bill.jpg"
    )
    
    # TC006 - Dental bill with mixed procedures
    create_hospital_bill(
        hospital_name="Smile Dental Clinic",
        patient_name="Priya Singh",
        age=34,
        gender="Female",
        bill_no="SDC/2024/05421",
        date="15-Oct-2024",
        line_items=[
            {"description": "Root Canal Treatment", "qty": 1, "rate": 8000.00, "amount": 8000.00},
            {"description": "Teeth Whitening (Cosmetic)", "qty": 1, "rate": 4000.00, "amount": 4000.00}
        ],
        total=12000.00,
        filename="tc006_dental_bill.jpg"
    )
    
    # TC010 - Network hospital (Apollo)
    create_hospital_bill(
        hospital_name="Apollo Hospitals",
        patient_name="Deepak Shah",
        age=44,
        gender="Male",
        bill_no="APL/2024/12345",
        date="03-Nov-2024",
        line_items=[
            {"description": "Consultation Fee", "qty": 1, "rate": 1500.00, "amount": 1500.00},
            {"description": "Medicines", "qty": 1, "rate": 3000.00, "amount": 3000.00}
        ],
        total=4500.00,
        filename="tc010_apollo_bill.jpg"
    )
    
    # 3. Create pharmacy bills
    print("\n💊 Creating Pharmacy Bills...")
    
    create_pharmacy_bill(
        patient_name="Rajesh Kumar",
        doctor_name="Dr. Arun Sharma",
        bill_no="HFP-24-09821",
        date=today,
        medicines=[
            {"name": "Paracetamol 650", "batch": "A2341", "exp": "03/26", "qty": 15, "mrp": 2.50, "amount": 37.50},
            {"name": "Vitamin C 500", "batch": "B7821", "exp": "06/26", "qty": 10, "mrp": 4.00, "amount": 40.00}
        ],
        subtotal=77.50,
        discount=5,
        filename="tc004_pharmacy_bill.jpg"
    )
    
    # 4. Create lab reports
    print("\n🔬 Creating Lab Reports...")
    
    create_lab_report(
        patient_name="Rajesh Kumar",
        age=39,
        gender="Male",
        doctor_name="Dr. Arun Sharma",
        date=today,
        tests=[
            {"name": "Hemoglobin", "result": "13.2", "unit": "g/dL", "normal": "13.0 – 17.0"},
            {"name": "WBC Count", "result": "9,800", "unit": "/μL", "normal": "4,500 – 11,000"},
            {"name": "Platelet Count", "result": "185,000", "unit": "/μL", "normal": "150,000 – 450,000"},
            {"name": "Dengue NS1 Antigen", "result": "NEGATIVE", "unit": "—", "normal": "—"}
        ],
        filename="tc004_lab_report.jpg"
    )
    
    print(f"\n✅ All mock documents created successfully!")
    print(f"📁 Documents saved to: {OUTPUT_DIR}")
    print(f"\nYou can now use these documents to test:")
    print("  - Document verification agent")
    print("  - OCR extraction agent")
    print("  - End-to-end claim processing")


if __name__ == "__main__":
    main()
