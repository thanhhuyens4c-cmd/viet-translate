-- 1. Bật extension btree_gist để hỗ trợ tạo index/constraint trên các kiểu dữ liệu ngoài btree
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- 2. Tạo exclusion constraint
ALTER TABLE translator_schedule
ADD CONSTRAINT no_overlapping_schedules
EXCLUDE USING gist (
    translator_id WITH =,
    tsrange(
        (scheduled_date + start_time) - (buffer_before_minutes * interval '1 minute'),
        (scheduled_date + end_time) + (buffer_after_minutes * interval '1 minute')
    ) WITH &&
)
WHERE (status IN ('reserved', 'active'));