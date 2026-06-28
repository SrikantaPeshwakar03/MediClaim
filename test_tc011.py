#!/usr/bin/env python3
"""
Test TC011: Component Failure - Graceful Degradation
Tests that the system continues processing even when a component fails
"""

import requests
import time
from pathlib import Path

# API Configuration
API_URL = "http://localhost:8000/api/v1"

# Test Case TC011 - Graceful Degradation
test_case = {
    "member_id": "EMP006",
    "policy_id": "PLUM_GHI_2024",
    "claim_category": "ALTERNATIVE_MEDICINE",
    "treatment_date": "2024-10-28",
    "claimed_amount": 4000.00,
    "hospital_name": "Ayur Wellness Centre",
    "simulate_component_failure": True,  # THIS IS THE KEY!
    "documents": [
        "backend/data/test_documents/prescriptions/F021.jpg",  # Ayurveda Prescription
        "backend/data/test_documents/bills/F022.jpg"           # Hospital Bill
    ]
}

print("=" * 70)
print("🧪 Testing TC011: Component Failure - Graceful Degradation")
print("=" * 70)
print(f"\n📋 Test Case Details:")
print(f"   Member: {test_case['member_id']} (Kavita Nair)")
print(f"   Category: {test_case['claim_category']} (Ayurveda)")
print(f"   Amount: ₹{test_case['claimed_amount']}")
print(f"   ⚠️  Simulate Failure: {test_case['simulate_component_failure']}")
print()
print(f"✅ Expected Behavior:")
print(f"   1. System does NOT crash (no 500 error)")
print(f"   2. Pipeline continues despite component failure")
print(f"   3. Decision: APPROVED (with reduced confidence)")
print(f"   4. Output shows which component failed")
print(f"   5. Recommends manual review")
print()

# Prepare the request
files = []
for doc_path in test_case["documents"]:
    file_path = Path(doc_path)
    if file_path.exists():
        files.append(
            ("files", (file_path.name, open(file_path, "rb"), "image/jpeg"))
        )
        print(f"📄 Document: {file_path.name}")
    else:
        print(f"❌ File not found: {doc_path}")

if len(files) != 2:
    print(f"\n❌ ERROR: Expected 2 documents, found {len(files)}")
    exit(1)

# Prepare form data
data = {
    "member_id": test_case["member_id"],
    "policy_id": test_case["policy_id"],
    "claim_category": test_case["claim_category"],
    "treatment_date": test_case["treatment_date"],
    "claimed_amount": test_case["claimed_amount"],
    "hospital_name": test_case["hospital_name"],
    "simulate_component_failure": test_case["simulate_component_failure"]
}

print(f"\n📤 Submitting claim to {API_URL}/claims/submit...")
print(f"   (with simulate_component_failure=True)")

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
        
        # Wait for processing
        print(f"\n⏳ Waiting for processing to complete...")
        max_wait = 60  # seconds
        waited = 0
        
        while waited < max_wait:
            time.sleep(3)
            waited += 3
            
            status_response = requests.get(f"{API_URL}/claims/{claim_id}/status")
            if status_response.status_code == 200:
                status_data = status_response.json()
                current_status = status_data.get("status")
                current_stage = status_data.get("current_stage", "")
                
                print(f"   [{waited}s] Status: {current_status}, Stage: {current_stage}")
                
                if current_status == "COMPLETED":
                    break
        
        # Get decision
        print(f"\n📊 Fetching decision...")
        decision_response = requests.get(f"{API_URL}/claims/{claim_id}/decision")
        
        if decision_response.status_code == 200:
            decision_data = decision_response.json()
            decision = decision_data.get("decision")
            trace = decision_data.get("trace", {})
            
            print(f"\n" + "=" * 70)
            print(f"🎯 RESULTS - TC011 Graceful Degradation Test")
            print("=" * 70)
            
            # Check #1: Did it crash?
            if decision_data.get("status") == "COMPLETED":
                print(f"✅ 1. System did NOT crash (status: COMPLETED)")
            else:
                print(f"❌ 1. System crashed or failed (status: {decision_data.get('status')})")
            
            # Check #2: Was a decision made?
            if decision:
                print(f"✅ 2. Decision was made: {decision.get('decision')}")
                
                # Check #3: Component failure visible?
                components_failed = decision.get('components_failed', [])
                if components_failed:
                    print(f"✅ 3. Component failures shown: {components_failed}")
                else:
                    print(f"⚠️  3. No component failures recorded (simulate_component_failure may not be working)")
                
                # Check #4: Confidence score reduced?
                confidence = decision.get('confidence_score')
                if confidence is not None:
                    print(f"✅ 4. Confidence score: {confidence:.2%}", end="")
                    if confidence < 0.7:
                        print(f" (reduced ✅)")
                    else:
                        print(f" (not reduced ⚠️)")
                else:
                    print(f"❌ 4. No confidence score provided")
                
                # Check #5: Manual review recommended?
                manual_review_reason = decision.get('manual_review_reason')
                if manual_review_reason:
                    print(f"✅ 5. Manual review recommended: {manual_review_reason}")
                else:
                    print(f"⚠️  5. No manual review recommendation")
                
                # Show decision details
                print(f"\n📋 Decision Details:")
                print(f"   Decision: {decision.get('decision')}")
                print(f"   Original Amount: ₹{decision.get('original_amount', 0)}")
                print(f"   Approved Amount: ₹{decision.get('approved_amount', 0)}")
                if decision.get('rejection_reasons'):
                    print(f"   Rejection Reasons: {decision.get('rejection_reasons')}")
                
            else:
                print(f"❌ 2. No decision was made")
                print(f"   This is a FAILURE - graceful degradation should still produce a decision")
            
            # Show trace
            agent_traces = trace.get('agent_traces', [])
            if agent_traces:
                print(f"\n📝 Agent Execution Trace:")
                for i, agent_trace in enumerate(agent_traces, 1):
                    agent_name = agent_trace.get('agent', 'Unknown')
                    status = agent_trace.get('status', 'unknown')
                    print(f"   {i}. {agent_name}: {status}")
            
            print(f"\n🌐 View full results at:")
            print(f"   http://localhost:5173/decision/{claim_id}")
            
        else:
            print(f"\n❌ Failed to fetch decision")
            print(f"   Status Code: {decision_response.status_code}")
            print(f"   Response: {decision_response.text[:500]}")
        
    else:
        print(f"\n❌ Submission failed!")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("\n❌ ERROR: Cannot connect to backend API")
    print("   Make sure the backend is running on http://localhost:8000")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
