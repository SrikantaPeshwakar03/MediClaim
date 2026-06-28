"""
LangGraph State Model

Defines the state schema used by the LangGraph orchestrator.
This state is passed between all agents in the pipeline.
"""

from typing import TypedDict, Optional, Dict, Any, List
from datetime import date
from .enums import ClaimCategory, ClaimDecision
from .document import DocumentVerificationResult, OCRResult
from .policy import PolicyValidationResult
from .claim import FraudDetectionResult, ClaimDecisionOutput


class ClaimState(TypedDict, total=False):
    """
    State schema for claim processing pipeline.
    
    This state is passed through all agents in sequence:
    DocumentVerifier → OCRExtractor → PolicyValidator → FraudDetector → DecisionMaker
    
    Each agent reads from previous agent outputs and adds its own results.
    """
    
    # === Input Data (from claim submission) ===
    claim_id: str
    member_id: str
    policy_id: str
    claim_category: ClaimCategory
    treatment_date: date
    claimed_amount: float
    hospital_name: Optional[str]
    
    # Document information
    document_file_paths: List[str]  # Paths to uploaded files in storage
    document_metadata: List[Dict[str, Any]]  # Metadata for each document

    # Testing / resilience: when True, one component deliberately fails to
    # exercise the graceful-degradation path (TC011).
    simulate_component_failure: bool
    
    # === Agent Outputs ===
    
    # 1. DocumentVerifier
    verification_result: Optional[DocumentVerificationResult]
    stop_processing: bool  # If True, pipeline stops (verification failed)
    
    # 2. OCRExtractor
    ocr_results: List[OCRResult]
    extracted_data: Dict[str, Any]  # Consolidated extracted data from all documents
    extraction_confidence: float  # Overall extraction confidence
    extraction_errors: List[str]  # Errors during OCR
    
    # 3. PolicyValidator
    policy_validation: Optional[PolicyValidationResult]
    eligible_amount: float  # Amount eligible after policy checks
    
    # 4. FraudDetector
    fraud_detection: Optional[FraudDetectionResult]
    fraud_score: float
    
    # 5. DecisionMaker
    final_decision: Optional[ClaimDecisionOutput]
    decision: Optional[ClaimDecision]
    approved_amount: float
    confidence_score: float
    
    # === Trace & Error Handling ===
    #
    # NOTE: These are plain lists (no LangGraph `add` reducer) because the agents
    # mutate them in place via .append()/.extend() and return the full state.
    # An `add` reducer would concatenate the already-accumulated list onto itself
    # at every node, producing duplicate trace entries.

    # Trace for explainability
    trace: List[Dict[str, Any]]  # Each agent appends its trace
    
    # Error handling
    errors: List[Dict[str, Any]]  # Component failures
    warnings: List[Dict[str, Any]]  # Non-critical issues
    
    # Component status tracking
    components_executed: List[str]  # Successfully executed agents
    components_failed: List[str]  # Failed agents (graceful degradation)
    
    # === Metadata ===
    processing_start_time: float  # Unix timestamp
    processing_end_time: Optional[float]


# Initial state factory
def create_initial_state(
    claim_id: str,
    member_id: str,
    policy_id: str,
    claim_category: ClaimCategory,
    treatment_date: date,
    claimed_amount: float,
    document_file_paths: List[str],
    document_metadata: List[Dict[str, Any]],
    hospital_name: Optional[str] = None,
    simulate_component_failure: bool = False
) -> ClaimState:
    """
    Create initial state for a new claim.
    
    This is the starting point for the LangGraph pipeline.
    """
    import time
    
    return ClaimState(
        # Input data
        claim_id=claim_id,
        member_id=member_id,
        policy_id=policy_id,
        claim_category=claim_category,
        treatment_date=treatment_date,
        claimed_amount=claimed_amount,
        hospital_name=hospital_name,
        document_file_paths=document_file_paths,
        document_metadata=document_metadata,
        simulate_component_failure=simulate_component_failure,
        
        # Agent outputs (initialized to None/defaults)
        verification_result=None,
        stop_processing=False,
        ocr_results=[],
        extracted_data={},
        extraction_confidence=0.0,
        extraction_errors=[],
        policy_validation=None,
        eligible_amount=0.0,
        fraud_detection=None,
        fraud_score=0.0,
        final_decision=None,
        decision=None,
        approved_amount=0.0,
        confidence_score=0.0,
        
        # Trace & error handling
        trace=[],
        errors=[],
        warnings=[],
        components_executed=[],
        components_failed=[],
        
        # Metadata
        processing_start_time=time.time(),
        processing_end_time=None
    )
