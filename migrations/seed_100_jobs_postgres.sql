-- ==========================================================================
-- SEED SCRIPT 100 INTERPRETER JOBS CHO POSTGRESQL (PRODUCTION / VPS)
-- Tương thích 100% PostgreSQL 16 & Supabase Cloud
-- Idempotent: chạy nhiều lần an toàn, sử dụng ON CONFLICT DO NOTHING
-- ==========================================================================

BEGIN;

-- 1. Nạp tài khoản Nhà tuyển dụng (Hirers)

INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Tập đoàn Công nghệ V-Tech', 'hirer_vtech@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'V-Tech Solutions & AI Lab', 'Trưởng phòng Hợp tác Quốc tế', 'Tòa nhà Keangnam, Cầu Giấy, Hà Nội', 4.9
FROM "user" WHERE email = 'hirer_vtech@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Bệnh viện Đa khoa Quốc tế Hạnh Phúc', 'hirer_medical@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'Hạnh Phúc International Hospital', 'Ban Hợp tác Y khoa & Chuyển giao Công nghệ', 'Quận 1, TP. Hồ Chí Minh', 4.9
FROM "user" WHERE email = 'hirer_medical@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Hãng Luật Quốc tế LexPartners', 'hirer_lexpartners@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'LexPartners Law Firm LLC', 'Luật sư Điều hành & Trọng tài viên', 'Bitexco Financial Tower, Quận 1, TP.HCM', 4.9
FROM "user" WHERE email = 'hirer_lexpartners@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Tổ hợp Chế tạo Apex Precision', 'hirer_apexmanuf@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'Apex Precision Manufacturing Co.', 'Giám đốc Vận hành Nhà máy', 'KCN DEEP C, Đình Vũ, Hải Phòng', 4.9
FROM "user" WHERE email = 'hirer_apexmanuf@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Công ty CP Đầu tư & Hạ tầng Vinastruct', 'hirer_vinastruct@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'Vinastruct Infrastructure Group', 'Ban Quản lý Dự án Giao thông & Metro', 'TP. Thủ Đức, TP. Hồ Chí Minh', 4.9
FROM "user" WHERE email = 'hirer_vinastruct@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Quỹ Đầu tư & Quản lý Tài sản Mekong', 'hirer_mekongcap@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'Mekong Capital & Ventures', 'Giám đốc Thẩm định Đầu tư M&A', 'Lotte Center, Ba Đình, Hà Nội', 4.9
FROM "user" WHERE email = 'hirer_mekongcap@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Saigon Global Travel & Hospitality', 'hirer_saigontour@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'Saigon Global Luxury Tours', 'Quản lý Dịch vụ VIP & Famtrip', 'Quận 3, TP. Hồ Chí Minh', 4.9
FROM "user" WHERE email = 'hirer_saigontour@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Viện Đối ngoại & Hợp tác Phát triển Á - Âu', 'hirer_diplomacy@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'Institute for Asian-European Diplomacy', 'Điều phối viên Dự án ODA', 'Hoàn Kiếm, Hà Nội', 4.9
FROM "user" WHERE email = 'hirer_diplomacy@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Tập đoàn Năng lượng Xanh GreenPower', 'hirer_greenpower@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'GreenPower Renewables & Offshore', 'Trưởng ban Kỹ thuật Dự án Điện gió', 'Vũng Tàu, Bà Rịa - Vũng Tàu', 4.9
FROM "user" WHERE email = 'hirer_greenpower@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Hãng Giao nhận Vận tải TransGlobal', 'hirer_transglobal@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'TransGlobal Freight & Marine Logistics', 'Giám đốc Khai thác Cảng & Chuỗi cung ứng', 'Khu ngoại quan Cái Mép, Bà Rịa - Vũng Tàu', 4.9
FROM "user" WHERE email = 'hirer_transglobal@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Hiệp hội Thực phẩm & Nông sản Sạch V-Agri', 'hirer_vasepfood@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'V-Agri Food Export Alliance', 'Phụ trách Xúc tiến Thương mại Quốc tế', 'Ninh Kiều, Cần Thơ', 4.9
FROM "user" WHERE email = 'hirer_vasepfood@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


INSERT INTO "user" (name, email, password_hash, role, is_active, created_at)
VALUES ('Tổ chức Giáo dục Quốc tế Global Pathway', 'hirer_edu_intl@viettranslate.demo', 'scrypt:32768:8:1$tqQOsP5ak4gwVkgm$47ed11c5590c6b1fb8e7ddf9624b8461f25ccd198bbf84072968090b69238c6a2dbe3a627942a6f99748abe98fac6542c3876feb64797a9e38f642cd85b90c36', 'hirer', true, NOW())
ON CONFLICT (email) DO UPDATE SET is_active = true;

INSERT INTO hirer_profile (user_id, company, title, location, rating)
SELECT id, 'Global Pathway Education', 'Giám đốc Tuyển sinh & Liên kết Đại học', 'Hải Châu, Đà Nẵng', 4.9
FROM "user" WHERE email = 'hirer_edu_intl@viettranslate.demo'
ON CONFLICT (user_id) DO NOTHING;


-- 2. Nạp 100 việc làm phiên dịch đa ngành (Jobs)

INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch cabin Hội nghị Thượng đỉnh Trí tuệ Nhân tạo AI Summit 2026', 'Cần 02 phiên dịch viên cabin chuyên ngành AI/Machine Learning cho hội thảo quốc tế với hơn 500 khách mời. Nội dung về Large Language Models, Generative AI và ứng dụng điện toán đám mây. Tài liệu thuyết trình và glossary thuật ngữ sẽ được gửi trước 5 ngày.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Anh', 'Tiếng Việt', 'range', 6000000, 9500000,
    '2026-11-12', '08:00', '17:30', 'Trung tâm Hội nghị Quốc gia, Nam Từ Liêm, Hà Nội',
    CURRENT_DATE + INTERVAL '18 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_vtech@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch cabin Hội nghị Thượng đỉnh Trí tuệ Nhân tạo AI Summit 2026');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn chuyên gia Nhật Bản nghiệm thu hệ thống Cloud ERP', 'Đoàn gồm 4 kỹ sư giải pháp từ Tokyo sang thẩm định quy trình vận hành và kiểm thử bảo mật dữ liệu hệ thống SAP/Cloud ERP tại trụ sở công ty. Yêu cầu JLPT N1/N2, tác phong doanh nghiệp chuẩn Nhật, nắm vững thuật ngữ công nghệ thông tin.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 3500000, 5500000,
    '2026-10-28', '08:30', '17:00', 'Tòa nhà Etown Central, Quận 4, TP. Hồ Chí Minh',
    CURRENT_DATE + INTERVAL '8 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_vtech@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn chuyên gia Nhật Bản nghiệm thu hệ thống Cloud ERP');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch đàm phán hợp tác chuyển giao công nghệ bán dẫn với đối tác Hàn Quốc', 'Buổi làm việc cấp cao giữa Ban Tổng Giám đốc và phái đoàn tập đoàn bán dẫn Seoul về đầu tư dây chuyền đóng gói vi mạch bán dẫn Packaging & Testing tại Khu công nghệ cao Đà Nẵng. Yêu cầu bảo mật thông tin tuyệt đối (ký NDA).', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Hàn', 'Tiếng Việt', 'range', 5000000, 8000000,
    '2026-11-05', '09:00', '16:30', 'Khách sạn Novotel Danang Premier Han River, Đà Nẵng',
    CURRENT_DATE + INTERVAL '12 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_vtech@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch đàm phán hợp tác chuyển giao công nghệ bán dẫn với đối tác Hàn Quốc');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch trực tuyến 2 giờ giới thiệu phần mềm FinTech cho khách hàng Thượng Hải', 'Họp trực tuyến qua Zoom để demo tính năng cổng thanh toán xuyên biên giới và giải đáp thắc mắc kỹ thuật tích hợp API cho đối tác thương mại Thượng Hải. Cần phiên dịch viên nói lưu loát tiếng Trung chuẩn phổ thông, tác phong nhanh nhẹn.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Trung', 'Tiếng Việt', 'fixed', 450000, NULL,
    '2026-10-22', '14:00', '16:00', 'Trực tuyến qua Zoom Meeting',
    CURRENT_DATE + INTERVAL '5 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_vtech@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch trực tuyến 2 giờ giới thiệu phần mềm FinTech cho khách hàng Thượng Hải');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch Workshop An ninh Mạng & Phòng chống Ransomware cùng chuyên gia Đức', 'Buổi đào tạo chuyên sâu kéo dài 1 ngày dành cho đội ngũ SOC và DevOps về nhận diện mối đe dọa Zero-day và chính sách bảo mật ISO 27001 từ chuyên gia Berlin. Dịch nối tiếp song song kết hợp giải thích câu hỏi kỹ thuật.', 'Hội thảo', 'interpretation_other', 'conference',
    'Tiếng Đức', 'Tiếng Việt', 'range', 3500000, 6000000,
    '2026-11-18', '08:30', '17:00', 'Học viện Công nghệ Bưu chính Viễn thông, Hà Đông, Hà Nội',
    CURRENT_DATE + INTERVAL '20 days', 'open', 'approved', false, NOW() - INTERVAL '5 days'
