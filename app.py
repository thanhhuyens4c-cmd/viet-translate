import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort, Response
from models import db, User, TranslatorProfile, TranslatorPreference, Service, Job, Proposal, Contract, Message, DirectMessage, Deliverable, Review, LANGUAGES
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
import re
from translations import t as t_lookup, get_localized_languages
from sqlalchemy.pool import StaticPool

# ─── MONGODB (dùng khi deploy trên Vercel) ────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI")
_mongo_users = None  # lazy-init collection

def get_mongo_users():
    """Trả về MongoDB users collection nếu MONGO_URI được cấu hình."""
    global _mongo_users
    if _mongo_users is None and MONGO_URI:
        try:
            from pymongo import MongoClient
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            _mongo_users = client["viettranslate_db"]["users"]
        except Exception as e:
            print(f"[MongoDB] Không thể kết nối: {e}")
    return _mongo_users

def mongo_register_user(username, email, hashed_password, phone, role):
    """Đăng ký tài khoản mới vào MongoDB. Trả về (success, message)."""
    col = get_mongo_users()
    if col is None:
        return False, "MongoDB chưa được cấu hình."
    if col.find_one({"email": email}):
        return False, "Email đã được sử dụng."
    col.insert_one({
        "name": username,
        "email": email,
        "password_hash": hashed_password,
        "phone": phone,
        "role": role,
        "is_admin": False,
        "is_active": True,
        "created_at": datetime.utcnow(),
    })
    return True, "Đăng ký thành công!"

def mongo_find_user_by_email(email):
    """Tìm user theo email trong MongoDB. Trả về dict hoặc None."""
    col = get_mongo_users()
    if col is None:
        return None
    return col.find_one({"email": email})

def mongo_find_user_by_id(user_id):
    """Tìm user theo _id string trong MongoDB. Trả về dict hoặc None."""
    col = get_mongo_users()
    if col is None:
        return None
    try:
        from bson import ObjectId
        return col.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None

# ─── LANGUAGE LANDING PAGE CONFIGURATION ──────────────────────────────────────

