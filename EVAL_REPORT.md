# MediClaim — Evaluation Report

_Generated: 2026-06-28T05:59:29.187199Z_

**Result: 12/12 test cases matched the expected outcome.**

This report runs every case from `test_cases.json` through the full 5-agent pipeline (DocumentVerifier → OCRExtractor → PolicyValidator → FraudDetector → DecisionMaker). External services (OCR/LLM/Supabase) are stubbed deterministically so the run is reproducible; all decision and policy logic is the real production code.

## Summary

| Case | Name | Expected | Actual | Match |
|------|------|----------|--------|-------|
| TC001 | Wrong Document Uploaded | STOP (no decision) | STOP (no decision) | ✅ |
| TC002 | Unreadable Document | STOP (no decision) | STOP (no decision) | ✅ |
| TC003 | Documents Belong to Different Patients | STOP (no decision) | STOP (no decision) | ✅ |
| TC004 | Clean Consultation — Full Approval | APPROVED | APPROVED | ✅ |
| TC005 | Waiting Period — Diabetes | REJECTED | REJECTED | ✅ |
| TC006 | Dental Partial Approval — Cosmetic Exclusion | PARTIAL | PARTIAL | ✅ |
| TC007 | MRI Without Pre-Authorization | REJECTED | REJECTED | ✅ |
| TC008 | Per-Claim Limit Exceeded | REJECTED | REJECTED | ✅ |
| TC009 | Fraud Signal — Multiple Same-Day Claims | MANUAL_REVIEW | MANUAL_REVIEW | ✅ |
| TC010 | Network Hospital — Discount Applied | APPROVED | APPROVED | ✅ |
| TC011 | Component Failure — Graceful Degradation | APPROVED | APPROVED | ✅ |
| TC012 | Excluded Treatment | REJECTED | REJECTED | ✅ |

## Case Details

### TC001 — Wrong Document Uploaded

**Status: PASS ✅** — Pipeline stopped before a decision, as required.

- Expected: `no decision (stop early)`
- Decision: _none (pipeline stopped at verification)_
- Verification errors:
    - Missing required documents: HOSPITAL_BILL. You uploaded: PRESCRIPTION, PRESCRIPTION. Please upload all required documents to proceed.

**Execution trace:**

- **DocumentVerifier** — `failed`
    - verification_passed: False

### TC002 — Unreadable Document

**Status: PASS ✅** — Pipeline stopped before a decision, as required.

- Expected: `no decision (stop early)`
- Decision: _none (pipeline stopped at verification)_
- Verification errors:
    - Missing required documents: PHARMACY_BILL. You uploaded: PRESCRIPTION, UNKNOWN. Please upload all required documents to proceed.
    - Cannot identify document type for 'doc1.jpg'. Please ensure the document is clear and readable.
    - Document 'doc1.jpg' (UNKNOWN) is not readable. Issues: Low confidence, Blurry. Please upload a clearer image of this document.

**Execution trace:**

- **DocumentVerifier** — `failed`
    - verification_passed: False

### TC003 — Documents Belong to Different Patients

**Status: PASS ✅** — Pipeline stopped before a decision, as required.

- Expected: `no decision (stop early)`
- Decision: _none (pipeline stopped at verification)_
- Verification errors:
    - Patient names are inconsistent across documents: Rajesh Kumar, Arjun Mehta. Different names

**Execution trace:**

- **DocumentVerifier** — `failed`
    - verification_passed: False

### TC004 — Clean Consultation — Full Approval

**Status: PASS ✅** — Decision matches expected outcome (approved amount ₹1,350.00 matches).

- Expected: `APPROVED`
- Decision: `APPROVED`
- Approved amount: ₹1,350.00
- Confidence: 1.00
- Message: Claim approved. Amount: ₹1,350.00. Co-pay deducted: ₹150.00.

**Execution trace:**

- **DocumentVerifier** — `success`
    - verification_passed: True
- **OCRExtractor** — `success`
- **PolicyValidator** — `success`
    - all_checks_passed: True
    - eligible_amount: 1350.0
- **FraudDetector** — `success`
    - fraud_score: 0.0
    - num_signals: 0
- **DecisionMaker** — `success`
    - decision: APPROVED
    - approved_amount: 1350.0
    - confidence_score: 1.0
    - decision_message: Claim approved. Amount: ₹1,350.00. Co-pay deducted: ₹150.00.

