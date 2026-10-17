-- Task 04: Quản lý báo giá của khách thuê. An toàn để chạy nhiều lần (PostgreSQL / Supabase).
ALTER TABLE proposal ADD COLUMN IF NOT EXISTS scope TEXT;
ALTER TABLE proposal ADD COLUMN IF NOT EXISTS delivery_terms TEXT;
ALTER TABLE proposal ADD COLUMN IF NOT EXISTS revision_terms TEXT;
ALTER TABLE proposal ADD COLUMN IF NOT EXISTS valid_until DATE;
ALTER TABLE proposal ADD COLUMN IF NOT EXISTS responded_at TIMESTAMP;
ALTER TABLE proposal ADD COLUMN IF NOT EXISTS response_note TEXT;
