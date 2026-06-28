"""
FraudDetector Agent

Fourth agent in the claims processing pipeline.
Detects fraud signals and calculates fraud risk score.
"""

import time
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..models import (
    ClaimState,
    FraudDetectionResult,
    FraudSignal
)
from ..config import settings
from ..exceptions import FraudDetectionError
from ..loggers import logger, log_claim_event


class FraudDetectorAgent:
    """
    Agent responsible for detecting potential fraud signals.
    
    Signals detected:
    1. Same-day claims (multiple claims from same member on same day)
    2. Monthly claims limit exceeded
    3. High-value claims (above threshold)
    4. Duplicate document hashes (if available)
    5. Amount anomalies (compared to historical average)
    6. Suspicious patterns
    """
    
    def __init__(self):
        self.agent_name = "FraudDetector"
        self._supabase_service = None
        self._policy_data = None
        
        # Load fraud thresholds from policy file
        self._load_fraud_thresholds()
        logger.info(f"[{self.agent_name}] Agent initialized")
    
    def _load_fraud_thresholds(self):
        """Load fraud thresholds from policy_terms.json"""
        try:
            from ..config import get_policy_file_path
            import json
            
            policy_path = get_policy_file_path()
            with open(policy_path, 'r') as f:
                self._policy_data = json.load(f)
            
            fraud_config = self._policy_data.get("fraud_thresholds", {})
            self.fraud_score_threshold = fraud_config.get("fraud_score_manual_review_threshold", 0.80)
            self.high_value_threshold = fraud_config.get("high_value_claim_threshold", 25000)
            self.same_day_limit = fraud_config.get("same_day_claims_limit", 2)
            self.monthly_limit = fraud_config.get("monthly_claims_limit", 6)
            
            logger.info(
                f"Fraud thresholds loaded from policy: "
                f"score_threshold={self.fraud_score_threshold}, "
                f"high_value={self.high_value_threshold}"
            )
            
        except Exception as e:
            logger.warning(f"Failed to load fraud thresholds from policy, using defaults: {e}")
            # Fallback to defaults
            self.fraud_score_threshold = 0.80
            self.high_value_threshold = 25000
            self.same_day_limit = 2
            self.monthly_limit = 6
    
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
    
    def detect(self, state: ClaimState) -> ClaimState:
        """
        Detect fraud signals in the claim.
        
        Args:
            state: Current claim state
            
        Returns:
            Updated claim state with fraud detection results
        """
        claim_id = state["claim_id"]
        logger.info(f"[{self.agent_name}] Starting fraud detection for claim: {claim_id}")
        
        start_time = time.time()
        fraud_signals: List[FraudSignal] = []
        fraud_score = 0.0
        requires_manual_review = False
        
        try:
            # Get claim history for this member
            # NOTE: In real implementation, this would query Supabase
            # For now, we'll use mock data or state if available
            claim_history = self._get_claim_history(state["member_id"])
            
            # Signal 1: Same-day claims check
            same_day_signal = self._check_same_day_claims(
                state["member_id"],
                state["treatment_date"],
                claim_history
            )
            if same_day_signal:
                fraud_signals.append(same_day_signal)
                fraud_score += 0.25
            
            # Signal 2: Monthly claims frequency
            monthly_signal = self._check_monthly_claims_frequency(
                state["member_id"],
                state["treatment_date"],
                claim_history
            )
            if monthly_signal:
                fraud_signals.append(monthly_signal)
                fraud_score += 0.20
            
            # Signal 3: High-value claim
            high_value_signal = self._check_high_value_claim(state["claimed_amount"])
            if high_value_signal:
                fraud_signals.append(high_value_signal)
                fraud_score += 0.15
            
            # Signal 4: Amount anomaly (compared to member's historical average)
            anomaly_signal = self._check_amount_anomaly(
                state["claimed_amount"],
                claim_history
            )
            if anomaly_signal:
                fraud_signals.append(anomaly_signal)
                fraud_score += 0.20
            
            # Signal 5: Rapid claim submission after joining
            rapid_signal = self._check_rapid_submission(
                state["member_id"],
                state["treatment_date"]
            )
            if rapid_signal:
                fraud_signals.append(rapid_signal)
                fraud_score += 0.10
            
            # Signal 6: Multiple claims to same hospital in short period
            hospital_signal = self._check_hospital_pattern(
                state["member_id"],
                state.get("hospital_name"),
                claim_history
            )
            if hospital_signal:
                fraud_signals.append(hospital_signal)
                fraud_score += 0.10

            # Signal 7: Document integrity — alterations / duplicate stamps
            # (per sample_documents_guide.md: flag DOCUMENT_ALTERATION and
            # duplicate "ORIGINAL"/"DUPLICATE" stamps for review)
            integrity_signal = self._check_document_integrity(
                state.get("ocr_results", []),
                state.get("extracted_data", {}).get("integrity_flags", [])
            )
            if integrity_signal:
                fraud_signals.append(integrity_signal)
                fraud_score += 0.15
            
            # Cap fraud score at 1.0
            fraud_score = min(fraud_score, 1.0)
            
            # Determine if manual review is required.
            # Any HIGH-severity signal (e.g. same-day claim limit breach) forces
            # manual review even if the aggregate score is below threshold.
            has_high_severity = any(s.severity == "HIGH" for s in fraud_signals)
            requires_manual_review = (
                fraud_score >= self.fraud_score_threshold or
                state["claimed_amount"] >= self.high_value_threshold or
                has_high_severity
            )
            
            # Build fraud detection result
            fraud_detection = FraudDetectionResult(
                fraud_score=fraud_score,
                fraud_signals=fraud_signals,
                requires_manual_review=requires_manual_review,
                claim_history=claim_history
            )
            
            # Update state
            state["fraud_detection"] = fraud_detection
            state["fraud_score"] = fraud_score
            
            # Add to trace
            elapsed_time = time.time() - start_time
            trace_entry = {
                "agent": self.agent_name,
                "timestamp": time.time(),
                "duration_seconds": elapsed_time,
                "input": {
                    "claim_id": claim_id,
                    "member_id": state["member_id"],
                    "claimed_amount": state["claimed_amount"]
                },
                "output": {
                    "fraud_score": round(fraud_score, 2),
                    "num_signals": len(fraud_signals),
                    "requires_manual_review": requires_manual_review,
                    "signals": [
                        {
                            "type": signal.signal_type,
                            "severity": signal.severity,
                            "description": signal.description
                        }
                        for signal in fraud_signals
                    ]
                },
                "status": "success"
            }
            state["trace"].append(trace_entry)
            state["components_executed"].append(self.agent_name)
            
            # Log event
            log_claim_event(
                claim_id=claim_id,
                event_type="FRAUD_DETECTION_COMPLETED",
                agent_name=self.agent_name,
                details={
                    "fraud_score": fraud_score,
                    "num_signals": len(fraud_signals),
                    "requires_manual_review": requires_manual_review
                },
                member_id=state["member_id"]
            )
            
            logger.info(
                f"[{self.agent_name}] Fraud detection completed for {claim_id}: "
                f"score={fraud_score:.2f}, signals={len(fraud_signals)}, "
                f"manual_review={requires_manual_review}"
            )

            # Log the reason for each fraud signal (explainability)
            for signal in fraud_signals:
                logger.info(
                    f"[{self.agent_name}] Fraud signal [{signal.severity}] "
                    f"{signal.signal_type}: {signal.description}"
                )
            
            return state
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error during fraud detection: {e}")
            
            # Mark component as failed but continue pipeline
            state["errors"].append({
                "agent": self.agent_name,
                "error": str(e),
                "timestamp": time.time()
            })
            state["components_failed"].append(self.agent_name)
            
            # Set defaults (conservative: assume no fraud)
            state["fraud_detection"] = FraudDetectionResult(
                fraud_score=0.0,
                fraud_signals=[],
                requires_manual_review=False,
                claim_history=[]
            )
            state["fraud_score"] = 0.0
            
            # Add trace
            state["trace"].append({
                "agent": self.agent_name,
                "timestamp": time.time(),
                "status": "failed",
                "error": str(e)
            })
            
            logger.warning(f"[{self.agent_name}] Continuing pipeline despite fraud detection failure")
            
            return state
    
    def _get_claim_history(self, member_id: str) -> List[Dict[str, Any]]:
        """
        Get claim history for member.
        
        Args:
            member_id: Member ID
            
        Returns:
            List of past claims (with treatment_date normalized to date objects)
        """
        if self.supabase:
            try:
                history = self.supabase.get_claim_history(member_id, limit=50)
                history = self._normalize_history_dates(history)
                logger.info(f"Retrieved {len(history)} past claims for member {member_id}")
                return history
            except Exception as e:
                logger.error(f"Failed to get claim history from Supabase: {e}")
                return []
        else:
            # Fallback to empty list if Supabase not available
            logger.warning("Supabase not available, using empty claim history")
            return []

    @staticmethod
    def _normalize_history_dates(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert string dates from the database into `date` objects so the
        fraud checks can safely use `.month`, `.year`, and date arithmetic.
        """
        for claim in history:
            td = claim.get("treatment_date")
            if isinstance(td, str):
                parsed = None
                # Try full ISO format first, then fall back to YYYY-MM-DD
                try:
                    parsed = datetime.fromisoformat(td.replace("Z", "")).date()
                except ValueError:
                    try:
                        parsed = datetime.strptime(td[:10], "%Y-%m-%d").date()
                    except ValueError:
                        parsed = None
                claim["treatment_date"] = parsed
            elif isinstance(td, datetime):
                claim["treatment_date"] = td.date()
        return history
    
    def _check_same_day_claims(
        self,
        member_id: str,
        treatment_date,
        claim_history: List[Dict[str, Any]]
    ) -> FraudSignal | None:
        """
        Check for multiple claims on the same day.
        
        Args:
            member_id: Member ID
            treatment_date: Treatment date
            claim_history: Past claims
            
        Returns:
            FraudSignal if pattern detected, None otherwise
        """
        if not claim_history:
            return None
        
        # Count claims on same day
        same_day_count = sum(
            1 for claim in claim_history
            if claim.get("treatment_date") == treatment_date
        )
        
        if same_day_count >= self.same_day_limit:
            return FraudSignal(
                signal_type="SAME_DAY_CLAIMS",
                severity="HIGH",
                description=f"Member has {same_day_count} claims on {treatment_date} (including this one). "
                           f"This exceeds the policy limit of {self.same_day_limit} claims per day.",
                evidence={
                    "same_day_claims_count": same_day_count,
                    "treatment_date": str(treatment_date),
                    "limit": self.same_day_limit
                }
            )
        
        return None
    
    def _check_monthly_claims_frequency(
        self,
        member_id: str,
        treatment_date,
        claim_history: List[Dict[str, Any]]
    ) -> FraudSignal | None:
        """Check if monthly claims limit is exceeded"""
        if not claim_history:
            return None
        
        # Count claims in current month
        current_month = treatment_date.month
        current_year = treatment_date.year
        
        monthly_count = sum(
            1 for claim in claim_history
            if (claim.get("treatment_date") and
                claim["treatment_date"].month == current_month and
                claim["treatment_date"].year == current_year)
        )
        
        if monthly_count >= self.monthly_limit:
            return FraudSignal(
                signal_type="MONTHLY_CLAIMS_EXCEEDED",
                severity="MEDIUM",
                description=f"Member has {monthly_count} claims in {treatment_date.strftime('%B %Y')} "
                           f"(including this one). This exceeds the policy limit of {self.monthly_limit} per month.",
                evidence={
                    "monthly_claims_count": monthly_count,
                    "month": f"{current_year}-{current_month:02d}",
                    "limit": self.monthly_limit
                }
            )
        
        return None
    
    def _check_high_value_claim(self, claimed_amount: float) -> FraudSignal | None:
        """Check if claim amount is unusually high"""
        if claimed_amount >= self.high_value_threshold:
            return FraudSignal(
                signal_type="HIGH_VALUE_CLAIM",
                severity="MEDIUM",
                description=f"Claim amount of ₹{claimed_amount:,.2f} exceeds high-value threshold "
                           f"of ₹{self.high_value_threshold:,.2f}. Requires additional scrutiny.",
                evidence={
                    "claimed_amount": claimed_amount,
                    "threshold": self.high_value_threshold
                }
            )
        
        return None
    
    def _check_amount_anomaly(
        self,
        claimed_amount: float,
        claim_history: List[Dict[str, Any]]
    ) -> FraudSignal | None:
        """Check if amount is anomalous compared to member's history"""
        if not claim_history or len(claim_history) < 3:
            # Not enough history to determine anomaly
            return None
        
        # Pull past amounts. Supabase returns claimed_amount / approved_amount,
        # so check those first; ignore missing/zero values to avoid a skewed
        # (or zero) average that would cause a division-by-zero.
        amounts = []
        for claim in claim_history:
            amt = (
                claim.get("claimed_amount")
                or claim.get("approved_amount")
                or claim.get("amount")
                or 0
            )
            if amt and amt > 0:
                amounts.append(amt)

        if len(amounts) < 3:
            return None

        avg_amount = sum(amounts) / len(amounts)
        if avg_amount <= 0:
            return None
        
        # Simple anomaly detection: more than 3x average
        if claimed_amount > avg_amount * 3:
            return FraudSignal(
                signal_type="AMOUNT_ANOMALY",
                severity="MEDIUM",
                description=f"Claim amount of ₹{claimed_amount:,.2f} is significantly higher than "
                           f"member's average claim of ₹{avg_amount:,.2f}.",
                evidence={
                    "claimed_amount": claimed_amount,
                    "historical_average": avg_amount,
                    "ratio": round(claimed_amount / avg_amount, 2)
                }
            )
        
        return None
    
    def _check_rapid_submission(
        self,
        member_id: str,
        treatment_date
    ) -> FraudSignal | None:
        """
        Check if claim was submitted very soon after member joined.
        
        NOTE: Requires member data. For now, skip this check.
        Will be implemented when database integration is complete.
        """
        # TODO: Implement when Supabase integration is complete
        return None
    
    def _check_hospital_pattern(
        self,
        member_id: str,
        hospital_name: str | None,
        claim_history: List[Dict[str, Any]]
    ) -> FraudSignal | None:
        """Check for suspicious patterns with specific hospital"""
        if not hospital_name or not claim_history:
            return None
        
        # Count recent claims to same hospital
        recent_claims_same_hospital = sum(
            1 for claim in claim_history
            if (claim.get("hospital_name", "").lower() == hospital_name.lower() and
                claim.get("treatment_date") and
                (datetime.now().date() - claim["treatment_date"]).days <= 30)
        )
        
        # If more than 3 claims to same hospital in 30 days, flag it
        if recent_claims_same_hospital >= 3:
            return FraudSignal(
                signal_type="HOSPITAL_PATTERN",
                severity="LOW",
                description=f"Member has {recent_claims_same_hospital} claims to {hospital_name} "
                           f"in the last 30 days. This pattern may warrant review.",
                evidence={
                    "hospital_name": hospital_name,
                    "claims_count": recent_claims_same_hospital,
                    "period_days": 30
                }
            )
        
        return None

    def _check_document_integrity(self, ocr_results, vision_flags=None) -> "FraudSignal | None":
        """
        Detect document-integrity issues from:
        - Vision-model integrity flags (crossed-out amounts, duplicate stamps, etc.)
        - Raw OCR text markers ("ORIGINAL"/"DUPLICATE" stamps, alteration words)

        Per sample_documents_guide.md these should be surfaced to fraud
        detection rather than silently ignored.
        """
        findings = []

        # 1. Vision-model integrity flags (from image-based extraction)
        flag_descriptions = {
            "CROSSED_OUT_AMOUNT": "An amount appears crossed out / overwritten",
            "DUPLICATE_STAMP": "Duplicate or multiple copy stamps detected",
            "HANDWRITTEN_ALTERATION": "Visible manual edits to printed values",
            "ILLEGIBLE_REGION": "A meaningful region of the document is unreadable",
        }
        for flag in (vision_flags or []):
            findings.append(flag_descriptions.get(flag, f"Integrity flag: {flag}"))

        # 2. Raw OCR text markers
        combined = []
        for r in (ocr_results or []):
            text = getattr(r, "raw_text", None)
            if not text and isinstance(r, dict):
                text = r.get("raw_text")
            if text:
                combined.append(text)

        if combined:
            full_text = " ".join(combined).upper()
            dup_count = full_text.count("DUPLICATE")
            orig_count = full_text.count("ORIGINAL")
            if dup_count >= 1 and orig_count >= 1:
                findings.append("Both 'ORIGINAL' and 'DUPLICATE' stamps present")
            elif dup_count >= 2 or orig_count >= 2:
                findings.append("Multiple copy stamps detected")

            for marker in ["CROSSED OUT", "OVERWRITTEN", "CORRECTED", "CANCELLED", "REWRITTEN"]:
                if marker in full_text:
                    findings.append(f"Possible alteration marker: '{marker.title()}'")

        if not findings:
            return None

        # De-duplicate while preserving order
        seen = set()
        unique_findings = [f for f in findings if not (f in seen or seen.add(f))]

        return FraudSignal(
            signal_type="DOCUMENT_ALTERATION",
            severity="MEDIUM",
            description=(
                "Document integrity concerns detected: "
                + "; ".join(unique_findings)
                + ". Manual verification of original documents is advised."
            ),
            evidence={"findings": unique_findings}
        )


# Factory function
def create_fraud_detector() -> FraudDetectorAgent:
    """Create FraudDetector agent instance"""
    return FraudDetectorAgent()