FROM "user" u WHERE u.email = 'hirer_vtech@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch Workshop An ninh Mạng & Phòng chống Ransomware cùng chuyên gia Đức');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch cabin Hội thảo Can thiệp Tim mạch Quốc tế Pháp - Việt lần thứ 12', 'Hội nghị khoa học thường niên quy tụ 30 giáo sư đầu ngành từ Bệnh viện Tim Paris và các bệnh viện tuyến đầu Việt Nam. Dịch cabin trực tiếp các ca mổ truyền hình trực tiếp và báo cáo lâm sàng kỹ thuật cao.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Pháp', 'Tiếng Việt', 'range', 7000000, 12000000,
    '2026-11-20', '08:00', '17:30', 'Trung tâm Hội nghị White Palace, Phú Nhuận, TP.HCM',
    CURRENT_DATE + INTERVAL '22 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_medical@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch cabin Hội thảo Can thiệp Tim mạch Quốc tế Pháp - Việt lần thứ 12');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn bác sĩ chuyên khoa thẩm mỹ tái tạo Hàn Quốc làm việc tại BV Hạnh Phúc', 'Hỗ trợ đoàn bác sĩ ngoại khoa Bệnh viện Đại học Quốc gia Seoul trong quá trình thăm khám, hội chẩn trước phẫu thuật và hướng dẫn hậu phẫu cho bệnh nhân. Cần phát âm chuẩn, thái độ ân cần và quen thuộc y lệnh tiếng Hàn.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Hàn', 'Tiếng Việt', 'range', 4000000, 6500000,
    '2026-10-30', '08:00', '17:00', 'Bệnh viện Quốc tế Hạnh Phúc, Quận 1, TP. Hồ Chí Minh',
    CURRENT_DATE + INTERVAL '9 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_medical@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn bác sĩ chuyên khoa thẩm mỹ tái tạo Hàn Quốc làm việc tại BV Hạnh Phúc');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch kỹ thuật lắp đặt & hướng dẫn vận hành hệ thống máy chụp cộng hưởng từ MRI 3.0T Siemens', 'Kỹ sư chuyên gia y sinh từ Erlangen (Đức) hướng dẫn nhóm kỹ sư và bác sĩ chẩn đoán hình ảnh tại Cần Thơ về quy chuẩn vận hành, cân chỉnh từ trường và bảo dưỡng định kỳ máy chụp MRI thế hệ mới.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Đức', 'Tiếng Việt', 'range', 3800000, 5500000,
    '2026-11-08', '08:30', '16:30', 'Bệnh viện Đa khoa Trung ương Cần Thơ, Ninh Kiều, Cần Thơ',
    CURRENT_DATE + INTERVAL '15 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_medical@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch kỹ thuật lắp đặt & hướng dẫn vận hành hệ thống máy chụp cộng hưởng từ MRI 3.0T Siemens');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tư vấn từ xa 1 giờ giải mã kết quả xét nghiệm di truyền & ung bướu với chuyên gia Mỹ', 'Phiên dịch nối tiếp trực tuyến buổi tư vấn giữa bệnh nhân, gia đình và bác sĩ chuyên khoa ung bướu Bệnh viện Mayo Clinic (Mỹ). Yêu cầu dịch chính xác, truyền tải rõ ràng chỉ số xét nghiệm gen di truyền, giọng nói ấm áp.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Anh', 'Tiếng Việt', 'fixed', 400000, NULL,
    '2026-10-24', '20:00', '21:00', 'Trực tuyến qua Microsoft Teams',
    CURRENT_DATE + INTERVAL '6 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_medical@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tư vấn từ xa 1 giờ giải mã kết quả xét nghiệm di truyền & ung bướu với chuyên gia Mỹ');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội thảo Quốc tế Nghiên cứu Dược phẩm & Thử nghiệm Lâm sàng Vắc-xin Sinh học', 'Phiên dịch hội trường phiên thảo luận quy trình cấp phép và chuẩn mực thử nghiệm lâm sàng GCP quốc tế. Có đại diện các tập đoàn dược phẩm đa quốc gia và cơ quan quản lý dược phẩm Việt Nam tham dự.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Anh', 'Tiếng Việt', 'range', 3000000, 5000000,
    '2026-11-25', '08:30', '17:00', 'Khách sạn Vinpearl Resort & Spa Nha Trang Bay, Khánh Hòa',
    CURRENT_DATE + INTERVAL '24 days', 'open', 'approved', false, NOW() - INTERVAL '6 days'
FROM "user" u WHERE u.email = 'hirer_medical@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội thảo Quốc tế Nghiên cứu Dược phẩm & Thử nghiệm Lâm sàng Vắc-xin Sinh học');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch phiên điều trần trọng tài quốc tế tại Trung tâm Trọng tài VIAC', 'Vụ tranh chấp hợp đồng mua bán ngoại thương và bồi thường thiệt hại logistics giữa công ty xuất nhập khẩu Việt Nam và đối tác châu Âu. Phiên xử kéo dài cả ngày, yêu cầu phiên dịch viên am tường tố tụng trọng tài thương mại quốc tế.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Anh', 'Tiếng Việt', 'range', 8000000, 14000000,
    '2026-11-15', '08:00', '17:30', 'Trung tâm Trọng tài Quốc tế Việt Nam (VIAC), Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '17 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_lexpartners@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch phiên điều trần trọng tài quốc tế tại Trung tâm Trọng tài VIAC');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch đàm phán hợp đồng M&A chuyển nhượng cổ phần doanh nghiệp vốn Nhật Bản', 'Đàm phán chi tiết các điều khoản bảo đảm vốn, quyền biểu quyết và nghĩa vụ cổ đông chiến lược. Yêu cầu dịch chính xác từng thuật ngữ luật doanh nghiệp Nhật - Việt, phản xạ nhanh và tuyệt đối trung lập.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 5500000, 8500000,
    '2026-11-03', '08:30', '17:00', 'Khách sạn Lotte Hotel Hanoi, Ba Đình, Hà Nội',
    CURRENT_DATE + INTERVAL '10 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_lexpartners@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch đàm phán hợp đồng M&A chuyển nhượng cổ phần doanh nghiệp vốn Nhật Bản');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng luật sư và thân chủ quốc tịch Nga làm việc tại Tòa án & Viện kiểm sát Vũng Tàu', 'Cần thông dịch viên tiếng Nga đồng hành cùng luật sư giải quyết thủ tục phân chia tài sản và quyền giám hộ liên quan đến công dân Liên bang Nga tại Vũng Tàu. Yêu cầu tác phong đứng đắn, giọng nói chuẩn và nắm chắc thuật ngữ tố tụng dân sự.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Nga', 'Tiếng Việt', 'range', 2500000, 4200000,
    '2026-10-29', '08:00', '16:00', 'Tòa án Nhân dân tỉnh Bà Rịa - Vũng Tàu, TP. Bà Rịa',
    CURRENT_DATE + INTERVAL '8 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_lexpartners@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng luật sư và thân chủ quốc tịch Nga làm việc tại Tòa án & Viện kiểm sát Vũng Tàu');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tư vấn trực tuyến 1.5 giờ về đăng ký bảo hộ nhãn hiệu và quyền tác giả tại thị trường Anh', 'Họp trực tuyến giữa doanh nghiệp thời trang xuất khẩu Việt Nam và luật sư sở hữu trí tuệ tại London để chuẩn bị hồ sơ nộp đơn lên Cục Sở hữu Trí tuệ Vương quốc Anh (UKIPO).', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Anh', 'Tiếng Việt', 'fixed', 600000, NULL,
    '2026-10-23', '15:00', '16:30', 'Trực tuyến qua Zoom Meeting',
    CURRENT_DATE + INTERVAL '4 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_lexpartners@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tư vấn trực tuyến 1.5 giờ về đăng ký bảo hộ nhãn hiệu và quyền tác giả tại thị trường Anh');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch công chứng hợp đồng góp vốn & thuê nhà xưởng khu công nghiệp cho nhà đầu tư Đài Loan', 'Hỗ trợ đoàn doanh nhân Đài Loan ký kết văn bản công chứng chuyển nhượng quyền sử dụng đất và thuê hạ tầng nhà xưởng 20.000m2. Cần phiên dịch chuẩn xác, đọc hiểu hợp đồng kinh tế tiếng Trung phồn thể/giản thể.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Trung', 'Tiếng Việt', 'range', 2000000, 3500000,
    '2026-11-06', '09:00', '15:30', 'Văn phòng Công chứng Bến Cát, KCN Mỹ Phước 3, Bình Dương',
    CURRENT_DATE + INTERVAL '13 days', 'open', 'approved', false, NOW() - INTERVAL '5 days'
FROM "user" u WHERE u.email = 'hirer_lexpartners@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch công chứng hợp đồng góp vốn & thuê nhà xưởng khu công nghiệp cho nhà đầu tư Đài Loan');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch chuyển giao công nghệ dập đúc kim loại tự động Fanuc từ Nhật Bản', 'Nhà máy cơ khí chính xác tại Hải Phòng tiếp nhận 2 cụm máy ép dập thuỷ lực tự động 500 tấn. Chuyên gia Nhật hướng dẫn cài đặt thông số servo, calibrate cảm biến quang học và xử lý sự cố kẹt khuôn.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 3200000, 5000000,
    '2026-11-10', '08:00', '17:00', 'Khu Công nghiệp DEEP C 1, Đình Vũ, Hải Phòng',
    CURRENT_DATE + INTERVAL '16 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_apexmanuf@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch chuyển giao công nghệ dập đúc kim loại tự động Fanuc từ Nhật Bản');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Đào tạo an toàn lao động & vận hành lò luyện phôi thép chuyên gia Trung Quốc', 'Đào tạo trực tiếp tại phân xưởng luyện kim cho 40 công nhân và kỹ thuật viên Việt Nam. Nội dung bao gồm quy trình nạp liệu, kiểm soát nhiệt độ hồ quang và cấp cứu ngộ độc khí CO.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Trung', 'Tiếng Việt', 'range', 2000000, 3500000,
    '2026-10-31', '08:00', '16:30', 'Nhà máy Thép Cán Nguội, TX. Quảng Yên, Quảng Ninh',
    CURRENT_DATE + INTERVAL '9 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_apexmanuf@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Đào tạo an toàn lao động & vận hành lò luyện phôi thép chuyên gia Trung Quốc');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn thanh tra chất lượng ISO 9001 & BSCI cho chuỗi nhà máy dệt may xuất khẩu', 'Đoàn đánh giá viên kiểm toán độc lập quốc tế thực hiện audit nhà máy dệt may, phỏng vấn đại diện công đoàn, kiểm tra nhật ký giờ làm việc và quy chuẩn an toàn hóa chất phòng cháy.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Anh', 'Tiếng Việt', 'range', 1800000, 3000000,
    '2026-10-27', '08:00', '17:00', 'KCN Amata, TP. Biên Hòa, Đồng Nai',
    CURRENT_DATE + INTERVAL '7 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_apexmanuf@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn thanh tra chất lượng ISO 9001 & BSCI cho chuỗi nhà máy dệt may xuất khẩu');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch kỹ thuật lắp đặt cụm cánh tay Robot công nghiệp 6 trục KUKA từ Đức', 'Kỹ sư chuyên gia hãng KUKA hướng dẫn lập trình đường chạy robot hàn điểm và liên kết PLC Siemens S7-1500 cho dây chuyền phụ tùng xe gắn máy.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Đức', 'Tiếng Việt', 'range', 4000000, 6500000,
    '2026-11-16', '08:30', '17:00', 'KCN VSIP 2 Mở rộng, TX. Tân Uyên, Bình Dương',
    CURRENT_DATE + INTERVAL '21 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_apexmanuf@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch kỹ thuật lắp đặt cụm cánh tay Robot công nghiệp 6 trục KUKA từ Đức');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Họp kỹ thuật xử lý sự cố thiết bị máy ép nhựa thủy lực tốc độ cao Hàn Quốc', 'Buổi họp tại chỗ giữa đội ngũ bảo trì nhà máy và kỹ sư bảo hành hãng Woojin Plaimm để phân tích nguyên nhân lỗi nhiệt độ dầu thủy lực và điều chỉnh chu kỳ ép khuôn mẫu linh kiện điện tử.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Hàn', 'Tiếng Việt', 'range', 2200000, 3800000,
    '2026-10-26', '09:00', '16:00', 'KCN Quế Võ, TP. Bắc Ninh, Bắc Ninh',
    CURRENT_DATE + INTERVAL '6 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_apexmanuf@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Họp kỹ thuật xử lý sự cố thiết bị máy ép nhựa thủy lực tốc độ cao Hàn Quốc');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch hiện trường công trường dự án mở rộng Tuyến Metro ngầm', 'Tháp tùng nhóm kỹ sư tư vấn giám sát Nhật Bản (Nippon Koei) kiểm tra thi công khoan hầm TBM, lắp đặt tấm vỏ hầm đúc sẵn và nghiệm thu cốt thép móng ga ngầm.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 3500000, 5800000,
    '2026-11-04', '07:30', '16:30', 'Công trường Nhà ga Bến Thành - Suối Tiên, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '11 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_vinastruct@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch hiện trường công trường dự án mở rộng Tuyến Metro ngầm');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Họp giao ban tiến độ thi công cao ốc tổ hợp thương mại với tổng thầu Hàn Quốc', 'Họp rà soát mốc bàn giao các gói thầu thi công mặt dựng kính Curtain Wall, thang máy tải trọng lớn và hệ thống cứu hỏa tiêu chuẩn NFPA với Ban Điều hành dự án Hyundai E&C.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Hàn', 'Tiếng Việt', 'range', 2800000, 4500000,
    '2026-11-09', '08:30', '16:30', 'Ban Quản lý Dự án Tòa tháp StarLake, Tây Hồ Tây, Hà Nội',
    CURRENT_DATE + INTERVAL '14 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_vinastruct@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Họp giao ban tiến độ thi công cao ốc tổ hợp thương mại với tổng thầu Hàn Quốc');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội thảo Kiến trúc Bền vững & Thiết kế Công trình Tiết kiệm Năng lượng Pháp - Việt', 'Hội thảo chuyên môn có bài phát biểu của các kiến trúc sư trưởng từ Paris giới thiệu vật liệu sinh thái, giải pháp thông gió tự nhiên nhiệt đới hóa và chứng chỉ công trình xanh LOTUS/LEED.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Pháp', 'Tiếng Việt', 'range', 3200000, 5500000,
    '2026-11-19', '08:30', '17:00', 'Trung tâm Hành chính TP. Đà Nẵng, Hải Châu, Đà Nẵng',
    CURRENT_DATE + INTERVAL '23 days', 'open', 'approved', false, NOW() - INTERVAL '5 days'
