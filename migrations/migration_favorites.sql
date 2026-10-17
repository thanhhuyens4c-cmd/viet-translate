-- Task 03: Phiên dịch viên đã lưu của khách thuê. An toàn để chạy nhiều lần (PostgreSQL / Supabase).
CREATE TABLE IF NOT EXISTS favorite_translator (
    id SERIAL PRIMARY KEY,
    hirer_id INTEGER NOT NULL REFERENCES "user"(id),
    translator_id INTEGER NOT NULL REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_favorite_hirer_translator UNIQUE (hirer_id, translator_id)
);
CREATE INDEX IF NOT EXISTS ix_favorite_translator_hirer_id ON favorite_translator(hirer_id);
CREATE INDEX IF NOT EXISTS ix_favorite_translator_translator_id ON favorite_translator(translator_id);
