-- =============================================================================
-- Migration: Add Professional Profile & Privacy Settings to translator_profile
-- Supports: Work modes, language pairs, interpreting direction, education,
--           certificates, experience, public CV visibility, and profile privacy.
-- Safe & Idempotent: Uses ADD COLUMN IF NOT EXISTS.
-- =============================================================================

ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT TRUE;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS is_cv_public BOOLEAN DEFAULT FALSE;

ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS source_language VARCHAR(100);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS target_language VARCHAR(100);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS interpreting_direction VARCHAR(50);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS language_proficiency VARCHAR(50);

ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS specializations TEXT;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS interpreting_types TEXT;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS work_modes VARCHAR(255);

ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS education_level VARCHAR(100);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS university VARCHAR(255);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS major VARCHAR(255);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS cert_name VARCHAR(255);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS cert_year INTEGER;

ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS experience_years INTEGER DEFAULT 0;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS current_position VARCHAR(255);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS notable_clients TEXT;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS featured_projects TEXT;
