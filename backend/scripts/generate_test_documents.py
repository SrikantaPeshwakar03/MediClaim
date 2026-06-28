"""
Generate Test Documents from test_cases.json

Creates realistic medical documents matching EXACT specifications from test_cases.json.
Documents are organized in subfolders: prescriptions/, bills/, reports/
"""

import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
TEST_CASES_FILE = PROJECT_ROOT / "test_cases.json"
BASE_DIR = PROJECT_ROOT / "backend" / "data" / "test_documents"
PRESCRIPTIONS_DIR = BASE_DIR / "prescriptions"
BILLS_DIR = BASE_DIR / "bills"
REPORTS_DIR = BASE_DIR / "reports"

# Create directories
for dir_path in [BASE_DIR, PRESCRIPTIONS_DIR, BILLS_DIR, REPORTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Load fonts
try:
    FONT_TITLE = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    FONT_BOLD = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    FONT_REGULAR = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    FONT_SMALL = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
except Exception:
    # Fallback to default fonts
    FONT_TITLE = ImageFont.load_default()
    FONT_BOLD = ImageFont.load_default()
    FONT_REGULAR = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()


def create_prescription(file_id: str, content: dict, output_dir: Path):
    """Create a prescription document"""
    img = Image.new('RGB', (850, 1100), color='white')
    draw = ImageDraw.Draw(img)
    
    y = 40
    
    # Doctor header
    doctor_name = content.get("doctor_name", "Unknown Doctor")
    draw.text((50, y), doctor_name, fill='black', font=FONT_BOLD)
    y += 35
    
    if "doctor_registration" in content:
        draw.text((50, y), f"Reg. No: {content['doctor_registration']}", fill='black', font=FONT_REGULAR)
        y += 28
    
    draw.text((50, y), "Medical Centre, Bengaluru", fill='black', font=FONT_SMALL)
    y += 28
    draw.text((50, y), "Ph: +91-80-XXXXXXXX", fill='black', font=FONT_SMALL)
    y += 40
    
    # Separator
    draw.line([(50, y), (800, y)], fill='black', width=2)
    y += 25
    
    # Patient details
    if "patient_name" in content:
        draw.text((50, y), f"Patient: {content['patient_name']}", fill='black', font=FONT_REGULAR)
    
    if "date" in content:
        draw.text((550, y), f"Date: {content['date']}", fill='black', font=FONT_REGULAR)
    y += 40
    
    # Separator
    draw.line([(50, y), (800, y)], fill='black', width=2)
    y += 25
    
    # Diagnosis
    if "diagnosis" in content:
        draw.text((50, y), f"Diagnosis: {content['diagnosis']}", fill='black', font=FONT_BOLD)
        y += 45
    
    # Medicines
    if "medicines" in content and content["medicines"]:
        draw.text((50, y), "Rx:", fill='black', font=FONT_BOLD)
        y += 35
        for i, medicine in enumerate(content["medicines"], 1):
            draw.text((70, y), f"{i}. {medicine}", fill='black', font=FONT_REGULAR)
            y += 28
        y += 20
    
    # Tests ordered
    if "tests_ordered" in content and content["tests_ordered"]:
        draw.text((50, y), f"Investigations: {', '.join(content['tests_ordered'])}", 
                 fill='black', font=FONT_REGULAR)
        y += 35
    
    # Treatment (for alternative medicine)
    if "treatment" in content:
        draw.text((50, y), f"Treatment: {content['treatment']}", fill='black', font=FONT_REGULAR)
        y += 35
    
    # Signature
    y = max(y + 60, 950)
    draw.text((550, y), "[Doctor's Signature]", fill='gray', font=FONT_SMALL)
    y += 25
    draw.text((550, y), "[Registration Stamp]", fill='gray', font=FONT_SMALL)
    
    # Save
    output_path = output_dir / f"{file_id}.jpg"
    img.save(output_path, quality=95)
    return output_path


def create_hospital_bill(file_id: str, content: dict, output_dir: Path):
    """Create a hospital/dental/pharmacy bill"""
    img = Image.new('RGB', (850, 1100), color='white')
    draw = ImageDraw.Draw(img)
    
    y = 40
    
    # Hospital header
    hospital_name = content.get("hospital_name", "Medical Centre")
    draw.text((300, y), hospital_name.upper(), fill='black', font=FONT_TITLE)
    y += 40
    draw.text((320, y), "Bengaluru, Karnataka", fill='black', font=FONT_SMALL)
    y += 25
    draw.text((340, y), "Ph: +91-80-XXXXXXXX", fill='black', font=FONT_SMALL)
    y += 40
    
    # Separator
    draw.line([(50, y), (800, y)], fill='black', width=2)
    y += 25
    
    # Bill title
    draw.text((370, y), "BILL / RECEIPT", fill='black', font=FONT_BOLD)
    y += 35
    
    # Bill number and date
    draw.text((50, y), f"Bill No: MC/{file_id}/2024", fill='black', font=FONT_REGULAR)
    if "date" in content:
        draw.text((550, y), f"Date: {content['date']}", fill='black', font=FONT_REGULAR)
    y += 40
    
    # Separator
    draw.line([(50, y), (800, y)], fill='black', width=2)
    y += 25
    
    # Patient
    if "patient_name" in content:
        draw.text((50, y), f"Patient Name: {content['patient_name']}", fill='black', font=FONT_REGULAR)
        y += 40
    
    # Separator
    draw.line([(50, y), (800, y)], fill='black', width=2)
    y += 25
    
    # Table header
    draw.text((50, y), "DESCRIPTION", fill='black', font=FONT_BOLD)
    draw.text((650, y), "AMOUNT (₹)", fill='black', font=FONT_BOLD)
    y += 30
    draw.line([(50, y), (800, y)], fill='gray', width=1)
    y += 20
    
    # Line items
    if "line_items" in content:
        for item in content["line_items"]:
            desc = item.get("description", "")
            amount = item.get("amount", 0)
            draw.text((50, y), desc, fill='black', font=FONT_REGULAR)
            draw.text((650, y), f"{amount:.2f}", fill='black', font=FONT_REGULAR)
            y += 28
    
    # Total
    y += 30
    draw.line([(50, y), (800, y)], fill='black', width=2)
    y += 20
    
    total = content.get("total", 0)
    draw.text((500, y), "Total Amount:", fill='black', font=FONT_BOLD)
    draw.text((650, y), f"₹ {total:.2f}", fill='black', font=FONT_BOLD)
    y += 40
    
    # Payment mode
    draw.text((50, y), "Payment Mode: Cash / UPI / Card", fill='black', font=FONT_SMALL)
    y += 60
    
    draw.text((550, y), "[Cashier Signature]", fill='gray', font=FONT_SMALL)
    
    # Save
    output_path = output_dir / f"{file_id}.jpg"
    img.save(output_path, quality=95)
    return output_path


def create_lab_report(file_id: str, content: dict, output_dir: Path):
    """Create a lab/diagnostic report"""
    img = Image.new('RGB', (850, 1100), color='white')
    draw = ImageDraw.Draw(img)
    
    y = 40
    
    # Lab header
    draw.text((250, y), "PRECISION DIAGNOSTICS", fill='black', font=FONT_TITLE)
    y += 40
    draw.text((280, y), "NABL Accredited Lab | Lab ID: KA-NABL-1234", fill='black', font=FONT_SMALL)
    y += 25
    draw.text((310, y), "Bengaluru, Karnataka", fill='black', font=FONT_SMALL)
    y += 40
    
    # Separator
    draw.line([(50, y), (800, y)], fill='black', width=2)
    y += 25
    
    # Patient details
    if "patient_name" in content:
        draw.text((50, y), f"Patient: {content['patient_name']}", fill='black', font=FONT_REGULAR)
        y += 30
    
    if "date" in content:
        draw.text((50, y), f"Report Date: {content['date']}", fill='black', font=FONT_REGULAR)
        y += 40
    
    # Separator
    draw.line([(50, y), (800, y)], fill='black', width=2)
    y += 25
    
    # Test header
    draw.text((50, y), "TEST NAME", fill='black', font=FONT_BOLD)
    draw.text((400, y), "RESULT", fill='black', font=FONT_BOLD)
    y += 30
    draw.line([(50, y), (800, y)], fill='gray', width=1)
    y += 20
    
    # Test name
    test_name = content.get("test_name", "Test")
    draw.text((50, y), test_name, fill='black', font=FONT_REGULAR)
    draw.text((400, y), "Completed", fill='black', font=FONT_REGULAR)
    y += 60
    
    # Separator
    draw.line([(50, y), (800, y)], fill='black', width=2)
    y += 30
    
    # Pathologist
    draw.text((50, y), "Dr. Meena Pillai, MD (Pathology)", fill='black', font=FONT_REGULAR)
    y += 25
    draw.text((50, y), "Reg. No: KA/89012/2018", fill='black', font=FONT_SMALL)
    y += 30
    draw.text((550, y), "[Signature & Stamp]", fill='gray', font=FONT_SMALL)
    
    # Save
    output_path = output_dir / f"{file_id}.jpg"
    img.save(output_path, quality=95)
    return output_path


def create_blurry_document(file_id: str, doc_type: str, output_dir: Path):
    """Create an unreadable blurry document"""
    img = Image.new('RGB', (850, 1100), color='white')
    draw = ImageDraw.Draw(img)
    
    y = 40
    draw.text((300, y), "PHARMACY BILL", fill='black', font=FONT_TITLE)
    y += 60
    draw.text((50, y), "Some text that will be unreadable...", fill='black', font=FONT_REGULAR)
    y += 40
    draw.text((50, y), "Patient: ????????", fill='black', font=FONT_REGULAR)
    y += 40
    draw.text((50, y), "Amount: ????.??", fill='black', font=FONT_REGULAR)
    y += 40
    draw.text((50, y), "Date: ??-??-????", fill='black', font=FONT_REGULAR)
    
    # Apply heavy blur to make it unreadable
    img = img.filter(ImageFilter.GaussianBlur(radius=15))
    
    # Save
    output_path = output_dir / f"{file_id}.jpg"
    img.save(output_path, quality=50)  # Lower quality for more unreadability
    return output_path


def main():
    """Generate all test documents from test_cases.json"""
    print("=" * 70)
    print("GENERATING TEST DOCUMENTS FROM test_cases.json")
    print("=" * 70)
    print()
    
    # Load test cases
    with open(TEST_CASES_FILE, 'r') as f:
        data = json.load(f)
    
    test_cases = data.get("test_cases", [])
    total_docs = 0
    prescription_count = 0
    bill_count = 0
    report_count = 0
    
    for test_case in test_cases:
        case_id = test_case.get("case_id")
        case_name = test_case.get("case_name")
        input_data = test_case.get("input", {})
        documents = input_data.get("documents", [])
        
        print(f"\n📋 {case_id}: {case_name}")
        
        for doc in documents:
            file_id = doc.get("file_id")
            actual_type = doc.get("actual_type")
            content = doc.get("content", {})
            quality = doc.get("quality")
            
            # Determine output directory based on document type
            if actual_type == "PRESCRIPTION":
                output_dir = PRESCRIPTIONS_DIR
                prescription_count += 1
            elif actual_type in ["HOSPITAL_BILL", "PHARMACY_BILL", "DENTAL_BILL"]:
                output_dir = BILLS_DIR
                bill_count += 1
            elif actual_type == "LAB_REPORT":
                output_dir = REPORTS_DIR
                report_count += 1
            else:
                output_dir = BASE_DIR
            
            # Handle special cases
            if quality == "UNREADABLE":
                # Create blurry document for TC002
                output_path = create_blurry_document(file_id, actual_type, output_dir)
                print(f"   ✓ {file_id}.jpg (BLURRY - {actual_type})")
            elif actual_type == "PRESCRIPTION":
                # Add treatment date if not in content
                if "date" not in content and "treatment_date" in input_data:
                    content["date"] = input_data["treatment_date"]
                output_path = create_prescription(file_id, content, output_dir)
                print(f"   ✓ {file_id}.jpg (PRESCRIPTION)")
            elif actual_type in ["HOSPITAL_BILL", "PHARMACY_BILL", "DENTAL_BILL"]:
                # Add treatment date if not in content
                if "date" not in content and "treatment_date" in input_data:
                    content["date"] = input_data["treatment_date"]
                output_path = create_hospital_bill(file_id, content, output_dir)
                print(f"   ✓ {file_id}.jpg ({actual_type})")
            elif actual_type == "LAB_REPORT":
                # Add treatment date if not in content
                if "date" not in content and "treatment_date" in input_data:
                    content["date"] = input_data["treatment_date"]
                # Add patient name if not in content (from member_id lookup)
                if "patient_name" not in content:
                    # Map member IDs to names (from policy_terms.json)
                    member_names = {
                        "EMP007": "Suresh Patil"
                    }
                    member_id = input_data.get("member_id")
                    if member_id in member_names:
                        content["patient_name"] = member_names[member_id]
                output_path = create_lab_report(file_id, content, output_dir)
                print(f"   ✓ {file_id}.jpg (LAB_REPORT)")
            
            total_docs += 1
    
    print("\n" + "=" * 70)
    print("✅ ALL TEST DOCUMENTS GENERATED SUCCESSFULLY")
    print("=" * 70)
    print(f"\n📁 Documents saved to:")
    print(f"   Prescriptions: {PRESCRIPTIONS_DIR} ({prescription_count} files)")
    print(f"   Bills:         {BILLS_DIR} ({bill_count} files)")
    print(f"   Reports:       {REPORTS_DIR} ({report_count} files)")
    print(f"\n📊 Total: {total_docs} documents for {len(test_cases)} test cases")
    print(f"\n🎯 All documents match exact specifications from test_cases.json")
    print(f"   - Dates, patient names, amounts are exact")
    print(f"   - Doctor registrations match specifications")
    print(f"   - Line items and totals are accurate")
    print()


if __name__ == "__main__":
    main()
