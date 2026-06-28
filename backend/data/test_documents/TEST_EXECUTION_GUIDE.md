# Test Execution Guide

Step-by-step guide for running all 12 test cases through the MediClaim system.

## Prerequisites

1. ✅ Backend server running (`uvicorn backend.app.main:app --reload`)
2. ✅ Frontend server running (`npm run dev` in frontend/)
3. ✅ Supabase credentials configured in `.env`
4. ✅ LLM provider configured (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`)
5. ✅ PaddleOCR installed and configured

## Test Execution Checklist

### TC001: Wrong Document Uploaded ❌
**Purpose**: System must detect wrong document type before processing

**Upload**:
- Member ID: EMP001
- Claim Category: CONSULTATION
- Treatment Date: 2024-11-01
- Claimed Amount: ₹1,500
- Documents: `prescriptions/F001.jpg`, `prescriptions/F002.jpg`

**Expected Result**:
- ❌ Should STOP before making any claim decision
- ✅ Error message should say: "Expected HOSPITAL_BILL but received PRESCRIPTION"
- ✅ Message must be specific, not generic

**Verification**:
- [ ] System stopped processing?
- [ ] Error message mentions specific document types?
- [ ] No claim decision was made?

---

### TC002: Unreadable Document 📷
**Purpose**: System must detect poor quality documents

**Upload**:
- Member ID: EMP004
- Claim Category: PHARMACY
- Treatment Date: 2024-10-25
- Claimed Amount: ₹800
- Documents: `prescriptions/F003.jpg`, `bills/F004.jpg` (blurry)

**Expected Result**:
- ❌ Should detect unreadable pharmacy bill
- ✅ Should ask member to re-upload specific document
- ✅ Should NOT reject claim outright

**Verification**:
- [ ] System detected blurry/unreadable bill?
- [ ] Requested re-upload of specific document?
- [ ] Did not auto-reject the claim?

---

### TC003: Documents Belong to Different Patients 👥
**Purpose**: System must validate patient name consistency

**Upload**:
- Member ID: EMP001
- Claim Category: CONSULTATION
- Treatment Date: 2024-11-01
- Claimed Amount: ₹1,500
- Documents: `prescriptions/F005.jpg` (Rajesh), `bills/F006.jpg` (Arjun)

**Expected Result**:
- ❌ Should detect name mismatch
- ✅ Should show both names found: "Rajesh Kumar" vs "Arjun Mehta"
- ✅ Should NOT proceed to claim decision

**Verification**:
- [ ] Detected patient name mismatch?
- [ ] Showed both names in error message?
- [ ] Did not proceed to decision?

---

### TC004: Clean Consultation — Full Approval ✅
**Purpose**: Baseline happy path test

**Upload**:
- Member ID: EMP001
- Claim Category: CONSULTATION
- Treatment Date: 2024-11-01
- Claimed Amount: ₹1,500
- YTD Claims: ₹5,000
- Documents: `prescriptions/F007.jpg`, `bills/F008.jpg`

**Expected Result**:
- ✅ Decision: APPROVED
- ✅ Approved Amount: ₹1,350 (10% co-pay = ₹150 deducted)
- ✅ Confidence Score: > 0.85
- ✅ Clear explanation of co-pay deduction

**Verification**:
- [ ] Decision = APPROVED?
- [ ] Approved amount = ₹1,350?
- [ ] Co-pay calculation shown?
- [ ] Confidence > 0.85?
- [ ] Full trace visible?

---

### TC005: Waiting Period — Diabetes ⏳
**Purpose**: Waiting period enforcement

**Upload**:
- Member ID: EMP005 (joined 2024-09-01)
- Claim Category: CONSULTATION
- Treatment Date: 2024-10-15 (only 44 days after joining)
- Claimed Amount: ₹3,000
- Documents: `prescriptions/F009.jpg`, `bills/F010.jpg`

**Expected Result**:
- ❌ Decision: REJECTED
- ✅ Reason: WAITING_PERIOD
- ✅ Must state eligible date (2024-09-01 + 90 days = 2024-11-30)

**Verification**:
- [ ] Decision = REJECTED?
- [ ] Reason mentions waiting period?
- [ ] Shows eligible date (2024-11-30)?
- [ ] Detected diabetes diagnosis?

---

### TC006: Dental Partial Approval — Cosmetic Exclusion 🦷
**Purpose**: Line-item level approval/rejection

**Upload**:
- Member ID: EMP002
- Claim Category: DENTAL
- Treatment Date: 2024-10-15
- Claimed Amount: ₹12,000
- Documents: `bills/F011.jpg`

**Expected Result**:
- ⚠️ Decision: PARTIAL
- ✅ Approved Amount: ₹8,000 (Root Canal only)
- ✅ Line items shown:
  - Root Canal (₹8,000) - APPROVED
  - Teeth Whitening (₹4,000) - REJECTED (cosmetic exclusion)

**Verification**:
- [ ] Decision = PARTIAL?
- [ ] Approved amount = ₹8,000?
- [ ] Line-item breakdown shown?
- [ ] Teeth whitening rejected with reason?

---

### TC007: MRI Without Pre-Authorization 🏥
**Purpose**: Pre-authorization requirement enforcement

**Upload**:
- Member ID: EMP007
- Claim Category: DIAGNOSTIC
- Treatment Date: 2024-11-02
- Claimed Amount: ₹15,000
- Documents: `prescriptions/F012.jpg`, `reports/F013.jpg`, `bills/F014.jpg`

**Expected Result**:
- ❌ Decision: REJECTED
- ✅ Reason: PRE_AUTH_MISSING
- ✅ Explanation: MRI > ₹10,000 requires pre-authorization
- ✅ Instructions on how to get pre-auth

**Verification**:
- [ ] Decision = REJECTED?
- [ ] Reason mentions pre-authorization?
- [ ] Threshold (₹10,000) mentioned?
- [ ] Instructions for resubmission provided?

---

### TC008: Per-Claim Limit Exceeded 💰
**Purpose**: Per-claim limit enforcement

**Upload**:
- Member ID: EMP003
- Claim Category: CONSULTATION
- Treatment Date: 2024-10-20
- Claimed Amount: ₹7,500 (exceeds ₹5,000 limit)
- YTD Claims: ₹10,000
- Documents: `prescriptions/F015.jpg`, `bills/F016.jpg`

**Expected Result**:
- ❌ Decision: REJECTED
- ✅ Reason: PER_CLAIM_EXCEEDED
- ✅ Must state limit (₹5,000) and claimed amount (₹7,500)

**Verification**:
- [ ] Decision = REJECTED?
- [ ] Reason mentions per-claim limit?
- [ ] Shows both limit and claimed amount?

---

### TC009: Fraud Signal — Multiple Same-Day Claims 🚨
**Purpose**: Fraud detection system

**Upload**:
- Member ID: EMP008
- Claim Category: CONSULTATION
- Treatment Date: 2024-10-30
- Claimed Amount: ₹4,800
- Claims History: 3 other claims on same day (CLM_0081, CLM_0082, CLM_0083)
- Documents: `prescriptions/F017.jpg`, `bills/F018.jpg`

**Expected Result**:
- ⚠️ Decision: MANUAL_REVIEW
- ✅ Fraud signals flagged (same-day pattern)
- ✅ NOT auto-rejected
- ✅ Specific signals mentioned in trace

**Verification**:
- [ ] Decision = MANUAL_REVIEW?
- [ ] Same-day pattern flagged?
- [ ] Not auto-rejected?
- [ ] Fraud score visible in trace?

---

### TC010: Network Hospital — Discount Applied 🏥
**Purpose**: Network discount + co-pay calculation order

**Upload**:
- Member ID: EMP010
- Claim Category: CONSULTATION
- Treatment Date: 2024-11-03
- Claimed Amount: ₹4,500
- Hospital: Apollo Hospitals (network)
- YTD Claims: ₹8,000
- Documents: `prescriptions/F019.jpg`, `bills/F020.jpg`

**Expected Result**:
- ✅ Decision: APPROVED
- ✅ Approved Amount: ₹3,240
- ✅ Calculation breakdown:
  1. Original: ₹4,500
  2. Network discount (20%): -₹900 = ₹3,600
  3. Co-pay (10%): -₹360 = ₹3,240 final

**Verification**:
- [ ] Decision = APPROVED?
- [ ] Approved amount = ₹3,240?
- [ ] Network discount applied BEFORE co-pay?
- [ ] Calculation breakdown visible?

---

### TC011: Component Failure — Graceful Degradation 🔧
**Purpose**: System resilience and graceful degradation

**Upload**:
- Member ID: EMP006
- Claim Category: ALTERNATIVE_MEDICINE
- Treatment Date: 2024-10-28
- Claimed Amount: ₹4,000
- Simulate Component Failure: TRUE
- Documents: `prescriptions/F021.jpg`, `bills/F022.jpg`

**Expected Result**:
- ✅ Decision: APPROVED (or partial - depends on failure)
- ✅ System did NOT crash (no 500 error)
- ✅ Trace shows component failure noted
- ✅ Confidence score LOWER than normal (< 0.85)
- ✅ Note recommending manual review

**Verification**:
- [ ] System did not crash?
- [ ] Decision still made?
- [ ] Component failure visible in trace?
- [ ] Confidence score lower than normal?
- [ ] Manual review recommended?

---

### TC012: Excluded Treatment ⛔
**Purpose**: Policy exclusion enforcement

**Upload**:
- Member ID: EMP009
- Claim Category: CONSULTATION
- Treatment Date: 2024-10-18
- Claimed Amount: ₹8,000
- Documents: `prescriptions/F023.jpg`, `bills/F024.jpg`

**Expected Result**:
- ❌ Decision: REJECTED
- ✅ Reason: EXCLUDED_CONDITION
- ✅ Confidence: > 0.90
- ✅ Explicit mention: "Obesity treatment" excluded

**Verification**:
- [ ] Decision = REJECTED?
- [ ] Reason mentions excluded condition?
- [ ] Obesity treatment identified?
- [ ] Confidence > 0.90?

---

## Scoring

**Pass Criteria**: 10/12 test cases must pass with correct decisions and reasoning.

**Critical Test Cases** (must pass):
- TC001, TC002, TC003 (document verification)
- TC004 (happy path)
- TC010 (calculation order)
- TC011 (resilience)

**Total Score**: _____ / 12

---

## Notes for Evaluator

1. **Trace Quality**: Every decision must have a complete trace showing:
   - What was checked
   - What passed/failed
   - Why the decision was made

2. **Error Messages**: TC001-TC003 require specific, actionable error messages

3. **Calculation Visibility**: TC004, TC006, TC010 must show calculation breakdowns

4. **Confidence Scores**: Should reflect processing quality (TC011 shows lower confidence)

5. **No Crashes**: System must handle all cases gracefully, even failures

---

**Last Updated**: Auto-generated with test documents
