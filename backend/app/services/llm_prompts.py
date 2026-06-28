"""
LLM Prompts

Prompt templates for various LLM-based extraction and classification tasks.
"""

from typing import Dict, Any
from ..models import DocumentType


# === Document Classification ===

DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT = """You are an expert at classifying medical documents from India.

Your task is to identify the type of document from its text content.

Valid document types:
- PRESCRIPTION: Doctor's prescription with medicines or treatment plan (includes Allopathy, Ayurveda, Homeopathy, Unani, etc.)
- HOSPITAL_BILL: Bill/invoice from hospital, clinic, or wellness center
- PHARMACY_BILL: Bill from pharmacy for medicines
- LAB_REPORT: Laboratory test results (CBC, X-ray, MRI, CT scan, ultrasound, etc.)
- DIAGNOSTIC_REPORT: Diagnostic reports (same as lab report)
- DISCHARGE_SUMMARY: Hospital discharge summary
- DENTAL_REPORT: Dental treatment report
- UNKNOWN: Cannot determine type

Key indicators:
- PRESCRIPTION: Contains doctor name, registration number, diagnosis, medicines/treatment prescribed, or phrases like "Rx:", "prescribed", "treatment advised"
- HOSPITAL_BILL: Contains total amount, itemized charges, hospital/clinic name, bill number, GST details
- LAB_REPORT: Contains test names, results, normal ranges, lab accreditation details

Be flexible with format variations. Alternative medicine practitioners (Ayurveda, Homeopathy) may use titles like "Vaidya" or have different registration formats (e.g., AYUR/STATE/NUMBER/YEAR).

Return ONLY the document type name, nothing else."""


def get_document_classification_prompt(text: str) -> str:
    """Get prompt for document classification"""
    return f"""Classify this medical document:

{text[:2000]}

Document type:"""


# === Structured Extraction by Document Type ===

PRESCRIPTION_EXTRACTION_SCHEMA = """{
  "doctor_name": "string or null",
  "doctor_registration": "string (format: STATE/NUMBER/YEAR) or null",
  "specialization": "string or null",
  "clinic_name": "string or null",
  "patient_name": "string or null",
  "patient_age": "integer or null",
  "patient_gender": "string (M/F) or null",
  "date": "string (YYYY-MM-DD if possible) or null",
  "diagnosis": "string or null",
  "medicines": ["list of medicine names"],
  "tests_ordered": ["list of tests/investigations ordered"]
}"""

HOSPITAL_BILL_EXTRACTION_SCHEMA = """{
  "hospital_name": "string or null",
  "hospital_address": "string or null",
  "gstin": "string or null",
  "bill_number": "string or null",
  "bill_date": "string (YYYY-MM-DD if possible) or null",
  "patient_name": "string or null",
  "patient_age": "integer or null",
  "patient_gender": "string (M/F) or null",
  "referring_doctor": "string or null",
  "line_items": [
    {
      "description": "string",
      "quantity": "number or null",
      "rate": "number or null",
      "amount": "number"
    }
  ],
  "subtotal": "number or null",
  "gst_amount": "number or null",
  "total_amount": "number or null",
  "payment_mode": "string or null"
}"""

LAB_REPORT_EXTRACTION_SCHEMA = """{
  "lab_name": "string or null",
  "nabl_accredited": "boolean or null",
  "patient_name": "string or null",
  "patient_age": "integer or null",
  "patient_gender": "string (M/F) or null",
  "referring_doctor": "string or null",
  "sample_date": "string (YYYY-MM-DD if possible) or null",
  "report_date": "string (YYYY-MM-DD if possible) or null",
  "sample_id": "string or null",
  "tests": [
    {
      "test_name": "string",
      "result": "string",
      "unit": "string or null",
      "normal_range": "string or null"
    }
  ],
  "pathologist_name": "string or null",
  "pathologist_registration": "string or null",
  "remarks": "string or null"
}"""

PHARMACY_BILL_EXTRACTION_SCHEMA = """{
  "pharmacy_name": "string or null",
  "drug_license": "string or null",
  "bill_number": "string or null",
  "bill_date": "string (YYYY-MM-DD if possible) or null",
  "patient_name": "string or null",
  "prescribing_doctor": "string or null",
  "medicines": [
    {
      "medicine": "string",
      "batch": "string or null",
      "expiry": "string or null",
      "quantity": "number or null",
      "mrp": "number or null",
      "amount": "number"
    }
  ],
  "subtotal": "number or null",
  "discount": "number or null",
  "net_amount": "number or null",
  "pharmacist_name": "string or null"
}"""


