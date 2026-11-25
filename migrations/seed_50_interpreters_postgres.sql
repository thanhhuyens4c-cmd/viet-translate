-- ==========================================================================
-- SEED SCRIPT 50 PHIÊN DỊCH VIÊN (PDV) DEMO CHO POSTGRESQL / SUPABASE
-- Áp dụng cho: Vercel Production (Supabase PostgreSQL)
-- Idempotent: Chạy nhiều lần an toàn, sử dụng ON CONFLICT và NOT EXISTS
-- ==========================================================================

BEGIN;

-- 0. Dọn dẹp các demo PDV cũ nếu cần để đảm bảo chuẩn xác đúng 50 hồ sơ

DELETE FROM interpreter_service WHERE user_id IN (SELECT id FROM "user" WHERE email LIKE 'pdv%@demo.viettranslate.local');
DELETE FROM "service" WHERE profile_id IN (SELECT id FROM translator_profile WHERE is_demo = true);
DELETE FROM interpreter_preference WHERE user_id IN (SELECT id FROM "user" WHERE email LIKE 'pdv%@demo.viettranslate.local');
DELETE FROM translator_preference WHERE translator_id IN (SELECT id FROM "user" WHERE email LIKE 'pdv%@demo.viettranslate.local');
DELETE FROM translator_verification WHERE profile_id IN (SELECT id FROM translator_profile WHERE is_demo = true);
DELETE FROM translator_profile WHERE is_demo = true;
DELETE FROM "user" WHERE email LIKE 'pdv%@demo.viettranslate.local';


-- PDV #01: Nguyễn Minh Tuấn (pdv001@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Nguyễn Minh Tuấn', 'pdv001@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000001', '/static/avatars/avatar_dung.jpg', 'Hà Nội', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Nguyễn Minh Tuấn', phone = '0901000001', avatar_url = '/static/avatars/avatar_dung.jpg', city = 'Hà Nội', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Anh', 'Đàm phán kinh doanh & Thương mại, Xây dựng & Bất động sản', 'Tiếng Việt', 'Tiếng Anh',
    'Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)', 1, 300000.0, 2200000.0, 4.3,
    5, 4, 'Phiên dịch viên chuyên nghiệp với 1 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Anh, am hiểu sâu sắc thuật ngữ chuyên ngành Đàm phán kinh doanh & Thương mại và Xây dựng & Bất động sản. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Hà Nội cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên triển vọng Tiếng Việt - Tiếng Anh | Chuyên ngành Đàm phán kinh doanh & Thương mại', 'Phiên dịch viên Tiếng Anh – Đàm phán kinh doanh & Thương mại', 'Cử nhân', 'Đại học Ngoại ngữ - ĐHQGHN',
    'Ngôn ngữ học ứng dụng', 'IELTS 8.5 Academic', 2022, 'Tập đoàn đa quốc gia ngành Đàm phán kinh doanh & Thương mại, Đối tác FDI tại Hà Nội, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Đàm phán kinh doanh & Thương mại; Hội thảo xúc tiến thương mại Xây dựng & Bất động sản', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Premium PDV'
FROM "user" u WHERE u.email = 'pdv001@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Anh", "Tiếng Anh > Tiếng Việt"]', '["Đàm phán kinh doanh & Thương mại", "Xây dựng & Bất động sản"]', 'both', 'Hà Nội', 300000.0, 2200000.0, false
FROM "user" u WHERE u.email = 'pdv001@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Anh', 'Tiếng Việt > Tiếng Anh, Tiếng Anh > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Đàm phán kinh doanh & Thương mại, Xây dựng & Bất động sản', 'Hà Nội', 'both', true
FROM "user" u WHERE u.email = 'pdv001@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Anh', 'Đàm phán & Thương mại', 'Đàm phán kinh doanh & Thương mại', 300000.0, 1200000.0, true
FROM "user" u WHERE u.email = 'pdv001@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Anh chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    600000.0, 1200000.0, 2400000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv001@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Nguyễn Minh Tuấn', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv001@demo.viettranslate.local';


-- PDV #02: Trần Thị Bích Ngọc (pdv002@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Trần Thị Bích Ngọc', 'pdv002@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000002', '/static/avatars/avatar_ha.jpg', 'TP. Hồ Chí Minh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Trần Thị Bích Ngọc', phone = '0901000002', avatar_url = '/static/avatars/avatar_ha.jpg', city = 'TP. Hồ Chí Minh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Anh, Tiếng Việt', 'Pháp lý & Hợp đồng, Công nghệ thông tin & Phần mềm', 'Tiếng Anh', 'Tiếng Việt',
    'Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng', 2, 350000.0, 2500000.0, 4.4,
    8, 6, 'Phiên dịch viên chuyên nghiệp với 2 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Anh - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Pháp lý & Hợp đồng và Công nghệ thông tin & Phần mềm. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực TP. Hồ Chí Minh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên triển vọng Tiếng Anh - Tiếng Việt | Chuyên ngành Pháp lý & Hợp đồng', 'Phiên dịch viên Tiếng Việt – Pháp lý & Hợp đồng', 'Cử nhân', 'Đại học Ngoại thương (FTU)',
    'Tiếng Anh Thương mại', 'IELTS 8.0 Academic', 2023, 'Tập đoàn đa quốc gia ngành Pháp lý & Hợp đồng, Đối tác FDI tại TP. Hồ Chí Minh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Pháp lý & Hợp đồng; Hội thảo xúc tiến thương mại Công nghệ thông tin & Phần mềm', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv002@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Anh > Tiếng Việt", "Tiếng Việt > Tiếng Anh"]', '["Pháp lý & Hợp đồng", "Công nghệ thông tin & Phần mềm"]', 'both', 'TP. Hồ Chí Minh', 350000.0, 2500000.0, false
FROM "user" u WHERE u.email = 'pdv002@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Anh, Tiếng Việt', 'Tiếng Anh > Tiếng Việt, Tiếng Việt > Tiếng Anh', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Pháp lý & Hợp đồng, Công nghệ thông tin & Phần mềm', 'TP. Hồ Chí Minh', 'both', true
FROM "user" u WHERE u.email = 'pdv002@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Anh', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Pháp lý & Hợp đồng', 350000.0, 1400000.0, true
FROM "user" u WHERE u.email = 'pdv002@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Anh ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    700000.0, 1400000.0, 2800000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv002@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Trần Thị Bích Ngọc', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv002@demo.viettranslate.local';


-- PDV #03: Lê Hoàng Long (pdv003@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Lê Hoàng Long', 'pdv003@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000003', '/static/avatars/avatar_bich.jpg', 'Đà Nẵng', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Lê Hoàng Long', phone = '0901000003', avatar_url = '/static/avatars/avatar_bich.jpg', city = 'Đà Nẵng', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Anh, Tiếng Pháp', 'Y tế & Chăm sóc sức khỏe, Giáo dục & Đào tạo', 'Tiếng Việt', 'Tiếng Anh',
    'Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy', 1, 400000.0, 2800000.0, 4.5,
    11, 8, 'Phiên dịch viên chuyên nghiệp với 1 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Anh, am hiểu sâu sắc thuật ngữ chuyên ngành Y tế & Chăm sóc sức khỏe và Giáo dục & Đào tạo. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Đà Nẵng cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên triển vọng Tiếng Việt - Tiếng Anh | Chuyên ngành Y tế & Chăm sóc sức khỏe', 'Phiên dịch viên Tiếng Anh – Y tế & Chăm sóc sức khỏe', 'Cử nhân', 'Đại học Hà Nội (HANU)',
    'Biên phiên dịch Chuyên nghiệp', 'TOEIC 985/990', 2021, 'Tập đoàn đa quốc gia ngành Y tế & Chăm sóc sức khỏe, Đối tác FDI tại Đà Nẵng, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Y tế & Chăm sóc sức khỏe; Hội thảo xúc tiến thương mại Giáo dục & Đào tạo', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv003@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Anh", "Tiếng Anh > Tiếng Việt"]', '["Y tế & Chăm sóc sức khỏe", "Giáo dục & Đào tạo"]', 'both', 'Đà Nẵng', 400000.0, 2800000.0, false
FROM "user" u WHERE u.email = 'pdv003@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Anh, Tiếng Pháp', 'Tiếng Việt > Tiếng Anh, Tiếng Anh > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Y tế & Chăm sóc sức khỏe, Giáo dục & Đào tạo', 'Đà Nẵng', 'both', true
FROM "user" u WHERE u.email = 'pdv003@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Anh', 'Đàm phán & Thương mại', 'Y tế & Chăm sóc sức khỏe', 400000.0, 1600000.0, true
FROM "user" u WHERE u.email = 'pdv003@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Anh chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    800000.0, 1600000.0, 3200000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv003@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Lê Hoàng Long', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv003@demo.viettranslate.local';


-- PDV #04: Phạm Hải Đăng (pdv004@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Phạm Hải Đăng', 'pdv004@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000004', '/static/avatars/avatar_cuong.jpg', 'Hải Phòng', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Phạm Hải Đăng', phone = '0901000004', avatar_url = '/static/avatars/avatar_cuong.jpg', city = 'Hải Phòng', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Anh, Tiếng Việt', 'Du lịch & Khách sạn, Xuất nhập khẩu & Logistics', 'Tiếng Anh', 'Tiếng Việt',
    'Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm', 2, 450000.0, 3100000.0, 4.6,
    14, 11, 'Phiên dịch viên chuyên nghiệp với 2 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Anh - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Du lịch & Khách sạn và Xuất nhập khẩu & Logistics. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Hải Phòng cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên triển vọng Tiếng Anh - Tiếng Việt | Chuyên ngành Du lịch & Khách sạn', 'Phiên dịch viên Tiếng Việt – Du lịch & Khách sạn', 'Cử nhân', 'Đại học KHXH&NV - ĐHQG TP.HCM',
    'Ngôn ngữ & Văn hóa Quốc tế', 'IELTS 7.5 Academic', 2023, 'Tập đoàn đa quốc gia ngành Du lịch & Khách sạn, Đối tác FDI tại Hải Phòng, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Du lịch & Khách sạn; Hội thảo xúc tiến thương mại Xuất nhập khẩu & Logistics', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv004@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Anh > Tiếng Việt", "Tiếng Việt > Tiếng Anh"]', '["Du lịch & Khách sạn", "Xuất nhập khẩu & Logistics"]', 'both', 'Hải Phòng', 450000.0, 3100000.0, false
FROM "user" u WHERE u.email = 'pdv004@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Anh, Tiếng Việt', 'Tiếng Anh > Tiếng Việt, Tiếng Việt > Tiếng Anh', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Du lịch & Khách sạn, Xuất nhập khẩu & Logistics', 'Hải Phòng', 'both', true
FROM "user" u WHERE u.email = 'pdv004@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Anh', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Du lịch & Khách sạn', 450000.0, 1800000.0, true
FROM "user" u WHERE u.email = 'pdv004@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Anh ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    900000.0, 1800000.0, 3600000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv004@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Phạm Hải Đăng', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv004@demo.viettranslate.local';


-- PDV #05: Hoàng Mai Phương (pdv005@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Hoàng Mai Phương', 'pdv005@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000005', '/static/avatars/avatar_duc.jpg', 'Cần Thơ', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Hoàng Mai Phương', phone = '0901000005', avatar_url = '/static/avatars/avatar_duc.jpg', city = 'Cần Thơ', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Anh', 'Sản xuất & Kỹ thuật công nghiệp, Tài chính & Ngân hàng', 'Tiếng Việt', 'Tiếng Anh',
    'Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương', 1, 300000.0, 2200000.0, 4.7,
    7, 5, 'Phiên dịch viên chuyên nghiệp với 1 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Anh, am hiểu sâu sắc thuật ngữ chuyên ngành Sản xuất & Kỹ thuật công nghiệp và Tài chính & Ngân hàng. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Cần Thơ cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên triển vọng Tiếng Việt - Tiếng Anh | Chuyên ngành Sản xuất & Kỹ thuật công nghiệp', 'Phiên dịch viên Tiếng Anh – Sản xuất & Kỹ thuật công nghiệp', 'Cử nhân', 'Đại học Bách Khoa Hà Nội',
    'Kỹ thuật & Ngoại ngữ chuyên ngành', 'IELTS 8.5 Academic', 2022, 'Tập đoàn đa quốc gia ngành Sản xuất & Kỹ thuật công nghiệp, Đối tác FDI tại Cần Thơ, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Sản xuất & Kỹ thuật công nghiệp; Hội thảo xúc tiến thương mại Tài chính & Ngân hàng', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Premium PDV'
FROM "user" u WHERE u.email = 'pdv005@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Anh", "Tiếng Anh > Tiếng Việt"]', '["Sản xuất & Kỹ thuật công nghiệp", "Tài chính & Ngân hàng"]', 'both', 'Cần Thơ', 300000.0, 2200000.0, false
FROM "user" u WHERE u.email = 'pdv005@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Anh', 'Tiếng Việt > Tiếng Anh, Tiếng Anh > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Sản xuất & Kỹ thuật công nghiệp, Tài chính & Ngân hàng', 'Cần Thơ', 'both', true
FROM "user" u WHERE u.email = 'pdv005@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Anh', 'Đàm phán & Thương mại', 'Sản xuất & Kỹ thuật công nghiệp', 300000.0, 1200000.0, true
FROM "user" u WHERE u.email = 'pdv005@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Anh chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    600000.0, 1200000.0, 2400000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv005@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Hoàng Mai Phương', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv005@demo.viettranslate.local';


-- PDV #06: Vũ Đình Trọng (pdv006@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Vũ Đình Trọng', 'pdv006@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000006', '/static/avatars/avatar_huong.jpg', 'Bình Dương', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Vũ Đình Trọng', phone = '0901000006', avatar_url = '/static/avatars/avatar_huong.jpg', city = 'Bình Dương', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Anh, Tiếng Việt, Tiếng Trung', 'Xây dựng & Bất động sản, Năng lượng & Dầu khí', 'Tiếng Anh', 'Tiếng Việt',
    'Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)', 2, 350000.0, 2500000.0, 4.3,
    10, 8, 'Phiên dịch viên chuyên nghiệp với 2 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Anh - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Xây dựng & Bất động sản và Năng lượng & Dầu khí. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Bình Dương cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên triển vọng Tiếng Anh - Tiếng Việt | Chuyên ngành Xây dựng & Bất động sản', 'Phiên dịch viên Tiếng Việt – Xây dựng & Bất động sản', 'Cử nhân', 'Đại học Sư phạm TP.HCM',
    'Sư phạm & Dịch thuật Ngoại ngữ', 'IELTS 8.0 Academic', 2023, 'Tập đoàn đa quốc gia ngành Xây dựng & Bất động sản, Đối tác FDI tại Bình Dương, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Xây dựng & Bất động sản; Hội thảo xúc tiến thương mại Năng lượng & Dầu khí', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv006@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Anh > Tiếng Việt", "Tiếng Việt > Tiếng Anh"]', '["Xây dựng & Bất động sản", "Năng lượng & Dầu khí"]', 'both', 'Bình Dương', 350000.0, 2500000.0, false
FROM "user" u WHERE u.email = 'pdv006@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Anh, Tiếng Việt, Tiếng Trung', 'Tiếng Anh > Tiếng Việt, Tiếng Việt > Tiếng Anh', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Xây dựng & Bất động sản, Năng lượng & Dầu khí', 'Bình Dương', 'both', true
FROM "user" u WHERE u.email = 'pdv006@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Anh', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Xây dựng & Bất động sản', 350000.0, 1400000.0, true
FROM "user" u WHERE u.email = 'pdv006@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Anh ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    700000.0, 1400000.0, 2800000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv006@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Vũ Đình Trọng', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv006@demo.viettranslate.local';