### TC005 — Waiting Period — Diabetes

**Status: PASS ✅** — Decision matches expected outcome (rejection reasons ['WAITING_PERIOD'] match).

- Expected: `REJECTED`
- Decision: `REJECTED`
- Approved amount: ₹0.00
- Confidence: 1.00
- Rejection reasons: ['WAITING_PERIOD']
- Message: Claim rejected. Reasons: Waiting period not completed

**Execution trace:**

- **DocumentVerifier** — `success`
    - verification_passed: True
- **OCRExtractor** — `success`
- **PolicyValidator** — `success`
    - all_checks_passed: False
    - eligible_amount: 0.0
- **FraudDetector** — `success`
    - fraud_score: 0.0
    - num_signals: 0
- **DecisionMaker** — `success`
    - decision: REJECTED
    - approved_amount: 0.0
    - confidence_score: 1.0
    - decision_message: Claim rejected. Reasons: Waiting period not completed

### TC006 — Dental Partial Approval — Cosmetic Exclusion

**Status: PASS ✅** — Decision matches expected outcome (approved amount ₹8,000.00 matches).

- Expected: `PARTIAL`
- Decision: `PARTIAL`
- Approved amount: ₹8,000.00
- Confidence: 1.00
- Message: Claim partially approved. Approved items: Root Canal Treatment. Rejected items: Teeth Whitening (Teeth Whitening is not covered). Approved amount: ₹8,000.00

**Execution trace:**

- **DocumentVerifier** — `success`
    - verification_passed: True
- **OCRExtractor** — `success`
- **PolicyValidator** — `success`
    - all_checks_passed: True
    - eligible_amount: 10800.0
- **FraudDetector** — `success`
    - fraud_score: 0.0
    - num_signals: 0
- **DecisionMaker** — `success`
    - decision: PARTIAL
    - approved_amount: 8000.0
    - confidence_score: 1.0
    - decision_message: Claim partially approved. Approved items: Root Canal Treatment. Rejected items: Teeth Whitening (Teeth Whitening is not covered). Approved amount: ₹8,000.00

### TC007 — MRI Without Pre-Authorization

**Status: PASS ✅** — Decision matches expected outcome (rejection reasons ['PRE_AUTH_MISSING'] match).

- Expected: `REJECTED`
- Decision: `REJECTED`
- Approved amount: ₹0.00
- Confidence: 1.00
- Rejection reasons: ['PRE_AUTH_MISSING']
- Message: Claim rejected. Reasons: Pre-authorization required

**Execution trace:**

- **DocumentVerifier** — `success`
    - verification_passed: True
- **OCRExtractor** — `success`
- **PolicyValidator** — `success`
    - all_checks_passed: False
    - eligible_amount: 0.0
- **FraudDetector** — `success`
    - fraud_score: 0.0
    - num_signals: 0
- **DecisionMaker** — `success`
    - decision: REJECTED
    - approved_amount: 0.0
    - confidence_score: 1.0
    - decision_message: Claim rejected. Reasons: Pre-authorization required

### TC008 — Per-Claim Limit Exceeded

**Status: PASS ✅** — Decision matches expected outcome (rejection reasons ['PER_CLAIM_EXCEEDED'] match).

- Expected: `REJECTED`
- Decision: `REJECTED`
- Approved amount: ₹0.00
- Confidence: 1.00
- Rejection reasons: ['PER_CLAIM_EXCEEDED']
- Message: Claim rejected. Reasons: Per-claim limit exceeded

**Execution trace:**

- **DocumentVerifier** — `success`
    - verification_passed: True
- **OCRExtractor** — `success`
- **PolicyValidator** — `success`
    - all_checks_passed: False
    - eligible_amount: 0.0
- **FraudDetector** — `success`
    - fraud_score: 0.0
    - num_signals: 0
- **DecisionMaker** — `success`
    - decision: REJECTED
    - approved_amount: 0.0
    - confidence_score: 1.0
    - decision_message: Claim rejected. Reasons: Per-claim limit exceeded

### TC009 — Fraud Signal — Multiple Same-Day Claims

**Status: PASS ✅** — Decision matches expected outcome.

