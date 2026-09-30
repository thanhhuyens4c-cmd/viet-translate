from app import app, db
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

with app.app_context():
    with open("full_safe_migration.sql", "w", encoding="utf-8") as f:
        f.write("-- 1. TẠO CÁC BẢNG NẾU CHƯA CÓ (Tự động)\n")
        for name, table in db.metadata.tables.items():
            create_stmt = str(CreateTable(table).compile(dialect=postgresql.dialect())).strip()
            create_stmt = create_stmt.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
            f.write(create_stmt + ";\n\n")
        
        f.write("-- 2. THÊM TẤT CẢ CÁC CỘT (Nếu thiếu, bỏ qua nếu đã có)\n")
        for name, table in db.metadata.tables.items():
            for column in table.columns:
                if column.name == 'id':
                    continue
                col_type = str(column.type.compile(dialect=postgresql.dialect()))
                # Postgres bool default mapping can be tricky, just basic types
                f.write(f'ALTER TABLE "{name}" ADD COLUMN IF NOT EXISTS {column.name} {col_type};\n')