-- PDV #07: Đặng Thùy Dương (pdv007@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Đặng Thùy Dương', 'pdv007@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000007', '/static/avatars/avatar_khoa.jpg', 'Bắc Ninh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Đặng Thùy Dương', phone = '0901000007', avatar_url = '/static/avatars/avatar_khoa.jpg', city = 'Bắc Ninh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Anh', 'Công nghệ thông tin & Phần mềm, Hội nghị & Sự kiện quốc tế', 'Tiếng Việt', 'Tiếng Anh',
    'Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng', 1, 400000.0, 2800000.0, 4.4,
    13, 10, 'Phiên dịch viên chuyên nghiệp với 1 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Anh, am hiểu sâu sắc thuật ngữ chuyên ngành Công nghệ thông tin & Phần mềm và Hội nghị & Sự kiện quốc tế. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Bắc Ninh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên triển vọng Tiếng Việt - Tiếng Anh | Chuyên ngành Công nghệ thông tin & Phần mềm', 'Phiên dịch viên Tiếng Anh – Công nghệ thông tin & Phần mềm', 'Cử nhân', 'Đại học Kinh tế Quốc dân (NEU)',
    'Kinh tế đối ngoại & Ngoại ngữ', 'TOEIC 985/990', 2021, 'Tập đoàn đa quốc gia ngành Công nghệ thông tin & Phần mềm, Đối tác FDI tại Bắc Ninh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Công nghệ thông tin & Phần mềm; Hội thảo xúc tiến thương mại Hội nghị & Sự kiện quốc tế', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv007@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Anh", "Tiếng Anh > Tiếng Việt"]', '["Công nghệ thông tin & Phần mềm", "Hội nghị & Sự kiện quốc tế"]', 'both', 'Bắc Ninh', 400000.0, 2800000.0, false
FROM "user" u WHERE u.email = 'pdv007@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Anh', 'Tiếng Việt > Tiếng Anh, Tiếng Anh > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Công nghệ thông tin & Phần mềm, Hội nghị & Sự kiện quốc tế', 'Bắc Ninh', 'both', true
FROM "user" u WHERE u.email = 'pdv007@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Anh', 'Đàm phán & Thương mại', 'Công nghệ thông tin & Phần mềm', 400000.0, 1600000.0, true
FROM "user" u WHERE u.email = 'pdv007@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Anh chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    800000.0, 1600000.0, 3200000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv007@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Đặng Thùy Dương', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv007@demo.viettranslate.local';


-- PDV #08: Bùi Quốc Anh (pdv008@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Bùi Quốc Anh', 'pdv008@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000008', '/static/avatars/avatar_nam.jpg', 'Quảng Ninh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Bùi Quốc Anh', phone = '0901000008', avatar_url = '/static/avatars/avatar_nam.jpg', city = 'Quảng Ninh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Anh, Tiếng Việt, Tiếng Đức', 'Giáo dục & Đào tạo, Đàm phán kinh doanh & Thương mại', 'Tiếng Anh', 'Tiếng Việt',
    'Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy', 2, 450000.0, 3100000.0, 4.5,
    6, 4, 'Phiên dịch viên chuyên nghiệp với 2 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Anh - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Giáo dục & Đào tạo và Đàm phán kinh doanh & Thương mại. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Quảng Ninh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên triển vọng Tiếng Anh - Tiếng Việt | Chuyên ngành Giáo dục & Đào tạo', 'Phiên dịch viên Tiếng Việt – Giáo dục & Đào tạo', 'Cử nhân', 'Học viện Ngoại giao (DAV)',
    'Quan hệ Quốc tế & Ngoại giao', 'IELTS 7.5 Academic', 2023, 'Tập đoàn đa quốc gia ngành Giáo dục & Đào tạo, Đối tác FDI tại Quảng Ninh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Giáo dục & Đào tạo; Hội thảo xúc tiến thương mại Đàm phán kinh doanh & Thương mại', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv008@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Anh > Tiếng Việt", "Tiếng Việt > Tiếng Anh"]', '["Giáo dục & Đào tạo", "Đàm phán kinh doanh & Thương mại"]', 'both', 'Quảng Ninh', 450000.0, 3100000.0, false
FROM "user" u WHERE u.email = 'pdv008@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Anh, Tiếng Việt, Tiếng Đức', 'Tiếng Anh > Tiếng Việt, Tiếng Việt > Tiếng Anh', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Giáo dục & Đào tạo, Đàm phán kinh doanh & Thương mại', 'Quảng Ninh', 'both', true
FROM "user" u WHERE u.email = 'pdv008@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Anh', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Giáo dục & Đào tạo', 450000.0, 1800000.0, true
FROM "user" u WHERE u.email = 'pdv008@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Anh ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    900000.0, 1800000.0, 3600000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv008@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Bùi Quốc Anh', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv008@demo.viettranslate.local';


-- PDV #09: Đỗ Thu Trang (pdv009@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Đỗ Thu Trang', 'pdv009@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000009', '/static/avatars/avatar_huy.jpg', 'Đồng Nai', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Đỗ Thu Trang', phone = '0901000009', avatar_url = '/static/avatars/avatar_huy.jpg', city = 'Đồng Nai', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Anh', 'Xuất nhập khẩu & Logistics, Pháp lý & Hợp đồng', 'Tiếng Việt', 'Tiếng Anh',
    'Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm', 1, 300000.0, 2200000.0, 4.6,
    9, 7, 'Phiên dịch viên chuyên nghiệp với 1 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Anh, am hiểu sâu sắc thuật ngữ chuyên ngành Xuất nhập khẩu & Logistics và Pháp lý & Hợp đồng. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Đồng Nai cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên triển vọng Tiếng Việt - Tiếng Anh | Chuyên ngành Xuất nhập khẩu & Logistics', 'Phiên dịch viên Tiếng Anh – Xuất nhập khẩu & Logistics', 'Cử nhân', 'Đại học Ngoại ngữ - ĐHQGHN',
    'Ngôn ngữ học ứng dụng', 'IELTS 8.5 Academic', 2022, 'Tập đoàn đa quốc gia ngành Xuất nhập khẩu & Logistics, Đối tác FDI tại Đồng Nai, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Xuất nhập khẩu & Logistics; Hội thảo xúc tiến thương mại Pháp lý & Hợp đồng', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Premium PDV'
FROM "user" u WHERE u.email = 'pdv009@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Anh", "Tiếng Anh > Tiếng Việt"]', '["Xuất nhập khẩu & Logistics", "Pháp lý & Hợp đồng"]', 'both', 'Đồng Nai', 300000.0, 2200000.0, false
FROM "user" u WHERE u.email = 'pdv009@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Anh', 'Tiếng Việt > Tiếng Anh, Tiếng Anh > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Xuất nhập khẩu & Logistics, Pháp lý & Hợp đồng', 'Đồng Nai', 'both', true
FROM "user" u WHERE u.email = 'pdv009@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Anh', 'Đàm phán & Thương mại', 'Xuất nhập khẩu & Logistics', 300000.0, 1200000.0, true
FROM "user" u WHERE u.email = 'pdv009@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Anh chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    600000.0, 1200000.0, 2400000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv009@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Đỗ Thu Trang', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv009@demo.viettranslate.local';


-- PDV #10: Ngô Thành Nam (pdv010@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Ngô Thành Nam', 'pdv010@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000010', '/static/avatars/avatar_lananh.jpg', 'Vũng Tàu', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Ngô Thành Nam', phone = '0901000010', avatar_url = '/static/avatars/avatar_lananh.jpg', city = 'Vũng Tàu', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Anh, Tiếng Việt', 'Tài chính & Ngân hàng, Y tế & Chăm sóc sức khỏe', 'Tiếng Anh', 'Tiếng Việt',
    'Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương', 2, 350000.0, 2500000.0, 4.7,
    12, 9, 'Phiên dịch viên chuyên nghiệp với 2 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Anh - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Tài chính & Ngân hàng và Y tế & Chăm sóc sức khỏe. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Vũng Tàu cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên triển vọng Tiếng Anh - Tiếng Việt | Chuyên ngành Tài chính & Ngân hàng', 'Phiên dịch viên Tiếng Việt – Tài chính & Ngân hàng', 'Cử nhân', 'Đại học Ngoại thương (FTU)',
    'Tiếng Anh Thương mại', 'IELTS 8.0 Academic', 2023, 'Tập đoàn đa quốc gia ngành Tài chính & Ngân hàng, Đối tác FDI tại Vũng Tàu, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Tài chính & Ngân hàng; Hội thảo xúc tiến thương mại Y tế & Chăm sóc sức khỏe', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv010@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Anh > Tiếng Việt", "Tiếng Việt > Tiếng Anh"]', '["Tài chính & Ngân hàng", "Y tế & Chăm sóc sức khỏe"]', 'both', 'Vũng Tàu', 350000.0, 2500000.0, false
FROM "user" u WHERE u.email = 'pdv010@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Anh, Tiếng Việt', 'Tiếng Anh > Tiếng Việt, Tiếng Việt > Tiếng Anh', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Tài chính & Ngân hàng, Y tế & Chăm sóc sức khỏe', 'Vũng Tàu', 'both', true
FROM "user" u WHERE u.email = 'pdv010@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Anh', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Tài chính & Ngân hàng', 350000.0, 1400000.0, true
FROM "user" u WHERE u.email = 'pdv010@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Anh ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    700000.0, 1400000.0, 2800000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv010@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Ngô Thành Nam', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv010@demo.viettranslate.local';


-- PDV #11: Dương Cẩm Tú (pdv011@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Dương Cẩm Tú', 'pdv011@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000011', '/static/avatars/avatar_dung.jpg', 'Hà Nội', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Dương Cẩm Tú', phone = '0901000011', avatar_url = '/static/avatars/avatar_dung.jpg', city = 'Hà Nội', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Trung', 'Năng lượng & Dầu khí, Du lịch & Khách sạn', 'Tiếng Việt', 'Tiếng Trung',
    'Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)', 3, 600000.0, 4200000.0, 4.5,
    15, 11, 'Phiên dịch viên chuyên nghiệp với 3 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Trung, am hiểu sâu sắc thuật ngữ chuyên ngành Năng lượng & Dầu khí và Du lịch & Khách sạn. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Hà Nội cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Việt - Tiếng Trung | Chuyên ngành Năng lượng & Dầu khí', 'Phiên dịch viên Tiếng Trung – Năng lượng & Dầu khí', 'Thạc sĩ', 'Đại học Hà Nội (HANU)',
    'Biên phiên dịch Chuyên nghiệp', 'HSK 5 (260/300)', 2021, 'Tập đoàn đa quốc gia ngành Năng lượng & Dầu khí, Đối tác FDI tại Hà Nội, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Năng lượng & Dầu khí; Hội thảo xúc tiến thương mại Du lịch & Khách sạn', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv011@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Trung", "Tiếng Trung > Tiếng Việt"]', '["Năng lượng & Dầu khí", "Du lịch & Khách sạn"]', 'both', 'Hà Nội', 600000.0, 4200000.0, false
FROM "user" u WHERE u.email = 'pdv011@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Trung', 'Tiếng Việt > Tiếng Trung, Tiếng Trung > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Năng lượng & Dầu khí, Du lịch & Khách sạn', 'Hà Nội', 'both', true
FROM "user" u WHERE u.email = 'pdv011@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Trung', 'Đàm phán & Thương mại', 'Năng lượng & Dầu khí', 600000.0, 2400000.0, true
FROM "user" u WHERE u.email = 'pdv011@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Trung chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1200000.0, 2400000.0, 4800000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv011@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Dương Cẩm Tú', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv011@demo.viettranslate.local';


-- PDV #12: Lý Gia Bảo (pdv012@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Lý Gia Bảo', 'pdv012@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000012', '/static/avatars/avatar_ha.jpg', 'TP. Hồ Chí Minh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Lý Gia Bảo', phone = '0901000012', avatar_url = '/static/avatars/avatar_ha.jpg', city = 'TP. Hồ Chí Minh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Trung, Tiếng Việt', 'Hội nghị & Sự kiện quốc tế, Sản xuất & Kỹ thuật công nghiệp', 'Tiếng Trung', 'Tiếng Việt',
    'Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng', 4, 680000.0, 4600000.0, 4.8,
    17, 12, 'Phiên dịch viên chuyên nghiệp với 4 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Trung - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Hội nghị & Sự kiện quốc tế và Sản xuất & Kỹ thuật công nghiệp. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực TP. Hồ Chí Minh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Trung - Tiếng Việt | Chuyên ngành Hội nghị & Sự kiện quốc tế', 'Phiên dịch viên Tiếng Việt – Hội nghị & Sự kiện quốc tế', 'Cử nhân', 'Đại học KHXH&NV - ĐHQG TP.HCM',
    'Ngôn ngữ & Văn hóa Quốc tế', 'HSK 6', 2024, 'Tập đoàn đa quốc gia ngành Hội nghị & Sự kiện quốc tế, Đối tác FDI tại TP. Hồ Chí Minh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Hội nghị & Sự kiện quốc tế; Hội thảo xúc tiến thương mại Sản xuất & Kỹ thuật công nghiệp', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv012@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Trung > Tiếng Việt", "Tiếng Việt > Tiếng Trung"]', '["Hội nghị & Sự kiện quốc tế", "Sản xuất & Kỹ thuật công nghiệp"]', 'both', 'TP. Hồ Chí Minh', 680000.0, 4600000.0, false
FROM "user" u WHERE u.email = 'pdv012@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Trung, Tiếng Việt', 'Tiếng Trung > Tiếng Việt, Tiếng Việt > Tiếng Trung', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Hội nghị & Sự kiện quốc tế, Sản xuất & Kỹ thuật công nghiệp', 'TP. Hồ Chí Minh', 'both', true
FROM "user" u WHERE u.email = 'pdv012@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Trung', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Hội nghị & Sự kiện quốc tế', 680000.0, 2720000.0, true
FROM "user" u WHERE u.email = 'pdv012@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Trung ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1360000.0, 2720000.0, 5440000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv012@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Lý Gia Bảo', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv012@demo.viettranslate.local';


-- PDV #13: Phan Thanh Trúc (pdv013@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Phan Thanh Trúc', 'pdv013@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000013', '/static/avatars/avatar_bich.jpg', 'Đà Nẵng', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Phan Thanh Trúc', phone = '0901000013', avatar_url = '/static/avatars/avatar_bich.jpg', city = 'Đà Nẵng', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Trung, Tiếng Anh', 'Đàm phán kinh doanh & Thương mại, Xây dựng & Bất động sản', 'Tiếng Việt', 'Tiếng Trung',
    'Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy', 5, 760000.0, 5000000.0, 4.7,
    19, 14, 'Phiên dịch viên chuyên nghiệp với 5 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Trung, am hiểu sâu sắc thuật ngữ chuyên ngành Đàm phán kinh doanh & Thương mại và Xây dựng & Bất động sản. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Đà Nẵng cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Việt - Tiếng Trung | Chuyên ngành Đàm phán kinh doanh & Thương mại', 'Phiên dịch viên Tiếng Trung – Đàm phán kinh doanh & Thương mại', 'Cử nhân', 'Đại học Bách Khoa Hà Nội',
    'Kỹ thuật & Ngoại ngữ chuyên ngành', 'HSK 6 (285/300) & HSKK Cao cấp', 2022, 'Tập đoàn đa quốc gia ngành Đàm phán kinh doanh & Thương mại, Đối tác FDI tại Đà Nẵng, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Đàm phán kinh doanh & Thương mại; Hội thảo xúc tiến thương mại Xây dựng & Bất động sản', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Premium PDV'
