import time, sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')
from app import app
from models import db, User

client = app.test_client()

with app.app_context():
    trans = User.query.filter_by(role='translator').first()
    hirer = User.query.filter_by(role='hirer').first()
    
    print('=== PERFORMANCE & PAGE LOAD SPEED BENCHMARK ===')
    
    # 1. Anonymous visitor
    urls_guest = ['/index', '/about', '/tin-tuc', '/payment-info', '/translator/1']
    print('\n[1. Khach vang lai / Guest]')
    for url in urls_guest:
        t0 = time.perf_counter()
        r = client.get(url)
        dt = (time.perf_counter() - t0) * 1000
        print(f'  GET {url:<28} -> {r.status_code} | {dt:6.2f} ms | {len(r.data)/1024:6.1f} KB')

    # 2. Translator (PDV)
    with client.session_transaction() as s:
        s.clear()
        s['user_id'] = trans.id
    urls_trans = ['/interpreter/dashboard', '/account/profile', '/profile', '/account/overview', '/jobs', '/my-schedule', '/interpreter/income/overview']
    print('\n[2. Phien dich vien / Translator]')
    for url in urls_trans:
        t0 = time.perf_counter()
        r = client.get(url)
        dt = (time.perf_counter() - t0) * 1000
        print(f'  GET {url:<28} -> {r.status_code} | {dt:6.2f} ms | {len(r.data)/1024:6.1f} KB')

    # 3. Hirer (Người đi thuê)
    with client.session_transaction() as s:
        s.clear()
        s['user_id'] = hirer.id
    urls_hirer = ['/client/dashboard', '/account/profile', '/profile', '/client/profile', '/my-jobs', '/my-projects', '/translators']
    print('\n[3. Nguoi di thue / Hirer]')
    for url in urls_hirer:
        t0 = time.perf_counter()
        r = client.get(url)
        dt = (time.perf_counter() - t0) * 1000
        print(f'  GET {url:<28} -> {r.status_code} | {dt:6.2f} ms | {len(r.data)/1024:6.1f} KB')
