"""
Document Models

Pydantic models for documents and OCR results.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from .enums import DocumentType, OCRStatus


class DocumentUpload(BaseModel):
    """Document uploaded by user"""
    file_name: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="MIME type (e.g., image/jpeg)")
    file_size_bytes: int = Field(..., gt=0, description="File size in bytes")
    document_type: Optional[DocumentType] = Field(None, description="Classified document type")


class DocumentMetadata(BaseModel):
    """Metadata for a stored document"""
    id: str = Field(..., description="Document UUID")
    claim_id: str = Field(..., description="Associated claim ID")
    file_name: str
    file_path: str = Field(..., description="Supabase storage path")
    file_type: str
    document_type: Optional[DocumentType] = None
    file_size_bytes: int
    ocr_status: OCRStatus = OCRStatus.PENDING
    ocr_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    uploaded_at: datetime
    processed_at: Optional[datetime] = None


class OCRResult(BaseModel):
    """Result of OCR extraction from a document"""
    document_id: str
    raw_text: str = Field(..., description="Raw OCR text output")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall OCR confidence")
    is_readable: bool = Field(default=True, description="Whether document quality is acceptable")
    quality_issues: list[str] = Field(default_factory=list, description="Quality problems detected")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Structured extraction")
    field_confidence: Dict[str, float] = Field(
        default_factory=dict, 
        description="Confidence score per extracted field"
    )
    extraction_errors: list[str] = Field(default_factory=list, description="Errors during extraction")


class PrescriptionData(BaseModel):
    """Structured data from prescription"""
    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    specialization: Optional[str] = None
    clinic_name: Optional[str] = None
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    date: Optional[str] = None  # Will be parsed to date later
    diagnosis: Optional[str] = None
    medicines: list[str] = Field(default_factory=list)
    tests_ordered: list[str] = Field(default_factory=list)


class HospitalBillData(BaseModel):
    """Structured data from hospital bill"""
    hospital_name: Optional[str] = None
    hospital_address: Optional[str] = None
    gstin: Optional[str] = None
    bill_number: Optional[str] = None
    bill_date: Optional[str] = None
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    referring_doctor: Optional[str] = None
    line_items: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of {description, quantity, rate, amount}"
    )
    subtotal: Optional[float] = None
    gst_amount: Optional[float] = None
    total_amount: Optional[float] = None
    payment_mode: Optional[str] = None


class LabReportData(BaseModel):
    """Structured data from lab report"""
    lab_name: Optional[str] = None
    nabl_accredited: Optional[bool] = None
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    referring_doctor: Optional[str] = None
    sample_date: Optional[str] = None
    report_date: Optional[str] = None
    sample_id: Optional[str] = None
    tests: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of {test_name, result, unit, normal_range}"
    )
    pathologist_name: Optional[str] = None
    pathologist_registration: Optional[str] = None
    remarks: Optional[str] = None


class PharmacyBillData(BaseModel):
    """Structured data from pharmacy bill"""
    pharmacy_name: Optional[str] = None
    drug_license: Optional[str] = None
    bill_number: Optional[str] = None
    bill_date: Optional[str] = None
    patient_name: Optional[str] = None
    prescribing_doctor: Optional[str] = None
    medicines: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of {medicine, batch, expiry, quantity, mrp, amount}"
    )
    subtotal: Optional[float] = None
    discount: Optional[float] = None
    net_amount: Optional[float] = None
    pharmacist_name: Optional[str] = None


class DocumentVerificationResult(BaseModel):
    """Result of document verification check"""
    verification_passed: bool
    errors: list[str] = Field(default_factory=list, description="Critical errors (block processing)")
    warnings: list[str] = Field(default_factory=list, description="Non-critical warnings")
    missing_documents: list[DocumentType] = Field(default_factory=list)
    document_classifications: Dict[str, DocumentType] = Field(
        default_factory=dict,
        description="Mapping of file_name to classified DocumentType"
    )
    patient_names_found: list[str] = Field(default_factory=list)
    patient_name_consistent: bool = True
