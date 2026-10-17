-- Task 05: Quản lý dự án của khách thuê. An toàn để chạy nhiều lần (PostgreSQL / Supabase).
CREATE TABLE IF NOT EXISTS contract_event (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contract(id),
    actor_id INTEGER REFERENCES "user"(id),
    event_type VARCHAR(40) NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_contract_event_contract_id ON contract_event(contract_id);
