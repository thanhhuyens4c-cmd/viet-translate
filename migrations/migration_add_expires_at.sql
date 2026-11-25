-- Thêm cột expires_at vào bảng translator_schedule để hỗ trợ anti-double-booking expiry
-- Lệnh này an toàn để chạy trực tiếp trên Supabase SQL Editor.
ALTER TABLE translator_schedule ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;
