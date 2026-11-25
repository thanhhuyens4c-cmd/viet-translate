# -*- coding: utf-8 -*-
"""
scripts/generate_interpreters_postgres_sql.py
Tạo file SQL thuần PostgreSQL: migrations/seed_50_interpreters_postgres.sql
Có thể chạy trực tiếp trong Supabase SQL Editor, psql, pgAdmin để nạp 50 PDV demo lên Production/Vercel.
"""

import os
import sys
import json
from werkzeug.security import generate_password_hash
from scripts.seed_demo_interpreters import generate_profile_data

default_pw = generate_password_hash("Demo@123456", method="pbkdf2:sha256")

DEMO_50_DATA = [generate_profile_data(i) for i in range(50)]

lines = [
    "-- ==========================================================================",
    "-- SEED SCRIPT 50 PHIÊN DỊCH VIÊN (PDV) DEMO CHO POSTGRESQL / SUPABASE",
    "-- Áp dụng cho: Vercel Production (Supabase PostgreSQL)",
    "-- Idempotent: Chạy nhiều lần an toàn, sử dụng ON CONFLICT và NOT EXISTS",
    "-- ==========================================================================\n",
    "BEGIN;\n"
]

lines.append("-- 0. Dọn dẹp các demo PDV cũ nếu cần để đảm bảo chuẩn xác đúng 50 hồ sơ")
lines.append("""
DELETE FROM interpreter_service WHERE user_id IN (SELECT id FROM "user" WHERE email LIKE 'pdv%@demo.viettranslate.local');
DELETE FROM "service" WHERE profile_id IN (SELECT id FROM translator_profile WHERE is_demo = true);
DELETE FROM interpreter_preference WHERE user_id IN (SELECT id FROM "user" WHERE email LIKE 'pdv%@demo.viettranslate.local');
DELETE FROM translator_preference WHERE translator_id IN (SELECT id FROM "user" WHERE email LIKE 'pdv%@demo.viettranslate.local');
DELETE FROM translator_verification WHERE profile_id IN (SELECT id FROM translator_profile WHERE is_demo = true);
DELETE FROM translator_profile WHERE is_demo = true;
DELETE FROM "user" WHERE email LIKE 'pdv%@demo.viettranslate.local';
""")

for idx, data in enumerate(DEMO_50_DATA, 1):
    email = data["email"].replace("'", "''")
    name = data["name"].replace("'", "''")
    phone = data["phone"].replace("'", "''")
    avatar = data["avatar"].replace("'", "''")
    city = data["city"].replace("'", "''")
    
    title = data["title"].replace("'", "''")
    bio = data["bio"].replace("'", "''")
    languages = data["languages"].replace("'", "''")
    specs = data["specializations"].replace("'", "''")
    src_lang = data["source_language"].replace("'", "''")
    tgt_lang = data["target_language"].replace("'", "''")
    itypes = data["interpreting_types"].replace("'", "''")
    exp = data["experience_years"]
    hrate = data["hourly_rate"]
    drate = data["daily_rate"]
    rating = data["rating"]
    tjobs = data["total_jobs"]
    treviews = data["total_reviews"]
    is_ver = "true" if data["is_verified"] else "false"
    ver_status = data["verification_status"].replace("'", "''")
    pos = data["current_position"].replace("'", "''")
    edu = data["education_level"].replace("'", "''")
    uni = data["university"].replace("'", "''")
    major = data["major"].replace("'", "''")
    cert = data["cert_name"].replace("'", "''")
    cert_year = data["cert_year"]
    clients = data["notable_clients"].replace("'", "''")
    projects = data["featured_projects"].replace("'", "''")
    badges = data["badges"].replace("'", "''")
    resp_time = data.get("response_time", "Trong vòng 1 giờ").replace("'", "''")

    lang_pairs_json = json.dumps([f"{data['source_language']} > {data['target_language']}", f"{data['target_language']} > {data['source_language']}"], ensure_ascii=False).replace("'", "''")
    spec_json = json.dumps([s.strip() for s in data["specializations"].split(",")], ensure_ascii=False).replace("'", "''")

    lines.append(f"""
-- PDV #{idx:02d}: {data['name']} ({data['email']})
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('{name}', '{email}', '{default_pw}', 'translator', true, true, '{phone}', '{avatar}', '{city}', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = '{name}', phone = '{phone}', avatar_url = '{avatar}', city = '{city}', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, '{languages}', '{specs}', '{src_lang}', '{tgt_lang}',
    '{itypes}', {exp}, {hrate}, {drate}, {rating},
    {tjobs}, {treviews}, '{bio}', {is_ver}, true, true,
    '{resp_time}', '{title}', '{pos}', '{edu}', '{uni}',
    '{major}', '{cert}', {cert_year}, '{clients}', '{projects}', '{badges}'
FROM "user" u WHERE u.email = '{email}';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '{lang_pairs_json}', '{spec_json}', 'both', '{city}', {hrate}, {drate}, false
FROM "user" u WHERE u.email = '{email}';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, '{languages}', '{src_lang} > {tgt_lang}, {tgt_lang} > {src_lang}', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', '{specs}', '{city}', 'both', true
FROM "user" u WHERE u.email = '{email}';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, '{src_lang}', '{tgt_lang}', 'Đàm phán & Thương mại', '{specs.split(",")[0].strip()}', {hrate}, {hrate * 4}, true
FROM "user" u WHERE u.email = '{email}';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch {src_lang} ↔ {tgt_lang} chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    {hrate * 2}, {hrate * 4}, {hrate * 8},
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = '{email}';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, '{name}', '00109' || LPAD(p.id::text, 7, '0'), '{ver_status}',
    CASE WHEN {is_ver} THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = '{email}';
""")

lines.append("\nCOMMIT;\n")

output_path = "migrations/seed_50_interpreters_postgres.sql"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"-> Tạo thành công file: {output_path} ({len(lines)} dòng)")
