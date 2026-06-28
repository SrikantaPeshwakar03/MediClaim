# Test Documents

This directory contains **24 medical document images** generated from the exact specifications in `test_cases.json`. These documents are used to test the AI claims processing system across all 12 test cases.

## 📁 Folder Structure

```
test_documents/
├── prescriptions/    # 12 prescription documents
├── bills/           # 11 hospital/dental/pharmacy bills
└── reports/         # 1 lab/diagnostic report
```

## 📋 Document Mapping by Test Case

### TC001: Wrong Document Uploaded
- `prescriptions/F001.jpg` - Dr. Sharma prescription for Rajesh Kumar
- `prescriptions/F002.jpg` - Another prescription (wrong document type)

### TC002: Unreadable Document
- `prescriptions/F003.jpg` - Valid prescription (good quality)
- `bills/F004.jpg` - **BLURRY pharmacy bill** (unreadable, intentional)

### TC003: Documents Belong to Different Patients
- `prescriptions/F005.jpg` - Prescription for **Rajesh Kumar**
- `bills/F006.jpg` - Bill for **Arjun Mehta** (different patient - should fail)

### TC004: Clean Consultation — Full Approval
- `prescriptions/F007.jpg` - Dr. Arun Sharma, Viral Fever, 2024-11-01
- `bills/F008.jpg` - City Clinic bill, ₹1,500 (Consultation + CBC + Dengue test)

### TC005: Waiting Period — Diabetes
- `prescriptions/F009.jpg` - Dr. Sunil Mehta, Type 2 Diabetes, 2024-10-15
- `bills/F010.jpg` - ₹3,000 consultation bill for Vikram Joshi

### TC006: Dental Partial Approval — Cosmetic Exclusion
- `bills/F011.jpg` - Smile Dental Clinic, ₹12,000 (Root Canal ₹8k + Teeth Whitening ₹4k)

### TC007: MRI Without Pre-Authorization
- `prescriptions/F012.jpg` - Dr. Venkat Rao, Lumbar Disc Herniation, MRI ordered
- `reports/F013.jpg` - MRI Lumbar Spine lab report
- `bills/F014.jpg` - ₹15,000 MRI bill (requires pre-auth above ₹10k)

### TC008: Per-Claim Limit Exceeded
- `prescriptions/F015.jpg` - Dr. R. Gupta, Gastroenteritis, 2024-10-20
- `bills/F016.jpg` - ₹7,500 bill (exceeds ₹5,000 per-claim limit)

### TC009: Fraud Signal — Multiple Same-Day Claims
- `prescriptions/F017.jpg` - Dr. S. Khan, Migraine, 2024-10-30
- `bills/F018.jpg` - ₹4,800 bill (4th claim on same day - fraud signal)

### TC010: Network Hospital — Discount Applied
- `prescriptions/F019.jpg` - Dr. S. Iyer, Acute Bronchitis, 2024-11-03
- `bills/F020.jpg` - Apollo Hospitals, ₹4,500 (network discount applies)

### TC011: Component Failure — Graceful Degradation
- `prescriptions/F021.jpg` - Vaidya T. Krishnan (Ayurveda), Chronic Joint Pain
- `bills/F022.jpg` - Ayur Wellness Centre, ₹4,000 (Panchakarma therapy)

### TC012: Excluded Treatment
- `prescriptions/F023.jpg` - Dr. P. Banerjee, Morbid Obesity (BMI 37)
- `bills/F024.jpg` - ₹8,000 (Bariatric consultation + diet program - excluded)

## ✅ Document Specifications

All documents match the exact specifications from `test_cases.json`:

| Aspect | Status |
|--------|--------|
| **Dates** | ✅ Exact match from test cases |
| **Patient Names** | ✅ Exact match (including mismatches for TC003) |
| **Doctor Names** | ✅ Complete with registration numbers |
| **Diagnosis** | ✅ Exact medical terms from specs |
| **Amounts** | ✅ Accurate to the rupee |
| **Line Items** | ✅ Complete breakdown where specified |
| **Document Quality** | ✅ Includes intentional blur for TC002 |

## 🎯 Special Test Documents

- **F004.jpg**: Intentionally blurry and unreadable (TC002)
- **F006.jpg**: Patient name mismatch - "Arjun Mehta" instead of "Rajesh Kumar" (TC003)
- **F021.jpg**: Ayurvedic registration format `AYUR/KL/2345/2019` (TC011)

## 🔄 Regenerating Documents

To regenerate all documents from `test_cases.json`:

```bash
python3 backend/scripts/generate_test_documents.py
```

This will overwrite all existing documents with fresh ones matching the current specifications.

## 📝 Notes

1. All images are JPG format (850x1100px) for realistic medical document size
2. Font sizes and layouts mimic real Indian medical documents
3. Registration numbers follow state-specific formats (KA/, GJ/, AP/, etc.)
4. Currency is in Indian Rupees (₹)
5. Dates are in YYYY-MM-DD format matching the policy period (2024-04 to 2025-03)

---

**Total Documents**: 24 files  
**Test Cases Covered**: 12 (TC001 - TC012)  
**Generation Date**: Auto-generated from test_cases.json
