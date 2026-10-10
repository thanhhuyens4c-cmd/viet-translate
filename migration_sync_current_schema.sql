-- Migration script to sync production database schema with current models.py
-- Run this script safely in Supabase SQL Editor.
-- It is idempotent (uses IF NOT EXISTS).

-- 1. Update "user" table
ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS admin_role VARCHAR(50),
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS avatar VARCHAR(255);

-- 2. Update "translator_schedule" table
ALTER TABLE translator_schedule
ADD COLUMN IF NOT EXISTS buffer_before_minutes INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS buffer_after_minutes INTEGER DEFAULT 30,
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'reserved',
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;

-- 3. Update "review" table
ALTER TABLE review
ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE NOT NULL;

-- 4. Create missing tables if they don't exist
-- Note: It is generally safer to let SQLAlchemy create new tables via db.create_all() (or migration_admin_security.py)
-- but adding them here ensures the SQL migration is complete.

CREATE TABLE IF NOT EXISTS report (
    id SERIAL PRIMARY KEY,
    reporter_id INTEGER NOT NULL REFERENCES "user"(id),
    target_type VARCHAR(50) NOT NULL,
    target_id INTEGER NOT NULL,
    reason VARCHAR(255) NOT NULL,
    description TEXT,
    evidence_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'new',
    related_job_id INTEGER REFERENCES job(id),
    related_contract_id INTEGER REFERENCES contract(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_report_reporter_id ON report (reporter_id);
CREATE INDEX IF NOT EXISTS ix_report_status ON report (status);
CREATE INDEX IF NOT EXISTS ix_report_created_at ON report (created_at);

CREATE TABLE IF NOT EXISTS payment_transaction (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contract(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    amount INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    payment_method VARCHAR(50),
    transaction_ref VARCHAR(100),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_payment_transaction_contract_id ON payment_transaction (contract_id);
CREATE INDEX IF NOT EXISTS ix_payment_transaction_status ON payment_transaction (status);
CREATE INDEX IF NOT EXISTS ix_payment_transaction_created_at ON payment_transaction (created_at);

CREATE TABLE IF NOT EXISTS admin_notification (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    url VARCHAR(500),
    is_read BOOLEAN DEFAULT FALSE,
    related_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_admin_notification_is_read ON admin_notification (is_read);
CREATE INDEX IF NOT EXISTS ix_admin_notification_created_at ON admin_notification (created_at);

CREATE TABLE IF NOT EXISTS login_attempt (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) NOT NULL,
    ip_address VARCHAR(64),
    success BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_login_attempt_email ON login_attempt (email);
CREATE INDEX IF NOT EXISTS ix_login_attempt_created_at ON login_attempt (created_at);

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES "user"(id),
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_id INTEGER,
    description TEXT,
    ip_address VARCHAR(64),
    user_agent VARCHAR(512),
    extra_data TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_admin_audit_log_admin_id ON admin_audit_log (admin_id);
CREATE INDEX IF NOT EXISTS ix_admin_audit_log_action ON admin_audit_log (action);
CREATE INDEX IF NOT EXISTS ix_admin_audit_log_created_at ON admin_audit_log (created_at);

-- 5. Constraint checking for translator_schedule (from migration_add_exclusion.sql)
-- Create extension if not exists
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- We cannot use IF NOT EXISTS for ADD CONSTRAINT directly in a simple query easily in all Postgres versions,
-- so we use a DO block to safely add the exclusion constraint.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_constraint 
        WHERE conname = 'no_overlapping_schedules' 
          AND conrelid = 'translator_schedule'::regclass
    ) THEN
        ALTER TABLE translator_schedule
        ADD CONSTRAINT no_overlapping_schedules
        EXCLUDE USING gist (
            translator_id WITH =,
            tsrange(
                (scheduled_date + start_time) - (COALESCE(buffer_before_minutes, 0) * interval '1 minute'),
                (scheduled_date + end_time) + (COALESCE(buffer_after_minutes, 30) * interval '1 minute')
            ) WITH &&
        )
        WHERE (status IN ('reserved', 'active'));
    END IF;
END $$;
