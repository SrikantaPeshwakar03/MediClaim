"""
API Schemas

Request and response models for FastAPI endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from ..models.enums import ClaimCategory, ClaimStatus, ClaimDecision
from ..models.claim import ClaimDecisionOutput, ClaimTrace


# === Request Schemas ===

class ClaimSubmitRequest(BaseModel):
    """Request body for claim submission"""
    member_id: str = Field(..., description="Member ID from policy", example="EMP001")
    policy_id: str = Field(..., description="Policy ID", example="PLUM_GHI_2024")
    claim_category: ClaimCategory = Field(..., example="CONSULTATION")
    treatment_date: date = Field(..., description="Date of treatment", example="2024-11-15")
    claimed_amount: float = Field(..., gt=0, description="Amount being claimed", example=1500.0)
    hospital_name: Optional[str] = Field(None, example="Apollo Hospitals")
    notes: Optional[str] = Field(None, max_length=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "member_id": "EMP001",
                "policy_id": "PLUM_GHI_2024",
                "claim_category": "CONSULTATION",
                "treatment_date": "2024-11-15",
                "claimed_amount": 1500.0,
                "hospital_name": "City Clinic",
                "notes": "Routine checkup for fever"
            }
        }


# === Response Schemas ===

class ClaimSubmitResponse(BaseModel):
    """Response after successful claim submission"""
    claim_id: str = Field(..., description="Unique claim identifier")
    status: ClaimStatus = Field(..., description="Current claim status")
    message: str = Field(..., description="Success message")
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "claim_id": "CLM_2024_001234",
                "status": "PENDING",
                "message": "Claim submitted successfully. Processing will begin shortly.",
                "created_at": "2024-11-15T10:30:00Z"
            }
        }


class ClaimStatusResponse(BaseModel):
    """Response for claim status query"""
    claim_id: str
    status: ClaimStatus
    current_stage: Optional[str] = Field(
        None, 
        description="Current processing stage",
        example="Policy Validation"
    )
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "claim_id": "CLM_2024_001234",
                "status": "PROCESSING",
                "current_stage": "Policy Validation",
                "created_at": "2024-11-15T10:30:00Z",
                "updated_at": "2024-11-15T10:31:00Z"
            }
        }


class ClaimDecisionResponse(BaseModel):
    """Complete response with decision and trace"""
    claim_id: str
    status: ClaimStatus
    decision: Optional[ClaimDecisionOutput] = None
    trace: Optional[ClaimTrace] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "claim_id": "CLM_2024_001234",
                "status": "COMPLETED",
                "decision": {
                    "decision": "APPROVED",
                    "approved_amount": 1350.0,
                    "rejection_reasons": [],
                    "decision_message": "Claim approved. 10% co-pay applied (₹150 deducted).",
                    "confidence_score": 0.92,
                    "original_amount": 1500.0,
                    "copay_deducted": 150.0,
                    "network_discount_applied": None,
                    "requires_manual_review": False,
                    "components_failed": []
                },
                "created_at": "2024-11-15T10:30:00Z",
                "processed_at": "2024-11-15T10:32:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="User-friendly error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "DocumentVerificationError",
                "message": "Missing required document: HOSPITAL_BILL",
                "details": {
                    "required_documents": ["PRESCRIPTION", "HOSPITAL_BILL"],
                    "uploaded_documents": ["PRESCRIPTION"]
                }
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., example="healthy")
    version: str = Field(..., example="1.0.0")
    timestamp: datetime
    services: dict = Field(
        default_factory=dict,
        description="Status of external services",
        example={
            "database": "connected",
            "storage": "connected",
            "llm": "available"
        }
    )


# === Document Upload Response ===

class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    document_id: str
    file_name: str
    file_path: str
    file_size_bytes: int
    uploaded_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_abc123",
                "file_name": "prescription.jpg",
                "file_path": "claims/CLM_2024_001234/prescription.jpg",
                "file_size_bytes": 245632,
                "uploaded_at": "2024-11-15T10:30:00Z"
            }
        }
