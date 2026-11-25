"""So khớp database thật với các model trong models.py: liệt kê bảng và cột còn thiếu.

Chỉ ĐỌC, không sửa gì. Chạy trên máy chủ, trong thư mục dự án, với đúng DATABASE_URL của web:

    python scripts/check_model_schema.py

Nếu có cột thiếu (ví dụ web báo 500 ở mọi trang đụng bảng `job`), script in ra câu ALTER TABLE gợi ý
để bạn xem lại rồi tự chạy. Không bao giờ tự chạy lệnh sửa.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import inspect  # noqa: E402
from sqlalchemy.schema import CreateColumn  # noqa: E402

from app import app, db  # noqa: E402


def main():
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        problems = 0
        for table in db.metadata.sorted_tables:
            if table.name not in existing_tables:
                problems += 1
                print(f'[THIẾU BẢNG] {table.name}')
                continue
            have = {c['name'] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                problems += 1
                ddl = str(CreateColumn(col).compile(dialect=db.engine.dialect)).strip()
                print(f'[THIẾU CỘT] {table.name}.{col.name}')
                print(f'    gợi ý: ALTER TABLE "{table.name}" ADD COLUMN {ddl};')
        if problems == 0:
            print('Database khớp với models.py: không thiếu bảng hay cột nào.')
        else:
            print(f'\nTổng cộng {problems} vấn đề. Xem lại từng dòng rồi mới chạy lệnh sửa.')
        return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
