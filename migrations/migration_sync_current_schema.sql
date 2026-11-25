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

-- 4. Create "saved_job" table
CREATE TABLE IF NOT EXISTS saved_job (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES job(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    CONSTRAINT uq_saved_job_user_job UNIQUE (user_id, job_id)
);
CREATE INDEX IF NOT EXISTS ix_saved_job_user_id ON saved_job (user_id);
CREATE INDEX IF NOT EXISTS ix_saved_job_job_id ON saved_job (job_id);

-- 5. Add proposal tracking columns
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='proposal' AND column_name='updated_at') THEN
        ALTER TABLE proposal ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='proposal' AND column_name='client_note') THEN
        ALTER TABLE proposal ADD COLUMN client_note TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='proposal' AND column_name='withdrawn_reason') THEN
        ALTER TABLE proposal ADD COLUMN withdrawn_reason VARCHAR(255);
    END IF;
END $$;

-- =============================================================================
-- 6. Phân hệ Tài khoản Phiên dịch viên (Mục V)
-- =============================================================================

-- 6.1 Mở rộng bảng "user"
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS date_of_birth VARCHAR(20);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_public_profile BOOLEAN DEFAULT TRUE;

-- 6.2 Tạo bảng InterpreterService (Năng lực & Bảng giá - Mục 5.2)
CREATE TABLE IF NOT EXISTS interpreter_service (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    source_lang VARCHAR(100) NOT NULL,
    target_lang VARCHAR(100) NOT NULL,
    interpreting_type VARCHAR(100) NOT NULL,
    specialization VARCHAR(255),
    hourly_rate DOUBLE PRECISION,
    session_rate DOUBLE PRECISION,
    currency VARCHAR(10) DEFAULT 'VND',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_interpreter_service_user_id ON interpreter_service (user_id);
CREATE INDEX IF NOT EXISTS ix_interpreter_service_is_active ON interpreter_service (is_active);

-- 6.3 Tạo bảng InterpreterPreference (Tiêu chí nhận việc - Mục 5.4)
CREATE TABLE IF NOT EXISTS interpreter_preference (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
    languages TEXT,
    specializations TEXT,
    work_mode VARCHAR(50) DEFAULT 'both',
    min_rate DOUBLE PRECISION,
    max_rate DOUBLE PRECISION,
    allow_outside_rate BOOLEAN DEFAULT FALSE,
    available_hours TEXT,
    locations TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_interpreter_preference_user_id ON interpreter_preference (user_id);
ALTER TABLE interpreter_preference ADD COLUMN IF NOT EXISTS locations TEXT;

-- 6.4 Tạo bảng NotificationSetting (Cài đặt thông báo - Mục 5.6.1)
CREATE TABLE IF NOT EXISTS notification_setting (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
    notify_job_match BOOLEAN DEFAULT TRUE,
    notify_application_update BOOLEAN DEFAULT TRUE,
    notify_profile_view BOOLEAN DEFAULT TRUE,
    notify_schedule_reminder BOOLEAN DEFAULT TRUE,
    reminder_time_60m BOOLEAN DEFAULT TRUE,
    reminder_time_30m BOOLEAN DEFAULT TRUE,
    reminder_time_15m BOOLEAN DEFAULT FALSE,
    notify_income_update BOOLEAN DEFAULT TRUE,
    notify_security_alert BOOLEAN DEFAULT TRUE,
    notify_marketing BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_job_match BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_application_update BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_profile_view BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_schedule_reminder BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS reminder_time_60m BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS reminder_time_30m BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS reminder_time_15m BOOLEAN DEFAULT FALSE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_income_update BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_security_alert BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_marketing BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS ix_notification_setting_user_id ON notification_setting (user_id);

-- 6.5 Tạo bảng UserSession (Quản lý phiên - Mục 5.6.2)
CREATE TABLE IF NOT EXISTS user_session (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    device_name VARCHAR(255),
    ip_address VARCHAR(50),
    last_active TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_user_session_user_id ON user_session (user_id);
CREATE INDEX IF NOT EXISTS ix_user_session_session_id ON user_session (session_id);

-- 6.6 Tạo bảng SupportTicket (Yêu cầu hỗ trợ - Mục 5.7.3)
CREATE TABLE IF NOT EXISTS support_ticket (
    id SERIAL PRIMARY KEY,
    ticket_code VARCHAR(50) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    attachment_url TEXT,
    status VARCHAR(50) DEFAULT 'open',
    admin_reply TEXT,
    admin_reply_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_support_ticket_user_id ON support_ticket (user_id);
CREATE INDEX IF NOT EXISTS ix_support_ticket_ticket_code ON support_ticket (ticket_code);
CREATE INDEX IF NOT EXISTS ix_support_ticket_status ON support_ticket (status);



