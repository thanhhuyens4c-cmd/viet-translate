-- Migration Task 1: Email Verification and Checklist Data
-- Target Database: PostgreSQL

-- 1. Add email_verified to user table
ALTER TABLE "user" ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
-- For existing users, you may want to set them to true if you don't want to lock them out, but according to plan, we don't automatically mark them verified unless justified. We will leave them as FALSE and let them verify, OR manually migrate active users. For safety, we just add the column.

-- 2. Create EmailVerificationToken table
CREATE TABLE email_verification_token (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    token_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    is_used BOOLEAN DEFAULT FALSE
);

CREATE INDEX ix_email_verification_token_user_id ON email_verification_token (user_id);

-- 3. Add checklist_data to translator_verification table
ALTER TABLE translator_verification ADD COLUMN checklist_data TEXT;

-- Rollback plan:
-- ALTER TABLE translator_verification DROP COLUMN checklist_data;
-- DROP TABLE email_verification_token;
-- ALTER TABLE "user" DROP COLUMN email_verified;