FROM "user" u WHERE u.email = 'pdv013@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Trung", "Tiếng Trung > Tiếng Việt"]', '["Đàm phán kinh doanh & Thương mại", "Xây dựng & Bất động sản"]', 'both', 'Đà Nẵng', 760000.0, 5000000.0, false
FROM "user" u WHERE u.email = 'pdv013@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Trung, Tiếng Anh', 'Tiếng Việt > Tiếng Trung, Tiếng Trung > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Đàm phán kinh doanh & Thương mại, Xây dựng & Bất động sản', 'Đà Nẵng', 'both', true
FROM "user" u WHERE u.email = 'pdv013@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Trung', 'Đàm phán & Thương mại', 'Đàm phán kinh doanh & Thương mại', 760000.0, 3040000.0, true
FROM "user" u WHERE u.email = 'pdv013@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Trung chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1520000.0, 3040000.0, 6080000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv013@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Phan Thanh Trúc', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv013@demo.viettranslate.local';


-- PDV #14: Võ Hữu Phước (pdv014@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Võ Hữu Phước', 'pdv014@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000014', '/static/avatars/avatar_cuong.jpg', 'Hải Phòng', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Võ Hữu Phước', phone = '0901000014', avatar_url = '/static/avatars/avatar_cuong.jpg', city = 'Hải Phòng', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Trung, Tiếng Việt', 'Pháp lý & Hợp đồng, Công nghệ thông tin & Phần mềm', 'Tiếng Trung', 'Tiếng Việt',
    'Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm', 3, 840000.0, 5400000.0, 4.6,
    21, 15, 'Phiên dịch viên chuyên nghiệp với 3 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Trung - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Pháp lý & Hợp đồng và Công nghệ thông tin & Phần mềm. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Hải Phòng cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Trung - Tiếng Việt | Chuyên ngành Pháp lý & Hợp đồng', 'Phiên dịch viên Tiếng Việt – Pháp lý & Hợp đồng', 'Thạc sĩ', 'Đại học Sư phạm TP.HCM',
    'Sư phạm & Dịch thuật Ngoại ngữ', 'HSK 6 (270/300)', 2023, 'Tập đoàn đa quốc gia ngành Pháp lý & Hợp đồng, Đối tác FDI tại Hải Phòng, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Pháp lý & Hợp đồng; Hội thảo xúc tiến thương mại Công nghệ thông tin & Phần mềm', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv014@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Trung > Tiếng Việt", "Tiếng Việt > Tiếng Trung"]', '["Pháp lý & Hợp đồng", "Công nghệ thông tin & Phần mềm"]', 'both', 'Hải Phòng', 840000.0, 5400000.0, false
FROM "user" u WHERE u.email = 'pdv014@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Trung, Tiếng Việt', 'Tiếng Trung > Tiếng Việt, Tiếng Việt > Tiếng Trung', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Pháp lý & Hợp đồng, Công nghệ thông tin & Phần mềm', 'Hải Phòng', 'both', true
FROM "user" u WHERE u.email = 'pdv014@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Trung', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Pháp lý & Hợp đồng', 840000.0, 3360000.0, true
FROM "user" u WHERE u.email = 'pdv014@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Trung ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1680000.0, 3360000.0, 6720000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv014@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Võ Hữu Phước', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv014@demo.viettranslate.local';


-- PDV #15: Trịnh Bảo Ngọc (pdv015@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Trịnh Bảo Ngọc', 'pdv015@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000015', '/static/avatars/avatar_duc.jpg', 'Cần Thơ', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Trịnh Bảo Ngọc', phone = '0901000015', avatar_url = '/static/avatars/avatar_duc.jpg', city = 'Cần Thơ', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Trung', 'Y tế & Chăm sóc sức khỏe, Giáo dục & Đào tạo', 'Tiếng Việt', 'Tiếng Trung',
    'Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương', 4, 920000.0, 5800000.0, 4.5,
    23, 17, 'Phiên dịch viên chuyên nghiệp với 4 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Trung, am hiểu sâu sắc thuật ngữ chuyên ngành Y tế & Chăm sóc sức khỏe và Giáo dục & Đào tạo. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Cần Thơ cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Việt - Tiếng Trung | Chuyên ngành Y tế & Chăm sóc sức khỏe', 'Phiên dịch viên Tiếng Trung – Y tế & Chăm sóc sức khỏe', 'Cử nhân', 'Đại học Kinh tế Quốc dân (NEU)',
    'Kinh tế đối ngoại & Ngoại ngữ', 'HSK 5 (260/300)', 2021, 'Tập đoàn đa quốc gia ngành Y tế & Chăm sóc sức khỏe, Đối tác FDI tại Cần Thơ, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Y tế & Chăm sóc sức khỏe; Hội thảo xúc tiến thương mại Giáo dục & Đào tạo', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv015@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Trung", "Tiếng Trung > Tiếng Việt"]', '["Y tế & Chăm sóc sức khỏe", "Giáo dục & Đào tạo"]', 'both', 'Cần Thơ', 920000.0, 5800000.0, false
FROM "user" u WHERE u.email = 'pdv015@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Trung', 'Tiếng Việt > Tiếng Trung, Tiếng Trung > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Y tế & Chăm sóc sức khỏe, Giáo dục & Đào tạo', 'Cần Thơ', 'both', true
FROM "user" u WHERE u.email = 'pdv015@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Trung', 'Đàm phán & Thương mại', 'Y tế & Chăm sóc sức khỏe', 920000.0, 3680000.0, true
FROM "user" u WHERE u.email = 'pdv015@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Trung chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1840000.0, 3680000.0, 7360000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv015@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Trịnh Bảo Ngọc', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv015@demo.viettranslate.local';


-- PDV #16: Mai Anh Dũng (pdv016@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Mai Anh Dũng', 'pdv016@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000016', '/static/avatars/avatar_huong.jpg', 'Bình Dương', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Mai Anh Dũng', phone = '0901000016', avatar_url = '/static/avatars/avatar_huong.jpg', city = 'Bình Dương', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Trung, Tiếng Việt', 'Du lịch & Khách sạn, Xuất nhập khẩu & Logistics', 'Tiếng Trung', 'Tiếng Việt',
    'Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)', 5, 600000.0, 4200000.0, 4.8,
    25, 18, 'Phiên dịch viên chuyên nghiệp với 5 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Trung - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Du lịch & Khách sạn và Xuất nhập khẩu & Logistics. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Bình Dương cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Trung - Tiếng Việt | Chuyên ngành Du lịch & Khách sạn', 'Phiên dịch viên Tiếng Việt – Du lịch & Khách sạn', 'Cử nhân', 'Học viện Ngoại giao (DAV)',
    'Quan hệ Quốc tế & Ngoại giao', 'HSK 6', 2024, 'Tập đoàn đa quốc gia ngành Du lịch & Khách sạn, Đối tác FDI tại Bình Dương, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Du lịch & Khách sạn; Hội thảo xúc tiến thương mại Xuất nhập khẩu & Logistics', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Top Rated'
FROM "user" u WHERE u.email = 'pdv016@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Trung > Tiếng Việt", "Tiếng Việt > Tiếng Trung"]', '["Du lịch & Khách sạn", "Xuất nhập khẩu & Logistics"]', 'both', 'Bình Dương', 600000.0, 4200000.0, false
FROM "user" u WHERE u.email = 'pdv016@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Trung, Tiếng Việt', 'Tiếng Trung > Tiếng Việt, Tiếng Việt > Tiếng Trung', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Du lịch & Khách sạn, Xuất nhập khẩu & Logistics', 'Bình Dương', 'both', true
FROM "user" u WHERE u.email = 'pdv016@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Trung', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Du lịch & Khách sạn', 600000.0, 2400000.0, true
FROM "user" u WHERE u.email = 'pdv016@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Trung ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1200000.0, 2400000.0, 4800000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv016@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Mai Anh Dũng', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv016@demo.viettranslate.local';


-- PDV #17: Đoàn Mỹ Linh (pdv017@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Đoàn Mỹ Linh', 'pdv017@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000017', '/static/avatars/avatar_khoa.jpg', 'Bắc Ninh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Đoàn Mỹ Linh', phone = '0901000017', avatar_url = '/static/avatars/avatar_khoa.jpg', city = 'Bắc Ninh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Trung', 'Sản xuất & Kỹ thuật công nghiệp, Tài chính & Ngân hàng', 'Tiếng Việt', 'Tiếng Trung',
    'Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng', 3, 680000.0, 4600000.0, 4.7,
    27, 20, 'Phiên dịch viên chuyên nghiệp với 3 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Trung, am hiểu sâu sắc thuật ngữ chuyên ngành Sản xuất & Kỹ thuật công nghiệp và Tài chính & Ngân hàng. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Bắc Ninh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Việt - Tiếng Trung | Chuyên ngành Sản xuất & Kỹ thuật công nghiệp', 'Phiên dịch viên Tiếng Trung – Sản xuất & Kỹ thuật công nghiệp', 'Thạc sĩ', 'Đại học Ngoại ngữ - ĐHQGHN',
    'Ngôn ngữ học ứng dụng', 'HSK 6 (285/300) & HSKK Cao cấp', 2022, 'Tập đoàn đa quốc gia ngành Sản xuất & Kỹ thuật công nghiệp, Đối tác FDI tại Bắc Ninh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Sản xuất & Kỹ thuật công nghiệp; Hội thảo xúc tiến thương mại Tài chính & Ngân hàng', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Premium PDV'
FROM "user" u WHERE u.email = 'pdv017@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Trung", "Tiếng Trung > Tiếng Việt"]', '["Sản xuất & Kỹ thuật công nghiệp", "Tài chính & Ngân hàng"]', 'both', 'Bắc Ninh', 680000.0, 4600000.0, false
FROM "user" u WHERE u.email = 'pdv017@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Trung', 'Tiếng Việt > Tiếng Trung, Tiếng Trung > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Sản xuất & Kỹ thuật công nghiệp, Tài chính & Ngân hàng', 'Bắc Ninh', 'both', true
FROM "user" u WHERE u.email = 'pdv017@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Trung', 'Đàm phán & Thương mại', 'Sản xuất & Kỹ thuật công nghiệp', 680000.0, 2720000.0, true
FROM "user" u WHERE u.email = 'pdv017@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Trung chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1360000.0, 2720000.0, 5440000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv017@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Đoàn Mỹ Linh', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv017@demo.viettranslate.local';


-- PDV #18: Lâm Quang Huy (pdv018@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Lâm Quang Huy', 'pdv018@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000018', '/static/avatars/avatar_nam.jpg', 'Quảng Ninh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Lâm Quang Huy', phone = '0901000018', avatar_url = '/static/avatars/avatar_nam.jpg', city = 'Quảng Ninh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Trung, Tiếng Việt', 'Xây dựng & Bất động sản, Năng lượng & Dầu khí', 'Tiếng Trung', 'Tiếng Việt',
    'Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy', 4, 760000.0, 5000000.0, 4.6,
    29, 21, 'Phiên dịch viên chuyên nghiệp với 4 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Trung - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Xây dựng & Bất động sản và Năng lượng & Dầu khí. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Quảng Ninh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Trung - Tiếng Việt | Chuyên ngành Xây dựng & Bất động sản', 'Phiên dịch viên Tiếng Việt – Xây dựng & Bất động sản', 'Cử nhân', 'Đại học Ngoại thương (FTU)',
    'Tiếng Anh Thương mại', 'HSK 6 (270/300)', 2023, 'Tập đoàn đa quốc gia ngành Xây dựng & Bất động sản, Đối tác FDI tại Quảng Ninh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Xây dựng & Bất động sản; Hội thảo xúc tiến thương mại Năng lượng & Dầu khí', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv018@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Trung > Tiếng Việt", "Tiếng Việt > Tiếng Trung"]', '["Xây dựng & Bất động sản", "Năng lượng & Dầu khí"]', 'both', 'Quảng Ninh', 760000.0, 5000000.0, false
FROM "user" u WHERE u.email = 'pdv018@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Trung, Tiếng Việt', 'Tiếng Trung > Tiếng Việt, Tiếng Việt > Tiếng Trung', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Xây dựng & Bất động sản, Năng lượng & Dầu khí', 'Quảng Ninh', 'both', true
FROM "user" u WHERE u.email = 'pdv018@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Trung', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Xây dựng & Bất động sản', 760000.0, 3040000.0, true
FROM "user" u WHERE u.email = 'pdv018@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Trung ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1520000.0, 3040000.0, 6080000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv018@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Lâm Quang Huy', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv018@demo.viettranslate.local';


-- PDV #19: Lương Thục Quyên (pdv019@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Lương Thục Quyên', 'pdv019@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000019', '/static/avatars/avatar_huy.jpg', 'Đồng Nai', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Lương Thục Quyên', phone = '0901000019', avatar_url = '/static/avatars/avatar_huy.jpg', city = 'Đồng Nai', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Nhật', 'Công nghệ thông tin & Phần mềm, Hội nghị & Sự kiện quốc tế', 'Tiếng Việt', 'Tiếng Nhật',
    'Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm', 5, 840000.0, 5400000.0, 4.5,
    31, 23, 'Phiên dịch viên chuyên nghiệp với 5 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Nhật, am hiểu sâu sắc thuật ngữ chuyên ngành Công nghệ thông tin & Phần mềm và Hội nghị & Sự kiện quốc tế. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Đồng Nai cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Việt - Tiếng Nhật | Chuyên ngành Công nghệ thông tin & Phần mềm', 'Phiên dịch viên Tiếng Nhật – Công nghệ thông tin & Phần mềm', 'Cử nhân', 'Đại học Hà Nội (HANU)',
    'Biên phiên dịch Chuyên nghiệp', 'JLPT N2 (165/180)', 2021, 'Tập đoàn đa quốc gia ngành Công nghệ thông tin & Phần mềm, Đối tác FDI tại Đồng Nai, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Công nghệ thông tin & Phần mềm; Hội thảo xúc tiến thương mại Hội nghị & Sự kiện quốc tế', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv019@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Nhật", "Tiếng Nhật > Tiếng Việt"]', '["Công nghệ thông tin & Phần mềm", "Hội nghị & Sự kiện quốc tế"]', 'both', 'Đồng Nai', 840000.0, 5400000.0, false
FROM "user" u WHERE u.email = 'pdv019@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Nhật', 'Tiếng Việt > Tiếng Nhật, Tiếng Nhật > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Công nghệ thông tin & Phần mềm, Hội nghị & Sự kiện quốc tế', 'Đồng Nai', 'both', true
FROM "user" u WHERE u.email = 'pdv019@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Nhật', 'Đàm phán & Thương mại', 'Công nghệ thông tin & Phần mềm', 840000.0, 3360000.0, true
FROM "user" u WHERE u.email = 'pdv019@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Nhật chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1680000.0, 3360000.0, 6720000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv019@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Lương Thục Quyên', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv019@demo.viettranslate.local';


-- PDV #20: Chu Mạnh Cường (pdv020@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Chu Mạnh Cường', 'pdv020@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000020', '/static/avatars/avatar_lananh.jpg', 'Vũng Tàu', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Chu Mạnh Cường', phone = '0901000020', avatar_url = '/static/avatars/avatar_lananh.jpg', city = 'Vũng Tàu', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Nhật, Tiếng Việt', 'Giáo dục & Đào tạo, Đàm phán kinh doanh & Thương mại', 'Tiếng Nhật', 'Tiếng Việt',
    'Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương', 3, 920000.0, 5800000.0, 4.8,
    33, 24, 'Phiên dịch viên chuyên nghiệp với 3 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Nhật - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Giáo dục & Đào tạo và Đàm phán kinh doanh & Thương mại. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Vũng Tàu cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Nhật - Tiếng Việt | Chuyên ngành Giáo dục & Đào tạo', 'Phiên dịch viên Tiếng Việt – Giáo dục & Đào tạo', 'Thạc sĩ', 'Đại học KHXH&NV - ĐHQG TP.HCM',
    'Ngôn ngữ & Văn hóa Quốc tế', 'JLPT N1', 2024, 'Tập đoàn đa quốc gia ngành Giáo dục & Đào tạo, Đối tác FDI tại Vũng Tàu, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Giáo dục & Đào tạo; Hội thảo xúc tiến thương mại Đàm phán kinh doanh & Thương mại', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Top Rated'
