import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort, Response, g
from models import db, User, TranslatorProfile, HirerProfile, TranslatorPreference, Service, Job, Proposal, SavedJob, Contract, Message, DirectMessage, Deliverable, Review, LANGUAGES, LoginAttempt, AdminAuditLog, ADMIN_AUDIT_ACTIONS, Report, PaymentTransaction, AdminNotification, TranslatorSchedule
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
import re
from translations import t as t_lookup, get_localized_languages, get_language_display_name
from sqlalchemy.pool import StaticPool

def get_locale():
    from flask import session, request
    lang = session.get('lang')
    if not lang and request:
        lang = request.cookies.get('lang')
    return lang if lang in ('vi', 'en') else 'vi'

def _t(key, **kwargs):
    return t_lookup(key, lang=get_locale(), **kwargs)

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
app.config['SESSION_COOKIE_HTTPONLY'] = True   # Ngăn JavaScript đọc session cookie
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
    elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    if os.environ.get('VERCEL') == '1':
        # Vercel: filesystem ephemeral — BẮT BUỘC dùng DATABASE_URL hoặc MONGO_URI
        if not os.getenv("MONGO_URI"):
            error_msg = "[CRITICAL] Chạy trên Vercel nhưng DATABASE_URL (và MONGO_URI) chưa được cấu hình! Không dùng SQLite memory trong production để tránh mất dữ liệu."
            print(error_msg, file=sys.stderr)
            raise RuntimeError(error_msg)
        # Nếu có MONGO_URI nhưng thiếu DATABASE_URL (chỉ dùng MongoDB):
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

print(f"[DB] Using: {database_url[:50]}...", file=__import__('sys').stderr)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

if 'sqlite' in database_url:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': StaticPool,
        'connect_args': {'check_same_thread': False},
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'prepare_threshold': None,
        },
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

from sqlalchemy import event
with app.app_context():
    @event.listens_for(db.engine, "connect")
    def set_psycopg_prepare_threshold(dbapi_connection, connection_record):
        if hasattr(dbapi_connection, "prepare_threshold"):
            dbapi_connection.prepare_threshold = None

import sys

def _init_db():
    """Tạo bảng nếu chưa tồn tại và nạp seed data DUY NHẤT khi DB trống.
    
    QUAN TRỌNG:
    - KHÔNG bao giờ drop_all() ở đây.
    - KHÔNG chạy seed nếu đã có user (idempotent).
    - Bắt lỗi IntegrityError riêng để tránh crash khi có race condition.
    """
    try:
        db.create_all()
        # Tự động đồng bộ các cột mới của proposal (updated_at, client_note, withdrawn_reason)
        with db.engine.connect() as conn:
            engine_url = str(db.engine.url).lower()
            if 'sqlite' in engine_url:
                cols = [row[1] for row in conn.execute(db.text("PRAGMA table_info(proposal)")).fetchall()]
                if cols:
                    if 'updated_at' not in cols:
                        conn.execute(db.text("ALTER TABLE proposal ADD COLUMN updated_at TIMESTAMP"))
                    if 'client_note' not in cols:
                        conn.execute(db.text("ALTER TABLE proposal ADD COLUMN client_note TEXT"))
                    if 'withdrawn_reason' not in cols:
                        conn.execute(db.text("ALTER TABLE proposal ADD COLUMN withdrawn_reason VARCHAR(255)"))
                    conn.commit()
            elif 'postgresql' in engine_url:
                conn.execute(db.text("ALTER TABLE proposal ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()"))
                conn.execute(db.text("ALTER TABLE proposal ADD COLUMN IF NOT EXISTS client_note TEXT"))
                conn.execute(db.text("ALTER TABLE proposal ADD COLUMN IF NOT EXISTS withdrawn_reason VARCHAR(255)"))
                conn.commit()
    except Exception as e:
        print(f"[DB] db.create_all() / migration error: {e}", file=sys.stderr)
        return

    try:
        # Thực hiện một query giả để SQLAlchemy fetch toàn bộ column của User và kiểm tra schema drift
        dummy_user = db.session.query(User).first()
        # Fetch thử một số Model khác để kiểm tra
        dummy_schedule = db.session.query(TranslatorSchedule).first()
        user_count = db.session.execute(db.select(db.func.count()).select_from(User)).scalar()
    except Exception as e:
        error_msg = str(e)
        if "UndefinedColumn" in error_msg or "no such column" in error_msg.lower():
            print(f"\\n{'='*50}\\n[CRITICAL DB ERROR] DATABASE SCHEMA DRIFT DETECTED!\\nLỗi thiếu column trong database: {error_msg}\\n=> HÃY CHẠY MIGRATION SCRIPT (migration_sync_current_schema.sql)\\n{'='*50}\\n", file=sys.stderr)
        else:
            print(f"[DB] Cannot query database during init: {e}", file=sys.stderr)
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


@app.errorhandler(500)
def handle_500(e):
    import traceback
    tb = traceback.format_exc()
    return f"<pre>500 Error:\n{e}\n\nTraceback:\n{tb}</pre>", 500

# ─── DECORATORS ────────────────────────────────────────────────────────────────

# Import admin_auth module và đăng ký context processor/globals
from admin_auth import (
    admin_login_required,
    require_permission,
    csrf_protected,
    audit_log as _audit_log,
    inject_admin_globals,
    get_csrf_token,
    destroy_admin_session,
    create_admin_session,
    get_client_ip,
    ADMIN_SESSION_KEY,
)

# Đăng ký inject_admin_globals cho tất cả admin templates
app.context_processor(inject_admin_globals)

# Helper: CSRF token cho templates
@app.template_global()
def csrf_token():
    """Trả về CSRF token hiện tại cho Admin templates."""
    return get_csrf_token()


# Context processor: Badge counts và helpers cho Admin sidebar
@app.context_processor
def inject_admin_badges():
    """
    Inject badge counts vào tất cả Admin templates.
    Chỉ query DB khi đang ở admin session để tránh overhead cho user thường.
    """
    if not session.get(ADMIN_SESSION_KEY):
        return {}

    badges = {}
    try:
        badges['admin_badge_pending_translators'] = TranslatorProfile.query.filter_by(is_verified=False).count()
        badges['admin_badge_flagged_jobs'] = Job.query.filter_by(is_flagged=True).count()
        badges['admin_badge_reports'] = Report.query.filter_by(status='new').count()
        badges['admin_badge_notifications'] = AdminNotification.query.filter_by(is_read=False).count()
    except SQLAlchemyError:
        badges = {
            'admin_badge_pending_translators': 0,
            'admin_badge_flagged_jobs': 0,
            'admin_badge_reports': 0,
            'admin_badge_notifications': 0,
        }
    return badges


