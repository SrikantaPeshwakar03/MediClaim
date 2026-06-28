"""
FastAPI Routes

API endpoints for claims submission, status checking, and decision retrieval.
"""

import asyncio
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from datetime import date, datetime
import uuid
from pathlib import Path

from ..models import ClaimCategory, ClaimStatus, create_initial_state
from ..api.schemas import (
    ClaimSubmitRequest,
    ClaimSubmitResponse,
    ClaimStatusResponse,
    ClaimDecisionResponse,
    ErrorResponse
)
from ..agents.orchestrator import get_orchestrator
from ..exceptions import MediClaimException
from ..loggers import logger
from ..config import settings

# In-memory storage for demo (will be replaced with Supabase in Batch 4)
# Format: {claim_id: {"status": str, "state": ClaimState, "created_at": datetime}}
_claims_storage = {}

# Upload directory lives OUTSIDE the backend package directory.
# If uploads were written inside backend/, uvicorn --reload would detect the new
# files and restart the server mid-processing, wiping the in-memory store.
# Project root = backend/app/api/routes.py -> parents[3]
UPLOAD_DIR = Path(__file__).resolve().parents[3] / "temp_uploads"


router = APIRouter(prefix="/api/v1")


def _get_supabase():
    """
    Lazily get the Supabase service. Returns None if unavailable so that
    persistence failures never break the core in-memory processing flow.
    """
    try:
        from ..services import get_supabase_service
        return get_supabase_service()
    except Exception as e:
        logger.warning(f"Supabase service unavailable: {e}")
        return None


