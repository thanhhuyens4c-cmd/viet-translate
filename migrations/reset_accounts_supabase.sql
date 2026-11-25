-- reset_accounts_supabase.sql
-- Xóa toàn bộ tài khoản khách thuê / phiên dịch viên (GIỮ admin) và dữ liệu đi kèm trên Supabase.
-- KHÔNG THỂ HOÀN TÁC. Hãy sao lưu trước: Supabase Dashboard -> Database -> Backups.
-- Chạy trong Supabase Dashboard -> SQL Editor. Toàn bộ chạy trong một giao dịch: lỗi thì không xóa gì.

BEGIN;

-- Bước 1: xem trước số tài khoản sẽ bị xóa (kiểm tra rồi mới chạy tiếp)
SELECT count(*) AS se_bi_xoa FROM "user" WHERE is_admin IS NOT TRUE;
SELECT count(*) AS admin_duoc_giu FROM "user" WHERE is_admin IS TRUE;

-- Bước 2: xóa dữ liệu phụ thuộc (một câu TRUNCATE để bỏ qua thứ tự khóa ngoại)
-- Giữ lại: "user" (admin) và admin_audit_log.
TRUNCATE TABLE
    verification_document,
    translator_verification,
    payment_transaction,
    report,
    review,
    deliverable,
    direct_message,
    message,
    notification,
    admin_notification,
    contract,
    proposal,
    job_schedule,
    job,
    service,
    translator_schedule,
    translator_preference,
    translator_profile,
    hirer_profile,
    login_attempt
RESTART IDENTITY;

-- Bước 3: xóa tài khoản không phải admin
DELETE FROM "user" WHERE is_admin IS NOT TRUE;

SELECT count(*) AS tai_khoan_con_lai FROM "user";

COMMIT;