@app.template_global()
def get_admin_routes():
    """Trả về set tên các admin routes đã được đăng ký để kiểm tra trong sidebar."""
    return {rule.endpoint for rule in app.url_map.iter_rules() if rule.endpoint.startswith('admin_')}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash(_t('flash.login_required'), 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """
    Decorator cũ — giữ lại để không break các route admin hiện có.
    Chuyển tiếp sang admin_login_required từ admin_auth.
    TASK 2: Tất cả route /admin/* phải dùng decorator này.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        return admin_login_required(f)(*args, **kwargs)
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

@app.template_filter('vnd')
def vnd_filter(value):
    try:
        return '{:,.0f}'.format(float(value))
    except (ValueError, TypeError):
        return value

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
        t=lambda key, **kwargs: t_lookup(key, current_lang, **kwargs),
        lang_name=lambda name: get_language_display_name(name, current_lang)
    )

@app.route('/set-language/<lang>')
def set_language(lang):
    referer = request.referrer
    if lang in ('vi', 'en'):
        session['lang'] = lang
        session.modified = True

    # Prevent open redirect vulnerabilities
    if referer and request.host in referer:
        resp = redirect(referer)
    else:
        resp = redirect(url_for('index'))
        
    if lang in ('vi', 'en'):
        # Ensure setting the lang cookie doesn't interfere with session
        resp.set_cookie('lang', lang, max_age=365*24*3600, samesite='Lax', secure=True, httponly=False)
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

# ─── NEWS / TIN TỨC ───────────────────────────────────────────────────────────

from news_data import (
    CATEGORIES as NEWS_CATEGORIES,
    POPULAR_TOPICS,
    get_article_by_slug,
    get_articles_by_category,
    get_featured_articles,
    get_latest_articles,
    get_popular_articles,
    get_related_articles,
    get_category_name as _get_category_name,
    format_date_news,
)

@app.route('/tin-tuc')
def news_list():
    category = request.args.get('category', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 6

    # Get featured articles (only on first page, all categories)
    featured = get_featured_articles() if (page == 1 and category in ('all', None, '')) else []

    # Get articles for listing
    all_articles = get_articles_by_category(category if category != 'all' else None)

    # Exclude featured slugs from latest to avoid duplication
    featured_slugs = [a['slug'] for a in featured]
    listing_articles = [a for a in all_articles if a['slug'] not in featured_slugs]

    # Pagination
    total = len(listing_articles)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = listing_articles[start:end]
    show_more = end < total

    return render_template('news_list.html',
        categories=NEWS_CATEGORIES,
        active_category=category,
        featured_articles=featured,
        latest_articles=paginated,
        popular_articles=get_popular_articles(5),
        popular_topics=POPULAR_TOPICS,
        current_page=page,
        show_more=show_more,
        get_category_name=_get_category_name,
        format_date=format_date_news,
    )


@app.route('/tin-tuc/<slug>')
def news_detail(slug):
    article = get_article_by_slug(slug)
    if not article:
        abort(404)

    # Extract TOC from content (h2, h3 with id attributes)
    import re as _re
    toc_items = []
    headings = _re.findall(r'<h([23])\s+id="([^"]+)"[^>]*>([^<]+)</h[23]>', article['content'])
    for level, hid, text in headings:
        toc_items.append({'level': int(level), 'id': hid, 'text': text.strip()})

    related = get_related_articles(article, limit=3)

    return render_template('news_detail.html',
        article=article,
        toc_items=toc_items,
        related_articles=related,
        popular_articles=get_popular_articles(5),
        popular_topics=POPULAR_TOPICS,
        get_category_name=_get_category_name,
        format_date=format_date_news,
    )

# ─── AUTH ──────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or request.form.get('next')

    def is_safe_redirect(url):
        return bool(url and url.startswith('/') and not url.startswith('//'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # ── Thử MongoDB trước (khi deploy trên Vercel) ──
            if MONGO_URI:
                mongo_user = mongo_find_user_by_email(email)
                if mongo_user:
                    if not mongo_user.get('is_active', True):
                        flash(_t('flash.account_locked'), 'error')
                        return render_template('login.html', email=email, next_url=next_url)
                    if check_password_hash(mongo_user['password_hash'], password):
                        # Lưu mongo _id dạng string vào session với prefix để phân biệt
                        session.clear()
                        session.permanent = True
                        session['user_id'] = f"mongo:{mongo_user['_id']}"
                        session['user_name'] = mongo_user.get('name', '')
                        session['user_role'] = mongo_user.get('role', '')
                        session['is_admin'] = mongo_user.get('is_admin', False)
                        flash(_t('flash.login_success'), 'success')
                        if mongo_user.get('is_admin'):
                            return redirect(url_for('admin_dashboard'))
                        if is_safe_redirect(next_url):
                            return redirect(next_url)
                        return redirect(url_for('index'))
                    else:
                        flash(_t('flash.invalid_password'), 'error')
                        return render_template('login.html', email=email, next_url=next_url)
                # Nếu không tìm thấy trong MongoDB thì fallback xuống SQLite bên dưới
    
            # ── Fallback: SQLite / SQLAlchemy (khi chạy local) ──
            user = User.query.filter_by(email=email).first()
            if user:
                if not user.is_active:
                    flash(_t('flash.account_locked'), 'error')
                    return render_template('login.html', email=email, next_url=next_url)
                if check_password_hash(user.password_hash, password):
                    session.clear()
                    session.permanent = True
                    session['user_id'] = user.id
                    flash(_t('flash.login_success'), 'success')
                    if user.is_admin:
                        return redirect(url_for('admin_dashboard'))
                    if is_safe_redirect(next_url):
                        return redirect(next_url)
                    return redirect(url_for('index'))
                else:
                    flash(_t('flash.invalid_password'), 'error')
                    return render_template('login.html', email=email, next_url=next_url)
            else:
                flash(_t('flash.account_not_found'), 'error')
                return render_template('login.html', email=email, next_url=next_url)
        except SQLAlchemyError as e:
            print(f"[AUTH SQL ERROR] {e}")
            flash(_t('flash.system_overload'), 'error')
            return render_template('login.html', email=email, next_url=next_url)
        except Exception as e:
            print(f"[AUTH ERROR] {e}")
            flash(_t('flash.db_error'), 'error')
            return render_template('login.html', email=email, next_url=next_url)

    return render_template('login.html', next_url=next_url)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        role = request.form.get('role')

        if role not in ('hirer', 'translator'):
            flash(_t('flash.invalid_role'), 'error')
            return redirect(url_for('register'))

        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash(_t('flash.invalid_email'), 'error')
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
                flash(_t('flash.register_success'), 'success')
                return redirect(url_for('login'))
            else:
                flash(message, 'error')
                return redirect(url_for('register'))

        # ── Fallback: SQLite / SQLAlchemy (khi chạy local) ──
        if User.query.filter_by(email=email).first():
            flash(_t('flash.email_exists'), 'error')
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

        flash(_t('flash.register_success'), 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash(_t('flash.logout_success'), 'success')
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
            flash(_t('flash.account_not_found'), 'error')
            return redirect(url_for('index'))
        user = SimpleMongoUser(mongo_data)

        if request.method == 'POST':
            action = request.form.get('action', 'basic')
            col = get_mongo_users()
            if col is None:
                flash(_t('flash.mongo_error'), 'error')
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
                flash(_t('flash.profile_updated'), 'success')

            elif action == 'change_password':
                old_pw = request.form.get('old_password', '')
                new_pw = request.form.get('new_password', '')
                confirm_pw = request.form.get('confirm_password', '')
                if not check_password_hash(mongo_data['password_hash'], old_pw):
                    flash(_t('flash.old_password_incorrect'), 'error')
                elif new_pw != confirm_pw:
                    flash(_t('flash.new_password_mismatch'), 'error')
                elif len(new_pw) < 6:
                    flash(_t('flash.password_too_short'), 'error')
                else:
                    col.update_one(
                        {"_id": ObjectId(mongo_id)},
                        {"$set": {"password_hash": generate_password_hash(new_pw)}}
                    )
                    flash(_t('flash.password_changed'), 'success')

            return redirect(url_for('account_profile'))
        return render_template('account_profile.html', user=user)

    # SQLite user
    user = User.query.get(uid)
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        action = request.form.get('action', 'basic')

        if action == 'basic':
            user.name = request.form.get('name', user.name).strip()
            user.phone = request.form.get('phone', user.phone or '').strip()
            db.session.commit()
            flash(_t('flash.profile_updated'), 'success')

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
            flash(_t('flash.translator_profile_updated'), 'success')

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
            flash(_t('flash.preferences_saved'), 'success')

        elif action == 'hirer_profile' and user.role == 'hirer':
            profile = user.hirer_profile
            if not profile:
                profile = HirerProfile(user_id=user.id)
                db.session.add(profile)
            profile.title = request.form.get('title', '').strip()
            profile.company = request.form.get('company', '').strip()
            profile.location = request.form.get('location', '').strip()
            db.session.commit()
            flash(_t('flash.hirer_profile_updated'), 'success')

        elif action == 'change_password':
            old_pw = request.form.get('old_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if not check_password_hash(user.password_hash, old_pw):
                flash(_t('flash.old_password_incorrect'), 'error')
            elif new_pw != confirm_pw:
                flash(_t('flash.new_password_mismatch'), 'error')
            elif len(new_pw) < 6:
                flash(_t('flash.password_too_short'), 'error')
            else:
                user.password_hash = generate_password_hash(new_pw)
                db.session.commit()
                flash(_t('flash.password_changed'), 'success')

        return redirect(url_for('account_profile'))
    current_lang = session.get('lang') or request.cookies.get('lang') or 'vi'
    return render_template('account_profile.html', user=user, LANGUAGES=get_localized_languages(current_lang))

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
        flash(_t('flash.account_not_found'), 'error')
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
    try:
        user_count = User.query.count()
        profile_count = TranslatorProfile.query.count()
        service_count = Service.query.count()
        db_status = 'connected'
    except Exception as e:
        user_count = profile_count = service_count = -1
        db_status = f'error: {e}'
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    safe_uri = db_uri.split('@')[-1] if '@' in db_uri else db_uri[:60]
    return jsonify({
        'db_host': safe_uri,
        'db_status': db_status,
        'vercel': os.environ.get('VERCEL', '0'),
        'users': user_count,
        'profiles': profile_count,
        'services': service_count,
    })

@app.route('/api/debug-index')
def debug_index():
    import traceback
    try:
        top_translators = TranslatorProfile.query.filter_by(is_verified=True).order_by(
            TranslatorProfile.rating.desc()).limit(4).all()
        if not top_translators:
            top_translators = TranslatorProfile.query.order_by(TranslatorProfile.rating.desc()).limit(4).all()
        latest_jobs = Job.query.filter_by(status='open', is_flagged=False).order_by(Job.created_at.desc()).limit(4).all()
        html = render_template('index.html', top_translators=top_translators, latest_jobs=latest_jobs)
        return jsonify({'status': 'ok', 'html_length': len(html)})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()})

@app.route('/api/translators')
def api_translators():
    """JSON API cho client-side filtering realtime."""
    try:
        from sqlalchemy.orm import joinedload
        profiles = TranslatorProfile.query.options(
            joinedload(TranslatorProfile.user),
            joinedload(TranslatorProfile.services)
        ).order_by(TranslatorProfile.rating.desc()).all()
        data = []
        for p in profiles:
            if not p.user:
                continue
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
                'avatar_url': p.avatar_url,
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
    except Exception as e:
        import traceback
        print(f"Error in api_translators: {e}\n{traceback.format_exc()}", file=sys.stderr)
        return jsonify([])

@app.route('/translator/<int:profile_id>')
def translator_profile(profile_id):
    profile = TranslatorProfile.query.get_or_404(profile_id)
    # Reviews received by this translator
    reviews = Review.query.filter_by(reviewee_id=profile.user_id).order_by(Review.created_at.desc()).limit(10).all()
    return render_template('translator_profile.html', profile=profile, reviews=reviews)

@app.route('/hirer/<int:hirer_id>')
def hirer_profile(hirer_id):
    user = User.query.get_or_404(hirer_id)
    if user.role != 'hirer':
        abort(404)
        
    profile = user.hirer_profile
    
    # Calculate stats
    total_jobs = Job.query.filter_by(hirer_id=hirer_id).count()
    completed_contracts = Contract.query.join(Job).filter(Job.hirer_id == hirer_id, Contract.status == 'completed').count()
    
    return render_template('hirer_profile.html', user=user, profile=profile, total_jobs=total_jobs, completed_contracts=completed_contracts)

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
        flash(_t('flash.login_required'), 'warning')
        return redirect(url_for('login'))
    translator = service.profile.user if service.profile else None

    if not translator or getattr(translator, 'role', '') != 'translator' or not getattr(translator, 'is_active', True):
        flash(_t('flash.translator_inactive'), 'error')
        return redirect(url_for('translators'))

    if current_user.id == translator.id:
        flash(_t('flash.cannot_hire_self'), 'error')
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
            flash(_t('flash.service_booked'), 'success')
            return redirect(url_for('payment_mockup', contract_id=contract.id))
            
        except (BookingConflictError, BookingValidationError, ScheduleCheckError) as e:
            flash(str(e), 'error')
            return redirect(url_for('book_service', service_id=service.id, tier=tier))
            
        except Exception as e:
            import logging
            logging.exception('Error in book_service: %s', e)
            flash(_t('flash.system_error'), 'error')
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
        flash(_t('flash.hirer_only_post'), 'error')
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

        flash(_t('flash.job_posted'), 'success')
        return redirect(url_for('job_detail', job_id=job.id))
    return render_template('post_job.html', LANGUAGES=LANGUAGES)

@app.route('/applied-jobs', endpoint='applied_jobs')
@app.route('/my-jobs', endpoint='my_jobs')
@login_required
def applied_jobs():
    user = get_current_user()
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('index'))

    # Tab phân loại: 'applied' (Đang ứng tuyển), 'contracts' (Hợp đồng đang làm), 'completed' (Hoàn thành), 'saved' (Đã lưu)
    filter_param = request.args.get('filter', '').strip().lower()
    tab = request.args.get('tab', '').strip().lower()
    if not tab:
        if filter_param in ['active']:
            tab = 'contracts'
        elif filter_param in ['completed']:
            tab = 'completed'
        elif filter_param in ['saved']:
            tab = 'saved'
        else:
            tab = 'applied'

    status_filter = request.args.get('status', 'all').strip().lower()
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'newest').strip().lower()

    # Truy vấn proposals của translator
    query = Proposal.query.filter_by(translator_id=user.id)
    if search_query:
        query = query.join(Job).filter(Job.title.ilike(f'%{search_query}%'))

    if sort_by == 'oldest':
        query = query.order_by(Proposal.created_at.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Proposal.price.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Proposal.price.asc())
    else:
        query = query.order_by(Proposal.created_at.desc())

    all_user_proposals = query.all()

    # Thống kê số lượng theo 8 trạng thái chuẩn nghiệp vụ
    status_counts = {
        'all': len(all_user_proposals),
        'pending': 0,
        'reviewing': 0,
        'needs_response': 0,
        'selected': 0,
        'accepted': 0,
        'rejected': 0,
        'withdrawn': 0,
        'job_closed': 0,
    }
    for p in all_user_proposals:
        eff = p.effective_status
        if eff in status_counts:
            status_counts[eff] += 1

    # Lọc danh sách theo status_filter
    if status_filter != 'all':
        filtered_proposals = [p for p in all_user_proposals if p.effective_status == status_filter]
    else:
        filtered_proposals = all_user_proposals

    # Lấy Contracts và SavedJobs cho các tab phụ trợ
    all_contracts = Contract.query.filter_by(translator_id=user.id).order_by(Contract.created_at.desc()).all()
    active_statuses = ('escrow_pending', 'escrow_paid', 'in_progress', 'delivered')
    completed_statuses = ('completed', 'reviewed')
    active_contracts = [c for c in all_contracts if c.status in active_statuses]
    completed_contracts = [c for c in all_contracts if c.status in completed_statuses]

    saved_records = SavedJob.query.filter_by(user_id=user.id).order_by(SavedJob.created_at.desc()).all()
    saved_jobs = [s.job for s in saved_records if s.job]

    counts = {
        'applied': len(all_user_proposals),
        'active': len(active_contracts),
        'completed': len(completed_contracts),
        'saved': len(saved_jobs),
    }

    return render_template('applied_jobs.html',
        proposals=filtered_proposals,
        status_counts=status_counts,
        status_filter=status_filter,
        search_query=search_query,
        sort_by=sort_by,
        tab=tab,
        active_contracts=active_contracts,
        completed_contracts=completed_contracts,
        saved_jobs=saved_jobs,
        counts=counts
    )


@app.route('/api/proposals/<int:proposal_id>/withdraw', methods=['POST'])
@login_required
def api_withdraw_proposal(proposal_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    proposal = Proposal.query.get_or_404(proposal_id)
    if proposal.translator_id != user.id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền thao tác trên đơn này.'}), 403
    
    if proposal.effective_status in ['accepted']:
        return jsonify({'success': False, 'message': 'Không thể rút đơn khi đã được ký hợp đồng nhận việc.'}), 400
    if proposal.status == 'withdrawn':
        return jsonify({'success': False, 'message': 'Đơn này đã được rút trước đó.'}), 400
        
    reason = request.form.get('reason', '').strip()
    if not reason and request.is_json:
        reason = request.json.get('reason', '').strip()
    proposal.status = 'withdrawn'
    proposal.withdrawn_reason = reason or 'Phiên dịch viên chủ động rút đơn'
    proposal.updated_at = datetime.utcnow()
    
    if proposal.job and proposal.job.hirer_id:
        try:
            create_notification(
                user_id=proposal.job.hirer_id,
                notification_type='JOB_APPLICATION',
                title='Ứng viên đã rút đơn',
                message=f'Phiên dịch viên {user.name} đã rút đơn ứng tuyển cho công việc "{proposal.job.title}".',
                url=url_for('job_detail', job_id=proposal.job_id),
                related_job_id=proposal.job_id,
                related_proposal_id=proposal.id
            )
        except Exception:
            pass

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Đã rút đơn ứng tuyển thành công.'
    })


@app.route('/api/proposals/<int:proposal_id>/update', methods=['POST'])
@login_required
def api_update_proposal(proposal_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    proposal = Proposal.query.get_or_404(proposal_id)
    if proposal.translator_id != user.id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền thao tác trên đơn này.'}), 403
        
    if proposal.effective_status in ['accepted', 'withdrawn', 'job_closed', 'rejected']:
        return jsonify({'success': False, 'message': 'Không thể chỉnh sửa đơn ở trạng thái hiện tại.'}), 400
        
    cover_letter = request.form.get('cover_letter', '').strip()
    price = request.form.get('price', type=int)
    time_estimate = request.form.get('time_estimate', '').strip()
    
    if cover_letter:
        proposal.cover_letter = cover_letter
    if price and price > 0:
        proposal.price = price
    if time_estimate:
        proposal.time_estimate = time_estimate
        
    # Nếu trước đó ở trạng thái needs_response, đưa về pending (đã phản hồi)
    if proposal.status == 'needs_response':
        proposal.status = 'pending'
        
    proposal.updated_at = datetime.utcnow()
    
    if proposal.job and proposal.job.hirer_id:
        try:
            create_notification(
                user_id=proposal.job.hirer_id,
                notification_type='JOB_APPLICATION',
                title='Ứng viên cập nhật thông tin',
                message=f'Phiên dịch viên {user.name} đã cập nhật thông tin đề xuất cho công việc "{proposal.job.title}".',
                url=url_for('job_detail', job_id=proposal.job_id),
                related_job_id=proposal.job_id,
                related_proposal_id=proposal.id
            )
        except Exception:
            pass

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Đã cập nhật thông tin đơn ứng tuyển thành công.'
    })


@app.route('/api/proposals/<int:proposal_id>/confirm-job', methods=['POST'])
@login_required
def api_confirm_job_acceptance(proposal_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    proposal = Proposal.query.get_or_404(proposal_id)
    if proposal.translator_id != user.id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền thao tác trên đơn này.'}), 403
        
    if proposal.effective_status != 'selected':
        return jsonify({'success': False, 'message': 'Chỉ có thể xác nhận nhận việc khi đơn ở trạng thái Được chọn / Chờ xác nhận.'}), 400
        
    job = proposal.job
    if not job or job.status not in ['open', 'selected']:
        return jsonify({'success': False, 'message': 'Công việc này hiện không còn khả dụng.'}), 400
        
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
        proposal.status = 'accepted'
        proposal.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Gửi thông báo cho Hirer
        try:
            create_notification(
                user_id=job.hirer_id,
                notification_type='CONTRACT_CREATED',
                title='Phiên dịch viên đã xác nhận nhận việc!',
                message=f'Phiên dịch viên {user.name} đã đồng ý nhận công việc "{job.title}". Hợp đồng đã sẵn sàng để thanh toán ký quỹ.',
                url=url_for('payment_mockup', contract_id=contract.id),
                related_job_id=job.id,
                related_contract_id=contract.id
            )
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'message': 'Chúc mừng! Bạn đã xác nhận nhận việc thành công.',
            'redirect_url': url_for('accepted_jobs')
        })
    except (BookingConflictError, BookingValidationError, ScheduleCheckError) as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error("Lỗi khi xác nhận nhận việc: %s", e)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi tạo hợp đồng. Vui lòng thử lại.'}), 500


@app.route('/api/proposals/<int:proposal_id>/select', methods=['POST'])
@login_required
def api_hirer_select_proposal(proposal_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    proposal = Proposal.query.get_or_404(proposal_id)
    job = proposal.job
    if not job or job.hirer_id != user.id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền thao tác trên công việc này.'}), 403
    if job.status != 'open':
        return jsonify({'success': False, 'message': 'Công việc này không còn mở tuyển dụng.'}), 400
    if proposal.status != 'pending':
        return jsonify({'success': False, 'message': 'Đề xuất này đã được xử lý.'}), 400
        
    proposal.status = 'selected'
    proposal.updated_at = datetime.utcnow()
    
    # Gửi thông báo cho ứng viên được chọn
    try:
        create_notification(
            user_id=proposal.translator_id,
            notification_type='JOB_APPLICATION',
            title='Bạn đã được chọn cho công việc!',
            message=f'Khách hàng {user.name} đã lựa chọn bạn cho công việc "{job.title}". Vui lòng xác nhận nhận việc.',
            url=url_for('applied_jobs'),
            related_job_id=job.id,
            related_proposal_id=proposal.id
        )
    except Exception:
        pass
        
    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Đã chọn ứng viên thành công. Đang chờ ứng viên xác nhận nhận việc.'
    })


@app.route('/api/proposals/<int:proposal_id>/reject', methods=['POST'])
@login_required
def api_hirer_reject_proposal(proposal_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    proposal = Proposal.query.get_or_404(proposal_id)
    job = proposal.job
    if not job or job.hirer_id != user.id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền thao tác trên công việc này.'}), 403
        
    reason = request.form.get('reason', '').strip()
    if not reason and request.is_json:
        reason = request.json.get('reason', '').strip()
        
    proposal.status = 'rejected'
    proposal.client_note = reason or 'Cảm ơn bạn đã quan tâm. Chúng tôi đã chọn ứng viên khác phù hợp hơn.'
    proposal.updated_at = datetime.utcnow()
    
    try:
        create_notification(
            user_id=proposal.translator_id,
            notification_type='JOB_APPLICATION',
            title='Thông báo kết quả ứng tuyển',
            message=f'Bên tuyển dụng đã xem xét đề xuất cho công việc "{job.title}" và quyết định chọn ứng viên khác.',
            url=url_for('applied_jobs'),
            related_job_id=job.id,
            related_proposal_id=proposal.id
        )
    except Exception:
        pass
        
    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Đã từ chối đề xuất.'
    })


@app.route('/api/proposals/<int:proposal_id>/request-info', methods=['POST'])
@login_required
def api_hirer_request_info(proposal_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    proposal = Proposal.query.get_or_404(proposal_id)
    job = proposal.job
    if not job or job.hirer_id != user.id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền thao tác trên công việc này.'}), 403
        
    note = request.form.get('note', '').strip()
    if not note and request.is_json:
        note = request.json.get('note', '').strip()
    if not note:
        return jsonify({'success': False, 'message': 'Vui lòng nhập nội dung cần yêu cầu bổ sung.'}), 400
        
    proposal.status = 'needs_response'
    proposal.client_note = note
    proposal.updated_at = datetime.utcnow()
    
    try:
        create_notification(
            user_id=proposal.translator_id,
            notification_type='JOB_APPLICATION',
            title='Yêu cầu bổ sung thông tin ứng tuyển',
            message=f'Khách hàng {user.name} có câu hỏi/yêu cầu bổ sung cho công việc "{job.title}": {note}',
            url=url_for('applied_jobs'),
            related_job_id=job.id,
            related_proposal_id=proposal.id
        )
    except Exception:
        pass
        
    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Đã gửi yêu cầu bổ sung thông tin tới ứng viên.'
    })


# ─── TRANG ĐÃ NHẬN (QUẢN LÝ CA LÀM ĐÃ XÁC NHẬN CHO PHIÊN DỊCH VIÊN) ───────────

@app.route('/accepted-jobs', endpoint='accepted_jobs')
@login_required
def accepted_jobs():
    user = get_current_user()
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('index'))

    status_filter = request.args.get('status', 'all').strip().lower()
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'event_asc').strip().lower()
    tab = request.args.get('tab', '').strip().lower()

    # Hỗ trợ tham số tab nếu có (ví dụ ?tab=upcoming từ menu Lịch làm việc)
    if tab and status_filter == 'all':
        if tab in ['upcoming', 'in_progress', 'delivered', 'completed', 'cancelled', 'escrow_pending']:
            status_filter = tab

    # Lấy toàn bộ hợp đồng / ca làm của phiên dịch viên hiện tại
    query = Contract.query.filter_by(translator_id=user.id)
    if search_query:
        query = query.outerjoin(Job, Contract.job_id == Job.id).filter(
            db.or_(
                Job.title.ilike(f'%{search_query}%'),
                Contract.location.ilike(f'%{search_query}%'),
                db.cast(Contract.id, db.String).ilike(f'%{search_query}%')
            )
        )

    all_user_contracts = query.all()

    # Thống kê số lượng theo 6 trạng thái chuẩn nghiệp vụ VietTranslate
    status_counts = {
        'all': len(all_user_contracts),
        'escrow_pending': 0,
        'upcoming': 0,
        'in_progress': 0,
        'delivered': 0,
        'completed': 0,
        'cancelled': 0,
    }
    for c in all_user_contracts:
        code = c.shift_status_info['code']
        if code in status_counts:
            status_counts[code] += 1

    # Lọc danh sách theo status_filter
    if status_filter != 'all':
        filtered_contracts = [c for c in all_user_contracts if c.shift_status_info['code'] == status_filter]
    else:
        filtered_contracts = all_user_contracts

    # Sắp xếp danh sách
    if sort_by == 'event_desc':
        filtered_contracts.sort(key=lambda c: c.event_sort_date, reverse=True)
    elif sort_by == 'newest':
        filtered_contracts.sort(key=lambda c: c.created_at or datetime.min, reverse=True)
    elif sort_by == 'price_desc':
        filtered_contracts.sort(key=lambda c: c.agreed_price or 0, reverse=True)
    elif sort_by == 'price_asc':
        filtered_contracts.sort(key=lambda c: c.agreed_price or 0)
    else:  # 'event_asc' mặc định: ca diễn ra gần nhất lên trước
        filtered_contracts.sort(key=lambda c: c.event_sort_date)

    counts = {
        'total': len(all_user_contracts),
        'active_or_upcoming': status_counts['upcoming'] + status_counts['in_progress'],
        'delivered': status_counts['delivered'],
        'completed': status_counts['completed'],
        'pending': status_counts['escrow_pending'],
    }

    return render_template('accepted_jobs.html',
        contracts=filtered_contracts,
        status_counts=status_counts,
        status_filter=status_filter,
        search_query=search_query,
        sort_by=sort_by,
        counts=counts
    )


@app.route('/api/contracts/<int:contract_id>/report-issue', methods=['POST'])
@login_required
def api_report_contract_issue(contract_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    contract = Contract.query.get_or_404(contract_id)
    if user.id not in [contract.translator_id, contract.hirer_id]:
        return jsonify({'success': False, 'message': 'Bạn không có quyền thao tác trên ca làm này.'}), 403

    reason = request.form.get('reason', '').strip()
    if not reason and request.is_json:
        reason = request.json.get('reason', '').strip()
    description = request.form.get('description', '').strip()
    if not description and request.is_json:
        description = request.json.get('description', '').strip()

    if not reason:
        return jsonify({'success': False, 'message': 'Vui lòng chọn hoặc nhập loại sự cố.'}), 400

    report = Report(
        reporter_id=user.id,
        target_type='contract',
        target_id=contract.id,
        related_contract_id=contract.id,
        related_job_id=contract.job_id,
        reason=reason,
        description=description or 'Báo sự cố phát sinh trong ca làm việc.',
        status='new'
    )
    db.session.add(report)

    # Thêm thông báo trong tin nhắn hợp đồng để hai bên đều nắm thông tin
    msg = Message(
        contract_id=contract.id,
        sender_id=user.id,
        content=f'⚠️ [Báo sự cố ca #{contract.id}]: {reason}. {description}'
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Đã gửi báo cáo sự cố thành công! Ban điều phối sẽ liên hệ hỗ trợ bạn kịp thời.'
    })


@app.route('/api/contracts/<int:contract_id>/complete-shift', methods=['POST'])
@login_required
def api_complete_shift(contract_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    contract = Contract.query.get_or_404(contract_id)
    if user.id != contract.translator_id:
        return jsonify({'success': False, 'message': 'Chỉ phiên dịch viên phụ trách ca mới có thể báo hoàn thành.'}), 403

    if contract.status not in ['in_progress', 'escrow_paid']:
        return jsonify({'success': False, 'message': 'Ca làm hiện không ở trạng thái cho phép báo hoàn thành.'}), 400

    note = request.form.get('note', '').strip()
    if not note and request.is_json:
        note = request.json.get('note', '').strip()

    contract.status = 'delivered'
    contract.updated_at = datetime.utcnow()

    completion_msg = Message(
        contract_id=contract.id,
        sender_id=user.id,
        content=f'✅ [Báo cáo hoàn thành ca làm]: Phiên dịch viên đã thực hiện xong ca làm việc. Ghi chú: {note or "Ca làm đã hoàn tất theo kế hoạch."}'
    )
    db.session.add(completion_msg)

    try:
        create_notification(
            user_id=contract.hirer_id,
            notification_type='CONTRACT_COMPLETED',
            title='Ca làm đã hoàn tất - Chờ bạn nghiệm thu',
            message=f'Phiên dịch viên {user.name} đã báo kết thúc ca làm "#{contract.id}". Vui lòng kiểm tra và nghiệm thu giải ngân.',
            url=url_for('transaction_detail', contract_id=contract.id),
            related_contract_id=contract.id
        )
    except Exception:
        pass

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Đã gửi báo cáo hoàn thành ca làm! Vui lòng chờ khách hàng nghiệm thu giải ngân.'
    })


@app.route('/api/contracts/<int:contract_id>/checkin', methods=['POST'])
@login_required
def api_contract_checkin(contract_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    contract = Contract.query.get_or_404(contract_id)
    if user.id != contract.translator_id:
        return jsonify({'success': False, 'message': 'Chỉ phiên dịch viên phụ trách mới có quyền check-in ca làm.'}), 403

    now_str = datetime.now().strftime('%H:%M %d/%m/%Y')
    checkin_msg = Message(
        contract_id=contract.id,
        sender_id=user.id,
        content=f'📍 [Check-in ca làm]: Phiên dịch viên {user.name} đã có mặt / sẵn sàng vào ca lúc {now_str}.'
    )
    db.session.add(checkin_msg)

    try:
        create_notification(
            user_id=contract.hirer_id,
            notification_type='NEW_MESSAGE',
            title='Phiên dịch viên đã check-in',
            message=f'Phiên dịch viên {user.name} đã check-in sẵn sàng cho ca làm "#{contract.id}".',
            url=url_for('transaction_detail', contract_id=contract.id),
            related_contract_id=contract.id
        )
    except Exception:
        pass

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Check-in thành công! Chúc bạn có ca làm việc chuyên nghiệp và hiệu quả.'
    })


@app.route('/completed-jobs', endpoint='completed_jobs')
@login_required
def completed_jobs():
    user = get_current_user()
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('index'))
    if user.role != 'translator':
        flash('Trang này dành riêng cho tài khoản phiên dịch viên.', 'warning')
        return redirect(url_for('index'))

    # Các tham số bộ lọc & tìm kiếm
    q = request.args.get('q', '').strip()
    acceptance_filter = request.args.get('acceptance', 'all').strip().lower()
    payment_filter = request.args.get('payment', 'all').strip().lower()
    time_range = request.args.get('time_range', 'all').strip().lower()
    sort_by = request.args.get('sort', 'newest').strip().lower()

    # Điều kiện ca đưa vào danh sách lịch sử kết thúc:
    # 1. Thuộc tài khoản phiên dịch viên hiện tại: translator_id == user.id
    # 2. Ca đã kết thúc theo quy trình: 'delivered', 'completed', 'reviewed'
    completed_status_codes = ['delivered', 'completed', 'reviewed']
    query = Contract.query.filter_by(translator_id=user.id).filter(Contract.status.in_(completed_status_codes))

    if q:
        q_clean = q.lstrip('#').replace('CA-', '').replace('ca-', '')
        query = query.outerjoin(Job, Contract.job_id == Job.id).outerjoin(User, Contract.hirer_id == User.id).filter(
            db.or_(
                Job.title.ilike(f'%{q}%'),
                Job.field.ilike(f'%{q}%'),
                Contract.location.ilike(f'%{q}%'),
                User.name.ilike(f'%{q}%'),
                db.cast(Contract.id, db.String).ilike(f'%{q_clean}%')
            )
        )

    all_user_completed = query.all()

    # Thống kê tổng quan dựa trên toàn bộ dữ liệu thực tế của tài khoản
    total_finished_count = len(all_user_completed)
    accepted_contracts = [c for c in all_user_completed if c.status in ['completed', 'reviewed']]
    pending_contracts = [c for c in all_user_completed if c.status == 'delivered']

    total_net_earned = sum(c.translator_net_amount for c in accepted_contracts)
    total_gross_earned = sum(c.agreed_price for c in accepted_contracts)
    total_platform_fee = sum(c.platform_fee for c in accepted_contracts)
    total_held_escrow = sum(c.translator_net_amount for c in pending_contracts)

    # Đánh giá sao trung bình từ khách hàng
    rated_reviews = [c.client_review for c in all_user_completed if c.client_review and c.client_review.rating]
    avg_rating = round(sum(r.rating for r in rated_reviews) / len(rated_reviews), 1) if rated_reviews else 0.0
    total_reviews_count = len(rated_reviews)

    filter_counts = {
        'all': total_finished_count,
        'accepted': len(accepted_contracts),
        'pending': len(pending_contracts),
        'paid': len(accepted_contracts),
        'escrow_held': len(pending_contracts)
    }

    filtered_list = list(all_user_completed)

    # Lọc theo trạng thái nghiệm thu
    if acceptance_filter == 'accepted':
        filtered_list = [c for c in filtered_list if c.status in ['completed', 'reviewed']]
    elif acceptance_filter == 'pending':
        filtered_list = [c for c in filtered_list if c.status == 'delivered']

    # Lọc theo trạng thái thanh toán
    if payment_filter == 'paid':
        filtered_list = [c for c in filtered_list if c.status in ['completed', 'reviewed']]
    elif payment_filter == 'escrow_held':
        filtered_list = [c for c in filtered_list if c.status == 'delivered']

    # Lọc theo khoảng thời gian thực hiện
    today = date.today()
    if time_range == 'this_month':
        filtered_list = [c for c in filtered_list if c.event_sort_date.year == today.year and c.event_sort_date.month == today.month]
    elif time_range == 'last_month':
        last_month = today.month - 1 if today.month > 1 else 12
        last_year = today.year if today.month > 1 else today.year - 1
        filtered_list = [c for c in filtered_list if c.event_sort_date.year == last_year and c.event_sort_date.month == last_month]
    elif time_range == 'this_year':
        filtered_list = [c for c in filtered_list if c.event_sort_date.year == today.year]

    # Sắp xếp
    if sort_by == 'oldest':
        filtered_list.sort(key=lambda c: (c.event_sort_date, c.created_at or datetime.min))
    elif sort_by == 'highest_pay':
        filtered_list.sort(key=lambda c: c.agreed_price or 0, reverse=True)
    elif sort_by == 'lowest_pay':
        filtered_list.sort(key=lambda c: c.agreed_price or 0)
    elif sort_by == 'top_rated':
        filtered_list.sort(key=lambda c: (c.client_review.rating if c.client_review else 0), reverse=True)
    else:  # 'newest'
        filtered_list.sort(key=lambda c: (c.event_sort_date, c.created_at or datetime.min), reverse=True)

    metrics = {
        'total_finished': total_finished_count,
        'accepted_count': len(accepted_contracts),
        'pending_count': len(pending_contracts),
        'total_net_earned': total_net_earned,
        'total_gross_earned': total_gross_earned,
        'total_platform_fee': total_platform_fee,
        'total_held_escrow': total_held_escrow,
        'avg_rating': avg_rating,
        'total_reviews_count': total_reviews_count
    }

    return render_template('completed_jobs.html',
        contracts=filtered_list,
        metrics=metrics,
        filter_counts=filter_counts,
        q=q,
        acceptance_filter=acceptance_filter,
        payment_filter=payment_filter,
        time_range=time_range,
        sort_by=sort_by
    )


@app.route('/api/contracts/<int:contract_id>/receipt-detail', methods=['GET'])
@login_required
def api_contract_receipt_detail(contract_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    contract = Contract.query.get_or_404(contract_id)
    if contract.translator_id != user.id and contract.hirer_id != user.id and not getattr(user, 'is_admin', False):
        return jsonify({'success': False, 'message': 'Bạn không có quyền truy cập thông tin ca này.'}), 403

    review_data = None
    if contract.client_review:
        review_data = {
            'rating': contract.client_review.rating,
            'comment': contract.client_review.comment or '',
            'created_at': contract.client_review.created_at.strftime('%d/%m/%Y %H:%M') if contract.client_review.created_at else ''
        }

    deliverables_data = [
        {
            'id': d.id,
            'filename': d.filename,
            'created_at': d.created_at.strftime('%d/%m/%Y %H:%M') if d.created_at else ''
        } for d in contract.deliverables
    ]

    payment_record = contract.payments[0] if contract.payments else None

    return jsonify({
        'success': True,
        'contract': {
            'id': contract.id,
            'job_title': contract.job.title if contract.job else (contract.service.name if contract.service else f'Ca #{contract.id}'),
            'job_code': f'CA-{contract.id}',
            'hirer_name': contract.hirer.name if contract.hirer else 'Bên tuyển dụng',
            'hirer_id': contract.hirer_id,
            'scheduled_date': contract.scheduled_date or 'Theo thỏa thuận',
            'scheduled_time': f"{contract.scheduled_time_start or ''} - {contract.scheduled_time_end or ''}".strip(' -'),
            'location': contract.location or 'Trực tuyến / Thỏa thuận',
            'source_lang': contract.job.source_language if contract.job else '',
            'target_lang': contract.job.target_language if contract.job else '',
            'field': contract.job.field if contract.job else '',
            'agreed_price': contract.agreed_price,
            'platform_fee': contract.platform_fee,
            'translator_net_amount': contract.translator_net_amount,
            'shift_status': contract.shift_status_info,
            'acceptance_status': contract.acceptance_status_info,
            'payment_status': contract.payment_status_info,
            'has_payment_record': payment_record is not None,
            'transaction_ref': payment_record.transaction_ref if payment_record else f'ESCROW-CA{contract.id}',
            'payment_method': payment_record.payment_method if payment_record else 'Escrow Bảo chứng VietTranslate',
            'review': review_data,
            'deliverables': deliverables_data,
            'transaction_url': url_for('transaction_detail', contract_id=contract.id)
        }
    })


@app.route('/api/proposals/<int:proposal_id>/detail', methods=['GET'])
@login_required
def api_proposal_detail(proposal_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
    proposal = Proposal.query.get_or_404(proposal_id)
    job = proposal.job
    if proposal.translator_id != user.id and (not job or job.hirer_id != user.id):
        return jsonify({'success': False, 'message': 'Bạn không có quyền xem đơn này.'}), 403
        
    return jsonify({
        'success': True,
        'proposal': {
            'id': proposal.id,
            'price': proposal.price,
            'time_estimate': proposal.time_estimate,
            'cover_letter': proposal.cover_letter,
            'client_note': proposal.client_note,
            'withdrawn_reason': proposal.withdrawn_reason,
            'effective_status': proposal.effective_status,
            'status_info': proposal.status_info,
            'created_at': proposal.created_at.strftime('%d/%m/%Y %H:%M') if proposal.created_at else '',
            'updated_at': proposal.updated_at.strftime('%d/%m/%Y %H:%M') if proposal.updated_at else '',
            'timeline': [{
                'title': ev['title'],
                'desc': ev['desc'],
                'time': ev['time'].strftime('%d/%m/%Y %H:%M') if ev.get('time') else ''
            } for ev in proposal.timeline]
        },
        'job': {
            'id': job.id if job else None,
            'title': job.title if job else '',
            'source_lang': job.source_lang if job else '',
            'target_lang': job.target_lang if job else '',
            'event_date': job.event_date if job else '',
            'event_location': job.event_location if job else '',
            'status': job.status if job else '',
            'deadline': job.deadline.strftime('%d/%m/%Y') if (job and job.deadline) else ''
        }
    })

@app.route('/jobs')
def job_list():
    lang = request.args.get('lang', '')
    budget = request.args.get('budget', '')
    sort = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Lấy các công việc đang mở, không bị gắn cờ và còn trong thời hạn ứng tuyển
    today = date.today()
    query = Job.query.filter_by(status='open', is_flagged=False)
    query = query.filter(db.or_(Job.deadline.is_(None), Job.deadline >= today))

    if lang:
        safe_lang = lang.replace('%', r'\%').replace('_', r'\_')
        query = query.filter(db.or_(Job.source_lang.ilike(f'%{safe_lang}%'), Job.target_lang.ilike(f'%{safe_lang}%')))

    if sort == 'budget_desc':
        query = query.order_by(Job.budget_min.desc())
    else:
        query = query.order_by(Job.created_at.desc())

    is_recommended = request.args.get('recommended')
    if is_recommended and session.get('user_id'):
        from services.matching import get_recommended_jobs_for_translator
        try:
            current_lang = session.get('lang') or request.cookies.get('lang') or 'vi'
            rec_jobs = get_recommended_jobs_for_translator(session['user_id'], limit=50, lang=current_lang)
            rec_ids = [r['job_id'] for r in rec_jobs]
            if rec_ids:
                query = query.filter(Job.id.in_(rec_ids))
        except Exception as e:
            import logging
            logging.warning("Error fetching recommended jobs in job_list: %s", e)

    # Lấy toàn bộ danh sách hợp lệ để client-side filter & pagination hoạt động đầy đủ
    all_jobs = query.all()
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('job_list.html', jobs=all_jobs, pagination=pagination,
                           lang_filter=lang, LANGUAGES=LANGUAGES)

@app.route('/job/<int:job_id>', methods=['GET', 'POST'])
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    user = get_current_user()

    # Xác định trạng thái hết hạn ứng tuyển
    today = date.today()
    is_expired = bool(job.deadline and job.deadline < today)

    # Trạng thái đã lưu và đề xuất đã tồn tại
    is_saved = False
    existing_proposal = None
    profile_incomplete = False
    profile_missing_fields = []

    if user:
        is_saved = SavedJob.query.filter_by(job_id=job.id, user_id=user.id).first() is not None
        if user.role == 'translator':
            existing_proposal = Proposal.query.filter_by(
                job_id=job.id, translator_id=user.id
            ).first()

            # Kiểm tra thông tin hồ sơ bắt buộc của phiên dịch viên
            if not user.phone or not str(user.phone).strip():
                profile_missing_fields.append('Số điện thoại liên hệ')
            if not user.profile or not user.profile.languages or not str(user.profile.languages).strip():
                profile_missing_fields.append('Ngôn ngữ chuyên môn')
            if profile_missing_fields:
                profile_incomplete = True

    if request.method == 'POST':
        # ── 1. Login & Role guard ─────────────────────────────────────────────
        if not user:
            flash(_t('flash.login_required'), 'warning')
            return redirect(url_for('login', next=url_for('job_detail', job_id=job.id)))
        if user.role != 'translator':
            flash(_t('flash.translator_only_apply'), 'error')
            return redirect(url_for('job_detail', job_id=job.id))
            
        if job.status != 'open':
            flash(_t('flash.job_closed'), 'error')
            return redirect(url_for('job_detail', job_id=job.id))

        if is_expired:
            flash('Công việc này đã hết hạn nhận hồ sơ ứng tuyển.', 'error')
            return redirect(url_for('job_detail', job_id=job.id))
            
        if user.id == job.hirer_id:
            flash(_t('flash.cannot_apply_own_job'), 'error')
            return redirect(url_for('job_detail', job_id=job.id))

        # ── 2. Duplicate proposal guard ───────────────────────────────────────
        if existing_proposal:
            flash(_t('flash.already_applied'), 'warning')
            return redirect(url_for('job_detail', job_id=job.id))

        # ── 2.5. Profile completeness guard ───────────────────────────────────
        if profile_incomplete:
            flash(
                f'Hồ sơ của bạn còn thiếu thông tin bắt buộc ({", ".join(profile_missing_fields)}). '
                f'Vui lòng hoàn thiện hồ sơ trước khi ứng tuyển.',
                'warning'
            )
            return redirect(url_for('profile'))

        # ── 3. Schedule conflict check ────────────────────────────────────────
        from services.schedule import (
            parse_job_datetime, is_schedule_complete,
            check_translator_schedule_conflict, ScheduleCheckError
        )
        try:
            parsed = parse_job_datetime(job)
            if is_schedule_complete(parsed):
                result = check_translator_schedule_conflict(
                    translator_id=user.id,
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
                    return render_template(
                        'job_detail.html', job=job, form_data=request.form,
                        is_saved=is_saved, existing_proposal=existing_proposal,
                        is_expired=is_expired, profile_incomplete=profile_incomplete,
                        profile_missing_fields=profile_missing_fields
                    )
        except ScheduleCheckError as e:
            flash(str(e), 'error')
            return render_template(
                'job_detail.html', job=job, form_data=request.form,
                is_saved=is_saved, existing_proposal=existing_proposal,
                is_expired=is_expired, profile_incomplete=profile_incomplete,
                profile_missing_fields=profile_missing_fields
            )

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
                        return render_template('job_detail.html', job=job, form_data=request.form, is_saved=is_saved, existing_proposal=existing_proposal, is_expired=is_expired, profile_incomplete=profile_incomplete, profile_missing_fields=profile_missing_fields)
                    unit_str = "ngày" if unit == 'days' else "giờ"
                    time_estimate_str = f"{val_int} {unit_str}"
                except ValueError:
                    flash('Giá trị thời gian hoàn thành phải là một số.', 'error')
                    return render_template('job_detail.html', job=job, form_data=request.form, is_saved=is_saved, existing_proposal=existing_proposal, is_expired=is_expired, profile_incomplete=profile_incomplete, profile_missing_fields=profile_missing_fields)
        elif completion_type == 'deadline':
            date_val = request.form.get('estimated_completion_date')
            if date_val:
                try:
                    parsed_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                    if parsed_date < date.today():
                        flash('Ngày hoàn thành không được nằm trong quá khứ.', 'error')
                        return render_template('job_detail.html', job=job, form_data=request.form, is_saved=is_saved, existing_proposal=existing_proposal, is_expired=is_expired, profile_incomplete=profile_incomplete, profile_missing_fields=profile_missing_fields)
                    time_estimate_str = parsed_date.strftime('%d/%m/%Y')
                except ValueError:
                    flash('Định dạng ngày không hợp lệ.', 'error')
                    return render_template('job_detail.html', job=job, form_data=request.form, is_saved=is_saved, existing_proposal=existing_proposal, is_expired=is_expired, profile_incomplete=profile_incomplete, profile_missing_fields=profile_missing_fields)

        # ── 4. Create Proposal ────────────────────────────────────────────────
        try:
            proposal = Proposal(
                job_id=job.id,
                translator_id=user.id,
                cover_letter=request.form.get('cover_letter', ''),
                price=int(request.form.get('price') or 0),
                time_estimate=time_estimate_str
            )
            db.session.add(proposal)
            db.session.flush()

            # Thông báo cho khách thuê về ứng viên mới
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

            # Thông báo xác nhận cho chính phiên dịch viên
            create_notification(
                user_id=user.id,
                notification_type='JOB_APPLICATION',
                title='Ứng tuyển thành công',
                message=f'Đơn ứng tuyển của bạn cho công việc "{job.title}" đã được gửi thành công. Vui lòng chờ khách thuê phản hồi.',
                url=url_for('job_detail', job_id=job.id),
                related_job_id=job.id,
                related_proposal_id=proposal.id
            )
                
            db.session.commit()
            flash('Đề xuất của bạn đã được gửi thành công!', 'success')
            return redirect(url_for('job_detail', job_id=job.id))
        except Exception as e:
            db.session.rollback()
            import logging
            logging.error("Lỗi khi tạo proposal: %s", e)
            flash('Đã xảy ra lỗi khi gửi đề xuất. Vui lòng thử lại.', 'error')
            return render_template('job_detail.html', job=job, form_data=request.form, is_saved=is_saved, existing_proposal=existing_proposal, is_expired=is_expired, profile_incomplete=profile_incomplete, profile_missing_fields=profile_missing_fields)

    return render_template(
        'job_detail.html', job=job, is_saved=is_saved,
        existing_proposal=existing_proposal, is_expired=is_expired,
        profile_incomplete=profile_incomplete,
        profile_missing_fields=profile_missing_fields
    )


@app.route('/api/jobs/<int:job_id>/save', methods=['POST'])
def api_toggle_save_job(job_id):
    """API lưu hoặc bỏ lưu công việc dành cho người dùng đã đăng nhập."""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập để lưu công việc.'}), 401
    
    job = Job.query.get_or_404(job_id)
    saved = SavedJob.query.filter_by(user_id=user.id, job_id=job.id).first()
    if saved:
        db.session.delete(saved)
        db.session.commit()
        return jsonify({
            'success': True,
            'saved': False,
            'message': 'Đã bỏ lưu công việc thành công.'
        })
    else:
        new_save = SavedJob(user_id=user.id, job_id=job.id)
        db.session.add(new_save)
        db.session.commit()
        return jsonify({
            'success': True,
            'saved': True,
            'message': 'Đã lưu công việc thành công.'
        })


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
        flash(_t('flash.system_error'), 'error')
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
        from services.scheduling import confirm_slot, SlotExpiredError
        try:
            success = confirm_slot(contract.id)
            if not success:
                flash('Thanh toán thất bại: Không tìm thấy lịch hoặc trạng thái không hợp lệ.', 'error')
                return redirect(url_for('index'))
                
            contract.status = 'in_progress'
            db.session.commit()
            flash('Thanh toán thành công! Tiền đã được giữ trong Escrow an toàn.', 'success')
            return redirect(url_for('transaction_detail', contract_id=contract.id))
            
        except SlotExpiredError as e:
            db.session.rollback()
            flash(str(e), 'error')
            
            # Re-fetch objects after rollback to apply permanent cancellations
            c = Contract.query.get(contract.id)
            if c:
                c.status = 'cancelled'
                
            from models import TranslatorSchedule
            s = TranslatorSchedule.query.filter_by(contract_id=contract.id).first()
            if s:
                s.status = 'cancelled'
                
            db.session.commit()
            return redirect(url_for('index'))
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
    if session['user_id'] == contract.hirer_id and contract.status in ['in_progress', 'delivered']:
        contract.status = 'completed'
        if contract.job:
            contract.job.status = 'completed'
        if contract.schedule:
            contract.schedule.status = 'completed'
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

# ─── ADMIN AUTH ROUTES ───────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    Trang đăng nhập riêng cho Admin.
    - Không dùng form /login chung với user thường.
    - Có login throttling: 5 lần thất bại → khóa 15 phút.
    - Ghi Audit Log cho mọi attempt.
    - Tạo Admin session tách biệt (admin_id) sau khi xác thực.
    """
    # Nếu đã đăng nhập Admin → redirect về dashboard
    if session.get(ADMIN_SESSION_KEY):
        from admin_auth import is_admin_session_valid
        valid, _ = is_admin_session_valid()
        if valid:
            return redirect(url_for('admin_dashboard'))

    client_ip = get_client_ip()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email và mật khẩu không được để trống.', 'error')
            return render_template('admin_login.html')

        # 1. Kiểm tra lockout TRƯỚC khi query DB
        try:
            if LoginAttempt.is_locked_out(email):
                AdminAuditLog.log(
                    action=ADMIN_AUDIT_ACTIONS['ACCOUNT_LOCKED'],
                    description=f'Đăng nhập bị chặn do quá {LoginAttempt.MAX_ATTEMPTS} lần thất bại. Email: {email}',
                    ip_address=client_ip,
                    user_agent=request.headers.get('User-Agent', '')[:512],
                    extra_data={'email': email},
                )
                db.session.commit()
                return render_template(
                    'admin_login.html',
                    locked_out=True,
                    lockout_minutes=LoginAttempt.LOCKOUT_MINUTES,
                )
        except SQLAlchemyError:
            pass  # Nếu DB lỗi, tiếp tục xử lý bình thường

        # 2. Tìm user trong database
        user = None
        try:
            user = User.query.filter_by(email=email).first()
        except SQLAlchemyError as e:
            print(f'[ADMIN LOGIN DB ERROR] {e}')
            flash('Lỗi hệ thống. Vui lòng thử lại sau.', 'error')
            return render_template('admin_login.html')

        # 3. Xác thực — PHẢI là Admin và còn active
        login_ok = False
        if user and user.is_admin and user.is_active:
            if check_password_hash(user.password_hash, password):
                login_ok = True

        try:
            if login_ok:
                # Đăng nhập thành công
                LoginAttempt.record(email=email, ip_address=client_ip, success=True)
                create_admin_session(user)
                AdminAuditLog.log(
                    action=ADMIN_AUDIT_ACTIONS['LOGIN_SUCCESS'],
                    admin_id=user.id,
                    description=f'Admin đăng nhập thành công. Email: {email}',
                    ip_address=client_ip,
                    user_agent=request.headers.get('User-Agent', '')[:512],
                )
                db.session.commit()
                return redirect(url_for('admin_dashboard'))
            else:
                # Đăng nhập thất bại — ghi attempt
                LoginAttempt.record(email=email, ip_address=client_ip, success=False)
                fail_reason = 'sai mật khẩu' if user else 'không tìm thấy tài khoản'
                AdminAuditLog.log(
                    action=ADMIN_AUDIT_ACTIONS['LOGIN_FAILED'],
                    description=f'Đăng nhập Admin thất bại. Email: {email} | Lý do: {fail_reason}',
                    ip_address=client_ip,
                    user_agent=request.headers.get('User-Agent', '')[:512],
                    extra_data={'email': email},
                )
                db.session.commit()

                # Tính số lần còn lại
                failures = LoginAttempt.count_recent_failures(email)
                remaining = max(0, LoginAttempt.MAX_ATTEMPTS - failures)

                if remaining == 0:
                    return render_template(
                        'admin_login.html',
                        locked_out=True,
                        lockout_minutes=LoginAttempt.LOCKOUT_MINUTES,
                    )

                flash('Email hoặc mật khẩu không đúng, hoặc tài khoản không có quyền Admin.', 'error')
                return render_template(
                    'admin_login.html',
                    email_prefill=email,
                    attempts_remaining=remaining,
                )
        except SQLAlchemyError as e:
            print(f'[ADMIN LOGIN COMMIT ERROR] {e}')
            db.session.rollback()
            flash('Lỗi hệ thống. Vui lòng thử lại.', 'error')
            return render_template('admin_login.html')

    # GET
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """
    Đăng xuất Admin — hủy Admin session, ghi Audit Log.
    Không đụng vào user session nếu có.
    """
    admin_id = session.get(ADMIN_SESSION_KEY)
    client_ip = get_client_ip()

    try:
        if admin_id:
            AdminAuditLog.log(
                action=ADMIN_AUDIT_ACTIONS['LOGOUT'],
                admin_id=admin_id,
                description='Admin đăng xuất.',
                ip_address=client_ip,
                user_agent=request.headers.get('User-Agent', '')[:512],
            )
            db.session.commit()
    except SQLAlchemyError as e:
        print(f'[ADMIN LOGOUT LOG ERROR] {e}')

    destroy_admin_session()
    flash('Bạn đã đăng xuất khỏi khu vực Admin.', 'success')
    return redirect(url_for('admin_login'))


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
    action_key = ADMIN_AUDIT_ACTIONS['FLAG_JOB'] if job.is_flagged else ADMIN_AUDIT_ACTIONS['UNFLAG_JOB']
    action_text = 'Đã gắn cờ vi phạm' if job.is_flagged else 'Đã khôi phục'
    _audit_log(
        action=action_key,
        target_type='job',
        target_id=job.id,
        description=f'{action_text} job "{job.title}" (ID={job.id})',
    )
    db.session.commit()
    flash(f'{action_text} bài đăng "{job.title}".', 'success')
    return redirect(url_for('admin_jobs'))

@app.route('/admin/jobs/<int:job_id>/delete', methods=['POST'])
@admin_required
def admin_delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    _audit_log(
        action=ADMIN_AUDIT_ACTIONS['DELETE_JOB'],
        target_type='job',
        target_id=job.id,
        description=f'Xóa vĩnh viễn job "{job.title}" (ID={job.id}) của hirer {job.hirer.name}',
    )
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
    action_key = ADMIN_AUDIT_ACTIONS['UNLOCK_USER'] if user.is_active else ADMIN_AUDIT_ACTIONS['LOCK_USER']
    action_text = 'kích hoạt' if user.is_active else 'khoá'
    _audit_log(
        action=action_key,
        target_type='user',
        target_id=user.id,
        description=f'Admin {action_text} tài khoản {user.name} ({user.email})',
    )
    db.session.commit()
    flash(f'Đã {action_text} tài khoản {user.name}.', 'success')
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
    action_key = ADMIN_AUDIT_ACTIONS['VERIFY_TRANSLATOR'] if profile.is_verified else ADMIN_AUDIT_ACTIONS['REJECT_TRANSLATOR']
    msg = 'Đã xác minh' if profile.is_verified else 'Đã từ chối xác minh'
    _audit_log(
        action=action_key,
        target_type='translator',
        target_id=profile.id,
        description=f'{msg} hồ sơ {profile.user.name} ({profile.user.email})',
    )
    db.session.commit()
    flash(f'{msg} hồ sơ {profile.user.name}.', 'success')
    return redirect(url_for('admin_translators'))

@app.route('/admin/reports')
@admin_required
def admin_reports():
    status_filter = request.args.get('status', 'new')
    query = Report.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    reports = query.order_by(Report.created_at.desc()).all()
    return render_template('admin_reports.html', reports=reports, status_filter=status_filter)

@app.route('/admin/reports/<int:report_id>/<action>', methods=['POST'])
@admin_required
def admin_update_report(report_id, action):
    report = Report.query.get_or_404(report_id)
    
    if action == 'investigate':
        report.status = 'investigating'
        msg = 'Đã chuyển sang trạng thái Đang điều tra'
    elif action == 'resolve':
        report.status = 'resolved'
        note = request.form.get('resolution_note')
        msg = 'Đã đánh dấu Giải quyết'
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS['RESOLVE_REPORT'],
            target_type='report',
            target_id=report.id,
            description=f'Giải quyết khiếu nại #{report.id}',
            extra_data={'note': note}
        )
    elif action == 'reject':
        report.status = 'rejected'
        reason = request.form.get('rejection_reason')
        msg = 'Đã từ chối khiếu nại'
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS['REJECT_REPORT'],
            target_type='report',
            target_id=report.id,
            description=f'Từ chối khiếu nại #{report.id}',
            extra_data={'reason': reason}
        )
    else:
        abort(400)
        
    db.session.commit()
    flash(msg, 'success')
    return redirect(url_for('admin_reports'))

