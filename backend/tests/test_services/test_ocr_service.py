"""
Test OCR Service

Unit tests for OCR service functionality.
Note: These tests use mocks since we don't have actual images in the test suite.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.ocr_service import OCRService, get_ocr_service
from app.models import OCRResult, DocumentType
from app.exceptions import OCRExtractionError


@pytest.fixture
def ocr_service():
    """Fixture to get OCR service instance with mocked PaddleOCR"""
    with patch('paddleocr.PaddleOCR') as mock_paddle:
        # Mock PaddleOCR initialization
        mock_instance = MagicMock()
        mock_paddle.return_value = mock_instance
        
        service = OCRService()
        
        yield service


class TestOCRInitialization:
    """Test OCR service initialization"""
    
    def test_singleton_pattern(self):
        """Test that get_ocr_service returns singleton"""
        with patch('paddleocr.PaddleOCR'):
            service1 = get_ocr_service()
            service2 = get_ocr_service()
            assert service1 is service2


class TestTextExtraction:
    """Test text extraction functionality"""
    
    def test_extract_text_success(self, ocr_service):
        """Test successful text extraction"""
        # Mock OCR result
        mock_ocr_result = [[
            [None, ('Dr. Arun Sharma', 0.95)],
            [None, ('Prescription', 0.92)],
            [None, ('Patient: Rajesh Kumar', 0.88)]
        ]]
        ocr_service._ocr_engine.ocr.return_value = mock_ocr_result
        
        with patch('cv2.imread') as mock_imread:
            mock_imread.return_value = MagicMock()  # Fake image
            
            text, confidence, issues = ocr_service.extract_text('fake_path.jpg', preprocess=False)
            
            assert 'Dr. Arun Sharma' in text
            assert 'Rajesh Kumar' in text
            assert confidence > 0.8
    
    def test_extract_text_no_text_detected(self, ocr_service):
        """Test handling when no text is detected"""
        ocr_service._ocr_engine.ocr.return_value = [[]]
        
        with patch('cv2.imread') as mock_imread:
            mock_imread.return_value = MagicMock()
            
            text, confidence, issues = ocr_service.extract_text('fake_path.jpg', preprocess=False)
            
            assert text == ""
            assert confidence == 0.0
            assert "No text detected" in issues
    
    def test_extract_text_low_confidence(self, ocr_service):
        """Test extraction with low confidence"""
        mock_ocr_result = [[
            [None, ('Some text', 0.3)],
            [None, ('More text', 0.25)]
        ]]
        ocr_service._ocr_engine.ocr.return_value = mock_ocr_result
        
        with patch('cv2.imread') as mock_imread:
            mock_imread.return_value = MagicMock()
            
            text, confidence, issues = ocr_service.extract_text('fake_path.jpg', preprocess=False)
            
            assert confidence < 0.5
            assert len(issues) > 0


class TestQualityAssessment:
    """Test quality assessment functionality"""
    
    def test_assess_quality_good(self, ocr_service):
        """Test quality assessment for good OCR"""
        text = "Dr. Arun Sharma\nPrescription for Rajesh Kumar\nDiagnosis: Viral Fever"
        issues = ocr_service._assess_quality(text, 0.92, [0.95, 0.92, 0.88])
        
        assert len(issues) == 0 or all('low' not in issue.lower() for issue in issues)
    
    def test_assess_quality_low_confidence(self, ocr_service):
        """Test quality assessment for low confidence"""
        text = "Some text"
        issues = ocr_service._assess_quality(text, 0.3, [0.3, 0.25, 0.35])
        
        assert any('confidence' in issue.lower() for issue in issues)
    
    def test_assess_quality_short_text(self, ocr_service):
        """Test quality assessment for very short text"""
        text = "Hi"
        issues = ocr_service._assess_quality(text, 0.9, [0.9])
        
        assert any('little text' in issue.lower() for issue in issues)


class TestDocumentQualityCheck:
    """Test document quality check"""
    
    def test_quality_check_readable(self, ocr_service):
        """Test quality check for readable document"""
        mock_ocr_result = [[
            [None, ('Dr. Arun Sharma, MBBS', 0.95)],
            [None, ('City Medical Centre', 0.93)],
            [None, ('Patient: Rajesh Kumar, Age: 39, Male', 0.90)]
        ]]
        ocr_service._ocr_engine.ocr.return_value = mock_ocr_result
        
        with patch('cv2.imread') as mock_imread:
            mock_imread.return_value = MagicMock()
            
            is_readable, issues = ocr_service.check_document_quality('fake_path.jpg')
            
            assert is_readable is True
    
    def test_quality_check_unreadable(self, ocr_service):
        """Test quality check for unreadable document"""
        mock_ocr_result = [[
            [None, ('###', 0.2)],
            [None, ('|||', 0.15)]
        ]]
        ocr_service._ocr_engine.ocr.return_value = mock_ocr_result
        
        with patch('cv2.imread') as mock_imread:
            mock_imread.return_value = MagicMock()
            
            is_readable, issues = ocr_service.check_document_quality('fake_path.jpg')
            
            assert is_readable is False
            assert len(issues) > 0


class TestExtractFromDocument:
    """Test complete extraction workflow"""
    
    def test_extract_from_document_success(self, ocr_service):
        """Test complete extraction workflow"""
        mock_ocr_result = [[
            [None, ('Dr. Arun Sharma', 0.95)],
            [None, ('Prescription for Rajesh Kumar', 0.92)],
            [None, ('Diagnosis: Viral Fever', 0.90)]
        ]]
        ocr_service._ocr_engine.ocr.return_value = mock_ocr_result
        
        with patch('cv2.imread') as mock_imread:
            mock_imread.return_value = MagicMock()
            
            result = ocr_service.extract_from_document(
                document_id='doc_123',
                image_path='fake_path.jpg',
                document_type=DocumentType.PRESCRIPTION
            )
            
            assert isinstance(result, OCRResult)
            assert result.document_id == 'doc_123'
            assert 'Dr. Arun Sharma' in result.raw_text
            assert result.confidence > 0.8
            assert result.is_readable is True
    
    def test_extract_from_document_low_quality(self, ocr_service):
        """Test extraction from low quality document"""
        mock_ocr_result = [[
            [None, ('###', 0.2)]
        ]]
        ocr_service._ocr_engine.ocr.return_value = mock_ocr_result
        
        with patch('cv2.imread') as mock_imread:
            mock_imread.return_value = MagicMock()
            
            result = ocr_service.extract_from_document(
                document_id='doc_123',
                image_path='fake_path.jpg'
            )
            
            assert result.is_readable is False
            assert len(result.quality_issues) > 0


class TestImagePreprocessing:
    """Test image preprocessing"""
    
    def test_preprocess_image_success(self, ocr_service):
        """Test image preprocessing"""
        with patch('cv2.imread') as mock_imread, \
             patch('cv2.cvtColor') as mock_cvt, \
             patch('cv2.adaptiveThreshold') as mock_threshold, \
             patch('cv2.fastNlMeansDenoising') as mock_denoise:
            
            mock_imread.return_value = MagicMock()
            mock_cvt.return_value = MagicMock()
            mock_threshold.return_value = MagicMock()
            mock_denoise.return_value = MagicMock()
            
            result = ocr_service.preprocess_image('fake_path.jpg')
            
            assert result is not None
            mock_imread.assert_called_once()
            mock_cvt.assert_called_once()
            mock_threshold.assert_called_once()
            mock_denoise.assert_called_once()
    
    def test_preprocess_image_failure_fallback(self, ocr_service):
        """Test preprocessing fallback on error"""
        with patch('cv2.imread') as mock_imread, \
             patch('cv2.cvtColor', side_effect=Exception("Processing error")):
            
            mock_imread.return_value = MagicMock()
            
            result = ocr_service.preprocess_image('fake_path.jpg')
            
            # Should fallback to original image
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
