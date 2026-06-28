"""
Supabase Client Service

Handles all database operations and file storage via Supabase.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pathlib import Path

from supabase import create_client, Client
from postgrest.exceptions import APIError

from ..config import settings
from ..models import ClaimStatus, ClaimDecision
from ..exceptions import ConfigurationError, NotFoundError
from ..loggers import logger


class SupabaseService:
    """
    Service for interacting with Supabase database and storage.
    
    Handles:
    - Claim CRUD operations
    - Document storage and retrieval
    - Trace storage
    - OCR results storage
    - Claim history queries
    - Audit logging
    """
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client"""
        try:
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise ConfigurationError(f"Supabase initialization failed: {e}")
    
    @property
    def client(self) -> Client:
        """Get Supabase client"""
        if self._client is None:
            raise ConfigurationError("Supabase client not initialized")
        return self._client
    
    # === Claim Operations ===
    
    def create_claim(
        self,
        claim_id: str,
        member_id: str,
        policy_id: str,
        claim_category: str,
        treatment_date: date,
        claimed_amount: float,
        hospital_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new claim record.
        
        Args:
            claim_id: Unique claim identifier
            member_id: Member ID
            policy_id: Policy ID
            claim_category: Claim category
            treatment_date: Date of treatment
            claimed_amount: Amount being claimed
            hospital_name: Hospital name (optional)
            
        Returns:
            Created claim record
        """
        try:
            data = {
                "claim_id": claim_id,
                "member_id": member_id,
                "policy_id": policy_id,
                "claim_category": claim_category,
                "treatment_date": treatment_date.isoformat(),
                "claimed_amount": claimed_amount,
                "hospital_name": hospital_name,
                "status": ClaimStatus.PENDING.value
            }
            
            result = self.client.table("claims").insert(data).execute()
            
            logger.info(f"Created claim record: {claim_id}")
            return result.data[0] if result.data else {}
            
        except APIError as e:
            logger.error(f"Failed to create claim: {e}")
            raise
    
    def update_claim_status(
        self,
        claim_id: str,
        status: ClaimStatus
    ) -> Dict[str, Any]:
        """Update claim status"""
        try:
            result = self.client.table("claims").update({
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("claim_id", claim_id).execute()
            
            logger.info(f"Updated claim {claim_id} status to {status.value}")
            return result.data[0] if result.data else {}
            
        except APIError as e:
            logger.error(f"Failed to update claim status: {e}")
            raise
    
    def update_claim_decision(
        self,
        claim_id: str,
        decision: ClaimDecision,
        approved_amount: float,
        rejection_reasons: List[str],
        confidence_score: float
    ) -> Dict[str, Any]:
        """Update claim with final decision"""
        try:
            result = self.client.table("claims").update({
                "status": ClaimStatus.COMPLETED.value,
                "decision": decision.value,
                "approved_amount": approved_amount,
                "rejection_reasons": rejection_reasons,
                "confidence_score": confidence_score,
                "processed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("claim_id", claim_id).execute()
            
            logger.info(f"Updated claim {claim_id} with decision: {decision.value}")
            return result.data[0] if result.data else {}
            
        except APIError as e:
            logger.error(f"Failed to update claim decision: {e}")
            raise
    
    def get_claim(self, claim_id: str) -> Dict[str, Any]:
        """Get claim by claim_id"""
        try:
            result = self.client.table("claims").select("*").eq(
                "claim_id", claim_id
            ).execute()
            
            if not result.data:
                raise NotFoundError("Claim", claim_id)
            
            return result.data[0]
            
        except APIError as e:
            logger.error(f"Failed to get claim: {e}")
            raise
    
    def get_claim_history(
        self,
        member_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get claim history for a member.
        
        Args:
            member_id: Member ID
            limit: Maximum number of claims to return
            
        Returns:
            List of past claims
        """
        try:
            result = self.client.table("claims").select(
                "claim_id, treatment_date, claimed_amount, approved_amount, "
                "decision, claim_category, hospital_name, created_at"
            ).eq(
                "member_id", member_id
            ).order(
                "created_at", desc=True
            ).limit(limit).execute()
            
            return result.data if result.data else []
            
        except APIError as e:
            logger.error(f"Failed to get claim history: {e}")
            return []
    
    def get_ytd_claims_amount(
        self,
        member_id: str,
        category: Optional[str] = None
    ) -> float:
        """
        Get year-to-date claims amount for a member.
        
        Args:
            member_id: Member ID
            category: Optional category filter
            
        Returns:
            Total YTD amount
        """
        try:
            current_year = datetime.now().year
            query = self.client.table("claims").select(
                "approved_amount"
            ).eq(
                "member_id", member_id
            ).eq(
                "status", ClaimStatus.COMPLETED.value
            ).gte(
                "treatment_date", f"{current_year}-01-01"
            )
            
            if category:
                query = query.eq("claim_category", category)
            
            result = query.execute()
            
            if not result.data:
                return 0.0
            
            total = sum(
                claim.get("approved_amount", 0.0) or 0.0
                for claim in result.data
            )
            
            return total
            
        except APIError as e:
            logger.error(f"Failed to get YTD claims: {e}")
            return 0.0
    
    # === Document Operations ===
    
    def upload_document(
        self,
        claim_id: str,
        file_path: str,
        file_name: str,
        file_type: str,
        document_type: Optional[str] = None
    ) -> str:
        """
        Upload document to Supabase Storage.
        
        Args:
            claim_id: Claim ID
            file_path: Local file path
            file_name: Original file name
            file_type: MIME type
            document_type: Document type (PRESCRIPTION, etc.)
            
        Returns:
            Storage path
        """
        try:
            # Create storage path: claims/{claim_id}/{filename}
            storage_path = f"claims/{claim_id}/{file_name}"
            
            # Read file
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Upload to storage
            self.client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
                storage_path,
                file_data,
                file_options={"content-type": file_type}
            )
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create document record
            # First, get the claim UUID from claim_id
            claim_result = self.client.table("claims").select("id").eq(
                "claim_id", claim_id
            ).execute()
            
            if not claim_result.data:
                raise NotFoundError("Claim", claim_id)
            
            claim_uuid = claim_result.data[0]["id"]
            
            # Insert document record
            self.client.table("documents").insert({
                "claim_id": claim_uuid,
                "file_name": file_name,
                "file_path": storage_path,
                "file_type": file_type,
                "document_type": document_type,
                "file_size_bytes": file_size,
                "ocr_status": "PENDING"
            }).execute()
            
            logger.info(f"Uploaded document: {storage_path}")
            return storage_path
            
        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            raise
    
    def get_document_url(self, storage_path: str) -> str:
        """Get public URL for document"""
        try:
            result = self.client.storage.from_(
                settings.SUPABASE_STORAGE_BUCKET
            ).get_public_url(storage_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get document URL: {e}")
            raise
    
    def update_document_ocr_status(
        self,
        document_id: str,
        status: str,
        confidence: Optional[float] = None
    ):
        """Update OCR status for document"""
        try:
            data = {
                "ocr_status": status,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            if confidence is not None:
                data["ocr_confidence"] = confidence
            
            self.client.table("documents").update(data).eq(
                "id", document_id
            ).execute()
            
            logger.info(f"Updated document OCR status: {document_id}")
            
        except APIError as e:
            logger.error(f"Failed to update document OCR status: {e}")
    
    # === Trace Operations ===
    
    def save_trace(self, claim_id: str, trace_data: Dict[str, Any]):
        """
        Save claim processing trace.
        
        Args:
            claim_id: Claim ID
            trace_data: Complete trace data
        """
        try:
            # Get claim UUID
            claim_result = self.client.table("claims").select("id").eq(
                "claim_id", claim_id
            ).execute()
            
            if not claim_result.data:
                raise NotFoundError("Claim", claim_id)
            
            claim_uuid = claim_result.data[0]["id"]
            
            # Insert or update trace
            # Check if trace exists
            existing = self.client.table("claim_traces").select("id").eq(
                "claim_id", claim_uuid
            ).execute()
            
            if existing.data:
                # Update
                self.client.table("claim_traces").update({
                    "trace_data": trace_data
                }).eq("claim_id", claim_uuid).execute()
            else:
                # Insert
                self.client.table("claim_traces").insert({
                    "claim_id": claim_uuid,
                    "trace_data": trace_data
                }).execute()
            
            logger.info(f"Saved trace for claim: {claim_id}")
            
        except APIError as e:
            logger.error(f"Failed to save trace: {e}")
    
    def get_trace(self, claim_id: str) -> Optional[Dict[str, Any]]:
        """Get trace for a claim"""
        try:
            # Get claim UUID
            claim_result = self.client.table("claims").select("id").eq(
                "claim_id", claim_id
            ).execute()
            
            if not claim_result.data:
                return None
            
            claim_uuid = claim_result.data[0]["id"]
            
            # Get trace
            result = self.client.table("claim_traces").select("trace_data").eq(
                "claim_id", claim_uuid
            ).execute()
            
            if result.data:
                return result.data[0].get("trace_data")
            
            return None
            
        except APIError as e:
            logger.error(f"Failed to get trace: {e}")
            return None
    
    # === OCR Results ===
    
    def save_ocr_result(
        self,
        document_id: str,
        extracted_data: Dict[str, Any],
        raw_text: str,
        field_confidence: Dict[str, float]
    ):
        """Save OCR extraction results"""
        try:
            self.client.table("ocr_results").insert({
                "document_id": document_id,
                "extracted_data": extracted_data,
                "raw_text": raw_text,
                "field_confidence": field_confidence
            }).execute()
            
            logger.info(f"Saved OCR results for document: {document_id}")
            
        except APIError as e:
            logger.error(f"Failed to save OCR results: {e}")
    
    # === Audit Logging ===
    
    def log_audit_event(
        self,
        claim_id: str,
        event_type: str,
        agent_name: Optional[str] = None,
        member_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log audit event to database"""
        try:
            self.client.table("audit_logs").insert({
                "claim_id": claim_id,
                "event_type": event_type,
                "agent_name": agent_name,
                "member_id": member_id,
                "details": details or {}
            }).execute()
            
        except APIError as e:
            logger.error(f"Failed to log audit event: {e}")


# Singleton instance
_supabase_service: Optional[SupabaseService] = None


def get_supabase_service() -> SupabaseService:
    """Get or create SupabaseService singleton"""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service
