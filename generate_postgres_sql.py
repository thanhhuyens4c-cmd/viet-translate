# -*- coding: utf-8 -*-
"""
generate_postgres_sql.py
Tạo file SQL thuần PostgreSQL: migrations/seed_100_jobs_postgres.sql
Có thể chạy trực tiếp trong psql, pgAdmin, aaPanel hoặc Supabase SQL Editor.
"""

import json
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

with open('jobs_data.json', 'r', encoding='utf-8') as f:
    jobs_data = json.load(f)

DEMO_HIRERS = [
    {
        'email': 'hirer_vtech@viettranslate.demo',
        'name': 'Tập đoàn Công nghệ V-Tech',
        'company': 'V-Tech Solutions & AI Lab',
        'title': 'Trưởng phòng Hợp tác Quốc tế',
        'location': 'Tòa nhà Keangnam, Cầu Giấy, Hà Nội'
    },
    {
        'email': 'hirer_medical@viettranslate.demo',
        'name': 'Bệnh viện Đa khoa Quốc tế Hạnh Phúc',
        'company': 'Hạnh Phúc International Hospital',
        'title': 'Ban Hợp tác Y khoa & Chuyển giao Công nghệ',
        'location': 'Quận 1, TP. Hồ Chí Minh'
    },
    {
        'email': 'hirer_lexpartners@viettranslate.demo',
        'name': 'Hãng Luật Quốc tế LexPartners',
        'company': 'LexPartners Law Firm LLC',
        'title': 'Luật sư Điều hành & Trọng tài viên',
        'location': 'Bitexco Financial Tower, Quận 1, TP.HCM'
    },
    {
        'email': 'hirer_apexmanuf@viettranslate.demo',
        'name': 'Tổ hợp Chế tạo Apex Precision',
        'company': 'Apex Precision Manufacturing Co.',
        'title': 'Giám đốc Vận hành Nhà máy',
        'location': 'KCN DEEP C, Đình Vũ, Hải Phòng'
    },
    {
        'email': 'hirer_vinastruct@viettranslate.demo',
        'name': 'Công ty CP Đầu tư & Hạ tầng Vinastruct',
        'company': 'Vinastruct Infrastructure Group',
        'title': 'Ban Quản lý Dự án Giao thông & Metro',
        'location': 'TP. Thủ Đức, TP. Hồ Chí Minh'
    },
    {
        'email': 'hirer_mekongcap@viettranslate.demo',
        'name': 'Quỹ Đầu tư & Quản lý Tài sản Mekong',
        'company': 'Mekong Capital & Ventures',
        'title': 'Giám đốc Thẩm định Đầu tư M&A',
        'location': 'Lotte Center, Ba Đình, Hà Nội'
    },
    {
        'email': 'hirer_saigontour@viettranslate.demo',
        'name': 'Saigon Global Travel & Hospitality',
        'company': 'Saigon Global Luxury Tours',
        'title': 'Quản lý Dịch vụ VIP & Famtrip',
        'location': 'Quận 3, TP. Hồ Chí Minh'
    },
    {
        'email': 'hirer_diplomacy@viettranslate.demo',
        'name': 'Viện Đối ngoại & Hợp tác Phát triển Á - Âu',
        'company': 'Institute for Asian-European Diplomacy',
        'title': 'Điều phối viên Dự án ODA',
        'location': 'Hoàn Kiếm, Hà Nội'
    },
    {
        'email': 'hirer_greenpower@viettranslate.demo',
        'name': 'Tập đoàn Năng lượng Xanh GreenPower',
        'company': 'GreenPower Renewables & Offshore',
        'title': 'Trưởng ban Kỹ thuật Dự án Điện gió',
        'location': 'Vũng Tàu, Bà Rịa - Vũng Tàu'
    },
    {
        'email': 'hirer_transglobal@viettranslate.demo',
        'name': 'Hãng Giao nhận Vận tải TransGlobal',
        'company': 'TransGlobal Freight & Marine Logistics',
        'title': 'Giám đốc Khai thác Cảng & Chuỗi cung ứng',
        'location': 'Khu ngoại quan Cái Mép, Bà Rịa - Vũng Tàu'
    },
    {
        'email': 'hirer_vasepfood@viettranslate.demo',
        'name': 'Hiệp hội Thực phẩm & Nông sản Sạch V-Agri',
        'company': 'V-Agri Food Export Alliance',
        'title': 'Phụ trách Xúc tiến Thương mại Quốc tế',
        'location': 'Ninh Kiều, Cần Thơ'
    },
    {
        'email': 'hirer_edu_intl@viettranslate.demo',
        'name': 'Tổ chức Giáo dục Quốc tế Global Pathway',
        'company': 'Global Pathway Education',
        'title': 'Giám đốc Tuyển sinh & Liên kết Đại học',
        'location': 'Hải Châu, Đà Nẵng'
    }
]

