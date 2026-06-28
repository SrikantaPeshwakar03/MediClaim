"""
Test Models

Unit tests for Pydantic models to ensure validation works correctly.
"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError

from app.models import (
    ClaimSubmission,
    ClaimCategory,
    DocumentUpload,
    DocumentType,
    OCRResult,
    PolicyCheck,
    PolicyCheckResult,
    ClaimDecisionOutput,
    ClaimDecision,
    create_initial_state
)


class TestClaimSubmission:
    """Test ClaimSubmission model"""
    
    def test_valid_claim_submission(self):
        """Test creating a valid claim submission"""
        claim = ClaimSubmission(
            member_id="EMP001",
            policy_id="PLUM_GHI_2024",
            claim_category=ClaimCategory.CONSULTATION,
            treatment_date=date(2024, 11, 15),
            claimed_amount=1500.0,
            documents=[
                DocumentUpload(
                    file_name="prescription.jpg",
                    file_type="image/jpeg",
                    file_size_bytes=123456
                )
            ]
        )
        
        assert claim.member_id == "EMP001"
        assert claim.claimed_amount == 1500.0
        assert len(claim.documents) == 1
    
    def test_invalid_amount(self):
        """Test that negative amounts are rejected"""
        with pytest.raises(ValidationError):
            ClaimSubmission(
                member_id="EMP001",
                policy_id="PLUM_GHI_2024",
                claim_category=ClaimCategory.CONSULTATION,
                treatment_date=date(2024, 11, 15),
                claimed_amount=-100.0,
                documents=[
                    DocumentUpload(
                        file_name="prescription.jpg",
                        file_type="image/jpeg",
                        file_size_bytes=123456
                    )
                ]
            )
    
    def test_missing_documents(self):
        """Test that at least one document is required"""
        with pytest.raises(ValidationError):
            ClaimSubmission(
                member_id="EMP001",
                policy_id="PLUM_GHI_2024",
                claim_category=ClaimCategory.CONSULTATION,
                treatment_date=date(2024, 11, 15),
                claimed_amount=1500.0,
                documents=[]
            )


class TestOCRResult:
    """Test OCRResult model"""
    
    def test_valid_ocr_result(self):
        """Test creating a valid OCR result"""
        ocr = OCRResult(
            document_id="doc_123",
            raw_text="Dr. Arun Sharma\nPrescription...",
            confidence=0.92,
            is_readable=True,
            extracted_data={
                "doctor_name": "Dr. Arun Sharma",
                "patient_name": "Rajesh Kumar"
            },
            field_confidence={
                "doctor_name": 0.95,
                "patient_name": 0.88
            }
        )
        
        assert ocr.confidence == 0.92
        assert ocr.is_readable is True
        assert "doctor_name" in ocr.extracted_data
    
    def test_invalid_confidence(self):
        """Test that confidence must be between 0 and 1"""
        with pytest.raises(ValidationError):
            OCRResult(
                document_id="doc_123",
                raw_text="Sample text",
                confidence=1.5,  # Invalid
                extracted_data={}
            )


class TestPolicyCheck:
    """Test PolicyCheck model"""
    
    def test_policy_check_passed(self):
        """Test a passing policy check"""
        check = PolicyCheck(
            check_name="waiting_period",
            result=PolicyCheckResult.PASSED,
            message="No waiting period applicable",
            details={"days_since_joining": 180},
            eligible_amount=1500.0
        )
        
        assert check.result == PolicyCheckResult.PASSED
        assert check.eligible_amount == 1500.0
    
    def test_policy_check_failed(self):
        """Test a failing policy check"""
        check = PolicyCheck(
            check_name="coverage_limit",
            result=PolicyCheckResult.FAILED,
            message="Per-claim limit exceeded",
            details={"limit": 5000, "claimed": 7500},
            eligible_amount=0.0
        )
        
        assert check.result == PolicyCheckResult.FAILED
        assert check.eligible_amount == 0.0


class TestClaimDecisionOutput:
    """Test ClaimDecisionOutput model"""
    
    def test_approved_decision(self):
        """Test creating an approved decision"""
        decision = ClaimDecisionOutput(
            decision=ClaimDecision.APPROVED,
            approved_amount=1350.0,
            rejection_reasons=[],
            decision_message="Claim approved with 10% co-pay",
            confidence_score=0.92,
            original_amount=1500.0,
            copay_deducted=150.0
        )
        
        assert decision.decision == ClaimDecision.APPROVED
        assert decision.approved_amount == 1350.0
        assert len(decision.rejection_reasons) == 0
    
    def test_rejected_decision(self):
        """Test creating a rejected decision"""
        from app.models.enums import RejectionReason
        
        decision = ClaimDecisionOutput(
            decision=ClaimDecision.REJECTED,
            approved_amount=0.0,
            rejection_reasons=[RejectionReason.WAITING_PERIOD],
            decision_message="Claim rejected due to waiting period",
            confidence_score=0.95,
            original_amount=3000.0
        )
        
        assert decision.decision == ClaimDecision.REJECTED
        assert decision.approved_amount == 0.0
        assert len(decision.rejection_reasons) == 1


class TestClaimState:
    """Test ClaimState creation"""
    
    def test_create_initial_state(self):
        """Test creating initial state for a claim"""
        state = create_initial_state(
            claim_id="CLM_001",
            member_id="EMP001",
            policy_id="PLUM_GHI_2024",
            claim_category=ClaimCategory.CONSULTATION,
            treatment_date=date(2024, 11, 15),
            claimed_amount=1500.0,
            document_file_paths=["path/to/doc1.jpg"],
            document_metadata=[{"file_name": "doc1.jpg"}]
        )
        
        assert state["claim_id"] == "CLM_001"
        assert state["member_id"] == "EMP001"
        assert state["stop_processing"] is False
        assert len(state["trace"]) == 0
        assert len(state["errors"]) == 0
        assert state["processing_start_time"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
