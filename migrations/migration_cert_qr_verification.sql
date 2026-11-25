-- =============================================================================
-- Migration: Bổ sung các cột phục vụ Xác thực chứng chỉ trực tuyến qua mã QR & Digital Badge (0đ)
-- Hệ cơ sở dữ liệu: PostgreSQL 16 (VPS Production 103.161.118.158 / Supabase)
-- Tính chất: Idempotent (Chạy lặp lại an toàn, không gián đoạn dữ liệu hiện có)
-- =============================================================================

-- 1. Bổ sung các trường huy hiệu số và kiểm thực cho hồ sơ phiên dịch viên (translator_profile)
ALTER TABLE translator_profile ADD COLUMN IF NOT EXISTS has_digital_credential BOOLEAN DEFAULT FALSE;
ALTER TABLE translator_profile ADD COLUMN IF NOT EXISTS credential_public_url VARCHAR(500);
ALTER TABLE translator_profile ADD COLUMN IF NOT EXISTS credential_issuer VARCHAR(100);
ALTER TABLE translator_profile ADD COLUMN IF NOT EXISTS credential_badge_name VARCHAR(255);

-- 2. Bổ sung các trường bóc tách dữ liệu từ mã QR / Digital Badge cho hồ sơ xác minh (translator_verification)
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS certificate_id VARCHAR(100);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS verification_url VARCHAR(500);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS verification_source VARCHAR(50);
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS verification_metadata TEXT;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS is_online_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE translator_verification ADD COLUMN IF NOT EXISTS online_verified_at TIMESTAMP;

