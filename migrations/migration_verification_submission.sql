-- Migration: Add submission columns and verification_submission_version table
-- Idempotent SQL script for PostgreSQL / Supabase SQL Editor

ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS submission_version INTEGER DEFAULT 0;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS submitted_snapshot TEXT;

CREATE TABLE IF NOT EXISTS verification_submission_version (
    id SERIAL PRIMARY KEY,
    verification_id INTEGER NOT NULL REFERENCES translator_verification(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pending',
    snapshot_data TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(50),
    user_agent VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_verif_sub_ver_verif_id ON verification_submission_version(verification_id);
CREATE INDEX IF NOT EXISTS idx_verif_sub_ver_user_id ON verification_submission_version(user_id);
CREATE INDEX IF NOT EXISTS idx_verif_sub_ver_submitted_at ON verification_submission_version(submitted_at);
