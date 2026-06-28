"""
Policy Engine Service

Loads and queries policy_terms.json for validation rules.
This service provides all policy-related business logic in a centralized location.
"""

import json
from typing import Optional, Dict, List, Any
from datetime import date, datetime, timedelta
from pathlib import Path

from ..config import get_policy_file_path, settings
from ..models import (
    PolicyConfig,
    MemberData,
    CoverageCategory,
    WaitingPeriod,
    DocumentRequirements,
    ClaimCategory,
    DocumentType,
    PolicyCheck,
    PolicyCheckResult
)
from ..exceptions import PolicyValidationError, NotFoundError, ConfigurationError
from ..loggers import logger


class PolicyEngine:
    """
    Centralized policy engine for loading and querying policy rules.
    
    This class is responsible for:
    - Loading policy_terms.json
    - Member lookups
    - Validation rule queries (waiting periods, limits, exclusions, etc.)
    - Financial calculations (co-pay, network discounts)
    """
    
    def __init__(self):
        self._policy_config: Optional[PolicyConfig] = None
        self._members_cache: Dict[str, MemberData] = {}
        self._load_policy()
    
    def _load_policy(self):
        """Load policy configuration from JSON file"""
        try:
            policy_path = get_policy_file_path()
            logger.info(f"Loading policy from: {policy_path}")
            
            with open(policy_path, 'r') as f:
                policy_data = json.load(f)
            
            # Flatten coverage fields to root level
            if 'coverage' in policy_data:
                coverage = policy_data.pop('coverage')
                policy_data['sum_insured_per_employee'] = coverage.get('sum_insured_per_employee')
                policy_data['annual_opd_limit'] = coverage.get('annual_opd_limit')
                policy_data['per_claim_limit'] = coverage.get('per_claim_limit')
            
            # Fix dependent members - inherit join_date from primary member
            if 'members' in policy_data:
                # First pass: build map of primary member join dates
                primary_join_dates = {}
                for member in policy_data['members']:
                    if 'join_date' in member and member.get('relationship') == 'SELF':
                        primary_join_dates[member['member_id']] = member['join_date']
                
                # Second pass: fix dependents
                for member in policy_data['members']:
                    if 'join_date' not in member and 'primary_member_id' in member:
                        primary_id = member['primary_member_id']
                        if primary_id in primary_join_dates:
                            member['join_date'] = primary_join_dates[primary_id]
                            logger.debug(f"Inherited join_date for {member['member_id']} from {primary_id}")
            
            # Parse into Pydantic model
            self._policy_config = PolicyConfig(**policy_data)
            
            # Build member cache for fast lookups
            self._members_cache = {
                member.member_id: member 
                for member in self._policy_config.members
            }
            
            logger.info(
                f"Policy loaded successfully: {self._policy_config.policy_id}, "
                f"{len(self._members_cache)} members"
            )
            
        except FileNotFoundError as e:
            logger.error(f"Policy file not found: {e}")
            raise ConfigurationError(f"Policy file not found: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in policy file: {e}")
            raise ConfigurationError(f"Invalid policy JSON: {e}")
        except Exception as e:
            logger.error(f"Error loading policy: {e}")
            raise ConfigurationError(f"Failed to load policy: {e}")
    
    @property
    def policy(self) -> PolicyConfig:
        """Get policy configuration"""
        if self._policy_config is None:
            raise ConfigurationError("Policy not loaded")
        return self._policy_config
    
    # === Member Management ===
    
    def get_member(self, member_id: str) -> MemberData:
        """
        Get member data by member ID.
        
        Args:
            member_id: Member ID to look up
            
        Returns:
            MemberData object
            
        Raises:
            NotFoundError: If member not found
        """
        member = self._members_cache.get(member_id)
        if member is None:
            raise NotFoundError("Member", member_id)
        return member
    
    def member_exists(self, member_id: str) -> bool:
        """Check if member exists in policy"""
        return member_id in self._members_cache
    
    # === Document Requirements ===
    
    def get_document_requirements(self, category: ClaimCategory) -> DocumentRequirements:
        """
        Get required documents for a claim category.
        
        Args:
            category: Claim category
            
        Returns:
            DocumentRequirements with required and optional document types
        """
        req_dict = self.policy.document_requirements.get(category)
        if req_dict is None:
            logger.warning(f"No document requirements found for category: {category}")
            return DocumentRequirements(required=[], optional=[])
        
        return req_dict
    
    # === Coverage Rules ===
    
    def get_coverage_category(self, category: ClaimCategory) -> Optional[CoverageCategory]:
        """Get coverage configuration for a category"""
        category_key = category.value.lower()
        return self.policy.opd_categories.get(category_key)
    
    def is_category_covered(self, category: ClaimCategory) -> bool:
        """Check if a claim category is covered"""
        cov = self.get_coverage_category(category)
        return cov is not None and cov.covered
    
    # === Waiting Period Checks ===
    
    def check_waiting_period(
        self, 
        member: MemberData, 
        treatment_date: date,
        diagnosis: Optional[str] = None
    ) -> PolicyCheck:
        """
        Check if treatment is within waiting period.
        
        Args:
            member: Member data
            treatment_date: Date of treatment
            diagnosis: Diagnosis (if available) for condition-specific checks
            
        Returns:
            PolicyCheck with result
        """
        days_since_joining = (treatment_date - member.join_date).days
        
        # Check initial waiting period
        initial_period = self.policy.waiting_periods.initial_waiting_period_days
        if days_since_joining < initial_period:
            eligible_date = member.join_date + timedelta(days=initial_period)
            return PolicyCheck(
                check_name="initial_waiting_period",
                result=PolicyCheckResult.FAILED,
                message=f"Initial waiting period not completed. Member joined on {member.join_date}. "
                        f"Eligible from {eligible_date}.",
                details={
                    "days_since_joining": days_since_joining,
                    "required_days": initial_period,
                    "eligible_date": eligible_date.isoformat()
                }
            )
        
        # Check condition-specific waiting periods
        if diagnosis:
            diagnosis_lower = diagnosis.lower()
            specific_conditions = self.policy.waiting_periods.specific_conditions
            
            for condition, wait_days in specific_conditions.items():
                if condition.lower() in diagnosis_lower:
                    if days_since_joining < wait_days:
                        eligible_date = member.join_date + timedelta(days=wait_days)
                        return PolicyCheck(
                            check_name="condition_waiting_period",
                            result=PolicyCheckResult.FAILED,
                            message=f"Waiting period for {condition} not completed. "
                                    f"Eligible from {eligible_date}.",
                            details={
                                "condition": condition,
                                "days_since_joining": days_since_joining,
                                "required_days": wait_days,
                                "eligible_date": eligible_date.isoformat()
                            }
                        )
        
        return PolicyCheck(
            check_name="waiting_period",
            result=PolicyCheckResult.PASSED,
            message="No waiting period applicable",
            details={"days_since_joining": days_since_joining}
        )
    
    # === Coverage Limits ===
    
    def check_per_claim_limit(
        self, 
        claimed_amount: float,
        category: ClaimCategory
    ) -> PolicyCheck:
        """Check if claim amount exceeds per-claim limit"""
        per_claim_limit = self.policy.per_claim_limit
        
        if claimed_amount > per_claim_limit:
            return PolicyCheck(
                check_name="per_claim_limit",
                result=PolicyCheckResult.FAILED,
                message=f"Claimed amount ₹{claimed_amount:,.2f} exceeds per-claim limit "
                        f"of ₹{per_claim_limit:,.2f}",
                details={
                    "claimed_amount": claimed_amount,
                    "limit": per_claim_limit
                },
                eligible_amount=0.0
            )
        
        return PolicyCheck(
            check_name="per_claim_limit",
            result=PolicyCheckResult.PASSED,
            message="Within per-claim limit",
            details={
                "claimed_amount": claimed_amount,
                "limit": per_claim_limit
            },
            eligible_amount=claimed_amount
        )
    
    def check_category_limit(
        self,
        claimed_amount: float,
        category: ClaimCategory,
        ytd_category_claims: float = 0.0
    ) -> PolicyCheck:
        """Check if claim amount exceeds category sub-limit"""
        coverage = self.get_coverage_category(category)
        if coverage is None:
            return PolicyCheck(
                check_name="category_limit",
                result=PolicyCheckResult.FAILED,
                message=f"Category {category.value} is not covered",
                eligible_amount=0.0
            )
        
        category_limit = coverage.sub_limit
        total_with_claim = ytd_category_claims + claimed_amount
        
        if total_with_claim > category_limit:
            remaining = max(0, category_limit - ytd_category_claims)
            return PolicyCheck(
                check_name="category_limit",
                result=PolicyCheckResult.FAILED if remaining == 0 else PolicyCheckResult.WARNING,
                message=f"Category limit exceeded. Limit: ₹{category_limit:,.2f}, "
                        f"YTD claims: ₹{ytd_category_claims:,.2f}, Remaining: ₹{remaining:,.2f}",
                details={
                    "category": category.value,
                    "limit": category_limit,
                    "ytd_claims": ytd_category_claims,
                    "claimed_amount": claimed_amount,
                    "remaining": remaining
                },
                eligible_amount=remaining
            )
        
        return PolicyCheck(
            check_name="category_limit",
            result=PolicyCheckResult.PASSED,
            message="Within category sub-limit",
            details={
                "category": category.value,
                "limit": category_limit,
                "ytd_claims": ytd_category_claims
            },
            eligible_amount=claimed_amount
        )
    
    def check_annual_limit(
        self,
        claimed_amount: float,
        ytd_total_claims: float = 0.0
    ) -> PolicyCheck:
        """Check if claim amount exceeds annual OPD limit"""
        annual_limit = self.policy.annual_opd_limit
        total_with_claim = ytd_total_claims + claimed_amount
        
        if total_with_claim > annual_limit:
            remaining = max(0, annual_limit - ytd_total_claims)
            return PolicyCheck(
                check_name="annual_limit",
                result=PolicyCheckResult.FAILED if remaining == 0 else PolicyCheckResult.WARNING,
                message=f"Annual OPD limit exceeded. Limit: ₹{annual_limit:,.2f}, "
                        f"YTD claims: ₹{ytd_total_claims:,.2f}, Remaining: ₹{remaining:,.2f}",
                details={
                    "limit": annual_limit,
                    "ytd_claims": ytd_total_claims,
                    "claimed_amount": claimed_amount,
                    "remaining": remaining
                },
                eligible_amount=remaining
            )
        
        return PolicyCheck(
            check_name="annual_limit",
            result=PolicyCheckResult.PASSED,
            message="Within annual OPD limit",
            details={
                "limit": annual_limit,
                "ytd_claims": ytd_total_claims
            },
            eligible_amount=claimed_amount
        )
    
    # === Exclusions ===
    
    # Generic / connective words that should never, on their own, trigger an
    # exclusion match (avoids false positives like "Dental Caries" matching
    # "Cosmetic dental procedures").
    _EXCLUSION_STOPWORDS = {
        "treatment", "treatments", "procedure", "procedures", "program",
        "programs", "surgery", "surgeries", "therapy", "therapies", "care",
        "and", "or", "of", "the", "with", "for", "non", "necessary",
        "medically", "other", "related", "including", "health", "general",
    }

    @staticmethod
    def _normalize_token(word: str) -> str:
        """Lowercase and strip a simple trailing plural 's'."""
        w = word.lower()
        if len(w) > 4 and w.endswith("s"):
            w = w[:-1]
        return w

    def _exclusion_keywords(self, phrase: str) -> set:
        """Distinctive keywords from an exclusion phrase (excludes stopwords)."""
        import re
        tokens = re.findall(r"[a-zA-Z]+", phrase.lower())
        return {
            self._normalize_token(t)
            for t in tokens
            if len(t) >= 4 and t not in self._EXCLUSION_STOPWORDS
        }

    def _text_matches_exclusion(self, text: str, phrase: str) -> bool:
        """
        Decide whether `text` (a diagnosis/treatment/procedure) is covered by an
        exclusion `phrase`, using keyword overlap rather than exact substring.

        A match occurs when:
        - any distinctive keyword that is highly specific (>= 7 chars, e.g.
          "obesity", "cosmetic", "bariatric", "refractive") appears in the text, OR
        - all distinctive keywords of the phrase appear in the text (handles
          short, multi-word phrases without false positives).
        """
        if not text:
            return False

        # Fast path: exact substring either direction
        text_l = text.lower()
        phrase_l = phrase.lower()
        if phrase_l in text_l or text_l in phrase_l:
            return True

        phrase_keys = self._exclusion_keywords(phrase)
        if not phrase_keys:
            return False

        import re
        text_keys = {
            self._normalize_token(t)
            for t in re.findall(r"[a-zA-Z]+", text_l)
            if len(t) >= 4
        }

        # Strong, specific keyword present
        if any(len(k) >= 7 and k in text_keys for k in phrase_keys):
            return True

        # All distinctive keywords present (for shorter multi-word phrases)
        if len(phrase_keys) >= 2 and phrase_keys.issubset(text_keys):
            return True

        return False

    def check_exclusions(
        self,
        diagnosis: Optional[str] = None,
        treatment: Optional[str] = None,
        procedures: Optional[List[str]] = None,
        category: Optional[ClaimCategory] = None
    ) -> PolicyCheck:
        """
        Check if diagnosis/treatment/procedures are excluded.
        
        Uses keyword-based matching (not exact substring) so policy phrases like
        "Obesity and weight loss programs" match diagnoses like "Morbid Obesity".
        Returns PolicyCheck with FAILED if excluded, PASSED otherwise.
        """
        excluded_items = []
        
        # Assemble the applicable exclusion phrases
        general_exclusions = self.policy.exclusions.get("conditions", [])
        category_exclusions = []
        if category == ClaimCategory.DENTAL:
            category_exclusions = self.policy.exclusions.get("dental_exclusions", [])
        elif category == ClaimCategory.VISION:
            category_exclusions = self.policy.exclusions.get("vision_exclusions", [])

        if diagnosis:
            for exclusion in general_exclusions + category_exclusions:
                if self._text_matches_exclusion(diagnosis, exclusion):
                    excluded_items.append(f"Diagnosis: {exclusion}")
        
        if treatment:
            for exclusion in general_exclusions + category_exclusions:
                if self._text_matches_exclusion(treatment, exclusion):
                    excluded_items.append(f"Treatment: {exclusion}")
        
        # Check category-specific procedure exclusions (line-item level)
        if category and procedures:
            coverage = self.get_coverage_category(category)
            if coverage and coverage.excluded_procedures:
                for procedure in procedures:
                    for excluded in coverage.excluded_procedures:
                        if self._text_matches_exclusion(procedure, excluded):
                            excluded_items.append(f"Procedure: {excluded}")
        
        # De-duplicate while preserving order
        seen = set()
        excluded_items = [x for x in excluded_items if not (x in seen or seen.add(x))]

        if excluded_items:
            return PolicyCheck(
                check_name="exclusions",
                result=PolicyCheckResult.FAILED,
                message=f"Claim contains excluded items: {', '.join(excluded_items)}",
                details={"excluded_items": excluded_items},
                eligible_amount=0.0
            )
        
        return PolicyCheck(
            check_name="exclusions",
            result=PolicyCheckResult.PASSED,
            message="No exclusions found",
            details={}
        )
    
    # === Pre-Authorization ===
    
    def check_pre_authorization(
        self,
        category: ClaimCategory,
        amount: float,
        tests_or_procedures: Optional[List[str]] = None
    ) -> PolicyCheck:
        """Check if pre-authorization was required"""
        coverage = self.get_coverage_category(category)
        
        if coverage is None:
            return PolicyCheck(
                check_name="pre_authorization",
                result=PolicyCheckResult.SKIPPED,
                message="Category not found"
            )
        
        # Check if pre-auth is required for this category
        if not coverage.requires_pre_auth:
            # Check threshold-based pre-auth
            if coverage.pre_auth_threshold and amount >= coverage.pre_auth_threshold:
                return PolicyCheck(
                    check_name="pre_authorization",
                    result=PolicyCheckResult.FAILED,
                    message=f"Pre-authorization required for amounts >= ₹{coverage.pre_auth_threshold:,.2f}",
                    details={
                        "threshold": coverage.pre_auth_threshold,
                        "amount": amount
                    },
                    eligible_amount=0.0
                )
        
        # Check specific tests/procedures requiring pre-auth (for diagnostics)
        if category == ClaimCategory.DIAGNOSTIC and tests_or_procedures:
            preauth_required = self.policy.pre_authorization.get("required_for", [])
            for test in tests_or_procedures:
                test_upper = test.upper()
                for required in preauth_required:
                    if required.upper() in test_upper:
                        return PolicyCheck(
                            check_name="pre_authorization",
                            result=PolicyCheckResult.FAILED,
                            message=f"Pre-authorization required for {required}",
                            details={"required_test": required},
                            eligible_amount=0.0
                        )
        
        return PolicyCheck(
            check_name="pre_authorization",
            result=PolicyCheckResult.PASSED,
            message="Pre-authorization not required"
        )
    
    # === Financial Calculations ===
    
    def apply_copay_and_discount(
        self,
        amount: float,
        category: ClaimCategory,
        is_network_hospital: bool = False
    ) -> Dict[str, float]:
        """
        Apply network discount and co-pay to the amount.
        
        Order: Network discount first, then co-pay on discounted amount.
        
        Returns:
            Dict with: original_amount, network_discount, amount_after_discount,
                      copay_amount, final_amount
        """
        coverage = self.get_coverage_category(category)
        
        if coverage is None:
            return {
                "original_amount": amount,
                "network_discount": 0.0,
                "amount_after_discount": amount,
                "copay_amount": 0.0,
                "final_amount": amount
            }
        
        # Step 1: Apply network discount
        network_discount = 0.0
        if is_network_hospital and coverage.network_discount_percent:
            network_discount = amount * (coverage.network_discount_percent / 100)
        
        amount_after_discount = amount - network_discount
        
        # Step 2: Apply co-pay on discounted amount
        copay_amount = 0.0
        if coverage.copay_percent:
            copay_amount = amount_after_discount * (coverage.copay_percent / 100)
        
        final_amount = amount_after_discount - copay_amount
        
        return {
            "original_amount": amount,
            "network_discount": round(network_discount, 2),
            "amount_after_discount": round(amount_after_discount, 2),
            "copay_amount": round(copay_amount, 2),
            "final_amount": round(final_amount, 2)
        }
    
    def is_network_hospital(self, hospital_name: Optional[str]) -> bool:
        """Check if hospital is in network"""
        if not hospital_name:
            return False
        
        hospital_lower = hospital_name.lower()
        for network_hospital in self.policy.network_hospitals:
            if network_hospital.lower() in hospital_lower:
                return True
        
        return False


# Singleton instance
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create PolicyEngine singleton"""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
