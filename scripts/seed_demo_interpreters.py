#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed script to generate and deploy exactly 50 unique demo interpreter profiles
for VietTranslate.

Idempotent: Re-running this script updates existing demo profiles without creating duplicates.
Real accounts are never touched.

Strict 10 Languages:
1. Tiếng Anh (10 profiles)
2. Tiếng Trung (8 profiles)
3. Tiếng Nhật (8 profiles)
4. Tiếng Hàn (6 profiles)
5. Tiếng Pháp (4 profiles)
6. Tiếng Đức (4 profiles)
7. Tiếng Nga (3 profiles)
8. Tiếng Tây Ban Nha (3 profiles)
9. Tiếng Thái (2 profiles)
10. Tiếng Bồ Đào Nha (2 profiles)
Total: Exactly 50 profiles.
"""

import sys
import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import (
    User,
    TranslatorProfile,
    Service,
    InterpreterService,
    InterpreterPreference,
    TranslatorPreference,
    TranslatorVerification,
)

TARGET_DEMO_COUNT = 50

# ─── 50 DIVERSE DEMO PROFILES SPECIFICATION (STRICT 10 LANGUAGES) ─────────────
LANG_DATA_50 = [
    # 0-9: Vietnamese - English (10)
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh, Tiếng Pháp", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt, Tiếng Đức", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt", "nat": "Tiếng Việt"},

    # 10-17: Vietnamese - Chinese (8)
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Trung"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Việt"},

    # 18-25: Vietnamese - Japanese (8)
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Nhật"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Nhật"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Việt"},

    # 26-31: Vietnamese - Korean (6)
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn", "nat": "Tiếng Việt"},
    {"src": "Tiếng Hàn", "tgt": "Tiếng Việt", "pair": "Tiếng Hàn - Tiếng Việt", "langs": "Tiếng Hàn, Tiếng Việt", "nat": "Tiếng Hàn"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Hàn", "tgt": "Tiếng Việt", "pair": "Tiếng Hàn - Tiếng Việt", "langs": "Tiếng Hàn, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn", "nat": "Tiếng Việt"},
    {"src": "Tiếng Hàn", "tgt": "Tiếng Việt", "pair": "Tiếng Hàn - Tiếng Việt", "langs": "Tiếng Hàn, Tiếng Việt", "nat": "Tiếng Hàn"},

    # 32-35: Vietnamese - French (4)
    {"src": "Tiếng Việt", "tgt": "Tiếng Pháp", "pair": "Tiếng Việt - Tiếng Pháp", "langs": "Tiếng Việt, Tiếng Pháp", "nat": "Tiếng Việt"},
    {"src": "Tiếng Pháp", "tgt": "Tiếng Việt", "pair": "Tiếng Pháp - Tiếng Việt", "langs": "Tiếng Pháp, Tiếng Việt", "nat": "Tiếng Pháp"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Pháp", "pair": "Tiếng Việt - Tiếng Pháp", "langs": "Tiếng Việt, Tiếng Pháp, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Pháp", "tgt": "Tiếng Việt", "pair": "Tiếng Pháp - Tiếng Việt", "langs": "Tiếng Pháp, Tiếng Việt", "nat": "Tiếng Việt"},

    # 36-39: Vietnamese - German (4)
    {"src": "Tiếng Việt", "tgt": "Tiếng Đức", "pair": "Tiếng Việt - Tiếng Đức", "langs": "Tiếng Việt, Tiếng Đức", "nat": "Tiếng Việt"},
    {"src": "Tiếng Đức", "tgt": "Tiếng Việt", "pair": "Tiếng Đức - Tiếng Việt", "langs": "Tiếng Đức, Tiếng Việt", "nat": "Tiếng Đức"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Đức", "pair": "Tiếng Việt - Tiếng Đức", "langs": "Tiếng Việt, Tiếng Đức, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Đức", "tgt": "Tiếng Việt", "pair": "Tiếng Đức - Tiếng Việt", "langs": "Tiếng Đức, Tiếng Việt", "nat": "Tiếng Việt"},

    # 40-42: Vietnamese - Russian (3)
    {"src": "Tiếng Việt", "tgt": "Tiếng Nga", "pair": "Tiếng Việt - Tiếng Nga", "langs": "Tiếng Việt, Tiếng Nga", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nga", "tgt": "Tiếng Việt", "pair": "Tiếng Nga - Tiếng Việt", "langs": "Tiếng Nga, Tiếng Việt", "nat": "Tiếng Nga"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nga", "pair": "Tiếng Việt - Tiếng Nga", "langs": "Tiếng Việt, Tiếng Nga, Tiếng Anh", "nat": "Tiếng Việt"},

    # 43-45: Vietnamese - Spanish (3)
    {"src": "Tiếng Việt", "tgt": "Tiếng Tây Ban Nha", "pair": "Tiếng Việt - Tiếng Tây Ban Nha", "langs": "Tiếng Việt, Tiếng Tây Ban Nha", "nat": "Tiếng Việt"},
    {"src": "Tiếng Tây Ban Nha", "tgt": "Tiếng Việt", "pair": "Tiếng Tây Ban Nha - Tiếng Việt", "langs": "Tiếng Tây Ban Nha, Tiếng Việt", "nat": "Tiếng Tây Ban Nha"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Tây Ban Nha", "pair": "Tiếng Việt - Tiếng Tây Ban Nha", "langs": "Tiếng Việt, Tiếng Tây Ban Nha, Tiếng Anh", "nat": "Tiếng Việt"},

    # 46-47: Vietnamese - Thai (2)
    {"src": "Tiếng Việt", "tgt": "Tiếng Thái", "pair": "Tiếng Việt - Tiếng Thái", "langs": "Tiếng Việt, Tiếng Thái", "nat": "Tiếng Việt"},
    {"src": "Tiếng Thái", "tgt": "Tiếng Việt", "pair": "Tiếng Thái - Tiếng Việt", "langs": "Tiếng Thái, Tiếng Việt", "nat": "Tiếng Thái"},

    # 48-49: Vietnamese - Portuguese (2)
    {"src": "Tiếng Việt", "tgt": "Tiếng Bồ Đào Nha", "pair": "Tiếng Việt - Tiếng Bồ Đào Nha", "langs": "Tiếng Việt, Tiếng Bồ Đào Nha", "nat": "Tiếng Việt"},
    {"src": "Tiếng Bồ Đào Nha", "tgt": "Tiếng Việt", "pair": "Tiếng Bồ Đào Nha - Tiếng Việt", "langs": "Tiếng Bồ Đào Nha, Tiếng Việt", "nat": "Tiếng Bồ Đào Nha"},
]

# 12 Diverse Industry Specializations
INDUSTRIES = [
    "Đàm phán kinh doanh & Thương mại",
    "Pháp lý & Hợp đồng",
    "Y tế & Chăm sóc sức khỏe",
    "Du lịch & Khách sạn",
    "Sản xuất & Kỹ thuật công nghiệp",
    "Xây dựng & Bất động sản",
    "Công nghệ thông tin & Phần mềm",
    "Giáo dục & Đào tạo",
    "Xuất nhập khẩu & Logistics",
    "Tài chính & Ngân hàng",
    "Năng lượng & Dầu khí",
    "Hội nghị & Sự kiện quốc tế",
]

# Locations (City, Country, Service Areas, Work Modes)
LOCATIONS = [
    ("Hà Nội", "Việt Nam", "Hà Nội và các tỉnh phía Bắc", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)"),
    ("TP. Hồ Chí Minh", "Việt Nam", "TP. Hồ Chí Minh và Đông Nam Bộ", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)"),
    ("Đà Nẵng", "Việt Nam", "Đà Nẵng, Huế, Quảng Nam và miền Trung", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)"),
    ("Hải Phòng", "Việt Nam", "Hải Phòng, Quảng Ninh và vùng duyên hải", "Trực tiếp tại địa điểm (On-site)"),
    ("Cần Thơ", "Việt Nam", "Cần Thơ và các tỉnh Đồng bằng sông Cửu Long", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)"),
    ("Bình Dương", "Việt Nam", "Bình Dương, Đồng Nai và các khu công nghiệp", "Trực tiếp tại địa điểm (On-site)"),
    ("Bắc Ninh", "Việt Nam", "Bắc Ninh, Bắc Giang, Vĩnh Phúc (Cụm KCN)", "Trực tiếp tại địa điểm (On-site)"),
    ("Quảng Ninh", "Việt Nam", "Hạ Long, Cẩm Phả và các cửa khẩu phía Bắc", "Trực tiếp tại địa điểm (On-site)"),
    ("Đồng Nai", "Việt Nam", "Biên Hòa, Long Thành và vùng phụ cận", "Trực tiếp tại địa điểm (On-site)"),
    ("Vũng Tàu", "Việt Nam", "Bà Rịa - Vũng Tàu và các cảng biển quốc tế", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)"),
]

# 50 Distinct Vietnamese Names
NAMES_50 = [
    "Nguyễn Minh Tuấn", "Trần Thị Bích Ngọc", "Lê Hoàng Long", "Phạm Hải Đăng", "Hoàng Mai Phương",
    "Vũ Đình Trọng", "Đặng Thùy Dương", "Bùi Quốc Anh", "Đỗ Thu Trang", "Ngô Thành Nam",
    "Dương Cẩm Tú", "Lý Gia Bảo", "Phan Thanh Trúc", "Võ Hữu Phước", "Trịnh Bảo Ngọc",
    "Mai Anh Dũng", "Đoàn Mỹ Linh", "Lâm Quang Huy", "Lương Thục Quyên", "Chu Mạnh Cường",
    "Cao Thị Kim Oanh", "Tạ Nhật Minh", "Hà Quỳnh Nga", "Phùng Thế Vinh", "Tô Ánh Nguyệt",
    "Đinh Hữu Đạt", "Trương Thảo Nhi", "Nguyễn Tiến Phát", "Trần Mỹ Hạnh", "Lê Bảo Lâm",
    "Phạm Ngọc Trâm", "Hoàng Gia Khiêm", "Vũ Tuyết Mai", "Đặng Minh Quân", "Bùi Khánh Linh",
    "Đỗ Trọng Hiếu", "Hồ Thúy Kiều", "Ngô Đình Trí", "Dương Yến Trang", "Lý Văn Hậu",
    "Phan Thu Thảo", "Võ Tuấn Kiệt", "Trịnh Thùy Linh", "Mai Văn Thịnh", "Đoàn Phương Mai",
    "Lâm Bá Thông", "Lương Diệu Linh", "Chu Quốc Bảo", "Cao Minh Nhật", "Tạ Thanh Huyền"
]

# 10 Static Avatar assets in project
AVATAR_ASSETS = [
    "/static/avatars/avatar_dung.jpg",
    "/static/avatars/avatar_ha.jpg",
    "/static/avatars/avatar_bich.jpg",
    "/static/avatars/avatar_cuong.jpg",
    "/static/avatars/avatar_duc.jpg",
    "/static/avatars/avatar_huong.jpg",
    "/static/avatars/avatar_khoa.jpg",
    "/static/avatars/avatar_nam.jpg",
    "/static/avatars/avatar_huy.jpg",
    "/static/avatars/avatar_lananh.jpg",
]

UNIVERSITIES = [
    ("Đại học Ngoại ngữ - ĐHQGHN", "Ngôn ngữ học ứng dụng"),
    ("Đại học Ngoại thương (FTU)", "Tiếng Anh Thương mại"),
    ("Đại học Hà Nội (HANU)", "Biên phiên dịch Chuyên nghiệp"),
    ("Đại học KHXH&NV - ĐHQG TP.HCM", "Ngôn ngữ & Văn hóa Quốc tế"),
    ("Đại học Bách Khoa Hà Nội", "Kỹ thuật & Ngoại ngữ chuyên ngành"),
    ("Đại học Sư phạm TP.HCM", "Sư phạm & Dịch thuật Ngoại ngữ"),
    ("Đại học Kinh tế Quốc dân (NEU)", "Kinh tế đối ngoại & Ngoại ngữ"),
    ("Học viện Ngoại giao (DAV)", "Quan hệ Quốc tế & Ngoại giao"),
]

CERTIFICATES_MAP = {
    "Tiếng Anh": [("IELTS 8.5 Academic", 2022), ("IELTS 8.0 Academic", 2023), ("TOEIC 985/990", 2021), ("IELTS 7.5 Academic", 2023)],
    "Tiếng Trung": [("HSK 6 (285/300) & HSKK Cao cấp", 2022), ("HSK 6 (270/300)", 2023), ("HSK 5 (260/300)", 2021), ("HSK 6", 2024)],
    "Tiếng Nhật": [("JLPT N1 (172/180)", 2022), ("JLPT N1 (160/180)", 2023), ("JLPT N2 (165/180)", 2021), ("JLPT N1", 2024)],
    "Tiếng Hàn": [("TOPIK 6 (Cấp cao nhất)", 2022), ("TOPIK 6 (Điểm xuất sắc)", 2023), ("TOPIK 5 (220/300)", 2021), ("TOPIK 6", 2024)],
    "Tiếng Pháp": [("DALF C1", 2022), ("DELF B2", 2023), ("DALF C2", 2021), ("DALF C1", 2024)],
    "Tiếng Đức": [("Goethe-Zertifikat C1", 2022), ("TestDaF TDN 5", 2023), ("Goethe-Zertifikat B2", 2021), ("Goethe C1", 2024)],
    "Tiếng Nga": [("ТРКИ C1", 2022), ("ТРКИ B2", 2023), ("ТРКИ C2", 2020), ("ТРКИ C1", 2024)],
    "Tiếng Tây Ban Nha": [("DELE C1", 2022), ("DELE B2", 2023), ("DELE C2", 2021), ("DELE C1", 2024)],
    "Tiếng Thái": [("Chứng chỉ tiếng Thái Cấp cao - Chulalongkorn", 2022), ("Kiểm tra trực tiếp - Đạt chuẩn thương mại", 2023), ("Tiếng Thái Thương mại Nâng cao", 2021)],
    "Tiếng Bồ Đào Nha": [("CELPE-Bras Cấp Avançado", 2022), ("CELPE-Bras Intermediário Superior", 2023), ("CELPE-Bras Avançado", 2021)],
}

EMPLOYMENT_PREFS = [
    "Freelance / Làm tự do theo dự án",
    "Bán thời gian (Part-time)",
    "Hợp đồng ngắn hạn & Trung hạn",
    "Toàn thời gian (Full-time)",
    "Linh hoạt theo giờ / Theo ca",
]

AVAILABILITY_STATUSES = [
    "Sẵn sàng nhận việc",
    "Sẵn sàng nhận việc",
    "Sẵn sàng nhận việc",
    "Linh hoạt theo lịch hẹn",
    "Bận dự án ngắn hạn (Nhận việc từ tuần tới)",
]

INTERPRETING_TYPES_LIST = [
    "Phiên dịch tháp tùng (Escort), Phiên dịch hội thảo (Consecutive)",
    "Phiên dịch cabin đồng thời (Simultaneous), Phiên dịch đàm phán hợp đồng",
    "Phiên dịch tháp tùng công tác, Khảo sát hiện trường nhà máy",
    "Phiên dịch sự kiện triển lãm quốc tế, Giới thiệu sản phẩm",
    "Phiên dịch hội nghị trực tuyến (Remote / Zoom), Họp song phương",
]


def build_experience_tiers_50():
    """Tạo 50 mức kinh nghiệm, rating, số job và biểu phí đa dạng."""
    tiers = []

    # 10 Junior (1-2 năm)
    for i in range(10):
        y = 1 + (i % 2)
        jobs = 5 + (i * 3) % 10
        rev = int(jobs * 0.8)
        rating = round(4.3 + (i % 5) * 0.1, 1)
        h_rate = 300000 + (i % 4) * 50000
        d_rate = 2200000 + (i % 4) * 300000
        tiers.append({
            "years": y, "level": "Cử nhân",
            "title_pfx": "Phiên dịch viên triển vọng",
            "jobs": jobs, "rating": rating, "rev": rev,
            "h_rate": float(h_rate), "d_rate": float(d_rate),
            "p_basic": int(d_rate), "p_std": int(d_rate * 1.6), "p_prem": int(d_rate * 2.5),
        })

    # 18 Mid-level (3-5 năm)
    for i in range(18):
        y = 3 + (i % 3)
        jobs = 15 + (i * 2) % 20
        rev = int(jobs * 0.75)
        rating = round(4.5 + ((i * 3) % 4) * 0.1, 1)
        h_rate = 600000 + (i % 5) * 80000
        d_rate = 4200000 + (i % 5) * 400000
        level = "Thạc sĩ" if i % 3 == 0 else "Cử nhân"
        tiers.append({
            "years": y, "level": level,
            "title_pfx": "Phiên dịch viên chuyên nghiệp",
            "jobs": jobs, "rating": rating, "rev": rev,
            "h_rate": float(h_rate), "d_rate": float(d_rate),
            "p_basic": int(d_rate), "p_std": int(d_rate * 1.7), "p_prem": int(d_rate * 2.8),
        })

    # 16 Senior (6-10 năm)
    for i in range(16):
        y = 6 + (i % 5)
        jobs = 38 + (i * 3) % 35
        rev = int(jobs * 0.8)
        rating = round(4.7 + (i % 3) * 0.1, 1)
        h_rate = 1000000 + (i % 5) * 120000
        d_rate = 7500000 + (i % 5) * 600000
        level = "Thạc sĩ" if i % 2 == 0 else "Cử nhân"
        tiers.append({
            "years": y, "level": level,
            "title_pfx": "Chuyên gia phiên dịch cao cấp",
            "jobs": jobs, "rating": rating, "rev": rev,
            "h_rate": float(h_rate), "d_rate": float(d_rate),
            "p_basic": int(d_rate), "p_std": int(d_rate * 1.8), "p_prem": int(d_rate * 2.9),
        })

    # 6 Expert (11-16 năm)
    for i in range(6):
        y = 11 + (i * 2)
        jobs = 85 + (i * 7) % 35
        rev = int(jobs * 0.85)
        rating = 5.0 if i % 2 == 0 else 4.9
        h_rate = 1600000 + i * 200000
        d_rate = 12000000 + i * 1500000
        level = "Tiến sĩ" if i % 2 == 0 else "Thạc sĩ"
        tiers.append({
            "years": y, "level": level,
            "title_pfx": "Chuyên gia phiên dịch cabin kỳ cựu",
            "jobs": jobs, "rating": rating, "rev": rev,
            "h_rate": float(h_rate), "d_rate": float(d_rate),
            "p_basic": int(d_rate), "p_std": int(d_rate * 1.8), "p_prem": int(d_rate * 2.8),
        })

    return tiers

ALL_TIERS_50 = build_experience_tiers_50()


def generate_profile_data(idx):
    """Tạo dữ liệu chi tiết cho hồ sơ thứ idx (0 đến 49)."""
    lang_info = LANG_DATA_50[idx]
    ind_primary = INDUSTRIES[idx % len(INDUSTRIES)]
    ind_secondary = INDUSTRIES[(idx + 5) % len(INDUSTRIES)]
    loc_city, loc_country, loc_area, loc_mode = LOCATIONS[idx % len(LOCATIONS)]
    name = NAMES_50[idx]
    exp = ALL_TIERS_50[idx]
    uni, major = UNIVERSITIES[idx % len(UNIVERSITIES)]

    # Certificate
    primary_tgt = lang_info["tgt"] if lang_info["tgt"] != "Tiếng Việt" else lang_info["src"]
    cert_options = CERTIFICATES_MAP.get(primary_tgt, [("Chứng chỉ Năng lực Ngôn ngữ Chuyên nghiệp", 2022)])
    cert_name, cert_year = cert_options[idx % len(cert_options)]

    # Proficiency
    y = exp["years"]
    if y <= 2:
        proficiency = "Thành thạo chuyên nghiệp (B2+/C1)"
    elif y <= 5:
        proficiency = "Thành thạo cao cấp (C1/C2)"
    elif y <= 10:
        proficiency = "Thành thạo xuất sắc (C2/Bản ngữ)"
    else:
        proficiency = "Chuyên gia bản ngữ / Cabin chuẩn Quốc tế"

    types = INTERPRETING_TYPES_LIST[idx % len(INTERPRETING_TYPES_LIST)]
    emp_pref = EMPLOYMENT_PREFS[idx % len(EMPLOYMENT_PREFS)]
    avail_stat = AVAILABILITY_STATUSES[idx % len(AVAILABILITY_STATUSES)]

    title = f"{exp['title_pfx']} {lang_info['pair']} | Chuyên ngành {ind_primary}"

    bio = (
        f"Phiên dịch viên chuyên nghiệp với {y} năm kinh nghiệm thực chiến trong cặp ngôn ngữ "
        f"{lang_info['pair']}, am hiểu sâu sắc thuật ngữ chuyên ngành {ind_primary} và {ind_secondary}. "
        f"Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. "
        f"Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. "
        f"Sẵn sàng nhận lịch làm việc tại khu vực {loc_city} cũng như các dự án trực tuyến qua Zoom/Teams."
    )

    notable_clients = f"Tập đoàn đa quốc gia ngành {ind_primary}, Đối tác FDI tại {loc_city}, Ban tổ chức sự kiện quốc tế"
    featured_projects = f"Dự án đàm phán hợp đồng hợp tác {ind_primary}; Hội thảo xúc tiến thương mại {ind_secondary}"

    # Verification: 38 Verified, 8 Pending, 4 Draft
    is_premium = (idx % 4 == 0)
    if idx < 38:
        is_verified = True
        verification_status = "approved"
        badge_list = ["Đã xác minh danh tính", "Đã kiểm tra kỹ năng"]
        if exp["rating"] >= 4.8 and exp["jobs"] >= 25:
            badge_list.append("Top Rated")
        if is_premium:
            badge_list.append("Premium PDV")
    elif idx < 46:
        is_verified = False
        verification_status = "pending"
        badge_list = ["Đang xác minh hồ sơ KYC"]
        if is_premium:
            badge_list.append("Premium PDV")
    else:
        is_verified = False
        verification_status = "draft"
        badge_list = []
        if is_premium:
            badge_list.append("Premium PDV")

    badges_str = ", ".join(badge_list)

    email = f"pdv{idx+1:03d}@demo.viettranslate.local"
    phone = f"0901000{idx+1:03d}"
    avatar = AVATAR_ASSETS[idx % len(AVATAR_ASSETS)]

    return {
        "email": email,
        "legacy_email": f"demo_interpreter_{idx+1:03d}@viettranslate.demo",
        "name": name,
        "phone": phone,
        "avatar": avatar,
        "title": title,
        "bio": bio,
        "languages": lang_info["langs"],
        "source_language": lang_info["src"],
        "target_language": lang_info["tgt"],
        "interpreting_direction": "Hai chiều (Song phương)",
        "language_proficiency": proficiency,
        "native_language": lang_info["nat"],
        "specializations": f"{ind_primary}, {ind_secondary}",
        "interpreting_types": types,
        "work_modes": loc_mode,
        "city": loc_city,
        "country": loc_country,
        "service_areas": loc_area,
        "education_level": exp["level"],
        "university": uni,
        "major": major,
        "cert_name": cert_name,
        "cert_year": cert_year,
        "experience_years": y,
        "current_position": f"Phiên dịch viên {lang_info['tgt']} – {ind_primary}",
        "notable_clients": notable_clients,
        "featured_projects": featured_projects,
        "badges": badges_str,
        "rating": exp["rating"],
        "total_reviews": exp["rev"],
        "total_jobs": exp["jobs"],
        "is_verified": is_verified,
        "verification_status": verification_status,
        "hourly_rate": exp["h_rate"],
        "daily_rate": exp["d_rate"],
        "currency": "VND",
        "basic_price": exp["p_basic"],
        "standard_price": exp["p_std"],
        "premium_price": exp["p_prem"],
        "ind_primary": ind_primary,
        "ind_secondary": ind_secondary,
        "employment_preference": emp_pref,
        "availability_status": avail_stat,
    }


def seed_demo_interpreters(target_count=TARGET_DEMO_COUNT):
    """Nạp và đồng bộ chính xác target_count (50) hồ sơ phiên dịch viên demo."""
    with app.app_context():
        # Đếm số lượng trước khi seed
        count_users_before = User.query.count()
        count_demo_users_before = User.query.filter_by(is_demo=True).count()
        count_profiles_before = TranslatorProfile.query.count()
        count_demo_profiles_before = TranslatorProfile.query.filter_by(is_demo=True).count()

        print(f"[TRƯỚC KHI SEED] Tổng Users: {count_users_before} (Demo: {count_demo_users_before})")
        print(f"[TRƯỚC KHI SEED] Tổng Profiles: {count_profiles_before} (Demo: {count_demo_profiles_before})")

        created_users = 0
        updated_users = 0
        default_pw_hash = generate_password_hash("Demo@123456", method="pbkdf2:sha256")

        try:
            # 1. Dọn dẹp các demo account vượt quá số lượng target_count (e.g. pdv051 - pdv100)
            target_emails = {f"pdv{i+1:03d}@demo.viettranslate.local" for i in range(target_count)}
            excess_demo_users = User.query.filter(User.is_demo == True, ~User.email.in_(target_emails)).all()
            if excess_demo_users:
                print(f"[DỌN DẸP] Phát hiện {len(excess_demo_users)} hồ sơ demo dư thừa ngoài danh sách {target_count}. Tiến hành loại bỏ...")
                ex_u_ids = [u.id for u in excess_demo_users]
                ex_profiles = TranslatorProfile.query.filter(TranslatorProfile.user_id.in_(ex_u_ids)).all()
                ex_p_ids = [p.id for p in ex_profiles]
                Service.query.filter(Service.profile_id.in_(ex_p_ids)).delete(synchronize_session=False)
                InterpreterService.query.filter(InterpreterService.user_id.in_(ex_u_ids)).delete(synchronize_session=False)
                InterpreterPreference.query.filter(InterpreterPreference.user_id.in_(ex_u_ids)).delete(synchronize_session=False)
                TranslatorPreference.query.filter(TranslatorPreference.translator_id.in_(ex_u_ids)).delete(synchronize_session=False)
                TranslatorVerification.query.filter(TranslatorVerification.user_id.in_(ex_u_ids)).delete(synchronize_session=False)
                TranslatorProfile.query.filter(TranslatorProfile.id.in_(ex_p_ids)).delete(synchronize_session=False)
                User.query.filter(User.id.in_(ex_u_ids)).delete(synchronize_session=False)
                db.session.commit()
                print(f"[DỌN DẸP] Đã loại bỏ sạch sẽ các hồ sơ demo dư thừa.")

            # 2. Tạo hoặc cập nhật chính xác target_count hồ sơ demo
            for i in range(target_count):
                data = generate_profile_data(i)

                user = User.query.filter_by(email=data["email"]).first()
                if not user:
                    user = User.query.filter_by(email=data["legacy_email"]).first()

                if not user:
                    user = User(
                        email=data["email"],
                        name=data["name"],
                        password_hash=default_pw_hash,
                        phone=data["phone"],
                        role="translator",
                        is_admin=False,
                        is_active=True,
                        is_demo=True,
                        email_verified=True,
                        avatar=data["avatar"],
                        city=data["city"],
                        bio=data["bio"],
                        is_public_profile=True,
                    )
                    db.session.add(user)
                    db.session.flush()
                    created_users += 1
                else:
                    user.email = data["email"]
                    user.name = data["name"]
                    user.phone = data["phone"]
                    user.role = "translator"
                    user.is_active = True
                    user.is_demo = True
                    user.avatar = data["avatar"]
                    user.city = data["city"]
                    user.bio = data["bio"]
                    user.is_public_profile = True
                    updated_users += 1

                # 1. TranslatorProfile
                profile = TranslatorProfile.query.filter_by(user_id=user.id).first()
                if not profile:
                    profile = TranslatorProfile(user_id=user.id)
                    db.session.add(profile)

                profile.title = data["title"]
                profile.bio = data["bio"]
                profile.languages = data["languages"]
                profile.source_language = data["source_language"]
                profile.target_language = data["target_language"]
                profile.interpreting_direction = data["interpreting_direction"]
                profile.language_proficiency = data["language_proficiency"]
                profile.native_language = data["native_language"]
                profile.specializations = data["specializations"]
                profile.interpreting_types = data["interpreting_types"]
                profile.work_modes = data["work_modes"]
                profile.education_level = data["education_level"]
                profile.university = data["university"]
                profile.major = data["major"]
                profile.cert_name = data["cert_name"]
                profile.cert_year = data["cert_year"]
                profile.certificates = f"{data['cert_name']} ({data['cert_year']})"
                profile.experience_years = data["experience_years"]
                profile.current_position = data["current_position"]
                profile.notable_clients = data["notable_clients"]
                profile.featured_projects = data["featured_projects"]
                profile.badges = data["badges"]
                profile.rating = data["rating"]
                profile.total_reviews = data["total_reviews"]
                profile.total_jobs = data["total_jobs"]
                profile.response_time = "Trong vòng 1 giờ"
                profile.is_verified = data["is_verified"]
                profile.is_demo = True
                profile.is_public = True
                profile.is_cv_public = False
                profile.hourly_rate = data["hourly_rate"]
                profile.daily_rate = data["daily_rate"]
                profile.currency = data["currency"]
                profile.employment_preference = data["employment_preference"]
                profile.availability_status = data["availability_status"]
                profile.service_areas = data["service_areas"]
                profile.country = data["country"]
                db.session.flush()

                # 2. TranslatorVerification (KYC module)
                verif = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
                if not verif:
                    verif = TranslatorVerification(user_id=user.id)
                    db.session.add(verif)

                verif.full_name = data["name"]
                verif.phone = data["phone"]
                verif.location = data["city"]
                verif.bio = data["bio"]
                verif.source_language = data["source_language"]
                verif.target_language = data["target_language"]
                verif.interpreting_direction = data["interpreting_direction"]
                verif.language_proficiency = data["language_proficiency"]
                verif.specializations = data["specializations"]
                verif.interpreting_types = data["interpreting_types"]
                verif.education_level = data["education_level"]
                verif.university = data["university"]
                verif.major = data["major"]
                verif.certificate_type = data["cert_name"].split()[0]
                verif.certificate_name = data["cert_name"]
                verif.cert_year = data["cert_year"]
                verif.experience_years = data["experience_years"]
                verif.current_position = data["current_position"]
                verif.notable_clients = data["notable_clients"]
                verif.featured_projects = data["featured_projects"]
                verif.status = data["verification_status"]
                if data["is_verified"]:
                    verif.current_step = 5
                    verif.reviewed_at = datetime.utcnow()
                elif data["verification_status"] in ["pending", "revision"]:
                    verif.current_step = 5
                    verif.submitted_at = datetime.utcnow()
                    if data["verification_status"] == "revision":
                        verif.rejection_reason = "Vui lòng bổ sung bản scan rõ nét hơn của chứng chỉ ngôn ngữ."
                else:
                    verif.current_step = 1

                # 3. Service Package (Used for search cards, pricing breakdown, and booking)
                svc = Service.query.filter_by(profile_id=profile.id).first()
                if not svc:
                    svc = Service(profile_id=profile.id)
                    db.session.add(svc)
                svc.name = f"Dịch vụ phiên dịch {data['ind_primary']}"
                svc.description = f"Gói dịch vụ phiên dịch {data['languages']} chuyên sâu ngành {data['ind_primary']} cho cuộc họp, đàm phán hoặc sự kiện."
                svc.languages = data["languages"]
                svc.category = data["ind_primary"]
                svc.basic_price = data["basic_price"]
                svc.standard_price = data["standard_price"]
                svc.premium_price = data["premium_price"]
                svc.basic_delivery = "1 ngày"
                svc.standard_delivery = "2 ngày"
                svc.premium_delivery = "3 ngày"

                # 4. InterpreterService (Phân hệ Mục V)
                isvc = InterpreterService.query.filter_by(user_id=user.id).first()
                if not isvc:
                    isvc = InterpreterService(user_id=user.id)
                    db.session.add(isvc)
                isvc.source_lang = data["source_language"]
                isvc.target_lang = data["target_language"]
                isvc.interpreting_type = data["interpreting_types"].split(",")[0].strip()
                isvc.specialization = data["ind_primary"]
                isvc.hourly_rate = data["hourly_rate"]
                isvc.session_rate = data["daily_rate"]
                isvc.currency = data["currency"]
                isvc.is_active = True

                # 5. InterpreterPreference (Phân hệ Mục 5.4)
                ipref = InterpreterPreference.query.filter_by(user_id=user.id).first()
                if not ipref:
                    ipref = InterpreterPreference(user_id=user.id)
                    db.session.add(ipref)
                lang_pairs_list = [
                    f"{data['source_language']} > {data['target_language']}",
                    f"{data['target_language']} > {data['source_language']}",
                ]
                ipref.set_languages_list(lang_pairs_list)
                ipref.specializations = data["specializations"]
                ipref.work_mode = "both"
                ipref.min_rate = data["hourly_rate"]
                ipref.max_rate = data["daily_rate"]
                ipref.locations = data["city"]

                # 6. TranslatorPreference (Smart Matching & Account Preferences)
                tpref = TranslatorPreference.query.filter_by(translator_id=user.id).first()
                if not tpref:
                    tpref = TranslatorPreference(translator_id=user.id)
                    db.session.add(tpref)
                tpref.languages = data["languages"]
                tpref.language_pairs = f"{data['source_language']} > {data['target_language']}, {data['target_language']} > {data['source_language']}"
                tpref.service_types = "Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện"
                tpref.specialties = data["specializations"]
                tpref.city = data["city"]
                tpref.work_mode = "both"
                tpref.offers_certified = True
                tpref.notify_new_jobs = True
                tpref.notify_messages = True
                tpref.notify_contracts = True
                tpref.notify_reviews = True

            db.session.commit()
            print(f"[SEED HOÀN TẤT] Tạo mới: {created_users}, Cập nhật: {updated_users}.")

            count_users_after = User.query.count()
            count_demo_users_after = User.query.filter_by(is_demo=True).count()
            count_profiles_after = TranslatorProfile.query.count()
            count_demo_profiles_after = TranslatorProfile.query.filter_by(is_demo=True).count()

            print(f"[SAU KHI SEED] Tổng Users: {count_users_after} (Demo: {count_demo_users_after})")
            print(f"[SAU KHI SEED] Tổng Profiles: {count_profiles_after} (Demo: {count_demo_profiles_after})")

            return {
                "before": {"users": count_users_before, "demo_users": count_demo_users_before, "profiles": count_profiles_before, "demo_profiles": count_demo_profiles_before},
                "after": {"users": count_users_after, "demo_users": count_demo_users_after, "profiles": count_profiles_after, "demo_profiles": count_demo_profiles_after},
                "created": created_users,
                "updated": updated_users,
            }

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Quá trình seed gặp lỗi, đã rollback: {e}")
            raise


if __name__ == "__main__":
    seed_demo_interpreters(50)