EXTRACTION_SYSTEM_PROMPT = """You are an expert at extracting structured information from Indian medical documents.

Your task is to extract specific fields from the document text and return them in JSON format.

Guidelines:
- Extract ONLY information that is clearly present in the text
- Use null for missing or unclear fields
- For amounts, extract numeric values only (remove ₹, Rs., commas)
- For dates, convert to YYYY-MM-DD format when possible
- For patient names, extract the full name as written
- Be precise and accurate
- If a field has multiple values, extract all of them
- For line items, extract all items found

Handling real-world Indian medical documents (IMPORTANT):
- MEDICAL SHORTHAND: Expand common abbreviations to their full form in the
  `diagnosis` field so downstream rules can match them. Examples:
  HTN -> Hypertension, T2DM / DM2 -> Type 2 Diabetes Mellitus,
  URI -> Upper Respiratory Infection, OA -> Osteoarthritis,
  GERD -> Gastroesophageal Reflux Disease, COPD -> Chronic Obstructive Pulmonary Disease,
  CA -> Carcinoma, K/C/O -> Known Case Of. Keep the original text too if unsure.
- HANDWRITTEN / BLURRY TEXT: Make a best-effort transcription. Never invent
  values; if a field is illegible, set it to null rather than guessing.
- RUBBER STAMPS / OBSCURED TEXT: If a value (e.g. registration number or amount)
  is partially obscured by a stamp, extract what is legible and leave the rest null.
- MULTILINGUAL DOCUMENTS (Hindi/Tamil/Telugu mixed with English): Extract the
  English fields. Do not translate regional-language text; leave such fields null.
- PARTIAL DOCUMENTS: Extract whatever fields are present; use null for anything
  cut off or missing.
- CORRECTIONS / CROSSED-OUT AMOUNTS: Prefer the final (corrected) value; if both
  an original and corrected value are visible, use the corrected one.

Return valid JSON matching the schema provided."""


def get_extraction_prompt(document_type: DocumentType, text: str) -> tuple[str, str]:
    """
    Get system prompt and user prompt for structured extraction.
    
    Args:
        document_type: Type of document
        text: Raw OCR text
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    schema_map = {
        DocumentType.PRESCRIPTION: PRESCRIPTION_EXTRACTION_SCHEMA,
        DocumentType.HOSPITAL_BILL: HOSPITAL_BILL_EXTRACTION_SCHEMA,
        DocumentType.LAB_REPORT: LAB_REPORT_EXTRACTION_SCHEMA,
        DocumentType.DIAGNOSTIC_REPORT: LAB_REPORT_EXTRACTION_SCHEMA,
        DocumentType.PHARMACY_BILL: PHARMACY_BILL_EXTRACTION_SCHEMA,
    }
    
    schema = schema_map.get(document_type, "{}")
    
    user_prompt = f"""Extract structured data from this {document_type.value}:

{text}

Expected JSON schema:
{schema}

Extracted data (valid JSON only):"""
    
    return EXTRACTION_SYSTEM_PROMPT, user_prompt


# === Vision-based Extraction (handwritten / messy documents) ===

VISION_EXTRACTION_SYSTEM_PROMPT = """You are an expert at reading Indian medical documents from IMAGES, including
handwritten prescriptions, phone photos, scanned bills, and documents with stamps.

Read the document image carefully and extract the requested fields as JSON.

Rules:
- Transcribe handwriting to the best of your ability; never invent values. If a
  field is illegible, set it to null.
- Expand medical shorthand in the diagnosis (HTN -> Hypertension,
  T2DM -> Type 2 Diabetes Mellitus, URI, COPD, GERD, OA, etc.).
- For amounts, return numbers only (no ₹, Rs., or commas). Prefer corrected
  values over crossed-out ones.
- For multilingual documents, extract the English fields and leave
  regional-language-only fields as null.
- If a rubber stamp obscures text (e.g. a registration number), extract what is
  legible and null the rest.

ALSO inspect the image for document-integrity issues and report them in an
"integrity_flags" array. Use these values when present:
- "CROSSED_OUT_AMOUNT" (an amount is struck through / overwritten)
- "DUPLICATE_STAMP" (both ORIGINAL and DUPLICATE stamps, or multiple copies)
- "HANDWRITTEN_ALTERATION" (visible manual edits to printed values)
- "ILLEGIBLE_REGION" (a meaningful region is unreadable)
Leave the array empty if none are observed.

