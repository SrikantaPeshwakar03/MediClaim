"""
Test Policy Engine Service

Unit tests for policy engine functionality.
"""

import pytest
from datetime import date, timedelta
from app.services.policy_engine import PolicyEngine, get_policy_engine
from app.models import ClaimCategory, PolicyCheckResult
from app.exceptions import NotFoundError


@pytest.fixture
def policy_engine():
    """Fixture to get policy engine instance"""
    return get_policy_engine()


class TestMemberManagement:
    """Test member lookup functionality"""
    
    def test_get_existing_member(self, policy_engine):
        """Test getting an existing member"""
        member = policy_engine.get_member("EMP001")
        assert member.member_id == "EMP001"
        assert member.name == "Rajesh Kumar"
    
    def test_get_nonexistent_member(self, policy_engine):
        """Test that getting non-existent member raises error"""
        with pytest.raises(NotFoundError):
            policy_engine.get_member("EMP999")
    
    def test_member_exists(self, policy_engine):
        """Test member existence check"""
        assert policy_engine.member_exists("EMP001") is True
        assert policy_engine.member_exists("EMP999") is False


class TestDocumentRequirements:
    """Test document requirements lookup"""
    
    def test_consultation_requirements(self, policy_engine):
        """Test document requirements for consultation"""
        req = policy_engine.get_document_requirements(ClaimCategory.CONSULTATION)
        assert "PRESCRIPTION" in [d.value for d in req.required]
        assert "HOSPITAL_BILL" in [d.value for d in req.required]
    
    def test_pharmacy_requirements(self, policy_engine):
        """Test document requirements for pharmacy"""
        req = policy_engine.get_document_requirements(ClaimCategory.PHARMACY)
        assert "PRESCRIPTION" in [d.value for d in req.required]
        assert "PHARMACY_BILL" in [d.value for d in req.required]


class TestWaitingPeriod:
    """Test waiting period checks"""
    
    def test_initial_waiting_period_passed(self, policy_engine):
        """Test member who has passed initial waiting period"""
        member = policy_engine.get_member("EMP001")
        treatment_date = date.today()
        
        check = policy_engine.check_waiting_period(member, treatment_date)
        assert check.result == PolicyCheckResult.PASSED
    
    def test_initial_waiting_period_failed(self, policy_engine):
        """Test member within initial waiting period"""
        # EMP005 joined on 2024-09-01, needs 30 days
        member = policy_engine.get_member("EMP005")
        treatment_date = date(2024, 9, 15)  # Only 14 days after joining
        
        check = policy_engine.check_waiting_period(member, treatment_date)
        assert check.result == PolicyCheckResult.FAILED
        assert "initial waiting period" in check.message.lower()
    
    def test_condition_specific_waiting_period(self, policy_engine):
        """Test condition-specific waiting period (diabetes)"""
        member = policy_engine.get_member("EMP005")
        # Member joined 2024-09-01, diabetes requires 90 days
        treatment_date = date(2024, 10, 15)  # 44 days later
        
        check = policy_engine.check_waiting_period(
            member, 
            treatment_date,
            diagnosis="Type 2 Diabetes Mellitus"
        )
        assert check.result == PolicyCheckResult.FAILED
        assert "diabetes" in check.message.lower()


class TestCoverageLimits:
    """Test coverage limit checks"""
    
    def test_per_claim_limit_passed(self, policy_engine):
        """Test claim within per-claim limit"""
        check = policy_engine.check_per_claim_limit(3000, ClaimCategory.CONSULTATION)
        assert check.result == PolicyCheckResult.PASSED
        assert check.eligible_amount == 3000
    
    def test_per_claim_limit_exceeded(self, policy_engine):
        """Test claim exceeding per-claim limit"""
        check = policy_engine.check_per_claim_limit(7500, ClaimCategory.CONSULTATION)
        assert check.result == PolicyCheckResult.FAILED
        assert check.eligible_amount == 0.0
    
    def test_category_limit_passed(self, policy_engine):
        """Test claim within category sub-limit"""
        check = policy_engine.check_category_limit(
            claimed_amount=1500,
            category=ClaimCategory.CONSULTATION,
            ytd_category_claims=500
        )
        assert check.result == PolicyCheckResult.PASSED
    
    def test_category_limit_exceeded(self, policy_engine):
        """Test claim exceeding category sub-limit"""
        # Consultation sub-limit is 2000
        check = policy_engine.check_category_limit(
            claimed_amount=1500,
            category=ClaimCategory.CONSULTATION,
            ytd_category_claims=1800  # Already at 1800, adding 1500 exceeds 2000
        )
        assert check.result in [PolicyCheckResult.FAILED, PolicyCheckResult.WARNING]
    
    def test_annual_limit_passed(self, policy_engine):
        """Test claim within annual limit"""
        check = policy_engine.check_annual_limit(
            claimed_amount=5000,
            ytd_total_claims=10000
        )
        assert check.result == PolicyCheckResult.PASSED
    
    def test_annual_limit_exceeded(self, policy_engine):
        """Test claim exceeding annual limit"""
        # Annual OPD limit is 50000
        check = policy_engine.check_annual_limit(
            claimed_amount=5000,
            ytd_total_claims=48000  # Already at 48000, adding 5000 exceeds 50000
        )
        assert check.result in [PolicyCheckResult.FAILED, PolicyCheckResult.WARNING]