FROM "user" u WHERE u.email = 'pdv020@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Nhật > Tiếng Việt", "Tiếng Việt > Tiếng Nhật"]', '["Giáo dục & Đào tạo", "Đàm phán kinh doanh & Thương mại"]', 'both', 'Vũng Tàu', 920000.0, 5800000.0, false
FROM "user" u WHERE u.email = 'pdv020@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Nhật, Tiếng Việt', 'Tiếng Nhật > Tiếng Việt, Tiếng Việt > Tiếng Nhật', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Giáo dục & Đào tạo, Đàm phán kinh doanh & Thương mại', 'Vũng Tàu', 'both', true
FROM "user" u WHERE u.email = 'pdv020@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Nhật', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Giáo dục & Đào tạo', 920000.0, 3680000.0, true
FROM "user" u WHERE u.email = 'pdv020@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Nhật ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1840000.0, 3680000.0, 7360000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv020@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Chu Mạnh Cường', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv020@demo.viettranslate.local';


-- PDV #21: Cao Thị Kim Oanh (pdv021@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Cao Thị Kim Oanh', 'pdv021@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000021', '/static/avatars/avatar_dung.jpg', 'Hà Nội', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Cao Thị Kim Oanh', phone = '0901000021', avatar_url = '/static/avatars/avatar_dung.jpg', city = 'Hà Nội', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Nhật, Tiếng Anh', 'Xuất nhập khẩu & Logistics, Pháp lý & Hợp đồng', 'Tiếng Việt', 'Tiếng Nhật',
    'Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)', 4, 600000.0, 4200000.0, 4.7,
    15, 11, 'Phiên dịch viên chuyên nghiệp với 4 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Nhật, am hiểu sâu sắc thuật ngữ chuyên ngành Xuất nhập khẩu & Logistics và Pháp lý & Hợp đồng. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Hà Nội cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Việt - Tiếng Nhật | Chuyên ngành Xuất nhập khẩu & Logistics', 'Phiên dịch viên Tiếng Nhật – Xuất nhập khẩu & Logistics', 'Cử nhân', 'Đại học Bách Khoa Hà Nội',
    'Kỹ thuật & Ngoại ngữ chuyên ngành', 'JLPT N1 (172/180)', 2022, 'Tập đoàn đa quốc gia ngành Xuất nhập khẩu & Logistics, Đối tác FDI tại Hà Nội, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Xuất nhập khẩu & Logistics; Hội thảo xúc tiến thương mại Pháp lý & Hợp đồng', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Premium PDV'
FROM "user" u WHERE u.email = 'pdv021@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Nhật", "Tiếng Nhật > Tiếng Việt"]', '["Xuất nhập khẩu & Logistics", "Pháp lý & Hợp đồng"]', 'both', 'Hà Nội', 600000.0, 4200000.0, false
FROM "user" u WHERE u.email = 'pdv021@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Nhật, Tiếng Anh', 'Tiếng Việt > Tiếng Nhật, Tiếng Nhật > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Xuất nhập khẩu & Logistics, Pháp lý & Hợp đồng', 'Hà Nội', 'both', true
FROM "user" u WHERE u.email = 'pdv021@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Nhật', 'Đàm phán & Thương mại', 'Xuất nhập khẩu & Logistics', 600000.0, 2400000.0, true
FROM "user" u WHERE u.email = 'pdv021@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Nhật chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1200000.0, 2400000.0, 4800000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv021@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Cao Thị Kim Oanh', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv021@demo.viettranslate.local';


-- PDV #22: Tạ Nhật Minh (pdv022@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Tạ Nhật Minh', 'pdv022@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000022', '/static/avatars/avatar_ha.jpg', 'TP. Hồ Chí Minh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Tạ Nhật Minh', phone = '0901000022', avatar_url = '/static/avatars/avatar_ha.jpg', city = 'TP. Hồ Chí Minh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Nhật, Tiếng Việt', 'Tài chính & Ngân hàng, Y tế & Chăm sóc sức khỏe', 'Tiếng Nhật', 'Tiếng Việt',
    'Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng', 5, 680000.0, 4600000.0, 4.6,
    17, 12, 'Phiên dịch viên chuyên nghiệp với 5 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Nhật - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Tài chính & Ngân hàng và Y tế & Chăm sóc sức khỏe. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực TP. Hồ Chí Minh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Nhật - Tiếng Việt | Chuyên ngành Tài chính & Ngân hàng', 'Phiên dịch viên Tiếng Việt – Tài chính & Ngân hàng', 'Cử nhân', 'Đại học Sư phạm TP.HCM',
    'Sư phạm & Dịch thuật Ngoại ngữ', 'JLPT N1 (160/180)', 2023, 'Tập đoàn đa quốc gia ngành Tài chính & Ngân hàng, Đối tác FDI tại TP. Hồ Chí Minh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Tài chính & Ngân hàng; Hội thảo xúc tiến thương mại Y tế & Chăm sóc sức khỏe', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv022@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Nhật > Tiếng Việt", "Tiếng Việt > Tiếng Nhật"]', '["Tài chính & Ngân hàng", "Y tế & Chăm sóc sức khỏe"]', 'both', 'TP. Hồ Chí Minh', 680000.0, 4600000.0, false
FROM "user" u WHERE u.email = 'pdv022@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Nhật, Tiếng Việt', 'Tiếng Nhật > Tiếng Việt, Tiếng Việt > Tiếng Nhật', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Tài chính & Ngân hàng, Y tế & Chăm sóc sức khỏe', 'TP. Hồ Chí Minh', 'both', true
FROM "user" u WHERE u.email = 'pdv022@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Nhật', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Tài chính & Ngân hàng', 680000.0, 2720000.0, true
FROM "user" u WHERE u.email = 'pdv022@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Nhật ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1360000.0, 2720000.0, 5440000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv022@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Tạ Nhật Minh', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv022@demo.viettranslate.local';


-- PDV #23: Hà Quỳnh Nga (pdv023@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Hà Quỳnh Nga', 'pdv023@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000023', '/static/avatars/avatar_bich.jpg', 'Đà Nẵng', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Hà Quỳnh Nga', phone = '0901000023', avatar_url = '/static/avatars/avatar_bich.jpg', city = 'Đà Nẵng', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Nhật', 'Năng lượng & Dầu khí, Du lịch & Khách sạn', 'Tiếng Việt', 'Tiếng Nhật',
    'Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy', 3, 760000.0, 5000000.0, 4.5,
    19, 14, 'Phiên dịch viên chuyên nghiệp với 3 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Nhật, am hiểu sâu sắc thuật ngữ chuyên ngành Năng lượng & Dầu khí và Du lịch & Khách sạn. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Đà Nẵng cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Việt - Tiếng Nhật | Chuyên ngành Năng lượng & Dầu khí', 'Phiên dịch viên Tiếng Nhật – Năng lượng & Dầu khí', 'Thạc sĩ', 'Đại học Kinh tế Quốc dân (NEU)',
    'Kinh tế đối ngoại & Ngoại ngữ', 'JLPT N2 (165/180)', 2021, 'Tập đoàn đa quốc gia ngành Năng lượng & Dầu khí, Đối tác FDI tại Đà Nẵng, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Năng lượng & Dầu khí; Hội thảo xúc tiến thương mại Du lịch & Khách sạn', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv023@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Nhật", "Tiếng Nhật > Tiếng Việt"]', '["Năng lượng & Dầu khí", "Du lịch & Khách sạn"]', 'both', 'Đà Nẵng', 760000.0, 5000000.0, false
FROM "user" u WHERE u.email = 'pdv023@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Nhật', 'Tiếng Việt > Tiếng Nhật, Tiếng Nhật > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Năng lượng & Dầu khí, Du lịch & Khách sạn', 'Đà Nẵng', 'both', true
FROM "user" u WHERE u.email = 'pdv023@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Nhật', 'Đàm phán & Thương mại', 'Năng lượng & Dầu khí', 760000.0, 3040000.0, true
FROM "user" u WHERE u.email = 'pdv023@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Nhật chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1520000.0, 3040000.0, 6080000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv023@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Hà Quỳnh Nga', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv023@demo.viettranslate.local';


-- PDV #24: Phùng Thế Vinh (pdv024@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Phùng Thế Vinh', 'pdv024@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000024', '/static/avatars/avatar_cuong.jpg', 'Hải Phòng', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Phùng Thế Vinh', phone = '0901000024', avatar_url = '/static/avatars/avatar_cuong.jpg', city = 'Hải Phòng', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Nhật, Tiếng Việt', 'Hội nghị & Sự kiện quốc tế, Sản xuất & Kỹ thuật công nghiệp', 'Tiếng Nhật', 'Tiếng Việt',
    'Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm', 4, 840000.0, 5400000.0, 4.8,
    21, 15, 'Phiên dịch viên chuyên nghiệp với 4 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Nhật - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Hội nghị & Sự kiện quốc tế và Sản xuất & Kỹ thuật công nghiệp. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Hải Phòng cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Nhật - Tiếng Việt | Chuyên ngành Hội nghị & Sự kiện quốc tế', 'Phiên dịch viên Tiếng Việt – Hội nghị & Sự kiện quốc tế', 'Cử nhân', 'Học viện Ngoại giao (DAV)',
    'Quan hệ Quốc tế & Ngoại giao', 'JLPT N1', 2024, 'Tập đoàn đa quốc gia ngành Hội nghị & Sự kiện quốc tế, Đối tác FDI tại Hải Phòng, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Hội nghị & Sự kiện quốc tế; Hội thảo xúc tiến thương mại Sản xuất & Kỹ thuật công nghiệp', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv024@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Nhật > Tiếng Việt", "Tiếng Việt > Tiếng Nhật"]', '["Hội nghị & Sự kiện quốc tế", "Sản xuất & Kỹ thuật công nghiệp"]', 'both', 'Hải Phòng', 840000.0, 5400000.0, false
FROM "user" u WHERE u.email = 'pdv024@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Nhật, Tiếng Việt', 'Tiếng Nhật > Tiếng Việt, Tiếng Việt > Tiếng Nhật', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Hội nghị & Sự kiện quốc tế, Sản xuất & Kỹ thuật công nghiệp', 'Hải Phòng', 'both', true
FROM "user" u WHERE u.email = 'pdv024@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Nhật', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Hội nghị & Sự kiện quốc tế', 840000.0, 3360000.0, true
FROM "user" u WHERE u.email = 'pdv024@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Nhật ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1680000.0, 3360000.0, 6720000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv024@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Phùng Thế Vinh', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv024@demo.viettranslate.local';


-- PDV #25: Tô Ánh Nguyệt (pdv025@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Tô Ánh Nguyệt', 'pdv025@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000025', '/static/avatars/avatar_duc.jpg', 'Cần Thơ', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Tô Ánh Nguyệt', phone = '0901000025', avatar_url = '/static/avatars/avatar_duc.jpg', city = 'Cần Thơ', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Nhật', 'Đàm phán kinh doanh & Thương mại, Xây dựng & Bất động sản', 'Tiếng Việt', 'Tiếng Nhật',
    'Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương', 5, 920000.0, 5800000.0, 4.7,
    23, 17, 'Phiên dịch viên chuyên nghiệp với 5 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Nhật, am hiểu sâu sắc thuật ngữ chuyên ngành Đàm phán kinh doanh & Thương mại và Xây dựng & Bất động sản. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Cần Thơ cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Việt - Tiếng Nhật | Chuyên ngành Đàm phán kinh doanh & Thương mại', 'Phiên dịch viên Tiếng Nhật – Đàm phán kinh doanh & Thương mại', 'Cử nhân', 'Đại học Ngoại ngữ - ĐHQGHN',
    'Ngôn ngữ học ứng dụng', 'JLPT N1 (172/180)', 2022, 'Tập đoàn đa quốc gia ngành Đàm phán kinh doanh & Thương mại, Đối tác FDI tại Cần Thơ, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Đàm phán kinh doanh & Thương mại; Hội thảo xúc tiến thương mại Xây dựng & Bất động sản', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Premium PDV'
FROM "user" u WHERE u.email = 'pdv025@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Nhật", "Tiếng Nhật > Tiếng Việt"]', '["Đàm phán kinh doanh & Thương mại", "Xây dựng & Bất động sản"]', 'both', 'Cần Thơ', 920000.0, 5800000.0, false
FROM "user" u WHERE u.email = 'pdv025@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Nhật', 'Tiếng Việt > Tiếng Nhật, Tiếng Nhật > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Đàm phán kinh doanh & Thương mại, Xây dựng & Bất động sản', 'Cần Thơ', 'both', true
FROM "user" u WHERE u.email = 'pdv025@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Nhật', 'Đàm phán & Thương mại', 'Đàm phán kinh doanh & Thương mại', 920000.0, 3680000.0, true
FROM "user" u WHERE u.email = 'pdv025@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Nhật chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1840000.0, 3680000.0, 7360000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv025@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Tô Ánh Nguyệt', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv025@demo.viettranslate.local';


-- PDV #26: Đinh Hữu Đạt (pdv026@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Đinh Hữu Đạt', 'pdv026@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000026', '/static/avatars/avatar_huong.jpg', 'Bình Dương', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Đinh Hữu Đạt', phone = '0901000026', avatar_url = '/static/avatars/avatar_huong.jpg', city = 'Bình Dương', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Nhật, Tiếng Việt', 'Pháp lý & Hợp đồng, Công nghệ thông tin & Phần mềm', 'Tiếng Nhật', 'Tiếng Việt',
    'Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)', 3, 600000.0, 4200000.0, 4.6,
    25, 18, 'Phiên dịch viên chuyên nghiệp với 3 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Nhật - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Pháp lý & Hợp đồng và Công nghệ thông tin & Phần mềm. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Bình Dương cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Nhật - Tiếng Việt | Chuyên ngành Pháp lý & Hợp đồng', 'Phiên dịch viên Tiếng Việt – Pháp lý & Hợp đồng', 'Thạc sĩ', 'Đại học Ngoại thương (FTU)',
    'Tiếng Anh Thương mại', 'JLPT N1 (160/180)', 2023, 'Tập đoàn đa quốc gia ngành Pháp lý & Hợp đồng, Đối tác FDI tại Bình Dương, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Pháp lý & Hợp đồng; Hội thảo xúc tiến thương mại Công nghệ thông tin & Phần mềm', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv026@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Nhật > Tiếng Việt", "Tiếng Việt > Tiếng Nhật"]', '["Pháp lý & Hợp đồng", "Công nghệ thông tin & Phần mềm"]', 'both', 'Bình Dương', 600000.0, 4200000.0, false
FROM "user" u WHERE u.email = 'pdv026@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Nhật, Tiếng Việt', 'Tiếng Nhật > Tiếng Việt, Tiếng Việt > Tiếng Nhật', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Pháp lý & Hợp đồng, Công nghệ thông tin & Phần mềm', 'Bình Dương', 'both', true
FROM "user" u WHERE u.email = 'pdv026@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Nhật', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Pháp lý & Hợp đồng', 600000.0, 2400000.0, true
FROM "user" u WHERE u.email = 'pdv026@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Nhật ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1200000.0, 2400000.0, 4800000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv026@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Đinh Hữu Đạt', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv026@demo.viettranslate.local';