@app.route('/admin/proposals')
@admin_required
def admin_proposals():
    status_filter = request.args.get('status', 'all')
    query = Proposal.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    proposals = query.order_by(Proposal.created_at.desc()).all()
    return render_template('admin_proposals.html', proposals=proposals, status_filter=status_filter)

@app.route('/admin/contracts')
@admin_required
def admin_contracts():
    status_filter = request.args.get('status', 'all')
    query = Contract.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    contracts = query.order_by(Contract.created_at.desc()).all()
    return render_template('admin_contracts.html', contracts=contracts, status_filter=status_filter)

@app.route('/admin/schedules')
@admin_required
def admin_schedules():
    status_filter = request.args.get('status', 'all')
    query = TranslatorSchedule.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    schedules = query.order_by(TranslatorSchedule.scheduled_date.desc(), TranslatorSchedule.start_time.desc()).all()
    return render_template('admin_schedules.html', schedules=schedules, status_filter=status_filter)

@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    show_filter = request.args.get('show', 'all')
    query = Review.query
    if show_filter == 'visible':
        query = query.filter_by(is_hidden=False)
    elif show_filter == 'hidden':
        query = query.filter_by(is_hidden=True)
        
    reviews = query.order_by(Review.created_at.desc()).all()
    return render_template('admin_reviews.html', reviews=reviews, show=show_filter)