class TestExclusions:
    """Test exclusion checks"""
    
    def test_no_exclusions(self, policy_engine):
        """Test claim with no exclusions"""
        check = policy_engine.check_exclusions(
            diagnosis="Viral Fever",
            treatment="Consultation"
        )
        assert check.result == PolicyCheckResult.PASSED
    
    def test_excluded_condition(self, policy_engine):
        """Test claim with excluded condition"""
        check = policy_engine.check_exclusions(
            diagnosis="Cosmetic dental procedure",
            category=ClaimCategory.DENTAL
        )
        # Should detect 'cosmetic' in exclusions
        assert check.result == PolicyCheckResult.FAILED
    
    def test_excluded_dental_procedure(self, policy_engine):
        """Test dental claim with excluded procedure"""
        check = policy_engine.check_exclusions(
            procedures=["Teeth Whitening", "Scaling"],
            category=ClaimCategory.DENTAL
        )
        assert check.result == PolicyCheckResult.FAILED
        assert "excluded" in check.message.lower()


class TestPreAuthorization:
    """Test pre-authorization checks"""
    
    def test_no_preauth_required(self, policy_engine):
        """Test claim that doesn't require pre-auth"""
        check = policy_engine.check_pre_authorization(
            category=ClaimCategory.CONSULTATION,
            amount=1500
        )
        assert check.result == PolicyCheckResult.PASSED
    
    def test_preauth_required_high_amount(self, policy_engine):
        """Test diagnostic claim with high amount requiring pre-auth"""
        check = policy_engine.check_pre_authorization(
            category=ClaimCategory.DIAGNOSTIC,
            amount=15000  # Exceeds 10000 threshold
        )
        assert check.result == PolicyCheckResult.FAILED
    
    def test_preauth_required_specific_test(self, policy_engine):
        """Test MRI requiring pre-auth"""
        check = policy_engine.check_pre_authorization(
            category=ClaimCategory.DIAGNOSTIC,
            amount=15000,
            tests_or_procedures=["MRI Lumbar Spine"]
        )
        assert check.result == PolicyCheckResult.FAILED
        assert "mri" in check.message.lower() or "pre-authorization" in check.message.lower()


class TestFinancialCalculations:
    """Test co-pay and network discount calculations"""
    
    def test_copay_only(self, policy_engine):
        """Test co-pay calculation without network discount"""
        result = policy_engine.apply_copay_and_discount(
            amount=1000,
            category=ClaimCategory.CONSULTATION,
            is_network_hospital=False
        )
        # Consultation has 10% co-pay
        assert result["original_amount"] == 1000
        assert result["network_discount"] == 0.0
        assert result["copay_amount"] == 100.0
        assert result["final_amount"] == 900.0
    
    def test_network_discount_then_copay(self, policy_engine):
        """Test network discount applied before co-pay"""
        result = policy_engine.apply_copay_and_discount(
            amount=4500,
            category=ClaimCategory.CONSULTATION,
            is_network_hospital=True
        )
        # Network discount: 20% = 900
        # Amount after discount: 3600
        # Co-pay: 10% of 3600 = 360
        # Final: 3240
        assert result["original_amount"] == 4500
        assert result["network_discount"] == 900.0
        assert result["amount_after_discount"] == 3600.0
        assert result["copay_amount"] == 360.0
        assert result["final_amount"] == 3240.0
    
    def test_is_network_hospital(self, policy_engine):
        """Test network hospital identification"""
        assert policy_engine.is_network_hospital("Apollo Hospitals") is True
        assert policy_engine.is_network_hospital("Max Healthcare") is True
        assert policy_engine.is_network_hospital("Random Clinic") is False
        assert policy_engine.is_network_hospital(None) is False


class TestCoverageCategory:
    """Test coverage category lookups"""
    
    def test_get_covered_category(self, policy_engine):
        """Test getting a covered category"""
        coverage = policy_engine.get_coverage_category(ClaimCategory.CONSULTATION)
        assert coverage is not None
        assert coverage.covered is True
        assert coverage.sub_limit == 2000
    
    def test_is_category_covered(self, policy_engine):
        """Test category coverage check"""
        assert policy_engine.is_category_covered(ClaimCategory.CONSULTATION) is True
        assert policy_engine.is_category_covered(ClaimCategory.DENTAL) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
