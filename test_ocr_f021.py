#!/usr/bin/env python3
"""
Test OCR extraction for F021.jpg (Ayurveda prescription)
"""
import sys
sys.path.insert(0, 'backend')

from app.services.ocr_service import OCRService

# Initialize OCR
print("Initializing OCR...")
ocr = OCRService()

# Test F021
doc_path = "backend/data/test_documents/prescriptions/F021.jpg"
print(f"\n📄 Testing: {doc_path}")
print("=" * 60)

try:
    full_text, confidence, quality_issues = ocr.extract_text(doc_path)
    
    print(f"\n✅ OCR completed:")
    print(f"   Avg confidence: {confidence:.2f}")
    print(f"   Quality issues: {len(quality_issues)}")
    
    if quality_issues:
        print(f"\n⚠️  Quality issues detected:")
        for issue in quality_issues:
            print(f"   - {issue}")
    
    print(f"\n📝 Extracted text:")
    print("=" * 60)
    print(full_text)
    print("=" * 60)
    
    # Check for key indicators
    text_lower = full_text.lower()
    print(f"\n🔍 Key indicators found:")
    print(f"   'vaidya': {'✅' if 'vaidya' in text_lower else '❌'}")
    print(f"   'ayur': {'✅' if 'ayur' in text_lower else '❌'}")
    print(f"   'krishnan': {'✅' if 'krishnan' in text_lower else '❌'}")
    print(f"   'treatment': {'✅' if 'treatment' in text_lower else '❌'}")
    print(f"   'prescription'/'rx': {'✅' if 'prescription' in text_lower or 'rx' in text_lower else '❌'}")
    print(f"   'diagnosis': {'✅' if 'diagnosis' in text_lower else '❌'}")
    print(f"   'panchakarma': {'✅' if 'panchakarma' in text_lower else '❌'}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
