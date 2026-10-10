-- Bổ sung cột cho hồ sơ khách thuê (hirer_profile) để phục vụ gợi ý phiên dịch viên.
-- Idempotent. App cũng tự ADD COLUMN khi khởi động (xem _ensure_hirer_profile_columns trong app.py),
-- file này dùng khi muốn chạy tay trong Supabase SQL Editor.

ALTER TABLE hirer_profile
    ADD COLUMN IF NOT EXISTS total_reviews INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS client_type VARCHAR(30),
    ADD COLUMN IF NOT EXISTS industry VARCHAR(60),
    ADD COLUMN IF NOT EXISTS website VARCHAR(200),
    ADD COLUMN IF NOT EXISTS about TEXT,
    ADD COLUMN IF NOT EXISTS default_source_lang VARCHAR(50),
    ADD COLUMN IF NOT EXISTS default_target_lang VARCHAR(50),
    ADD COLUMN IF NOT EXISTS preferred_service_types TEXT,
    ADD COLUMN IF NOT EXISTS work_mode VARCHAR(20),
    ADD COLUMN IF NOT EXISTS hiring_frequency VARCHAR(20),
    ADD COLUMN IF NOT EXISTS typical_budget_min INTEGER,
    ADD COLUMN IF NOT EXISTS typical_budget_max INTEGER,
    ADD COLUMN IF NOT EXISTS needs_nda BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS needs_certified BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS special_requirements TEXT,
    ADD COLUMN IF NOT EXISTS tax_code VARCHAR(20);

-- Tạo hồ sơ rỗng cho khách đã đăng ký trước đây nhưng chưa có hirer_profile
INSERT INTO hirer_profile (user_id, rating, total_reviews, is_verified)
SELECT u.id, 0, 0, FALSE FROM "user" u
WHERE u.role = 'hirer' AND NOT EXISTS (SELECT 1 FROM hirer_profile h WHERE h.user_id = u.id);