FROM "user" u WHERE u.email = 'hirer_vinastruct@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội thảo Kiến trúc Bền vững & Thiết kế Công trình Tiết kiệm Năng lượng Pháp - Việt');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng khảo sát địa chất & thiết kế kết cấu cầu vượt biển chuyên gia Vương quốc Anh', 'Làm việc tại hiện trường ven biển Hải Phòng và trên cano khảo sát vị trí móng cọc trụ cầu dây văng. Kỹ sư kết cấu Anh cần trao đổi chi tiết về độ sụt lún bùn đáy biển và ăn mòn nước mặn.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Anh', 'Tiếng Việt', 'range', 4000000, 6800000,
    '2026-11-07', '07:00', '16:00', 'Khu vực Cảng Lạch Huyện - Cát Hải, Hải Phòng',
    CURRENT_DATE + INTERVAL '13 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_vinastruct@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng khảo sát địa chất & thiết kế kết cấu cầu vượt biển chuyên gia Vương quốc Anh');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Đàm phán gói thầu cơ điện MEP trung tâm logistics quy mô 50 triệu USD', 'Phiên làm việc song ngữ đàm phán hợp đồng cung ứng và lắp đặt hệ thống máy phát điện dự phòng, điều hòa không khí VRV trung tâm và trạm biến áp hạ thế cho chủ đầu tư Singapore.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Anh', 'Tiếng Việt', 'range', 2500000, 4000000,
    '2026-10-28', '09:00', '16:30', 'Tòa nhà Saigon Centre, Lê Lợi, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '7 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_vinastruct@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Đàm phán gói thầu cơ điện MEP trung tâm logistics quy mô 50 triệu USD');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch cabin Diễn đàn Đầu tư Mạo hiểm & Startup Đông Nam Á (Venture Summit)', 'Sự kiện quy tụ hơn 40 quỹ đầu tư mạo hiểm (Sequoia, 500 Global, Insignia) và 80 nhà sáng lập công nghệ. Phiên dịch cabin song song các phần thuyết trình gọi vốn Pitching Session và tọa đàm kinh tế vĩ mô.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Anh', 'Tiếng Việt', 'range', 7500000, 13000000,
    '2026-11-14', '08:00', '18:00', 'Khách sạn The Reverie Saigon, Times Square, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '19 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_mekongcap@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch cabin Diễn đàn Đầu tư Mạo hiểm & Startup Đông Nam Á (Venture Summit)');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Đàm phán hợp đồng vay hợp vốn quốc tế 120 triệu USD giữa các ngân hàng thương mại', 'Phiên làm việc kỹ thuật giữa đoàn đàm phán tài chính doanh nghiệp và nhóm đại diện ngân hàng bảo lãnh tín dụng (Syndicated Loan). Yêu cầu nắm chắc các khái niệm L/C, lãi suất SOFR, covenant tài chính.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Anh', 'Tiếng Việt', 'range', 5000000, 8500000,
    '2026-11-02', '09:00', '17:00', 'Tòa nhà Ngân hàng Nhà nước, Hoàn Kiếm, Hà Nội',
    CURRENT_DATE + INTERVAL '10 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_mekongcap@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Đàm phán hợp đồng vay hợp vốn quốc tế 120 triệu USD giữa các ngân hàng thương mại');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn lãnh đạo Quỹ Đầu tư Tư nhân Tokyo khảo sát các doanh nghiệp bán lẻ', 'Đồng hành cùng 3 đối tác quản lý quỹ của Nhật trong chuyến công tác 2 ngày khảo sát thực tế mạng lưới kho bãi, quy trình quản lý tồn kho và trao đổi với ban điều hành công ty mục tiêu.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 4000000, 6500000,
    '2026-11-11', '08:30', '17:30', 'KCN Tân Bình và các trung tâm phân phối tại TP.HCM',
    CURRENT_DATE + INTERVAL '16 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_mekongcap@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn lãnh đạo Quỹ Đầu tư Tư nhân Tokyo khảo sát các doanh nghiệp bán lẻ');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Thẩm định năng lực tài chính & Due Diligence dự án nhà máy quang điện với đối tác Trung Quốc', 'Kiểm toán soát xét chứng từ kế toán, dòng tiền dự án EPC năng lượng và mô hình dự báo tài chính DCF tại chỗ với đoàn kiểm toán viên và ban tài chính tập đoàn Hong Kong.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Trung', 'Tiếng Việt', 'range', 3000000, 5200000,
    '2026-11-05', '08:30', '17:00', 'Văn phòng Dự án Năng lượng, TP. Phan Rang - Tháp Chàm, Ninh Thuận',
    CURRENT_DATE + INTERVAL '12 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_mekongcap@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Thẩm định năng lực tài chính & Due Diligence dự án nhà máy quang điện với đối tác Trung Quốc');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Họp trực tuyến 2 giờ rà soát báo cáo tài chính IFRS theo chuẩn mực kế toán quốc tế', 'Thảo luận về phương pháp ghi nhận suy giảm giá trị tài sản vô hình và khấu hao tài sản cố định theo chuẩn IAS 36 giữa kế toán trưởng tại Việt Nam và chuyên gia kiểm toán PwC Singapore.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Anh', 'Tiếng Việt', 'fixed', 850000, NULL,
    '2026-10-25', '14:00', '16:00', 'Trực tuyến qua Zoom Meeting',
    CURRENT_DATE + INTERVAL '5 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_mekongcap@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Họp trực tuyến 2 giờ rà soát báo cáo tài chính IFRS theo chuẩn mực kế toán quốc tế');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn du khách thượng lưu Pháp trải nghiệm du thuyền cao cấp vịnh Hạ Long (2 ngày)', 'Đoàn 8 du khách VIP quốc tịch Pháp đi tour du thuyền 5 sao khám phá di sản vịnh Hạ Long và vịnh Lan Hạ. Thuyết minh địa chất hang động, hỗ trợ dịch thực đơn fine dining và phục vụ suốt hành trình.', 'Du lịch', 'interpretation_other', 'travel',
    'Tiếng Pháp', 'Tiếng Việt', 'range', 5000000, 8000000,
    '2026-11-07', '08:00', '18:00', 'Cảng Tàu Khách Quốc tế Tuần Châu, TP. Hạ Long, Quảng Ninh',
    CURRENT_DATE + INTERVAL '13 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn du khách thượng lưu Pháp trải nghiệm du thuyền cao cấp vịnh Hạ Long (2 ngày)');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch đoàn Famtrip 20 công ty lữ hành Liên bang Nga khảo sát chuỗi resort Nha Trang', 'Hỗ trợ đoàn đại diện các hãng lữ hành lớn của Nga khảo sát hạ tầng lưu trú, dịch vụ tắm bùn khoáng nóng, khu vui chơi giải trí và đàm phán hợp đồng bao phòng mùa cao điểm đông xuân.', 'Du lịch', 'interpretation_other', 'travel',
    'Tiếng Nga', 'Tiếng Việt', 'range', 3200000, 5500000,
    '2026-11-13', '08:30', '17:30', 'Khu nghỉ dưỡng Vinpearl Resort & Spa Nha Trang, Khánh Hòa',
    CURRENT_DATE + INTERVAL '17 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch đoàn Famtrip 20 công ty lữ hành Liên bang Nga khảo sát chuỗi resort Nha Trang');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hướng dẫn đoàn du khách cao cấp Thái Lan trải nghiệm ẩm thực phố cổ Hà Nội', 'Dẫn đoàn 10 khách thương gia Thái Lan thưởng thức ẩm thực Michelin Selected tại phố cổ Hà Nội, giới thiệu văn hóa cà phê trứng, trà sen Tây Hồ và mua sắm lụa tơ tằm Vạn Phúc.', 'Du lịch', 'interpretation_other', 'travel',
    'Tiếng Thái', 'Tiếng Việt', 'range', 1500000, 2500000,
    '2026-10-27', '10:00', '18:00', 'Khu phố cổ Hoàn Kiếm, Hà Nội',
    CURRENT_DATE + INTERVAL '6 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hướng dẫn đoàn du khách cao cấp Thái Lan trải nghiệm ẩm thực phố cổ Hà Nội');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn doanh nhân Tây Ban Nha tham quan làng nghề điêu khắc đá Non Nước & phố cổ Hội An', 'Thuyết minh lịch sử giao thương Đàng Trong thế kỷ 17, giới thiệu kiến trúc nhà cổ và nghệ thuật chế tác thủ công mỹ nghệ cho đoàn kiến trúc sư và nhà sưu tập nghệ thuật Tây Ban Nha.', 'Du lịch', 'interpretation_other', 'travel',
    'Tiếng Tây Ban Nha', 'Tiếng Việt', 'range', 2200000, 3800000,
    '2026-11-01', '08:30', '17:00', 'Khu phố cổ Hội An, Quảng Nam và Làng đá Non Nước, Đà Nẵng',
    CURRENT_DATE + INTERVAL '9 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn doanh nhân Tây Ban Nha tham quan làng nghề điêu khắc đá Non Nước & phố cổ Hội An');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch viên phục vụ giải Golf giao hữu doanh nhân Hàn Quốc tại đảo ngọc Phú Quốc', 'Đồng hành trên sân golf 18 lỗ hỗ trợ dịch giao lưu thi đấu thể thao giữa các CEO câu lạc bộ doanh nhân Daegu và hội đồng doanh nghiệp tỉnh Kiên Giang. Yêu cầu ngoại hình thanh lịch, hiểu rõ quy tắc và thuật ngữ chơi golf.', 'Du lịch', 'interpretation_other', 'travel',
    'Tiếng Hàn', 'Tiếng Việt', 'range', 3500000, 6000000,
    '2026-11-17', '06:30', '15:30', 'Sân Vinpearl Golf Phú Quốc, Gành Dầu, TP. Phú Quốc',
    CURRENT_DATE + INTERVAL '21 days', 'open', 'approved', false, NOW() - INTERVAL '6 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch viên phục vụ giải Golf giao hữu doanh nhân Hàn Quốc tại đảo ngọc Phú Quốc');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch cabin Diễn đàn Kinh tế & Hợp tác Song phương Việt Nam - Cộng hòa Pháp', 'Hội nghị cấp cao nhân dịp kỷ niệm quan hệ đối tác chiến lược giữa hai nước với sự tham dự của các bộ trưởng, đại sứ quán và hơn 200 tập đoàn hàng đầu. Yêu cầu phiên dịch cabin kỳ cựu, giọng chuẩn Paris, nắm chắc nghi thức ngoại giao.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Pháp', 'Tiếng Việt', 'range', 9000000, 16000000,
    '2026-11-24', '08:00', '17:30', 'Khách sạn Sofitel Legend Metropole Hanoi, Ngô Quyền, Hà Nội',
    CURRENT_DATE + INTERVAL '25 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch cabin Diễn đàn Kinh tế & Hợp tác Song phương Việt Nam - Cộng hòa Pháp');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng phái đoàn Đại sứ quán Bồ Đào Nha làm việc với UBND TP. Hồ Chí Minh', 'Hỗ trợ phái đoàn ngoại giao và doanh nghiệp Bồ Đào Nha trong buổi chào xã giao lãnh đạo thành phố, thảo luận về hợp tác bảo tồn kiến trúc di sản đô thị và xúc tiến thương mại nông nghiệp Nam Âu.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Bồ Đào Nha', 'Tiếng Việt', 'range', 4000000, 6500000,
    '2026-11-06', '08:30', '16:30', 'Trụ sở UBND TP. Hồ Chí Minh, 86 Lê Thánh Tôn, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '12 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng phái đoàn Đại sứ quán Bồ Đào Nha làm việc với UBND TP. Hồ Chí Minh');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Họp đánh giá tác động môi trường & xã hội dự án ODA viện trợ không hoàn lại của JICA Nhật Bản', 'Làm việc cùng đoàn thẩm định JICA về tiến độ đền bù giải phóng mặt bằng và các giải pháp chống ngập thích ứng triều cường vùng đồng bằng sông Cửu Long.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 3500000, 5800000,
    '2026-11-09', '08:00', '16:30', 'Sở Nông nghiệp & Phát triển Nông thôn TP. Cần Thơ, Ninh Kiều',
    CURRENT_DATE + INTERVAL '15 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Họp đánh giá tác động môi trường & xã hội dự án ODA viện trợ không hoàn lại của JICA Nhật Bản');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch phái đoàn Ủy ban Thương mại Nghị viện Châu Âu về giám sát thực thi hiệp định EVFTA', 'Tọa đàm chuyên đề giữa các nghị sĩ châu Âu, đại diện Bộ Công Thương và các hiệp hội xuất khẩu Việt Nam về sở hữu trí tuệ, tiêu chuẩn lao động và bảo vệ môi trường bền vững.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Anh', 'Tiếng Việt', 'range', 6500000, 11000000,
    '2026-11-18', '08:30', '17:00', 'Tòa nhà Quốc hội, Ba Đình, Hà Nội',
    CURRENT_DATE + INTERVAL '20 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch phái đoàn Ủy ban Thương mại Nghị viện Châu Âu về giám sát thực thi hiệp định EVFTA');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội nghị Liên kết các Thành phố Kết nghĩa Việt Nam - Liên bang Nga nhân kỷ niệm thiết lập quan hệ', 'Phiên dịch song song thảo luận về chương trình trao đổi sinh viên đại học, liên kết du lịch biển và hợp tác khai thác logistics cảng biển giữa Đà Nẵng và Saint Petersburg.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Nga', 'Tiếng Việt', 'range', 4500000, 7500000,
    '2026-11-21', '08:30', '17:00', 'Khách sạn Furama Resort Danang, Ngũ Hành Sơn, Đà Nẵng',
    CURRENT_DATE + INTERVAL '22 days', 'open', 'approved', false, NOW() - INTERVAL '5 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội nghị Liên kết các Thành phố Kết nghĩa Việt Nam - Liên bang Nga nhân kỷ niệm thiết lập quan hệ');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch kỹ thuật công tác trên giàn khoan dầu khí ngoài khơi Vietsovpetro (2 ngày)', 'Bay trực thăng ra giàn khoan mỏ Bạch Hổ để dịch nối tiếp kỹ thuật lắp đặt đầu giếng ngầm và hệ thống van chống phun trào áp lực cao cùng chuyên gia kỹ thuật Nga.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Nga', 'Tiếng Việt', 'range', 7000000, 12000000,
    '2026-11-12', '07:00', '18:00', 'Giàn khoan trung tâm Mỏ Bạch Hổ, Thềm lục địa Vũng Tàu',
    CURRENT_DATE + INTERVAL '16 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_greenpower@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch kỹ thuật công tác trên giàn khoan dầu khí ngoài khơi Vietsovpetro (2 ngày)');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội thảo Quốc tế về Phát triển Điện gió Ngoài khơi & Công nghệ Hydro Xanh', 'Hội thảo bàn tròn kỹ thuật giữa Bộ Công Thương, đại diện Tập đoàn Orsted (Đan Mạch) và các nhà đầu tư quốc tế về cơ chế giá FIT, khảo sát độ sâu đáy biển và chuỗi cung ứng tua-bin 15MW.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Anh', 'Tiếng Việt', 'range', 5500000, 9000000,
    '2026-11-23', '08:30', '17:30', 'Khách sạn Sea Links City, Mũi Né, TP. Phan Thiết, Bình Thuận',
    CURRENT_DATE + INTERVAL '24 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_greenpower@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội thảo Quốc tế về Phát triển Điện gió Ngoài khơi & Công nghệ Hydro Xanh');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng chuyên gia Trung Quốc lắp đặt & hiệu chuẩn trạm biến áp 220kV nhà máy điện mặt trời', 'Làm việc tại hiện trường kiểm tra sơ đồ đấu nối máy biến áp lực, tủ điều khiển bảo vệ rơ-le số và hệ thống giám sát SCADA công trình quang điện 150MW.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Trung', 'Tiếng Việt', 'range', 2800000, 4800000,
    '2026-10-30', '08:00', '17:00', 'Khu vực Nhà máy Điện mặt trời Dầu Tiếng, Dương Minh Châu, Tây Ninh',
    CURRENT_DATE + INTERVAL '8 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_greenpower@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng chuyên gia Trung Quốc lắp đặt & hiệu chuẩn trạm biến áp 220kV nhà máy điện mặt trời');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Đàm phán hợp đồng mua bán chứng chỉ năng lượng tái tạo quốc tế I-REC', 'Họp song phương giữa chủ đầu tư cụm nhà máy thủy điện vừa và nhỏ tại Việt Nam với quỹ đầu tư thương mại carbon Thụy Sĩ về giá bán và cơ chế chuyển quyền sở hữu chỉ tiêu phát thải.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Anh', 'Tiếng Việt', 'range', 3000000, 5000000,
    '2026-11-04', '09:00', '16:00', 'Tòa nhà Deutsches Haus, Lê Duẩn, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '11 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_greenpower@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Đàm phán hợp đồng mua bán chứng chỉ năng lượng tái tạo quốc tế I-REC');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Họp kỹ thuật chuyên gia Đức đánh giá hiệu suất tổ máy phát điện chạy khí Biogas', 'Chuyên gia động cơ khí đốt MTU (Đức) kiểm tra hệ thống lọc tạp chất H2S, độ ổn định điện áp và tiêu chuẩn khí thải Euro 6 của dự án năng lượng sinh học từ trang trại chăn nuôi quy mô lớn.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Đức', 'Tiếng Việt', 'range', 3000000, 4800000,
    '2026-11-10', '08:30', '16:30', 'Trang trại Năng lượng Xanh, Cẩm Mỹ, Đồng Nai',
    CURRENT_DATE + INTERVAL '16 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_greenpower@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Họp kỹ thuật chuyên gia Đức đánh giá hiệu suất tổ máy phát điện chạy khí Biogas');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch nghiệm thu kỹ thuật bảo dưỡng đại tu động cơ phản lực Boeing 787', 'Làm việc tại xưởng bảo dưỡng máy bay VAECO cùng chuyên gia hãng chế tạo động cơ Rolls-Royce/GE kiểm tra cánh quạt tuabin áp suất cao và hệ thống đo lường dao động động cơ.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Anh', 'Tiếng Việt', 'range', 5000000, 8500000,
    '2026-11-13', '08:00', '17:00', 'Khu Hangar Bảo dưỡng Máy bay VAECO, Sân bay Quốc tế Nội Bài, Hà Nội',
    CURRENT_DATE + INTERVAL '18 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_transglobal@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch nghiệm thu kỹ thuật bảo dưỡng đại tu động cơ phản lực Boeing 787');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn chuyên gia Cảng vụ Rotterdam (Hà Lan) khảo sát luồng tàu Cảng Cái Mép', 'Đi cano dọc luồng hàng hải Vũng Tàu - Thị Vải, hỗ trợ thảo luận kỹ thuật về độ sâu mớn nước, quy hoạch bến sà lan trung chuyển và ứng dụng hệ thống số hóa cảng thông minh TOS.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Anh', 'Tiếng Việt', 'range', 3800000, 6200000,
    '2026-11-03', '07:30', '16:30', 'Cảng Quốc tế Gemalink, Cái Mép, Thị xã Phú Mỹ, Bà Rịa - Vũng Tàu',
    CURRENT_DATE + INTERVAL '10 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_transglobal@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn chuyên gia Cảng vụ Rotterdam (Hà Lan) khảo sát luồng tàu Cảng Cái Mép');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Đàm phán hợp đồng thuê tàu định hạn vận tải hàng container tuyến quốc tế', 'Họp thương thảo điều khoản giá cước thuê tàu Charterparty, phụ phí nhiên liệu BAF và mức phạt bốc dỡ chậm Demurrage với đại diện hãng tàu container COSCO Trung Quốc.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Trung', 'Tiếng Việt', 'range', 2500000, 4200000,
    '2026-10-29', '09:00', '16:30', 'Tòa nhà TD Plaza, Ngô Quyền, Hải Phòng',
    CURRENT_DATE + INTERVAL '7 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_transglobal@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Đàm phán hợp đồng thuê tàu định hạn vận tải hàng container tuyến quốc tế');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội thảo Giải pháp Tự động hóa Kho bãi Thông minh Smart Warehouse & AGV Nhật Bản', 'Giới thiệu ứng dụng xe tự hành AGV, hệ thống băng tải tự động phân loại hàng hóa phân phối thương mại điện tử và giải pháp quản lý kho WMS từ tập đoàn Daifuku Nhật Bản.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 3500000, 5800000,
    '2026-11-17', '08:30', '17:00', 'Trung tâm Hội chợ & Triển lãm Sài Gòn (SECC), Quận 7, TP.HCM',
    CURRENT_DATE + INTERVAL '21 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_transglobal@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội thảo Giải pháp Tự động hóa Kho bãi Thông minh Smart Warehouse & AGV Nhật Bản');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Đào tạo quy trình bốc dỡ thiết bị siêu trường siêu trọng chuyên gia logistics Đức', 'Tập huấn cho đội ngũ cẩu bờ và điều hành logistics về tính toán tâm trọng lực, sơ đồ chằng buộc kiện hàng máy biến áp 300 tấn theo tiêu chuẩn an toàn hàng hải DNV-GL.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Đức', 'Tiếng Việt', 'range', 2800000, 4800000,
    '2026-11-07', '08:00', '16:30', 'Khu Cảng Nam Tiền Phong, KCN Bắc Tiền Phong, Quảng Ninh',
    CURRENT_DATE + INTERVAL '14 days', 'open', 'approved', false, NOW() - INTERVAL '5 days'
