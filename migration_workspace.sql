-- Phòng làm việc (workspace): các bảng mới cho quy trình nhận việc → thực hiện → nghiệm thu → giải ngân.
-- App tự tạo các bảng này qua db.create_all() khi khởi động; file này dùng khi muốn chạy tay trên Supabase.
-- Không thay đổi bảng cũ. Contract.status dùng thêm các giá trị: funded, revision, submitted, disputed.

CREATE TABLE IF NOT EXISTS contract_workflow (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL UNIQUE REFERENCES contract(id),
    work_mode VARCHAR(20) NOT NULL DEFAULT 'document',
    progress_percent INTEGER NOT NULL DEFAULT 0,
    funded_at TIMESTAMP, accept_deadline TIMESTAMP, accepted_at TIMESTAMP,
    last_progress_at TIMESTAMP, progress_requested_at TIMESTAMP,
    submitted_at TIMESTAMP, review_deadline TIMESTAMP,
    revision_count INTEGER NOT NULL DEFAULT 0,
    completed_at TIMESTAMP, auto_approved BOOLEAN NOT NULL DEFAULT FALSE,
    released_at TIMESTAMP, payout_amount INTEGER, platform_fee INTEGER,
    disputed_at TIMESTAMP, dispute_by INTEGER REFERENCES "user"(id), dispute_reason TEXT, dispute_prev_status VARCHAR(50),
    cancelled_at TIMESTAMP, cancel_reason TEXT, refunded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_contract_workflow_contract_id ON contract_workflow (contract_id);

CREATE TABLE IF NOT EXISTS contract_event (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contract(id),
    actor_id INTEGER REFERENCES "user"(id),
    type VARCHAR(40) NOT NULL,
    note TEXT,
    data TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_contract_event_contract_id ON contract_event (contract_id);
CREATE INDEX IF NOT EXISTS ix_contract_event_created_at ON contract_event (created_at);

CREATE TABLE IF NOT EXISTS work_submission (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contract(id),
    round_no INTEGER NOT NULL DEFAULT 1,
    note TEXT,
    actual_hours DOUBLE PRECISION,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_work_submission_contract_id ON work_submission (contract_id);

CREATE TABLE IF NOT EXISTS attendance_session (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contract(id),
    checkin_at TIMESTAMP NOT NULL,
    checkin_lat DOUBLE PRECISION, checkin_lng DOUBLE PRECISION, checkin_note VARCHAR(500),
    checkout_at TIMESTAMP, checkout_note VARCHAR(500),
    confirmed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_attendance_session_contract_id ON attendance_session (contract_id);

CREATE TABLE IF NOT EXISTS workspace_file (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contract(id),
    uploader_id INTEGER NOT NULL REFERENCES "user"(id),
    category VARCHAR(20) NOT NULL DEFAULT 'reference',
    original_name VARCHAR(255) NOT NULL,
    stored_name VARCHAR(255) NOT NULL UNIQUE,
    size INTEGER DEFAULT 0,
    message_id INTEGER REFERENCES message(id),
    event_id INTEGER REFERENCES contract_event(id),
    submission_id INTEGER REFERENCES work_submission(id),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_workspace_file_contract_id ON workspace_file (contract_id);
