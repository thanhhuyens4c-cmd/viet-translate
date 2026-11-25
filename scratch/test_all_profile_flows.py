import time, sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')
from app import app
from models import db, User, TranslatorProfile, Job, Proposal, Contract
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
    profile = TranslatorProfile.query.filter_by(user_id=trans.id).first()
    
    print('========================================')
    print('INVESTIGATING PERFORMANCE & FREEZE RISKS')
    print('========================================')

    # Test 1: PDV clicking /account/profile
    queries.clear()
    with client.session_transaction() as s:
        s.clear()
        s['user_id'] = trans.id
    t0 = time.perf_counter()
    r = client.get('/account/profile')
    t1 = time.perf_counter() - t0
    print(f'1. PDV -> /account/profile: {t1*1000:.1f} ms | Status: {r.status_code} | Queries: {len(queries)}')

    # Test 2: Hirer clicking /account/profile
    queries.clear()
    with client.session_transaction() as s:
        s.clear()
        s['user_id'] = hirer.id
    t0 = time.perf_counter()
    r = client.get('/account/profile')
    t1 = time.perf_counter() - t0
    print(f'2. Hirer -> /account/profile: {t1*1000:.1f} ms | Status: {r.status_code} | Queries: {len(queries)}')

    # Test 3: PDV viewing their own profile /translator/<id>
    if profile:
        queries.clear()
        with client.session_transaction() as s:
            s.clear()
            s['user_id'] = trans.id
        t0 = time.perf_counter()
        r = client.get(f'/translator/{profile.id}')
        t1 = time.perf_counter() - t0
        print(f'3. PDV (Owner) -> /translator/{profile.id}: {t1*1000:.1f} ms | Status: {r.status_code} | Queries: {len(queries)}')

    # Test 4: Hirer viewing PDV profile /translator/<id>
    if profile:
        queries.clear()
        with client.session_transaction() as s:
            s.clear()
            s['user_id'] = hirer.id
        t0 = time.perf_counter()
        r = client.get(f'/translator/{profile.id}')
        t1 = time.perf_counter() - t0
        print(f'4. Hirer -> /translator/{profile.id}: {t1*1000:.1f} ms | Status: {r.status_code} | Queries: {len(queries)}')
        for dur, q in sorted(queries, key=lambda x: x[0], reverse=True)[:5]:
            print(f'   Q: [{dur*1000:.2f} ms] {q.strip().replace(chr(10), " ")[:120]}')

    # Test 5: Hirer browsing /translators (Finding profiles)
    queries.clear()
    with client.session_transaction() as s:
        s.clear()
        s['user_id'] = hirer.id
    t0 = time.perf_counter()
    r = client.get('/translators')
    t1 = time.perf_counter() - t0
    print(f'5. Hirer -> /translators: {t1*1000:.1f} ms | Status: {r.status_code} | Queries: {len(queries)}')
    for dur, q in sorted(queries, key=lambda x: x[0], reverse=True)[:5]:
        print(f'   Q: [{dur*1000:.2f} ms] {q.strip().replace(chr(10), " ")[:120]}')

    # Test 6: API Translators search
    queries.clear()
    with client.session_transaction() as s:
        s.clear()
        s['user_id'] = hirer.id
    t0 = time.perf_counter()
    r = client.get('/api/translators')
    t1 = time.perf_counter() - t0
    print(f'6. Hirer -> /api/translators: {t1*1000:.1f} ms | Status: {r.status_code} | Queries: {len(queries)}')
    print(f'   Items returned: {len(r.json.get("items", [])) if r.is_json else "not json"}')
    for dur, q in sorted(queries, key=lambda x: x[0], reverse=True)[:5]:
        print(f'   Q: [{dur*1000:.2f} ms] {q.strip().replace(chr(10), " ")[:120]}')

    # Test 7: PDV browsing /translators
    queries.clear()
    with client.session_transaction() as s:
        s.clear()
        s['user_id'] = trans.id
    t0 = time.perf_counter()
    r = client.get('/translators')
    t1 = time.perf_counter() - t0
    print(f'7. PDV -> /translators: {t1*1000:.1f} ms | Status: {r.status_code} | Queries: {len(queries)}')