FROM "user" u WHERE u.email = 'hirer_transglobal@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Đào tạo quy trình bốc dỡ thiết bị siêu trường siêu trọng chuyên gia logistics Đức');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Đàm phán hợp đồng xuất khẩu sầu riêng Ri6 & thanh long ruột đỏ sang hệ thống siêu thị Trung Quốc', 'Làm việc với đoàn thương nhân tập đoàn bán lẻ nông sản Bắc Kinh về quy chuẩn mã số vùng trồng, kiểm dịch thực vật và kiểm soát dư lượng thuốc bảo vệ thực vật theo Lệnh 248.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Trung', 'Tiếng Việt', 'range', 2500000, 4200000,
    '2026-10-31', '08:30', '17:00', 'Văn phòng Hợp tác xã Nông sản Cái Bè, Tiền Giang',
    CURRENT_DATE + INTERVAL '8 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_vasepfood@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Đàm phán hợp đồng xuất khẩu sầu riêng Ri6 & thanh long ruột đỏ sang hệ thống siêu thị Trung Quốc');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Thẩm định quy trình nuôi tôm sinh thái đạt chứng nhận quốc tế ASC xuất khẩu sang Brazil', 'Đoàn đánh giá viên chứng nhận độc lập nói tiếng Bồ Đào Nha khảo sát mô hình nuôi tôm sú dưới tán rừng ngập mặn Cà Mau, kiểm tra sổ tay nhật ký sinh học và môi trường nước nuôi.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Bồ Đào Nha', 'Tiếng Việt', 'range', 3500000, 6000000,
    '2026-11-08', '07:30', '16:30', 'Vùng nuôi tôm sinh thái xã Đất Mũi, Ngọc Hiển, Cà Mau',
    CURRENT_DATE + INTERVAL '14 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_vasepfood@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Thẩm định quy trình nuôi tôm sinh thái đạt chứng nhận quốc tế ASC xuất khẩu sang Brazil');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch gian hàng Hội chợ Triển lãm Quốc tế Chuyên ngành Thực phẩm Vietfood & Beverage', 'Đón tiếp các nhà nhập khẩu quốc tế, giới thiệu mẫu sản phẩm cà phê Robusta đặc sản và hạt điều chế biến sâu, hỗ trợ chốt đơn hàng và lưu giữ danh thiếp đối tác giao thương.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Anh', 'Tiếng Việt', 'range', 2200000, 3800000,
    '2026-11-12', '08:30', '17:30', 'Trung tâm Hội chợ và Triển lãm Sài Gòn (SECC), Quận 7, TP.HCM',
    CURRENT_DATE + INTERVAL '16 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_vasepfood@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch gian hàng Hội chợ Triển lãm Quốc tế Chuyên ngành Thực phẩm Vietfood & Beverage');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Khảo sát dây chuyền chế biến sữa tươi tiệt trùng từ tập đoàn thực phẩm Thái Lan', 'Đoàn kỹ sư tập đoàn sữa Charoen Pokphand (Thái Lan) tham quan trang trại bò sữa hữu cơ và hệ thống vắt sữa tự động khép kín để hợp tác nhượng quyền sản phẩm tiệt trùng.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Thái', 'Tiếng Việt', 'range', 2000000, 3500000,
    '2026-11-05', '08:00', '16:30', 'Cụm Trang trại Bò sữa Hữu cơ, Nghĩa Đàn, Nghệ An',
    CURRENT_DATE + INTERVAL '12 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_vasepfood@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Khảo sát dây chuyền chế biến sữa tươi tiệt trùng từ tập đoàn thực phẩm Thái Lan');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Chuyển giao công nghệ canh tác rau củ quả trong nhà kính thủy canh thông minh từ Nhật Bản', 'Chuyên gia nông nghiệp hữu cơ tỉnh Nagano (Nhật Bản) hướng dẫn kỹ thuật pha chế dung dịch dinh dưỡng hữu cơ và tự động hóa hệ thống tưới nhỏ giọt kiểm soát qua smartphone.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 2800000, 4800000,
    '2026-11-15', '08:00', '16:30', 'Khu Nông nghiệp Công nghệ cao Đơn Dương, TP. Đà Lạt, Lâm Đồng',
    CURRENT_DATE + INTERVAL '19 days', 'open', 'approved', false, NOW() - INTERVAL '5 days'