- Expected: `MANUAL_REVIEW`
- Decision: `MANUAL_REVIEW`
- Approved amount: ₹0.00
- Confidence: 1.00
- Manual review: Fraud signals detected: SAME_DAY_CLAIMS: Member has 3 claims on 2024-10-30 (including this one). This exceeds the policy limit of 2 claims per day.
- Message: Claim flagged for manual review. Reason: Fraud signals detected: SAME_DAY_CLAIMS: Member has 3 claims on 2024-10-30 (including this one). This exceeds the policy limit of 2 claims per day.

**Execution trace:**

- **DocumentVerifier** — `success`
    - verification_passed: True
- **OCRExtractor** — `success`
- **PolicyValidator** — `success`
    - all_checks_passed: True
    - eligible_amount: 4320.0
- **FraudDetector** — `success`
    - fraud_score: 0.25
    - num_signals: 1
- **DecisionMaker** — `success`
    - decision: MANUAL_REVIEW
    - approved_amount: 0.0
    - confidence_score: 1.0
    - decision_message: Claim flagged for manual review. Reason: Fraud signals detected: SAME_DAY_CLAIMS: Member has 3 claims on 2024-10-30 (including this one). This exceeds the policy limit of 2 claims per day.

### TC010 — Network Hospital — Discount Applied

**Status: PASS ✅** — Decision matches expected outcome (approved amount ₹3,240.00 matches).

- Expected: `APPROVED`
- Decision: `APPROVED`
- Approved amount: ₹3,240.00
- Confidence: 1.00
- Message: Claim approved. Amount: ₹3,240.00. Network discount applied: ₹900.00. Co-pay deducted: ₹360.00.

**Execution trace:**

- **DocumentVerifier** — `success`
    - verification_passed: True
- **OCRExtractor** — `success`
- **PolicyValidator** — `success`
    - all_checks_passed: True
    - eligible_amount: 3240.0
- **FraudDetector** — `success`
    - fraud_score: 0.0
    - num_signals: 0
- **DecisionMaker** — `success`
    - decision: APPROVED
    - approved_amount: 3240.0
    - confidence_score: 1.0
    - decision_message: Claim approved. Amount: ₹3,240.00. Network discount applied: ₹900.00. Co-pay deducted: ₹360.00.

### TC011 — Component Failure — Graceful Degradation

**Status: PASS ✅** — Decision matches expected outcome.

- Expected: `APPROVED`
- Decision: `APPROVED`
- Approved amount: ₹3,600.00
- Confidence: 0.70
- Manual review: Incomplete processing — the following component(s) failed: OCRExtractor.
- Message: Claim approved. Amount: ₹3,600.00. Co-pay deducted: ₹400.00. Note: OCRExtractor did not complete, so processing was partial. Manual review is recommended due to incomplete processing.

**Execution trace:**

- **DocumentVerifier** — `success`
    - verification_passed: True
- **OCRExtractor** — `failed`
    - error: Simulated component failure — extraction skipped (graceful degradation)
- **PolicyValidator** — `success`
    - all_checks_passed: True
    - eligible_amount: 3600.0
- **FraudDetector** — `success`
    - fraud_score: 0.0
    - num_signals: 0
- **DecisionMaker** — `success`
    - decision: APPROVED
    - approved_amount: 3600.0
    - confidence_score: 0.7000000000000001
    - decision_message: Claim approved. Amount: ₹3,600.00. Co-pay deducted: ₹400.00. Note: OCRExtractor did not complete, so processing was partial. Manual review is recommended due to incomplete processing.

_Components failed (graceful degradation): ['OCRExtractor']_

### TC012 — Excluded Treatment

**Status: PASS ✅** — Decision matches expected outcome (rejection reasons ['EXCLUDED_CONDITION'] match).

- Expected: `REJECTED`
- Decision: `REJECTED`
- Approved amount: ₹0.00
- Confidence: 1.00
- Rejection reasons: ['EXCLUDED_CONDITION']
- Message: Claim rejected. Reasons: Treatment is excluded

**Execution trace:**

- **DocumentVerifier** — `success`
    - verification_passed: True
- **OCRExtractor** — `success`
- **PolicyValidator** — `success`
    - all_checks_passed: False
    - eligible_amount: 0.0
- **FraudDetector** — `success`
    - fraud_score: 0.0
    - num_signals: 0
- **DecisionMaker** — `success`
    - decision: REJECTED
    - approved_amount: 0.0
    - confidence_score: 1.0
    - decision_message: Claim rejected. Reasons: Treatment is excluded
