import os
import sys
from sqlalchemy import text
from app import app, db
from models import TranslatorSchedule

def check_overlaps():
    """Kiểm tra dữ liệu trùng lặp trước khi tạo constraint."""
    # Vì SQLite không có tsrange, ta phải kiểm tra bằng code Python
    # hoặc query tương đương. Ta dùng script kiểm tra toàn bộ.
    from services.schedule import build_effective_interval, datetime_intervals_overlap
    
    schedules = TranslatorSchedule.query.filter(TranslatorSchedule.status.in_(['reserved', 'active'])).all()
    overlaps = []
    
    for i in range(len(schedules)):
        for j in range(i + 1, len(schedules)):
            s1 = schedules[i]
            s2 = schedules[j]
            if s1.translator_id == s2.translator_id and s1.scheduled_date == s2.scheduled_date:
                start1, end1 = build_effective_interval(
                    s1.scheduled_date, s1.start_time, s1.end_time, s1.buffer_before_minutes, s1.buffer_after_minutes
                )
                start2, end2 = build_effective_interval(
                    s2.scheduled_date, s2.start_time, s2.end_time, s2.buffer_before_minutes, s2.buffer_after_minutes
                )
                if datetime_intervals_overlap(start1, end1, start2, end2):
                    overlaps.append((s1.id, s2.id))
                    
    return overlaps

def run_migration():
    with app.app_context():
        # 1. Kiểm tra database URL có phải Postgres không
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        if not db_url.startswith('postgres'):
            print("CẢNH BÁO: Database hiện tại không phải PostgreSQL.")
            print("Exclusion constraint sử dụng gist và tsrange chỉ hỗ trợ trên PostgreSQL.")
            print("Lưu file migration_add_exclusion.sql để bạn chạy thủ công trên Supabase.")
            
            sql_content = """
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
            """
            with open("migration_add_exclusion.sql", "w", encoding="utf-8") as f:
                f.write(sql_content.strip())
            print("Đã tạo migration_add_exclusion.sql")
            return

        # 2. Nếu là PostgreSQL, kiểm tra dữ liệu trùng lặp
        print("Đang kiểm tra dữ liệu trùng lặp...")
        overlaps = check_overlaps()
        if overlaps:
            print("PHÁT HIỆN DỮ LIỆU TRÙNG LẶP. KHÔNG THỂ TẠO CONSTRAINT!")
            for o in overlaps:
                print(f" - Trùng lịch giữa bản ghi id={o[0]} và id={o[1]}")
            print("Vui lòng xử lý thủ công (hủy một trong hai lịch) trước khi chạy migration.")
            sys.exit(1)
            
        print("Không có dữ liệu trùng lặp. Bắt đầu tạo constraint trên PostgreSQL...")
        
        try:
            db.session.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist;"))
            
            # Kiểm tra xem constraint đã tồn tại chưa
            check_exist = db.session.execute(text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'translator_schedule' 
                AND constraint_name = 'no_overlapping_schedules';
            """)).fetchone()
            
            if check_exist:
                print("Constraint 'no_overlapping_schedules' đã tồn tại.")
            else:
                db.session.execute(text("""
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
                """))
                db.session.commit()
                print("Đã tạo exclusion constraint thành công.")
                
        except Exception as e:
            db.session.rollback()
            print(f"Lỗi khi chạy migration: {e}")
            sys.exit(1)

if __name__ == '__main__':
    run_migration()