@app.route('/admin/reviews/<int:review_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_review(review_id):
    r = Review.query.get_or_404(review_id)
    r.is_hidden = not r.is_hidden
    
    action_key = ADMIN_AUDIT_ACTIONS['HIDE_REVIEW'] if r.is_hidden else ADMIN_AUDIT_ACTIONS['RESTORE_REVIEW']
    msg = 'Đã ẩn đánh giá' if r.is_hidden else 'Đã khôi phục hiển thị đánh giá'
    
    _audit_log(
        action=action_key,
        target_type='review',
        target_id=r.id,
        description=f"{msg} #{r.id} của {r.reviewer.name}",
    )
    
    db.session.commit()
    flash(msg, 'success')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/payments')
@admin_required
def admin_payments():
    status_filter = request.args.get('status', 'all')
    query = PaymentTransaction.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
        
    payments = query.order_by(PaymentTransaction.created_at.desc()).all()
    return render_template('admin_payments.html', payments=payments, status_filter=status_filter)

@app.route('/admin/payments/<int:payment_id>/refund', methods=['POST'])
@admin_required
def admin_refund_payment(payment_id):
    p = PaymentTransaction.query.get_or_404(payment_id)
    if p.status != 'escrow_pending' and p.status != 'completed':
        flash('Chỉ có thể hoàn tiền các giao dịch ở trạng thái escrow_pending hoặc completed.', 'error')
        return redirect(url_for('admin_payments'))
        
    p.status = 'refunded'
    if p.contract:
        p.contract.status = 'cancelled' # hoặc trạng thái tương ứng

    _audit_log(
        action=ADMIN_AUDIT_ACTIONS['PAYMENT_ACTION'],
        target_type='payment',
        target_id=p.id,
        description=f"Admin hoàn tiền giao dịch #{p.id} (Contract #{p.contract_id})",
    )
    
    db.session.commit()
    flash('Đã hoàn tiền thành công.', 'success')
    return redirect(url_for('admin_payments'))

@app.route('/admin/notifications')
@admin_required
def admin_notifications():
    show_filter = request.args.get('show', 'all')
    query = AdminNotification.query
    if show_filter == 'unread':
        query = query.filter_by(is_read=False)
        
    notifications = query.order_by(AdminNotification.created_at.desc()).all()
    return render_template('admin_notifications.html', notifications=notifications, show=show_filter)

@app.route('/admin/notifications/<int:notif_id>/read', methods=['POST'])
@admin_required
def admin_notifications_read(notif_id):
    n = AdminNotification.query.get_or_404(notif_id)
    n.is_read = True
    db.session.commit()
    return redirect(url_for('admin_notifications'))

@app.route('/admin/notifications/read-all', methods=['POST'])
@admin_required
def admin_notifications_mark_all():
    AdminNotification.query.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('admin_notifications'))