LANGUAGE_PAGES = {
    "english": {
        "name": "Tiếng Anh",
        "flag": "🇬🇧",
        "slug": "english",
        "title": "Phiên Dịch Tiếng Anh",
        "subtitle": "Tìm phiên dịch viên tiếng Anh phù hợp cho công việc, hội thảo, phỏng vấn và tài liệu chuyên ngành.",
        "seo_description": "Tìm phiên dịch viên tiếng Anh chuyên nghiệp tại VietTranslate. So sánh hồ sơ, đánh giá, mức giá và chuyên môn trước khi lựa chọn.",
        "starting_price": 40000,
        "certificates": ["IELTS", "TOEIC", "VSTEP"],
        "use_cases": [
            "Phiên dịch hội nghị & sự kiện quốc tế",
            "Dịch tài liệu pháp lý & hợp đồng",
            "Phiên dịch y tế & khoa học",
            "Dịch thuật thương mại & xuất nhập khẩu",
        ],
        "seo_content": (
            "Tiếng Anh là ngôn ngữ quốc tế được sử dụng rộng rãi nhất trong giao thương, giáo dục và ngoại giao. "
            "Nhu cầu thuê phiên dịch viên tiếng Anh tại Việt Nam ngày càng tăng cao, đặc biệt trong bối cảnh hội nhập kinh tế toàn cầu. "
            "Từ các hội nghị quốc tế, đàm phán thương mại đến dịch thuật tài liệu pháp lý và y tế, phiên dịch viên tiếng Anh chuyên nghiệp đóng vai trò không thể thiếu. "
            "Khi lựa chọn phiên dịch viên tiếng Anh, bạn nên xem xét chứng chỉ (IELTS 7.0+, TOEIC 900+, hoặc VSTEP C1), kinh nghiệm trong lĩnh vực cụ thể, "
            "và khả năng phiên dịch cả hai chiều Anh-Việt, Việt-Anh một cách trơn tru. "
            "Tại VietTranslate, bạn có thể dễ dàng so sánh hồ sơ, xem đánh giá từ khách hàng thực tế và đặt dịch vụ an toàn qua hệ thống Escrow."
        ),
        "faq": [
            {
                "q": "Giá thuê phiên dịch tiếng Anh là bao nhiêu?",
                "a": "Mức giá phiên dịch tiếng Anh tham khảo từ 40.000đ trở lên, tùy vào loại hình (phiên dịch cabin, liên tục, tài liệu), thời lượng và chuyên môn yêu cầu.",
            },
            {
                "q": "Phiên dịch tiếng Anh cần chứng chỉ gì?",
                "a": "Phiên dịch viên tiếng Anh chuyên nghiệp thường có IELTS 7.0 trở lên, TOEIC 900+, hoặc VSTEP C1. Một số vị trí chuyên ngành yêu cầu bằng cấp phù hợp.",
            },
            {
                "q": "Làm thế nào để chọn phiên dịch viên tiếng Anh?",
                "a": "Hãy xem xét kinh nghiệm trong lĩnh vực cần dịch, đánh giá từ khách hàng trước, chứng chỉ ngôn ngữ và khả năng giao tiếp phản hồi nhanh.",
            },
            {
                "q": "Phiên dịch tiếng Anh có thể nhận những loại công việc nào?",
                "a": "Phiên dịch hội nghị, tòa án, y tế, thương mại, kỹ thuật, dịch tài liệu, phụ đề video, phiên dịch online qua Zoom/Teams...",
            },
        ],
    },
    "japanese": {
        "name": "Tiếng Nhật",
        "flag": "🇯🇵",
        "slug": "japanese",
        "title": "Phiên Dịch Tiếng Nhật",
        "subtitle": "Tìm phiên dịch viên tiếng Nhật phù hợp cho công việc, hội nghị, giao tiếp kinh doanh và các nhu cầu chuyên môn.",
        "seo_description": "Tìm phiên dịch viên tiếng Nhật chuyên nghiệp tại VietTranslate. Xem hồ sơ, đánh giá, mức giá và kinh nghiệm để lựa chọn phiên dịch viên phù hợp.",
        "starting_price": 30000,
        "certificates": ["JLPT N2 trở lên"],
        "use_cases": [
            "Phiên dịch làm việc với doanh nghiệp Nhật Bản",
            "Dịch tài liệu kỹ thuật & bản vẽ",
            "Phiên dịch xuất khẩu lao động Nhật Bản",
            "Dịch hợp đồng & tài liệu pháp lý Nhật-Việt",
        ],
        "seo_content": (
            "Tiếng Nhật là ngôn ngữ đặc thù với ba bộ chữ Hiragana, Katakana và Kanji, đòi hỏi phiên dịch viên phải đạt trình độ học thuật cao. "
            "Quan hệ thương mại Việt–Nhật ngày càng phát triển, kéo theo nhu cầu lớn về phiên dịch trong lĩnh vực sản xuất, FDI, xuất khẩu lao động và hợp tác kỹ thuật. "
            "Phiên dịch viên tiếng Nhật giỏi không chỉ thông thạo ngôn ngữ mà còn phải hiểu văn hóa doanh nghiệp Nhật Bản — tính cẩn thận, tôn trọng thứ bậc và giao tiếp gián tiếp. "
            "Khi chọn phiên dịch viên tiếng Nhật, hãy ưu tiên người có JLPT N2 trở lên và kinh nghiệm thực tế trong ngành bạn cần. "
            "VietTranslate kết nối bạn với đội ngũ phiên dịch viên tiếng Nhật uy tín, được đánh giá bởi khách hàng thực tế."
        ),
        "faq": [
            {
                "q": "Giá thuê phiên dịch tiếng Nhật là bao nhiêu?",
                "a": "Mức giá tham khảo từ 30.000đ, tùy vào loại hình phiên dịch, thời lượng và chuyên môn. Phiên dịch kỹ thuật hoặc tài liệu pháp lý thường có mức giá cao hơn.",
            },
            {
                "q": "Phiên dịch tiếng Nhật cần chứng chỉ gì?",
                "a": "Phiên dịch viên tiếng Nhật chuyên nghiệp thường có chứng chỉ JLPT N2 trở lên. Với công việc kỹ thuật cao, JLPT N1 được ưu tiên.",
            },
            {
                "q": "Làm thế nào để chọn phiên dịch viên tiếng Nhật?",
                "a": "Xem xét trình độ JLPT, kinh nghiệm trong lĩnh vực cụ thể (kỹ thuật, pháp lý, y tế), đánh giá từ khách hàng và khả năng hiểu văn hóa Nhật.",
            },
            {
                "q": "Phiên dịch tiếng Nhật có thể nhận những loại công việc nào?",
                "a": "Phiên dịch hội nghị với đối tác Nhật, dịch tài liệu kỹ thuật, hồ sơ xuất khẩu lao động, hợp đồng thương mại, phiên dịch nhà máy, dịch manga/anime chuyên nghiệp.",
            },
        ],
    },
    "korean": {
        "name": "Tiếng Hàn",
        "flag": "🇰🇷",
        "slug": "korean",
        "title": "Phiên Dịch Tiếng Hàn",
        "subtitle": "Kết nối với phiên dịch viên tiếng Hàn có kinh nghiệm cho mọi nhu cầu kinh doanh, giáo dục và văn hóa.",
        "seo_description": "Tìm phiên dịch viên tiếng Hàn chuyên nghiệp tại VietTranslate. So sánh hồ sơ, mức giá và đánh giá để chọn người phù hợp nhất.",
        "starting_price": 35000,
        "certificates": ["TOPIK 4 trở lên"],
        "use_cases": [
            "Phiên dịch làm việc với doanh nghiệp Hàn Quốc",
            "Dịch hồ sơ xuất khẩu lao động Hàn Quốc (EPS-TOPIK)",
            "Phiên dịch hội nghị & đàm phán thương mại",
            "Dịch nội dung K-pop, phim, truyện tranh",
        ],
        "seo_content": (
            "Quan hệ Việt–Hàn đang ở giai đoạn phát triển mạnh với hàng nghìn doanh nghiệp Hàn Quốc đầu tư vào Việt Nam. "
            "Nhu cầu phiên dịch tiếng Hàn rất đa dạng: từ môi trường nhà máy, văn phòng doanh nghiệp đến các lĩnh vực văn hóa, giải trí và du học. "
            "Phiên dịch viên tiếng Hàn cần thành thạo cả Hangul lẫn văn hóa giao tiếp Hàn Quốc. Chứng chỉ TOPIK cấp 4 trở lên là tiêu chuẩn tối thiểu cho phiên dịch chuyên nghiệp. "
            "Tại VietTranslate, bạn có thể tìm phiên dịch viên tiếng Hàn theo chuyên ngành, xem đánh giá thực tế và đặt dịch vụ với chi phí minh bạch."
        ),
        "faq": [
            {
                "q": "Giá thuê phiên dịch tiếng Hàn là bao nhiêu?",
                "a": "Mức giá tham khảo từ 35.000đ, tùy theo loại hình và thời lượng phiên dịch.",
            },
            {
                "q": "Phiên dịch tiếng Hàn cần chứng chỉ gì?",
                "a": "Phiên dịch viên tiếng Hàn thường có TOPIK cấp 4 (điểm 200+) trở lên. Các vị trí cao cấp yêu cầu TOPIK cấp 5 hoặc 6.",
            },
            {
                "q": "Làm thế nào để chọn phiên dịch viên tiếng Hàn phù hợp?",
                "a": "Xem xét cấp TOPIK, kinh nghiệm trong ngành (sản xuất, pháp lý, giải trí), đánh giá từ khách hàng và tốc độ phản hồi.",
            },
            {
                "q": "Phiên dịch tiếng Hàn phù hợp với những lĩnh vực nào?",
                "a": "Nhà máy, doanh nghiệp FDI Hàn Quốc, EPS-TOPIK, K-beauty, K-pop, phim truyền hình, du học Hàn Quốc, hợp đồng thương mại.",
            },
        ],
    },
    "chinese": {
        "name": "Tiếng Trung",
        "flag": "🇨🇳",
        "slug": "chinese",
        "title": "Phiên Dịch Tiếng Trung",
        "subtitle": "Tìm phiên dịch viên tiếng Trung (Quan Thoại/Quảng Đông) cho thương mại, kỹ thuật và giao tiếp doanh nghiệp.",
        "seo_description": "Tìm phiên dịch viên tiếng Trung chuyên nghiệp tại VietTranslate. Xem hồ sơ, đánh giá và mức giá để lựa chọn người phù hợp.",
        "starting_price": 30000,
        "certificates": ["HSK 5 trở lên"],
        "use_cases": [
            "Phiên dịch thương mại Việt–Trung",
            "Dịch tài liệu kỹ thuật & bản vẽ từ Trung Quốc",
            "Phiên dịch đàm phán nhập khẩu hàng hóa",
            "Dịch hợp đồng & chứng từ xuất nhập khẩu",
        ],
        "seo_content": (
            "Trung Quốc là đối tác thương mại lớn nhất của Việt Nam, tạo ra nhu cầu khổng lồ về phiên dịch tiếng Trung trong kinh doanh, thương mại và sản xuất. "
            "Phiên dịch viên tiếng Trung cần phân biệt rõ tiếng Phổ Thông (Quan Thoại) và tiếng Quảng Đông, cũng như chữ Giản Thể và Phồn Thể. "
            "Chứng chỉ HSK (Hanyu Shuiping Kaoshi) cấp 5 trở lên là tiêu chuẩn cho phiên dịch chuyên nghiệp. "
            "Tại VietTranslate, bạn có thể tìm phiên dịch viên tiếng Trung theo từng chuyên ngành, đảm bảo chính xác và hiệu quả trong giao tiếp thương mại."
        ),
        "faq": [
            {
                "q": "Giá thuê phiên dịch tiếng Trung là bao nhiêu?",
                "a": "Mức giá tham khảo từ 30.000đ, tùy theo phương ngữ (Quan Thoại/Quảng Đông), loại hình và thời lượng.",
            },
            {
                "q": "Phiên dịch tiếng Trung cần chứng chỉ gì?",
                "a": "Phiên dịch viên tiếng Trung thường có HSK 5 trở lên. Một số vị trí yêu cầu HSK 6 hoặc bằng cử nhân tiếng Trung.",
            },
            {
                "q": "Làm thế nào để chọn phiên dịch viên tiếng Trung?",
                "a": "Xác định phương ngữ cần (Quan Thoại hay Quảng Đông), xem chứng chỉ HSK, kinh nghiệm thương mại và đánh giá từ khách hàng.",
            },
            {
                "q": "Phiên dịch tiếng Trung phù hợp với những lĩnh vực nào?",
                "a": "Thương mại xuất nhập khẩu, đàm phán với đối tác Trung Quốc, dịch tài liệu kỹ thuật, hội nghị doanh nghiệp, dịch nội dung số.",
            },
        ],
    },
    "russian": {
        "name": "Tiếng Nga",
        "flag": "🇷🇺",
        "slug": "russian",
        "title": "Phiên Dịch Tiếng Nga",
        "subtitle": "Tìm phiên dịch viên tiếng Nga chuyên nghiệp cho ngoại giao, kỹ thuật, khoa học và hợp tác quốc tế.",
        "seo_description": "Tìm phiên dịch viên tiếng Nga chuyên nghiệp tại VietTranslate. So sánh hồ sơ, mức giá và kinh nghiệm để lựa chọn phù hợp.",
        "starting_price": 45000,
        "certificates": ["ТРКИ B2 trở lên"],
        "use_cases": [
            "Phiên dịch hợp tác kỹ thuật & khoa học",
            "Dịch tài liệu ngoại giao & quốc phòng",
            "Phiên dịch năng lượng & dầu khí",
            "Dịch văn học & nghiên cứu học thuật",
        ],
        "seo_content": (
            "Tiếng Nga là ngôn ngữ chính thức của Liên bang Nga và được sử dụng rộng rãi ở nhiều quốc gia thuộc Liên Xô cũ. "
            "Quan hệ Việt–Nga có lịch sử lâu dài trong lĩnh vực giáo dục, khoa học, quốc phòng và năng lượng. "
            "Phiên dịch viên tiếng Nga chuyên nghiệp thường có kiến thức sâu về khoa học kỹ thuật hoặc ngoại giao. "
            "Tại VietTranslate, bạn có thể tìm phiên dịch viên tiếng Nga phù hợp với yêu cầu chuyên môn của mình."
        ),
        "faq": [
            {
                "q": "Giá thuê phiên dịch tiếng Nga là bao nhiêu?",
                "a": "Mức giá tham khảo từ 45.000đ, phụ thuộc vào chuyên ngành và thời lượng yêu cầu.",
            },
            {
                "q": "Phiên dịch tiếng Nga cần yêu cầu chuyên môn gì?",
                "a": "Yêu cầu chuyên môn tùy theo từng công việc. Phiên dịch kỹ thuật thường yêu cầu nền tảng khoa học; phiên dịch ngoại giao yêu cầu kinh nghiệm thực tế.",
            },
            {
                "q": "Làm thế nào để chọn phiên dịch viên tiếng Nga?",
                "a": "Xem xét kinh nghiệm trong lĩnh vực cụ thể, khả năng phiên dịch 2 chiều, đánh giá từ khách hàng và bằng cấp học thuật liên quan.",
            },
            {
                "q": "Phiên dịch tiếng Nga phù hợp với những lĩnh vực nào?",
                "a": "Hợp tác kỹ thuật, dầu khí, nghiên cứu khoa học, ngoại giao, giáo dục, du lịch và văn học.",
            },
        ],
    },
    "thai": {
        "name": "Tiếng Thái",
        "flag": "🇹🇭",
        "slug": "thai",
        "title": "Phiên Dịch Tiếng Thái",
        "subtitle": "Tìm phiên dịch viên tiếng Thái cho thương mại, du lịch và hợp tác khu vực ASEAN.",
        "seo_description": "Tìm phiên dịch viên tiếng Thái chuyên nghiệp tại VietTranslate. Xem hồ sơ và đánh giá để chọn người phù hợp.",
        "starting_price": 40000,
        "certificates": None,
        "use_cases": [
            "Phiên dịch thương mại ASEAN",
            "Dịch hợp đồng & tài liệu pháp lý Thái–Việt",
            "Phiên dịch du lịch & khách sạn",
            "Dịch nội dung truyền thông & giải trí",
        ],
        "seo_content": (
            "Thái Lan và Việt Nam là hai nền kinh tế lớn trong khối ASEAN với quan hệ thương mại ngày càng mở rộng. "
            "Nhu cầu phiên dịch tiếng Thái tập trung chủ yếu vào thương mại, nông nghiệp, du lịch và đầu tư FDI. "
            "Tiếng Thái có hệ thống chữ viết và thanh điệu đặc trưng, đòi hỏi phiên dịch viên được đào tạo chuyên biệt. "
            "VietTranslate kết nối bạn với phiên dịch viên tiếng Thái uy tín, phù hợp với nhu cầu thực tế của bạn."
        ),
        "faq": [
            {
                "q": "Giá thuê phiên dịch tiếng Thái là bao nhiêu?",
                "a": "Mức giá tham khảo từ 40.000đ, tùy theo loại hình và thời lượng phiên dịch.",
            },
            {
                "q": "Phiên dịch tiếng Thái cần yêu cầu chuyên môn gì?",
                "a": "Yêu cầu chuyên môn tùy theo từng công việc. Liên hệ trực tiếp với phiên dịch viên để thảo luận về yêu cầu cụ thể.",
            },
            {
                "q": "Phiên dịch tiếng Thái phù hợp với những lĩnh vực nào?",
                "a": "Thương mại ASEAN, du lịch, nông nghiệp, hợp đồng đầu tư, nội dung truyền thông và giải trí.",
            },
            {
                "q": "Làm thế nào để chọn phiên dịch viên tiếng Thái?",
                "a": "Xem xét kinh nghiệm trong lĩnh vực cần dịch, đánh giá từ khách hàng trước và khả năng phản hồi nhanh.",
            },
        ],
    },
    "french": {
        "name": "Tiếng Pháp",
        "flag": "🇫🇷",
        "slug": "french",
        "title": "Phiên Dịch Tiếng Pháp",
        "subtitle": "Tìm phiên dịch viên tiếng Pháp cho ngoại giao, pháp lý, văn hóa và hợp tác quốc tế Pháp ngữ.",
        "seo_description": "Tìm phiên dịch viên tiếng Pháp chuyên nghiệp tại VietTranslate. So sánh hồ sơ, mức giá và chuyên môn để lựa chọn phù hợp.",
        "starting_price": 45000,
        "certificates": ["DELF B2 trở lên"],
        "use_cases": [
            "Phiên dịch ngoại giao & tổ chức quốc tế",
            "Dịch tài liệu pháp lý & hành chính Pháp ngữ",
            "Phiên dịch văn hóa & nghệ thuật",
            "Dịch học thuật & nghiên cứu khoa học",
        ],
        "seo_content": (
            "Tiếng Pháp là ngôn ngữ chính thức của 29 quốc gia và là ngôn ngữ làm việc của nhiều tổ chức quốc tế lớn như Liên Hợp Quốc, EU. "
            "Việt Nam có lịch sử gắn bó với tiếng Pháp và hiện có cộng đồng Pháp ngữ đáng kể. "
            "Phiên dịch viên tiếng Pháp thường hoạt động trong lĩnh vực ngoại giao, pháp lý, giáo dục và văn hóa. "
            "Chứng chỉ DELF B2 trở lên là tiêu chuẩn tối thiểu, với các vị trí cao cấp yêu cầu DALF C1/C2. "
            "Tại VietTranslate, bạn có thể tìm phiên dịch viên tiếng Pháp uy tín với đánh giá minh bạch từ khách hàng thực tế."
        ),
        "faq": [
            {
                "q": "Giá thuê phiên dịch tiếng Pháp là bao nhiêu?",
                "a": "Mức giá tham khảo từ 45.000đ, tùy theo chuyên ngành và thời lượng yêu cầu.",
            },
            {
                "q": "Phiên dịch tiếng Pháp cần chứng chỉ gì?",
                "a": "Phiên dịch viên tiếng Pháp chuyên nghiệp thường có DELF B2 trở lên hoặc DALF C1/C2. Một số có bằng cử nhân tiếng Pháp hoặc ngành liên quan.",
            },
            {
                "q": "Phiên dịch tiếng Pháp phù hợp với những lĩnh vực nào?",
                "a": "Ngoại giao, tổ chức quốc tế, pháp lý, giáo dục đại học, nghiên cứu khoa học, văn hóa nghệ thuật và du lịch.",
            },
            {
                "q": "Làm thế nào để chọn phiên dịch viên tiếng Pháp?",
                "a": "Xem xét chứng chỉ DELF/DALF, kinh nghiệm trong lĩnh vực cụ thể, khả năng phiên dịch hai chiều và đánh giá từ khách hàng.",
            },
        ],
    },
    "german": {
        "name": "Tiếng Đức",
        "flag": "🇩🇪",
        "slug": "german",
        "title": "Phiên Dịch Tiếng Đức",
        "subtitle": "Tìm phiên dịch viên tiếng Đức cho kỹ thuật, sản xuất, xuất nhập khẩu và hợp tác với doanh nghiệp Đức.",
        "seo_description": "Tìm phiên dịch viên tiếng Đức chuyên nghiệp tại VietTranslate. So sánh hồ sơ, đánh giá và mức giá để chọn người phù hợp.",
        "starting_price": 50000,
        "certificates": ["TestDaF / Goethe B2"],
        "use_cases": [
            "Phiên dịch làm việc với doanh nghiệp Đức & châu Âu",
            "Dịch tài liệu kỹ thuật & máy móc nhập khẩu",
            "Phiên dịch hội nghị thương mại",
            "Hỗ trợ du học & định cư tại Đức",
        ],
        "seo_content": (
            "Đức là nền kinh tế lớn nhất châu Âu và là đối tác thương mại quan trọng của Việt Nam trong lĩnh vực máy móc, thiết bị và công nghệ cao. "
            "Phiên dịch tiếng Đức đòi hỏi độ chính xác cao do tiếng Đức có cấu trúc ngữ pháp phức tạp và nhiều thuật ngữ kỹ thuật chuyên biệt. "
            "Chứng chỉ Goethe B2 hoặc TestDaF là tiêu chuẩn phổ biến, với các vị trí cao cấp yêu cầu C1/C2. "
            "Tại VietTranslate, bạn có thể tìm phiên dịch viên tiếng Đức giàu kinh nghiệm, đặc biệt trong lĩnh vực kỹ thuật và thương mại quốc tế."
        ),
        "faq": [
            {
                "q": "Giá thuê phiên dịch tiếng Đức là bao nhiêu?",
                "a": "Mức giá tham khảo từ 50.000đ, tùy theo chuyên ngành và mức độ phức tạp của nội dung.",
            },
            {
                "q": "Phiên dịch tiếng Đức cần chứng chỉ gì?",
                "a": "Phiên dịch tiếng Đức chuyên nghiệp thường có Goethe B2 trở lên hoặc TestDaF. Vị trí kỹ thuật có thể yêu cầu bằng cấp chuyên ngành.",
            },
            {
                "q": "Phiên dịch tiếng Đức phù hợp với những lĩnh vực nào?",
                "a": "Kỹ thuật, máy móc thiết bị, ô tô, dược phẩm, hóa chất, thương mại quốc tế, hỗ trợ du học Đức.",
            },
            {
                "q": "Làm thế nào để chọn phiên dịch viên tiếng Đức?",
                "a": "Xem xét chứng chỉ ngôn ngữ, kiến thức chuyên ngành kỹ thuật, đánh giá từ khách hàng và khả năng phản hồi nhanh.",
            },
        ],
    },
    "portuguese": {
        "name": "Tiếng Bồ Đào Nha",
        "flag": "🇵🇹",
        "slug": "portuguese",
        "title": "Phiên Dịch Tiếng Bồ Đào Nha",
        "subtitle": "Tìm phiên dịch viên tiếng Bồ Đào Nha (Brazil/Portugal) cho thương mại, đầu tư và hợp tác quốc tế.",
        "seo_description": "Tìm phiên dịch viên tiếng Bồ Đào Nha chuyên nghiệp tại VietTranslate. Xem hồ sơ và đánh giá để lựa chọn phù hợp.",
        "starting_price": 50000,
        "certificates": ["CELPE-Bras"],
        "use_cases": [
            "Phiên dịch thương mại với đối tác Brazil & Bồ Đào Nha",
            "Dịch tài liệu nông nghiệp & thực phẩm",
            "Phiên dịch hội nghị quốc tế",
            "Dịch nội dung truyền thông Lusophone",
        ],
        "seo_content": (
            "Tiếng Bồ Đào Nha là ngôn ngữ của hơn 250 triệu người trên thế giới, đặc biệt tại Brazil — nền kinh tế lớn nhất Nam Mỹ. "
            "Việt Nam có quan hệ thương mại ngày càng phát triển với Brazil trong lĩnh vực nông nghiệp, thực phẩm và hàng hóa tiêu dùng. "
            "Phiên dịch viên tiếng Bồ Đào Nha cần phân biệt rõ tiếng Bồ Đào Nha của Brazil và Bồ Đào Nha (châu Âu). "
            "Tại VietTranslate, bạn có thể tìm phiên dịch viên tiếng Bồ Đào Nha phù hợp với nhu cầu cụ thể của mình."
        ),
        "faq": [
            {
                "q": "Giá thuê phiên dịch tiếng Bồ Đào Nha là bao nhiêu?",
                "a": "Mức giá tham khảo từ 50.000đ, tùy theo phương ngữ (Brazil hay Bồ Đào Nha), loại hình và thời lượng.",
            },
            {
                "q": "Phiên dịch tiếng Bồ Đào Nha cần chứng chỉ gì?",
                "a": "Chứng chỉ CELPE-Bras (Brazil) là phổ biến. Yêu cầu chuyên môn cụ thể tùy theo từng công việc.",
            },
            {
                "q": "Phiên dịch tiếng Bồ Đào Nha phù hợp với những lĩnh vực nào?",
                "a": "Thương mại nông sản, xuất nhập khẩu, đầu tư quốc tế, nội dung truyền thông, nghiên cứu học thuật.",
            },
            {
                "q": "Làm thế nào để chọn phiên dịch viên tiếng Bồ Đào Nha?",
                "a": "Xác định phương ngữ cần (Brazil hay châu Âu), xem kinh nghiệm thực tế, đánh giá từ khách hàng và chuyên môn lĩnh vực.",
            },
        ],
    },
    "spanish": {
        "name": "Tiếng Tây Ban Nha",
        "flag": "🇪🇸",
        "slug": "spanish",
        "title": "Phiên Dịch Tiếng Tây Ban Nha",
        "subtitle": "Tìm phiên dịch viên tiếng Tây Ban Nha cho thương mại quốc tế, pháp lý và hợp tác với thị trường Mỹ Latinh.",
        "seo_description": "Tìm phiên dịch viên tiếng Tây Ban Nha chuyên nghiệp tại VietTranslate. So sánh hồ sơ, mức giá và kinh nghiệm để lựa chọn phù hợp.",
        "starting_price": 50000,
        "certificates": ["DELE B2 trở lên"],
        "use_cases": [
            "Phiên dịch thương mại với thị trường Mỹ Latinh",
            "Dịch tài liệu pháp lý & hợp đồng",
            "Phiên dịch hội nghị quốc tế",
            "Dịch nội dung marketing & truyền thông",
        ],
        "seo_content": (
            "Tiếng Tây Ban Nha là ngôn ngữ được nói nhiều thứ hai trên thế giới, với hơn 500 triệu người sử dụng tại Tây Ban Nha và 20 quốc gia Mỹ Latinh. "
            "Nhu cầu phiên dịch tiếng Tây Ban Nha tại Việt Nam đang tăng trong bối cảnh mở rộng quan hệ thương mại với các nước Mỹ Latinh. "
            "Phiên dịch viên tiếng Tây Ban Nha cần nắm rõ sự khác biệt giữa tiếng Tây Ban Nha Châu Âu và các phương ngữ Mỹ Latinh. "
            "Tại VietTranslate, bạn có thể tìm phiên dịch viên tiếng Tây Ban Nha phù hợp với thị trường mục tiêu của mình."
        ),
        "faq": [
            {
                "q": "Giá thuê phiên dịch tiếng Tây Ban Nha là bao nhiêu?",
                "a": "Mức giá tham khảo từ 50.000đ, tùy theo phương ngữ, loại hình và thời lượng phiên dịch.",
            },
            {
                "q": "Phiên dịch tiếng Tây Ban Nha cần chứng chỉ gì?",
                "a": "Phiên dịch viên tiếng Tây Ban Nha thường có DELE B2 trở lên. Một số có bằng cử nhân tiếng Tây Ban Nha hoặc SIELE.",
            },
            {
                "q": "Phiên dịch tiếng Tây Ban Nha phù hợp với những lĩnh vực nào?",
                "a": "Thương mại quốc tế, nông sản, năng lượng tái tạo, pháp lý, marketing, du lịch và nghiên cứu học thuật.",
            },
            {
                "q": "Làm thế nào để chọn phiên dịch viên tiếng Tây Ban Nha?",
                "a": "Xác định phương ngữ (Châu Âu hay Mỹ Latinh), xem chứng chỉ DELE, kinh nghiệm trong ngành và đánh giá khách hàng.",
            },
        ],
    },
}

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Bật Secure cookie nếu đang chạy trên HTTPS (Vercel, Render, hoặc bất kỳ môi trường có HTTPS=1)
_is_https_env = bool(
    os.environ.get('VERCEL') or
    os.environ.get('RENDER') or        # Render.com tự set RENDER=true
    os.environ.get('HTTPS') or
    os.environ.get('FORCE_HTTPS')
)
app.config['SESSION_COOKIE_SECURE'] = _is_https_env
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

