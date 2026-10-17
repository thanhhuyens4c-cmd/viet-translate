-- Migration: Add verification_document table for secure document vault management
-- Idempotent SQL script for PostgreSQL / Supabase SQL Editor

CREATE TABLE IF NOT EXISTS verification_document (
    id SERIAL PRIMARY KEY,
    verification_id INTEGER NOT NULL REFERENCES translator_verification(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    storage_provider VARCHAR(50) DEFAULT 'local',
    storage_path VARCHAR(500),
    file_size INTEGER DEFAULT 0,
    mime_type VARCHAR(100),
    file_extension VARCHAR(20),
    file_hash VARCHAR(64),
    status VARCHAR(50) DEFAULT 'uploaded',
    review_notes TEXT,
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_verification_doc_verif_id ON verification_document(verification_id);
CREATE INDEX IF NOT EXISTS idx_verification_doc_user_id ON verification_document(user_id);
CREATE INDEX IF NOT EXISTS idx_verification_doc_type ON verification_document(document_type);
