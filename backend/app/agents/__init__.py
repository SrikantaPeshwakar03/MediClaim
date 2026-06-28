"""
Agents Package

Multi-agent system for claims processing.
"""

from .document_verifier import DocumentVerifierAgent, create_document_verifier
from .ocr_extractor import OCRExtractorAgent, create_ocr_extractor
from .policy_validator import PolicyValidatorAgent, create_policy_validator
from .fraud_detector import FraudDetectorAgent, create_fraud_detector
from .decision_maker import DecisionMakerAgent, create_decision_maker

__all__ = [
    "DocumentVerifierAgent",
    "create_document_verifier",
    "OCRExtractorAgent",
    "create_ocr_extractor",
    "PolicyValidatorAgent",
    "create_policy_validator",
    "FraudDetectorAgent",
    "create_fraud_detector",
    "DecisionMakerAgent",
    "create_decision_maker",
]
