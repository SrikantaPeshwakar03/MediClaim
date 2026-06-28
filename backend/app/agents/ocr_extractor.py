"""
OCRExtractor Agent

Second agent in the claims processing pipeline.
Extracts structured data from verified documents using OCR + LLM.
"""

import time
from typing import Dict, Any, List
from pathlib import Path

from ..models import (
    ClaimState,
    DocumentType,
    OCRResult
)
from ..config import settings
from ..services import get_ocr_service, get_llm_service
from ..services.llm_prompts import get_extraction_prompt
from ..exceptions import OCRExtractionError
from ..loggers import logger, log_claim_event


class OCRExtractorAgent:
    """
    Agent responsible for extracting structured data from documents.
    
    Process:
    1. Run OCR on each document
    2. Use LLM to extract structured fields
    3. Aggregate data from all documents
    4. Handle extraction failures gracefully
    """
    
    def __init__(self):
        self.ocr_service = get_ocr_service()
        self.llm_service = get_llm_service()
        self.agent_name = "OCRExtractor"
        logger.info(f"[{self.agent_name}] Agent initialized")
    
    def extract(self, state: ClaimState) -> ClaimState:
        """
        Extract structured data from documents.
        
        Args:
            state: Current claim state
            
        Returns:
            Updated claim state with extracted data
        """
        claim_id = state["claim_id"]
        logger.info(f"[{self.agent_name}] Starting extraction for claim: {claim_id}")
        
        start_time = time.time()
        ocr_results = []
        extraction_errors = []
        extracted_data = {}
        total_confidence = 0.0
        successful_extractions = 0
        all_integrity_flags = []

        # Resilience test (TC011): deliberately fail this component to exercise
        # the graceful-degradation path. The pipeline must continue and the
        # failure must be visible in the trace with reduced confidence.
        if state.get("simulate_component_failure"):
            logger.warning(
                f"[{self.agent_name}] Simulated component failure triggered for {claim_id} "
                f"(graceful-degradation test). Skipping extraction."
            )
            state["errors"].append({
                "agent": self.agent_name,
                "error": "Simulated component failure (graceful-degradation test)",
                "timestamp": time.time()
            })
            state["components_failed"].append(self.agent_name)
            state["ocr_results"] = []
            state["extracted_data"] = {}
            state["extraction_confidence"] = 0.0
            state["trace"].append({
                "agent": self.agent_name,
                "timestamp": time.time(),
                "status": "failed",
                "error": "Simulated component failure — extraction skipped (graceful degradation)"
            })
            log_claim_event(
                claim_id=claim_id,
                event_type="OCR_EXTRACTION_SKIPPED",
                agent_name=self.agent_name,
                details={"reason": "simulated_component_failure"}
            )
            return state
        
        try:
            # Get document classifications from verification
            verification_result = state.get("verification_result")
            if not verification_result:
                raise OCRExtractionError("No verification result found")
            
            document_classifications = verification_result.document_classifications
            
            # Extract from each document
            for doc_path, doc_type in document_classifications.items():
                try:
                    logger.info(f"[{self.agent_name}] Extracting from {Path(doc_path).name} ({doc_type.value})")
                    
                    # Step 1: OCR extraction (text + quality assessment)
                    ocr_result = self.ocr_service.extract_from_document(
                        document_id=Path(doc_path).stem,
                        image_path=doc_path,
                        document_type=doc_type
                    )
                    
                    # Step 2: Structured extraction.
                    # Prefer the vision model when configured (handles handwritten
                    # and messy documents better); fall back to text extraction.
                    structured_data = None
                    used_vision = False

                    if settings.LLM_VISION_MODEL and doc_type != DocumentType.UNKNOWN:
                        try:
                            structured_data = self._extract_structured_fields_vision(doc_path, doc_type)
                            used_vision = bool(structured_data)
                        except Exception as ve:
                            logger.warning(
                                f"[{self.agent_name}] Vision extraction failed for "
                                f"{Path(doc_path).name}, falling back to text OCR: {ve}"
                            )

                    if not structured_data and ocr_result.is_readable and doc_type != DocumentType.UNKNOWN:
                        structured_data = self._extract_structured_fields(
                            ocr_result.raw_text,
                            doc_type
                        )

                    if structured_data:
                        # Separate any document-integrity flags (used by fraud detection)
                        integrity_flags = structured_data.pop("integrity_flags", None) or []
                        if integrity_flags:
                            ocr_result.quality_issues = list(ocr_result.quality_issues or []) + [
                                f"integrity:{flag}" for flag in integrity_flags
                            ]
                            all_integrity_flags.extend(integrity_flags)

                        ocr_result.extracted_data = structured_data
                        extracted_data[doc_type.value] = structured_data

                        # Vision can read documents PaddleOCR marks unreadable, so
                        # use a reasonable confidence floor when vision succeeded.
                        doc_confidence = ocr_result.confidence
                        if used_vision and doc_confidence < 0.85:
                            doc_confidence = 0.85
                        total_confidence += doc_confidence
                        successful_extractions += 1
                        logger.info(
                            f"[{self.agent_name}] Successfully extracted from {doc_type.value} "
                            f"({'vision' if used_vision else 'text'})"
                        )
                    else:
                        extraction_errors.append(
                            f"Failed to extract structured data from {Path(doc_path).name}"
                        )
                        logger.warning(f"[{self.agent_name}] No structured data extracted from {doc_type.value}")
                    
                    ocr_results.append(ocr_result)
                    
                except Exception as e:
                    logger.error(f"[{self.agent_name}] Extraction failed for {doc_path}: {e}")
                    extraction_errors.append(
                        f"Extraction error for {Path(doc_path).name}: {str(e)}"
                    )
                    
                    # Create failed OCR result
                    ocr_results.append(OCRResult(
                        document_id=Path(doc_path).stem,
                        raw_text="",
                        confidence=0.0,
                        is_readable=False,
                        quality_issues=[str(e)],
                        extracted_data={},
                        field_confidence={},
                        extraction_errors=[str(e)]
                    ))
            
            # Calculate overall extraction confidence
            avg_confidence = (total_confidence / successful_extractions) if successful_extractions > 0 else 0.0
            
            # Consolidate extracted data
            consolidated_data = self._consolidate_extracted_data(extracted_data, state)

            # Surface document-integrity flags (from vision extraction) for fraud detection
            if all_integrity_flags:
                consolidated_data["integrity_flags"] = sorted(set(all_integrity_flags))

            # Validate doctor registration number format (flag, never fail) per
            # the formats in sample_documents_guide.md
            reg_number = consolidated_data.get("doctor_registration")
            if reg_number:
                from ..services.medical_validators import validate_doctor_registration
                is_valid, note = validate_doctor_registration(reg_number)
                consolidated_data["doctor_registration_valid"] = is_valid
                if not is_valid:
                    logger.warning(f"[{self.agent_name}] {note}")
                    state["warnings"].append({
                        "agent": self.agent_name,
                        "message": "Doctor registration number could not be validated",
                        "details": note
                    })
            
            # Update state
            state["ocr_results"] = ocr_results
            state["extracted_data"] = consolidated_data
            state["extraction_confidence"] = avg_confidence
            state["extraction_errors"].extend(extraction_errors)
            
            # If all extractions failed, mark component as failed
            if successful_extractions == 0 and len(document_classifications) > 0:
                state["components_failed"].append(self.agent_name)
                logger.warning(f"[{self.agent_name}] All extractions failed, marking component as failed")
            
            # Add to trace
            elapsed_time = time.time() - start_time
            trace_entry = {
                "agent": self.agent_name,
                "timestamp": time.time(),
                "duration_seconds": elapsed_time,
                "input": {
                    "claim_id": claim_id,
                    "num_documents": len(document_classifications)
                },
                "output": {
                    "num_successful": successful_extractions,
                    "avg_confidence": round(avg_confidence, 2),
                    "num_errors": len(extraction_errors),
                    "extracted_fields": list(consolidated_data.keys())
                },
                "errors": extraction_errors if extraction_errors else None,
                "status": "success" if successful_extractions > 0 else "partial_failure"
            }
            state["trace"].append(trace_entry)
            state["components_executed"].append(self.agent_name)
            
            # Add to warnings if some extractions failed
            if extraction_errors:
                state["warnings"].append({
                    "agent": self.agent_name,
                    "message": f"{len(extraction_errors)} document(s) had extraction issues",
                    "details": extraction_errors
                })
            
            # Log event
            log_claim_event(
                claim_id=claim_id,
                event_type="OCR_EXTRACTION_COMPLETED",
                agent_name=self.agent_name,
                details={
                    "successful_extractions": successful_extractions,
                    "avg_confidence": avg_confidence,
                    "num_errors": len(extraction_errors)
                }
            )
            
            logger.info(
                f"[{self.agent_name}] Extraction completed for {claim_id}: "
                f"successful={successful_extractions}/{len(document_classifications)}, "
                f"confidence={avg_confidence:.2f}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Fatal error during extraction: {e}")
            
            # Mark component as failed but continue pipeline (graceful degradation)
            state["errors"].append({
                "agent": self.agent_name,
                "error": str(e),
                "timestamp": time.time()
            })
            state["components_failed"].append(self.agent_name)
            
            # Set defaults
            state["ocr_results"] = []
            state["extracted_data"] = {}
            state["extraction_confidence"] = 0.0
            
            # Add trace entry
            state["trace"].append({
                "agent": self.agent_name,
                "timestamp": time.time(),
                "status": "failed",
                "error": str(e)
            })
            
            logger.warning(f"[{self.agent_name}] Continuing pipeline despite extraction failure")
            
            return state
    
    def _extract_structured_fields(
        self,
        raw_text: str,
        document_type: DocumentType
    ) -> Dict[str, Any]:
        """
        Extract structured fields from raw OCR text using LLM.
        
        Args:
            raw_text: Raw OCR text
            document_type: Type of document
            
        Returns:
            Dictionary of extracted fields
        """
        try:
            system_prompt, user_prompt = get_extraction_prompt(document_type, raw_text)
            
            response = self.llm_service.call_llm(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
                json_mode=True,
                max_tokens=1500
            )
            
            # Parse JSON response
            structured_data = self.llm_service._parse_json_response(response)
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Structured field extraction failed: {e}")
            return {}

    def _extract_structured_fields_vision(
        self,
        image_path: str,
        document_type: DocumentType
    ) -> Dict[str, Any]:
        """
        Extract structured fields directly from the document IMAGE using a
        vision-capable LLM. Better for handwritten / messy documents and also
        reports visual integrity issues via `integrity_flags`.
        """
        try:
            from ..services.llm_prompts import get_vision_extraction_prompt

            system_prompt, user_prompt = get_vision_extraction_prompt(document_type)

            # Render the document (image or multi-page PDF) to page images
            page_images = self.ocr_service.render_document_to_images(image_path)
            if not page_images:
                return {}

            response = self.llm_service.call_llm_vision(
                images=page_images,
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
                json_mode=True,
                max_tokens=1500,
            )

            return self.llm_service._parse_json_response(response)

        except Exception as e:
            logger.error(f"Vision field extraction failed: {e}")
            return {}
    
    def _consolidate_extracted_data(
        self,
        extracted_data: Dict[str, Dict[str, Any]],
        state: ClaimState
    ) -> Dict[str, Any]:
        """
        Consolidate extracted data from all documents into a unified structure.
        
        Args:
            extracted_data: Dict mapping document_type to extracted fields
            state: Current claim state
            
        Returns:
            Consolidated data dictionary
        """
        consolidated = {
            "patient_name": None,
            "patient_age": None,
            "patient_gender": None,
            "doctor_name": None,
            "doctor_registration": None,
            "hospital_name": None,
            "treatment_date": None,
            "diagnosis": None,
            "medicines": [],
            "tests_ordered": [],
            "line_items": [],
            "total_amount": state["claimed_amount"],
            "bill_details": {}
        }
        
        # Extract patient information (prefer prescription, then hospital bill)
        for doc_type in ["PRESCRIPTION", "HOSPITAL_BILL", "LAB_REPORT", "PHARMACY_BILL"]:
            if doc_type in extracted_data:
                data = extracted_data[doc_type]
                
                # Patient info
                if not consolidated["patient_name"] and data.get("patient_name"):
                    consolidated["patient_name"] = data["patient_name"]
                if not consolidated["patient_age"] and data.get("patient_age"):
                    consolidated["patient_age"] = data["patient_age"]
                if not consolidated["patient_gender"] and data.get("patient_gender"):
                    consolidated["patient_gender"] = data["patient_gender"]
                
                # Doctor info (from prescription)
                if doc_type == "PRESCRIPTION":
                    if data.get("doctor_name"):
                        consolidated["doctor_name"] = data["doctor_name"]
                    if data.get("doctor_registration"):
                        consolidated["doctor_registration"] = data["doctor_registration"]
                    if data.get("diagnosis"):
                        consolidated["diagnosis"] = data["diagnosis"]
                    if data.get("medicines"):
                        consolidated["medicines"].extend(data["medicines"])
                    if data.get("tests_ordered"):
                        consolidated["tests_ordered"].extend(data["tests_ordered"])
                
                # Hospital/clinic info
                if doc_type == "HOSPITAL_BILL":
                    if data.get("hospital_name"):
                        consolidated["hospital_name"] = data["hospital_name"]
                    if data.get("line_items"):
                        consolidated["line_items"].extend(data["line_items"])
                    if data.get("total_amount"):
                        consolidated["total_amount"] = data["total_amount"]
                    if data.get("bill_date"):
                        consolidated["treatment_date"] = data["bill_date"]
                    
                    # Store full bill details
                    consolidated["bill_details"]["hospital_bill"] = data
                
                # Pharmacy info
                if doc_type == "PHARMACY_BILL":
                    if data.get("medicines"):
                        consolidated["medicines"].extend([
                            m.get("medicine", "") for m in data["medicines"]
                        ])
                    if data.get("net_amount"):
                        consolidated["total_amount"] = data["net_amount"]
                    
                    consolidated["bill_details"]["pharmacy_bill"] = data
                
                # Lab report info
                if doc_type == "LAB_REPORT":
                    consolidated["bill_details"]["lab_report"] = data
        
        # Use claim-level hospital name if not found in documents
        if not consolidated["hospital_name"] and state.get("hospital_name"):
            consolidated["hospital_name"] = state["hospital_name"]
        
        # Use treatment date from claim if not found
        if not consolidated["treatment_date"]:
            consolidated["treatment_date"] = state["treatment_date"].isoformat()
        
        return consolidated


# Factory function
def create_ocr_extractor() -> OCRExtractorAgent:
    """Create OCRExtractor agent instance"""
    return OCRExtractorAgent()
