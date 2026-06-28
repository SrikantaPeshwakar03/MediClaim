"""
Claim Models

Pydantic models for claims, submissions, and decisions.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import date, datetime
from .enums import (
    ClaimStatus, 
    ClaimDecision, 
    ClaimCategory, 
    RejectionReason
)
from .document import DocumentUpload


class ClaimSubmission(BaseModel):
    """Data submitted when creating a new claim"""
    member_id: str = Field(..., description="Member ID from policy")
    policy_id: str = Field(..., description="Policy ID")
    claim_category: ClaimCategory
    treatment_date: date
    claimed_amount: float = Field(..., gt=0, description="Amount being claimed")
    hospital_name: Optional[str] = None
    documents: List[DocumentUpload] = Field(..., min_length=1, description="At least one document required")
    
    # Optional metadata
    notes: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('claimed_amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Claimed amount must be positive")
        if v > 1000000:  # 10 lakh max sanity check
            raise ValueError("Claimed amount exceeds maximum allowed")
        return round(v, 2)


class ClaimMetadata(BaseModel):
    """Metadata for a claim record"""
    id: str = Field(..., description="Claim UUID")
    claim_id: str = Field(..., description="Human-readable claim ID")
    member_id: str
    policy_id: str
    claim_category: ClaimCategory
    treatment_date: date
    claimed_amount: float
    hospital_name: Optional[str] = None
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None


class ClaimDecisionOutput(BaseModel):
    """Final decision output for a claim"""
    decision: ClaimDecision
    approved_amount: float = Field(0.0, ge=0)
    rejection_reasons: List[RejectionReason] = Field(default_factory=list)
    decision_message: str = Field(..., description="Human-readable decision explanation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in decision")
    
    # Breakdown
    original_amount: float
    copay_deducted: Optional[float] = None
    network_discount_applied: Optional[float] = None
    
    # Flags
    requires_manual_review: bool = False
    manual_review_reason: Optional[str] = None
    
    # Component status
    components_failed: List[str] = Field(default_factory=list, description="List of failed agent names")


class FraudSignal(BaseModel):
    """A detected fraud signal"""
    signal_type: str = Field(..., description="Type of fraud signal")
    severity: str = Field(..., description="HIGH, MEDIUM, LOW")
    description: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class FraudDetectionResult(BaseModel):
    """Result of fraud detection analysis"""
    fraud_score: float = Field(..., ge=0.0, le=1.0, description="Overall fraud risk score")
    fraud_signals: List[FraudSignal] = Field(default_factory=list)
    requires_manual_review: bool
    claim_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent claims from this member"
    )


class ClaimTrace(BaseModel):
    """Complete trace of claim processing for explainability"""
    claim_id: str
    agent_traces: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Trace from each agent in order"
    )
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time_seconds: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ClaimStatusResponse(BaseModel):
    """Response for claim status query"""
    claim_id: str
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    current_stage: Optional[str] = None


class ClaimDecisionResponse(BaseModel):
    """Complete response with decision and trace"""
    claim_id: str
    status: ClaimStatus
    decision: Optional[ClaimDecisionOutput] = None
    trace: Optional[ClaimTrace] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
