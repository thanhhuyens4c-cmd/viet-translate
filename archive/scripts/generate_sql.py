from app import app, db
from sqlalchemy.dialects.postgresql import base as pg_base
with app.app_context():
    with open("alter_all.sql", "w") as f:
        for table_name, table in db.metadata.tables.items():
            for column in table.columns:
                if column.name == 'id':
                    continue
                col_type = column.type.compile(dialect=pg_base.PGDialect())
                f.write(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS {column.name} {col_type};\n')