-- PDV #27: Trương Thảo Nhi (pdv027@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Trương Thảo Nhi', 'pdv027@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000027', '/static/avatars/avatar_khoa.jpg', 'Bắc Ninh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Trương Thảo Nhi', phone = '0901000027', avatar_url = '/static/avatars/avatar_khoa.jpg', city = 'Bắc Ninh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Hàn', 'Y tế & Chăm sóc sức khỏe, Giáo dục & Đào tạo', 'Tiếng Việt', 'Tiếng Hàn',
    'Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng', 4, 680000.0, 4600000.0, 4.5,
    27, 20, 'Phiên dịch viên chuyên nghiệp với 4 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Hàn, am hiểu sâu sắc thuật ngữ chuyên ngành Y tế & Chăm sóc sức khỏe và Giáo dục & Đào tạo. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Bắc Ninh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Việt - Tiếng Hàn | Chuyên ngành Y tế & Chăm sóc sức khỏe', 'Phiên dịch viên Tiếng Hàn – Y tế & Chăm sóc sức khỏe', 'Cử nhân', 'Đại học Hà Nội (HANU)',
    'Biên phiên dịch Chuyên nghiệp', 'TOPIK 5 (220/300)', 2021, 'Tập đoàn đa quốc gia ngành Y tế & Chăm sóc sức khỏe, Đối tác FDI tại Bắc Ninh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Y tế & Chăm sóc sức khỏe; Hội thảo xúc tiến thương mại Giáo dục & Đào tạo', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv027@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Hàn", "Tiếng Hàn > Tiếng Việt"]', '["Y tế & Chăm sóc sức khỏe", "Giáo dục & Đào tạo"]', 'both', 'Bắc Ninh', 680000.0, 4600000.0, false
FROM "user" u WHERE u.email = 'pdv027@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Hàn', 'Tiếng Việt > Tiếng Hàn, Tiếng Hàn > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Y tế & Chăm sóc sức khỏe, Giáo dục & Đào tạo', 'Bắc Ninh', 'both', true
FROM "user" u WHERE u.email = 'pdv027@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Hàn', 'Đàm phán & Thương mại', 'Y tế & Chăm sóc sức khỏe', 680000.0, 2720000.0, true
FROM "user" u WHERE u.email = 'pdv027@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Hàn chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1360000.0, 2720000.0, 5440000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv027@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Trương Thảo Nhi', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv027@demo.viettranslate.local';


-- PDV #28: Nguyễn Tiến Phát (pdv028@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Nguyễn Tiến Phát', 'pdv028@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000028', '/static/avatars/avatar_nam.jpg', 'Quảng Ninh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Nguyễn Tiến Phát', phone = '0901000028', avatar_url = '/static/avatars/avatar_nam.jpg', city = 'Quảng Ninh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Hàn, Tiếng Việt', 'Du lịch & Khách sạn, Xuất nhập khẩu & Logistics', 'Tiếng Hàn', 'Tiếng Việt',
    'Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy', 5, 760000.0, 5000000.0, 4.8,
    29, 21, 'Phiên dịch viên chuyên nghiệp với 5 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Hàn - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Du lịch & Khách sạn và Xuất nhập khẩu & Logistics. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Quảng Ninh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Phiên dịch viên chuyên nghiệp Tiếng Hàn - Tiếng Việt | Chuyên ngành Du lịch & Khách sạn', 'Phiên dịch viên Tiếng Việt – Du lịch & Khách sạn', 'Cử nhân', 'Đại học KHXH&NV - ĐHQG TP.HCM',
    'Ngôn ngữ & Văn hóa Quốc tế', 'TOPIK 6', 2024, 'Tập đoàn đa quốc gia ngành Du lịch & Khách sạn, Đối tác FDI tại Quảng Ninh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Du lịch & Khách sạn; Hội thảo xúc tiến thương mại Xuất nhập khẩu & Logistics', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Top Rated'
FROM "user" u WHERE u.email = 'pdv028@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Hàn > Tiếng Việt", "Tiếng Việt > Tiếng Hàn"]', '["Du lịch & Khách sạn", "Xuất nhập khẩu & Logistics"]', 'both', 'Quảng Ninh', 760000.0, 5000000.0, false
FROM "user" u WHERE u.email = 'pdv028@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Hàn, Tiếng Việt', 'Tiếng Hàn > Tiếng Việt, Tiếng Việt > Tiếng Hàn', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Du lịch & Khách sạn, Xuất nhập khẩu & Logistics', 'Quảng Ninh', 'both', true
FROM "user" u WHERE u.email = 'pdv028@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Hàn', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Du lịch & Khách sạn', 760000.0, 3040000.0, true
FROM "user" u WHERE u.email = 'pdv028@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Hàn ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    1520000.0, 3040000.0, 6080000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv028@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Nguyễn Tiến Phát', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv028@demo.viettranslate.local';


-- PDV #29: Trần Mỹ Hạnh (pdv029@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Trần Mỹ Hạnh', 'pdv029@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000029', '/static/avatars/avatar_huy.jpg', 'Đồng Nai', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Trần Mỹ Hạnh', phone = '0901000029', avatar_url = '/static/avatars/avatar_huy.jpg', city = 'Đồng Nai', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Hàn, Tiếng Anh', 'Sản xuất & Kỹ thuật công nghiệp, Tài chính & Ngân hàng', 'Tiếng Việt', 'Tiếng Hàn',
    'Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm', 6, 1000000.0, 7500000.0, 4.7,
    38, 30, 'Phiên dịch viên chuyên nghiệp với 6 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Hàn, am hiểu sâu sắc thuật ngữ chuyên ngành Sản xuất & Kỹ thuật công nghiệp và Tài chính & Ngân hàng. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Đồng Nai cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Việt - Tiếng Hàn | Chuyên ngành Sản xuất & Kỹ thuật công nghiệp', 'Phiên dịch viên Tiếng Hàn – Sản xuất & Kỹ thuật công nghiệp', 'Thạc sĩ', 'Đại học Bách Khoa Hà Nội',
    'Kỹ thuật & Ngoại ngữ chuyên ngành', 'TOPIK 6 (Cấp cao nhất)', 2022, 'Tập đoàn đa quốc gia ngành Sản xuất & Kỹ thuật công nghiệp, Đối tác FDI tại Đồng Nai, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Sản xuất & Kỹ thuật công nghiệp; Hội thảo xúc tiến thương mại Tài chính & Ngân hàng', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Premium PDV'
FROM "user" u WHERE u.email = 'pdv029@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Hàn", "Tiếng Hàn > Tiếng Việt"]', '["Sản xuất & Kỹ thuật công nghiệp", "Tài chính & Ngân hàng"]', 'both', 'Đồng Nai', 1000000.0, 7500000.0, false
FROM "user" u WHERE u.email = 'pdv029@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Hàn, Tiếng Anh', 'Tiếng Việt > Tiếng Hàn, Tiếng Hàn > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Sản xuất & Kỹ thuật công nghiệp, Tài chính & Ngân hàng', 'Đồng Nai', 'both', true
FROM "user" u WHERE u.email = 'pdv029@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Hàn', 'Đàm phán & Thương mại', 'Sản xuất & Kỹ thuật công nghiệp', 1000000.0, 4000000.0, true
FROM "user" u WHERE u.email = 'pdv029@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Hàn chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2000000.0, 4000000.0, 8000000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv029@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Trần Mỹ Hạnh', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv029@demo.viettranslate.local';


-- PDV #30: Lê Bảo Lâm (pdv030@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Lê Bảo Lâm', 'pdv030@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000030', '/static/avatars/avatar_lananh.jpg', 'Vũng Tàu', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Lê Bảo Lâm', phone = '0901000030', avatar_url = '/static/avatars/avatar_lananh.jpg', city = 'Vũng Tàu', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Hàn, Tiếng Việt', 'Xây dựng & Bất động sản, Năng lượng & Dầu khí', 'Tiếng Hàn', 'Tiếng Việt',
    'Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương', 7, 1120000.0, 8100000.0, 4.8,
    41, 32, 'Phiên dịch viên chuyên nghiệp với 7 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Hàn - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Xây dựng & Bất động sản và Năng lượng & Dầu khí. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Vũng Tàu cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Hàn - Tiếng Việt | Chuyên ngành Xây dựng & Bất động sản', 'Phiên dịch viên Tiếng Việt – Xây dựng & Bất động sản', 'Cử nhân', 'Đại học Sư phạm TP.HCM',
    'Sư phạm & Dịch thuật Ngoại ngữ', 'TOPIK 6 (Điểm xuất sắc)', 2023, 'Tập đoàn đa quốc gia ngành Xây dựng & Bất động sản, Đối tác FDI tại Vũng Tàu, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Xây dựng & Bất động sản; Hội thảo xúc tiến thương mại Năng lượng & Dầu khí', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Top Rated'
FROM "user" u WHERE u.email = 'pdv030@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Hàn > Tiếng Việt", "Tiếng Việt > Tiếng Hàn"]', '["Xây dựng & Bất động sản", "Năng lượng & Dầu khí"]', 'both', 'Vũng Tàu', 1120000.0, 8100000.0, false
FROM "user" u WHERE u.email = 'pdv030@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Hàn, Tiếng Việt', 'Tiếng Hàn > Tiếng Việt, Tiếng Việt > Tiếng Hàn', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Xây dựng & Bất động sản, Năng lượng & Dầu khí', 'Vũng Tàu', 'both', true
FROM "user" u WHERE u.email = 'pdv030@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Hàn', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Xây dựng & Bất động sản', 1120000.0, 4480000.0, true
FROM "user" u WHERE u.email = 'pdv030@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Hàn ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2240000.0, 4480000.0, 8960000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv030@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Lê Bảo Lâm', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv030@demo.viettranslate.local';


-- PDV #31: Phạm Ngọc Trâm (pdv031@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Phạm Ngọc Trâm', 'pdv031@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000031', '/static/avatars/avatar_dung.jpg', 'Hà Nội', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Phạm Ngọc Trâm', phone = '0901000031', avatar_url = '/static/avatars/avatar_dung.jpg', city = 'Hà Nội', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Hàn', 'Công nghệ thông tin & Phần mềm, Hội nghị & Sự kiện quốc tế', 'Tiếng Việt', 'Tiếng Hàn',
    'Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)', 8, 1240000.0, 8700000.0, 4.9,
    44, 35, 'Phiên dịch viên chuyên nghiệp với 8 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Hàn, am hiểu sâu sắc thuật ngữ chuyên ngành Công nghệ thông tin & Phần mềm và Hội nghị & Sự kiện quốc tế. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Hà Nội cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Việt - Tiếng Hàn | Chuyên ngành Công nghệ thông tin & Phần mềm', 'Phiên dịch viên Tiếng Hàn – Công nghệ thông tin & Phần mềm', 'Thạc sĩ', 'Đại học Kinh tế Quốc dân (NEU)',
    'Kinh tế đối ngoại & Ngoại ngữ', 'TOPIK 5 (220/300)', 2021, 'Tập đoàn đa quốc gia ngành Công nghệ thông tin & Phần mềm, Đối tác FDI tại Hà Nội, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Công nghệ thông tin & Phần mềm; Hội thảo xúc tiến thương mại Hội nghị & Sự kiện quốc tế', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Top Rated'
FROM "user" u WHERE u.email = 'pdv031@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Hàn", "Tiếng Hàn > Tiếng Việt"]', '["Công nghệ thông tin & Phần mềm", "Hội nghị & Sự kiện quốc tế"]', 'both', 'Hà Nội', 1240000.0, 8700000.0, false
FROM "user" u WHERE u.email = 'pdv031@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Hàn', 'Tiếng Việt > Tiếng Hàn, Tiếng Hàn > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Công nghệ thông tin & Phần mềm, Hội nghị & Sự kiện quốc tế', 'Hà Nội', 'both', true
FROM "user" u WHERE u.email = 'pdv031@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Hàn', 'Đàm phán & Thương mại', 'Công nghệ thông tin & Phần mềm', 1240000.0, 4960000.0, true
FROM "user" u WHERE u.email = 'pdv031@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Hàn chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2480000.0, 4960000.0, 9920000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv031@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Phạm Ngọc Trâm', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv031@demo.viettranslate.local';


-- PDV #32: Hoàng Gia Khiêm (pdv032@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Hoàng Gia Khiêm', 'pdv032@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000032', '/static/avatars/avatar_ha.jpg', 'TP. Hồ Chí Minh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Hoàng Gia Khiêm', phone = '0901000032', avatar_url = '/static/avatars/avatar_ha.jpg', city = 'TP. Hồ Chí Minh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Hàn, Tiếng Việt', 'Giáo dục & Đào tạo, Đàm phán kinh doanh & Thương mại', 'Tiếng Hàn', 'Tiếng Việt',
    'Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng', 9, 1360000.0, 9300000.0, 4.7,
    47, 37, 'Phiên dịch viên chuyên nghiệp với 9 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Hàn - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Giáo dục & Đào tạo và Đàm phán kinh doanh & Thương mại. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực TP. Hồ Chí Minh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Hàn - Tiếng Việt | Chuyên ngành Giáo dục & Đào tạo', 'Phiên dịch viên Tiếng Việt – Giáo dục & Đào tạo', 'Cử nhân', 'Học viện Ngoại giao (DAV)',
    'Quan hệ Quốc tế & Ngoại giao', 'TOPIK 6', 2024, 'Tập đoàn đa quốc gia ngành Giáo dục & Đào tạo, Đối tác FDI tại TP. Hồ Chí Minh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Giáo dục & Đào tạo; Hội thảo xúc tiến thương mại Đàm phán kinh doanh & Thương mại', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv032@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Hàn > Tiếng Việt", "Tiếng Việt > Tiếng Hàn"]', '["Giáo dục & Đào tạo", "Đàm phán kinh doanh & Thương mại"]', 'both', 'TP. Hồ Chí Minh', 1360000.0, 9300000.0, false
FROM "user" u WHERE u.email = 'pdv032@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Hàn, Tiếng Việt', 'Tiếng Hàn > Tiếng Việt, Tiếng Việt > Tiếng Hàn', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Giáo dục & Đào tạo, Đàm phán kinh doanh & Thương mại', 'TP. Hồ Chí Minh', 'both', true
FROM "user" u WHERE u.email = 'pdv032@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Hàn', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Giáo dục & Đào tạo', 1360000.0, 5440000.0, true
FROM "user" u WHERE u.email = 'pdv032@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Hàn ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2720000.0, 5440000.0, 10880000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv032@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Hoàng Gia Khiêm', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv032@demo.viettranslate.local';


-- PDV #33: Vũ Tuyết Mai (pdv033@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Vũ Tuyết Mai', 'pdv033@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000033', '/static/avatars/avatar_bich.jpg', 'Đà Nẵng', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Vũ Tuyết Mai', phone = '0901000033', avatar_url = '/static/avatars/avatar_bich.jpg', city = 'Đà Nẵng', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Pháp', 'Xuất nhập khẩu & Logistics, Pháp lý & Hợp đồng', 'Tiếng Việt', 'Tiếng Pháp',
    'Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy', 10, 1480000.0, 9900000.0, 4.8,
    50, 40, 'Phiên dịch viên chuyên nghiệp với 10 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Pháp, am hiểu sâu sắc thuật ngữ chuyên ngành Xuất nhập khẩu & Logistics và Pháp lý & Hợp đồng. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Đà Nẵng cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Việt - Tiếng Pháp | Chuyên ngành Xuất nhập khẩu & Logistics', 'Phiên dịch viên Tiếng Pháp – Xuất nhập khẩu & Logistics', 'Thạc sĩ', 'Đại học Ngoại ngữ - ĐHQGHN',
    'Ngôn ngữ học ứng dụng', 'DALF C1', 2022, 'Tập đoàn đa quốc gia ngành Xuất nhập khẩu & Logistics, Đối tác FDI tại Đà Nẵng, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Xuất nhập khẩu & Logistics; Hội thảo xúc tiến thương mại Pháp lý & Hợp đồng', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Top Rated, Premium PDV'
