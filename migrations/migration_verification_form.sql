-- Migration: Add multi-step verification form columns to translator_verification table
-- Idempotent SQL script for PostgreSQL / Supabase SQL Editor

ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS current_step INTEGER DEFAULT 1;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS draft_data TEXT;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS full_name VARCHAR(100);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS gender VARCHAR(20);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS dob VARCHAR(20);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS location VARCHAR(100);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS source_language VARCHAR(100);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS target_language VARCHAR(100);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS interpreting_direction VARCHAR(50);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS language_proficiency VARCHAR(50);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS specializations TEXT;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS interpreting_types TEXT;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS education_level VARCHAR(100);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS university VARCHAR(255);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS major VARCHAR(255);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS cert_year INTEGER;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS current_position VARCHAR(255);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS notable_clients TEXT;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS featured_projects TEXT;
