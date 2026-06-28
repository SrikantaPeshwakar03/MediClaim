#!/usr/bin/env python3
"""
Quick test script to submit a claim with correct documents.
Tests TC004: Clean approval case (Rajesh Kumar)
"""

import requests
from pathlib import Path

# API Configuration
API_URL = "http://localhost:8000/api/v1"

# Test Case TC004 - Should APPROVE
test_case = {
    "member_id": "EMP001",
    "policy_id": "PLUM_GHI_2024",
    "claim_category": "CONSULTATION",
    "treatment_date": "2024-11-01",
    "claimed_amount": 1500.00,
    "hospital_name": "City Clinic",
    "documents": [
        "backend/data/test_documents/prescriptions/F007.jpg",  # Prescription
        "backend/data/test_documents/bills/F008.jpg"           # Hospital Bill
    ]
}

print("=" * 60)
print("🧪 Testing Claim Submission - TC004 (Clean Approval)")
print("=" * 60)
print(f"\n📋 Test Case Details:")
print(f"   Member: {test_case['member_id']} (Rajesh Kumar)")
print(f"   Category: {test_case['claim_category']}")
print(f"   Amount: ₹{test_case['claimed_amount']}")
print(f"   Expected: APPROVED with ₹1,350 (10% co-pay)")
print()

# Prepare the request
files = []
for doc_path in test_case["documents"]:
    file_path = Path(doc_path)
    if file_path.exists():
        files.append(
            ("files", (file_path.name, open(file_path, "rb"), "image/jpeg"))
        )
        print(f"✅ Document: {file_path.name}")
    else:
        print(f"❌ File not found: {doc_path}")

if len(files) != 2:
    print("\n❌ ERROR: Expected 2 documents, found", len(files))
    exit(1)

# Prepare form data
data = {
    "member_id": test_case["member_id"],
    "policy_id": test_case["policy_id"],
    "claim_category": test_case["claim_category"],
    "treatment_date": test_case["treatment_date"],
    "claimed_amount": test_case["claimed_amount"],
    "hospital_name": test_case["hospital_name"],
    "simulate_component_failure": False
}

print(f"\n📤 Submitting claim to {API_URL}/claims/submit...")

try:
    # Submit the claim
    response = requests.post(
        f"{API_URL}/claims/submit",
        data=data,
        files=files,
        timeout=30
    )
    
    # Close file handles
    for _, file_tuple in files:
        file_tuple[1].close()
    
    if response.status_code == 200:
        result = response.json()
        claim_id = result.get("claim_id")
        print(f"\n✅ Claim submitted successfully!")
        print(f"   Claim ID: {claim_id}")
        print(f"   Status: {result.get('status')}")
        print()
        print(f"🔗 Check status at:")
        print(f"   {API_URL}/claims/{claim_id}/status")
        print()
        print(f"🔗 View decision at:")
        print(f"   {API_URL}/claims/{claim_id}/decision")
        print()
        print(f"🌐 Frontend URL:")
        print(f"   http://localhost:5173/status/{claim_id}")
        
    else:
        print(f"\n❌ Submission failed!")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("\n❌ ERROR: Cannot connect to backend API")
    print("   Make sure the backend is running on http://localhost:8000")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("\n" + "=" * 60)
