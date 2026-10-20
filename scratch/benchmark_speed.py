import sys
sys.path.insert(0, '.')
import time
import gzip
from app import app
from models import db
from sqlalchemy import event

queries = []
with app.app_context():
    @event.listens_for(db.engine, 'before_cursor_execute')
    def count_query(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    client = app.test_client()

    routes = [
        ('/', None),
        ('/jobs', None),
        ('/translators', None),
        ('/translator/1', None),
        ('/account/profile', 14),
    ]

    print(f"{'Route':<22} | {'Status':<6} | {'Time':<10} | {'Queries':<7} | {'Raw Size':<10} | {'Gzip Size':<10} | {'Reduction':<10}")
    print('-' * 85)

    for url, uid in routes:
        queries.clear()
        with client.session_transaction() as s:
            s.clear()
            if uid:
                s['user_id'] = uid
        t0 = time.perf_counter()
        resp = client.get(url, headers={'Accept-Encoding': 'gzip'})
        dt = (time.perf_counter() - t0) * 1000
        comp_len = len(resp.data)
        decomp = gzip.decompress(resp.data) if resp.headers.get('Content-Encoding') == 'gzip' else resp.data
        raw_kb = len(decomp) / 1024
        comp_kb = comp_len / 1024
        red = (1 - comp_kb / raw_kb) * 100 if raw_kb > 0 else 0
        q_count = len(queries)
        print(f"{url:<22} | {resp.status_code:<6} | {dt:7.1f} ms | {q_count:<7} | {raw_kb:7.1f} KB | {comp_kb:7.1f} KB | {red:7.1f} %")