@app.route('/admin/audit')
@admin_required
def admin_audit_logs():
    action_filter = request.args.get('action', 'all')
    query = AdminAuditLog.query
    
    if action_filter != 'all':
        if action_filter == 'AUTH':
            query = query.filter(AdminAuditLog.action.in_([
                ADMIN_AUDIT_ACTIONS['LOGIN_SUCCESS'],
                ADMIN_AUDIT_ACTIONS['LOGIN_FAILED']
            ]))
        elif action_filter == 'MODERATION':
            query = query.filter(AdminAuditLog.action.in_([
                ADMIN_AUDIT_ACTIONS['VERIFY_TRANSLATOR'],
                ADMIN_AUDIT_ACTIONS['REJECT_TRANSLATOR'],
                ADMIN_AUDIT_ACTIONS['BAN_USER'],
                ADMIN_AUDIT_ACTIONS['UNBAN_USER'],
                ADMIN_AUDIT_ACTIONS['FLAG_JOB'],
                ADMIN_AUDIT_ACTIONS['UNFLAG_JOB'],
                ADMIN_AUDIT_ACTIONS['RESOLVE_REPORT'],
                ADMIN_AUDIT_ACTIONS['REJECT_REPORT'],
                ADMIN_AUDIT_ACTIONS['HIDE_REVIEW'],
                ADMIN_AUDIT_ACTIONS['RESTORE_REVIEW']
            ]))
        elif action_filter == 'PAYMENT':
            query = query.filter(AdminAuditLog.action.in_([
                ADMIN_AUDIT_ACTIONS['PAYMENT_ACTION']
            ]))
            
    # Limit to last 50 logs for simple MVP
    logs = query.order_by(AdminAuditLog.created_at.desc()).limit(50).all()
    
    return render_template('admin_audit.html', logs=logs, action_filter=action_filter)

