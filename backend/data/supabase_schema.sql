-- MediClaim Supabase Schema
-- Run this in your Supabase SQL Editor to set up the database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===================================
-- Claims Table
-- ===================================
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id VARCHAR(50) UNIQUE NOT NULL,
    member_id VARCHAR(50) NOT NULL,
    policy_id VARCHAR(50) NOT NULL,
    
    -- Claim details
    claim_category VARCHAR(50) NOT NULL,
    treatment_date DATE NOT NULL,
    claimed_amount DECIMAL(10, 2) NOT NULL,
    hospital_name VARCHAR(255),
    
    -- Processing status
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    -- Status values: PENDING, PROCESSING, COMPLETED, FAILED
    
    -- Decision results
    decision VARCHAR(50),
    -- Decision values: APPROVED, PARTIAL, REJECTED, MANUAL_REVIEW
    approved_amount DECIMAL(10, 2),
    rejection_reasons TEXT[],
    confidence_score DECIMAL(3, 2),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    
    -- Indexes
    CONSTRAINT claims_status_check CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    CONSTRAINT claims_decision_check CHECK (decision IN ('APPROVED', 'PARTIAL', 'REJECTED', 'MANUAL_REVIEW', NULL))
);

-- Create indexes for performance
CREATE INDEX idx_claims_member_id ON claims(member_id);
CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_claims_created_at ON claims(created_at DESC);
CREATE INDEX idx_claims_treatment_date ON claims(treatment_date);

-- ===================================
-- Documents Table
-- ===================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    
    -- Document details
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,  -- Supabase Storage path
    file_type VARCHAR(100) NOT NULL,  -- MIME type
    document_type VARCHAR(50),  -- PRESCRIPTION, HOSPITAL_BILL, LAB_REPORT, etc.
    file_size_bytes INTEGER,
    
    -- OCR status
    ocr_status VARCHAR(50) DEFAULT 'PENDING',
    -- OCR status values: PENDING, PROCESSING, COMPLETED, FAILED
    ocr_confidence DECIMAL(3, 2),
    
    -- Metadata
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    
    CONSTRAINT documents_ocr_status_check CHECK (ocr_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'))
);

-- Create indexes
CREATE INDEX idx_documents_claim_id ON documents(claim_id);
CREATE INDEX idx_documents_ocr_status ON documents(ocr_status);

-- ===================================
-- Claim Traces Table (for explainability)
-- ===================================
CREATE TABLE IF NOT EXISTS claim_traces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    
    -- Trace data (stored as JSONB for flexibility)
    trace_data JSONB NOT NULL,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Index for JSON queries
    CONSTRAINT claim_traces_claim_id_unique UNIQUE (claim_id)
);

-- Create index for fast claim lookup
CREATE INDEX idx_claim_traces_claim_id ON claim_traces(claim_id);

-- ===================================
-- OCR Results Table (detailed extraction)
-- ===================================
CREATE TABLE IF NOT EXISTS ocr_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Extracted data (JSONB for flexibility)
    extracted_data JSONB NOT NULL,
    raw_text TEXT,
    
    -- Field confidence scores
    field_confidence JSONB,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT ocr_results_document_id_unique UNIQUE (document_id)
);

-- Create index
CREATE INDEX idx_ocr_results_document_id ON ocr_results(document_id);

-- ===================================
-- Audit Logs Table
-- ===================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id VARCHAR(50),
    event_type VARCHAR(100) NOT NULL,
    agent_name VARCHAR(100),
    member_id VARCHAR(50),
    details JSONB,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for audit queries
CREATE INDEX idx_audit_logs_claim_id ON audit_logs(claim_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);

-- ===================================
-- Policy Config Cache (optional - for versioning)
-- ===================================
CREATE TABLE IF NOT EXISTS policy_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id VARCHAR(50) UNIQUE NOT NULL,
    policy_data JSONB NOT NULL,
    version VARCHAR(20) NOT NULL,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_active BOOLEAN DEFAULT true,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index
CREATE INDEX idx_policy_config_active ON policy_config(is_active, effective_date DESC);

-- ===================================
-- Members Cache (optional - for quick lookups)
-- ===================================
CREATE TABLE IF NOT EXISTS members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    member_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(10),
    relationship VARCHAR(50),
    join_date DATE NOT NULL,
    primary_member_id VARCHAR(50),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index
CREATE INDEX idx_members_member_id ON members(member_id);

-- ===================================
-- Update Trigger for updated_at
-- ===================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to relevant tables
CREATE TRIGGER update_claims_updated_at BEFORE UPDATE ON claims
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_policy_config_updated_at BEFORE UPDATE ON policy_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_members_updated_at BEFORE UPDATE ON members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===================================
-- Storage Bucket Setup
-- ===================================
-- Run this in Supabase Dashboard > Storage or via SQL:
-- 
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('claim-documents', 'claim-documents', false);
-- 
-- Then set up RLS policies as needed for your security requirements.
