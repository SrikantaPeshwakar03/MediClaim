"""
Policy Models

Pydantic models for policy configuration and validation results.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import date
from .enums import ClaimCategory, DocumentType, PolicyCheckResult


class MemberData(BaseModel):
    """Member information from policy"""
    member_id: str
    name: str
    date_of_birth: date
    gender: str
    relationship: str
    join_date: date
    dependents: List[str] = Field(default_factory=list)
    primary_member_id: Optional[str] = None


class CoverageCategory(BaseModel):
    """Coverage configuration for a claim category"""
    sub_limit: int
    copay_percent: int
    network_discount_percent: Optional[int] = None
    requires_prescription: bool
    requires_pre_auth: bool = False
    pre_auth_threshold: Optional[int] = None
    covered: bool = True
    covered_procedures: List[str] = Field(default_factory=list)
    excluded_procedures: List[str] = Field(default_factory=list)


class WaitingPeriod(BaseModel):
    """Waiting period configuration"""
    initial_waiting_period_days: int
    pre_existing_conditions_days: int
    specific_conditions: Dict[str, int] = Field(default_factory=dict)


class DocumentRequirements(BaseModel):
    """Required documents for a claim category"""
    required: List[DocumentType]
    optional: List[DocumentType] = Field(default_factory=list)


class PolicyConfig(BaseModel):
    """Complete policy configuration"""
    policy_id: str
    policy_name: str
    insurer: str
    
    # Coverage
    sum_insured_per_employee: int
    annual_opd_limit: int
    per_claim_limit: int
    
    # Categories
    opd_categories: Dict[str, CoverageCategory]
    
    # Rules
    waiting_periods: WaitingPeriod
    exclusions: Dict[str, List[str]]
    pre_authorization: Dict[str, Any]
    network_hospitals: List[str]
    
    # Requirements
    document_requirements: Dict[ClaimCategory, DocumentRequirements]
    
    # Fraud thresholds
    fraud_thresholds: Dict[str, Any]
    
    # Members
    members: List[MemberData]
    
    class Config:
        arbitrary_types_allowed = True


class PolicyCheck(BaseModel):
    """Result of a single policy validation check"""
    check_name: str = Field(..., description="Name of the check (e.g., 'waiting_period', 'coverage_limit')")
    result: PolicyCheckResult
    message: str = Field(..., description="Human-readable explanation")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional check details")
    eligible_amount: Optional[float] = Field(None, description="Amount eligible after this check")


class PolicyValidationResult(BaseModel):
    """Complete result of policy validation"""
    member_found: bool
    member_data: Optional[MemberData] = None
    policy_checks: List[PolicyCheck] = Field(default_factory=list)
    all_checks_passed: bool
    final_eligible_amount: float = Field(0.0, description="Final amount after all validations")
    applied_copay: Optional[float] = None
    applied_network_discount: Optional[float] = None
    line_item_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Per line-item validation for itemized bills"
    )