@app.route('/admin/admins')
@admin_required
def admin_admins():
    # Only super_admin or users with manage_admins can see all details easily
    # But let's allow all admins to view the list, just restrict actions in UI
    admins = User.query.filter_by(is_admin=True, role='admin').all()
    return render_template('admin_admins.html', admins=admins)

@app.route('/admin/admins/add', methods=['POST'])
@admin_required
def admin_add_admin():
    role = getattr(g, 'admin_role', None)
    if role != 'super_admin':
        abort(403)
        
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    admin_role = request.form.get('admin_role')
    
    if User.query.filter_by(email=email).first():
        flash('Email đã tồn tại trong hệ thống.', 'error')
        return redirect(url_for('admin_admins'))
        
    new_admin = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role='admin',
        is_admin=True,
        admin_role=admin_role,
        is_active=True
    )
    db.session.add(new_admin)
    db.session.commit()
    
    _audit_log(
        action=ADMIN_AUDIT_ACTIONS['LOGIN_SUCCESS'], # using existing enum or we can just pass a string
        target_type='admin',
        target_id=new_admin.id,
        description=f"Tạo admin mới: {email} ({admin_role})"
    )
    
    flash('Thêm Admin thành công.', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/<int:admin_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_admin_status(admin_id):
    role = getattr(g, 'admin_role', None)
    if role != 'super_admin':
        abort(403)
        
    target_admin = User.query.get_or_404(admin_id)
    if target_admin.id == session.get('admin_id'):
        flash('Không thể tự vô hiệu hóa tài khoản của chính mình.', 'error')
        return redirect(url_for('admin_admins'))
        
    target_admin.is_active = not target_admin.is_active
    db.session.commit()
    
    msg = 'Đã vô hiệu hóa admin' if not target_admin.is_active else 'Đã kích hoạt admin'
    flash(msg, 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/search')
@admin_required
def admin_search():
    q = request.args.get('q', '').strip()
    results = {'users': [], 'jobs': [], 'contracts': []}
    
    if len(q) >= 2:
        # Search users
        results['users'] = User.query.filter(
            db.or_(
                User.name.ilike(f'%{q}%'),
                User.email.ilike(f'%{q}%')
            )
        ).limit(20).all()
        
        # Search jobs
        results['jobs'] = Job.query.filter(
            db.or_(
                Job.title.ilike(f'%{q}%'),
                Job.description.ilike(f'%{q}%')
            )
        ).limit(20).all()
        
        # Search contracts (by ID if numeric)
        if q.isdigit():
            c = Contract.query.get(int(q))
            if c:
                results['contracts'].append(c)
                
    return render_template('admin_search.html', query=q, results=results)

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
    current_lang = session.get('lang') or request.cookies.get('lang') or 'vi'
    try:
        recommended = get_recommended_jobs_for_translator(session['user_id'], limit, current_lang)
        results = []
        today = date.today()
        for rec in recommended:
            job = Job.query.get(rec['job_id'])
            if job and job.status == 'open' and not job.is_flagged:
                if job.deadline and job.deadline < today:
                    continue
                results.append({
                    'id': job.id,
                    'job_id': job.id,
                    'title': job.title,
                    'category_group': job.display_category_group,
                    'category_text': job.display_category_text(current_lang),
                    'service_type': job.display_service_type,
                    'source_lang': job.source_lang,
                    'target_lang': job.target_lang,
                    'budget_min': job.budget_min,
                    'budget_max': job.budget_max,
                    'budget_type': job.budget_type or 'negotiable',
                    'event_location': job.event_location or '',
                    'event_date': job.event_date or '',
                    'applicant_count': job.applicant_count,
                    'match_score': rec['match_score'],
                    'match_reasons': rec['reasons'],
                    'match_reason': rec['reasons'][0] if rec['reasons'] else ''
                })
        return jsonify(results)
    except Exception as e:
        import logging
        logging.warning("Error fetching recommended jobs API: %s", e)
        return jsonify([])

@app.route('/api/jobs/<int:job_id>/recommended-translators', methods=['GET'])
@login_required
def api_recommended_translators(job_id):
    job = Job.query.get_or_404(job_id)
    if job.hirer_id != session['user_id']:
        abort(403)

    from services.matching import get_recommended_translators_for_job
    limit = request.args.get('limit', 10, type=int)
    current_lang = session.get('lang') or request.cookies.get('lang') or 'vi'
    # Safe execute
    try:
        recommended = get_recommended_translators_for_job(job_id, limit, current_lang)
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
@app.route('/api/cron/release-expired', methods=['GET', 'POST'])
def cron_release_expired():
    # Simple secret verification
    cron_secret = request.args.get('secret') or request.headers.get('Authorization')
    expected_secret = os.environ.get('CRON_SECRET')
    
    if not expected_secret:
        return jsonify({'error': 'CRON_SECRET not configured'}), 500
        
    if cron_secret != expected_secret and cron_secret != f'Bearer {expected_secret}':
        return jsonify({'error': 'Unauthorized'}), 401
        
    from services.scheduling import release_expired
    try:
        count = release_expired()
        return jsonify({'success': True, 'released_count': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