FROM "user" u WHERE u.email = 'hirer_vasepfood@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Chuyển giao công nghệ canh tác rau củ quả trong nhà kính thủy canh thông minh từ Nhật Bản');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch Ngày hội Triển lãm Giáo dục & Học bổng Vương quốc Anh (Study in UK)', 'Hỗ trợ đại diện tuyển sinh của 15 trường đại học nhóm Russell Group (Oxford, UCL, Warwick) tư vấn ngành học, yêu cầu IELTS và điều kiện nộp hồ sơ xin học bổng toàn phần cho học sinh Việt Nam.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Anh', 'Tiếng Việt', 'range', 2500000, 4500000,
    '2026-11-01', '08:30', '17:00', 'Khách sạn Daewoo Hanoi, Ba Đình, Hà Nội',
    CURRENT_DATE + INTERVAL '9 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_edu_intl@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch Ngày hội Triển lãm Giáo dục & Học bổng Vương quốc Anh (Study in UK)');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội thảo Liên kết Đào tạo Thạc sĩ Quản trị Đổi mới Sáng tạo Đại học Tokyo (UTokyo)', 'Tọa đàm chuyên đề và ký kết biên bản ghi nhớ (MOU) chương trình đào tạo thạc sĩ 1+1 giữa Viện Sau Đại học UTokyo và trường đại học thành viên ĐHQG TP.HCM. Cần thông dịch viên dịch trôi chảy, học thuật cao.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 3500000, 6000000,
    '2026-11-11', '08:30', '16:30', 'Trường Đại học Bách Khoa ĐHQG-HCM, Quận 10, TP.HCM',
    CURRENT_DATE + INTERVAL '15 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_edu_intl@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội thảo Liên kết Đào tạo Thạc sĩ Quản trị Đổi mới Sáng tạo Đại học Tokyo (UTokyo)');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phỏng vấn trực tuyến 1 giờ xét duyệt học bổng chính phủ Pháp Eiffel Excellence', 'Phiên dịch viên hỗ trợ ứng viên Việt Nam trong buổi phỏng vấn trực tuyến với hội đồng giáo sư chuyên ngành kinh tế học phát triển tại Paris. Đòi hỏi tiếng Pháp học thuật chuẩn xác, lưu loát.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Pháp', 'Tiếng Việt', 'fixed', 400000, NULL,
    '2026-10-25', '19:00', '20:00', 'Trực tuyến qua Zoom Meeting',
    CURRENT_DATE + INTERVAL '5 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_edu_intl@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phỏng vấn trực tuyến 1 giờ xét duyệt học bổng chính phủ Pháp Eiffel Excellence');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Khóa tập huấn phương pháp sư phạm mầm non quốc tế Reggio Emilia cho giáo viên', 'Chuyên gia giáo dục sớm từ Ý giảng dạy bằng tiếng Anh cho 50 hiệu trưởng và giáo viên trường mầm non song ngữ. Nội dung về giáo dục cảm xúc, không gian học tập mở và phát triển tư duy sáng tạo của trẻ nhỏ.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Anh', 'Tiếng Việt', 'range', 2200000, 3800000,
    '2026-11-06', '08:00', '16:30', 'Trường Quốc tế Song ngữ Song Ngữ Đà Nẵng, Ngũ Hành Sơn, Đà Nẵng',
    CURRENT_DATE + INTERVAL '12 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_edu_intl@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Khóa tập huấn phương pháp sư phạm mầm non quốc tế Reggio Emilia cho giáo viên');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tọa đàm Hợp tác Nghiên cứu Khoa học Biển & Hải dương học cùng Viện sĩ Viện Hàn lâm Nga', 'Trao đổi kết quả chuyến khảo sát thực địa hải văn học tại vùng biển sâu Nam Trung Bộ giữa Viện Hải dương học Nha Trang và các nhà khoa học Viện Hàn lâm Khoa học Nga (RAS).', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Nga', 'Tiếng Việt', 'range', 3200000, 5200000,
    '2026-11-19', '08:30', '16:30', 'Viện Hải dương học Nha Trang, Trần Phú, Cầu Đá, Nha Trang',
    CURRENT_DATE + INTERVAL '21 days', 'open', 'approved', false, NOW() - INTERVAL '6 days'
