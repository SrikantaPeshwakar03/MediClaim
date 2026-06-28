"""
OCR Service

Extracts text from medical documents using RapidOCR (PP-OCR models running on
ONNXRuntime) and structures it using an LLM. Handles quality checks,
preprocessing, and field extraction.

RapidOCR is used instead of PaddleOCR because it runs the same detection and
recognition models on ONNXRuntime, with a tiny bundled model set and a much
lower memory footprint. This avoids the OOM kills that the heavyweight
``paddlepaddle`` runtime caused on small cloud instances.
"""

import cv2
import numpy as np
import gc
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from PIL import Image

# Keep OpenCV from spawning many threads (each costs memory); important on
# small cloud instances to avoid OOM kills.
try:
    cv2.setNumThreads(1)
except Exception:
    pass

from ..config import settings
from ..models import (
    OCRResult,
    DocumentType,
    PrescriptionData,
    HospitalBillData,
    LabReportData,
    PharmacyBillData
)
from ..exceptions import OCRExtractionError
from ..loggers import logger


class OCRService:
    """
    Service for OCR extraction from medical documents.

    Uses RapidOCR (PP-OCR models on ONNXRuntime) for text extraction and
    quality assessment.
    """
    
    def __init__(self):
        self._ocr_engine = None
        self._initialize_ocr()
    
    def _initialize_ocr(self):
        """Initialize the RapidOCR engine (ONNXRuntime backend).

        RapidOCR ships the PP-OCR detection/recognition/classification models and
        runs them on ONNXRuntime instead of the heavyweight ``paddlepaddle``
        runtime. The models are small and peak RAM stays low — the key reason for
        switching away from paddlepaddle on memory-constrained hosts.

        The unified ``rapidocr`` package supports Python 3.13 (unlike
        ``rapidocr_onnxruntime``, which is capped at <3.13) but requires the
        ``onnxruntime`` engine to be installed separately.
        """
        try:
            from rapidocr import RapidOCR

            self._ocr_engine = RapidOCR()

            logger.info("RapidOCR (ONNXRuntime) initialized successfully")

        except ImportError as e:
            logger.error(f"RapidOCR not installed: {e}")
            raise OCRExtractionError(
                "RapidOCR not available. Please install 'rapidocr' and 'onnxruntime'.",
                details={"error": str(e)}
            )
        except Exception as e:
            logger.error(f"Failed to initialize RapidOCR: {e}")
            raise OCRExtractionError(
                f"OCR initialization failed: {e}",
                details={"error": str(e)}
            )
    
    def _is_pdf(self, file_path: str) -> bool:
        """Return True if the file is a PDF (by extension or magic bytes)."""
        if str(file_path).lower().endswith(".pdf"):
            return True
        try:
            with open(file_path, "rb") as f:
                return f.read(5) == b"%PDF-"
        except Exception:
            return False

    def _pdf_to_images(self, pdf_path: str) -> List[np.ndarray]:
        """
        Convert each page of a PDF into an OpenCV (BGR) image array.

        Uses pypdfium2 (no system dependencies). Returns one image per page so
        multi-page bills can be processed page-by-page and aggregated.
        """
        try:
            import pypdfium2 as pdfium
        except ImportError:
            raise OCRExtractionError(
                "PDF support requires pypdfium2. Please install it (pip install pypdfium2)."
            )

        images: List[np.ndarray] = []
        pdf = pdfium.PdfDocument(pdf_path)
        try:
            for page in pdf:
                # Render at ~200 DPI (scale 200/72) for good OCR quality
                bitmap = page.render(scale=200 / 72)
                pil_image = bitmap.to_pil().convert("RGB")
                # PIL (RGB) -> OpenCV (BGR)
                img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                images.append(img)
        finally:
            pdf.close()

        return images

    def _downscale_if_large(self, img: np.ndarray) -> np.ndarray:
        """Downscale an image so its largest side <= OCR_MAX_IMAGE_DIM.

        Large source images are the main driver of OCR memory spikes. Capping
        the dimension keeps peak RAM bounded without materially hurting OCR
        accuracy for documents.
        """
        max_dim = settings.OCR_MAX_IMAGE_DIM
        if max_dim and img is not None:
            h, w = img.shape[:2]
            longest = max(h, w)
            if longest > max_dim:
                scale = max_dim / float(longest)
                new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
                img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
        return img

    def _read_image(self, image_path: str) -> np.ndarray:
        """Read an image OR the first page of a PDF as an OpenCV image."""
        if self._is_pdf(image_path):
            pages = self._pdf_to_images(image_path)
            if not pages:
                raise OCRExtractionError(f"PDF has no pages: {image_path}")
            return self._downscale_if_large(pages[0])
        img = cv2.imread(image_path)
        if img is None:
            raise OCRExtractionError(f"Failed to read image: {image_path}")
        return self._downscale_if_large(img)

    def render_document_to_images(self, file_path: str) -> List[bytes]:
        """
        Render a document to a list of PNG image byte strings — one per page.

        Works for both images (1 entry) and multi-page PDFs (N entries). Used to
        feed vision-capable LLMs, which cannot read raw PDF bytes directly.
        """
        if self._is_pdf(file_path):
            arrays = self._pdf_to_images(file_path)
        else:
            arrays = [self._read_image(file_path)]

        images: List[bytes] = []
        for arr in arrays:
            ok, buf = cv2.imencode(".png", arr)
            if ok:
                images.append(buf.tobytes())
        return images

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Read image (handles PDF first page too)
            img = self._read_image(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply adaptive thresholding to handle varying lighting
            processed = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(processed, None, 10, 7, 21)
            
            return denoised
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {e}")
            # Return original if preprocessing fails
            return self._read_image(image_path)
    
    def extract_text(
        self,
        image_path: str,
        preprocess: bool = True
    ) -> Tuple[str, float, List[str]]:
        """
        Extract text from image using RapidOCR.
        
        Args:
            image_path: Path to image file
            preprocess: Whether to preprocess image
            
        Returns:
            Tuple of (extracted_text, confidence, quality_issues)
        """
        if self._ocr_engine is None:
            raise OCRExtractionError("OCR engine not initialized")
        
        try:
            # Build the list of page images to OCR.
            # Multi-page PDFs are processed page-by-page and aggregated
            # (per sample_documents_guide.md).
            if self._is_pdf(image_path):
                page_images = self._pdf_to_images(image_path)
                logger.info(f"PDF detected: {len(page_images)} page(s) to process")
            else:
                if preprocess:
                    page_images = [self.preprocess_image(image_path)]
                else:
                    page_images = [self._read_image(image_path)]

            all_lines: List[str] = []
            all_confidences: List[float] = []

            for page_num, img in enumerate(page_images, start=1):
                img = self._downscale_if_large(img)
                # RapidOCR is callable and returns a RapidOCROutput whose `txts`
                # and `scores` are parallel sequences (both None when nothing is
                # detected).
                out = self._ocr_engine(img)
                txts = getattr(out, "txts", None) if out is not None else None
                scores = getattr(out, "scores", None) if out is not None else None
                if txts:
                    for i, txt in enumerate(txts):
                        all_lines.append(txt)
                        conf = scores[i] if (scores is not None and i < len(scores)) else 0.0
                        all_confidences.append(float(conf))
                # Release per-page buffers promptly to keep peak memory low.
                del img, out
                gc.collect()

            if not all_lines:
                logger.warning(f"No text detected in document: {image_path}")
                return "", 0.0, ["No text detected"]

            full_text = "\n".join(all_lines)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            quality_issues = self._assess_quality(full_text, avg_confidence, all_confidences)

            logger.info(
                f"OCR completed: {len(all_lines)} lines across "
                f"{len(page_images)} page(s), avg confidence: {avg_confidence:.2f}"
            )

            return full_text, avg_confidence, quality_issues
            
        except OCRExtractionError:
            raise
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise OCRExtractionError(
                f"Failed to extract text: {e}",
                document_id=image_path
            )
    
    def _assess_quality(
        self,
        text: str,
        avg_confidence: float,
        confidences: List[float]
    ) -> List[str]:
        """
        Assess OCR quality and identify issues.
        
        Args:
            text: Extracted text
            avg_confidence: Average confidence score
            confidences: List of confidence scores per line
            
        Returns:
            List of quality issue descriptions
        """
        issues = []
        
        # Check confidence threshold
        if avg_confidence < settings.OCR_CONFIDENCE_THRESHOLD:
            issues.append(f"Low overall confidence: {avg_confidence:.2f}")
        
        # Check for very low confidence lines
        low_conf_lines = sum(1 for c in confidences if c < 0.3)
        if low_conf_lines > len(confidences) * 0.3:  # More than 30% low confidence
            issues.append(f"Many low-confidence lines: {low_conf_lines}/{len(confidences)}")
        
        # Check text length
        if len(text.strip()) < 50:
            issues.append("Very little text extracted")
        
        # Check for common OCR artifacts
        if text.count('|||') > 3 or text.count('___') > 3:
            issues.append("Possible OCR artifacts detected")
        
        return issues
    
    def check_document_quality(self, image_path: str) -> Tuple[bool, List[str]]:
        """
        Quick quality check without full extraction.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (is_readable, quality_issues)
        """
        try:
            text, confidence, issues = self.extract_text(image_path, preprocess=False)
            
            is_readable = (
                confidence >= settings.OCR_CONFIDENCE_THRESHOLD and
                len(text.strip()) >= 50 and
                len(issues) < 2
            )
            
            return is_readable, issues
            
        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            return False, [f"Quality check error: {str(e)}"]
    
    def extract_from_document(
        self,
        document_id: str,
        image_path: str,
        document_type: Optional[DocumentType] = None
    ) -> OCRResult:
        """
        Complete OCR extraction workflow for a document.
        
        Args:
            document_id: Document identifier
            image_path: Path to image file
            document_type: Type of document (if known)
            
        Returns:
            OCRResult with extracted text and quality assessment
        """
        logger.info(f"Starting OCR extraction for document: {document_id}")
        
        try:
            # Extract text
            raw_text, confidence, quality_issues = self.extract_text(image_path)
            
            # Determine readability
            is_readable = (
                confidence >= settings.OCR_CONFIDENCE_THRESHOLD and
                len(raw_text.strip()) >= 50
            )
            
            # Create OCR result
            ocr_result = OCRResult(
                document_id=document_id,
                raw_text=raw_text,
                confidence=confidence,
                is_readable=is_readable,
                quality_issues=quality_issues,
                extracted_data={},  # Will be populated by LLM extraction
                field_confidence={},
                extraction_errors=[]
            )
            
            logger.info(
                f"OCR extraction completed for {document_id}: "
                f"readable={is_readable}, confidence={confidence:.2f}"
            )
            
            return ocr_result
            
        except OCRExtractionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OCR extraction: {e}")
            raise OCRExtractionError(
                f"OCR extraction failed unexpectedly: {e}",
                document_id=document_id
            )


# Singleton instance
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get or create OCRService singleton"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


# === Helper Functions for Structured Extraction ===

def parse_prescription_from_text(text: str) -> PrescriptionData:
    """
    Parse prescription data from OCR text.
    This is a simple parser - will be enhanced with LLM in next batch.
    
    Args:
        text: Raw OCR text
        
    Returns:
        PrescriptionData object
    """
    import re
    
    data = PrescriptionData()
    
    # Simple regex patterns for common fields
    # In production, this will be replaced with LLM-based extraction
    
    # Extract doctor name (lines starting with Dr.)
    dr_match = re.search(r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text, re.IGNORECASE)
    if dr_match:
        data.doctor_name = dr_match.group(0)
    
    # Extract registration number
    reg_match = re.search(r'Reg\.?\s*No\.?:\s*([A-Z]{2}/\d+/\d{4})', text, re.IGNORECASE)
    if reg_match:
        data.doctor_registration = reg_match.group(1)
    
    # Extract patient name
    patient_match = re.search(r'Patient:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text, re.IGNORECASE)
    if patient_match:
        data.patient_name = patient_match.group(1)
    
    # Extract diagnosis
    diag_match = re.search(r'Diagnosis:?\s*([A-Za-z\s,]+)', text, re.IGNORECASE)
    if diag_match:
        data.diagnosis = diag_match.group(1).strip()
    
    return data


def parse_hospital_bill_from_text(text: str) -> HospitalBillData:
    """
    Parse hospital bill data from OCR text.
    Simple parser - will be enhanced with LLM.
    
    Args:
        text: Raw OCR text
        
    Returns:
        HospitalBillData object
    """
    import re
    
    data = HospitalBillData()
    
    # Extract hospital name (usually at top)
    lines = text.split('\n')
    if lines:
        data.hospital_name = lines[0].strip()
    
    # Extract patient name
    patient_match = re.search(r'Patient:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text, re.IGNORECASE)
    if patient_match:
        data.patient_name = patient_match.group(1)
    
    # Extract total amount
    total_match = re.search(r'Total:?\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d{2})?)', text, re.IGNORECASE)
    if total_match:
        amount_str = total_match.group(1).replace(',', '')
        try:
            data.total_amount = float(amount_str)
        except ValueError:
            pass
    
    return data


def parse_lab_report_from_text(text: str) -> LabReportData:
    """
    Parse lab report data from OCR text.
    Simple parser - will be enhanced with LLM.
    
    Args:
        text: Raw OCR text
        
    Returns:
        LabReportData object
    """
    import re
    
    data = LabReportData()
    
    # Extract lab name
    lines = text.split('\n')
    if lines:
        data.lab_name = lines[0].strip()
    
    # Extract patient name
    patient_match = re.search(r'Patient:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text, re.IGNORECASE)
    if patient_match:
        data.patient_name = patient_match.group(1)
    
    # Check for NABL accreditation
    if 'NABL' in text.upper():
        data.nabl_accredited = True
    
    return data


def parse_pharmacy_bill_from_text(text: str) -> PharmacyBillData:
    """
    Parse pharmacy bill data from OCR text.
    Simple parser - will be enhanced with LLM.
    
    Args:
        text: Raw OCR text
        
    Returns:
        PharmacyBillData object
    """
    import re
    
    data = PharmacyBillData()
    
    # Extract pharmacy name
    lines = text.split('\n')
    if lines:
        data.pharmacy_name = lines[0].strip()
    
    # Extract patient name
    patient_match = re.search(r'Patient:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text, re.IGNORECASE)
    if patient_match:
        data.patient_name = patient_match.group(1)
    
    # Extract net amount
    net_match = re.search(r'Net:?\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d{2})?)', text, re.IGNORECASE)
    if net_match:
        amount_str = net_match.group(1).replace(',', '')
        try:
            data.net_amount = float(amount_str)
        except ValueError:
            pass
    
    return data