basedir = os.path.abspath(os.path.dirname(__file__))

# ─── DATABASE URL RESOLUTION ───────────────────────────────────────────────────
import sys

database_url = os.getenv("DATABASE_URL")
_is_memory_db = False  # flag: True nếu đang dùng :memory: (Vercel demo mode)

if database_url:
    # Fix Heroku/Render PostgreSQL URL scheme
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    print(f"[DB] Sử dụng PostgreSQL (DATABASE_URL)", file=sys.stderr)
else:
    if os.environ.get('VERCEL') == '1':
        # Vercel: filesystem ephemeral — phải dùng MONGO_URI hoặc DATABASE_URL
        # Nếu không có, fallback sang :memory: với cảnh báo rõ ràng
        if not os.getenv("MONGO_URI"):
            print("[DB WARNING] Chạy trên Vercel nhưng MONGO_URI và DATABASE_URL đều chưa được cấu hình!", file=sys.stderr)
            print("[DB WARNING] Dữ liệu sẽ MẤT sau mỗi request do SQLite :memory: không lưu trữ!", file=sys.stderr)
        database_url = 'sqlite:///:memory:'
        _is_memory_db = True
    elif os.environ.get('RENDER'):
        # Chạy trên Render nhưng không có DATABASE_URL
        print("[DB WARNING] Chạy trên Render nhưng DATABASE_URL chưa được cấu hình!", file=sys.stderr)
        print("[DB WARNING] Hãy vào Render Dashboard → Environment → thêm DATABASE_URL hoặc MONGO_URI", file=sys.stderr)
        # Vẫn dùng SQLite nhưng đây là ephemeral trên Render!
        database_url = 'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')
        print("[DB WARNING] Render filesystem là ephemeral — dữ liệu sẽ mất khi redeploy!", file=sys.stderr)
    else:
        # Local development: dùng SQLite file cục bộ
        db_path = os.path.join(basedir, 'instance', 'database.db')
        database_url = 'sqlite:///' + db_path
        print(f"[DB] Sử dụng SQLite cục bộ: {db_path}", file=sys.stderr)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url

