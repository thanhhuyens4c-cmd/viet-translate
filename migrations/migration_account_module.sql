-- =============================================================================
-- Migration: Phân hệ Tài khoản Phiên dịch viên (Mục V)
-- Mô tả:
-- 1. Bổ sung trường cho bảng User: bio, date_of_birth, city, is_public_profile
-- 2. Tạo bảng InterpreterService (Năng lực & Bảng giá - Mục 5.2)
-- 3. Tạo bảng InterpreterPreference (Tiêu chí nhận việc - Mục 5.4)
-- 4. Tạo bảng NotificationSetting (Cài đặt thông báo - Mục 5.6.1)
-- 5. Tạo bảng UserSession (Quản lý phiên đăng nhập & Thiết bị - Mục 5.6.2)
-- 6. Tạo bảng SupportTicket (Yêu cầu hỗ trợ & Khiếu nại - Mục 5.7.3)
-- Ràng buộc: Tuyệt đối không can thiệp các bảng KYC/Verification.
-- Tính chất: An toàn & Idempotent (IF NOT EXISTS).
-- =============================================================================

-- 1. Mở rộng bảng "user" hiện có
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS date_of_birth VARCHAR(20);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_public_profile BOOLEAN DEFAULT TRUE;

-- 2. Tạo bảng InterpreterService (Năng lực & Bảng giá - Mục 5.2)
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

-- 3. Tạo bảng InterpreterPreference (Tiêu chí nhận việc - Mục 5.4)
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

-- 4. Tạo bảng NotificationSetting (Cài đặt thông báo - Mục 5.6.1)
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

ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_profile_view BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS reminder_time_60m BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS reminder_time_30m BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS reminder_time_15m BOOLEAN DEFAULT FALSE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_income_update BOOLEAN DEFAULT TRUE;
ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_security_alert BOOLEAN DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS ix_notification_setting_user_id ON notification_setting (user_id);

-- 5. Tạo bảng UserSession (Quản lý phiên - Mục 5.6.2)
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

-- 6. Tạo bảng SupportTicket (Yêu cầu hỗ trợ - Mục 5.7.3)
CREATE TABLE IF NOT EXISTS support_ticket (
    id SERIAL PRIMARY KEY,
    ticket_code VARCHAR(50) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    attachment_url VARCHAR(500),
    status VARCHAR(30) DEFAULT 'open',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_support_ticket_user_id ON support_ticket (user_id);
CREATE INDEX IF NOT EXISTS ix_support_ticket_ticket_code ON support_ticket (ticket_code);
CREATE INDEX IF NOT EXISTS ix_support_ticket_status ON support_ticket (status);
CREATE INDEX IF NOT EXISTS ix_support_ticket_created_at ON support_ticket (created_at);
