-- Tài chính admin + chi trả rút tiền.
-- App tự chạy các lệnh này lúc khởi động (_add_missing_columns, _fix_interpretation_pricing_unit);
-- file này để chạy tay trên Supabase nếu cần.

-- Bản chụp tài khoản nhận tiền rút (số tài khoản đầy đủ) và mốc admin xử lý.
ALTER TABLE payment_transaction ADD COLUMN IF NOT EXISTS payout_account TEXT;
ALTER TABLE payment_transaction ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP;

-- Phiên dịch (kể cả dịch cabin) tính theo giờ, không theo trang.
UPDATE job SET pricing_unit = 'hour'
 WHERE pricing_unit = 'page' AND category_group IS NOT NULL AND category_group <> 'translation';
UPDATE contract SET pricing_unit = 'hour'
 WHERE pricing_unit = 'page' AND refund_policy IN ('event', 'conference');

-- Ghi rõ khối lượng phiên dịch: giờ mỗi ngày / mỗi buổi, số ngày của trọn kì.
ALTER TABLE job ADD COLUMN IF NOT EXISTS hours_per_unit INTEGER;
ALTER TABLE job ADD COLUMN IF NOT EXISTS period_days INTEGER;