default_pw = generate_password_hash('123456')

lines = [
    "-- ==========================================================================",
    "-- SEED SCRIPT 100 INTERPRETER JOBS CHO POSTGRESQL (PRODUCTION / VPS)",
    "-- Tương thích 100% PostgreSQL 16 & Supabase Cloud",
    "-- Idempotent: chạy nhiều lần an toàn, sử dụng ON CONFLICT DO NOTHING",
    "-- ==========================================================================\n",
    "BEGIN;\n"
]

# 1. Insert hirer users
lines.append("-- 1. Nạp tài khoản Nhà tuyển dụng (Hirers)")
for h in DEMO_HIRERS:
    email = h['email'].replace("'", "''")
    name = h['name'].replace("'", "''")
    company = h['company'].replace("'", "''")
    title = h['title'].replace("'", "''")
    loc = h['location'].replace("'", "''")
    lines.append(f"""
INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('{name}', '{email}', '{default_pw}', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, '{company}', '{title}', '{loc}', 4.9
FROM "user" WHERE email = '{email}'
ON CONFLICT (user_id) DO NOTHING;
""")

# 2. Insert 100 jobs
lines.append("\n-- 2. Nạp 100 việc làm phiên dịch đa ngành (Jobs)")
base_date = date.today()

for idx, j in enumerate(jobs_data):
    hirer_meta = DEMO_HIRERS[j['hirer_index'] % len(DEMO_HIRERS)]
    hirer_email = hirer_meta['email'].replace("'", "''")
    title = j['title'].replace("'", "''")
    desc = j['description'].replace("'", "''")
    cat = j.get('category', 'Hội nghị').replace("'", "''")
    cat_grp = j.get('category_group', 'interpretation_other').replace("'", "''")
    stype = j.get('service_type', 'conference').replace("'", "''")
    slang = j['source_lang'].replace("'", "''")
    tlang = j['target_lang'].replace("'", "''")
    btype = j['budget_type'].replace("'", "''")
    bmin = j['budget_min']
    bmax = j.get('budget_max') or 'NULL'
    edate = j['event_date'].replace("'", "''")
    estart = j.get('event_time_start', '08:30').replace("'", "''")
    eend = j.get('event_time_end', '17:00').replace("'", "''")
    eloc = j['event_location'].replace("'", "''")
    deadline_val = f"CURRENT_DATE + INTERVAL '{j.get('deadline_days', 10)} days'"
    created_val = f"NOW() - INTERVAL '{j.get('days_ago', 0)} days'"

    lines.append(f"""
INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, '{title}', '{desc}', '{cat}', '{cat_grp}', '{stype}',
    '{slang}', '{tlang}', '{btype}', {bmin}, {bmax},
    '{edate}', '{estart}', '{eend}', '{eloc}',
    {deadline_val}, 'open', 'approved', false, {created_val}
FROM "user" u WHERE u.email = '{hirer_email}'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = '{title}');
""")

lines.append("\nCOMMIT;\n")

output_file = 'migrations/seed_100_jobs_postgres.sql'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"-> Đã tạo thành công {output_file} với đầy đủ 100 việc làm cho PostgreSQL!")
