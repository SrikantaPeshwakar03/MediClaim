# MediClaim Component Contracts

## Overview

This document defines the contracts for every major component in the MediClaim system. It specifies:

- Shared state structure
- API interfaces
- LangGraph orchestration
- Agent responsibilities
- Service interfaces
- Exception hierarchy

These contracts ensure that every component can be independently developed, tested, and replaced while maintaining compatibility across the system.

---

## General Conventions

| Item | Description |
| --- | --- |
| Currency | Float (INR) |
| Dates | Python `date` objects (or ISO strings at API boundaries) |
| Confidence Score | Float between **0.0 – 1.0** |
| Fraud Score | Float between **0.0 – 1.0** |
| Base Exception | `MediClaimException` |

Every agent follows the **Graceful Degradation Rule**:

- Internal exceptions are never propagated.
- Agent records its failure.
- Component name is added to `components_failed`.
- Pipeline execution continues (except Document Verifier).

---

## 1. Shared State Contract

### ClaimState

`ClaimState` is a shared `TypedDict` that flows through the entire LangGraph pipeline.

Every agent:

- Reads existing values
- Updates its own fields
- Appends execution trace
- Returns the updated state

---

#### Input Fields

| Field | Type |
| --- | --- |
| claim_id | str |
| member_id | str |
| policy_id | str |
| claim_category | ClaimCategory |
| treatment_date | date |
| claimed_amount | float |
| hospital_name | Optional[str] |
| document_file_paths | List[str] |
| document_metadata | List[dict] |
| simulate_component_failure | bool |

---

#### Agent Output Fields

**Document Verification**

- verification_result
- stop_processing

**OCR Extraction**

- ocr_results
- extracted_data
- extraction_confidence
- extraction_errors

**Policy Validation**

- policy_validation
- eligible_amount

**Fraud Detection**

- fraud_detection
- fraud_score

**Final Decision**

- final_decision
- decision
- approved_amount
- confidence_score

---

#### Cross-Cutting Metadata

- trace
- errors
- warnings
- components_executed
- components_failed
- processing_start_time
- processing_end_time

**Design Note**

Shared collections such as `trace`, `errors`, and `warnings` are maintained as plain Python lists with **last-write-wins semantics**. They are intentionally not implemented as LangGraph reducers to prevent duplicate entries during graph execution.

---

## 2. API Contracts

### 2.1 Submit Claim

**Endpoint**

```http
POST /api/v1/claims/submit
```

**Input**

Multipart form containing:

- Member ID
- Policy ID
- Claim Category
- Treatment Date
- Claimed Amount
- Hospital Name (optional)
- Uploaded Documents

**Response**

```python
ClaimSubmitResponse
```

Returns:

- Claim ID
- Status (PENDING)
- Message
- Created Timestamp

**Side Effects**

- Stores uploaded documents
- Creates claim record
- Inserts into Supabase (best effort)
- Starts background processing

---

### 2.2 Claim Status

```http
GET /api/v1/claims/{claim_id}/status
```

**Returns**

- Current Status
- Current Processing Stage
- Creation Time
- Updated Time

---

### 2.3 Claim Decision

```http
GET /api/v1/claims/{claim_id}/decision
```

**Returns**

- Final Decision
- Approval Amount
- Confidence Score
- Execution Trace
- Processing Time

---

### 2.4 Health Check

```http
GET /api/v1/health
```

**Returns**

```json
{
  "status": "...",
  "version": "...",
  "timestamp": "..."
}
```

---

### Exception Mapping

| Exception | HTTP Status |
| --- | --- |
| MediClaimException | 400 |
| Unknown Exception | 500 |

---

## 3. LangGraph Orchestrator

### process_claim(state)

Responsible for executing the complete claim workflow.

Execution flow:

```text
DocumentVerifier
        │
        ▼
OCRExtractor
        │
        ▼
PolicyValidator
        │
        ▼
FraudDetector
        │
        ▼
DecisionMaker
```

**Conditional Routing**

If

```python
stop_processing == True
```

Pipeline immediately terminates.

Otherwise execution continues until completion.

The orchestrator never propagates exceptions. Unexpected failures are recorded inside the shared state.

---

## 4. Agent Contracts

Each agent follows the interface:

```python
agent(state: ClaimState) -> ClaimState
```

Every agent:

- Reads required state
- Performs its task
- Updates ClaimState
- Records execution trace
- Returns updated state

---

### 4.1 Document Verifier

**Purpose**

Validates uploaded claim documents before processing begins.

**Responsibilities**

