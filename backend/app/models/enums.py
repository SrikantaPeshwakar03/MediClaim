"""
Enums for MediClaim

Centralized enum definitions for consistent type safety across the application.
"""

from enum import Enum


class ClaimStatus(str, Enum):
    """Status of claim processing"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ClaimDecision(str, Enum):
    """Final decision on a claim"""
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ClaimCategory(str, Enum):
    """Types of medical claims"""
    CONSULTATION = "CONSULTATION"
    DIAGNOSTIC = "DIAGNOSTIC"
    PHARMACY = "PHARMACY"
    DENTAL = "DENTAL"
    VISION = "VISION"
    ALTERNATIVE_MEDICINE = "ALTERNATIVE_MEDICINE"


class DocumentType(str, Enum):
    """Types of medical documents"""
    PRESCRIPTION = "PRESCRIPTION"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    PHARMACY_BILL = "PHARMACY_BILL"
    LAB_REPORT = "LAB_REPORT"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    DENTAL_REPORT = "DENTAL_REPORT"
    UNKNOWN = "UNKNOWN"


class OCRStatus(str, Enum):
    """Status of OCR processing"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RejectionReason(str, Enum):
    """Standardized rejection reasons"""
    WAITING_PERIOD = "WAITING_PERIOD"
    EXCLUDED_CONDITION = "EXCLUDED_CONDITION"
    PRE_AUTH_MISSING = "PRE_AUTH_MISSING"
    PER_CLAIM_EXCEEDED = "PER_CLAIM_EXCEEDED"
    ANNUAL_LIMIT_EXCEEDED = "ANNUAL_LIMIT_EXCEEDED"
    CATEGORY_LIMIT_EXCEEDED = "CATEGORY_LIMIT_EXCEEDED"
    INVALID_DOCUMENTS = "INVALID_DOCUMENTS"
    MEMBER_NOT_FOUND = "MEMBER_NOT_FOUND"
    POLICY_INACTIVE = "POLICY_INACTIVE"
    FRAUD_DETECTED = "FRAUD_DETECTED"
    INCOMPLETE_INFORMATION = "INCOMPLETE_INFORMATION"


class PolicyCheckResult(str, Enum):
    """Result of a policy validation check"""
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


class AgentName(str, Enum):
    """Names of agents in the pipeline"""
    DOCUMENT_VERIFIER = "DocumentVerifier"
    OCR_EXTRACTOR = "OCRExtractor"
    POLICY_VALIDATOR = "PolicyValidator"
    FRAUD_DETECTOR = "FraudDetector"
    DECISION_MAKER = "DecisionMaker"
