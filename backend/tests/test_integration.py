"""
Integration Tests

Tests for the complete claims processing pipeline.
These tests verify end-to-end functionality with the orchestrator.
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from app.models import ClaimCategory, ClaimDecision, create_initial_state
from app.agents.orchestrator import ClaimsOrchestrator


@pytest.fixture
def mock_all_services():
    """Mock all external services for integration testing"""
    with patch('app.agents.document_verifier.get_policy_engine') as mock_policy, \
         patch('app.agents.document_verifier.get_ocr_service') as mock_ocr, \
         patch('app.agents.document_verifier.get_llm_service') as mock_llm_dv, \
         patch('app.agents.ocr_extractor.get_ocr_service') as mock_ocr_oe, \
         patch('app.agents.ocr_extractor.get_llm_service') as mock_llm_oe, \
         patch('app.agents.policy_validator.get_policy_engine') as mock_policy_pv:
        
        # Mock policy engine
        from app.models import DocumentRequirements, DocumentType, MemberData
        from app.models import PolicyCheck, PolicyCheckResult, PolicyValidationResult
        
        policy_engine = MagicMock()
        mock_policy.return_value = policy_engine
        mock_policy_pv.return_value = policy_engine
        
        # Mock document requirements
        policy_engine.get_document_requirements.return_value = DocumentRequirements(
            required=[DocumentType.PRESCRIPTION, DocumentType.HOSPITAL_BILL],
            optional=[]
        )
        
        # Mock member data
        policy_engine.get_member.return_value = MemberData(
            member_id="EMP001",
            name="Rajesh Kumar",
            date_of_birth=date(1985, 3, 15),
            gender="M",
            relationship="SELF",
            join_date=date(2024, 4, 1),
            dependents=[]
        )
        
        # Mock policy checks (all passing)
        policy_engine.check_waiting_period.return_value = PolicyCheck(
            check_name="waiting_period",
            result=PolicyCheckResult.PASSED,
            message="No waiting period",
            eligible_amount=1500.0
        )
        
        policy_engine.check_per_claim_limit.return_value = PolicyCheck(
            check_name="per_claim_limit",
            result=PolicyCheckResult.PASSED,
            message="Within limit",
            eligible_amount=1500.0
        )
        
        policy_engine.check_category_limit.return_value = PolicyCheck(
            check_name="category_limit",
            result=PolicyCheckResult.PASSED,
            message="Within limit",
            eligible_amount=1500.0
        )
        
        policy_engine.check_annual_limit.return_value = PolicyCheck(
            check_name="annual_limit",
            result=PolicyCheckResult.PASSED,
            message="Within limit",
            eligible_amount=1500.0
        )
        
        policy_engine.check_exclusions.return_value = PolicyCheck(
            check_name="exclusions",
            result=PolicyCheckResult.PASSED,
            message="No exclusions",
            eligible_amount=1500.0
        )
        
        policy_engine.check_pre_authorization.return_value = PolicyCheck(
            check_name="pre_authorization",
            result=PolicyCheckResult.PASSED,
            message="Not required",
            eligible_amount=1500.0
        )
        
        policy_engine.is_network_hospital.return_value = False
        policy_engine.apply_copay_and_discount.return_value = {
            "original_amount": 1500.0,
            "network_discount": 0.0,
            "amount_after_discount": 1500.0,
            "copay_amount": 150.0,  # 10% copay
            "final_amount": 1350.0
        }
        
        # Mock OCR service
        ocr_service = MagicMock()
        mock_ocr.return_value = ocr_service
        mock_ocr_oe.return_value = ocr_service
        
        ocr_service.extract_text.return_value = (
            "Dr. Arun Sharma\nPatient: Rajesh Kumar\nDiagnosis: Viral Fever",
            0.92,
            []
        )
        
        ocr_service.check_document_quality.return_value = (True, [])
        
        from app.models import OCRResult
        ocr_service.extract_from_document.return_value = OCRResult(
            document_id="doc1",
            raw_text="Dr. Arun Sharma\nPatient: Rajesh Kumar",
            confidence=0.92,
            is_readable=True,
            quality_issues=[],
            extracted_data={
                "doctor_name": "Dr. Arun Sharma",
                "patient_name": "Rajesh Kumar"
            },
            field_confidence={},
            extraction_errors=[]
        )
        
        # Mock LLM service
        llm_service = MagicMock()
        mock_llm_dv.return_value = llm_service
        mock_llm_oe.return_value = llm_service
        
        llm_service.classify_document.side_effect = ["PRESCRIPTION", "HOSPITAL_BILL"]
        llm_service.check_patient_name_consistency.return_value = {
            "same_person": True,
            "confidence": 0.95,
            "explanation": "Same person"
        }
        
        llm_service.call_llm.return_value = """{
            "doctor_name": "Dr. Arun Sharma",
            "patient_name": "Rajesh Kumar",
            "diagnosis": "Viral Fever",
            "medicines": ["Paracetamol 650mg"]
        }"""
        
        llm_service._parse_json_response.return_value = {
            "doctor_name": "Dr. Arun Sharma",
            "patient_name": "Rajesh Kumar",
            "diagnosis": "Viral Fever",
            "medicines": ["Paracetamol 650mg"]
        }
        
        yield {
            'policy_engine': policy_engine,
            'ocr_service': ocr_service,
            'llm_service': llm_service
        }


class TestCompleteWorkflow:
    """Test complete claim processing workflow"""
    
    def test_successful_claim_processing(self, mock_all_services):
        """Test successful end-to-end claim processing (TC004)"""
        # Create orchestrator
        orchestrator = ClaimsOrchestrator()
        
        # Create initial state
        state = create_initial_state(
            claim_id="CLM_TEST_001",
            member_id="EMP001",
            policy_id="PLUM_GHI_2024",
            claim_category=ClaimCategory.CONSULTATION,
            treatment_date=date(2024, 11, 15),
            claimed_amount=1500.0,
            document_file_paths=["doc1.jpg", "doc2.jpg"],
            document_metadata=[
                {"file_name": "doc1.jpg"},
                {"file_name": "doc2.jpg"}
            ]
        )
        
        # Process claim
        final_state = orchestrator.process_claim(state)
        
        # Verify all agents executed
        assert "DocumentVerifier" in final_state["components_executed"]
        assert "OCRExtractor" in final_state["components_executed"]
        assert "PolicyValidator" in final_state["components_executed"]
        assert "FraudDetector" in final_state["components_executed"]
        assert "DecisionMaker" in final_state["components_executed"]
        
        # Verify decision was made
        assert final_state["final_decision"] is not None
        assert final_state["decision"] is not None
        
        # Verify trace
        assert len(final_state["trace"]) >= 5  # At least one per agent
        
        print(f"\nDecision: {final_state['decision']}")
        print(f"Approved Amount: ₹{final_state['approved_amount']:.2f}")
        print(f"Confidence: {final_state['confidence_score']:.2f}")
        print(f"Components Executed: {final_state['components_executed']}")
    
    def test_verification_failure_stops_pipeline(self, mock_all_services):
        """Test that verification failure stops the pipeline (TC001)"""
        # Mock to return only PRESCRIPTION (missing HOSPITAL_BILL)
        mock_all_services['llm_service'].classify_document.return_value = "PRESCRIPTION"
        
        orchestrator = ClaimsOrchestrator()
        
        state = create_initial_state(
            claim_id="CLM_TEST_002",
            member_id="EMP001",
            policy_id="PLUM_GHI_2024",
            claim_category=ClaimCategory.CONSULTATION,
            treatment_date=date(2024, 11, 15),
            claimed_amount=1500.0,
            document_file_paths=["doc1.jpg"],
            document_metadata=[{"file_name": "doc1.jpg"}]
        )
        
        final_state = orchestrator.process_claim(state)
        
        # Verify pipeline stopped after verification
        assert "DocumentVerifier" in final_state["components_executed"]
        assert "OCRExtractor" not in final_state["components_executed"]
        
        # Verify no decision made
        assert final_state.get("final_decision") is None
        
        print(f"\nPipeline stopped: {final_state['stop_processing']}")
        print(f"Verification errors: {final_state['verification_result'].errors}")
    
    def test_graceful_degradation(self, mock_all_services):
        """Test graceful degradation when OCR fails (TC011)"""
        # Mock OCR to fail
        mock_all_services['ocr_service'].extract_from_document.side_effect = Exception("OCR failed")
        
        orchestrator = ClaimsOrchestrator()
        
        state = create_initial_state(
            claim_id="CLM_TEST_003",
            member_id="EMP001",
            policy_id="PLUM_GHI_2024",
            claim_category=ClaimCategory.CONSULTATION,
            treatment_date=date(2024, 11, 15),
            claimed_amount=1500.0,
            document_file_paths=["doc1.jpg", "doc2.jpg"],
            document_metadata=[
                {"file_name": "doc1.jpg"},
                {"file_name": "doc2.jpg"}
            ]
        )
        
        final_state = orchestrator.process_claim(state)
        
        # Verify pipeline continued despite OCR failure
        assert "OCRExtractor" in final_state["components_failed"]
        assert "DecisionMaker" in final_state["components_executed"]
        
        # Verify decision was still made (with reduced confidence)
        assert final_state["final_decision"] is not None
        
        # Verify confidence was reduced
        assert final_state["confidence_score"] < 1.0
        
        print(f"\nComponents failed: {final_state['components_failed']}")
        print(f"Decision: {final_state['decision']}")
        print(f"Confidence (reduced): {final_state['confidence_score']:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
