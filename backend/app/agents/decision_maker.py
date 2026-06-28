"""
DecisionMaker Agent

Fifth and final agent in the claims processing pipeline.
Aggregates all previous agent outputs and makes final decision.
"""

import time
from typing import List

from ..models import (
    ClaimState,
    ClaimDecision,
    ClaimDecisionOutput,
    RejectionReason,
    PolicyCheckResult
)
from ..exceptions import DecisionMakingError
from ..loggers import logger, log_claim_event


class DecisionMakerAgent:
    """
    Agent responsible for making the final claim decision.
    
    Decision logic:
    1. If verification failed → No decision (already stopped)
    2. If fraud score >= threshold OR manual review required → MANUAL_REVIEW
    3. If any critical policy check failed → REJECTED
    4. If some line items rejected but others approved → PARTIAL
    5. If all passed → APPROVED
    
    Also calculates:
    - Final approved amount
    - Confidence score (reduced for failed components)
    - Comprehensive trace
    - Decision message
    """
    
    def __init__(self):
        self.agent_name = "DecisionMaker"
        logger.info(f"[{self.agent_name}] Agent initialized")
    
    def decide(self, state: ClaimState) -> ClaimState:
        """
        Make final decision on the claim.
        
        Args:
            state: Current claim state
            
        Returns:
            Updated claim state with final decision
        """
        claim_id = state["claim_id"]
        logger.info(f"[{self.agent_name}] Starting decision making for claim: {claim_id}")
        
        start_time = time.time()
        
        try:
            # Check if verification failed (should have been stopped already)
            verification_result = state.get("verification_result")
            if verification_result and not verification_result.verification_passed:
                # Should not reach here, but handle gracefully
                decision = None
                logger.warning(f"[{self.agent_name}] Verification failed, no decision made")
                state["final_decision"] = None
                state["decision"] = None
                return state
            
            # Get all agent results
            policy_validation = state.get("policy_validation")
            fraud_detection = state.get("fraud_detection")
            
            # Step 1: Check if manual review is required
            if self._requires_manual_review(state, fraud_detection):
                decision = self._create_manual_review_decision(state, fraud_detection)
                state["final_decision"] = decision
                state["decision"] = ClaimDecision.MANUAL_REVIEW
                state["approved_amount"] = 0.0
                state["confidence_score"] = self._calculate_confidence(state)
                
                self._add_trace(state, start_time, decision)
                self._log_decision(state, decision)
                return state
            
            # Step 2: Check policy validation results
            if not policy_validation or not policy_validation.all_checks_passed:
                decision = self._create_rejected_decision(state, policy_validation)
                state["final_decision"] = decision
                state["decision"] = ClaimDecision.REJECTED
                state["approved_amount"] = 0.0
                state["confidence_score"] = self._calculate_confidence(state)
                
                self._add_trace(state, start_time, decision)
                self._log_decision(state, decision)
                return state
            
            # Step 3: Check for partial approval (line items)
            if policy_validation.line_item_results:
                has_rejected_items = any(
                    item.get("status") == "REJECTED"
                    for item in policy_validation.line_item_results
                )
                
                if has_rejected_items:
                    decision = self._create_partial_decision(state, policy_validation)
                    state["final_decision"] = decision
                    state["decision"] = ClaimDecision.PARTIAL
                    state["approved_amount"] = decision.approved_amount
                    state["confidence_score"] = self._calculate_confidence(state)
                    
                    self._add_trace(state, start_time, decision)
                    self._log_decision(state, decision)
                    return state
            
            # Step 4: Full approval
            decision = self._create_approved_decision(state, policy_validation)
            state["final_decision"] = decision
            state["decision"] = ClaimDecision.APPROVED
            state["approved_amount"] = decision.approved_amount
            state["confidence_score"] = self._calculate_confidence(state)
            
            self._add_trace(state, start_time, decision)
            self._log_decision(state, decision)
            
            # Mark processing as complete
            state["processing_end_time"] = time.time()
            
            logger.info(
                f"[{self.agent_name}] Decision completed for {claim_id}: "
                f"{decision.decision.value}, approved=₹{decision.approved_amount:.2f}, "
                f"confidence={decision.confidence_score:.2f}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error during decision making: {e}")
            
            # This is critical - mark as failed but create a manual review decision
            state["errors"].append({
                "agent": self.agent_name,
                "error": str(e),
                "timestamp": time.time()
            })
            state["components_failed"].append(self.agent_name)
            
            # Create manual review decision as fallback
            decision = ClaimDecisionOutput(
                decision=ClaimDecision.MANUAL_REVIEW,
                approved_amount=0.0,
                rejection_reasons=[],
                decision_message="System error occurred during decision making. Manual review required.",
                confidence_score=0.0,
                original_amount=state["claimed_amount"],
                requires_manual_review=True,
                manual_review_reason=f"Decision making error: {str(e)}",
                components_failed=state.get("components_failed", [])
            )
            
            state["final_decision"] = decision
            state["decision"] = ClaimDecision.MANUAL_REVIEW
            state["approved_amount"] = 0.0
            state["confidence_score"] = 0.0
            
            state["trace"].append({
                "agent": self.agent_name,
                "timestamp": time.time(),
                "status": "failed",
                "error": str(e),
                "fallback_decision": "MANUAL_REVIEW"
            })
            
            return state
    
    def _requires_manual_review(self, state: ClaimState, fraud_detection) -> bool:
        """Check if manual review is required"""
        if not fraud_detection:
            return False
        
        # Manual review if fraud detection flags it
        if fraud_detection.requires_manual_review:
            return True
        
        # Manual review if fraud score is high
        if fraud_detection.fraud_score >= 0.80:
            return True
        
        return False
    
    def _create_manual_review_decision(
        self,
        state: ClaimState,
        fraud_detection
    ) -> ClaimDecisionOutput:
        """Create manual review decision"""
        reasons = []
        
        if fraud_detection and fraud_detection.fraud_signals:
            signal_descriptions = [
                f"{signal.signal_type}: {signal.description}"
                for signal in fraud_detection.fraud_signals
            ]
            reason = f"Fraud signals detected: {'; '.join(signal_descriptions)}"
        else:
            reason = "High-value claim requires manual review"
        
        return ClaimDecisionOutput(
            decision=ClaimDecision.MANUAL_REVIEW,
            approved_amount=0.0,
            rejection_reasons=[],
            decision_message=f"Claim flagged for manual review. Reason: {reason}",
            confidence_score=self._calculate_confidence(state),
            original_amount=state["claimed_amount"],
            requires_manual_review=True,
            manual_review_reason=reason,
            components_failed=state.get("components_failed", [])
        )
    
    def _create_rejected_decision(
        self,
        state: ClaimState,
        policy_validation
    ) -> ClaimDecisionOutput:
        """Create rejected decision"""
        rejection_reasons = []
        rejection_messages = []
        
        if policy_validation:
            for check in policy_validation.policy_checks:
                if check.result == PolicyCheckResult.FAILED:
                    rejection_messages.append(check.message)
                    
                    # Map check names to rejection reasons
                    reason_map = {
                        "initial_waiting_period": RejectionReason.WAITING_PERIOD,
                        "condition_waiting_period": RejectionReason.WAITING_PERIOD,
                        "waiting_period": RejectionReason.WAITING_PERIOD,
                        "per_claim_limit": RejectionReason.PER_CLAIM_EXCEEDED,
                        "category_limit": RejectionReason.CATEGORY_LIMIT_EXCEEDED,
                        "annual_limit": RejectionReason.ANNUAL_LIMIT_EXCEEDED,
                        "exclusions": RejectionReason.EXCLUDED_CONDITION,
                        "pre_authorization": RejectionReason.PRE_AUTH_MISSING,
                        "member_validation": RejectionReason.MEMBER_NOT_FOUND
                    }
                    
                    reason = reason_map.get(check.check_name, RejectionReason.INCOMPLETE_INFORMATION)
                    if reason not in rejection_reasons:
                        rejection_reasons.append(reason)
        
        if not rejection_reasons:
            rejection_reasons.append(RejectionReason.INCOMPLETE_INFORMATION)
        
        decision_message = "Claim rejected. Reasons: " + "; ".join(rejection_messages)
        
        return ClaimDecisionOutput(
            decision=ClaimDecision.REJECTED,
            approved_amount=0.0,
            rejection_reasons=rejection_reasons,
            decision_message=decision_message,
            confidence_score=self._calculate_confidence(state),
            original_amount=state["claimed_amount"],
            components_failed=state.get("components_failed", [])
        )
    
    def _create_partial_decision(
        self,
        state: ClaimState,
        policy_validation
    ) -> ClaimDecisionOutput:
        """Create partial approval decision"""
        # Calculate approved amount from line items
        approved_items = [
            item for item in policy_validation.line_item_results
            if item.get("status") == "APPROVED"
        ]
        rejected_items = [
            item for item in policy_validation.line_item_results
            if item.get("status") == "REJECTED"
        ]
        
        approved_amount = sum(item.get("approved_amount", 0) for item in approved_items)
        
        # Build message
        approved_desc = ", ".join([item["description"] for item in approved_items])
        rejected_desc = ", ".join([
            f"{item['description']} ({item.get('reason', 'excluded')})"
            for item in rejected_items
        ])
        
        decision_message = (
            f"Claim partially approved. Approved items: {approved_desc}. "
            f"Rejected items: {rejected_desc}. "
            f"Approved amount: ₹{approved_amount:,.2f}"
        )
        
        return ClaimDecisionOutput(
            decision=ClaimDecision.PARTIAL,
            approved_amount=approved_amount,
            rejection_reasons=[],
            decision_message=decision_message,
            confidence_score=self._calculate_confidence(state),
            original_amount=state["claimed_amount"],
            copay_deducted=policy_validation.applied_copay,
            network_discount_applied=policy_validation.applied_network_discount,
            components_failed=state.get("components_failed", [])
        )
    
    def _create_approved_decision(
        self,
        state: ClaimState,
        policy_validation
    ) -> ClaimDecisionOutput:
        """Create approved decision"""
        approved_amount = policy_validation.final_eligible_amount
        
        # Build message
        message_parts = [f"Claim approved. Amount: ₹{approved_amount:,.2f}"]
        
        if policy_validation.applied_network_discount:
            message_parts.append(
                f"Network discount applied: ₹{policy_validation.applied_network_discount:,.2f}"
            )
        
        if policy_validation.applied_copay:
            message_parts.append(
                f"Co-pay deducted: ₹{policy_validation.applied_copay:,.2f}"
            )
        
        decision_message = ". ".join(message_parts) + "."

        # If any component failed (e.g. graceful degradation / TC011), surface
        # that processing was incomplete and recommend manual review.
        components_failed = state.get("components_failed", [])
        degraded = bool(components_failed)
        manual_review_reason = None
        if degraded:
            failed = ", ".join(sorted(set(components_failed)))
            decision_message += (
                f" Note: {failed} did not complete, so processing was partial. "
                f"Manual review is recommended due to incomplete processing."
            )
            manual_review_reason = (
                f"Incomplete processing — the following component(s) failed: {failed}."
            )

        return ClaimDecisionOutput(
            decision=ClaimDecision.APPROVED,
            approved_amount=approved_amount,
            rejection_reasons=[],
            decision_message=decision_message,
            confidence_score=self._calculate_confidence(state),
            original_amount=state["claimed_amount"],
            copay_deducted=policy_validation.applied_copay,
            network_discount_applied=policy_validation.applied_network_discount,
            requires_manual_review=degraded,
            manual_review_reason=manual_review_reason,
            components_failed=components_failed
        )
    
    def _calculate_confidence(self, state: ClaimState) -> float:
        """
        Calculate overall confidence score.
        
        Starts at 1.0, reduces by 0.2 for each failed component.
        Also reduces based on OCR extraction confidence.
        """
        confidence = 1.0
        
        # Reduce for failed components
        num_failed = len(state.get("components_failed", []))
        confidence -= (num_failed * 0.2)
        
        # Factor in OCR extraction confidence
        extraction_confidence = state.get("extraction_confidence", 1.0)
        if extraction_confidence < 0.8:
            confidence -= 0.1
        
        # Factor in fraud score (high fraud score reduces confidence)
        fraud_score = state.get("fraud_score", 0.0)
        if fraud_score > 0.5:
            confidence -= 0.1
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))
    
    def _add_trace(
        self,
        state: ClaimState,
        start_time: float,
        decision: ClaimDecisionOutput
    ):
        """Add trace entry for this agent"""
        elapsed_time = time.time() - start_time
        
        trace_entry = {
            "agent": self.agent_name,
            "timestamp": time.time(),
            "duration_seconds": elapsed_time,
            "input": {
                "claim_id": state["claim_id"],
                "policy_checks_passed": state.get("policy_validation", {}).all_checks_passed if state.get("policy_validation") else False,
                "fraud_score": state.get("fraud_score", 0.0),
                "eligible_amount": state.get("eligible_amount", 0.0)
            },
            "output": {
                "decision": decision.decision.value,
                "approved_amount": decision.approved_amount,
                "confidence_score": decision.confidence_score,
                "decision_message": decision.decision_message,
                "rejection_reasons": [r.value for r in decision.rejection_reasons],
                "requires_manual_review": decision.requires_manual_review,
                "components_failed": decision.components_failed
            },
            "status": "success"
        }
        
        state["trace"].append(trace_entry)
        state["components_executed"].append(self.agent_name)
    
    def _log_decision(self, state: ClaimState, decision: ClaimDecisionOutput):
        """Log decision event"""
        # Human-readable decision + reason for the log file (explainability)
        logger.info(
            f"[{self.agent_name}] DECISION={decision.decision.value} "
            f"for claim {state['claim_id']}: {decision.decision_message}"
        )
        if decision.rejection_reasons:
            logger.info(
                f"[{self.agent_name}] Rejection reasons: "
                f"{', '.join(r.value for r in decision.rejection_reasons)}"
            )
        if decision.requires_manual_review and decision.manual_review_reason:
            logger.info(
                f"[{self.agent_name}] Manual review reason: {decision.manual_review_reason}"
            )

        log_claim_event(
            claim_id=state["claim_id"],
            event_type=f"DECISION_{decision.decision.value}",
            agent_name=self.agent_name,
            details={
                "decision": decision.decision.value,
                "approved_amount": decision.approved_amount,
                "confidence_score": decision.confidence_score,
                "components_failed": decision.components_failed
            },
            member_id=state["member_id"]
        )


# Factory function
def create_decision_maker() -> DecisionMakerAgent:
    """Create DecisionMaker agent instance"""
    return DecisionMakerAgent()