# Pool config cho SQLite (cả local và :memory:)
if 'sqlite' in database_url:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': StaticPool,
        'connect_args': {'check_same_thread': False},
    }

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join('static', 'uploads')
if os.environ.get('VERCEL') == '1' or _is_memory_db:
    UPLOAD_FOLDER = '/tmp'
else:
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except OSError:
        UPLOAD_FOLDER = '/tmp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'zip', 'rar', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)

# ─── DATABASE INITIALIZATION ───────────────────────────────────────────────────

def _init_db():
    """Tạo bảng nếu chưa tồn tại và nạp seed data DUY NHẤT khi DB trống.
    
    QUAN TRỌNG:
    - KHÔNG bao giờ drop_all() ở đây.
    - KHÔNG chạy seed nếu đã có user (idempotent).
    - Bắt lỗi IntegrityError riêng để tránh crash khi có race condition.
    """
    try:
        db.create_all()
    except Exception as e:
        print(f"[DB] db.create_all() error: {e}", file=sys.stderr)
        return

    try:
        user_count = db.session.execute(db.select(db.func.count()).select_from(User)).scalar()
    except Exception as e:
        print(f"[DB] Cannot count users: {e}", file=sys.stderr)
        user_count = 1  # Giả định đã có data, không seed

    if user_count == 0:
        # Chỉ seed khi DB thực sự trống
        try:
            from seed_data import seed_data as _run_seed
            _run_seed()
            print(f"[SEED] Seed hoàn thành. Users={User.query.count()}, Profiles={TranslatorProfile.query.count()}", file=sys.stderr)
        except Exception as e:
            # Không để seed failure crash app — user có thể tự đăng ký
            db.session.rollback()
            print(f"[SEED ERROR] Seed thất bại (bỏ qua): {e}", file=sys.stderr)
    else:
        print(f"[DB] Database sẵn sàng. Users={user_count}", file=sys.stderr)

# Chạy _init_db() một lần khi module được import
try:
    with app.app_context():
        _init_db()
except Exception as e:
    print(f"[DB INIT ERROR] {e}", file=sys.stderr)

# Trên Vercel, mỗi serverless invocation có thể là process mới;
# _db_ready flag giúp tránh re-init trong cùng 1 process.
_db_ready = False

@app.before_request
def _ensure_db():
    """Chạy _init_db() một lần duy nhất cho mỗi process.
    Trên Vercel/serverless: mỗi cold-start là process mới,
    nên sẽ chạy 1 lần đầu tiên của process đó.
    KHAI BÁO này không gây re-seed nếu DB có dữ liệu (điều kiện user_count == 0).
    """
    global _db_ready
    if not _db_ready:
        try:
            _init_db()
        except Exception as e:
            print(f"[DB before_request ERROR] {e}", file=sys.stderr)
        _db_ready = True


