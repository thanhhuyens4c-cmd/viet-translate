-- Ví cá nhân: nạp ví, trả hợp đồng bằng ví, từ chối rút tiền.
-- Idempotent — chạy an toàn trong Supabase SQL Editor. App cũng tự áp dụng khi khởi động.

-- Giao dịch nạp ví (kind = 'topup') không gắn hợp đồng.
ALTER TABLE payment_transaction ALTER COLUMN contract_id DROP NOT NULL;

-- Ghi chú của admin, ví dụ lý do từ chối rút tiền (status = 'rejected').
ALTER TABLE payment_transaction ADD COLUMN IF NOT EXISTS note VARCHAR(255);
