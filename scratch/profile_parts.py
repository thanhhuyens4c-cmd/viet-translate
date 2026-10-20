import time, sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')
from app import app
from models import db, User

client = app.test_client()

with app.app_context():
    trans = User.query.filter_by(role='translator').first()
    
    with client.session_transaction() as s:
        s['user_id'] = trans.id

    t0 = time.perf_counter()
    r = client.get('/account/profile')
    t_req = time.perf_counter() - t0
    print(f'Full GET request: {t_req*1000:.2f} ms | Status: {r.status_code} | Size: {len(r.data)/1024:.1f} KB')
