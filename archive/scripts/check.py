from app import app, db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
with app.app_context():
    db.create_all()
    with db.engine.connect() as conn:
        res = conn.execute(db.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='translator_schedule'"))
        print('TABLE SCHEMA:', res.scalar())
        res = conn.execute(db.text("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='translator_schedule'"))
        print('INDEXES:')
        for row in res:
            print(row[0])