FROM "user" u WHERE u.email = 'hirer_edu_intl@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tọa đàm Hợp tác Nghiên cứu Khoa học Biển & Hải dương học cùng Viện sĩ Viện Hàn lâm Nga');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch thử nghiệm va chạm & khí động học xe điện thông minh cùng kỹ sư Đức', 'Làm việc tại trung tâm thử nghiệm an toàn xe hơi cùng chuyên gia hãng kiểm định TUV SUD (Đức). Kiểm tra độ biến dạng khung gầm nhôm hợp kim, độ nhạy cảm biến túi khí và phân tích dữ liệu hộp đen.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Đức', 'Tiếng Việt', 'range', 4500000, 7500000,
    '2026-11-14', '08:00', '17:00', 'Tổ hợp Sản xuất Ô tô & Xe điện, Cát Hải, Hải Phòng',
    CURRENT_DATE + INTERVAL '18 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_apexmanuf@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch thử nghiệm va chạm & khí động học xe điện thông minh cùng kỹ sư Đức');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Chuyển giao công nghệ trạm sạc xe điện siêu nhanh 360kW từ đối tác Trung Quốc', 'Kỹ sư chuyên môn của hãng sản xuất trạm sạc hàng đầu Thâm Quyến đào tạo quy trình đấu nối lưới điện trung thế, giao thức truyền thông sạc CCS2 và giải pháp tản nhiệt chất lỏng cho trụ sạc.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Trung', 'Tiếng Việt', 'range', 2500000, 4200000,
    '2026-10-31', '08:30', '16:30', 'Trung tâm Đào tạo Kỹ thuật Xe điện, Long Biên, Hà Nội',
    CURRENT_DATE + INTERVAL '9 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_apexmanuf@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Chuyển giao công nghệ trạm sạc xe điện siêu nhanh 360kW từ đối tác Trung Quốc');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Đàm phán chuỗi cung ứng linh kiện hộp điều khiển động cơ ECU với tập đoàn Denso Nhật', 'Họp đàm phán hợp đồng cung ứng phụ tùng gốc OEM dài hạn, kiểm toán quy trình kiểm soát tỷ lệ lỗi PPM và thống nhất kế hoạch dự phòng kho đệm linh kiện.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 3500000, 5800000,
    '2026-11-09', '09:00', '17:00', 'KCN Bình Xuyên, Huyện Bình Xuyên, Vĩnh Phúc',
    CURRENT_DATE + INTERVAL '15 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_apexmanuf@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Đàm phán chuỗi cung ứng linh kiện hộp điều khiển động cơ ECU với tập đoàn Denso Nhật');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng kỹ sư Hàn Quốc kiểm thử hệ thống pin Lithium Iron Phosphate (LFP) trong môi trường khắc nghiệt', 'Đoàn kỹ sư pin năng lượng LG Energy Solution kiểm tra chu kỳ nạp xả, khả năng chống cháy nổ IP67 và hệ thống quản lý pin BMS dưới điều kiện nhiệt ẩm cao tại miền Trung.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Hàn', 'Tiếng Việt', 'range', 3500000, 5800000,
    '2026-11-04', '07:30', '16:30', 'Khu kinh tế Vũng Áng, Thị xã Kỳ Anh, Hà Tĩnh',
    CURRENT_DATE + INTERVAL '11 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_apexmanuf@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng kỹ sư Hàn Quốc kiểm thử hệ thống pin Lithium Iron Phosphate (LFP) trong môi trường khắc nghiệt');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội thảo Tiêu chuẩn An toàn Ô tô Quốc tế & Đổi mới Công nghệ Tự hành Euro NCAP 2026', 'Phiên dịch chuyên đề về hệ thống hỗ trợ người lái nâng cao ADAS cấp độ 3, phanh khẩn cấp tự động và chia sẻ hạ tầng thử nghiệm phương tiện kết nối thông minh V2X.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Anh', 'Tiếng Việt', 'range', 3000000, 5200000,
    '2026-11-20', '08:30', '17:00', 'Khách sạn Sheraton Saigon Hotel & Towers, Đồng Khởi, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '22 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_apexmanuf@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội thảo Tiêu chuẩn An toàn Ô tô Quốc tế & Đổi mới Công nghệ Tự hành Euro NCAP 2026');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Đàm phán mở rộng chuỗi đại siêu thị bán lẻ Thái Lan Central Retail tại Việt Nam', 'Làm việc giữa ban phát triển mặt bằng tập đoàn bán lẻ Thái Lan và các chủ đầu tư trung tâm thương mại tại các thành phố vệ tinh. Thảo luận chi tiết về diện tích sàn GLM, tỷ lệ chia sẻ doanh thu và thời hạn thuê 20 năm.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Thái', 'Tiếng Việt', 'range', 3000000, 5000000,
    '2026-11-05', '09:00', '17:00', 'Tòa nhà Bitexco Financial Tower, Quận 1, TP. Hồ Chí Minh',
    CURRENT_DATE + INTERVAL '12 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_vasepfood@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Đàm phán mở rộng chuỗi đại siêu thị bán lẻ Thái Lan Central Retail tại Việt Nam');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng Giám đốc Thu mua Toàn cầu Lotte Mart Hàn Quốc khảo sát vùng trồng nông sản', 'Đoàn chuyên gia thu mua sang Việt Nam tìm kiếm đối tác cung ứng ớt chỉ thiên, tỏi cô đơn và hạt tiêu xuất khẩu về hệ thống đại siêu thị Hàn Quốc. Đòi hỏi dịch chính xác và nhạy bén thương trường.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Hàn', 'Tiếng Việt', 'range', 2500000, 4200000,
    '2026-10-28', '08:00', '16:30', 'Vùng trồng nông sản huyện Hòa Vang, TP. Đà Nẵng',
    CURRENT_DATE + INTERVAL '7 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_vasepfood@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng Giám đốc Thu mua Toàn cầu Lotte Mart Hàn Quốc khảo sát vùng trồng nông sản');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch Livestream trực tiếp bán hàng nông sản xuất khẩu trên nền tảng Douyin', 'Cần 01 bạn phiên dịch viên tiếng Trung năng động, nói năng hoạt bát, phát âm chuẩn Bắc Kinh hỗ trợ KOL nổi tiếng Trung Quốc livestream bán hạt điều rang muối và mít sấy giòn trong 3 giờ.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Trung', 'Tiếng Việt', 'fixed', 1500000, NULL,
    '2026-10-26', '18:30', '21:30', 'Studio MCN Livestream, Cầu Giấy, Hà Nội',
    CURRENT_DATE + INTERVAL '5 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_vasepfood@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch Livestream trực tiếp bán hàng nông sản xuất khẩu trên nền tảng Douyin');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Khảo sát thị trường phân phối dược mỹ phẩm và chăm sóc cá nhân thương hiệu Tây Ban Nha', 'Tháp tùng giám đốc kinh doanh khu vực Đông Nam Á của tập đoàn mỹ phẩm Barcelona thăm chuỗi nhà thuốc Guardian, Pharmacity và các đại lý mỹ phẩm tại TP.HCM để phân tích hành vi người tiêu dùng.', 'Kinh doanh', 'interpretation_other', 'business',
    'Tiếng Tây Ban Nha', 'Tiếng Việt', 'range', 2200000, 3800000,
    '2026-11-03', '09:00', '17:00', 'Các trung tâm thương mại Vincom & Takashimaya, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '11 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_vasepfood@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Khảo sát thị trường phân phối dược mỹ phẩm và chăm sóc cá nhân thương hiệu Tây Ban Nha');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội nghị Khách hàng Thường niên Chuỗi Nhượng quyền F&B Quốc tế Hoa Kỳ', 'Phiên dịch hội thảo cho 120 đối tác nhận quyền thương hiệu thức ăn nhanh Mỹ. Nội dung cập nhật chiến lược tiếp thị đa kênh Omni-channel, kiểm soát chi phí nguyên liệu và tiêu chuẩn dịch vụ khách hàng.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Anh', 'Tiếng Việt', 'range', 3500000, 6000000,
    '2026-11-18', '08:30', '17:30', 'Khách sạn InterContinental Nha Trang, Trần Phú, Nha Trang',
    CURRENT_DATE + INTERVAL '20 days', 'open', 'approved', false, NOW() - INTERVAL '5 days'