FROM "user" u WHERE u.email = 'pdv033@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Pháp", "Tiếng Pháp > Tiếng Việt"]', '["Xuất nhập khẩu & Logistics", "Pháp lý & Hợp đồng"]', 'both', 'Đà Nẵng', 1480000.0, 9900000.0, false
FROM "user" u WHERE u.email = 'pdv033@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Pháp', 'Tiếng Việt > Tiếng Pháp, Tiếng Pháp > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Xuất nhập khẩu & Logistics, Pháp lý & Hợp đồng', 'Đà Nẵng', 'both', true
FROM "user" u WHERE u.email = 'pdv033@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Pháp', 'Đàm phán & Thương mại', 'Xuất nhập khẩu & Logistics', 1480000.0, 5920000.0, true
FROM "user" u WHERE u.email = 'pdv033@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Pháp chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2960000.0, 5920000.0, 11840000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv033@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Vũ Tuyết Mai', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv033@demo.viettranslate.local';


-- PDV #34: Đặng Minh Quân (pdv034@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Đặng Minh Quân', 'pdv034@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000034', '/static/avatars/avatar_cuong.jpg', 'Hải Phòng', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Đặng Minh Quân', phone = '0901000034', avatar_url = '/static/avatars/avatar_cuong.jpg', city = 'Hải Phòng', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Pháp, Tiếng Việt', 'Tài chính & Ngân hàng, Y tế & Chăm sóc sức khỏe', 'Tiếng Pháp', 'Tiếng Việt',
    'Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm', 6, 1000000.0, 7500000.0, 4.9,
    53, 42, 'Phiên dịch viên chuyên nghiệp với 6 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Pháp - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Tài chính & Ngân hàng và Y tế & Chăm sóc sức khỏe. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Hải Phòng cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Pháp - Tiếng Việt | Chuyên ngành Tài chính & Ngân hàng', 'Phiên dịch viên Tiếng Việt – Tài chính & Ngân hàng', 'Cử nhân', 'Đại học Ngoại thương (FTU)',
    'Tiếng Anh Thương mại', 'DELF B2', 2023, 'Tập đoàn đa quốc gia ngành Tài chính & Ngân hàng, Đối tác FDI tại Hải Phòng, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Tài chính & Ngân hàng; Hội thảo xúc tiến thương mại Y tế & Chăm sóc sức khỏe', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Top Rated'
FROM "user" u WHERE u.email = 'pdv034@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Pháp > Tiếng Việt", "Tiếng Việt > Tiếng Pháp"]', '["Tài chính & Ngân hàng", "Y tế & Chăm sóc sức khỏe"]', 'both', 'Hải Phòng', 1000000.0, 7500000.0, false
FROM "user" u WHERE u.email = 'pdv034@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Pháp, Tiếng Việt', 'Tiếng Pháp > Tiếng Việt, Tiếng Việt > Tiếng Pháp', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Tài chính & Ngân hàng, Y tế & Chăm sóc sức khỏe', 'Hải Phòng', 'both', true
FROM "user" u WHERE u.email = 'pdv034@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Pháp', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Tài chính & Ngân hàng', 1000000.0, 4000000.0, true
FROM "user" u WHERE u.email = 'pdv034@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Pháp ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2000000.0, 4000000.0, 8000000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv034@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Đặng Minh Quân', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv034@demo.viettranslate.local';


-- PDV #35: Bùi Khánh Linh (pdv035@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Bùi Khánh Linh', 'pdv035@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000035', '/static/avatars/avatar_duc.jpg', 'Cần Thơ', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Bùi Khánh Linh', phone = '0901000035', avatar_url = '/static/avatars/avatar_duc.jpg', city = 'Cần Thơ', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Pháp, Tiếng Anh', 'Năng lượng & Dầu khí, Du lịch & Khách sạn', 'Tiếng Việt', 'Tiếng Pháp',
    'Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương', 7, 1120000.0, 8100000.0, 4.7,
    56, 44, 'Phiên dịch viên chuyên nghiệp với 7 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Pháp, am hiểu sâu sắc thuật ngữ chuyên ngành Năng lượng & Dầu khí và Du lịch & Khách sạn. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Cần Thơ cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Việt - Tiếng Pháp | Chuyên ngành Năng lượng & Dầu khí', 'Phiên dịch viên Tiếng Pháp – Năng lượng & Dầu khí', 'Thạc sĩ', 'Đại học Hà Nội (HANU)',
    'Biên phiên dịch Chuyên nghiệp', 'DALF C2', 2021, 'Tập đoàn đa quốc gia ngành Năng lượng & Dầu khí, Đối tác FDI tại Cần Thơ, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Năng lượng & Dầu khí; Hội thảo xúc tiến thương mại Du lịch & Khách sạn', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv035@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Pháp", "Tiếng Pháp > Tiếng Việt"]', '["Năng lượng & Dầu khí", "Du lịch & Khách sạn"]', 'both', 'Cần Thơ', 1120000.0, 8100000.0, false
FROM "user" u WHERE u.email = 'pdv035@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Pháp, Tiếng Anh', 'Tiếng Việt > Tiếng Pháp, Tiếng Pháp > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Năng lượng & Dầu khí, Du lịch & Khách sạn', 'Cần Thơ', 'both', true
FROM "user" u WHERE u.email = 'pdv035@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Pháp', 'Đàm phán & Thương mại', 'Năng lượng & Dầu khí', 1120000.0, 4480000.0, true
FROM "user" u WHERE u.email = 'pdv035@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Pháp chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2240000.0, 4480000.0, 8960000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv035@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Bùi Khánh Linh', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv035@demo.viettranslate.local';


-- PDV #36: Đỗ Trọng Hiếu (pdv036@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Đỗ Trọng Hiếu', 'pdv036@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000036', '/static/avatars/avatar_huong.jpg', 'Bình Dương', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Đỗ Trọng Hiếu', phone = '0901000036', avatar_url = '/static/avatars/avatar_huong.jpg', city = 'Bình Dương', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Pháp, Tiếng Việt', 'Hội nghị & Sự kiện quốc tế, Sản xuất & Kỹ thuật công nghiệp', 'Tiếng Pháp', 'Tiếng Việt',
    'Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)', 8, 1240000.0, 8700000.0, 4.8,
    59, 47, 'Phiên dịch viên chuyên nghiệp với 8 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Pháp - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Hội nghị & Sự kiện quốc tế và Sản xuất & Kỹ thuật công nghiệp. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Bình Dương cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Pháp - Tiếng Việt | Chuyên ngành Hội nghị & Sự kiện quốc tế', 'Phiên dịch viên Tiếng Việt – Hội nghị & Sự kiện quốc tế', 'Cử nhân', 'Đại học KHXH&NV - ĐHQG TP.HCM',
    'Ngôn ngữ & Văn hóa Quốc tế', 'DALF C1', 2024, 'Tập đoàn đa quốc gia ngành Hội nghị & Sự kiện quốc tế, Đối tác FDI tại Bình Dương, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Hội nghị & Sự kiện quốc tế; Hội thảo xúc tiến thương mại Sản xuất & Kỹ thuật công nghiệp', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Top Rated'
FROM "user" u WHERE u.email = 'pdv036@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Pháp > Tiếng Việt", "Tiếng Việt > Tiếng Pháp"]', '["Hội nghị & Sự kiện quốc tế", "Sản xuất & Kỹ thuật công nghiệp"]', 'both', 'Bình Dương', 1240000.0, 8700000.0, false
FROM "user" u WHERE u.email = 'pdv036@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Pháp, Tiếng Việt', 'Tiếng Pháp > Tiếng Việt, Tiếng Việt > Tiếng Pháp', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Hội nghị & Sự kiện quốc tế, Sản xuất & Kỹ thuật công nghiệp', 'Bình Dương', 'both', true
FROM "user" u WHERE u.email = 'pdv036@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Pháp', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Hội nghị & Sự kiện quốc tế', 1240000.0, 4960000.0, true
FROM "user" u WHERE u.email = 'pdv036@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Pháp ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2480000.0, 4960000.0, 9920000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv036@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Đỗ Trọng Hiếu', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv036@demo.viettranslate.local';


-- PDV #37: Hồ Thúy Kiều (pdv037@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Hồ Thúy Kiều', 'pdv037@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000037', '/static/avatars/avatar_khoa.jpg', 'Bắc Ninh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Hồ Thúy Kiều', phone = '0901000037', avatar_url = '/static/avatars/avatar_khoa.jpg', city = 'Bắc Ninh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Đức', 'Đàm phán kinh doanh & Thương mại, Xây dựng & Bất động sản', 'Tiếng Việt', 'Tiếng Đức',
    'Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng', 9, 1360000.0, 9300000.0, 4.9,
    62, 49, 'Phiên dịch viên chuyên nghiệp với 9 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Đức, am hiểu sâu sắc thuật ngữ chuyên ngành Đàm phán kinh doanh & Thương mại và Xây dựng & Bất động sản. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Bắc Ninh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Việt - Tiếng Đức | Chuyên ngành Đàm phán kinh doanh & Thương mại', 'Phiên dịch viên Tiếng Đức – Đàm phán kinh doanh & Thương mại', 'Thạc sĩ', 'Đại học Bách Khoa Hà Nội',
    'Kỹ thuật & Ngoại ngữ chuyên ngành', 'Goethe-Zertifikat C1', 2022, 'Tập đoàn đa quốc gia ngành Đàm phán kinh doanh & Thương mại, Đối tác FDI tại Bắc Ninh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Đàm phán kinh doanh & Thương mại; Hội thảo xúc tiến thương mại Xây dựng & Bất động sản', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng, Top Rated, Premium PDV'
FROM "user" u WHERE u.email = 'pdv037@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Đức", "Tiếng Đức > Tiếng Việt"]', '["Đàm phán kinh doanh & Thương mại", "Xây dựng & Bất động sản"]', 'both', 'Bắc Ninh', 1360000.0, 9300000.0, false
FROM "user" u WHERE u.email = 'pdv037@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Đức', 'Tiếng Việt > Tiếng Đức, Tiếng Đức > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Đàm phán kinh doanh & Thương mại, Xây dựng & Bất động sản', 'Bắc Ninh', 'both', true
FROM "user" u WHERE u.email = 'pdv037@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Đức', 'Đàm phán & Thương mại', 'Đàm phán kinh doanh & Thương mại', 1360000.0, 5440000.0, true
FROM "user" u WHERE u.email = 'pdv037@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Đức chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2720000.0, 5440000.0, 10880000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv037@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Hồ Thúy Kiều', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv037@demo.viettranslate.local';


-- PDV #38: Ngô Đình Trí (pdv038@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Ngô Đình Trí', 'pdv038@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000038', '/static/avatars/avatar_nam.jpg', 'Quảng Ninh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Ngô Đình Trí', phone = '0901000038', avatar_url = '/static/avatars/avatar_nam.jpg', city = 'Quảng Ninh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Đức, Tiếng Việt', 'Pháp lý & Hợp đồng, Công nghệ thông tin & Phần mềm', 'Tiếng Đức', 'Tiếng Việt',
    'Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy', 10, 1480000.0, 9900000.0, 4.7,
    65, 52, 'Phiên dịch viên chuyên nghiệp với 10 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Đức - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Pháp lý & Hợp đồng và Công nghệ thông tin & Phần mềm. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Quảng Ninh cũng như các dự án trực tuyến qua Zoom/Teams.', true, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Đức - Tiếng Việt | Chuyên ngành Pháp lý & Hợp đồng', 'Phiên dịch viên Tiếng Việt – Pháp lý & Hợp đồng', 'Cử nhân', 'Đại học Sư phạm TP.HCM',
    'Sư phạm & Dịch thuật Ngoại ngữ', 'TestDaF TDN 5', 2023, 'Tập đoàn đa quốc gia ngành Pháp lý & Hợp đồng, Đối tác FDI tại Quảng Ninh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Pháp lý & Hợp đồng; Hội thảo xúc tiến thương mại Công nghệ thông tin & Phần mềm', 'Đã xác minh danh tính, Đã kiểm tra kỹ năng'
FROM "user" u WHERE u.email = 'pdv038@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Đức > Tiếng Việt", "Tiếng Việt > Tiếng Đức"]', '["Pháp lý & Hợp đồng", "Công nghệ thông tin & Phần mềm"]', 'both', 'Quảng Ninh', 1480000.0, 9900000.0, false
FROM "user" u WHERE u.email = 'pdv038@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Đức, Tiếng Việt', 'Tiếng Đức > Tiếng Việt, Tiếng Việt > Tiếng Đức', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Pháp lý & Hợp đồng, Công nghệ thông tin & Phần mềm', 'Quảng Ninh', 'both', true
FROM "user" u WHERE u.email = 'pdv038@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Đức', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Pháp lý & Hợp đồng', 1480000.0, 5920000.0, true
FROM "user" u WHERE u.email = 'pdv038@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Đức ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2960000.0, 5920000.0, 11840000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv038@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Ngô Đình Trí', '00109' || LPAD(p.id::text, 7, '0'), 'approved',
    CASE WHEN true THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv038@demo.viettranslate.local';


-- PDV #39: Dương Yến Trang (pdv039@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Dương Yến Trang', 'pdv039@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000039', '/static/avatars/avatar_huy.jpg', 'Đồng Nai', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Dương Yến Trang', phone = '0901000039', avatar_url = '/static/avatars/avatar_huy.jpg', city = 'Đồng Nai', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Đức, Tiếng Anh', 'Y tế & Chăm sóc sức khỏe, Giáo dục & Đào tạo', 'Tiếng Việt', 'Tiếng Đức',
    'Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm', 6, 1000000.0, 7500000.0, 4.8,
    68, 54, 'Phiên dịch viên chuyên nghiệp với 6 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Đức, am hiểu sâu sắc thuật ngữ chuyên ngành Y tế & Chăm sóc sức khỏe và Giáo dục & Đào tạo. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Đồng Nai cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Việt - Tiếng Đức | Chuyên ngành Y tế & Chăm sóc sức khỏe', 'Phiên dịch viên Tiếng Đức – Y tế & Chăm sóc sức khỏe', 'Thạc sĩ', 'Đại học Kinh tế Quốc dân (NEU)',
    'Kinh tế đối ngoại & Ngoại ngữ', 'Goethe-Zertifikat B2', 2021, 'Tập đoàn đa quốc gia ngành Y tế & Chăm sóc sức khỏe, Đối tác FDI tại Đồng Nai, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Y tế & Chăm sóc sức khỏe; Hội thảo xúc tiến thương mại Giáo dục & Đào tạo', 'Đang xác minh hồ sơ KYC'
FROM "user" u WHERE u.email = 'pdv039@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Đức", "Tiếng Đức > Tiếng Việt"]', '["Y tế & Chăm sóc sức khỏe", "Giáo dục & Đào tạo"]', 'both', 'Đồng Nai', 1000000.0, 7500000.0, false
FROM "user" u WHERE u.email = 'pdv039@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Đức, Tiếng Anh', 'Tiếng Việt > Tiếng Đức, Tiếng Đức > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Y tế & Chăm sóc sức khỏe, Giáo dục & Đào tạo', 'Đồng Nai', 'both', true
FROM "user" u WHERE u.email = 'pdv039@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Đức', 'Đàm phán & Thương mại', 'Y tế & Chăm sóc sức khỏe', 1000000.0, 4000000.0, true
FROM "user" u WHERE u.email = 'pdv039@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Đức chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2000000.0, 4000000.0, 8000000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv039@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Dương Yến Trang', '00109' || LPAD(p.id::text, 7, '0'), 'pending',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv039@demo.viettranslate.local';


