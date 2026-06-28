"""
DocumentVerifier Agent

First agent in the claims processing pipeline.
Validates that uploaded documents meet requirements for the claim category.
"""

import time
from typing import Dict, Any
from pathlib import Path

from ..models import (
    ClaimState,
    DocumentType,
    DocumentVerificationResult,
    ClaimCategory
)
from ..services import get_policy_engine, get_ocr_service, get_llm_service
from ..config import settings
from ..exceptions import DocumentVerificationError
from ..loggers import logger, log_claim_event


class DocumentVerifierAgent:
    """
    Agent responsible for verifying uploaded documents before processing.
    
    Checks performed:
    1. Document type classification
    2. Required documents present
    3. Document quality/readability
    4. Patient name consistency across documents
    """
    
    def __init__(self):
        self.policy_engine = get_policy_engine()
        self.ocr_service = get_ocr_service()
        self.llm_service = get_llm_service()
        self.agent_name = "DocumentVerifier"
        logger.info(f"[{self.agent_name}] Agent initialized")
    
    def verify(self, state: ClaimState) -> ClaimState:
        """
        Verify documents for the claim.
        
        Args:
            state: Current claim state
            
        Returns:
            Updated claim state with verification results
        """
        claim_id = state["claim_id"]
        logger.info(f"[{self.agent_name}] Starting verification for claim: {claim_id}")
        
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # Get required documents for this claim category
            required_docs = self.policy_engine.get_document_requirements(
                state["claim_category"]
            )
            
            # Step 1: Classify all uploaded documents
            logger.info(f"[{self.agent_name}] Classifying {len(state['document_file_paths'])} documents")
            document_classifications = self._classify_documents(
                state["document_file_paths"]
            )
            
            # Step 2: Check if all required documents are present
            missing_docs = self._check_required_documents(
                required_docs.required,
                list(document_classifications.values())
            )
            
            if missing_docs:
                error_msg = self._format_missing_documents_error(
                    missing_docs,
                    list(document_classifications.values())
                )
                errors.append(error_msg)
            
            # Step 3: Check for wrong document types uploaded
            wrong_docs = self._check_wrong_documents(
                required_docs.required + required_docs.optional,
                document_classifications
            )
            
            if wrong_docs:
                for wrong_doc in wrong_docs:
                    errors.append(wrong_doc)
            
            # Step 4: Check document quality (readability)
            quality_issues = self._check_document_quality(
                state["document_file_paths"],
                document_classifications
            )
            
            if quality_issues:
                for issue in quality_issues:
                    errors.append(issue)
            
            # Step 5: Check patient name consistency
            if not errors:  # Only if no critical errors so far
                patient_names = self._extract_patient_names(
                    state["document_file_paths"],
                    document_classifications
                )
                
                if len(patient_names) > 1:
                    consistency_check = self._check_patient_name_consistency(patient_names)
                    if not consistency_check["consistent"]:
                        errors.append(
                            f"Patient names are inconsistent across documents: "
                            f"{', '.join(patient_names)}. {consistency_check['explanation']}"
                        )
            
            # Build verification result
            verification_passed = len(errors) == 0
            
            verification_result = DocumentVerificationResult(
                verification_passed=verification_passed,
                errors=errors,
                warnings=warnings,
                missing_documents=missing_docs,
                document_classifications=document_classifications,
                patient_names_found=patient_names if not errors else [],
                patient_name_consistent=len(errors) == 0
            )
            
            # Update state
            state["verification_result"] = verification_result
            state["stop_processing"] = not verification_passed
            
            # Add to trace
            elapsed_time = time.time() - start_time
            trace_entry = {
                "agent": self.agent_name,
                "timestamp": time.time(),
                "duration_seconds": elapsed_time,
                "input": {
                    "claim_id": claim_id,
                    "category": state["claim_category"].value,
                    "num_documents": len(state["document_file_paths"])
                },
                "output": {
                    "verification_passed": verification_passed,
                    "document_classifications": document_classifications,
                    "errors": errors,
                    "warnings": warnings
                },
                "status": "success" if verification_passed else "failed"
            }
            state["trace"].append(trace_entry)
            state["components_executed"].append(self.agent_name)
            
            # Log event
            log_claim_event(
                claim_id=claim_id,
                event_type="DOCUMENT_VERIFIED" if verification_passed else "DOCUMENT_VERIFICATION_FAILED",
                agent_name=self.agent_name,
                details={
                    "verification_passed": verification_passed,
                    "num_errors": len(errors)
                }
            )
            
            logger.info(
                f"[{self.agent_name}] Verification completed for {claim_id}: "
                f"passed={verification_passed}, errors={len(errors)}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error during verification: {e}")
            
            # Add error to state
            state["errors"].append({
                "agent": self.agent_name,
                "error": str(e),
                "timestamp": time.time()
            })
            state["stop_processing"] = True
            
            # Create failed verification result
            state["verification_result"] = DocumentVerificationResult(
                verification_passed=False,
                errors=[f"Verification failed: {str(e)}"],
                warnings=[],
                missing_documents=[],
                document_classifications={},
                patient_names_found=[],
                patient_name_consistent=False
            )
            
            return state
    
    def _classify_documents(
        self,
        document_paths: list[str]
    ) -> Dict[str, DocumentType]:
        """
        Classify each document using OCR + LLM.
        
        Args:
            document_paths: List of file paths to documents
            
        Returns:
            Dict mapping file_path to DocumentType
        """
        classifications = {}
        
        for doc_path in document_paths:
            try:
                # Quick OCR to get text
                text, confidence, _ = self.ocr_service.extract_text(doc_path, preprocess=False)
                
                doc_type = DocumentType.UNKNOWN

                if text and confidence >= 0.3:
                    # Use LLM to classify from text
                    doc_type_str = self.llm_service.classify_document(text[:2000])
                    try:
                        doc_type = DocumentType[doc_type_str]
                    except KeyError:
                        doc_type = DocumentType.UNKNOWN
                else:
                    logger.warning(f"Low quality OCR for {doc_path}")

                # Vision fallback for handwritten / messy docs that text OCR
                # couldn't classify (only when a vision model is configured).
                if doc_type == DocumentType.UNKNOWN and settings.LLM_VISION_MODEL:
                    try:
                        page_images = self.ocr_service.render_document_to_images(doc_path)
                        vision_type_str = self.llm_service.classify_document_vision(page_images)
                        doc_type = DocumentType[vision_type_str]
                        logger.info(
                            f"[{self.agent_name}] Vision classified {Path(doc_path).name} "
                            f"as {doc_type.value}"
                        )
                    except Exception as ve:
                        logger.warning(f"Vision classification failed for {doc_path}: {ve}")
                        doc_type = DocumentType.UNKNOWN

                classifications[doc_path] = doc_type
                logger.debug(f"Classified {Path(doc_path).name} as {doc_type.value}")
                
            except Exception as e:
                logger.error(f"Failed to classify {doc_path}: {e}")
                classifications[doc_path] = DocumentType.UNKNOWN
        
        return classifications
    
    def _check_required_documents(
        self,
        required: list[DocumentType],
        uploaded: list[DocumentType]
    ) -> list[DocumentType]:
        """
        Check if all required documents are present.
        
        Args:
            required: List of required document types
            uploaded: List of uploaded document types
            
        Returns:
            List of missing document types
        """
        missing = []
        for req_type in required:
            if req_type not in uploaded:
                missing.append(req_type)
        return missing
    
    def _check_wrong_documents(
        self,
        allowed: list[DocumentType],
        classifications: Dict[str, DocumentType]
    ) -> list[str]:
        """
        Check if any uploaded documents are of wrong type.
        
        Args:
            allowed: List of allowed document types (required + optional)
            classifications: Document classifications
            
        Returns:
            List of error messages for wrong documents
        """
        errors = []
        
        for file_path, doc_type in classifications.items():
            if doc_type == DocumentType.UNKNOWN:
                errors.append(
                    f"Cannot identify document type for '{Path(file_path).name}'. "
                    f"Please ensure the document is clear and readable."
                )
            elif doc_type not in allowed:
                allowed_str = ", ".join([t.value for t in allowed])
                errors.append(
                    f"Uploaded document '{Path(file_path).name}' is a {doc_type.value}, "
                    f"but this claim type requires: {allowed_str}. "
                    f"Please upload the correct document type."
                )
        
        return errors
    
    def _format_missing_documents_error(
        self,
        missing: list[DocumentType],
        uploaded: list[DocumentType]
    ) -> str:
        """Format a specific error message for missing documents"""
        missing_str = ", ".join([t.value for t in missing])
        uploaded_str = ", ".join([t.value for t in uploaded]) if uploaded else "None"
        
        return (
            f"Missing required documents: {missing_str}. "
            f"You uploaded: {uploaded_str}. "
            f"Please upload all required documents to proceed."
        )
    
    def _check_document_quality(
        self,
        document_paths: list[str],
        classifications: Dict[str, DocumentType]
    ) -> list[str]:
        """
        Check if documents are readable.
        
        Args:
            document_paths: List of document paths
            classifications: Document classifications
            
        Returns:
            List of quality issue errors
        """
        errors = []
        
        for doc_path in document_paths:
            try:
                is_readable, quality_issues = self.ocr_service.check_document_quality(doc_path)
                
                if not is_readable:
                    doc_type = classifications.get(doc_path, DocumentType.UNKNOWN)
                    file_name = Path(doc_path).name
                    
                    errors.append(
                        f"Document '{file_name}' ({doc_type.value}) is not readable. "
                        f"Issues: {', '.join(quality_issues)}. "
                        f"Please upload a clearer image of this document."
                    )
                    
            except Exception as e:
                logger.error(f"Quality check failed for {doc_path}: {e}")
                errors.append(
                    f"Unable to verify quality of '{Path(doc_path).name}'. "
                    f"Please ensure the document is a valid image or PDF."
                )
        
        return errors
    
    def _extract_patient_names(
        self,
        document_paths: list[str],
        classifications: Dict[str, DocumentType]
    ) -> list[str]:
        """
        Extract patient names from all documents.
        
        Uses targeted parsing that ignores form labels (Name, Age, Date, etc.)
        so placeholder/label text isn't mistaken for an actual patient name.
        """
        patient_names = []
        
        for doc_path in document_paths:
            try:
                text, confidence, _ = self.ocr_service.extract_text(doc_path, preprocess=False)
                
                if not text or confidence < 0.4:
                    continue
                
                name = self._parse_patient_name(text)
                if name and name.lower() not in [n.lower() for n in patient_names]:
                    patient_names.append(name)
                        
            except Exception as e:
                logger.error(f"Failed to extract patient name from {doc_path}: {e}")
        
        return patient_names

    def _parse_patient_name(self, text: str) -> str | None:
        """
        Parse a clean patient name from raw OCR text.

        Looks for a "Patient Name:" / "Patient:" / "Name:" field, captures the
        value up to the next field label, and strips out label words and noise.
        Returns None if no plausible name is found.
        """
        import re

        # Words that are field labels, never part of a real name
        label_words = {
            "name", "patient", "date", "age", "gender", "sex", "ref",
            "referring", "doctor", "dr", "bill", "no", "diagnosis", "mrn",
            "id", "uhid", "years", "year", "yrs", "male", "female", "m", "f"
        }
        # Stop the captured value when we hit another field label on the same line
        stop_label = re.compile(
            r'\b(Age|Date|Gender|Sex|Ref|Referring|Doctor|Dr|Bill|Diagnosis|'
            r'MRN|UHID|ID|Phone|Ph|Years?|Yrs)\b',
            re.IGNORECASE
        )

        patterns = [
            r'Patient\s*Name\s*[:\-]\s*([^\n\r]+)',
            r'Patient\s*[:\-]\s*([^\n\r]+)',
            r'\bName\s*[:\-]\s*([^\n\r]+)',
        ]

        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if not m:
                continue

            candidate = m.group(1).strip()

            # Cut at the next field label (e.g. "Deepak Shah  Age: 44")
            stop = stop_label.search(candidate)
            if stop:
                candidate = candidate[:stop.start()].strip()

            # Keep only letters, spaces, and dots (titles like "Dr.")
            candidate = re.sub(r'[^A-Za-z.\s]', ' ', candidate)

            # Drop label/noise tokens
            tokens = [
                t for t in candidate.split()
                if t.lower().strip('.') not in label_words and len(t.strip('.')) > 1
            ]
            candidate = " ".join(tokens).strip()

            if len(candidate) >= 3 and any(c.isalpha() for c in candidate):
                return candidate

        return None
    
    def _check_patient_name_consistency(
        self,
        names: list[str]
    ) -> Dict[str, Any]:
        """
        Check if patient names refer to the same person.

        Strategy (conservative, to avoid false rejections):
        1. Normalize names; if only one unique name remains -> consistent.
        2. If every pair of names shares a common name token -> consistent.
        3. Only when names are clearly disjoint do we consult the LLM, and we
           default to "consistent" if the LLM call fails.
        """
        normalized = []
        for n in names:
            cleaned = " ".join(
                tok for tok in n.lower().replace(".", "").split() if len(tok) > 1
            ).strip()
            if cleaned:
                normalized.append(cleaned)

        unique = set(normalized)
        if len(unique) <= 1:
            return {
                "consistent": True,
                "confidence": 1.0,
                "explanation": "All documents reference the same patient name."
            }

        # Token-overlap heuristic: shared first/last name => same person
        token_sets = [set(n.split()) for n in normalized]
        all_pairs_share = True
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                if token_sets[i].isdisjoint(token_sets[j]):
                    all_pairs_share = False
                    break
            if not all_pairs_share:
                break

        if all_pairs_share:
            return {
                "consistent": True,
                "confidence": 0.9,
                "explanation": "Patient names share common identifiers."
            }

        # Names look genuinely different — confirm with the LLM
        try:
            result = self.llm_service.check_patient_name_consistency(names)
            return {
                "consistent": result.get("same_person", True),
                "confidence": result.get("confidence", 0.5),
                "explanation": result.get("explanation", "")
            }
        except Exception as e:
            logger.error(f"Patient name consistency check failed: {e}")
            # Default to consistent to avoid false rejections
            return {
                "consistent": True,
                "confidence": 0.5,
                "explanation": f"Check failed: {str(e)}"
            }


# Factory function
def create_document_verifier() -> DocumentVerifierAgent:
    """Create DocumentVerifier agent instance"""
    return DocumentVerifierAgent()
