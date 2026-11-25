-- Migration: Add translator_verification table
-- Safe, idempotent script for Supabase PostgreSQL Editor.

CREATE TABLE IF NOT EXISTS translator_verification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    cv_filename VARCHAR(255),
    cv_url VARCHAR(500),
    certificate_filename VARCHAR(255),
    certificate_url VARCHAR(500),
    id_card_filename VARCHAR(255),
    id_card_url VARCHAR(500),
    certificate_type VARCHAR(100),
    certificate_name VARCHAR(255),
    primary_language VARCHAR(100),
    experience_years INTEGER DEFAULT 0,
    notes TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    rejection_reason TEXT,
    reviewed_by INTEGER REFERENCES "user"(id),
    reviewed_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_translator_verification_user_id ON translator_verification (user_id);
CREATE INDEX IF NOT EXISTS ix_translator_verification_status ON translator_verification (status);
CREATE INDEX IF NOT EXISTS ix_translator_verification_created_at ON translator_verification (created_at);
