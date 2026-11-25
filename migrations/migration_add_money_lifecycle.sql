-- Vòng đời tiền: mốc giữ tiền, tự giải ngân, hủy và hoàn tiền, tranh chấp, vi phạm của phiên dịch viên.
-- Chạy SAU migration_add_unified_pricing.sql. An toàn để chạy lại nhiều lần trên Supabase SQL Editor.
ALTER TABLE contract ADD COLUMN IF NOT EXISTS refund_policy VARCHAR(20);
ALTER TABLE contract ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP;
ALTER TABLE contract ADD COLUMN IF NOT EXISTS started_at TIMESTAMP;
ALTER TABLE contract ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMP;
ALTER TABLE contract ADD COLUMN IF NOT EXISTS auto_release_at TIMESTAMP;
ALTER TABLE contract ADD COLUMN IF NOT EXISTS release_reminded_at TIMESTAMP;
ALTER TABLE contract ADD COLUMN IF NOT EXISTS revisions_used INTEGER DEFAULT 0;
ALTER TABLE contract ADD COLUMN IF NOT EXISTS cancelled_by VARCHAR(20);
ALTER TABLE contract ADD COLUMN IF NOT EXISTS cancel_reason VARCHAR(255);
CREATE INDEX IF NOT EXISTS ix_contract_auto_release_at ON contract (auto_release_at);

CREATE TABLE IF NOT EXISTS translator_violation (
    id SERIAL PRIMARY KEY,
    translator_id INTEGER NOT NULL REFERENCES "user"(id),
    contract_id INTEGER REFERENCES contract(id),
    points INTEGER NOT NULL DEFAULT 1,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_translator_violation_translator_id ON translator_violation (translator_id);
CREATE INDEX IF NOT EXISTS ix_translator_violation_created_at ON translator_violation (created_at);