FROM "user" u WHERE u.email = 'hirer_vasepfood@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội nghị Khách hàng Thường niên Chuỗi Nhượng quyền F&B Quốc tế Hoa Kỳ');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch hậu trường Tuần lễ Thời trang Quốc tế Vietnam International Fashion Week', 'Hỗ trợ các nhà thiết kế thời trang quốc tế và đạo diễn catwalk kiểm tra trang phục Fitting, khớp nhạc sàn diễn và hướng dẫn người mẫu quốc tế trong 2 ngày diễn ra tuần lễ thời trang.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Anh', 'Tiếng Việt', 'range', 4000000, 7000000,
    '2026-11-13', '13:00', '22:00', 'Nhà thi đấu Quân khu 7, Phú Nhuận, TP. Hồ Chí Minh',
    CURRENT_DATE + INTERVAL '17 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch hậu trường Tuần lễ Thời trang Quốc tế Vietnam International Fashion Week');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Workshop Đào tạo Kỹ thuật Điêu khắc Chân mày & Phun xăm Thẩm mỹ Viện trưởng Seoul', 'Master thẩm mỹ từ Gangnam (Hàn Quốc) trực tiếp thị phạm kỹ thuật đi sợi chân mày Hairstroke và phun môi tế bào gốc cho 30 học viên chuyên nghiệp tại Hà Nội.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Hàn', 'Tiếng Việt', 'range', 2500000, 4500000,
    '2026-11-02', '09:00', '17:00', 'Khách sạn Pan Pacific Hanoi, Ba Đình, Hà Nội',
    CURRENT_DATE + INTERVAL '10 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Workshop Đào tạo Kỹ thuật Điêu khắc Chân mày & Phun xăm Thẩm mỹ Viện trưởng Seoul');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng nhà thiết kế Haute Couture Pháp tuyển chọn chất liệu tơ lụa tự nhiên tại Lâm Đồng', 'Đồng hành cùng nhà thiết kế thời trang cao cấp Paris thăm các nhà máy ươm tơ dệt lụa Bảo Lộc, dịch thuật chuyên môn về độ bóng sợi tơ tằm, mật độ sợi dọc ngang và quy trình nhuộm màu tự nhiên.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Pháp', 'Tiếng Việt', 'range', 3200000, 5200000,
    '2026-11-08', '08:30', '17:00', 'Làng lụa tơ tằm Bảo Lộc, TP. Bảo Lộc, Lâm Đồng',
    CURRENT_DATE + INTERVAL '14 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng nhà thiết kế Haute Couture Pháp tuyển chọn chất liệu tơ lụa tự nhiên tại Lâm Đồng');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Giới thiệu ra mắt dòng sản phẩm tinh dầu hữu cơ thương hiệu Bồ Đào Nha tại TTTM', 'Phiên dịch giới thiệu thương hiệu và thông dịch giao lưu giữa chuyên gia liệu pháp hương thơm (Aromatherapy) đến từ Lisbon và khách hàng VIP tại gian hàng pop-up.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Bồ Đào Nha', 'Tiếng Việt', 'fixed', 1800000, NULL,
    '2026-10-31', '14:00', '20:00', 'TTTM Saigon Centre, Lê Lợi, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '8 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Giới thiệu ra mắt dòng sản phẩm tinh dầu hữu cơ thương hiệu Bồ Đào Nha tại TTTM');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội thảo Chuyên sâu về Công nghệ Chống lão hóa & Tế bào gốc Thực vật Nhật Bản', 'Bác sĩ da liễu và viện sĩ nghiên cứu hóa mỹ phẩm Tokyo trình bày cơ chế tái tạo collagen tầng sâu, kiểm nghiệm độ an toàn trên da nhạy cảm châu Á và chuyển giao công thức serum.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 3200000, 5500000,
    '2026-11-16', '08:30', '16:30', 'Khách sạn Grand Tourane Hotel Danang, Sơn Trà, Đà Nẵng',
    CURRENT_DATE + INTERVAL '20 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội thảo Chuyên sâu về Công nghệ Chống lão hóa & Tế bào gốc Thực vật Nhật Bản');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn làm phim tài liệu đài truyền hình NHK Nhật Bản tác nghiệp tại miền Trung', 'Hỗ trợ đạo diễn, quay phim đài truyền hình NHK quay phim tài liệu về nghề đánh bắt cá ngừ đại dương và cuộc sống ngư dân đảo Lý Sơn. Cần phiên dịch viên sức khỏe tốt, chịu khó và nhiệt tình.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 3800000, 6500000,
    '2026-11-06', '06:00', '18:00', 'Huyện đảo Lý Sơn, Quảng Ngãi và Cảng cá Sa Kỳ',
    CURRENT_DATE + INTERVAL '13 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn làm phim tài liệu đài truyền hình NHK Nhật Bản tác nghiệp tại miền Trung');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch hậu trường & điều phối kỹ thuật đêm nhạc giao lưu nghệ sĩ K-Pop tại Hà Nội', 'Dịch chỉ đạo từ đạo diễn sân khấu Hàn Quốc cho đội ngũ ánh sáng, âm thanh, visual màn hình LED và hỗ trợ quản lý nghệ sĩ trong suốt buổi diễn tập Rehearsal và đêm diễn chính thức.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Hàn', 'Tiếng Việt', 'range', 3200000, 5500000,
    '2026-11-21', '13:00', '23:00', 'Sân vận động Quốc gia Mỹ Đình, Nam Từ Liêm, Hà Nội',
    CURRENT_DATE + INTERVAL '23 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch hậu trường & điều phối kỹ thuật đêm nhạc giao lưu nghệ sĩ K-Pop tại Hà Nội');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Họp trực tuyến 1.5 giờ đàm phán bản quyền phát sóng phim điện ảnh với hãng phim Hollywood', 'Họp giữa nền tảng xem phim trực tuyến tại Việt Nam và đơn vị phân phối phim Los Angeles về điều khoản chia sẻ doanh thu VOD, cửa sổ phát hành bản quyền (Holdback Period) và phụ đề số.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Anh', 'Tiếng Việt', 'fixed', 850000, NULL,
    '2026-10-24', '09:00', '10:30', 'Trực tuyến qua Zoom Meeting',
    CURRENT_DATE + INTERVAL '4 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Họp trực tuyến 1.5 giờ đàm phán bản quyền phát sóng phim điện ảnh với hãng phim Hollywood');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch đạo diễn âm thanh Pháp cho dự án hợp tác nhạc kịch cổ điển tại Nhà hát Lớn', 'Làm việc cùng đạo diễn dàn dựng âm hưởng và nhạc trưởng người Pháp hướng dẫn dàn nhạc giao hưởng và các nghệ sĩ opera tập luyện tác phẩm Carmen.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Pháp', 'Tiếng Việt', 'range', 3000000, 5000000,
    '2026-11-10', '09:00', '17:00', 'Nhà hát Thành phố (Nhà hát Lớn), Công trường Lam Sơn, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '15 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch đạo diễn âm thanh Pháp cho dự án hợp tác nhạc kịch cổ điển tại Nhà hát Lớn');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn phóng viên báo chí quốc tế tác nghiệp tại Festival Nghệ thuật Truyền thống Huế', 'Đồng hành cùng các nhà báo tạp chí du lịch quốc tế chụp ảnh, phỏng vấn nghệ nhân nhã nhạc cung đình Huế, trải nghiệm làm nón bài thơ và ẩm thực chay cung đình.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Anh', 'Tiếng Việt', 'range', 2200000, 3800000,
    '2026-11-04', '08:00', '17:00', 'Quần thể Di tích Cố đô Huế, TP. Huế, Thừa Thiên Huế',
    CURRENT_DATE + INTERVAL '11 days', 'open', 'approved', false, NOW() - INTERVAL '5 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn phóng viên báo chí quốc tế tác nghiệp tại Festival Nghệ thuật Truyền thống Huế');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch sân khấu Giải đấu Thể thao Điện tử Vô địch Đông Nam Á Mobile Legends SEA Cup', 'Dịch trực tiếp phỏng vấn tuyển thủ sau trận đấu (Post-match Interview) trên sân khấu chính trước hàng nghìn khán giả và hàng trăm nghìn người theo dõi trực tuyến. Yêu cầu phản xạ cực nhanh, am hiểu thuật ngữ gaming.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Anh', 'Tiếng Việt', 'range', 3800000, 6500000,
    '2026-11-15', '12:00', '21:30', 'Nhà thi đấu Thể dục Thể thao Phú Thọ, Quận 11, TP.HCM',
    CURRENT_DATE + INTERVAL '18 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch sân khấu Giải đấu Thể thao Điện tử Vô địch Đông Nam Á Mobile Legends SEA Cup');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Họp chiến thuật & huấn luyện thể lực cùng Huấn luyện viên trưởng người Hàn Quốc', 'Dịch nối tiếp trong các buổi họp phân tích video đối thủ, giao bài tập thể lực chuyên biệt và truyền tải chỉ đạo trên sân tập cho câu lạc bộ bóng đá chuyên nghiệp V-League.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Hàn', 'Tiếng Việt', 'range', 2800000, 4800000,
    '2026-10-30', '08:00', '16:30', 'Trung tâm Đào tạo Bóng đá Trẻ, TP. Bà Rịa, Bà Rịa - Vũng Tàu',
    CURRENT_DATE + INTERVAL '7 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Họp chiến thuật & huấn luyện thể lực cùng Huấn luyện viên trưởng người Hàn Quốc');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch trọng tài quốc tế giải quần vợt nhà nghề ATP Challenger Tour Đà Nẵng', 'Hỗ trợ giám sát trận đấu, ban trọng tài quốc tế ATP và các tay vợt hàng đầu châu Á trong công tác tổ chức, xử lý khiếu nại luật thi đấu và phỏng vấn báo chí.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Anh', 'Tiếng Việt', 'range', 2800000, 4800000,
    '2026-11-09', '08:30', '17:30', 'Cụm Sân Quần vợt Làng Thể thao Tuyên Sơn, Hải Châu, Đà Nẵng',
    CURRENT_DATE + INTERVAL '15 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch trọng tài quốc tế giải quần vợt nhà nghề ATP Challenger Tour Đà Nẵng');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn võ sĩ Muay Thái giao hữu tranh đai vô địch quốc tế tại TP.HCM', 'Hỗ trợ các võ sĩ và ban huấn luyện Thái Lan trong buổi cân ký chính thức (Official Weigh-in), họp phổ biến luật thi đấu của Ủy ban quyền Anh nhà nghề và lễ chào võ đài.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Thái', 'Tiếng Việt', 'range', 2000000, 3500000,
    '2026-11-03', '13:00', '21:00', 'Câu lạc bộ Thể thao Hồ Xuân Hương, Quận 3, TP.HCM',
    CURRENT_DATE + INTERVAL '10 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn võ sĩ Muay Thái giao hữu tranh đai vô địch quốc tế tại TP.HCM');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội thảo Dinh dưỡng Vận động & Phục hồi Chấn thương Thể thao chuyên gia Đức', 'Bác sĩ thể thao từ Munich chia sẻ về ứng dụng liệu pháp lạnh Cryotherapy, phương pháp giãn cơ mạc sâu và chế độ bổ sung điện giải chuyên sâu cho vận động viên đỉnh cao.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Đức', 'Tiếng Việt', 'range', 2800000, 4500000,
    '2026-11-18', '08:30', '16:30', 'Bệnh viện Thể thao Việt Nam, Mỹ Đình, Nam Từ Liêm, Hà Nội',
    CURRENT_DATE + INTERVAL '21 days', 'open', 'approved', false, NOW() - INTERVAL '5 days'