-- PDV #40: Lý Văn Hậu (pdv040@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Lý Văn Hậu', 'pdv040@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000040', '/static/avatars/avatar_lananh.jpg', 'Vũng Tàu', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Lý Văn Hậu', phone = '0901000040', avatar_url = '/static/avatars/avatar_lananh.jpg', city = 'Vũng Tàu', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Đức, Tiếng Việt', 'Du lịch & Khách sạn, Xuất nhập khẩu & Logistics', 'Tiếng Đức', 'Tiếng Việt',
    'Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương', 7, 1120000.0, 8100000.0, 4.9,
    71, 56, 'Phiên dịch viên chuyên nghiệp với 7 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Đức - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Du lịch & Khách sạn và Xuất nhập khẩu & Logistics. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Vũng Tàu cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Đức - Tiếng Việt | Chuyên ngành Du lịch & Khách sạn', 'Phiên dịch viên Tiếng Việt – Du lịch & Khách sạn', 'Cử nhân', 'Học viện Ngoại giao (DAV)',
    'Quan hệ Quốc tế & Ngoại giao', 'Goethe C1', 2024, 'Tập đoàn đa quốc gia ngành Du lịch & Khách sạn, Đối tác FDI tại Vũng Tàu, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Du lịch & Khách sạn; Hội thảo xúc tiến thương mại Xuất nhập khẩu & Logistics', 'Đang xác minh hồ sơ KYC'
FROM "user" u WHERE u.email = 'pdv040@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Đức > Tiếng Việt", "Tiếng Việt > Tiếng Đức"]', '["Du lịch & Khách sạn", "Xuất nhập khẩu & Logistics"]', 'both', 'Vũng Tàu', 1120000.0, 8100000.0, false
FROM "user" u WHERE u.email = 'pdv040@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Đức, Tiếng Việt', 'Tiếng Đức > Tiếng Việt, Tiếng Việt > Tiếng Đức', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Du lịch & Khách sạn, Xuất nhập khẩu & Logistics', 'Vũng Tàu', 'both', true
FROM "user" u WHERE u.email = 'pdv040@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Đức', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Du lịch & Khách sạn', 1120000.0, 4480000.0, true
FROM "user" u WHERE u.email = 'pdv040@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Đức ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2240000.0, 4480000.0, 8960000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv040@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Lý Văn Hậu', '00109' || LPAD(p.id::text, 7, '0'), 'pending',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv040@demo.viettranslate.local';


-- PDV #41: Phan Thu Thảo (pdv041@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Phan Thu Thảo', 'pdv041@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000041', '/static/avatars/avatar_dung.jpg', 'Hà Nội', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Phan Thu Thảo', phone = '0901000041', avatar_url = '/static/avatars/avatar_dung.jpg', city = 'Hà Nội', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Nga', 'Sản xuất & Kỹ thuật công nghiệp, Tài chính & Ngân hàng', 'Tiếng Việt', 'Tiếng Nga',
    'Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)', 8, 1240000.0, 8700000.0, 4.7,
    39, 31, 'Phiên dịch viên chuyên nghiệp với 8 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Nga, am hiểu sâu sắc thuật ngữ chuyên ngành Sản xuất & Kỹ thuật công nghiệp và Tài chính & Ngân hàng. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Hà Nội cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Việt - Tiếng Nga | Chuyên ngành Sản xuất & Kỹ thuật công nghiệp', 'Phiên dịch viên Tiếng Nga – Sản xuất & Kỹ thuật công nghiệp', 'Thạc sĩ', 'Đại học Ngoại ngữ - ĐHQGHN',
    'Ngôn ngữ học ứng dụng', 'ТРКИ C1', 2022, 'Tập đoàn đa quốc gia ngành Sản xuất & Kỹ thuật công nghiệp, Đối tác FDI tại Hà Nội, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Sản xuất & Kỹ thuật công nghiệp; Hội thảo xúc tiến thương mại Tài chính & Ngân hàng', 'Đang xác minh hồ sơ KYC, Premium PDV'
FROM "user" u WHERE u.email = 'pdv041@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Nga", "Tiếng Nga > Tiếng Việt"]', '["Sản xuất & Kỹ thuật công nghiệp", "Tài chính & Ngân hàng"]', 'both', 'Hà Nội', 1240000.0, 8700000.0, false
FROM "user" u WHERE u.email = 'pdv041@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Nga', 'Tiếng Việt > Tiếng Nga, Tiếng Nga > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Sản xuất & Kỹ thuật công nghiệp, Tài chính & Ngân hàng', 'Hà Nội', 'both', true
FROM "user" u WHERE u.email = 'pdv041@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Nga', 'Đàm phán & Thương mại', 'Sản xuất & Kỹ thuật công nghiệp', 1240000.0, 4960000.0, true
FROM "user" u WHERE u.email = 'pdv041@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Nga chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2480000.0, 4960000.0, 9920000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv041@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Phan Thu Thảo', '00109' || LPAD(p.id::text, 7, '0'), 'pending',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv041@demo.viettranslate.local';


-- PDV #42: Võ Tuấn Kiệt (pdv042@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Võ Tuấn Kiệt', 'pdv042@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000042', '/static/avatars/avatar_ha.jpg', 'TP. Hồ Chí Minh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Võ Tuấn Kiệt', phone = '0901000042', avatar_url = '/static/avatars/avatar_ha.jpg', city = 'TP. Hồ Chí Minh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Nga, Tiếng Việt', 'Xây dựng & Bất động sản, Năng lượng & Dầu khí', 'Tiếng Nga', 'Tiếng Việt',
    'Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng', 9, 1360000.0, 9300000.0, 4.8,
    42, 33, 'Phiên dịch viên chuyên nghiệp với 9 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Nga - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Xây dựng & Bất động sản và Năng lượng & Dầu khí. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực TP. Hồ Chí Minh cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Nga - Tiếng Việt | Chuyên ngành Xây dựng & Bất động sản', 'Phiên dịch viên Tiếng Việt – Xây dựng & Bất động sản', 'Cử nhân', 'Đại học Ngoại thương (FTU)',
    'Tiếng Anh Thương mại', 'ТРКИ B2', 2023, 'Tập đoàn đa quốc gia ngành Xây dựng & Bất động sản, Đối tác FDI tại TP. Hồ Chí Minh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Xây dựng & Bất động sản; Hội thảo xúc tiến thương mại Năng lượng & Dầu khí', 'Đang xác minh hồ sơ KYC'
FROM "user" u WHERE u.email = 'pdv042@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Nga > Tiếng Việt", "Tiếng Việt > Tiếng Nga"]', '["Xây dựng & Bất động sản", "Năng lượng & Dầu khí"]', 'both', 'TP. Hồ Chí Minh', 1360000.0, 9300000.0, false
FROM "user" u WHERE u.email = 'pdv042@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Nga, Tiếng Việt', 'Tiếng Nga > Tiếng Việt, Tiếng Việt > Tiếng Nga', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Xây dựng & Bất động sản, Năng lượng & Dầu khí', 'TP. Hồ Chí Minh', 'both', true
FROM "user" u WHERE u.email = 'pdv042@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Nga', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Xây dựng & Bất động sản', 1360000.0, 5440000.0, true
FROM "user" u WHERE u.email = 'pdv042@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Nga ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2720000.0, 5440000.0, 10880000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv042@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Võ Tuấn Kiệt', '00109' || LPAD(p.id::text, 7, '0'), 'pending',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv042@demo.viettranslate.local';


-- PDV #43: Trịnh Thùy Linh (pdv043@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Trịnh Thùy Linh', 'pdv043@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000043', '/static/avatars/avatar_bich.jpg', 'Đà Nẵng', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Trịnh Thùy Linh', phone = '0901000043', avatar_url = '/static/avatars/avatar_bich.jpg', city = 'Đà Nẵng', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Nga, Tiếng Anh', 'Công nghệ thông tin & Phần mềm, Hội nghị & Sự kiện quốc tế', 'Tiếng Việt', 'Tiếng Nga',
    'Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy', 10, 1480000.0, 9900000.0, 4.9,
    45, 36, 'Phiên dịch viên chuyên nghiệp với 10 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Nga, am hiểu sâu sắc thuật ngữ chuyên ngành Công nghệ thông tin & Phần mềm và Hội nghị & Sự kiện quốc tế. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Đà Nẵng cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Việt - Tiếng Nga | Chuyên ngành Công nghệ thông tin & Phần mềm', 'Phiên dịch viên Tiếng Nga – Công nghệ thông tin & Phần mềm', 'Thạc sĩ', 'Đại học Hà Nội (HANU)',
    'Biên phiên dịch Chuyên nghiệp', 'ТРКИ C2', 2020, 'Tập đoàn đa quốc gia ngành Công nghệ thông tin & Phần mềm, Đối tác FDI tại Đà Nẵng, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Công nghệ thông tin & Phần mềm; Hội thảo xúc tiến thương mại Hội nghị & Sự kiện quốc tế', 'Đang xác minh hồ sơ KYC'
FROM "user" u WHERE u.email = 'pdv043@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Nga", "Tiếng Nga > Tiếng Việt"]', '["Công nghệ thông tin & Phần mềm", "Hội nghị & Sự kiện quốc tế"]', 'both', 'Đà Nẵng', 1480000.0, 9900000.0, false
FROM "user" u WHERE u.email = 'pdv043@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Nga, Tiếng Anh', 'Tiếng Việt > Tiếng Nga, Tiếng Nga > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Công nghệ thông tin & Phần mềm, Hội nghị & Sự kiện quốc tế', 'Đà Nẵng', 'both', true
FROM "user" u WHERE u.email = 'pdv043@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Nga', 'Đàm phán & Thương mại', 'Công nghệ thông tin & Phần mềm', 1480000.0, 5920000.0, true
FROM "user" u WHERE u.email = 'pdv043@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Nga chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2960000.0, 5920000.0, 11840000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv043@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Trịnh Thùy Linh', '00109' || LPAD(p.id::text, 7, '0'), 'pending',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv043@demo.viettranslate.local';


-- PDV #44: Mai Văn Thịnh (pdv044@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Mai Văn Thịnh', 'pdv044@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000044', '/static/avatars/avatar_cuong.jpg', 'Hải Phòng', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Mai Văn Thịnh', phone = '0901000044', avatar_url = '/static/avatars/avatar_cuong.jpg', city = 'Hải Phòng', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Tây Ban Nha', 'Giáo dục & Đào tạo, Đàm phán kinh doanh & Thương mại', 'Tiếng Việt', 'Tiếng Tây Ban Nha',
    'Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm', 6, 1000000.0, 7500000.0, 4.7,
    48, 38, 'Phiên dịch viên chuyên nghiệp với 6 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Tây Ban Nha, am hiểu sâu sắc thuật ngữ chuyên ngành Giáo dục & Đào tạo và Đàm phán kinh doanh & Thương mại. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Hải Phòng cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cao cấp Tiếng Việt - Tiếng Tây Ban Nha | Chuyên ngành Giáo dục & Đào tạo', 'Phiên dịch viên Tiếng Tây Ban Nha – Giáo dục & Đào tạo', 'Cử nhân', 'Đại học KHXH&NV - ĐHQG TP.HCM',
    'Ngôn ngữ & Văn hóa Quốc tế', 'DELE C1', 2024, 'Tập đoàn đa quốc gia ngành Giáo dục & Đào tạo, Đối tác FDI tại Hải Phòng, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Giáo dục & Đào tạo; Hội thảo xúc tiến thương mại Đàm phán kinh doanh & Thương mại', 'Đang xác minh hồ sơ KYC'
FROM "user" u WHERE u.email = 'pdv044@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Tây Ban Nha", "Tiếng Tây Ban Nha > Tiếng Việt"]', '["Giáo dục & Đào tạo", "Đàm phán kinh doanh & Thương mại"]', 'both', 'Hải Phòng', 1000000.0, 7500000.0, false
FROM "user" u WHERE u.email = 'pdv044@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Tây Ban Nha', 'Tiếng Việt > Tiếng Tây Ban Nha, Tiếng Tây Ban Nha > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Giáo dục & Đào tạo, Đàm phán kinh doanh & Thương mại', 'Hải Phòng', 'both', true
FROM "user" u WHERE u.email = 'pdv044@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Tây Ban Nha', 'Đàm phán & Thương mại', 'Giáo dục & Đào tạo', 1000000.0, 4000000.0, true
FROM "user" u WHERE u.email = 'pdv044@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Tây Ban Nha chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    2000000.0, 4000000.0, 8000000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv044@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Mai Văn Thịnh', '00109' || LPAD(p.id::text, 7, '0'), 'pending',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv044@demo.viettranslate.local';


-- PDV #45: Đoàn Phương Mai (pdv045@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Đoàn Phương Mai', 'pdv045@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000045', '/static/avatars/avatar_duc.jpg', 'Cần Thơ', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Đoàn Phương Mai', phone = '0901000045', avatar_url = '/static/avatars/avatar_duc.jpg', city = 'Cần Thơ', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Tây Ban Nha, Tiếng Việt', 'Xuất nhập khẩu & Logistics, Pháp lý & Hợp đồng', 'Tiếng Tây Ban Nha', 'Tiếng Việt',
    'Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương', 11, 1600000.0, 12000000.0, 5.0,
    85, 72, 'Phiên dịch viên chuyên nghiệp với 11 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Tây Ban Nha - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Xuất nhập khẩu & Logistics và Pháp lý & Hợp đồng. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Cần Thơ cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cabin kỳ cựu Tiếng Tây Ban Nha - Tiếng Việt | Chuyên ngành Xuất nhập khẩu & Logistics', 'Phiên dịch viên Tiếng Việt – Xuất nhập khẩu & Logistics', 'Tiến sĩ', 'Đại học Bách Khoa Hà Nội',
    'Kỹ thuật & Ngoại ngữ chuyên ngành', 'DELE C1', 2022, 'Tập đoàn đa quốc gia ngành Xuất nhập khẩu & Logistics, Đối tác FDI tại Cần Thơ, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Xuất nhập khẩu & Logistics; Hội thảo xúc tiến thương mại Pháp lý & Hợp đồng', 'Đang xác minh hồ sơ KYC, Premium PDV'
FROM "user" u WHERE u.email = 'pdv045@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Tây Ban Nha > Tiếng Việt", "Tiếng Việt > Tiếng Tây Ban Nha"]', '["Xuất nhập khẩu & Logistics", "Pháp lý & Hợp đồng"]', 'both', 'Cần Thơ', 1600000.0, 12000000.0, false
FROM "user" u WHERE u.email = 'pdv045@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Tây Ban Nha, Tiếng Việt', 'Tiếng Tây Ban Nha > Tiếng Việt, Tiếng Việt > Tiếng Tây Ban Nha', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Xuất nhập khẩu & Logistics, Pháp lý & Hợp đồng', 'Cần Thơ', 'both', true
FROM "user" u WHERE u.email = 'pdv045@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Tây Ban Nha', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Xuất nhập khẩu & Logistics', 1600000.0, 6400000.0, true
FROM "user" u WHERE u.email = 'pdv045@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Tây Ban Nha ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    3200000.0, 6400000.0, 12800000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv045@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Đoàn Phương Mai', '00109' || LPAD(p.id::text, 7, '0'), 'pending',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv045@demo.viettranslate.local';


