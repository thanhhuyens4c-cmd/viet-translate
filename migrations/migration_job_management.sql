-- Task 02: Quản lý yêu cầu dịch thuật của khách thuê.
-- An toàn để chạy nhiều lần (Supabase SQL Editor / PostgreSQL).
ALTER TABLE job ADD COLUMN IF NOT EXISTS specialty VARCHAR(100);
ALTER TABLE job ADD COLUMN IF NOT EXISTS word_count INTEGER;
ALTER TABLE job ADD COLUMN IF NOT EXISTS extra_requirements TEXT;
ALTER TABLE job ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
ALTER TABLE job ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP;

CREATE TABLE IF NOT EXISTS job_attachment (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES job(id),
    original_name VARCHAR(255) NOT NULL,
    stored_name VARCHAR(100) NOT NULL,
    size INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_job_attachment_job_id ON job_attachment(job_id);
