"""
PolicyValidator Agent

Third agent in the claims processing pipeline.
Validates claim against all policy rules and calculates eligible amount.
"""

import time
from typing import Dict, Any, List, Optional
from datetime import date

from ..models import (
    ClaimState,
    PolicyValidationResult,
    PolicyCheck,
    PolicyCheckResult,
    MemberData
)
from ..services import get_policy_engine
from ..exceptions import PolicyValidationError, NotFoundError
from ..loggers import logger, log_claim_event


class PolicyValidatorAgent:
    """
    Agent responsible for validating claims against policy rules.
    
    Validations performed:
    1. Member exists and is active
    2. Waiting periods (initial + condition-specific)
    3. Per-claim limit
    4. Category sub-limit
    5. Annual OPD limit
    6. Exclusions
    7. Pre-authorization requirements
    8. Line-item validation for itemized bills
    9. Financial calculations (co-pay, network discount)
    """
    
    def __init__(self):
        self.policy_engine = get_policy_engine()
        self.agent_name = "PolicyValidator"
        self._supabase_service = None
        logger.info(f"[{self.agent_name}] Agent initialized")
    
    @property
    def supabase(self):
        """Lazy load Supabase service"""
        if self._supabase_service is None:
            from ..services import get_supabase_service
            try:
                self._supabase_service = get_supabase_service()
            except Exception as e:
                logger.warning(f"Supabase service not available: {e}")
                self._supabase_service = None
        return self._supabase_service
    
    def validate(self, state: ClaimState) -> ClaimState:
        """
        Validate claim against policy rules.
        
        Args:
            state: Current claim state
            
        Returns:
            Updated claim state with validation results
        """
        claim_id = state["claim_id"]
        logger.info(f"[{self.agent_name}] Starting validation for claim: {claim_id}")
        
        start_time = time.time()
        policy_checks: List[PolicyCheck] = []
        member_found = False
        member_data: Optional[MemberData] = None
        
        try:
            # Step 1: Validate member exists
            try:
                member_data = self.policy_engine.get_member(state["member_id"])
                member_found = True
                logger.info(f"[{self.agent_name}] Member found: {member_data.name}")
            except NotFoundError:
                logger.error(f"[{self.agent_name}] Member not found: {state['member_id']}")
                member_found = False
                
                # Create failed validation
                validation_result = PolicyValidationResult(
                    member_found=False,
                    member_data=None,
                    policy_checks=[PolicyCheck(
                        check_name="member_validation",
                        result=PolicyCheckResult.FAILED,
                        message=f"Member {state['member_id']} not found in policy",
                        eligible_amount=0.0
                    )],
                    all_checks_passed=False,
                    final_eligible_amount=0.0
                )
                
                state["policy_validation"] = validation_result
                state["eligible_amount"] = 0.0
                
                self._add_trace(state, start_time, validation_result, success=False)
                return state
            
            # Step 2: Get extracted data
            extracted_data = state.get("extracted_data", {})
            diagnosis = extracted_data.get("diagnosis")
            line_items = extracted_data.get("line_items", [])
            
            # Step 3: Run policy checks
            
            # 3a. Waiting period check
            waiting_check = self.policy_engine.check_waiting_period(
                member=member_data,
                treatment_date=state["treatment_date"],
                diagnosis=diagnosis
            )
            policy_checks.append(waiting_check)
            
            # 3b. Per-claim limit check
            per_claim_check = self.policy_engine.check_per_claim_limit(
                claimed_amount=state["claimed_amount"],
                category=state["claim_category"]
            )
            policy_checks.append(per_claim_check)
            
            # 3c. Category sub-limit check
            ytd_category_claims = 0.0
            if self.supabase:
                try:
                    ytd_category_claims = self.supabase.get_ytd_claims_amount(
                        state["member_id"],
                        category=state["claim_category"].value
                    )
                except Exception as e:
                    logger.warning(f"Failed to get YTD category claims: {e}")
            
            category_check = self.policy_engine.check_category_limit(
                claimed_amount=state["claimed_amount"],
                category=state["claim_category"],
                ytd_category_claims=ytd_category_claims
            )
            policy_checks.append(category_check)
            
            # 3d. Annual OPD limit check
            ytd_total_claims = 0.0
            if self.supabase:
                try:
                    ytd_total_claims = self.supabase.get_ytd_claims_amount(
                        state["member_id"]
                    )
                except Exception as e:
                    logger.warning(f"Failed to get YTD total claims: {e}")
            
            annual_check = self.policy_engine.check_annual_limit(
                claimed_amount=state["claimed_amount"],
                ytd_total_claims=ytd_total_claims
            )
            policy_checks.append(annual_check)
            
            # 3e. Exclusions check
            exclusion_check = self.policy_engine.check_exclusions(
                diagnosis=diagnosis,
                treatment=extracted_data.get("treatment"),
                procedures=[item.get("description", "") for item in line_items] if line_items else None,
                category=state["claim_category"]
            )
            policy_checks.append(exclusion_check)
            
            # 3f. Pre-authorization check
            tests_or_procedures = extracted_data.get("tests_ordered", [])
            if line_items:
                tests_or_procedures.extend([item.get("description", "") for item in line_items])
            
            preauth_check = self.policy_engine.check_pre_authorization(
                category=state["claim_category"],
                amount=state["claimed_amount"],
                tests_or_procedures=tests_or_procedures if tests_or_procedures else None
            )
            policy_checks.append(preauth_check)
            
            # Step 4: Validate line items if present
            line_item_results = []
            if line_items:
                line_item_results = self._validate_line_items(
                    line_items,
                    state["claim_category"]
                )
            
            # Step 5: Calculate eligible amount
            # Only a FAILED check blocks a claim. WARNING is advisory (e.g. a
            # soft category sub-limit) and must not reject the claim outright.
            all_checks_passed = all(
                check.result != PolicyCheckResult.FAILED
                for check in policy_checks
            )
            
            if all_checks_passed:
                # Calculate final amount with co-pay and network discount
                is_network = self.policy_engine.is_network_hospital(
                    state.get("hospital_name") or extracted_data.get("hospital_name")
                )
                
                # Start with claimed amount; only PASSED checks may cap it lower.
                # (A WARNING check's eligible_amount is advisory and must not
                # silently reduce the payout.)
                base_amount = state["claimed_amount"]
                for check in policy_checks:
                    if (
                        check.result == PolicyCheckResult.PASSED
                        and check.eligible_amount is not None
                        and check.eligible_amount < base_amount
                    ):
                        base_amount = check.eligible_amount
                
                # Apply line item filtering if needed
                if line_item_results:
                    approved_items_total = sum(
                        item["approved_amount"] 
                        for item in line_item_results
                    )
                    base_amount = min(base_amount, approved_items_total)
                
                # Apply co-pay and network discount
                financial_calc = self.policy_engine.apply_copay_and_discount(
                    amount=base_amount,
                    category=state["claim_category"],
                    is_network_hospital=is_network
                )
                
                final_eligible_amount = financial_calc["final_amount"]
                applied_copay = financial_calc["copay_amount"]
                applied_network_discount = financial_calc["network_discount"]
            else:
                # If any check failed, eligible amount is 0
                final_eligible_amount = 0.0
                applied_copay = None
                applied_network_discount = None
            
            # Step 6: Build validation result
            validation_result = PolicyValidationResult(
                member_found=True,
                member_data=member_data,
                policy_checks=policy_checks,
                all_checks_passed=all_checks_passed,
                final_eligible_amount=final_eligible_amount,
                applied_copay=applied_copay,
                applied_network_discount=applied_network_discount,
                line_item_results=line_item_results
            )
            
            # Update state
            state["policy_validation"] = validation_result
            state["eligible_amount"] = final_eligible_amount
            
            # Add to trace
            self._add_trace(state, start_time, validation_result, success=True)
            state["components_executed"].append(self.agent_name)
            
            # Log event
            log_claim_event(
                claim_id=claim_id,
                event_type="POLICY_VALIDATION_COMPLETED",
                agent_name=self.agent_name,
                details={
                    "all_checks_passed": all_checks_passed,
                    "eligible_amount": final_eligible_amount,
                    "num_checks": len(policy_checks),
                    "failed_checks": [
                        check.check_name 
                        for check in policy_checks 
                        if check.result == PolicyCheckResult.FAILED
                    ]
                },
                member_id=state["member_id"]
            )
            
            logger.info(
                f"[{self.agent_name}] Validation completed for {claim_id}: "
                f"passed={all_checks_passed}, eligible=₹{final_eligible_amount:.2f}"
            )

            # Log the reason for each check (explainability)
            for check in policy_checks:
                logger.info(
                    f"[{self.agent_name}] Check '{check.check_name}': "
                    f"{check.result.value} — {check.message}"
                )
            if not all_checks_passed:
                failed = [c.check_name for c in policy_checks if c.result == PolicyCheckResult.FAILED]
                logger.info(f"[{self.agent_name}] Claim failed policy checks: {', '.join(failed)}")
            
            return state
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error during validation: {e}")
            
            # Mark component as failed but continue pipeline
            state["errors"].append({
                "agent": self.agent_name,
                "error": str(e),
                "timestamp": time.time()
            })
            state["components_failed"].append(self.agent_name)
            
            # Set defaults
            state["policy_validation"] = PolicyValidationResult(
                member_found=member_found,
                member_data=member_data,
                policy_checks=[],
                all_checks_passed=False,
                final_eligible_amount=0.0
            )
            state["eligible_amount"] = 0.0
            
            # Add trace
            state["trace"].append({
                "agent": self.agent_name,
                "timestamp": time.time(),
                "status": "failed",
                "error": str(e)
            })
            
            logger.warning(f"[{self.agent_name}] Continuing pipeline despite validation failure")
            
            return state
    
    def _validate_line_items(
        self,
        line_items: List[Dict[str, Any]],
        category: str
    ) -> List[Dict[str, Any]]:
        """
        Validate individual line items (for partial approvals).
        
        Args:
            line_items: List of line items from bill
            category: Claim category
            
        Returns:
            List of validation results per line item
        """
        results = []
        
        coverage = self.policy_engine.get_coverage_category(category)
        
        for item in line_items:
            description = item.get("description", "")
            amount = item.get("amount", 0.0)
            
            # Check if item is in excluded procedures
            is_excluded = False
            exclusion_reason = None
            
            if coverage and coverage.excluded_procedures:
                for excluded in coverage.excluded_procedures:
                    if excluded.lower() in description.lower():
                        is_excluded = True
                        exclusion_reason = f"{excluded} is not covered"
                        break
            
            # Build result
            if is_excluded:
                results.append({
                    "description": description,
                    "claimed_amount": amount,
                    "approved_amount": 0.0,
                    "status": "REJECTED",
                    "reason": exclusion_reason
                })
            else:
                results.append({
                    "description": description,
                    "claimed_amount": amount,
                    "approved_amount": amount,
                    "status": "APPROVED",
                    "reason": None
                })
        
        return results
    
    def _add_trace(
        self,
        state: ClaimState,
        start_time: float,
        validation_result: PolicyValidationResult,
        success: bool
    ):
        """Add trace entry for this agent"""
        elapsed_time = time.time() - start_time
        
        trace_entry = {
            "agent": self.agent_name,
            "timestamp": time.time(),
            "duration_seconds": elapsed_time,
            "input": {
                "claim_id": state["claim_id"],
                "member_id": state["member_id"],
                "claimed_amount": state["claimed_amount"],
                "category": state["claim_category"].value
            },
            "output": {
                "member_found": validation_result.member_found,
                "all_checks_passed": validation_result.all_checks_passed,
                "eligible_amount": validation_result.final_eligible_amount,
                "num_checks": len(validation_result.policy_checks),
                "checks": [
                    {
                        "name": check.check_name,
                        "result": check.result.value,
                        "message": check.message
                    }
                    for check in validation_result.policy_checks
                ],
                "applied_copay": validation_result.applied_copay,
                "applied_network_discount": validation_result.applied_network_discount
            },
            "status": "success" if success else "failed"
        }
        
        state["trace"].append(trace_entry)


# Factory function
def create_policy_validator() -> PolicyValidatorAgent:
    """Create PolicyValidator agent instance"""
    return PolicyValidatorAgent()