FROM "user" u WHERE u.email = 'hirer_saigontour@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội thảo Dinh dưỡng Vận động & Phục hồi Chấn thương Thể thao chuyên gia Đức');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Triển lãm Nghệ thuật Gốm sứ Truyền thống Giao lưu Văn hóa Nhật Bản - Việt Nam', 'Thông dịch lễ khai mạc và buổi trò chuyện chuyên đề giữa nghệ nhân gốm sứ Bizen cổ đại của Nhật và các nghệ nhân làng gốm Bát Tràng về kỹ thuật nung củi và men tro tự nhiên.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 2500000, 4200000,
    '2026-11-05', '09:00', '17:00', 'Trung tâm Giao lưu Văn hóa Nhật Bản tại Việt Nam, Quang Trung, Hà Nội',
    CURRENT_DATE + INTERVAL '12 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Triển lãm Nghệ thuật Gốm sứ Truyền thống Giao lưu Văn hóa Nhật Bản - Việt Nam');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn chuyên gia di sản UNESCO khảo sát thực địa bảo tồn Điện Kiến Trung - Huế', 'Làm việc cùng đoàn kiến trúc sư di sản UNESCO kiểm tra kỹ thuật khảm sành sứ, kỹ thuật phục hồi tranh tường sơn dầu và quy chuẩn chống ẩm dột cho công trình hoàng gia.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Anh', 'Tiếng Việt', 'range', 3800000, 6200000,
    '2026-11-12', '08:00', '16:30', 'Khu di tích Tử Cấm Thành Huế, TP. Huế, Thừa Thiên Huế',
    CURRENT_DATE + INTERVAL '16 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn chuyên gia di sản UNESCO khảo sát thực địa bảo tồn Điện Kiến Trung - Huế');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tọa đàm Văn hóa Ẩm thực & Di sản Rượu vang Tây Ban Nha vùng Rioja', 'Chuyên gia thử nếm rượu vang (Sommelier) giới thiệu phương pháp ủ thùng gỗ sồi, lịch sử làm vang hàng trăm năm và hướng dẫn thực khách kết hợp vang với đặc sản ẩm thực Việt.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Tây Ban Nha', 'Tiếng Việt', 'range', 2200000, 3800000,
    '2026-10-30', '16:00', '21:00', 'Khách sạn Caravelle Saigon, Quảng trường Lam Sơn, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '8 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tọa đàm Văn hóa Ẩm thực & Di sản Rượu vang Tây Ban Nha vùng Rioja');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội thảo Khoa học Phục chế Sách Cổ & Bản khắc Hán Nôm Viện Viễn Đông Bác Cổ (EFEO)', 'Các nhà lưu trữ học Pháp chia sẻ kỹ thuật khử axit giấy dó, kỹ thuật đóng gáy chỉ truyền thống và số hóa 3D các văn bia cổ quý hiếm thời Lê - Nguyễn.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Pháp', 'Tiếng Việt', 'range', 3500000, 5800000,
    '2026-11-20', '08:30', '17:00', 'Thư viện Quốc gia Việt Nam, Tràng Thi, Hoàn Kiếm, Hà Nội',
    CURRENT_DATE + INTERVAL '22 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội thảo Khoa học Phục chế Sách Cổ & Bản khắc Hán Nôm Viện Viễn Đông Bác Cổ (EFEO)');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Thuyết minh trưng bày hiện vật khảo cổ học hợp tác Bảo tàng Quốc gia Hermitage (Nga)', 'Phiên dịch viên hỗ trợ các nhà nghiên cứu Nga trong lễ mở màn triển lãm cổ vật văn hóa Đông Sơn và trao đổi học thuật về niên đại phóng xạ carbon C14 của các di vật đồng thau.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Nga', 'Tiếng Việt', 'range', 2800000, 4800000,
    '2026-11-14', '09:00', '16:30', 'Bảo tàng Lịch sử TP. Hồ Chí Minh, Nguyễn Bỉnh Khiêm, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '17 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Thuyết minh trưng bày hiện vật khảo cổ học hợp tác Bảo tàng Quốc gia Hermitage (Nga)');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Đàm phán hợp đồng chuyển nhượng tín chỉ carbon rừng theo tiêu chuẩn quốc tế Verra (VCS)', 'Làm việc giữa ban quản lý dự án bảo vệ rừng tự nhiên và quỹ đầu tư môi trường quốc tế về định giá tín chỉ carbon, cơ chế thẩm định MRV và chia sẻ lợi ích với cộng đồng cư dân bản địa.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Anh', 'Tiếng Việt', 'range', 4500000, 7500000,
    '2026-11-06', '08:30', '17:00', 'Văn phòng Vườn Quốc gia Phong Nha - Kẻ Bàng, Bố Trạch, Quảng Bình',
    CURRENT_DATE + INTERVAL '13 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_greenpower@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Đàm phán hợp đồng chuyển nhượng tín chỉ carbon rừng theo tiêu chuẩn quốc tế Verra (VCS)');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Chuyển giao công nghệ xử lý rác thải sinh hoạt phát điện Waste-to-Energy Thụy Điển', 'Chuyên gia công nghệ môi trường Bắc Âu hướng dẫn quy trình kiểm soát khí thải Dioxin/Furan theo tiêu chuẩn EU 2010 và giải pháp tận dụng xỉ đáy lò làm gạch không nung.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Anh', 'Tiếng Việt', 'range', 3800000, 6200000,
    '2026-11-13', '08:00', '16:30', 'Nhà máy Điện rác Cần Thơ, Huyện Thới Lai, Cần Thơ',
    CURRENT_DATE + INTERVAL '18 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_greenpower@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Chuyển giao công nghệ xử lý rác thải sinh hoạt phát điện Waste-to-Energy Thụy Điển');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Thẩm tra báo cáo kiểm kê khí nhà kính Scope 1-2-3 cho tập đoàn sản xuất Nhật Bản', 'Làm việc cùng đoàn chuyên gia kiểm toán carbon độc lập từ Tokyo soát xét số liệu tiêu thụ điện, khí gas và phát thải gián tiếp từ chuỗi cung ứng theo chuẩn mực quốc tế ISO 14064.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Nhật', 'Tiếng Việt', 'range', 3200000, 5500000,
    '2026-11-03', '08:30', '17:00', 'KCN Sóng Thần 3, TP. Thủ Dầu Một, Bình Dương',
    CURRENT_DATE + INTERVAL '10 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_greenpower@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Thẩm tra báo cáo kiểm kê khí nhà kính Scope 1-2-3 cho tập đoàn sản xuất Nhật Bản');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Khảo sát công nghệ xử lý nước thải công nghiệp tuần hoàn không xả thải ZLD từ CHLB Đức', 'Kỹ sư xử lý nước thải công nghiệp Đức khảo sát trạm xử lý nước thải tập trung KCN dệt nhuộm, kiểm tra màng lọc thẩm thấu ngược RO áp lực cao và thiết bị kết tinh muối bay hơi MVR.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Đức', 'Tiếng Việt', 'range', 3200000, 5200000,
    '2026-11-09', '08:30', '16:30', 'KCN Yên Phong, Huyện Yên Phong, Bắc Ninh',
    CURRENT_DATE + INTERVAL '15 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_greenpower@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Khảo sát công nghệ xử lý nước thải công nghiệp tuần hoàn không xả thải ZLD từ CHLB Đức');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Hội thảo Giải pháp Bao bì Tự hủy Sinh học & Tái chế Nhựa cho Chuỗi Cung ứng Xanh', 'Các nhà sản xuất bao bì thân thiện môi trường hàng đầu châu Á và đại diện các tập đoàn bán lẻ đa quốc gia thảo luận về lộ trình loại bỏ nhựa sử dụng một lần và áp dụng trách nhiệm mở rộng của nhà sản xuất (EPR).', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Anh', 'Tiếng Việt', 'range', 2800000, 4800000,
    '2026-11-17', '08:30', '17:00', 'Khách sạn New World Saigon, Lê Lai, Quận 1, TP.HCM',
    CURRENT_DATE + INTERVAL '21 days', 'open', 'approved', false, NOW() - INTERVAL '5 days'
FROM "user" u WHERE u.email = 'hirer_greenpower@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Hội thảo Giải pháp Bao bì Tự hủy Sinh học & Tái chế Nhựa cho Chuỗi Cung ứng Xanh');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch Hội nghị Tổng kết Dự án Sinh kế Thích ứng Biến đổi Khí hậu Đồng bằng Sông Cửu Long', 'Hội thảo tổng kết dự án 5 năm do Tổ chức Phát triển Quốc tế tài trợ. Trình bày các mô hình sinh kế thành công: nuôi tôm rừng, trồng lúa chịu mặn và thành lập hợp tác xã thích ứng nước ngọt.', 'Hội nghị', 'interpretation_other', 'conference',
    'Tiếng Anh', 'Tiếng Việt', 'range', 3200000, 5200000,
    '2026-11-10', '08:00', '17:00', 'Trung tâm Hội nghị Khách sạn Hàm Luông, TP. Bến Tre, Bến Tre',
    CURRENT_DATE + INTERVAL '16 days', 'open', 'approved', false, NOW() - INTERVAL '1 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch Hội nghị Tổng kết Dự án Sinh kế Thích ứng Biến đổi Khí hậu Đồng bằng Sông Cửu Long');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tháp tùng đoàn công tác UNICEF khảo sát chương trình cải thiện dinh dưỡng học đường vùng cao', 'Đến các điểm trường mầm non và tiểu học vùng đồng bào dân tộc thiểu số tại Điện Biên. Dịch các buổi phỏng vấn giáo viên, phụ huynh và kiểm tra điều kiện nước sạch, bếp ăn bán trú.', 'Tháp tùng', 'interpretation_other', 'escort',
    'Tiếng Anh', 'Tiếng Việt', 'range', 3800000, 6500000,
    '2026-11-04', '07:30', '17:00', 'Các xã vùng cao huyện Mường Chà và Nậm Pồ, Tỉnh Điện Biên',
    CURRENT_DATE + INTERVAL '11 days', 'open', 'approved', false, NOW() - INTERVAL '2 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tháp tùng đoàn công tác UNICEF khảo sát chương trình cải thiện dinh dưỡng học đường vùng cao');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Phiên dịch phỏng vấn nhóm cộng đồng dự án bảo tồn động vật hoang dã của WWF', 'Làm việc cùng các chuyên gia bảo tồn sinh học quốc tế phỏng vấn các đội tuần tra rừng cộng đồng và cán bộ kiểm lâm về công tác tháo gỡ bẫy thú và phục hồi rừng hành lang đa dạng sinh học.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Anh', 'Tiếng Việt', 'range', 2500000, 4200000,
    '2026-10-31', '08:30', '16:30', 'Khu Bảo tồn Thiên nhiên Sông Thanh, Nam Giang, Quảng Nam',
    CURRENT_DATE + INTERVAL '8 days', 'open', 'approved', false, NOW() - INTERVAL '3 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Phiên dịch phỏng vấn nhóm cộng đồng dự án bảo tồn động vật hoang dã của WWF');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Họp điều phối cứu trợ khẩn cấp thiên tai bão lũ cùng phái đoàn Chữ Thập Đỏ Pháp', 'Phiên dịch khẩn các cuộc họp giao ban giữa đoàn cứu trợ nhân đạo Hội Chữ Thập Đỏ Pháp và Ban Chỉ huy Phòng chống Thiên tai & Tìm kiếm Cứu nạn địa phương để phân phối gói hàng cứu trợ.', 'Đàm phán', 'interpretation_other', 'meeting',
    'Tiếng Pháp', 'Tiếng Việt', 'range', 2800000, 4800000,
    '2026-10-28', '08:00', '17:00', 'UBND Huyện Cẩm Xuyên, Tỉnh Hà Tĩnh',
    CURRENT_DATE + INTERVAL '6 days', 'open', 'approved', false, NOW() - INTERVAL '0 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Họp điều phối cứu trợ khẩn cấp thiên tai bão lũ cùng phái đoàn Chữ Thập Đỏ Pháp');


INSERT INTO job (
    hirer_id, title, description, category, category_group, service_type,
    source_lang, target_lang, budget_type, budget_min, budget_max,
    event_date, event_time_start, event_time_end, event_location,
    deadline, status, moderation_status, is_flagged, created_at
)
SELECT
    u.id, 'Tập huấn nâng cao năng lực phụ nữ khởi nghiệp nông thôn tiểu vùng sông Mê Kông', 'Dịch cho chuyên gia đào tạo phát triển kinh tế cộng đồng Thái Lan giảng dạy phương pháp lập kế hoạch tài chính hộ gia đình, tiếp thị sản phẩm thủ công dệt chiếu và thương mại du lịch cộng đồng.', 'Sự kiện', 'interpretation_other', 'event',
    'Tiếng Thái', 'Tiếng Việt', 'range', 2200000, 3800000,
    '2026-11-07', '08:30', '16:30', 'Hội Liên hiệp Phụ nữ Huyện Châu Phú, Tỉnh An Giang',
    CURRENT_DATE + INTERVAL '13 days', 'open', 'approved', false, NOW() - INTERVAL '4 days'
FROM "user" u WHERE u.email = 'hirer_diplomacy@viettranslate.demo'
AND NOT EXISTS (SELECT 1 FROM job WHERE title = 'Tập huấn nâng cao năng lực phụ nữ khởi nghiệp nông thôn tiểu vùng sông Mê Kông');


COMMIT;
