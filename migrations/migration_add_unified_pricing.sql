-- Gộp giá dịch tài liệu và phiên dịch về một mô hình: số lượng x đơn giá, một bảng giao dịch.
-- An toàn để chạy trực tiếp trên Supabase SQL Editor (chạy lại nhiều lần không lỗi).
ALTER TABLE job ADD COLUMN IF NOT EXISTS pricing_unit VARCHAR(20);
ALTER TABLE job ADD COLUMN IF NOT EXISTS quantity INTEGER;

ALTER TABLE contract ADD COLUMN IF NOT EXISTS pricing_unit VARCHAR(20);
ALTER TABLE contract ADD COLUMN IF NOT EXISTS quantity INTEGER;
ALTER TABLE contract ADD COLUMN IF NOT EXISTS unit_price INTEGER;
ALTER TABLE contract ADD COLUMN IF NOT EXISTS client_fee INTEGER;
ALTER TABLE contract ADD COLUMN IF NOT EXISTS commission INTEGER;
ALTER TABLE contract ADD COLUMN IF NOT EXISTS translator_net INTEGER;

ALTER TABLE payment_transaction ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'deposit';
ALTER TABLE payment_transaction ADD COLUMN IF NOT EXISTS payee_id INTEGER REFERENCES "user"(id);
CREATE INDEX IF NOT EXISTS ix_payment_transaction_kind ON payment_transaction (kind);
CREATE INDEX IF NOT EXISTS ix_payment_transaction_payee_id ON payment_transaction (payee_id);
