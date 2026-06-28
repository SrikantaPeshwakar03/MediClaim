"""
Test Document Upload Script

Quick script to test uploading the generated mock documents to the API.
"""

import requests
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000/api/v1/claims/submit"
DOCS_DIR = Path(__file__).parent.parent.parent / "test_documents"

# Test Case 004 - Clean Consultation
def test_tc004():
    """Test TC004: Clean consultation approval"""
    print("\n🧪 Testing TC004: Clean Consultation (Expected: APPROVED)")
    
    # Prepare files
    files = [
        ("files", open(DOCS_DIR / "tc004_prescription.jpg", "rb")),
        ("files", open(DOCS_DIR / "tc004_hospital_bill.jpg", "rb")),
    ]
    
    # Prepare form data
    data = {
        "member_id": "EMP001",
        "policy_id": "PLUM_GHI_2024",
        "claim_category": "CONSULTATION",
        "treatment_date": "2024-11-08",
        "claimed_amount": "1500",
        "hospital_name": "City Medical Centre"
    }
    
    try:
        response = requests.post(API_URL, files=files, data=data)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ Claim submitted successfully!")
        print(f"   Claim ID: {result['claim_id']}")
        print(f"   Status: {result['status']}")
        print(f"   Message: {result['message']}")
        
        return result['claim_id']
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        return None
    finally:
        # Close file handles
        for _, file in files:
            file.close()


# Test Case 006 - Dental Partial
def test_tc006():
    """Test TC006: Dental partial approval"""
    print("\n🧪 Testing TC006: Dental Partial (Expected: PARTIAL)")
    
    files = [
        ("files", open(DOCS_DIR / "tc006_prescription.jpg", "rb")),
        ("files", open(DOCS_DIR / "tc006_dental_bill.jpg", "rb")),
    ]
    
    data = {
        "member_id": "EMP002",
        "policy_id": "PLUM_GHI_2024",
        "claim_category": "DENTAL",
        "treatment_date": "2024-10-15",
        "claimed_amount": "12000",
        "hospital_name": "Smile Dental Clinic"
    }
    
    try:
        response = requests.post(API_URL, files=files, data=data)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ Claim submitted successfully!")
        print(f"   Claim ID: {result['claim_id']}")
        print(f"   Status: {result['status']}")
        
        return result['claim_id']
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        for _, file in files:
            file.close()


# Test Case 010 - Network Hospital
def test_tc010():
    """Test TC010: Network hospital discount"""
    print("\n🧪 Testing TC010: Network Hospital (Expected: APPROVED with discount)")
    
    files = [
        ("files", open(DOCS_DIR / "tc010_apollo_bill.jpg", "rb")),
    ]
    
    data = {
        "member_id": "EMP010",
        "policy_id": "PLUM_GHI_2024",
        "claim_category": "CONSULTATION",
        "treatment_date": "2024-11-03",
        "claimed_amount": "4500",
        "hospital_name": "Apollo Hospitals"
    }
    
    try:
        response = requests.post(API_URL, files=files, data=data)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ Claim submitted successfully!")
        print(f"   Claim ID: {result['claim_id']}")
        print(f"   Status: {result['status']}")
        
        return result['claim_id']
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        for _, file in files:
            file.close()


def check_status(claim_id):
    """Check claim status"""
    if not claim_id:
        return
    
    print(f"\n📊 Checking status for {claim_id}...")
    
    try:
        response = requests.get(f"http://localhost:8000/api/v1/claims/{claim_id}/status")
        response.raise_for_status()
        
        result = response.json()
        print(f"   Status: {result['status']}")
        if result.get('current_stage'):
            print(f"   Current Stage: {result['current_stage']}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error checking status: {e}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Mock Document Upload Test")
    print("=" * 60)
    print("\n⚠️  Make sure the backend is running:")
    print("   cd backend && python -m uvicorn app.main:app --reload --port 8000")
    print()
    
    # Run tests
    claim_ids = []
    
    claim_id = test_tc004()
    if claim_id:
        claim_ids.append(claim_id)
    
    claim_id = test_tc006()
    if claim_id:
        claim_ids.append(claim_id)
    
    claim_id = test_tc010()
    if claim_id:
        claim_ids.append(claim_id)
    
    # Check statuses
    if claim_ids:
        print("\n" + "=" * 60)
        print("Checking Claim Statuses")
        print("=" * 60)
        
        import time
        time.sleep(2)  # Wait for processing to start
        
        for claim_id in claim_ids:
            check_status(claim_id)
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("   1. Check frontend: http://localhost:5173")
    print("   2. View claim status pages")
    print("   3. View final decisions with trace")


if __name__ == "__main__":
    main()