- Document classification
- Required document validation
- Readability checks
- Patient name consistency

**Writes**

- verification_result
- stop_processing

**Pipeline Behavior**

This is the **only blocking agent**.

Processing stops if:

- Required document missing
- Wrong document uploaded
- Unreadable document
- Patient mismatch

---

### 4.2 OCR Extractor

**Purpose**

Extracts structured medical information.

**Responsibilities**

- OCR
- Vision OCR (optional)
- Medical entity extraction
- Doctor registration validation
- Integrity flag detection

**Outputs**

- OCR Results
- Structured Medical Data
- Extraction Confidence
- Extraction Errors

Supports graceful degradation when extraction fails.

---

### 4.3 Policy Validator

**Purpose**

Determines policy eligibility.

**Validation Rules**

- Member verification
- Waiting periods
- Coverage limits
- Category limits
- Annual limits
- Exclusions
- Pre-authorization

**Financial Calculation**

1. Coverage validation
2. Network discount
3. Co-pay deduction
4. Eligible reimbursement

Supports line-item approvals.

---

### 4.4 Fraud Detector

**Purpose**

Detects suspicious claims.

**Fraud Signals**

- Same-day claims
- Monthly frequency
- High-value claims
- Historical anomalies
- Hospital patterns
- Document alteration
- Duplicate submissions

Produces:

- Fraud Score
- Fraud Signals
- Manual Review Recommendation

Pipeline continues even if fraud detection fails.

---

### 4.5 Decision Maker

**Purpose**

Generates the final claim decision.

Possible outcomes:

- APPROVED
- PARTIAL
- REJECTED
- MANUAL_REVIEW

Decision priority:

1. Manual Review
2. Rejected
3. Partial Approval
4. Approved

Confidence score is computed from:

- Failed components
- OCR confidence
- Fraud score

---

## 5. Service Contracts

### OCR Service

Responsible for:

- Image preprocessing
- PDF rendering
- PaddleOCR extraction
- Readability assessment
- Vision model preparation

Primary methods:

- extract_text()
- extract_from_document()
- check_document_quality()
- render_document_to_images()

---

### LLM Service

Provides a provider-independent interface through LiteLLM.

Responsibilities:

- Structured extraction
- Document classification
- Vision processing
- JSON parsing
- Patient name validation

Supports:

- OpenAI
- Gemini
- Anthropic
- OpenRouter
- Ollama

Includes automatic retry with exponential backoff.

---

### Policy Engine

Loads policy configuration and applies deterministic business rules.

Responsibilities:

- Member lookup
- Waiting periods
- Coverage validation
- Exclusion checking
- Financial calculations
- Network hospital validation

Policy rules are loaded dynamically from configuration files.

---

### Supabase Service

Handles persistent storage.

Responsibilities:

- Claim creation
- Status updates
- Decision storage
- OCR persistence
- Trace storage
- Audit logging
- Claim history retrieval

Database failures never interrupt claim processing.

---

### Medical Validators

Provides reusable medical validation utilities.

Currently includes:

- Doctor Registration Number Validation

Validation is advisory only and never rejects claims directly.

---

## 6. Exception Hierarchy

```text
MediClaimException
│
├── DocumentVerificationError
├── OCRExtractionError
├── PolicyValidationError
├── FraudDetectionError
├── DecisionMakingError
├── NotFoundError
├── ConfigurationError
├── AuthenticationError
└── AccessDeniedError
```

Each exception contains:

- Internal message
- User-friendly message
- Additional metadata

---

## 7. Design Principles

The component contracts follow several core architectural principles:

**Single Responsibility**

Each agent performs exactly one task.

**Shared State Communication**

Components communicate exclusively through `ClaimState`, ensuring loose coupling.

**Graceful Degradation**

Except for `DocumentVerifier`, component failures never halt the workflow. Instead, failures are recorded and processing continues with reduced confidence.

**Deterministic Business Logic**

Policy validation and financial calculations remain deterministic, while AI is used only for document understanding and information extraction.

**Replaceability**

Every service and agent conforms to a stable contract, allowing implementations to be swapped without impacting the rest of the system.

---

## 8. Reimplementation Requirements

Any component may be reimplemented independently provided the following invariants are preserved:

1. `ClaimState` field names and types remain unchanged.
2. Agent interfaces continue to follow:

```python
agent(state: ClaimState) -> ClaimState
```

3. The Graceful Degradation Rule is maintained.
4. Execution traces are consistently recorded.
5. Document Verifier remains the sole component capable of terminating the pipeline.
