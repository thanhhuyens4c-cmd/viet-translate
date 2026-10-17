-- ============================================================
-- MIGRATION: TASK 1 -- SUPABASE SCHEMA FOUNDATION
-- VietTranslate
-- Ngay tao: 2026-10-06
-- Muc dich:
--   1. Tao bang job_schedule (ho tro multi-day voi gio rieng tung ngay)
--   2. Sua notification.related_job_id FK -> ON DELETE SET NULL
--      (ngan ForeignKeyViolation khi soft-remove job)
--   3. Bo UNIQUE(contract_id) tren translator_schedule
--      (cho phep 1 contract co nhieu schedule entry - multi-day)
--
-- QUAN TRONG:
--   - Script nay IDEMPOTENT -- an toan de chay nhieu lan.
--   - KHONG xoa du lieu.
--   - KHONG DROP cot hien co.
--   - KHONG sua migration cu.
--   - Chay truc tiep trong Supabase SQL Editor.
-- ============================================================

-- PHAN 1: TAO BANG job_schedule
-- Bang luu lich lam viec chi tiet tung ngay cho mot Job.
-- Moi ngay = mot row, voi gio bat dau/ket thuc rieng biet.
-- ON DELETE CASCADE: khi Job bi xoa, schedule entries tu xoa theo.

CREATE TABLE IF NOT EXISTS job_schedule (
    id              SERIAL PRIMARY KEY,
    job_id          INTEGER NOT NULL
                        REFERENCES job(id)
                        ON DELETE CASCADE,
    scheduled_date  DATE        NOT NULL,
    start_time      VARCHAR(10) NOT NULL,
    end_time        VARCHAR(10) NOT NULL,
    created_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_job_schedule_job_id
    ON job_schedule (job_id);

CREATE INDEX IF NOT EXISTS ix_job_schedule_scheduled_date
    ON job_schedule (scheduled_date);


-- PHAN 2: SUA notification.related_job_id FK
-- Van de: FK hien tai khong co ON DELETE SET NULL.
-- Khi Admin go Job (soft remove hoac hard delete), PostgreSQL raise
-- ForeignKeyViolation vi Notification dang reference Job.
--
-- Giai phap: Doi FK thanh ON DELETE SET NULL.
-- Khi Job bi hard delete -> related_job_id tu dong = NULL (khong crash).
-- Khi Job chi soft remove (status='removed') -> FK giu nguyen, khong anh huong.

DO $$
DECLARE
    v_constraint_name TEXT;
    v_del_type CHAR(1);
BEGIN
    -- Tim ten FK constraint hien tai cua notification.related_job_id
    SELECT conname, confdeltype
    INTO v_constraint_name, v_del_type
    FROM pg_constraint
    WHERE conrelid = 'notification'::regclass
      AND contype = 'f'
      AND conkey && ARRAY(
          SELECT attnum::smallint
          FROM pg_attribute
          WHERE attrelid = 'notification'::regclass
            AND attname = 'related_job_id'
      )
    LIMIT 1;

    IF v_constraint_name IS NOT NULL THEN
        IF v_del_type != 'n' THEN
            -- DROP FK cu
            EXECUTE format('ALTER TABLE notification DROP CONSTRAINT %I', v_constraint_name);

            -- Them FK moi voi ON DELETE SET NULL
            ALTER TABLE notification
            ADD CONSTRAINT notification_related_job_id_fkey
            FOREIGN KEY (related_job_id)
            REFERENCES job(id)
            ON DELETE SET NULL;

            RAISE NOTICE 'notification.related_job_id FK updated to ON DELETE SET NULL.';
        ELSE
            RAISE NOTICE 'notification.related_job_id FK already has ON DELETE SET NULL. Skipped.';
        END IF;
    ELSE
        -- Chua co FK -> tao moi
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'notification_related_job_id_fkey'
              AND conrelid = 'notification'::regclass
        ) THEN
            ALTER TABLE notification
            ADD CONSTRAINT notification_related_job_id_fkey
            FOREIGN KEY (related_job_id)
            REFERENCES job(id)
            ON DELETE SET NULL;

            RAISE NOTICE 'notification.related_job_id FK created with ON DELETE SET NULL.';
        ELSE
            RAISE NOTICE 'notification_related_job_id_fkey already exists. Skipped.';
        END IF;
    END IF;
END $$;


-- PHAN 3: BO UNIQUE(contract_id) tren translator_schedule
-- Van de: Migration cu (full_safe_migration.sql) co UNIQUE(contract_id) tren
-- translator_schedule. Nhung multi-day booking can 1 contract -> nhieu schedule.
-- Constraint UNIQUE nay se block INSERT khi cung contract_id xuat hien lan 2+.
--
-- Model Python KHONG co UniqueConstraint nay -> can align production DB voi model.

DO $$
DECLARE
    v_unique_name TEXT;
BEGIN
    SELECT conname INTO v_unique_name
    FROM pg_constraint
    WHERE conrelid = 'translator_schedule'::regclass
      AND contype = 'u'
      AND conkey = ARRAY(
          SELECT attnum::smallint
          FROM pg_attribute
          WHERE attrelid = 'translator_schedule'::regclass
            AND attname = 'contract_id'
      );

    IF v_unique_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE translator_schedule DROP CONSTRAINT %I', v_unique_name);
        RAISE NOTICE 'Dropped UNIQUE(contract_id) constraint "%" from translator_schedule.', v_unique_name;
    ELSE
        RAISE NOTICE 'No UNIQUE(contract_id) constraint found on translator_schedule. Nothing to drop.';
    END IF;
END $$;


-- PHAN 4: DAM BAO CAC COT CAN THIET TREN CAC BANG HIEN CO
-- Cac lenh nay idempotent (IF NOT EXISTS). An toan de chay lai.

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS avatar VARCHAR(255);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS admin_role VARCHAR(50);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

ALTER TABLE translator_schedule ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE translator_schedule ADD COLUMN IF NOT EXISTS buffer_before_minutes INTEGER DEFAULT 0;
ALTER TABLE translator_schedule ADD COLUMN IF NOT EXISTS buffer_after_minutes INTEGER DEFAULT 30;

ALTER TABLE message ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE direct_message ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE review ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE;


-- PHAN 5: VERIFY (chay rieng de kiem tra ket qua)
-- Chay cac cau query sau trong Supabase SQL Editor de xac nhan:
--
-- SELECT 'job_schedule table exists' AS check_item,
--        EXISTS(SELECT 1 FROM information_schema.tables
--               WHERE table_name = 'job_schedule') AS passed;
--
-- SELECT 'notification FK ON DELETE SET NULL' AS check_item,
--        EXISTS(
--            SELECT 1 FROM pg_constraint
--            WHERE conrelid = 'notification'::regclass
--              AND contype = 'f'
--              AND confdeltype = 'n'
--              AND conkey && ARRAY(
--                  SELECT attnum::smallint FROM pg_attribute
--                  WHERE attrelid = 'notification'::regclass
--                    AND attname = 'related_job_id'
--              )
--        ) AS passed;
--
-- SELECT 'No UNIQUE(contract_id) on translator_schedule' AS check_item,
--        NOT EXISTS(
--            SELECT 1 FROM pg_constraint
--            WHERE conrelid = 'translator_schedule'::regclass
--              AND contype = 'u'
--              AND conkey = ARRAY(
--                  SELECT attnum::smallint FROM pg_attribute
--                  WHERE attrelid = 'translator_schedule'::regclass
--                    AND attname = 'contract_id'
--              )
--        ) AS passed;