def _parse_dt(value, default=None):
    """Parse an ISO datetime string from the DB into a datetime object."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return default
    return default


def _status_from_supabase(claim_id: str):
    """
    Build a ClaimStatusResponse from Supabase when the claim is not in the
    in-memory store (e.g. after a server restart). Returns None if unavailable.
    """
    supabase = _get_supabase()
    if not supabase:
        return None
    try:
        row = supabase.get_claim(claim_id)
    except Exception:
        return None
    if not row:
        return None

    created = _parse_dt(row.get("created_at"), datetime.utcnow())
    updated = _parse_dt(row.get("updated_at"), created)
    try:
        status = ClaimStatus(row.get("status", "PENDING"))
    except ValueError:
        status = ClaimStatus.PENDING

    return ClaimStatusResponse(
        claim_id=claim_id,
        status=status,
        current_stage=None,
        created_at=created,
        updated_at=updated,
    )


def _decision_from_supabase(claim_id: str):
    """
    Reconstruct a ClaimDecisionResponse from Supabase when the claim is not in
    the in-memory store. Returns None if unavailable or not yet completed.
    """
    supabase = _get_supabase()
    if not supabase:
        return None
    try:
        row = supabase.get_claim(claim_id)
    except Exception:
        return None
    if not row:
        return None

    try:
        status = ClaimStatus(row.get("status", "PENDING"))
    except ValueError:
        status = ClaimStatus.PENDING

    created = _parse_dt(row.get("created_at"), datetime.utcnow())
    processed = _parse_dt(row.get("processed_at"))

    from ..models import ClaimDecisionOutput, ClaimDecision, RejectionReason, ClaimTrace

    decision_output = None
    if row.get("decision"):
        try:
            reasons = []
            for r in (row.get("rejection_reasons") or []):
                try:
                    reasons.append(RejectionReason(r))
                except ValueError:
                    continue
            decision_output = ClaimDecisionOutput(
                decision=ClaimDecision(row["decision"]),
                approved_amount=row.get("approved_amount") or 0.0,
                rejection_reasons=reasons,
                decision_message=row.get("decision_message", ""),
                confidence_score=row.get("confidence_score") or 0.0,
                original_amount=row.get("claimed_amount") or 0.0,
            )
        except Exception as e:
            logger.warning(f"[Supabase] Could not rebuild decision for {claim_id}: {e}")

    # Rebuild trace if available
    trace = None
    try:
        trace_data = supabase.get_trace(claim_id)
        if trace_data:
            trace = ClaimTrace(
                claim_id=claim_id,
                agent_traces=trace_data.get("agent_traces", []),
                errors=trace_data.get("errors", []),
                warnings=trace_data.get("warnings", []),
                processing_time_seconds=trace_data.get("processing_time_seconds", 0.0),
            )
    except Exception:
        pass

    return ClaimDecisionResponse(
        claim_id=claim_id,
        status=status,
        decision=decision_output,
        trace=trace,
        created_at=created,
        processed_at=processed,
    )


# === Helper Functions ===

def _save_uploaded_files(claim_id: str, files: List[UploadFile]) -> List[str]:
    """
    Save uploaded files to local storage.
    
    In production (Batch 4), this will upload to Supabase Storage.
    
    Args:
        claim_id: Claim ID
        files: List of uploaded files
        
    Returns:
        List of file paths
    """
    # Create directory for this claim (outside the reload-watched backend dir)
    claim_dir = UPLOAD_DIR / claim_id
    claim_dir.mkdir(parents=True, exist_ok=True)
    
    file_paths = []
    for file in files:
        file_path = claim_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        file_paths.append(str(file_path))
    
    return file_paths


async def _process_claim_async(claim_id: str):
    """
    Background task to process claim asynchronously.
    
    Args:
        claim_id: Claim ID to process
    """
    try:
        logger.info(f"Starting async processing for claim: {claim_id}")
        
        # Get claim from storage
        claim_data = _claims_storage.get(claim_id)
        if not claim_data:
            logger.error(f"Claim not found in storage: {claim_id}")
            return
        
        # Update status to PROCESSING
        claim_data["status"] = ClaimStatus.PROCESSING
        claim_data["updated_at"] = datetime.utcnow()
        
        # Get orchestrator
        orchestrator = get_orchestrator()
        
        # Process claim in a worker thread so the event loop stays responsive.
        # process_claim() runs blocking work (PaddleOCR, LLM HTTP calls), so running
        # it directly in the async task would freeze the whole server.
        initial_state = claim_data["state"]
        final_state = await asyncio.to_thread(orchestrator.process_claim, initial_state)
        
        # Update storage with final state
        claim_data["state"] = final_state
        claim_data["status"] = ClaimStatus.COMPLETED
        claim_data["processed_at"] = datetime.utcnow()
        claim_data["updated_at"] = datetime.utcnow()
        
        logger.info(f"Async processing completed for claim: {claim_id}")

        # Persist decision + trace to Supabase (best-effort)
        supabase = _get_supabase()
        if supabase:
            try:
                final_decision = final_state.get("final_decision")
                if final_decision is not None:
                    supabase.update_claim_decision(
                        claim_id=claim_id,
                        decision=final_decision.decision,
                        approved_amount=final_decision.approved_amount or 0.0,
                        rejection_reasons=[r.value for r in final_decision.rejection_reasons],
                        confidence_score=final_decision.confidence_score or 0.0
                    )
                    logger.info(
                        f"[Supabase] Decision uploaded for {claim_id}: "
                        f"{final_decision.decision.value}, "
                        f"approved=₹{final_decision.approved_amount or 0.0:.2f}"
                    )
                else:
                    # Pipeline stopped (e.g. verification failed) — still mark completed
                    supabase.update_claim_status(claim_id, ClaimStatus.COMPLETED)
                    logger.info(f"[Supabase] Claim {claim_id} marked COMPLETED (no decision)")

                # Save the full execution trace for explainability
                trace_payload = {
                    "agent_traces": final_state.get("trace", []),
                    "errors": final_state.get("errors", []),
                    "warnings": final_state.get("warnings", []),
                    "components_executed": final_state.get("components_executed", []),
                    "components_failed": final_state.get("components_failed", []),
                }
                # Ensure JSON-serializable (enums, etc.)
                import json
                trace_payload = json.loads(json.dumps(trace_payload, default=str))
                supabase.save_trace(claim_id, trace_payload)
                logger.info(f"[Supabase] Trace uploaded for {claim_id}")
            except Exception as e:
                logger.warning(f"[Supabase] Failed to upload decision/trace for {claim_id}: {e}")
        
    except Exception as e:
        logger.error(f"Error in async processing for claim {claim_id}: {e}")
        
        # Update status to FAILED
        if claim_id in _claims_storage:
            _claims_storage[claim_id]["status"] = ClaimStatus.FAILED
            _claims_storage[claim_id]["error"] = str(e)
            _claims_storage[claim_id]["updated_at"] = datetime.utcnow()

        # Reflect failure in Supabase (best-effort)
        supabase = _get_supabase()
        if supabase:
            try:
                supabase.update_claim_status(claim_id, ClaimStatus.FAILED)
            except Exception as persist_err:
                logger.warning(f"Failed to persist FAILED status for {claim_id}: {persist_err}")


# === API Endpoints ===

@router.post("/claims/submit", response_model=ClaimSubmitResponse)
async def submit_claim(
    background_tasks: BackgroundTasks,
    member_id: str = Form(...),
    policy_id: str = Form(...),
    claim_category: str = Form(...),
    treatment_date: str = Form(...),
    claimed_amount: float = Form(...),
    hospital_name: str = Form(None),
    simulate_component_failure: bool = Form(False),
    files: List[UploadFile] = File(...)
):
    """
    Submit a new claim for processing.
    
    Args:
        member_id: Member ID from policy
        policy_id: Policy ID
        claim_category: Category (CONSULTATION, DIAGNOSTIC, etc.)
        treatment_date: Date of treatment (YYYY-MM-DD)
        claimed_amount: Amount being claimed
        hospital_name: Hospital name (optional)
        files: Uploaded document files
        
    Returns:
        ClaimSubmitResponse with claim_id and status
    """
    try:
        # Validate inputs
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one document file is required"
            )
        
        # Parse claim category
        try:
            category_enum = ClaimCategory[claim_category.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid claim category: {claim_category}"
            )
        
        # Parse treatment date
        try:
            treatment_date_obj = datetime.strptime(treatment_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid treatment date format. Use YYYY-MM-DD"
            )
        
        # Generate claim ID
        claim_id = f"CLM_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8].upper()}"
        
        # Save uploaded files
        file_paths = _save_uploaded_files(claim_id, files)
        
        # Create document metadata
        document_metadata = [
            {
                "file_name": file.filename,
                "file_type": file.content_type,
                "file_size_bytes": file.size if hasattr(file, 'size') else 0
            }
            for file in files
        ]
        
        # Create initial state
        initial_state = create_initial_state(
            claim_id=claim_id,
            member_id=member_id,
            policy_id=policy_id,
            claim_category=category_enum,
            treatment_date=treatment_date_obj,
            claimed_amount=claimed_amount,
            document_file_paths=file_paths,
            document_metadata=document_metadata,
            hospital_name=hospital_name,
            simulate_component_failure=simulate_component_failure
        )
        
        # Store claim
        created_at = datetime.utcnow()
        _claims_storage[claim_id] = {
            "status": ClaimStatus.PENDING,
            "state": initial_state,
            "created_at": created_at,
            "updated_at": created_at,
            "processed_at": None
        }

        # Persist claim to Supabase (best-effort; failure won't block processing)
        supabase = _get_supabase()
        if supabase:
            try:
                supabase.create_claim(
                    claim_id=claim_id,
                    member_id=member_id,
                    policy_id=policy_id,
                    claim_category=category_enum.value,
                    treatment_date=treatment_date_obj,
                    claimed_amount=claimed_amount,
                    hospital_name=hospital_name
                )
                logger.info(f"[Supabase] Claim {claim_id} uploaded to database (status=PENDING)")
            except Exception as e:
                logger.warning(f"[Supabase] Failed to upload claim {claim_id}: {e}")
        else:
            logger.info(f"[Supabase] Service unavailable — claim {claim_id} not persisted")
        
        # Add background task for processing
        background_tasks.add_task(_process_claim_async, claim_id)
        
        logger.info(f"Claim submitted: {claim_id}")
        
        return ClaimSubmitResponse(
            claim_id=claim_id,
            status=ClaimStatus.PENDING,
            message="Claim submitted successfully. Processing will begin shortly.",
            created_at=created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting claim: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit claim: {str(e)}"
        )


@router.get("/claims/{claim_id}/status", response_model=ClaimStatusResponse)
async def get_claim_status(claim_id: str):
    """
    Get current status of a claim.
    
    Args:
        claim_id: Claim ID
        
    Returns:
        ClaimStatusResponse with current status
    """
    try:
        claim_data = _claims_storage.get(claim_id)
        
        if not claim_data:
            # Fall back to Supabase (e.g. after a server restart wiped memory)
            fallback = _status_from_supabase(claim_id)
            if fallback is not None:
                logger.info(f"[Supabase] Served status for {claim_id} from database")
                return fallback
            raise HTTPException(
                status_code=404,
                detail=f"Claim not found: {claim_id}"
            )
        
        # Determine current stage
        state = claim_data["state"]
        components_executed = state.get("components_executed", [])
        
        current_stage = None
        if claim_data["status"] == ClaimStatus.PROCESSING:
            if "DecisionMaker" in components_executed:
                current_stage = "Making Decision"
            elif "FraudDetector" in components_executed:
                current_stage = "Fraud Detection"
            elif "PolicyValidator" in components_executed:
                current_stage = "Policy Validation"
            elif "OCRExtractor" in components_executed:
                current_stage = "Data Extraction"
            elif "DocumentVerifier" in components_executed:
                current_stage = "Document Verification"
            else:
                current_stage = "Starting Processing"
        
        return ClaimStatusResponse(
            claim_id=claim_id,
            status=claim_data["status"],
            current_stage=current_stage,
            created_at=claim_data["created_at"],
            updated_at=claim_data["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting claim status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get claim status: {str(e)}"
        )


@router.get("/claims/{claim_id}/decision", response_model=ClaimDecisionResponse)
async def get_claim_decision(claim_id: str):
    """
    Get final decision for a completed claim.
    
    Args:
        claim_id: Claim ID
        
    Returns:
        ClaimDecisionResponse with decision and trace
    """
    try:
        claim_data = _claims_storage.get(claim_id)
        
        if not claim_data:
            # Fall back to Supabase (e.g. after a server restart wiped memory)
            fallback = _decision_from_supabase(claim_id)
            if fallback is not None:
                if fallback.status != ClaimStatus.COMPLETED:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Claim is not yet completed. Current status: {fallback.status.value}"
                    )
                logger.info(f"[Supabase] Served decision for {claim_id} from database")
                return fallback
            raise HTTPException(
                status_code=404,
                detail=f"Claim not found: {claim_id}"
            )
        
        # Check if processing is complete
        if claim_data["status"] != ClaimStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Claim is not yet completed. Current status: {claim_data['status'].value}"
            )
        
        state = claim_data["state"]
        
        # Build trace
        from ..models import ClaimTrace

        # Guard against missing timing data (e.g. pipeline stopped early at
        # verification, so processing_end_time was never set).
        start_time = state.get("processing_start_time")
        end_time = state.get("processing_end_time")
        processing_time = (
            end_time - start_time
            if (start_time is not None and end_time is not None)
            else 0.0
        )

        trace = ClaimTrace(
            claim_id=claim_id,
            agent_traces=state.get("trace", []),
            errors=state.get("errors", []),
            warnings=state.get("warnings", []),
            processing_time_seconds=processing_time
        )
        
        return ClaimDecisionResponse(
            claim_id=claim_id,
            status=claim_data["status"],
            decision=state.get("final_decision"),
            trace=trace,
            created_at=claim_data["created_at"],
            processed_at=claim_data.get("processed_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting claim decision: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get claim decision: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }
