"""
LangGraph Orchestrator

Orchestrates the multi-agent claims processing pipeline using LangGraph.
Manages state flow between all 5 agents with conditional routing.
"""

from typing import Literal
from langgraph.graph import StateGraph, END

from ..models import ClaimState
from ..loggers import logger
from .document_verifier import create_document_verifier
from .ocr_extractor import create_ocr_extractor
from .policy_validator import create_policy_validator
from .fraud_detector import create_fraud_detector
from .decision_maker import create_decision_maker


class ClaimsOrchestrator:
    """
    Orchestrator for the claims processing pipeline.
    
    Pipeline flow:
    1. DocumentVerifier → checks documents (STOPS if failed)
    2. OCRExtractor → extracts data (continues even if failed)
    3. PolicyValidator → validates against policy (continues even if failed)
    4. FraudDetector → detects fraud signals (continues even if failed)
    5. DecisionMaker → makes final decision
    """
    
    def __init__(self):
        self.graph = self._build_graph()
        logger.info("Claims orchestrator initialized")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph state graph.
        
        Returns:
            Compiled StateGraph
        """
        # Create workflow
        workflow = StateGraph(ClaimState)
        
        # Create agent instances
        logger.info("Initializing pipeline agents...")
        document_verifier = create_document_verifier()
        ocr_extractor = create_ocr_extractor()
        policy_validator = create_policy_validator()
        fraud_detector = create_fraud_detector()
        decision_maker = create_decision_maker()
        logger.info(
            "All 5 agents created: DocumentVerifier, OCRExtractor, "
            "PolicyValidator, FraudDetector, DecisionMaker"
        )
        
        # Add nodes (agent functions)
        workflow.add_node("verify_documents", document_verifier.verify)
        workflow.add_node("extract_data", ocr_extractor.extract)
        workflow.add_node("validate_policy", policy_validator.validate)
        workflow.add_node("detect_fraud", fraud_detector.detect)
        workflow.add_node("make_decision", decision_maker.decide)
        
        # Set entry point
        workflow.set_entry_point("verify_documents")
        
        # Add conditional edges
        
        # After verification: stop if failed, continue if passed
        workflow.add_conditional_edges(
            "verify_documents",
            self._should_continue_after_verification,
            {
                "continue": "extract_data",
                "stop": END
            }
        )
        
        # After extraction: always continue to validation
        workflow.add_edge("extract_data", "validate_policy")
        
        # After validation: always continue to fraud detection
        workflow.add_edge("validate_policy", "detect_fraud")
        
        # After fraud detection: always continue to decision
        workflow.add_edge("detect_fraud", "make_decision")
        
        # After decision: end
        workflow.add_edge("make_decision", END)
        
        # Compile the graph
        return workflow.compile()
    
    def _should_continue_after_verification(
        self,
        state: ClaimState
    ) -> Literal["continue", "stop"]:
        """
        Determine if pipeline should continue after document verification.
        
        Args:
            state: Current claim state
            
        Returns:
            "continue" if verification passed, "stop" otherwise
        """
        if state.get("stop_processing", False):
            logger.info(f"Pipeline stopped for claim {state['claim_id']}: verification failed")
            return "stop"
        
        return "continue"
    
    def process_claim(self, state: ClaimState) -> ClaimState:
        """
        Process a claim through the complete pipeline.
        
        Args:
            state: Initial claim state
            
        Returns:
            Final claim state with decision
        """
        claim_id = state["claim_id"]
        logger.info(f"Starting claim processing for: {claim_id}")
        
        try:
            # Run the graph
            final_state = self.graph.invoke(state)
            
            logger.info(
                f"Claim processing completed for {claim_id}: "
                f"decision={final_state.get('decision', 'NONE')}"
            )
            
            return final_state
            
        except Exception as e:
            logger.error(f"Orchestrator error for claim {claim_id}: {e}")
            
            # Add error to state
            state["errors"].append({
                "agent": "Orchestrator",
                "error": str(e),
                "timestamp": __import__('time').time()
            })
            
            # Return state with error
            return state


# Singleton instance
_orchestrator = None


def get_orchestrator() -> ClaimsOrchestrator:
    """Get or create orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ClaimsOrchestrator()
    return _orchestrator
