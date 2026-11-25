-- Migration: Ví cá nhân (wallet) cho khách thuê và phiên dịch viên.
-- Idempotent — chạy an toàn trong Supabase SQL Editor.
-- (db.create_all() khi khởi động app cũng tự tạo 2 bảng này nếu chưa có.)

CREATE TABLE IF NOT EXISTS wallet (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
    balance BIGINT NOT NULL DEFAULT 0,
    pending_balance BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT ck_wallet_balance_non_negative CHECK (balance >= 0 AND pending_balance >= 0)
);
CREATE INDEX IF NOT EXISTS ix_wallet_user_id ON wallet (user_id);

CREATE TABLE IF NOT EXISTS wallet_transaction (
    id SERIAL PRIMARY KEY,
    wallet_id INTEGER NOT NULL REFERENCES wallet(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL,
    amount BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    description VARCHAR(255),
    contract_id INTEGER REFERENCES contract(id),
    bank_name VARCHAR(100),
    bank_account VARCHAR(50),
    bank_holder VARCHAR(100),
    admin_note VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_wallet_transaction_wallet_id ON wallet_transaction (wallet_id);
CREATE INDEX IF NOT EXISTS ix_wallet_transaction_type ON wallet_transaction (type);
CREATE INDEX IF NOT EXISTS ix_wallet_transaction_status ON wallet_transaction (status);
CREATE INDEX IF NOT EXISTS ix_wallet_transaction_contract_id ON wallet_transaction (contract_id);
CREATE INDEX IF NOT EXISTS ix_wallet_transaction_created_at ON wallet_transaction (created_at);