Return ONLY valid JSON."""


def get_vision_extraction_prompt(document_type: DocumentType) -> tuple[str, str]:
    """
    Get (system_prompt, user_prompt) for vision-based extraction from an image.
    The schema is the same as text extraction plus an `integrity_flags` array.
    """
    schema_map = {
        DocumentType.PRESCRIPTION: PRESCRIPTION_EXTRACTION_SCHEMA,
        DocumentType.HOSPITAL_BILL: HOSPITAL_BILL_EXTRACTION_SCHEMA,
        DocumentType.LAB_REPORT: LAB_REPORT_EXTRACTION_SCHEMA,
        DocumentType.DIAGNOSTIC_REPORT: LAB_REPORT_EXTRACTION_SCHEMA,
        DocumentType.PHARMACY_BILL: PHARMACY_BILL_EXTRACTION_SCHEMA,
    }
    schema = schema_map.get(document_type, "{}")

    # Add integrity_flags to the expected schema
    schema_with_integrity = schema.rstrip().rstrip("}") + ',\n  "integrity_flags": ["list of integrity issue codes, may be empty"]\n}'

    user_prompt = f"""This image is a {document_type.value}. Extract the fields below.

Expected JSON schema:
{schema_with_integrity}

Extracted data (valid JSON only):"""

    return VISION_EXTRACTION_SYSTEM_PROMPT, user_prompt


# === Patient Name Consistency Check ===

PATIENT_NAME_CHECK_SYSTEM_PROMPT = """You are an expert at comparing patient names from medical documents.

Your task is to determine if the patient names from different documents belong to the same person.

Consider:
- Name variations (e.g., "Rajesh Kumar" vs "R. Kumar" vs "Rajesh")
- Spelling variations
- Middle name presence/absence
- Title differences (Mr., Mrs., etc.)

Return your response in this JSON format:
{
  "same_person": true/false,
  "confidence": 0.0-1.0,
  "explanation": "Brief explanation of your decision"
}"""


def get_patient_name_check_prompt(names: list[str]) -> str:
    """Get prompt for patient name consistency check"""
    names_list = "\n".join([f"- {name}" for name in names])
    return f"""Are these names from different documents referring to the same patient?

Names found:
{names_list}

Analysis (valid JSON only):"""


# === Diagnosis Extraction ===

DIAGNOSIS_EXTRACTION_SYSTEM_PROMPT = """You are a medical expert analyzing diagnoses from medical documents.

Extract the primary diagnosis and any secondary diagnoses mentioned.

Return JSON in this format:
{{
  "primary_diagnosis": "string",
  "secondary_diagnoses": ["list of strings"],
  "condition_categories": ["list of general categories like 'diabetes', 'hypertension', etc."]
}}"""


def get_diagnosis_extraction_prompt(text: str) -> str:
    """Get prompt for diagnosis extraction"""
    return f"""Extract all diagnoses from this medical text:

{text}

Extracted diagnoses (valid JSON only):"""


# === Line Item Classification (for partial approvals) ===

LINE_ITEM_CLASSIFICATION_SYSTEM_PROMPT = """You are an expert at classifying medical bill line items.

Your task is to categorize each line item as:
- COVERED: Medical treatment/test/procedure that is typically covered by insurance
- COSMETIC: Cosmetic or aesthetic procedure (not covered)
- PREVENTIVE: Preventive care (may have special rules)
- UNCLEAR: Cannot determine

For DENTAL items, specifically identify:
- Teeth Whitening (COSMETIC)
- Veneers (COSMETIC)
- Orthodontic Treatment/Braces (COSMETIC)
- Root Canal Treatment (COVERED)
- Tooth Extraction (COVERED)
- Dental Filling (COVERED)
- Scaling (COVERED)
- Crown Placement (COVERED)

Return JSON array:
[
  {
    "item_description": "string",
    "category": "COVERED/COSMETIC/PREVENTIVE/UNCLEAR",
    "reasoning": "brief explanation"
  }
]"""


def get_line_item_classification_prompt(line_items: list[str]) -> str:
    """Get prompt for line item classification"""
    items_list = "\n".join([f"{i+1}. {item}" for i, item in enumerate(line_items)])
    return f"""Classify each of these medical bill line items:

{items_list}

Classification (valid JSON only):"""
