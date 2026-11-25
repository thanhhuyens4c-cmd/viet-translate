import time, sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')
from app import app
from models import db, User
from sqlalchemy import event

queries = []

with app.app_context():
    @event.listens_for(db.engine, 'before_cursor_execute')
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.perf_counter()

    @event.listens_for(db.engine, 'after_cursor_execute')
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.perf_counter() - getattr(context, '_query_start_time', time.perf_counter())
        queries.append((total, statement))

    client = app.test_client()

    trans = User.query.filter_by(role='translator').first()
    hirer = User.query.filter_by(role='hirer').first()
    
    # 1. Profile Translator
    queries.clear()
    with client.session_transaction() as s:
        s.clear()
        s['user_id'] = trans.id
    t0 = time.perf_counter()
    r = client.get('/account/profile')
    t_total = time.perf_counter() - t0
    print(f'=== TRANSLATOR /account/profile ===')
    print(f'Total Time: {t_total*1000:.2f} ms | Status: {r.status_code} | HTML Size: {len(r.data)/1024:.1f} KB | Total SQL queries: {len(queries)}')
    for i, (dur, q) in enumerate(queries):
        print(f'  Q{i+1:02d} [{dur*1000:6.2f} ms] {q.strip().replace(chr(10), " ")[:140]}...')

    # 2. Profile Hirer
    queries.clear()
    with client.session_transaction() as s:
        s.clear()
        s['user_id'] = hirer.id
    t0 = time.perf_counter()
    r = client.get('/account/profile')
    t_total = time.perf_counter() - t0
    print(f'\n=== HIRER /account/profile ===')
    print(f'Total Time: {t_total*1000:.2f} ms | Status: {r.status_code} | HTML Size: {len(r.data)/1024:.1f} KB | Total SQL queries: {len(queries)}')
    for i, (dur, q) in enumerate(queries):
        print(f'  Q{i+1:02d} [{dur*1000:6.2f} ms] {q.strip().replace(chr(10), " ")[:140]}...')