-- PDV #46: Lâm Bá Thông (pdv046@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Lâm Bá Thông', 'pdv046@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000046', '/static/avatars/avatar_huong.jpg', 'Bình Dương', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Lâm Bá Thông', phone = '0901000046', avatar_url = '/static/avatars/avatar_huong.jpg', city = 'Bình Dương', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Tây Ban Nha, Tiếng Anh', 'Tài chính & Ngân hàng, Y tế & Chăm sóc sức khỏe', 'Tiếng Việt', 'Tiếng Tây Ban Nha',
    'Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)', 13, 1800000.0, 13500000.0, 4.9,
    92, 78, 'Phiên dịch viên chuyên nghiệp với 13 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Tây Ban Nha, am hiểu sâu sắc thuật ngữ chuyên ngành Tài chính & Ngân hàng và Y tế & Chăm sóc sức khỏe. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Bình Dương cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cabin kỳ cựu Tiếng Việt - Tiếng Tây Ban Nha | Chuyên ngành Tài chính & Ngân hàng', 'Phiên dịch viên Tiếng Tây Ban Nha – Tài chính & Ngân hàng', 'Thạc sĩ', 'Đại học Sư phạm TP.HCM',
    'Sư phạm & Dịch thuật Ngoại ngữ', 'DELE B2', 2023, 'Tập đoàn đa quốc gia ngành Tài chính & Ngân hàng, Đối tác FDI tại Bình Dương, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Tài chính & Ngân hàng; Hội thảo xúc tiến thương mại Y tế & Chăm sóc sức khỏe', 'Đang xác minh hồ sơ KYC'
FROM "user" u WHERE u.email = 'pdv046@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Tây Ban Nha", "Tiếng Tây Ban Nha > Tiếng Việt"]', '["Tài chính & Ngân hàng", "Y tế & Chăm sóc sức khỏe"]', 'both', 'Bình Dương', 1800000.0, 13500000.0, false
FROM "user" u WHERE u.email = 'pdv046@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Tây Ban Nha, Tiếng Anh', 'Tiếng Việt > Tiếng Tây Ban Nha, Tiếng Tây Ban Nha > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Tài chính & Ngân hàng, Y tế & Chăm sóc sức khỏe', 'Bình Dương', 'both', true
FROM "user" u WHERE u.email = 'pdv046@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Tây Ban Nha', 'Đàm phán & Thương mại', 'Tài chính & Ngân hàng', 1800000.0, 7200000.0, true
FROM "user" u WHERE u.email = 'pdv046@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Tây Ban Nha chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    3600000.0, 7200000.0, 14400000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv046@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Lâm Bá Thông', '00109' || LPAD(p.id::text, 7, '0'), 'pending',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv046@demo.viettranslate.local';


-- PDV #47: Lương Diệu Linh (pdv047@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Lương Diệu Linh', 'pdv047@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000047', '/static/avatars/avatar_khoa.jpg', 'Bắc Ninh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Lương Diệu Linh', phone = '0901000047', avatar_url = '/static/avatars/avatar_khoa.jpg', city = 'Bắc Ninh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Thái', 'Năng lượng & Dầu khí, Du lịch & Khách sạn', 'Tiếng Việt', 'Tiếng Thái',
    'Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng', 15, 2000000.0, 15000000.0, 5.0,
    99, 84, 'Phiên dịch viên chuyên nghiệp với 15 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Thái, am hiểu sâu sắc thuật ngữ chuyên ngành Năng lượng & Dầu khí và Du lịch & Khách sạn. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Bắc Ninh cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cabin kỳ cựu Tiếng Việt - Tiếng Thái | Chuyên ngành Năng lượng & Dầu khí', 'Phiên dịch viên Tiếng Thái – Năng lượng & Dầu khí', 'Tiến sĩ', 'Đại học Kinh tế Quốc dân (NEU)',
    'Kinh tế đối ngoại & Ngoại ngữ', 'Kiểm tra trực tiếp - Đạt chuẩn thương mại', 2023, 'Tập đoàn đa quốc gia ngành Năng lượng & Dầu khí, Đối tác FDI tại Bắc Ninh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Năng lượng & Dầu khí; Hội thảo xúc tiến thương mại Du lịch & Khách sạn', ''
FROM "user" u WHERE u.email = 'pdv047@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Thái", "Tiếng Thái > Tiếng Việt"]', '["Năng lượng & Dầu khí", "Du lịch & Khách sạn"]', 'both', 'Bắc Ninh', 2000000.0, 15000000.0, false
FROM "user" u WHERE u.email = 'pdv047@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Thái', 'Tiếng Việt > Tiếng Thái, Tiếng Thái > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Năng lượng & Dầu khí, Du lịch & Khách sạn', 'Bắc Ninh', 'both', true
FROM "user" u WHERE u.email = 'pdv047@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Thái', 'Đàm phán & Thương mại', 'Năng lượng & Dầu khí', 2000000.0, 8000000.0, true
FROM "user" u WHERE u.email = 'pdv047@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Thái chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    4000000.0, 8000000.0, 16000000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv047@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Lương Diệu Linh', '00109' || LPAD(p.id::text, 7, '0'), 'draft',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv047@demo.viettranslate.local';


-- PDV #48: Chu Quốc Bảo (pdv048@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Chu Quốc Bảo', 'pdv048@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000048', '/static/avatars/avatar_nam.jpg', 'Quảng Ninh', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Chu Quốc Bảo', phone = '0901000048', avatar_url = '/static/avatars/avatar_nam.jpg', city = 'Quảng Ninh', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Thái, Tiếng Việt', 'Hội nghị & Sự kiện quốc tế, Sản xuất & Kỹ thuật công nghiệp', 'Tiếng Thái', 'Tiếng Việt',
    'Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy', 17, 2200000.0, 16500000.0, 4.9,
    106, 90, 'Phiên dịch viên chuyên nghiệp với 17 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Thái - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Hội nghị & Sự kiện quốc tế và Sản xuất & Kỹ thuật công nghiệp. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Quảng Ninh cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cabin kỳ cựu Tiếng Thái - Tiếng Việt | Chuyên ngành Hội nghị & Sự kiện quốc tế', 'Phiên dịch viên Tiếng Việt – Hội nghị & Sự kiện quốc tế', 'Thạc sĩ', 'Học viện Ngoại giao (DAV)',
    'Quan hệ Quốc tế & Ngoại giao', 'Tiếng Thái Thương mại Nâng cao', 2021, 'Tập đoàn đa quốc gia ngành Hội nghị & Sự kiện quốc tế, Đối tác FDI tại Quảng Ninh, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Hội nghị & Sự kiện quốc tế; Hội thảo xúc tiến thương mại Sản xuất & Kỹ thuật công nghiệp', ''
FROM "user" u WHERE u.email = 'pdv048@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Thái > Tiếng Việt", "Tiếng Việt > Tiếng Thái"]', '["Hội nghị & Sự kiện quốc tế", "Sản xuất & Kỹ thuật công nghiệp"]', 'both', 'Quảng Ninh', 2200000.0, 16500000.0, false
FROM "user" u WHERE u.email = 'pdv048@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Thái, Tiếng Việt', 'Tiếng Thái > Tiếng Việt, Tiếng Việt > Tiếng Thái', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Hội nghị & Sự kiện quốc tế, Sản xuất & Kỹ thuật công nghiệp', 'Quảng Ninh', 'both', true
FROM "user" u WHERE u.email = 'pdv048@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Thái', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Hội nghị & Sự kiện quốc tế', 2200000.0, 8800000.0, true
FROM "user" u WHERE u.email = 'pdv048@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Thái ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    4400000.0, 8800000.0, 17600000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv048@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Chu Quốc Bảo', '00109' || LPAD(p.id::text, 7, '0'), 'draft',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv048@demo.viettranslate.local';


-- PDV #49: Cao Minh Nhật (pdv049@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Cao Minh Nhật', 'pdv049@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000049', '/static/avatars/avatar_huy.jpg', 'Đồng Nai', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Cao Minh Nhật', phone = '0901000049', avatar_url = '/static/avatars/avatar_huy.jpg', city = 'Đồng Nai', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Việt, Tiếng Bồ Đào Nha', 'Đàm phán kinh doanh & Thương mại, Xây dựng & Bất động sản', 'Tiếng Việt', 'Tiếng Bồ Đào Nha',
    'Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm', 19, 2400000.0, 18000000.0, 5.0,
    113, 96, 'Phiên dịch viên chuyên nghiệp với 19 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Việt - Tiếng Bồ Đào Nha, am hiểu sâu sắc thuật ngữ chuyên ngành Đàm phán kinh doanh & Thương mại và Xây dựng & Bất động sản. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Đồng Nai cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cabin kỳ cựu Tiếng Việt - Tiếng Bồ Đào Nha | Chuyên ngành Đàm phán kinh doanh & Thương mại', 'Phiên dịch viên Tiếng Bồ Đào Nha – Đàm phán kinh doanh & Thương mại', 'Tiến sĩ', 'Đại học Ngoại ngữ - ĐHQGHN',
    'Ngôn ngữ học ứng dụng', 'CELPE-Bras Cấp Avançado', 2022, 'Tập đoàn đa quốc gia ngành Đàm phán kinh doanh & Thương mại, Đối tác FDI tại Đồng Nai, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Đàm phán kinh doanh & Thương mại; Hội thảo xúc tiến thương mại Xây dựng & Bất động sản', 'Premium PDV'
FROM "user" u WHERE u.email = 'pdv049@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Việt > Tiếng Bồ Đào Nha", "Tiếng Bồ Đào Nha > Tiếng Việt"]', '["Đàm phán kinh doanh & Thương mại", "Xây dựng & Bất động sản"]', 'both', 'Đồng Nai', 2400000.0, 18000000.0, false
FROM "user" u WHERE u.email = 'pdv049@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Việt, Tiếng Bồ Đào Nha', 'Tiếng Việt > Tiếng Bồ Đào Nha, Tiếng Bồ Đào Nha > Tiếng Việt', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Đàm phán kinh doanh & Thương mại, Xây dựng & Bất động sản', 'Đồng Nai', 'both', true
FROM "user" u WHERE u.email = 'pdv049@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Việt', 'Tiếng Bồ Đào Nha', 'Đàm phán & Thương mại', 'Đàm phán kinh doanh & Thương mại', 2400000.0, 9600000.0, true
FROM "user" u WHERE u.email = 'pdv049@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Việt ↔ Tiếng Bồ Đào Nha chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    4800000.0, 9600000.0, 19200000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv049@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Cao Minh Nhật', '00109' || LPAD(p.id::text, 7, '0'), 'draft',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv049@demo.viettranslate.local';


-- PDV #50: Tạ Thanh Huyền (pdv050@demo.viettranslate.local)
INSERT INTO "user" (name, email, password_hash, role, is_active, is_demo, phone, avatar_url, city, created_at)
VALUES ('Tạ Thanh Huyền', 'pdv050@demo.viettranslate.local', 'pbkdf2:sha256:600000$EbOcZyz3rlCdZ89P$5c935b96814e56cb7213a376f5698712cf184a8fc1f1a50020b3c55f17398006', 'translator', true, true, '0901000050', '/static/avatars/avatar_lananh.jpg', 'Vũng Tàu', NOW())
ON CONFLICT (email) DO UPDATE SET
    name = 'Tạ Thanh Huyền', phone = '0901000050', avatar_url = '/static/avatars/avatar_lananh.jpg', city = 'Vũng Tàu', is_active = true, is_demo = true;

INSERT INTO translator_profile (
    user_id, languages, specializations, source_language, target_language,
    interpreting_types, experience_years, hourly_rate, daily_rate, rating,
    total_jobs, total_reviews, bio, is_verified, is_demo, is_public,
    response_time, title, current_position, education_level, university,
    major, cert_name, cert_year, notable_clients, featured_projects, badges
)
SELECT
    u.id, 'Tiếng Bồ Đào Nha, Tiếng Việt', 'Pháp lý & Hợp đồng, Công nghệ thông tin & Phần mềm', 'Tiếng Bồ Đào Nha', 'Tiếng Việt',
    'Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương', 21, 2600000.0, 19500000.0, 4.9,
    85, 72, 'Phiên dịch viên chuyên nghiệp với 21 năm kinh nghiệm thực chiến trong cặp ngôn ngữ Tiếng Bồ Đào Nha - Tiếng Việt, am hiểu sâu sắc thuật ngữ chuyên ngành Pháp lý & Hợp đồng và Công nghệ thông tin & Phần mềm. Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. Sẵn sàng nhận lịch làm việc tại khu vực Vũng Tàu cũng như các dự án trực tuyến qua Zoom/Teams.', false, true, true,
    'Trong vòng 1 giờ', 'Chuyên gia phiên dịch cabin kỳ cựu Tiếng Bồ Đào Nha - Tiếng Việt | Chuyên ngành Pháp lý & Hợp đồng', 'Phiên dịch viên Tiếng Việt – Pháp lý & Hợp đồng', 'Thạc sĩ', 'Đại học Ngoại thương (FTU)',
    'Tiếng Anh Thương mại', 'CELPE-Bras Intermediário Superior', 2023, 'Tập đoàn đa quốc gia ngành Pháp lý & Hợp đồng, Đối tác FDI tại Vũng Tàu, Ban tổ chức sự kiện quốc tế', 'Dự án đàm phán hợp đồng hợp tác Pháp lý & Hợp đồng; Hội thảo xúc tiến thương mại Công nghệ thông tin & Phần mềm', ''
FROM "user" u WHERE u.email = 'pdv050@demo.viettranslate.local';

-- InterpreterPreference
INSERT INTO interpreter_preference (user_id, languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate)
SELECT u.id, '["Tiếng Bồ Đào Nha > Tiếng Việt", "Tiếng Việt > Tiếng Bồ Đào Nha"]', '["Pháp lý & Hợp đồng", "Công nghệ thông tin & Phần mềm"]', 'both', 'Vũng Tàu', 2600000.0, 19500000.0, false
FROM "user" u WHERE u.email = 'pdv050@demo.viettranslate.local';

-- TranslatorPreference
INSERT INTO translator_preference (translator_id, languages, language_pairs, service_types, specialties, city, work_mode, offers_certified)
SELECT u.id, 'Tiếng Bồ Đào Nha, Tiếng Việt', 'Tiếng Bồ Đào Nha > Tiếng Việt, Tiếng Việt > Tiếng Bồ Đào Nha', 'Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện', 'Pháp lý & Hợp đồng, Công nghệ thông tin & Phần mềm', 'Vũng Tàu', 'both', true
FROM "user" u WHERE u.email = 'pdv050@demo.viettranslate.local';

-- InterpreterService
INSERT INTO interpreter_service (user_id, source_lang, target_lang, interpreting_type, specialization, hourly_rate, session_rate, is_active)
SELECT u.id, 'Tiếng Bồ Đào Nha', 'Tiếng Việt', 'Đàm phán & Thương mại', 'Pháp lý & Hợp đồng', 2600000.0, 10400000.0, true
FROM "user" u WHERE u.email = 'pdv050@demo.viettranslate.local';

-- Service Packages (Basic, Standard, Premium)
INSERT INTO "service" (profile_id, name, category, basic_price, standard_price, premium_price, basic_delivery, standard_delivery, premium_delivery, description, is_active)
SELECT
    p.id,
    'Dịch vụ phiên dịch Tiếng Bồ Đào Nha ↔ Tiếng Việt chuyên nghiệp',
    'Phiên dịch trực tiếp & Online',
    5200000.0, 10400000.0, 20800000.0,
    '2 giờ', '1 buổi (4 giờ)', '1 ngày (8 giờ)',
    'Phiên dịch chuyên sâu theo chuẩn quốc tế, bảo mật NDA và phản xạ chuẩn xác.',
    true
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv050@demo.viettranslate.local';

-- TranslatorVerification
INSERT INTO translator_verification (profile_id, full_name, id_number, status, verified_at, created_at)
SELECT
    p.id, 'Tạ Thanh Huyền', '00109' || LPAD(p.id::text, 7, '0'), 'draft',
    CASE WHEN false THEN NOW() ELSE NULL END, NOW()
FROM translator_profile p
JOIN "user" u ON p.user_id = u.id
WHERE u.email = 'pdv050@demo.viettranslate.local';


COMMIT;