# ─── DECORATORS ────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        uid = session['user_id']
        # MongoDB users: check is_admin từ session (đã lưu khi login)
        if isinstance(uid, str) and uid.startswith('mongo:'):
            if not session.get('is_admin', False):
                flash('Bạn không có quyền truy cập trang này.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        # SQLite users
        try:
            user = User.query.get(uid)
        except SQLAlchemyError:
            user = None
        if not user or not user.is_admin:
            flash('Bạn không có quyền truy cập trang này.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


@app.template_filter('format_date_vn')
def format_date_vn(val):
    if not val:
        return ''
    if hasattr(val, 'strftime'):
        return val.strftime('%d/%m/%Y')
    if isinstance(val, str):
        try:
            parts = val.split(' to ')
            if len(parts) == 2:
                d1 = datetime.strptime(parts[0].strip(), '%Y-%m-%d').strftime('%d/%m/%Y')
                d2 = datetime.strptime(parts[1].strip(), '%Y-%m-%d').strftime('%d/%m/%Y')
                return f'{d1} – {d2}'
            return datetime.strptime(val.strip(), '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            return val
    return str(val)

class SimpleMongoUser:
    """Wrapper nhẹ để templates có thể dùng current_user.name, .role, v.v. với MongoDB user."""
    def __init__(self, data: dict):
        self.id = f"mongo:{data['_id']}"
        self.name = data.get('name', '')
        self.email = data.get('email', '')
        self.role = data.get('role', '')
        self.phone = data.get('phone', '')
        self.is_admin = data.get('is_admin', False)
        self.is_active = data.get('is_active', True)
        self.profile = None  # Không dùng SQLAlchemy relationship


def get_current_user():
    """Trả về User object của người đang đăng nhập từ session hiện tại.
    KHÔNG dùng User.query.first(), ID mặc định, hoặc dữ liệu hard-code.
    Trả về None nếu chưa đăng nhập hoặc user không còn tồn tại.
    """
    uid = session.get('user_id')
    if not uid:
        return None
    if isinstance(uid, str) and uid.startswith('mongo:'):
        mongo_id = uid[len('mongo:'):]
        mongo_data = mongo_find_user_by_id(mongo_id)
        return SimpleMongoUser(mongo_data) if mongo_data else None
    try:
        return User.query.get(uid)
    except SQLAlchemyError as e:
        print(f"[get_current_user SQLError] {e}")
        return None


@app.context_processor
def inject_globals():
    user = None
    uid = session.get('user_id')
    if uid:
        try:
            if isinstance(uid, str) and uid.startswith('mongo:'):
                # MongoDB user: dựng dữ liệu đã lưu trong session (tránh query lại)
                mongo_id = uid[len('mongo:'):]
                mongo_data = mongo_find_user_by_id(mongo_id)
                if mongo_data:
                    user = SimpleMongoUser(mongo_data)
                else:
                    session.pop('user_id', None)
            else:
                user = User.query.get(uid)
                if not user:
                    session.pop('user_id', None)
        except SQLAlchemyError as e:
            print(f"[AUTH SQL GLOBALS ERROR] {e}")
            # Do not pop session on transient DB locks to prevent random logout
        except Exception as e:
            print(f"[AUTH GLOBALS ERROR] {e}")
    current_lang = session.get('lang') or request.cookies.get('lang') or 'vi'
    if current_lang not in ('vi', 'en'):
        current_lang = 'vi'
    return dict(
        current_user=user,
        LANGUAGES=get_localized_languages(current_lang),
        current_lang=current_lang,
        t=lambda key, **kwargs: t_lookup(key, current_lang, **kwargs)
    )

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in ('vi', 'en'):
        session['lang'] = lang
        session.modified = True
    referer = request.referrer
    # Prevent open redirect vulnerabilities
    if referer and request.host in referer:
        resp = redirect(referer)
    else:
        resp = redirect(url_for('index'))
    if lang in ('vi', 'en'):
        resp.set_cookie('lang', lang, max_age=365*24*3600, samesite='Lax')
    return resp

# ─── PUBLIC ROUTES ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    top_translators = TranslatorProfile.query.filter_by(is_verified=True).order_by(
        TranslatorProfile.rating.desc()).limit(4).all()
    if not top_translators:
        top_translators = TranslatorProfile.query.order_by(TranslatorProfile.rating.desc()).limit(4).all()
    latest_jobs = Job.query.filter_by(status='open', is_flagged=False).order_by(Job.created_at.desc()).limit(4).all()
    return render_template('index.html', top_translators=top_translators, latest_jobs=latest_jobs)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/payment-info')
def payment_info():
    return render_template('payment_info.html')

# ─── AUTH ──────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # ── Thử MongoDB trước (khi deploy trên Vercel) ──
            if MONGO_URI:
                mongo_user = mongo_find_user_by_email(email)
                if mongo_user:
                    if not mongo_user.get('is_active', True):
                        flash('Tài khoản đã bị khoá.', 'error')
                        return render_template('login.html', email=email)
                    if check_password_hash(mongo_user['password_hash'], password):
                        # Lưu mongo _id dạng string vào session với prefix để phân biệt
                        session.clear()
                        session.permanent = True
                        session['user_id'] = f"mongo:{mongo_user['_id']}"
                        session['user_name'] = mongo_user.get('name', '')
                        session['user_role'] = mongo_user.get('role', '')
                        session['is_admin'] = mongo_user.get('is_admin', False)
                        flash('Đăng nhập thành công!', 'success')
                        if mongo_user.get('is_admin'):
                            return redirect(url_for('admin_dashboard'))
                        return redirect(url_for('index'))
                    else:
                        flash('Mật khẩu không đúng.', 'error')
                        return render_template('login.html', email=email)
                # Nếu không tìm thấy trong MongoDB thì fallback xuống SQLite bên dưới
    
            # ── Fallback: SQLite / SQLAlchemy (khi chạy local) ──
            user = User.query.filter_by(email=email).first()
            if user:
                if not user.is_active:
                    flash('Tài khoản đã bị khoá.', 'error')
                    return render_template('login.html', email=email)
                if check_password_hash(user.password_hash, password):
                    session.clear()
                    session.permanent = True
                    session['user_id'] = user.id
                    flash('Đăng nhập thành công!', 'success')
                    if user.is_admin:
                        return redirect(url_for('admin_dashboard'))
                    return redirect(url_for('index'))
                else:
                    flash('Mật khẩu không đúng.', 'error')
                    return render_template('login.html', email=email)
            else:
                flash('Tài khoản không tồn tại hoặc email không đúng.', 'error')
                return render_template('login.html', email=email)
        except SQLAlchemyError as e:
            print(f"[AUTH SQL ERROR] {e}")
            flash('Hệ thống đang quá tải hoặc cơ sở dữ liệu bị khoá. Vui lòng thử lại sau.', 'error')
            return render_template('login.html', email=email)
        except Exception as e:
            print(f"[AUTH ERROR] {e}")
            flash('Lỗi kết nối cơ sở dữ liệu. Vui lòng thử lại sau.', 'error')
            return render_template('login.html', email=email)

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        role = request.form.get('role')

        if role not in ('hirer', 'translator'):
            flash('Vai trò không hợp lệ.', 'error')
            return redirect(url_for('register'))

        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Email không hợp lệ. Vui lòng nhập đúng định dạng.', 'error')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)

        # ── Dùng MongoDB khi MONGO_URI được cấu hình (Vercel) ──
        if MONGO_URI:
            success, message = mongo_register_user(
                username=name,
                email=email,
                hashed_password=hashed_pw,
                phone=phone,
                role=role,
            )
            if success:
                flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
                return redirect(url_for('login'))
            else:
                flash(message, 'error')
                return redirect(url_for('register'))

        # ── Fallback: SQLite / SQLAlchemy (khi chạy local) ──
        if User.query.filter_by(email=email).first():
            flash('Tài khoản với email này đã tồn tại. Vui lòng đăng nhập.', 'error')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email,
                        password_hash=hashed_pw,
                        phone=phone, role=role)
        db.session.add(new_user)
        db.session.commit()

        if role == 'translator':
            profile = TranslatorProfile(user_id=new_user.id)
            db.session.add(profile)
            db.session.commit()

        flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Đã đăng xuất.', 'success')
    return redirect(url_for('index'))

# ─── ACCOUNT ───────────────────────────────────────────────────────────────────

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account_profile():
    uid = session['user_id']

    # MongoDB user
    if isinstance(uid, str) and uid.startswith('mongo:'):
        mongo_id = uid[len('mongo:'):]
        mongo_data = mongo_find_user_by_id(mongo_id)
        if not mongo_data:
            flash('Không tìm thấy tài khoản.', 'error')
            return redirect(url_for('index'))
        user = SimpleMongoUser(mongo_data)

        if request.method == 'POST':
            action = request.form.get('action', 'basic')
            col = get_mongo_users()
            if col is None:
                flash('MongoDB chưa được cấu hình.', 'error')
                return redirect(url_for('account_profile'))

            from bson import ObjectId
            if action == 'basic':
                col.update_one(
                    {"_id": ObjectId(mongo_id)},
                    {"$set": {
                        "name": request.form.get('name', user.name).strip(),
                        "phone": request.form.get('phone', user.phone or '').strip(),
                    }}
                )
                session['user_name'] = request.form.get('name', user.name).strip()
                flash('Đã cập nhật thông tin cơ bản!', 'success')

            elif action == 'change_password':
                old_pw = request.form.get('old_password', '')
                new_pw = request.form.get('new_password', '')
                confirm_pw = request.form.get('confirm_password', '')
                if not check_password_hash(mongo_data['password_hash'], old_pw):
                    flash('Mật khẩu hiện tại không đúng.', 'error')
                elif new_pw != confirm_pw:
                    flash('Mật khẩu mới không khớp.', 'error')
                elif len(new_pw) < 6:
                    flash('Mật khẩu mới phải ít nhất 6 ký tự.', 'error')
                else:
                    col.update_one(
                        {"_id": ObjectId(mongo_id)},
                        {"$set": {"password_hash": generate_password_hash(new_pw)}}
                    )
                    flash('Đã đổi mật khẩu thành công!', 'success')

            return redirect(url_for('account_profile'))
        return render_template('account_profile.html', user=user)

    # SQLite user
    user = User.query.get(uid)
    if not user:
        flash('Không tìm thấy tài khoản.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        action = request.form.get('action', 'basic')

        if action == 'basic':
            user.name = request.form.get('name', user.name).strip()
            user.phone = request.form.get('phone', user.phone or '').strip()
            db.session.commit()
            flash('Đã cập nhật thông tin cơ bản!', 'success')

        elif action == 'translator_profile' and user.role == 'translator':
            profile = user.profile
            if not profile:
                profile = TranslatorProfile(user_id=user.id)
                db.session.add(profile)
            profile.title = request.form.get('title', '').strip()
            profile.bio = request.form.get('bio', '').strip()
            profile.languages = request.form.get('languages', '').strip()
            profile.badges = request.form.get('badges', '').strip()
            profile.response_time = request.form.get('response_time', '< 1 giờ').strip()
            db.session.commit()
            flash('Đã cập nhật hồ sơ phiên dịch viên!', 'success')

        elif action == 'translator_preference' and user.role == 'translator':
            pref = user.preference
            if not pref:
                pref = TranslatorPreference(translator_id=user.id)
                db.session.add(pref)
            
            pref.languages = ",".join(request.form.getlist('languages'))
            pref.service_types = ",".join(request.form.getlist('service_types'))
            pref.notify_new_jobs = 'notify_new_jobs' in request.form
            pref.notify_messages = 'notify_messages' in request.form
            pref.notify_contracts = 'notify_contracts' in request.form
            pref.notify_reviews = 'notify_reviews' in request.form
            
            db.session.commit()
            flash('Đã cập nhật cài đặt nhận việc!', 'success')

        elif action == 'change_password':
            old_pw = request.form.get('old_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if not check_password_hash(user.password_hash, old_pw):
                flash('Mật khẩu hiện tại không đúng.', 'error')
            elif new_pw != confirm_pw:
                flash('Mật khẩu mới không khớp.', 'error')
            elif len(new_pw) < 6:
                flash('Mật khẩu mới phải ít nhất 6 ký tự.', 'error')
            else:
                user.password_hash = generate_password_hash(new_pw)
                db.session.commit()
                flash('Đã đổi mật khẩu thành công!', 'success')

        return redirect(url_for('account_profile'))
    return render_template('account_profile.html', user=user, LANGUAGES=LANGUAGES)

def get_translator_preferences(user_id):
    return TranslatorPreference.query.filter_by(translator_id=user_id).first()

def translator_accepts_job(translator, job):
    if translator.role != 'translator' or not translator.is_active:
        return False
        
    pref = translator.preference
    if not pref:
        return True # Default to accepting if no preference set
        
    # Check language
    pref_langs = [l.strip() for l in pref.languages.split(',')] if pref.languages else []
    if pref_langs and job.source_lang not in pref_langs and job.target_lang not in pref_langs:
        return False
        
    # Check category
    pref_services = [s.strip() for s in pref.service_types.split(',')] if pref.service_types else []
    
    # map job's new format or old format to the preference options
    # The form options are: 'Dịch thuật', 'Phiên dịch', 'Hội họp', 'Kinh doanh', 'Du lịch', 'Sự kiện', 'Khác'
    job_group = job.display_category_group
    job_type = job.display_service_type
    
    job_service_matches = []
    if job_group == 'translation':
        job_service_matches.append('Dịch thuật')
    else:
        if job_type in ['conference', 'meeting', 'escort']:
            job_service_matches.append('Phiên dịch')
        if job_type in ['meeting']:
            job_service_matches.append('Hội họp')
        if job_type in ['business']:
            job_service_matches.append('Kinh doanh')
        if job_type in ['travel']:
            job_service_matches.append('Du lịch')
        if job_type in ['event']:
            job_service_matches.append('Sự kiện')
        if not job_service_matches or job_type == 'other_interpretation':
            job_service_matches.append('Khác')
            
    if pref_services and not any(s in pref_services for s in job_service_matches):
        return False
        
    return True


def get_job_applicant_count(job_id):
    return Proposal.query.filter_by(job_id=job_id).count()


@app.route('/account/history')
@login_required
def account_history():
    user = get_current_user()
    if not user:
        flash('Không tìm thấy tài khoản.', 'error')
        return redirect(url_for('index'))
    if user.role == 'hirer':
        contracts = Contract.query.filter_by(hirer_id=user.id).order_by(Contract.created_at.desc()).all()
    else:
        contracts = Contract.query.filter_by(translator_id=user.id).order_by(Contract.created_at.desc()).all()
    return render_template('account_history.html', user=user, contracts=contracts)

# ─── FLOW 1: TÌM PHIÊN DỊCH VIÊN ──────────────────────────────────────────────

@app.route('/translator')
@app.route('/translators')
def translator_list():
    lang = request.args.get('lang', '')
    rating_filter = request.args.get('rating', '')
    page = request.args.get('page', 1, type=int)
    per_page = 9

    query = TranslatorProfile.query
    if lang:
        safe_lang = lang.replace('%', r'\%').replace('_', r'\_')
        query = query.filter(TranslatorProfile.languages.ilike(f'%{safe_lang}%'))
    if rating_filter:
        query = query.filter(TranslatorProfile.rating >= float(rating_filter))

    pagination = query.order_by(TranslatorProfile.rating.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('translator_list.html', profiles=pagination.items,
                           pagination=pagination, lang_filter=lang, LANGUAGES=LANGUAGES)

@app.route('/api/health')
def api_health():
    user_count = User.query.count()
    profile_count = TranslatorProfile.query.count()
    service_count = Service.query.count()
    return jsonify({
        'db_uri': app.config['SQLALCHEMY_DATABASE_URI'],
        'vercel': os.environ.get('VERCEL', '0'),
        'users': user_count,
        'profiles': profile_count,
        'services': service_count,
    })

@app.route('/api/translators')
def api_translators():
    """JSON API cho client-side filtering realtime."""
    profiles = TranslatorProfile.query.order_by(TranslatorProfile.rating.desc()).all()
    data = []
    for p in profiles:
        # Lấy giá thấp nhất từ services
        min_price = None
        if p.services:
            prices = [s.basic_price for s in p.services if s.basic_price]
            min_price = min(prices) if prices else None

        # Lấy thời gian hoàn thành thấp nhất từ services (parse số ngày)
        min_days = None
        if p.services:
            for s in p.services:
                for field in [s.basic_delivery, s.standard_delivery, s.premium_delivery]:
                    if field:
                        nums = re.findall(r'\d+', field)
                        if nums:
                            d = int(nums[0])
                            if min_days is None or d < min_days:
                                min_days = d

        # Tách languages và badges thành list
        langs = [l.strip() for l in (p.languages or '').split(',') if l.strip()]
        badges = [b.strip() for b in (p.badges or '').split(',') if b.strip()]

        data.append({
            'id': p.id,
            'user_id': p.user_id,
            'name': p.user.name,
            'initial': p.user.name[0].upper() if p.user.name else '?',
            'title': p.title or '',
            'languages': langs,
            'badges': badges,
            'rating': float(p.rating or 0),
            'total_reviews': p.total_reviews or 0,
            'min_price': min_price,
            'completion_days': min_days,
            'is_verified': p.is_verified,
            'profile_url': url_for('translator_profile', profile_id=p.id),
            'chat_url': url_for('direct_chat', translator_user_id=p.user_id),
        })
    return jsonify(data)

@app.route('/translator/<int:profile_id>')
def translator_profile(profile_id):
    profile = TranslatorProfile.query.get_or_404(profile_id)
    # Reviews received by this translator
    reviews = Review.query.filter_by(reviewee_id=profile.user_id).order_by(Review.created_at.desc()).limit(10).all()
    return render_template('translator_profile.html', profile=profile, reviews=reviews)

@app.route('/translator/<string:lang_slug>')
def translator_language(lang_slug):
    """SEO landing page theo từng ngôn ngữ."""
    lang_config = LANGUAGE_PAGES.get(lang_slug)
    if not lang_config:
        abort(404)
    # Các ngôn ngữ khác để internal linking
    other_languages = {k: v for k, v in LANGUAGE_PAGES.items() if k != lang_slug}
    return render_template(
        'translator_language.html',
        lang=lang_config,
        other_languages=other_languages,
    )

@app.route('/sitemap.xml')
def sitemap():
    """Sitemap XML chứa tất cả language landing pages."""
    base_url = request.url_root.rstrip('/')
    urls = [
        {'loc': f"{base_url}/translator", 'priority': '0.9'},
    ]
    for slug in LANGUAGE_PAGES:
        urls.append({'loc': f"{base_url}/translator/{slug}", 'priority': '0.8'})
    urls += [
        {'loc': f"{base_url}/", 'priority': '1.0'},
        {'loc': f"{base_url}/jobs", 'priority': '0.7'},
        {'loc': f"{base_url}/about", 'priority': '0.5'},
    ]
    xml = render_template('sitemap.xml', urls=urls)
    return Response(xml, mimetype='application/xml')



# ─── DIRECT CHAT ───────────────────────────────────────────────────────────────

@app.route('/chat/<int:translator_user_id>')
@login_required
def direct_chat(translator_user_id):
    if session['user_id'] == translator_user_id:
        return redirect(url_for('index'))
    translator = User.query.get_or_404(translator_user_id)
    return render_template('chat.html', other_user=translator)

@app.route('/api/direct-messages/<int:other_user_id>')
@login_required
def get_direct_messages(other_user_id):
    me = session['user_id']
    msgs = DirectMessage.query.filter(
        db.or_(
            db.and_(DirectMessage.sender_id == me, DirectMessage.receiver_id == other_user_id),
            db.and_(DirectMessage.sender_id == other_user_id, DirectMessage.receiver_id == me)
        )
    ).order_by(DirectMessage.created_at.asc()).all()

    # Mark messages from the other user as read
    unread = [m for m in msgs if m.receiver_id == me and not m.is_read]
    for m in unread:
        m.is_read = True
    if unread:
        db.session.commit()

    return jsonify([{
        'id': m.id, 'sender_id': m.sender_id, 'sender_name': m.sender.name,
        'content': m.content, 'time': m.created_at.strftime('%H:%M %d/%m')
    } for m in msgs])

@app.route('/api/direct-messages/<int:other_user_id>', methods=['POST'])
@login_required
def send_direct_message(other_user_id):
    content = request.json.get('content', '').strip()
    me = session['user_id']
    
    if not content or other_user_id == me:
        return jsonify({'status': 'error'}), 400
        
    receiver = User.query.get(other_user_id)
    if not receiver:
        return jsonify({'status': 'error'}), 400
        
    msg = DirectMessage(sender_id=me, receiver_id=other_user_id, content=content)
    db.session.add(msg)

    # Notify receiver
    sender = User.query.get(me)
    if sender:
        from services.notifications import should_notify
        if should_notify(receiver, 'NEW_MESSAGE'):
            try:
                create_notification(
                    user_id=other_user_id,
                    notification_type='NEW_MESSAGE',
                    title='Bạn có tin nhắn mới',
                    message=f'{sender.name} đã gửi cho bạn một tin nhắn.',
                    url=url_for('direct_chat', translator_user_id=me)
                )
            except Exception as e:
                print(f"Error creating notification: {e}")
                pass

    db.session.commit()
    return jsonify({'status': 'ok'})


# ─── MESSAGES PAGE ─────────────────────────────────────────────────────────────

@app.route('/messages')
@login_required
def messages_page():
    return render_template('messages.html')

@app.route('/api/messages/conversations')
@login_required
def api_conversations():
    """Return all conversations (DirectMessage + Contract Message) for current user."""
    me = session['user_id']
    conversations = {}  # keyed by other_user_id

    # ── 1. DirectMessage conversations ─────────────────────────────────────────
    all_dm = DirectMessage.query.filter(
        db.or_(DirectMessage.sender_id == me, DirectMessage.receiver_id == me)
    ).order_by(DirectMessage.created_at.desc()).all()

    for dm in all_dm:
        other_id = dm.receiver_id if dm.sender_id == me else dm.sender_id
        if other_id not in conversations:
            other = User.query.get(other_id)
            if not other:
                continue
            conversations[other_id] = {
                'type': 'direct',
                'other_user_id': other_id,
                'other_name': other.name,
                'other_initial': other.name[0].upper(),
                'last_message': dm.content,
                'last_time': dm.created_at,
                'last_time_str': dm.created_at.strftime('%H:%M %d/%m'),
                'unread_count': 0,
                'url': url_for('direct_chat', translator_user_id=other_id),
            }
        # Count unread DMs from that person
        if dm.receiver_id == me and not dm.is_read:
            conversations[other_id]['unread_count'] = conversations[other_id].get('unread_count', 0) + 1

    # ── 2. Contract Message conversations ──────────────────────────────────────
    my_contracts = Contract.query.filter(
        db.or_(Contract.hirer_id == me, Contract.translator_id == me)
    ).all()

    for contract in my_contracts:
        other_id = contract.translator_id if contract.hirer_id == me else contract.hirer_id
        last_msg = Message.query.filter_by(contract_id=contract.id).order_by(Message.created_at.desc()).first()
        if not last_msg:
            continue

        other = User.query.get(other_id)
        if not other:
            continue

        # Use max(last_time) if this person already exists from DM
        if other_id not in conversations or last_msg.created_at > conversations[other_id]['last_time']:
            unread = Message.query.filter_by(contract_id=contract.id, is_read=False).filter(
                Message.sender_id != me
            ).count()
            conversations[other_id] = {
                'type': 'contract',
                'other_user_id': other_id,
                'other_name': other.name,
                'other_initial': other.name[0].upper(),
                'last_message': last_msg.content,
                'last_time': last_msg.created_at,
                'last_time_str': last_msg.created_at.strftime('%H:%M %d/%m'),
                'unread_count': unread,
                'url': url_for('transaction_detail', contract_id=contract.id),
                'contract_id': contract.id,
            }

    # Sort by last_time descending, strip datetime object before json
    sorted_convs = sorted(conversations.values(), key=lambda x: x['last_time'], reverse=True)
    for c in sorted_convs:
        del c['last_time']

    return jsonify(sorted_convs)

@app.route('/api/messages/unread-count')
@login_required
def api_messages_unread_count():
    """Total unread messages across DMs + Contract messages."""
    me = session['user_id']

    dm_unread = DirectMessage.query.filter_by(receiver_id=me, is_read=False).count()

    my_contract_ids = [c.id for c in Contract.query.filter(
        db.or_(Contract.hirer_id == me, Contract.translator_id == me)
    ).all()]
    contract_unread = 0
    if my_contract_ids:
        contract_unread = Message.query.filter(
            Message.contract_id.in_(my_contract_ids),
            Message.sender_id != me,
            Message.is_read == False
        ).count()

    return jsonify({'count': dm_unread + contract_unread})

# ─── DIRECT BOOKING ────────────────────────────────────────────────────────────

@app.route('/book/<int:service_id>', methods=['GET', 'POST'])
@login_required
def book_service(service_id):
    service = Service.query.get_or_404(service_id)
    tier = request.args.get('tier', 'basic')
    prices = {'basic': service.basic_price, 'standard': service.standard_price,
              'premium': service.premium_price}
    price = prices.get(tier, service.basic_price)

    current_user = get_current_user()
    if not current_user:
        flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
        return redirect(url_for('login'))
    translator = service.profile.user if service.profile else None

    if not translator or getattr(translator, 'role', '') != 'translator' or not getattr(translator, 'is_active', True):
        flash('Phiên dịch viên này hiện không hoạt động.', 'error')
        return redirect(url_for('translators'))

    if current_user.id == translator.id:
        flash('Bạn không thể tự thuê chính mình.', 'error')
        return redirect(url_for('service_detail', service_id=service.id))

    if request.method == 'POST':
        scheduled_date_str = request.form.get('scheduled_date', '')
        time_start_str = request.form.get('time_start', '')
        time_end_str = request.form.get('time_end', '')
        
        from services.booking import create_contract_booking, BookingConflictError, BookingValidationError
        from services.schedule import ScheduleCheckError
        
        try:
            contract = create_contract_booking(
                hirer_id=session['user_id'],
                translator_id=translator.id,
                agreed_price=int(request.form.get('price', price)),
                scheduled_date=scheduled_date_str,
                start_time=time_start_str,
                end_time=time_end_str,
                location=request.form.get('location', ''),
                service_id=service.id
            )
            flash('Đặt dịch vụ thành công! Vui lòng thanh toán Escrow để bắt đầu.', 'success')
            return redirect(url_for('payment_mockup', contract_id=contract.id))
            
        except (BookingConflictError, BookingValidationError, ScheduleCheckError) as e:
            flash(str(e), 'error')
            return redirect(url_for('book_service', service_id=service.id, tier=tier))
            
        except Exception as e:
            import logging
            logging.exception('Error in book_service: %s', e)
            flash('Đã xảy ra lỗi hệ thống, vui lòng thử lại sau.', 'error')
            return redirect(url_for('book_service', service_id=service.id, tier=tier))

    # Extract fixed_days from delivery string
    delivery_str = service.basic_delivery if tier == 'basic' else (service.standard_delivery if tier == 'standard' else service.premium_delivery)
    fixed_days = None
    if delivery_str:
        s = delivery_str.lower()
        if 'nửa ngày' in s or 'trong ngày' in s:
            fixed_days = 1
        elif 'theo' not in s:
            match = re.search(r'(\d+)', s)
            if match:
                fixed_days = int(match.group(1))

    return render_template('book_service.html', service=service, tier=tier, price=price, fixed_days=fixed_days)

# ─── FLOW 2: JOB BOARD ─────────────────────────────────────────────────────────

@app.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    user = get_current_user()
    if not user or user.role != 'hirer':
        flash('Chỉ Khách hàng mới có thể đăng công việc.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        deadline_str = request.form.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        job = Job(
            hirer_id=session['user_id'],
            title=request.form.get('title'),
            description=request.form.get('description'),
            category=request.form.get('category'),
            category_group=request.form.get('category_group'),
            service_type=request.form.get('service_type'),
            source_lang=request.form.get('source_lang'),
            target_lang=request.form.get('target_lang'),
            budget_type=request.form.get('budget_type'),
            budget_min=int(request.form.get('budget_min') or 0),
            budget_max=int(request.form.get('budget_max') or 0) or None,
            event_date=request.form.get('event_date', ''),
            event_time_start=request.form.get('event_time_start', ''),
            event_time_end=request.form.get('event_time_end', ''),
            event_location=request.form.get('event_location', ''),
            deadline=deadline
        )
        db.session.add(job)
        db.session.commit()

        # Notify matching translators (safe, won't block job creation if fails)
        from services.matching import notify_matching_translators_for_new_job
        notify_matching_translators_for_new_job(job)

        flash('Đã đăng yêu cầu thành công!', 'success')
        return redirect(url_for('job_detail', job_id=job.id))
    return render_template('post_job.html', LANGUAGES=LANGUAGES)

@app.route('/jobs')
def job_list():
    lang = request.args.get('lang', '')
    budget = request.args.get('budget', '')
    sort = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = Job.query.filter_by(status='open', is_flagged=False)
    if lang:
        safe_lang = lang.replace('%', r'\%').replace('_', r'\_')
        query = query.filter(db.or_(Job.source_lang.ilike(f'%{safe_lang}%'), Job.target_lang.ilike(f'%{safe_lang}%')))

    if sort == 'budget_desc':
        query = query.order_by(Job.budget_min.desc())
    else:
        query = query.order_by(Job.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('job_list.html', jobs=pagination.items, pagination=pagination,
                           lang_filter=lang, LANGUAGES=LANGUAGES)

@app.route('/job/<int:job_id>', methods=['GET', 'POST'])
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    if request.method == 'POST':
        # ── 1. Login & Role guard ─────────────────────────────────────────────
        user = get_current_user()
        if not user:
            flash('Vui lòng đăng nhập để gửi đề xuất.', 'warning')
            return redirect(url_for('login'))
        if user.role != 'translator':
            flash('Chỉ Phiên dịch viên mới có thể ứng tuyển.', 'error')
            return redirect(url_for('job_detail', job_id=job.id))

        # ── 2. Duplicate proposal guard ───────────────────────────────────────
        existing_proposal = Proposal.query.filter_by(
            job_id=job.id, translator_id=session['user_id']
        ).first()
        if existing_proposal:
            flash('Bạn đã gửi đề xuất cho công việc này rồi.', 'warning')
            return redirect(url_for('job_detail', job_id=job.id))

        # ── 3. Schedule conflict check ────────────────────────────────────────
        from services.schedule import (
            parse_job_datetime, is_schedule_complete,
            check_translator_schedule_conflict, ScheduleCheckError
        )
        try:
            parsed = parse_job_datetime(job)
            if is_schedule_complete(parsed):
                result = check_translator_schedule_conflict(
                    translator_id=session['user_id'],
                    scheduled_date=parsed['date'],
                    start_time=parsed['start_time'],
                    end_time=parsed['end_time'],
                )
                if result['conflict']:
                    flash(
                        f'Bạn đã có lịch công việc khác trong khoảng thời gian này '
                        f'({result["start_time"]}–{result["end_time"]}). '
                        f'Vui lòng kiểm tra lịch của bạn.',
                        'error'
                    )
                    return render_template('job_detail.html', job=job, form_data=request.form)
        except ScheduleCheckError as e:
            flash(str(e), 'error')
            return render_template('job_detail.html', job=job, form_data=request.form)

        # ── 3.5. Time Estimate Parsing & Validation ───────────────────────────
        completion_type = request.form.get('completion_type')
        time_estimate_str = ""
        
        if completion_type == 'duration':
            val = request.form.get('estimated_duration_value')
            unit = request.form.get('estimated_duration_unit')
            if val:
                try:
                    val_int = int(val)
                    if val_int <= 0:
                        flash('Thời gian hoàn thành phải lớn hơn 0.', 'error')
                        return render_template('job_detail.html', job=job, form_data=request.form)
                    unit_str = "ngày" if unit == 'days' else "giờ"
                    time_estimate_str = f"{val_int} {unit_str}"
                except ValueError:
                    flash('Giá trị thời gian hoàn thành phải là một số.', 'error')
                    return render_template('job_detail.html', job=job, form_data=request.form)
        elif completion_type == 'deadline':
            date_val = request.form.get('estimated_completion_date')
            if date_val:
                try:
                    parsed_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                    if parsed_date < datetime.today().date():
                        flash('Ngày hoàn thành không được nằm trong quá khứ.', 'error')
                        return render_template('job_detail.html', job=job, form_data=request.form)
                    time_estimate_str = parsed_date.strftime('%d/%m/%Y')
                except ValueError:
                    flash('Định dạng ngày không hợp lệ.', 'error')
                    return render_template('job_detail.html', job=job, form_data=request.form)

        # ── 4. Create Proposal (unchanged logic) ──────────────────────────────
        proposal = Proposal(
            job_id=job.id,
            translator_id=session['user_id'],
            cover_letter=request.form.get('cover_letter'),
            price=int(request.form.get('price') or 0),
            time_estimate=time_estimate_str
        )
        db.session.add(proposal)
        db.session.flush()

        # Notify the hirer about new applicant (avoid duplicate for same proposal)
        from models import Notification
        existing_notif = Notification.query.filter_by(
            user_id=job.hirer_id, 
            type='JOB_APPLICATION', 
            related_proposal_id=proposal.id
        ).first()

        if not existing_notif:
            create_notification(
                user_id=job.hirer_id,
                notification_type='JOB_APPLICATION',
                title='Có ứng viên mới',
                message=f'Một phiên dịch viên vừa ứng tuyển vào công việc "{job.title}".',
                url=url_for('job_detail', job_id=job.id),
                related_job_id=job.id,
                related_proposal_id=proposal.id
            )
            
        db.session.commit()
        flash('Đề xuất của bạn đã được gửi!', 'success')
        return redirect(url_for('job_detail', job_id=job.id))
    return render_template('job_detail.html', job=job)


@app.route('/api/jobs/<int:job_id>/schedule-check', methods=['GET'])
@login_required
def api_schedule_check(job_id):
    """Frontend pre-check: returns whether the logged-in translator has a
    schedule conflict with this job's date/time.  Backend still re-validates
    at proposal submission — this is for UI feedback only.
    """
    from services.schedule import (
        parse_job_datetime, is_schedule_complete,
        check_translator_schedule_conflict,
    )
    job = Job.query.get_or_404(job_id)
    parsed = parse_job_datetime(job)

    if not is_schedule_complete(parsed):
        # Job has no fixed time → no conflict possible
        return jsonify({'available': True, 'reason': 'no_schedule'})

    result = check_translator_schedule_conflict(
        translator_id=session['user_id'],
        scheduled_date=parsed['date'],
        start_time=parsed['start_time'],
        end_time=parsed['end_time'],
    )

    if result['conflict']:
        return jsonify({
            'available': False,
            'conflict_start': result['start_time'],
            'conflict_end': result['end_time'],
            'message': result['message'],
        })
    return jsonify({'available': True})

# ─── CONTRACT / BUSINESS PROCESS ───────────────────────────────────────────────

@app.route('/accept-proposal/<int:proposal_id>', methods=['POST'])
@login_required
def accept_proposal(proposal_id):
    try:
        # Lock Proposal and Job to prevent concurrent accepts for the same job/proposal
        proposal = Proposal.query.with_for_update().get_or_404(proposal_id)
        job = Job.query.with_for_update().get(proposal.job_id)

        if not job or job.hirer_id != session['user_id']:
            flash('Không có quyền.', 'error')
            db.session.rollback()
            return redirect(url_for('index'))

        # Check Job open/active
        if job.status != 'open':
            flash('Công việc này không còn mở.', 'error')
            db.session.rollback()
            return redirect(url_for('job_detail', job_id=job.id))

        # Check Proposal pending
        if proposal.status != 'pending':
            flash('Đề xuất này đã được xử lý.', 'error')
            db.session.rollback()
            return redirect(url_for('job_detail', job_id=job.id))

        from services.booking import create_contract_booking, BookingConflictError, BookingValidationError
        from services.schedule import ScheduleCheckError
        
        try:
            contract = create_contract_booking(
                hirer_id=job.hirer_id,
                translator_id=proposal.translator_id,
                agreed_price=proposal.price,
                scheduled_date=job.event_date,
                start_time=job.event_time_start,
                end_time=job.event_time_end,
                location=job.event_location,
                job_id=job.id,
                proposal_id=proposal.id
            )
            flash('Đã chấp nhận đề xuất! Vui lòng thanh toán để bắt đầu.', 'success')
            return redirect(url_for('payment_mockup', contract_id=contract.id))
            
        except (BookingConflictError, BookingValidationError, ScheduleCheckError) as e:
            flash(str(e), 'error')
            return redirect(url_for('job_detail', job_id=job.id))

    except Exception as e:
        db.session.rollback()
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            raise
        import logging
        logging.error("Exception in accept_proposal for proposal %s: %s", proposal_id, e)
        flash('Đã xảy ra lỗi hệ thống, vui lòng thử lại sau.', 'error')
        return redirect(url_for('index'))

@app.route('/payment-mockup/<int:contract_id>', methods=['GET', 'POST'])
@login_required
def payment_mockup(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    from services.permissions import require_contract_access
    require_contract_access(session['user_id'], contract)

    platform_fee = int(contract.agreed_price * 0.10)
    translator_receives = contract.agreed_price - platform_fee
    if request.method == 'POST':
        contract.status = 'in_progress'
        db.session.commit()
        flash('Thanh toán thành công! Tiền đã được giữ trong Escrow an toàn.', 'success')
        return redirect(url_for('transaction_detail', contract_id=contract.id))
    return render_template('payment_mockup.html', contract=contract,
                           platform_fee=platform_fee, translator_receives=translator_receives)

@app.route('/transaction/<int:contract_id>', methods=['GET', 'POST'])
@login_required
def transaction_detail(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    from services.permissions import require_contract_access
    require_contract_access(session['user_id'], contract)

    if request.method == 'POST' and 'file' in request.files:
        if contract.status != 'in_progress':
            flash('Hợp đồng chưa ở trạng thái thực hiện.', 'error')
            return redirect(url_for('transaction_detail', contract_id=contract.id))

        if session['user_id'] != contract.translator_id:
            abort(403)

        file = request.files.get('file')
        if not file or file.filename == '':
            flash('Vui lòng chọn file.', 'error')
            return redirect(url_for('transaction_detail', contract_id=contract.id))

        if not allowed_file(file.filename):
            flash('Loại tệp không được hỗ trợ.', 'error')
            return redirect(url_for('transaction_detail', contract_id=contract.id))

        filename = secure_filename(file.filename)
        if not filename:
            flash('Tên file không hợp lệ.', 'error')
            return redirect(url_for('transaction_detail', contract_id=contract.id))

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            file.save(filepath)
        except Exception:
            flash('Lỗi khi tải file lên máy chủ.', 'error')
            return redirect(url_for('transaction_detail', contract_id=contract.id))

        try:
            deliverable = Deliverable(
                contract_id=contract.id,
                filename=filename,
                filepath=filename
            )
            message = Message(
                contract_id=contract.id,
                sender_id=session['user_id'],
                content=f'📎 Đã gửi tệp: {filename}'
            )

            db.session.add(deliverable)
            db.session.add(message)
            db.session.flush()

            from services.notifications import should_notify
            hirer = User.query.get(contract.hirer_id)
            if hirer and should_notify(hirer, 'NEW_MESSAGE'):
                create_notification(
                    user_id=contract.hirer_id,
                    notification_type='NEW_MESSAGE',
                    title='Bạn có tin nhắn mới',
                    message=f'{contract.translator.name} đã gửi cho bạn một tin nhắn trong hợp đồng.',
                    url=url_for('transaction_detail', contract_id=contract.id),
                    related_contract_id=contract.id
                )

            db.session.commit()
            flash('Đã gửi tài liệu thành công.', 'success')
        except Exception:
            db.session.rollback()
            flash('Lỗi hệ thống khi lưu tài liệu.', 'error')

        return redirect(url_for('transaction_detail', contract_id=contract.id))

    return render_template('transaction_detail.html', contract=contract)

@app.route('/approve-contract/<int:contract_id>', methods=['POST'])
@login_required
def approve_contract(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    from services.permissions import require_contract_access
    require_contract_access(session['user_id'], contract)
    if session['user_id'] == contract.hirer_id and contract.status == 'in_progress':
        contract.status = 'completed'
        if contract.job:
            contract.job.status = 'completed'
        prof = TranslatorProfile.query.filter_by(user_id=contract.translator_id).first()
        if prof:
            prof.total_jobs += 1
        db.session.commit()
        flash('Nghiệm thu thành công! Tiền Escrow đã được giải ngân.', 'success')
    return redirect(url_for('transaction_detail', contract_id=contract.id))

@app.route('/submit-review/<int:contract_id>', methods=['POST'])
@login_required
def submit_review(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    from services.permissions import require_contract_access
    require_contract_access(session['user_id'], contract)
    if contract.status == 'completed':
        try:
            rating = int(request.form.get('rating', 5))
        except ValueError:
            flash('Vui lòng chọn số sao đánh giá hợp lệ.', 'error')
            return redirect(url_for('transaction_detail', contract_id=contract.id))
        
        comment = request.form.get('comment', '')
        reviewer_id = session['user_id']
        reviewee_id = contract.translator_id if reviewer_id == contract.hirer_id else contract.hirer_id

        if reviewer_id == reviewee_id:
            flash('Bạn không thể tự đánh giá chính mình.', 'error')
            return redirect(url_for('transaction_detail', contract_id=contract.id))

        existing = Review.query.filter_by(contract_id=contract.id, reviewer_id=reviewer_id).first()
        is_edit = False
        old_rating = 0
        if existing:
            is_edit = True
            old_rating = existing.rating
            existing.rating = rating
            existing.comment = comment
            review = existing
        else:
            review = Review(contract_id=contract.id, reviewer_id=reviewer_id,
                            reviewee_id=reviewee_id, rating=rating, comment=comment)
            db.session.add(review)

        if reviewer_id == contract.hirer_id:
            prof = TranslatorProfile.query.filter_by(user_id=contract.translator_id).first()
            if prof:
                if is_edit:
                    total = (prof.rating * prof.total_reviews) - old_rating + rating
                    prof.rating = round(total / prof.total_reviews, 1) if prof.total_reviews > 0 else rating
                else:
                    total = (prof.rating * prof.total_reviews) + rating
                    prof.total_reviews += 1
                    prof.rating = round(total / prof.total_reviews, 1)

        db.session.flush() # Để lấy review.id cho notification

        reviewer = User.query.get(reviewer_id)
        if reviewer:
            from services.notifications import should_notify
            reviewee = User.query.get(reviewee_id)
            if reviewee and should_notify(reviewee, 'NEW_REVIEW'):
                from models import Notification
                try:
                    if is_edit:
                        existing_notif = Notification.query.filter_by(
                            user_id=reviewee_id, 
                            type='NEW_REVIEW', 
                            related_contract_id=contract.id
                        ).first()
                        if existing_notif:
                            existing_notif.is_read = False
                            existing_notif.created_at = datetime.utcnow()
                            existing_notif.message = f'{reviewer.name} vừa cập nhật đánh giá {rating}/5.'
                        else:
                            create_notification(
                                user_id=reviewee_id,
                                notification_type='NEW_REVIEW',
                                title='Bạn nhận được đánh giá mới',
                                message=f'{reviewer.name} vừa cập nhật đánh giá {rating}/5.',
                                url=url_for('transaction_detail', contract_id=contract.id),
                                related_review_id=review.id,
                                related_contract_id=contract.id
                            )
                    else:
                        create_notification(
                            user_id=reviewee_id,
                            notification_type='NEW_REVIEW',
                            title='Bạn nhận được đánh giá mới',
                            message=f'{reviewer.name} vừa đánh giá bạn {rating}/5.',
                            url=url_for('transaction_detail', contract_id=contract.id),
                            related_review_id=review.id,
                            related_contract_id=contract.id
                        )
                except Exception as e:
                    print(f"Error creating review notification: {e}")
                    pass

        db.session.commit()
        flash('Đánh giá đã được lưu thành công!', 'success')
    return redirect(url_for('transaction_detail', contract_id=contract.id))

# ─── CHAT API (CONTRACT) ────────────────────────────────────────────────────────

@app.route('/api/messages/<int:contract_id>')
@login_required
def get_messages(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    from services.permissions import require_contract_access
    require_contract_access(session['user_id'], contract)
    
    me = session['user_id']
    msgs = Message.query.filter_by(contract_id=contract_id).order_by(Message.created_at.asc()).all()
    
    # Mark messages from the other user as read
    unread = [m for m in msgs if m.sender_id != me and not m.is_read]
    for m in unread:
        m.is_read = True
    if unread:
        db.session.commit()

    return jsonify([{'id': m.id, 'sender_id': m.sender_id, 'sender_name': m.sender.name,
                     'content': m.content, 'time': m.created_at.strftime('%H:%M %d/%m')} for m in msgs])

@app.route('/api/messages/<int:contract_id>', methods=['POST'])
@login_required
def send_message(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    sender_id = session['user_id']
    from services.permissions import require_contract_access
    require_contract_access(sender_id, contract)

    content = request.json.get('content', '').strip()
    if content:
        db.session.add(Message(contract_id=contract_id, sender_id=sender_id, content=content))
        db.session.flush()

        if sender_id == contract.hirer_id:
            receiver_id = contract.translator_id
        else:
            receiver_id = contract.hirer_id
            
        receiver = User.query.get(receiver_id)
        if receiver:
            from services.notifications import should_notify
            sender = User.query.get(sender_id)
            if should_notify(receiver, 'NEW_MESSAGE'):
                try:
                    create_notification(
                        user_id=receiver_id,
                        notification_type='NEW_MESSAGE',
                        title='Bạn có tin nhắn mới',
                        message=f'{sender.name} đã gửi cho bạn một tin nhắn trong hợp đồng.',
                        url=url_for('transaction_detail', contract_id=contract.id),
                        related_contract_id=contract.id
                    )
                except Exception as e:
                    print(f"Error creating notification: {e}")
                    pass

        db.session.commit()
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400

# ─── ADMIN ROUTES ───────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = {
        'total_users': User.query.filter_by(is_admin=False).count(),
        'total_translators': TranslatorProfile.query.count(),
        'pending_verify': TranslatorProfile.query.filter_by(is_verified=False).count(),
        'open_jobs': Job.query.filter_by(status='open', is_flagged=False).count(),
        'flagged_jobs': Job.query.filter_by(is_flagged=True).count(),
        'active_contracts': Contract.query.filter_by(status='in_progress').count(),
        'completed_contracts': Contract.query.filter_by(status='completed').count(),
    }
    recent_users = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).limit(5).all()
    recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
    return render_template('admin_dashboard.html', stats=stats, recent_users=recent_users, recent_jobs=recent_jobs)

@app.route('/admin/jobs')
@admin_required
def admin_jobs():
    status_filter = request.args.get('status', 'all')
    query = Job.query
    if status_filter == 'flagged':
        query = query.filter_by(is_flagged=True)
    elif status_filter == 'open':
        query = query.filter_by(status='open', is_flagged=False)
    elif status_filter == 'completed':
        query = query.filter_by(status='completed')
    jobs = query.order_by(Job.created_at.desc()).all()
    return render_template('admin_jobs.html', jobs=jobs, status_filter=status_filter)

@app.route('/admin/jobs/<int:job_id>/flag', methods=['POST'])
@admin_required
def admin_flag_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_flagged = not job.is_flagged
    db.session.commit()
    action = 'Đã gắn cờ vi phạm' if job.is_flagged else 'Đã khôi phục'
    flash(f'{action} bài đăng "{job.title}".', 'success')
    return redirect(url_for('admin_jobs'))

@app.route('/admin/jobs/<int:job_id>/delete', methods=['POST'])
@admin_required
def admin_delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash('Đã xoá vĩnh viễn bài đăng.', 'success')
    return redirect(url_for('admin_jobs'))

@app.route('/admin/users')
@admin_required
def admin_users():
    role_filter = request.args.get('role', 'all')
    query = User.query.filter_by(is_admin=False)
    if role_filter == 'hirer':
        query = query.filter_by(role='hirer')
    elif role_filter == 'translator':
        query = query.filter_by(role='translator')
    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users, role_filter=role_filter)

@app.route('/admin/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def admin_toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status = 'kích hoạt' if user.is_active else 'khoá'
    flash(f'Đã {status} tài khoản {user.name}.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/translators')
@admin_required
def admin_translators():
    show = request.args.get('show', 'pending')
    if show == 'verified':
        profiles = TranslatorProfile.query.filter_by(is_verified=True).all()
    else:
        profiles = TranslatorProfile.query.filter_by(is_verified=False).all()
    return render_template('admin_translators.html', profiles=profiles, show=show)

@app.route('/admin/translators/<int:profile_id>/verify', methods=['POST'])
@admin_required
def admin_verify_translator(profile_id):
    profile = TranslatorProfile.query.get_or_404(profile_id)
    action = request.form.get('action')
    profile.is_verified = (action == 'verify')
    db.session.commit()
    msg = 'Đã xác minh' if profile.is_verified else 'Đã từ chối xác minh'
    flash(f'{msg} hồ sơ {profile.user.name}.', 'success')
    return redirect(url_for('admin_translators'))

# ─── NOTIFICATION API ─────────────────────────────────────────────────────────

def create_notification(user_id, notification_type, title, message, url=None, related_job_id=None, related_contract_id=None, related_review_id=None, related_proposal_id=None):
    from models import Notification
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        url=url,
        related_job_id=related_job_id,
        related_contract_id=related_contract_id,
        related_review_id=related_review_id,
        related_proposal_id=related_proposal_id
    )
    db.session.add(notification)
    return notification

@app.route('/notifications')
@login_required
def notifications_page():
    return render_template('notifications.html')

@app.route('/api/notifications', methods=['GET'])
@login_required
def api_get_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    from models import Notification
    pagination = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'notifications': [{
            'id': n.id,
            'type': n.type,
            'title': n.title,
            'message': n.message,
            'url': n.url,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        } for n in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def api_read_notification(notification_id):
    from models import Notification
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != session['user_id']:
        abort(403)
    notification.is_read = True
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_read_all_notifications():
    from models import Notification
    Notification.query.filter_by(user_id=session['user_id'], is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/notifications/unread-count', methods=['GET'])
@login_required
def api_unread_notifications_count():
    from models import Notification
    count = Notification.query.filter_by(user_id=session['user_id'], is_read=False).count()
    return jsonify({'count': count})
@app.route('/api/jobs/recommended', methods=['GET'])
@login_required
def api_recommended_jobs():
    from services.matching import get_recommended_jobs_for_translator
    limit = request.args.get('limit', 10, type=int)
    recommended = get_recommended_jobs_for_translator(session['user_id'], limit)
    return jsonify(recommended)

@app.route('/api/jobs/<int:job_id>/recommended-translators', methods=['GET'])
@login_required
def api_recommended_translators(job_id):
    job = Job.query.get_or_404(job_id)
    if job.hirer_id != session['user_id']:
        abort(403)
        
    from services.matching import get_recommended_translators_for_job
    limit = request.args.get('limit', 10, type=int)
    # Safe execute
    try:
        recommended = get_recommended_translators_for_job(job_id, limit)
        return jsonify(recommended)
    except Exception as e:
        print(f"Error fetching recommended translators: {e}")
        return jsonify([])

@app.route('/api/jobs/<int:job_id>/invite/<int:translator_id>', methods=['POST'])
@login_required
def api_invite_translator(job_id, translator_id):
    job = Job.query.get_or_404(job_id)
    if job.hirer_id != session['user_id']:
        abort(403)
        
    if job.status != 'open':
        return jsonify({'status': 'error', 'message': 'Công việc không còn mở để nhận ứng tuyển.'}), 400
        
    translator = User.query.get_or_404(translator_id)
    if translator.role != 'translator' or not translator.is_active:
        return jsonify({'status': 'error', 'message': 'Phiên dịch viên không hợp lệ hoặc đã bị khóa.'}), 400
        
    from app import translator_accepts_job
    if not translator_accepts_job(translator, job):
        return jsonify({'status': 'error', 'message': 'Phiên dịch viên không nhận loại công việc này.'}), 400
        
    from services.matching import translator_is_available_for_job
    available, availability_reason = translator_is_available_for_job(translator.id, job)
    if not available:
        return jsonify({'status': 'error', 'message': 'Phiên dịch viên này đã có lịch trong khoảng thời gian của công việc.'}), 400
        
    from models import Notification
    existing = Notification.query.filter_by(
        user_id=translator.id,
        type='JOB_INVITATION',
        related_job_id=job.id
    ).first()
    
    if existing:
        return jsonify({'status': 'already_invited'})
        
    from services.notifications import should_notify
    if should_notify(translator, 'JOB_INVITATION'):
        from app import create_notification
        create_notification(
            user_id=translator.id,
            notification_type='JOB_INVITATION',
            title='Bạn được mời ứng tuyển',
            message=f'Khách hàng {job.hirer.name} đã mời bạn ứng tuyển vào công việc "{job.title}".',
            url=url_for('job_detail', job_id=job.id),
            related_job_id=job.id
        )
        db.session.commit()
        
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
