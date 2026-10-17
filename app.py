import os
from dotenv import load_dotenv

load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort, Response, g, send_from_directory, send_file
from models import (
    db, User, TranslatorProfile, HirerProfile, TranslatorPreference, Service, Job, Proposal,
    SavedJob, Contract, Message, DirectMessage, Deliverable, Review, Notification, NOTIFICATION_TYPES,
    LANGUAGES, LoginAttempt, AdminAuditLog, ADMIN_AUDIT_ACTIONS, Report, PaymentTransaction,
    AdminNotification, TranslatorSchedule, JobSchedule, get_job_schedule_entries,
    validate_schedule_entries, VerificationDocument, TranslatorVerification,
    VerificationSubmissionVersion, PasswordResetToken, EmailVerificationToken, JobAttachment,
    FavoriteTranslator, ContractEvent, InterpreterService, InterpreterPreference,
    NotificationSetting, UserSession, SupportTicket
)
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
    flask_env = os.environ.get('FLASK_ENV', 'development').lower()
    if flask_env == 'production' or os.environ.get('VERCEL') == '1' or os.environ.get('RENDER'):
        error_msg = (
            "[CRITICAL] Production environment requires DATABASE_URL pointing to PostgreSQL! "
            "SQLite fallback is strictly forbidden in production."
        )
        print(error_msg, file=sys.stderr)
        raise RuntimeError(error_msg)
    else:
        # Local development: dùng SQLite file cục bộ
        db_path = os.path.join(basedir, 'instance', 'database.db')
        database_url = 'sqlite:///' + db_path
        print(f"[DB] Sử dụng SQLite cục bộ: {db_path}", file=sys.stderr)

print(f"[DB] Using: {database_url[:50]}...", file=__import__('sys').stderr)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

if 'sqlite' in database_url and ':memory:' in database_url:
    # DB in-memory cần đúng một kết nối dùng chung
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': StaticPool,
        'connect_args': {'check_same_thread': False},
    }
elif 'sqlite' in database_url:
    # SQLite file: mỗi request một kết nối riêng để transaction không giẫm lên nhau
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False, 'timeout': 15},
    }
else:
    _engine_opts = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'prepare_threshold': None,
            'connect_timeout': 10,
        },
    }
    if os.environ.get('VERCEL') == '1' or 'pooler' in database_url or ':6543' in database_url:
        # Serverless / Supabase pooler: để pooler quản lý kết nối, tránh cạn connection → "quá tải"
        from sqlalchemy.pool import NullPool
        _engine_opts['poolclass'] = NullPool
        _engine_opts.pop('pool_recycle')
    else:
        _engine_opts.update({'pool_size': 3, 'max_overflow': 2, 'pool_timeout': 15})
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = _engine_opts
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(basedir, 'static', 'uploads'))
if os.environ.get('VERCEL') == '1' or _is_memory_db:
    UPLOAD_FOLDER = '/tmp'
else:
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except OSError as e:
        if os.environ.get('FLASK_ENV') == 'production':
            raise RuntimeError(f"[CRITICAL] Failed to create UPLOAD_FOLDER at {UPLOAD_FOLDER}: {e}")
        UPLOAD_FOLDER = '/tmp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

AVATAR_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'avatars')
if os.environ.get('VERCEL') == '1' or _is_memory_db:
    AVATAR_UPLOAD_FOLDER = '/tmp/avatars'
try:
    os.makedirs(AVATAR_UPLOAD_FOLDER, exist_ok=True)
except OSError as e:
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError(f"[CRITICAL] Failed to create AVATAR_UPLOAD_FOLDER at {AVATAR_UPLOAD_FOLDER}: {e}")
    AVATAR_UPLOAD_FOLDER = '/tmp'
app.config['AVATAR_UPLOAD_FOLDER'] = AVATAR_UPLOAD_FOLDER

# Thư mục lưu trữ tài liệu riêng tư (Private Storage - Hoàn toàn ngoài static webroot)
PRIVATE_STORAGE_FOLDER = os.getenv('PRIVATE_STORAGE_FOLDER', os.path.join(basedir, 'instance', 'storage', 'private_verifications'))
if os.environ.get('VERCEL') == '1' or _is_memory_db:
    PRIVATE_STORAGE_FOLDER = '/tmp/private_verifications'
try:
    os.makedirs(PRIVATE_STORAGE_FOLDER, exist_ok=True)
except OSError as e:
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError(f"[CRITICAL] Failed to create PRIVATE_STORAGE_FOLDER at {PRIVATE_STORAGE_FOLDER}: {e}")
    PRIVATE_STORAGE_FOLDER = '/tmp/private_verifications'
app.config['PRIVATE_STORAGE_FOLDER'] = PRIVATE_STORAGE_FOLDER

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'zip', 'rar', 'png', 'jpg', 'jpeg'}
ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_avatar_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS

def save_user_avatar(file, user_id, current_avatar=None):
    """Lưu tệp ảnh đại diện được tải lên và trả về (thành_công, tên_file_hoặc_mã_lỗi)."""
    if not file or not file.filename:
        return False, 'flash.avatar_invalid_file'
    if not allowed_avatar_file(file.filename):
        return False, 'flash.avatar_invalid_file'

    try:
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
    except Exception:
        size = 0
    if size > 5 * 1024 * 1024:
        return False, 'flash.avatar_file_too_large'

    import time, shutil
    clean_uid = str(user_id)
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"avatar_u{clean_uid}_{int(time.time())}.{ext}"
    folder = app.config.get('AVATAR_UPLOAD_FOLDER', os.path.join(app.root_path, 'static', 'uploads', 'avatars'))
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    local_static_folder = os.path.join(app.root_path, 'static', 'uploads', 'avatars')
    if os.path.abspath(folder) != os.path.abspath(local_static_folder):
        try:
            os.makedirs(local_static_folder, exist_ok=True)
        except OSError:
            pass

    try:
        if current_avatar and not current_avatar.startswith('http') and not current_avatar.startswith('/static/avatars/'):
            old_base = os.path.basename(current_avatar)
            for check_dir in [folder, local_static_folder, '/var/lib/viettranslate/uploads/avatars', '/tmp/avatars']:
                if os.path.isdir(check_dir):
                    old_path = os.path.join(check_dir, old_base)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except OSError:
                            pass
        file.save(filepath)

        # Tạo bản sao tại local_static_folder để cả Nginx/Flask static đều thấy tệp
        if os.path.abspath(folder) != os.path.abspath(local_static_folder) and os.path.isdir(local_static_folder):
            try:
                shutil.copy2(filepath, os.path.join(local_static_folder, filename))
            except Exception:
                pass

        return True, filename
    except Exception as e:
        print(f"[AVATAR UPLOAD ERROR] {e}", file=sys.stderr)
        return False, 'flash.avatar_upload_failed'

def allowed_certificate_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'pdf'}

def save_certificate_file(file, user_id):
    """Lưu tệp chứng chỉ được tải lên và trả về (thành_công, tên_file_hoặc_mã_lỗi)."""
    if not file or not file.filename:
        return False, 'File không hợp lệ'
    if not allowed_certificate_file(file.filename):
        return False, 'Chỉ chấp nhận file PDF, PNG, JPG, JPEG'

    try:
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
    except Exception:
        size = 0
    if size > 10 * 1024 * 1024:
        return False, 'File chứng chỉ không được vượt quá 10MB'

    import time
    clean_uid = str(user_id)
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"cert_u{clean_uid}_{int(time.time())}.{ext}"
    folder = os.path.join(app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static', 'uploads')), 'certificates')
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    try:
        file.save(filepath)
        return True, filename
    except Exception as e:
        print(f"[CERT UPLOAD ERROR] {e}", file=sys.stderr)
        return False, 'Lỗi hệ thống khi lưu file chứng chỉ'

def delete_user_avatar(current_avatar):
    """Xóa file ảnh đại diện cũ nếu là ảnh do người dùng tải lên."""
    if not current_avatar:
        return False
    folder = app.config.get('AVATAR_UPLOAD_FOLDER', os.path.join(app.root_path, 'static', 'uploads', 'avatars'))
    local_static_folder = os.path.join(app.root_path, 'static', 'uploads', 'avatars')
    deleted = False
    if not current_avatar.startswith('http') and not current_avatar.startswith('/static/avatars/'):
        old_base = os.path.basename(current_avatar)
        for check_dir in [folder, local_static_folder, '/var/lib/viettranslate/uploads/avatars', '/tmp/avatars']:
            if os.path.isdir(check_dir):
                old_path = os.path.join(check_dir, old_base)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                        deleted = True
                    except OSError:
                        pass
    return deleted

db.init_app(app)

import sys

def _add_missing_columns():
    """Tự thêm các cột model có nhưng DB thiếu (schema drift) để tránh ProgrammingError/UndefinedColumn.

    create_all() chỉ tạo bảng mới, không thêm cột vào bảng đã tồn tại.
    Chỉ ADD COLUMN (nullable, không ràng buộc) nên an toàn và idempotent.
    """
    from sqlalchemy import inspect as _sa_inspect
    try:
        inspector = _sa_inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        for table in db.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            existing_cols = {c['name'] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing_cols:
                    continue
                col_type = col.type.compile(dialect=db.engine.dialect)
                preparer = db.engine.dialect.identifier_preparer
                stmt = f'ALTER TABLE {preparer.quote(table.name)} ADD COLUMN {preparer.quote(col.name)} {col_type}'
                _d = col.default.arg if col.default is not None and getattr(col.default, 'is_scalar', False) else None
                if isinstance(_d, bool):
                    stmt += ' DEFAULT TRUE' if _d else ' DEFAULT FALSE'
                elif isinstance(_d, (int, float)):
                    stmt += f' DEFAULT {_d}'
                try:
                    db.session.execute(db.text(stmt))
                    db.session.commit()
                    print(f"[DB MIGRATE] {stmt}", file=sys.stderr)
                except Exception as e:
                    db.session.rollback()
                    print(f"[DB MIGRATE ERROR] {stmt}: {e}", file=sys.stderr)
    except Exception as e:
        db.session.rollback()
        print(f"[DB MIGRATE] Không kiểm tra được schema: {e}", file=sys.stderr)


HIRER_COMPANY_SIZES = ('<10', '10-50', '50-200', '200+')
FREE_EMAIL_DOMAINS = {
    'gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.com.vn', 'hotmail.com', 'outlook.com',
    'live.com', 'icloud.com', 'me.com', 'msn.com', 'aol.com', 'proton.me', 'protonmail.com',
}
HIRING_FIELDS = ('Du lịch', 'Y tế', 'Đàm phán / Thương mại', 'Hội nghị / Sự kiện', 'Pháp lý / Công chứng',
                 'Giáo dục / Du học', 'Sản xuất / Kỹ thuật', 'Tài chính / Ngân hàng', 'Công nghệ / IT',
                 'Xuất nhập khẩu / Logistics', 'Khác')
HIRING_LANGUAGES = ('Tiếng Anh', 'Tiếng Trung', 'Tiếng Nhật', 'Tiếng Hàn', 'Tiếng Pháp', 'Tiếng Đức',
                    'Tiếng Nga', 'Tiếng Thái', 'Ngôn ngữ khác')
HIRING_SERVICES = ('Phiên dịch trực tiếp', 'Phiên dịch online', 'Phiên dịch tháp tùng', 'Dịch tài liệu / Biên dịch')
BUSINESS_INDUSTRIES = ('Sản xuất / Công nghiệp', 'Thương mại / Xuất nhập khẩu', 'Du lịch / Khách sạn / Nhà hàng',
                       'Y tế / Dược', 'Giáo dục / Đào tạo', 'Công nghệ / IT', 'Tài chính / Ngân hàng / Bảo hiểm',
                       'Xây dựng / Bất động sản', 'Pháp lý / Tư vấn', 'Truyền thông / Sự kiện',
                       'Logistics / Vận tải', 'Nông nghiệp / Thực phẩm', 'Tổ chức phi lợi nhuận / NGO', 'Khác')
app.jinja_env.globals.update(HIRING_FIELDS=HIRING_FIELDS, HIRING_LANGUAGES=HIRING_LANGUAGES,
                             HIRING_SERVICES=HIRING_SERVICES, BUSINESS_INDUSTRIES=BUSINESS_INDUSTRIES)
LOGO_MAX_BYTES = 300 * 1024
LOGO_MIME = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'webp': 'image/webp'}


def _read_logo_upload(file_storage):
    """Trả về (data_uri, error). File trống -> (None, None)."""
    if not file_storage or not file_storage.filename:
        return None, None
    ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else ''
    if ext not in LOGO_MIME:
        return None, 'Logo / ảnh đại diện chỉ chấp nhận PNG, JPG hoặc WEBP.'
    data = file_storage.read(LOGO_MAX_BYTES + 1)
    if len(data) > LOGO_MAX_BYTES:
        return None, 'Logo / ảnh đại diện tối đa 300KB.'
    import base64
    return f'data:{LOGO_MIME[ext]};base64,{base64.b64encode(data).decode()}', None


def _apply_hirer_profile_form(user, profile, form, files):
    """Validate và gán dữ liệu form hồ sơ khách thuê. Trả về list lỗi (rỗng = hợp lệ)."""
    import re
    errors = []
    get = lambda k: (form.get(k) or '').strip()
    phone_re = re.compile(r'^(\+84|0)\d{9,10}$')

    def clean_phone(v):
        return re.sub(r'[\s.\-]', '', v)

    def pick(name, options):
        """Chỉ nhận giá trị nằm trong danh sách có sẵn, giữ đúng thứ tự danh sách."""
        chosen = set(form.getlist(name))
        return [o for o in options if o in chosen]

    account_type = get('account_type')
    if account_type not in ('business', 'individual'):
        return ['Vui lòng chọn loại khách hàng: Doanh nghiệp / Tổ chức hoặc Cá nhân.']
    # Mỗi tài khoản chỉ thuộc một loại: đã lưu hồ sơ (có SĐT) thì không được đổi loại
    if profile.contact_phone and profile.account_type and profile.account_type != account_type:
        return ['Loại khách hàng đã được xác lập và không thể thay đổi. Mỗi tài khoản chỉ được là Doanh nghiệp / Tổ chức hoặc Cá nhân.']

    phone = clean_phone(get('contact_phone'))
    if not phone_re.match(phone):
        errors.append('Số điện thoại không hợp lệ (VD: 0912345678).')


    website = get('website')
    for label, url in (('Website / LinkedIn / Fanpage', website),):
        if url and not re.match(r'^https?://\S+$', url):
            errors.append(f'{label} phải bắt đầu bằng http:// hoặc https://')

    logo, logo_err = _read_logo_upload(files.get('logo'))
    if logo_err:
        errors.append(logo_err)

    if account_type == 'business':
        company = get('company')
        tax_code = re.sub(r'[\s\-]', '', get('tax_code'))
        industries = pick('industry', BUSINESS_INDUSTRIES)
        industry = ', '.join(industries)
        size = get('company_size')
        address = get('address')
        email = get('company_email').lower()
        rep_name = get('rep_name')
        rep_title = get('title')
        hotline = clean_phone(get('hotline'))

        if not company: errors.append('Vui lòng nhập tên công ty / tổ chức.')
        if not re.fullmatch(r'\d{10}|\d{13}', tax_code):
            errors.append('Mã số thuế phải gồm 10 hoặc 13 chữ số.')
        if not industry: errors.append('Vui lòng chọn ít nhất một lĩnh vực hoạt động.')
        if size not in HIRER_COMPANY_SIZES: errors.append('Vui lòng chọn quy mô công ty.')
        if not address: errors.append('Vui lòng nhập địa chỉ trụ sở / chi nhánh.')
        if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
            errors.append('Email doanh nghiệp không hợp lệ.')
        elif email.rsplit('@', 1)[1] in FREE_EMAIL_DOMAINS:
            errors.append('Vui lòng dùng email doanh nghiệp (dạng @tencongty.com), không dùng email miễn phí.')
        if not rep_name or not rep_title: errors.append('Vui lòng nhập họ tên và chức vụ người đại diện.')
        if hotline and not re.fullmatch(r'\+?\d{8,12}', hotline):
            errors.append('Hotline bàn không hợp lệ.')
        if errors:
            return errors

        profile.account_type = 'business'
        profile.company, profile.tax_code, profile.industry = company, tax_code, industry
        profile.company_size, profile.address, profile.company_email = size, address, email
        profile.website, profile.hotline = website, hotline
        profile.rep_name, profile.title = rep_name, rep_title
        profile.about = get('about')[:1000]
        profile.location = address[:100]
    else:
        full_name = get('full_name')
        province = get('location')
        fields = pick('hiring_field', HIRING_FIELDS)
        languages = pick('hiring_languages', HIRING_LANGUAGES)
        services = pick('hiring_services', HIRING_SERVICES)
        if not full_name: errors.append('Vui lòng nhập họ và tên.')
        if not province: errors.append('Vui lòng nhập tỉnh / thành phố.')
        if not fields: errors.append('Vui lòng chọn ít nhất một lĩnh vực thường thuê phiên dịch.')
        if errors:
            return errors

        profile.account_type = 'individual'
        user.name = full_name
        profile.location = province
        profile.hiring_field = ', '.join(fields)
        profile.hiring_languages = ', '.join(languages)
        profile.hiring_services = ', '.join(services)
        profile.about = get('about')[:500]

    from services.hirer import apply_hirer_hiring_needs
    apply_hirer_hiring_needs(profile, form)
    profile.contact_phone = phone
    user.phone = phone
    if logo:
        profile.logo = logo

    # Lưu thông tin tài khoản ngân hàng nếu có
    bank_name = get('bank_name')
    bank_acc = get('bank_account_number')
    if bank_name:
        profile.bank_name = bank_name
    if bank_acc:
        profile.bank_account_number = bank_acc

    # Lưu file giấy ủy quyền / GPKD nếu có upload
    auth_file = files.get('authorization_doc')
    if auth_file and auth_file.filename:
        from werkzeug.utils import secure_filename
        sec_name = secure_filename(f"auth_{user.id}_{int(datetime.utcnow().timestamp())}_{auth_file.filename}")
        doc_dir = os.path.join(app.root_path, 'static', 'uploads', 'hirer_docs')
        os.makedirs(doc_dir, exist_ok=True)
        auth_file.save(os.path.join(doc_dir, sec_name))
        profile.authorization_doc_url = f"/static/uploads/hirer_docs/{sec_name}"

    # Cập nhật trạng thái xác minh:
    # Người dùng điền đủ thông tin hợp lệ chỉ đưa hồ sơ vào trạng thái 'pending' chờ Admin duyệt.
    # Tuyệt đối KHÔNG tự động cấp quyền 'verified'. Quyết định phê duyệt thuộc thẩm quyền Admin.
    # Nếu hồ sơ đang ở trạng thái bị từ chối/thu hồi/đình chỉ, không tự mở lại.
    # Nếu hồ sơ đã được Admin xác minh trước đó, giữ nguyên trạng thái xác minh.
    if profile.verification_status in ('unverified', None, '', 'needs_revision'):
        profile.verification_status = 'pending'
        profile.is_verified = False
    return []


def _ensure_new_columns():
    """Tự động đồng bộ các cột còn thiếu trong DB (hỗ trợ cả PostgreSQL Supabase và SQLite)."""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        is_postgres = (db.engine.dialect.name == 'postgresql')

        with db.engine.connect() as conn:
            for name, table in db.metadata.tables.items():
                if name not in existing_tables:
                    continue
                try:
                    existing_cols = {c['name'] for c in inspector.get_columns(name)}
                except Exception:
                    continue

                for col in table.columns:
                    if col.name in existing_cols or col.name == 'id':
                        continue
                    try:
                        coltype = col.type.compile(dialect=db.engine.dialect)
                        if is_postgres:
                            conn.execute(text(f'ALTER TABLE "{name}" ADD COLUMN IF NOT EXISTS "{col.name}" {coltype}'))
                        else:
                            conn.execute(text(f'ALTER TABLE "{name}" ADD COLUMN "{col.name}" {coltype}'))
                        conn.commit()
                    except Exception as col_err:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        print(f"[DB Sync] Could not add column {name}.{col.name}: {col_err}", file=sys.stderr)
    except Exception as e:
        print(f"[DB Sync Error] {e}", file=sys.stderr)

def _ensure_columns(table, cols):
    """Bổ sung cột mới (additive, nullable) nếu DB cũ chưa có. Xem thư mục migrations/."""
    try:
        from sqlalchemy import inspect, text
        existing = {c['name'] for c in inspect(db.engine).get_columns(table)}
        for name, ddl in cols.items():
            if name not in existing:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[DB] _ensure_columns({table}) error: {e}", file=sys.stderr)


def _ensure_job_columns():
    _ensure_columns('job', {'specialty': 'VARCHAR(100)', 'word_count': 'INTEGER', 'extra_requirements': 'TEXT',
                            'updated_at': 'TIMESTAMP', 'closed_at': 'TIMESTAMP'})
    _ensure_columns('proposal', {'scope': 'TEXT', 'delivery_terms': 'TEXT', 'revision_terms': 'TEXT',
                                 'valid_until': 'DATE', 'responded_at': 'TIMESTAMP', 'response_note': 'TEXT'})
    _ensure_columns('translator_schedule', {'schedule_type': "VARCHAR(20) DEFAULT 'shift'",
                                           'note': 'VARCHAR(255)',
                                           'is_all_day': 'BOOLEAN DEFAULT 0'})


_account_schema_ensured = False

def _ensure_account_schema(force=False):
    """
    Tự động đồng bộ cấu trúc bảng và các cột của Phân hệ Tài khoản (Mục V):
    1. Bổ sung các cột mới cho notification_setting (notify_profile_view, reminder_time_*, notify_income_update, notify_security_alert, notify_marketing)
    2. Bổ sung các cột mới cho User (bio, date_of_birth, city, is_public_profile)
    3. Tạo bảng và bổ sung cột cho interpreter_service, interpreter_preference (locations), user_session, support_ticket
    Tương thích tuyệt đối cả PostgreSQL (Supabase/Vercel) và SQLite (Local/Test).
    Chạy idempotent, an toàn, không gián đoạn hoặc xung đột dữ liệu hiện có.
    """
    global _account_schema_ensured
    if _account_schema_ensured and not force:
        return

    from sqlalchemy import text, inspect
    try:
        engine_url = str(db.engine.url).lower()
        is_postgres = (db.engine.dialect.name == 'postgresql' or 'postgresql' in engine_url)

        if is_postgres:
            pg_statements = [
                # 1. Bổ sung cột cho bảng user
                'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS bio TEXT',
                'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS date_of_birth VARCHAR(20)',
                'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS city VARCHAR(100)',
                'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_public_profile BOOLEAN DEFAULT TRUE',

                # 2. Tạo bảng interpreter_service (Mục 5.2)
                '''CREATE TABLE IF NOT EXISTS interpreter_service (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                    source_lang VARCHAR(100) NOT NULL,
                    target_lang VARCHAR(100) NOT NULL,
                    interpreting_type VARCHAR(100) NOT NULL,
                    specialization VARCHAR(255),
                    hourly_rate DOUBLE PRECISION,
                    session_rate DOUBLE PRECISION,
                    currency VARCHAR(10) DEFAULT 'VND',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )''',
                'CREATE INDEX IF NOT EXISTS ix_interpreter_service_user_id ON interpreter_service (user_id)',
                'CREATE INDEX IF NOT EXISTS ix_interpreter_service_is_active ON interpreter_service (is_active)',

                # 3. Tạo bảng interpreter_preference (Mục 5.4)
                '''CREATE TABLE IF NOT EXISTS interpreter_preference (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
                    languages TEXT,
                    specializations TEXT,
                    work_mode VARCHAR(50) DEFAULT 'both',
                    min_rate DOUBLE PRECISION,
                    max_rate DOUBLE PRECISION,
                    allow_outside_rate BOOLEAN DEFAULT FALSE,
                    available_hours TEXT,
                    locations TEXT,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )''',
                'CREATE INDEX IF NOT EXISTS ix_interpreter_preference_user_id ON interpreter_preference (user_id)',
                'ALTER TABLE interpreter_preference ADD COLUMN IF NOT EXISTS locations TEXT',

                # 4. Tạo bảng notification_setting và bổ sung đầy đủ các cột mới (Mục 5.6.1)
                '''CREATE TABLE IF NOT EXISTS notification_setting (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
                    notify_job_match BOOLEAN DEFAULT TRUE,
                    notify_application_update BOOLEAN DEFAULT TRUE,
                    notify_profile_view BOOLEAN DEFAULT TRUE,
                    notify_schedule_reminder BOOLEAN DEFAULT TRUE,
                    reminder_time_60m BOOLEAN DEFAULT TRUE,
                    reminder_time_30m BOOLEAN DEFAULT TRUE,
                    reminder_time_15m BOOLEAN DEFAULT FALSE,
                    notify_income_update BOOLEAN DEFAULT TRUE,
                    notify_security_alert BOOLEAN DEFAULT TRUE,
                    notify_marketing BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )''',
                'ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_job_match BOOLEAN DEFAULT TRUE',
                'ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_application_update BOOLEAN DEFAULT TRUE',
                'ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_profile_view BOOLEAN DEFAULT TRUE',
                'ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_schedule_reminder BOOLEAN DEFAULT TRUE',
                'ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS reminder_time_60m BOOLEAN DEFAULT TRUE',
                'ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS reminder_time_30m BOOLEAN DEFAULT TRUE',
                'ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS reminder_time_15m BOOLEAN DEFAULT FALSE',
                'ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_income_update BOOLEAN DEFAULT TRUE',
                'ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_security_alert BOOLEAN DEFAULT TRUE',
                'ALTER TABLE notification_setting ADD COLUMN IF NOT EXISTS notify_marketing BOOLEAN DEFAULT FALSE',
                'CREATE INDEX IF NOT EXISTS ix_notification_setting_user_id ON notification_setting (user_id)',

                # 5. Tạo bảng user_session (Mục 5.6.2)
                '''CREATE TABLE IF NOT EXISTS user_session (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                    session_id VARCHAR(255),
                    device_name VARCHAR(255),
                    ip_address VARCHAR(50),
                    last_active TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_current BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )''',
                'CREATE INDEX IF NOT EXISTS ix_user_session_user_id ON user_session (user_id)',
                'CREATE INDEX IF NOT EXISTS ix_user_session_session_id ON user_session (session_id)',

                # 6. Tạo bảng support_ticket (Mục 5.7.3)
                '''CREATE TABLE IF NOT EXISTS support_ticket (
                    id SERIAL PRIMARY KEY,
                    ticket_code VARCHAR(50) NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                    category VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    attachment_url TEXT,
                    status VARCHAR(50) DEFAULT 'open',
                    admin_reply TEXT,
                    admin_reply_at TIMESTAMP WITHOUT TIME ZONE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )''',
                'CREATE INDEX IF NOT EXISTS ix_support_ticket_user_id ON support_ticket (user_id)',
                'CREATE INDEX IF NOT EXISTS ix_support_ticket_ticket_code ON support_ticket (ticket_code)',
                'CREATE INDEX IF NOT EXISTS ix_support_ticket_status ON support_ticket (status)',
            ]

            with db.engine.connect() as conn:
                for sql_stmt in pg_statements:
                    try:
                        conn.execute(text(sql_stmt))
                        conn.commit()
                    except Exception as pg_err:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        print(f"[Account Schema Sync PG] Non-fatal: {pg_err}", file=sys.stderr)
        else:
            # SQLite (Local Dev / Tests)
            inspector = inspect(db.engine)
            existing_tables = set(inspector.get_table_names())

            # Bảng user
            if 'user' in existing_tables:
                user_cols = {c['name'] for c in inspector.get_columns('user')}
                for col, typ in [('bio', 'TEXT'), ('date_of_birth', 'VARCHAR(20)'), ('city', 'VARCHAR(100)'), ('is_public_profile', 'BOOLEAN DEFAULT 1')]:
                    if col not in user_cols:
                        with db.engine.connect() as conn:
                            try:
                                conn.execute(text(f'ALTER TABLE "user" ADD COLUMN {col} {typ}'))
                                conn.commit()
                            except Exception:
                                conn.rollback()

            # Bảng notification_setting
            if 'notification_setting' in existing_tables:
                notif_cols = {c['name'] for c in inspector.get_columns('notification_setting')}
                notif_fields = [
                    ('notify_job_match', 'BOOLEAN DEFAULT 1'),
                    ('notify_application_update', 'BOOLEAN DEFAULT 1'),
                    ('notify_profile_view', 'BOOLEAN DEFAULT 1'),
                    ('notify_schedule_reminder', 'BOOLEAN DEFAULT 1'),
                    ('reminder_time_60m', 'BOOLEAN DEFAULT 1'),
                    ('reminder_time_30m', 'BOOLEAN DEFAULT 1'),
                    ('reminder_time_15m', 'BOOLEAN DEFAULT 0'),
                    ('notify_income_update', 'BOOLEAN DEFAULT 1'),
                    ('notify_security_alert', 'BOOLEAN DEFAULT 1'),
                    ('notify_marketing', 'BOOLEAN DEFAULT 0'),
                ]
                for col, typ in notif_fields:
                    if col not in notif_cols:
                        with db.engine.connect() as conn:
                            try:
                                conn.execute(text(f'ALTER TABLE notification_setting ADD COLUMN {col} {typ}'))
                                conn.commit()
                            except Exception:
                                conn.rollback()

            # Bảng interpreter_preference
            if 'interpreter_preference' in existing_tables:
                pref_cols = {c['name'] for c in inspector.get_columns('interpreter_preference')}
                if 'locations' not in pref_cols:
                    with db.engine.connect() as conn:
                        try:
                            conn.execute(text('ALTER TABLE interpreter_preference ADD COLUMN locations TEXT'))
                            conn.commit()
                        except Exception:
                            conn.rollback()

            # Tạo các bảng thiếu nếu chưa có bằng db.create_all()
            try:
                db.create_all()
            except Exception:
                pass

        _account_schema_ensured = True
        print("[DB Sync] Phân hệ Tài khoản: Đã đồng bộ schema thành công.", file=sys.stderr)
    except Exception as e:
        print(f"[Account Schema Sync Error] {e}", file=sys.stderr)


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

        from sqlalchemy import text
        is_postgres = (db.engine.dialect.name == 'postgresql')
        with db.engine.connect() as conn:
            alter_statements = [
                'ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "image_url" TEXT' if is_postgres else 'ALTER TABLE message ADD COLUMN image_url TEXT',
                'ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "image_url" TEXT' if is_postgres else 'ALTER TABLE direct_message ADD COLUMN image_url TEXT',
            ]
            for stmt in alter_statements:
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
    except Exception as e:
        print(f"[DB] db.create_all() or migration error: {e}", file=sys.stderr)
        db.session.rollback()
        # Vẫn phải bù cột thiếu, nếu không mọi truy vấn User sẽ lỗi UndefinedColumn
        _add_missing_columns()
        return

    _ensure_new_columns()
    _ensure_job_columns()
    _ensure_account_schema()
    _add_missing_columns()

    try:
        # Thực hiện một query giả để SQLAlchemy fetch toàn bộ column của User và kiểm tra schema drift
        dummy_user = db.session.query(User).first()
        # Fetch thử một số Model khác để kiểm tra
        dummy_schedule = db.session.query(TranslatorSchedule).first()
        user_count = db.session.execute(db.select(db.func.count()).select_from(User)).scalar()
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        if "UndefinedColumn" in error_msg or "no such column" in error_msg.lower():
            print(f"\\n{'='*50}\\n[CRITICAL DB ERROR] DATABASE SCHEMA DRIFT DETECTED!\\nLỗi thiếu column trong database: {error_msg}\\n=> HÃY CHẠY MIGRATION SCRIPT (migration_sync_current_schema.sql)\\n{'='*50}\\n", file=sys.stderr)
        else:
            print(f"[DB] Cannot query database during init: {e}", file=sys.stderr)
        user_count = 1  # Giả định đã có data, không seed

    if user_count == 0:
        # CHẶN TUYỆT ĐỐI SEED DATA TRÊN PRODUCTION
        if os.getenv('FLASK_ENV') == 'production':
            print("[SECURITY] Môi trường Production: Tự động seed data bị vô hiệu hóa để bảo vệ an toàn.", file=sys.stderr)
        else:
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

# Trên Vercel (serverless) KHÔNG chạy create_all/seed ở mỗi cold start vì rất chậm
# (hàng chục round-trip tới DB). Chạy thủ công bằng INIT_DB=1 hoặc script migration.
_db_ready = False
_SKIP_AUTO_INIT = os.environ.get('VERCEL') == '1' and os.environ.get('INIT_DB') != '1'

if not _SKIP_AUTO_INIT:
    try:
        with app.app_context():
            _init_db()
        _db_ready = True
    except Exception as e:
        db.session.rollback()
        print(f"[DB INIT ERROR] {e}", file=sys.stderr)


@app.after_request
def _static_cache(resp):
    if request.path.startswith('/static/') and resp.status_code == 200:
        resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


@app.errorhandler(500)
def handle_500(e):
    import uuid
    import logging
    error_id = uuid.uuid4().hex[:8]
    logging.error(f"[ERROR 500 - Ref: {error_id}] {e}", exc_info=True)
    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/')
    if is_ajax:
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': 'Đã có lỗi hệ thống phát sinh. Vui lòng thử lại sau ít phút.',
            'ref': error_id
        }), 500
    if os.getenv('FLASK_ENV') == 'development' and app.debug:
        import traceback
        tb = traceback.format_exc()
        return f"<pre>500 Debug Error (Ref {error_id}):\n{e}\n\nTraceback:\n{tb}</pre>", 500
    try:
        return render_template('500.html', error_ref=error_id), 500
    except Exception:
        return (
            f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>500 - Lỗi hệ thống</title>"
            f"<style>body{{font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#f8fafc;color:#1e293b}} "
            f".box{{background:#fff;padding:2.5rem;border-radius:1rem;box-shadow:0 10px 25px rgba(0,0,0,0.05);max-width:480px;text-align:center}} "
            f"h1{{font-size:1.8rem;margin-bottom:0.5rem;color:#e11d48}} p{{color:#64748b;line-height:1.6}} "
            f".code{{font-family:monospace;background:#f1f5f9;padding:0.25rem 0.5rem;border-radius:0.25rem;font-size:0.875rem}} "
            f"a{{display:inline-block;margin-top:1.5rem;background:#2563eb;color:#fff;padding:0.75rem 1.5rem;border-radius:0.5rem;text-decoration:none;font-weight:bold}}</style></head>"
            f"<body><div class='box'><h1>500 - Lỗi hệ thống</h1>"
            f"<p>Hệ thống đang gặp sự cố gián đoạn tạm thời. Vui lòng thử lại sau ít phút.</p>"
            f"<p>Mã tham chiếu hỗ trợ: <span class='code'>ERR-{error_id.upper()}</span></p>"
            f"<a href='/'>Về trang chủ</a></div></body></html>"
        ), 500

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

# Defensive fallback cho templates: đăng ký hasattr và getattr vào Jinja globals
app.jinja_env.globals['hasattr'] = hasattr
app.jinja_env.globals['getattr'] = getattr


# Context processor: Badge counts và helpers cho Admin sidebar
@app.context_processor
def inject_admin_badges():
    """
    Inject badge counts vào tất cả Admin templates.
    Chỉ query DB khi đang ở admin session để tránh overhead cho user thường.
    """
    default_badges = {
        'admin_badge_pending_translators': 0,
        'admin_badge_pending_verifications': 0,
        'admin_badge_pending_hirers': 0,
        'admin_badge_pending_jobs': 0,
        'admin_badge_flagged_jobs': 0,
        'admin_badge_reports': 0,
        'admin_badge_notifications': 0,
    }
    if not session.get(ADMIN_SESSION_KEY):
        return {**default_badges, 'badge_counts': default_badges}

    badges = dict(default_badges)
    try:
        from models import TranslatorVerification, HirerProfile
        badges['admin_badge_pending_translators'] = TranslatorProfile.query.filter_by(is_verified=False).count()
        badges['admin_badge_pending_verifications'] = TranslatorVerification.query.filter_by(status='pending').count()
        badges['admin_badge_pending_hirers'] = HirerProfile.query.filter_by(verification_status='pending').count()
        badges['admin_badge_pending_jobs'] = Job.query.filter(
            db.or_(Job.moderation_status == 'pending', db.and_(Job.status == 'pending', Job.moderation_status.is_(None))),
            db.or_(Job.is_flagged == False, Job.is_flagged.is_(None))
        ).count()
        badges['admin_badge_flagged_jobs'] = Job.query.filter_by(is_flagged=True).count()
        badges['admin_badge_reports'] = Report.query.filter_by(status='new').count()
        badges['admin_badge_notifications'] = AdminNotification.query.filter_by(is_read=False).count()
    except Exception:
        db.session.rollback()
    badges['badge_counts'] = badges.copy()
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
        
        user = get_current_user()
        if not user:
            flash("Tài khoản của bạn đã bị vô hiệu hóa hoặc phiên đăng nhập không hợp lệ.", "error")
            return redirect(url_for('login'))
            
        return f(*args, **kwargs)
    return decorated

def email_verified_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash(_t('flash.login_required'), 'warning')
            return redirect(url_for('login'))
        
        user = get_current_user()
        if not user or not user.is_active:
            flash("Tài khoản của bạn đã bị vô hiệu hóa.", "error")
            return redirect(url_for('login'))
            
        if not app.config.get('TESTING') and not user.email_verified:
            flash("Bạn cần xác minh địa chỉ email để thực hiện chức năng này.", "warning")
            return redirect(url_for('account_profile'))
            
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

@app.template_filter('vnd')
def vnd_filter(value):
    try:
        return '{:,.0f}'.format(float(value))
    except (ValueError, TypeError):
        return value

# TASK 5 + TASK 9: get_current_user và inject_globals dùng SQL only.
# Legacy Auth object đã được loại bỏ.

def get_current_user():
    """Trả về User object của người đang đăng nhập từ session hiện tại.
    SQL only.
    TASK 9: Nếu session có user_id không phải integer -> clear session.
    Trả về None nếu chưa đăng nhập hoặc user không còn tồn tại.
    """
    uid = session.get('user_id')
    if not uid:
        return None
    # TASK 9: Clear invalid/legacy session và yêu cầu login lại
    if not isinstance(uid, int):
        session.clear()
        return None
    try:
        user = User.query.get(uid)
        if user and not user.is_active:
            session.clear()
            return None

        # Kiểm tra tính hợp lệ của phiên đăng nhập (Session Revocation Check - Mục 5.6.2)
        token = session.get('session_token')
        if token and user:
            from models import UserSession
            user_sess = UserSession.query.filter_by(user_id=user.id, session_id=token).first()
            if not user_sess:
                # Phiên đã bị thu hồi ở backend từ thiết bị khác -> Hủy session ngay lập tức
                session.clear()
                return None
            # Cập nhật thời gian hoạt động gần nhất (giảm tải DB: chỉ commit nếu cách hơn 60s)
            now = datetime.utcnow()
            if user_sess.last_active is None or (now - user_sess.last_active).total_seconds() > 60:
                user_sess.last_active = now
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

        return user
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"[get_current_user SQLError] {e}")
        return None


@app.context_processor
def inject_globals():
    # TASK 5: context processor dùng SQL only.
    # TASK 9: Nếu session không hợp lệ → clear, user sẽ thấy màn hình login.
    user = None
    uid = session.get('user_id')
    if uid:
        # TASK 9: Clear legacy/invalid session
        if not isinstance(uid, int):
            session.clear()
            uid = None
        else:
            try:
                user = User.query.get(uid)
                if not user:
                    session.pop('user_id', None)
            except SQLAlchemyError as e:
                db.session.rollback()
                print(f"[AUTH SQL GLOBALS ERROR] {e}")
                # Do not pop session on transient DB locks to prevent random logout
            except Exception as e:
                db.session.rollback()
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
@app.route('/index')
def index():
    try:
        from sqlalchemy.orm import joinedload
        top_translators = TranslatorProfile.query.options(joinedload(TranslatorProfile.user)).join(User).filter(
            TranslatorProfile.is_verified == True,
            User.is_active == True
        ).order_by(TranslatorProfile.rating.desc()).limit(4).all()
        
        latest_jobs = Job.query.options(joinedload(Job.hirer)).join(User, Job.hirer_id == User.id).filter(
            Job.status == 'open', 
            db.or_(Job.is_flagged == False, Job.is_flagged == None),
            User.is_active == True
        ).order_by(Job.created_at.desc()).limit(4).all()
        return render_template('index.html', top_translators=top_translators, latest_jobs=latest_jobs)
    except Exception as e:
        db.session.rollback()
        print(f"[INDEX ERROR] {e}", file=sys.stderr)
        try:
            return render_template('index.html', top_translators=[], latest_jobs=[])
        except Exception:
            return "Internal Server Error", 500


@app.route('/interpreter/dashboard')
@login_required
def interpreter_dashboard():
    """Trang Tổng quan dành riêng cho phiên dịch viên."""
    from datetime import date as date_cls, timedelta
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if user.role != 'translator':
        return redirect(url_for('index'))

    uid = user.id

    # ── 1. Hồ sơ & xác minh ──────────────────────────────────────────────────
    profile = user.profile
    preference = getattr(user, 'preference', None)

    # Tiêu chí hoàn thiện hồ sơ có căn cứ rõ ràng từ các trường dữ liệu thực tế (100% tổng thể):
    # 1. Họ và tên: 15% (user.name)
    # 2. Ảnh đại diện: 10% (user.avatar hoặc user.avatar_url)
    # 3. Số điện thoại: 10% (user.phone)
    # 4. Tiêu đề chuyên môn: 15% (profile.title)
    # 5. Ngôn ngữ thông thạo: 20% (profile.languages)
    # 6. Giới thiệu bản thân: 15% (profile.bio)
    # 7. Cài đặt nhận việc / Dịch vụ: 15% (preference.service_types hoặc profile.services)
    profile_completeness = 0
    profile_missing = []

    # 1. Họ và tên
    if user.name and user.name.strip():
        profile_completeness += 15
    else:
        profile_missing.append('Họ và tên')

    # 2. Ảnh đại diện cá nhân
    if getattr(user, 'avatar', None) or getattr(user, 'avatar_url', None):
        profile_completeness += 10
    else:
        profile_missing.append('Ảnh đại diện')

    # 3. Số điện thoại
    if user.phone and user.phone.strip():
        profile_completeness += 10
    else:
        profile_missing.append('Số điện thoại')

    # 4. Tiêu đề chuyên môn
    if profile and profile.title and profile.title.strip():
        profile_completeness += 15
    else:
        profile_missing.append('Tiêu đề chuyên môn')

    # 5. Ngôn ngữ thông thạo
    if profile and profile.languages and profile.languages.strip():
        profile_completeness += 20
    else:
        profile_missing.append('Ngôn ngữ thông thạo')

    # 6. Giới thiệu bản thân
    if profile and profile.bio and profile.bio.strip():
        profile_completeness += 15
    else:
        profile_missing.append('Giới thiệu bản thân')

    # 7. Cài đặt nhận việc / Dịch vụ
    has_services = False
    if profile and getattr(profile, 'services', None) and len(profile.services) > 0:
        has_services = True
    elif preference and getattr(preference, 'service_types', None) and preference.service_types.strip():
        has_services = True

    if has_services:
        profile_completeness += 15
    else:
        profile_missing.append('Dịch vụ / Cài đặt nhận việc')

    # Đảm bảo phần trăm nằm chính xác trong khoảng 0 - 100
    profile_completeness = max(0, min(100, int(profile_completeness)))

    # Xác định trạng thái xác minh thực tế (dựa trên hồ sơ và yêu cầu thẩm định):
    verif_req = None
    try:
        verif_req = getattr(user, 'latest_verification', None)
    except Exception:
        verif_req = None

    if not profile:
        verification_status = {
            'code': 'no_profile',
            'label': 'Chưa tạo hồ sơ',
            'color': 'slate',
            'badge_bg': 'bg-slate-100',
            'badge_text': 'text-slate-600',
            'badge_border': 'border-slate-200',
            'tooltip': 'Chưa có thông tin hồ sơ phiên dịch viên.',
            'action_hint': 'Vui lòng khởi tạo hồ sơ cá nhân.',
        }
    elif profile.is_verified or (verif_req and getattr(verif_req, 'status', None) in ('approved', 'verified')):
        verification_status = {
            'code': 'verified',
            'label': 'Đã xác minh',
            'color': 'emerald',
            'badge_bg': 'bg-emerald-50',
            'badge_text': 'text-emerald-700',
            'badge_border': 'border-emerald-200',
            'tooltip': 'Hồ sơ và chứng chỉ đã được Ban quản trị VietTranslate kiểm duyệt & chứng nhận.',
            'action_hint': 'Hồ sơ đã được cấp huy hiệu uy tín.',
        }
    elif verif_req and getattr(verif_req, 'status', None) in ('needs_revision', 'revision_requested'):
        verification_status = {
            'code': 'needs_revision',
            'label': 'Cần bổ sung',
            'color': 'amber',
            'badge_bg': 'bg-amber-50',
            'badge_text': 'text-amber-700',
            'badge_border': 'border-amber-200',
            'tooltip': 'Ban quản trị yêu cầu bổ sung thông tin hoặc tài liệu xác minh.',
            'action_hint': 'Cần bổ sung tài liệu theo yêu cầu của Admin.',
        }
    elif verif_req and getattr(verif_req, 'status', None) == 'rejected':
        verification_status = {
            'code': 'rejected',
            'label': 'Bị từ chối',
            'color': 'rose',
            'badge_bg': 'bg-rose-50',
            'badge_text': 'text-rose-700',
            'badge_border': 'border-rose-200',
            'tooltip': 'Hồ sơ xác minh chưa đạt yêu cầu của Ban quản trị.',
            'action_hint': 'Xem lý do từ chối và nộp lại hồ sơ.',
        }
    elif (verif_req and getattr(verif_req, 'status', None) in ('pending', 'in_review')) or (profile.badges and profile.badges.strip()):
        verification_status = {
            'code': 'pending',
            'label': 'Đang chờ duyệt',
            'color': 'blue',
            'badge_bg': 'bg-blue-50',
            'badge_text': 'text-blue-700',
            'badge_border': 'border-blue-200',
            'tooltip': 'Bạn đã cung cấp chứng chỉ. Hồ sơ đang trong danh sách chờ Ban quản trị xét duyệt.',
            'action_hint': 'Đang chờ Ban quản trị duyệt chứng chỉ.',
        }
    else:
        verification_status = {
            'code': 'unverified',
            'label': 'Chưa xác minh',
            'color': 'amber',
            'badge_bg': 'bg-amber-50',
            'badge_text': 'text-amber-700',
            'badge_border': 'border-amber-200',
            'tooltip': 'Chưa nộp chứng chỉ. Nhấn để bổ sung chứng chỉ (IELTS, JLPT, HSK...) và gửi duyệt.',
            'action_hint': 'Cần bổ sung chứng chỉ để xác minh.',
        }

    # ── 2. Thống kê công việc (Đồng bộ 100% với trang Thống kê công việc /job-statistics) ─────────
    today = date_cls.today()

    all_user_proposals = Proposal.query.filter_by(translator_id=uid).all()
    all_user_contracts = Contract.query.filter_by(translator_id=uid).all()

    try:
        saved_records = SavedJob.query.filter_by(user_id=uid).all()
        saved_jobs_count = len([s.job for s in saved_records if s.job])
    except Exception:
        db.session.rollback()
        saved_jobs_count = 0

    # 4 chỉ số chính đồng bộ chuẩn xác với trang Thống kê công việc:
    # 1. Đang ứng tuyển: Đang chờ phản hồi / đang xem xét / cần phản hồi / được chọn chờ xác nhận
    pending_review_proposals = [p for p in all_user_proposals if p.effective_status in ['pending', 'reviewing', 'needs_response', 'selected']]
    pending_review_count = len(pending_review_proposals)

    # 2. Đã nhận: Hợp đồng đã tạo và sẵn sàng / ký quỹ
    accepted_upcoming_contracts = [c for c in all_user_contracts if c.shift_status_info['code'] in ['escrow_pending', 'upcoming']]
    accepted_count = len(accepted_upcoming_contracts)

    # 3. Đang thực hiện: Ca đang diễn ra & ca chờ xác nhận hoàn thành (delivered)
    in_progress_contracts = [c for c in all_user_contracts if c.shift_status_info['code'] == 'in_progress']
    in_progress_count = len(in_progress_contracts)
    delivered_contracts = [c for c in all_user_contracts if c.status == 'delivered']
    delivered_count = len(delivered_contracts)
    in_progress_total = in_progress_count + delivered_count

    # 4. Đã hoàn thành: Đã nghiệm thu xong
    completed_contracts = [c for c in all_user_contracts if c.status in ['completed', 'reviewed']]
    completed_count = len(completed_contracts)

    proposals_all = all_user_proposals
    proposals_pending = pending_review_proposals
    proposals_accepted = [p for p in all_user_proposals if p.status == 'accepted']
    pending_proposals_count = pending_review_count

    # Hợp đồng của interpreter phục vụ các phần khác
    contracts_all = all_user_contracts
    contracts_active = [c for c in contracts_all if c.status in ('escrow_held', 'in_progress', 'active')]
    contracts_done = [c for c in contracts_all if c.status in ('completed', 'reviewed')]
    contracts_pending_payment = [c for c in contracts_all if c.status == 'escrow_pending']

    # translator schedules cho ca làm sắp tới
    all_schedules = TranslatorSchedule.query.filter_by(translator_id=uid).all()
    upcoming_schedules_all = [
        s for s in all_schedules
        if s.scheduled_date and s.scheduled_date >= today and s.status in ('reserved', 'active')
    ]
    scheduled_contract_ids = {s.contract_id for s in upcoming_schedules_all if s.contract_id}
    extra_active_contracts = [c for c in contracts_active if c.id not in scheduled_contract_ids]
    upcoming_shifts_count = len(upcoming_schedules_all) + len(extra_active_contracts)

    metrics = {
        'total_applications': len(all_user_proposals),
        'pending_review':     pending_review_count,
        'accepted':           accepted_count,
        'in_progress':        in_progress_count,
        'in_progress_total':  in_progress_total,
        'delivered':          delivered_count,
        'completed':          completed_count,
        'saved':              saved_jobs_count,
    }

    job_stats = {
        'pending_review':     pending_review_count,
        'accepted':           accepted_count,
        'in_progress':        in_progress_count,
        'in_progress_total':  in_progress_total,
        'completed':          completed_count,
        'pending_proposals':  pending_review_count,
        'upcoming_shifts':    accepted_count,
        'completed_shifts':   completed_count,
        'total_contracts':    len(contracts_all),
        'active_contracts':   in_progress_total,
        'completed_contracts': completed_count,
        'accepted_proposals': len(proposals_accepted),
        'rating':             profile.rating if profile else 0.0,
        'total_reviews':      profile.total_reviews if profile else 0,
    }

    # ── 3. Thống kê thu nhập (từ contracts completed có agreed_price) ─────────
    import calendar
    first_of_month = today.replace(day=1)
    _, last_day = calendar.monthrange(today.year, today.month)
    end_of_month = today.replace(day=last_day)
    period_label = f"Tháng {today.month:02d}/{today.year}"
    period_range = f"01/{today.month:02d} - {last_day:02d}/{today.month:02d}/{today.year}"

    # 1. Thu nhập trong kỳ hiện tại: Hợp đồng hoàn tất (nghiệm thu giải ngân) trong tháng hiện tại
    monthly_contracts = [
        c for c in contracts_done
        if c.updated_at and c.updated_at.date() >= first_of_month and c.updated_at.date() <= end_of_month
    ]
    monthly_earned = sum(c.agreed_price for c in monthly_contracts if c.agreed_price)

    # 2. Thu nhập đã thanh toán: Tổng các khoản thực sự đã thanh toán (nghiệm thu/giải ngân tích lũy)
    total_earned = sum(c.agreed_price for c in contracts_done if c.agreed_price)

    # 3. Khoản thu nhập đang chờ xử lý:
    # - Tiền đang giữ an toàn trong Escrow cho các hợp đồng đang thực hiện (in_progress, active, escrow_held)
    pending_payout = sum(c.agreed_price for c in contracts_active if c.agreed_price)
    # - Khoản chờ khách nạp tiền ký quỹ Escrow (escrow_pending)
    escrow_pending_amount = sum(c.agreed_price for c in contracts_pending_payment if c.agreed_price)

    # 4. Chuỗi dữ liệu biến động thu nhập 6 tháng gần nhất cho biểu đồ
    chart_months = []
    for offset in range(5, -1, -1):
        m = today.month - offset
        y = today.year
        while m <= 0:
            m += 12
            y -= 1

        # Lọc hợp đồng hoàn tất trong tháng (y, m)
        m_contracts = [
            c for c in contracts_done
            if c.updated_at and c.updated_at.year == y and c.updated_at.month == m
        ]
        m_earned = sum(c.agreed_price for c in m_contracts if c.agreed_price)
        chart_months.append({
            'year': y,
            'month': m,
            'label': f"Thg {m:02d}",
            'short_label': f"T{m}",
            'full_label': f"Tháng {m:02d}/{y}",
            'earned': m_earned,
            'count': len(m_contracts),
            'is_current': (offset == 0)
        })

    max_chart_earned = max((item['earned'] for item in chart_months), default=0)
    total_chart_earned = sum(item['earned'] for item in chart_months)
    has_chart_data = any(item['earned'] > 0 for item in chart_months)

    # Tọa độ SVG cho biểu đồ vector nội tại (kích thước viewBox 0 0 600 180)
    svg_width = 600
    svg_height = 180
    pad_x = 45
    pad_top = 25
    pad_bottom = 35
    plot_w = svg_width - 2 * pad_x
    plot_h = svg_height - pad_top - pad_bottom
    ceiling = max(int(max_chart_earned * 1.15), 1000000) if max_chart_earned > 0 else 1000000

    chart_points = []
    num_pts = len(chart_months)
    step_x = plot_w / (num_pts - 1) if num_pts > 1 else plot_w

    for idx, item in enumerate(chart_months):
        x = round(pad_x + idx * step_x, 1)
        val = item['earned']
        if max_chart_earned > 0:
            y = round(pad_top + plot_h * (1.0 - (val / ceiling)), 1)
        else:
            y = round(pad_top + plot_h, 1)
        chart_points.append({
            'x': x,
            'y': y,
            'earned': val,
            'count': item['count'],
            'label': item['label'],
            'short_label': item['short_label'],
            'full_label': item['full_label'],
            'is_current': item['is_current']
        })

    line_path = ""
    baseline_y = round(pad_top + plot_h, 1)
    if chart_points:
        line_path = f"M {chart_points[0]['x']} {chart_points[0]['y']}"
        for i in range(len(chart_points) - 1):
            p0 = chart_points[max(0, i - 1)]
            p1 = chart_points[i]
            p2 = chart_points[i + 1]
            p3 = chart_points[min(len(chart_points) - 1, i + 2)]

            cp1x = round(p1['x'] + (p2['x'] - p0['x']) / 6.0, 1)
            cp1y = round(p1['y'] + (p2['y'] - p0['y']) / 6.0, 1)
            cp2x = round(p2['x'] - (p3['x'] - p1['x']) / 6.0, 1)
            cp2y = round(p2['y'] - (p3['y'] - p1['y']) / 6.0, 1)
            line_path += f" C {cp1x} {cp1y}, {cp2x} {cp2y}, {p2['x']} {p2['y']}"

        area_path = f"{line_path} L {chart_points[-1]['x']} {baseline_y} L {chart_points[0]['x']} {baseline_y} Z"
    else:
        area_path = ""

    grid_lines = [
        {'y': round(pad_top, 1), 'val': ceiling},
        {'y': round(pad_top + plot_h * 0.5, 1), 'val': int(ceiling * 0.5)},
        {'y': baseline_y, 'val': 0}
    ]

    income_chart_data = {
        'months': chart_months,
        'points': chart_points,
        'line_path': line_path,
        'area_path': area_path,
        'baseline_y': baseline_y,
        'grid_lines': grid_lines,
        'max_earned': max_chart_earned,
        'total_earned': total_chart_earned,
        'has_data': has_chart_data,
        'ceiling': ceiling,
        'start_month': chart_months[0]['label'] if chart_months else '',
        'end_month': chart_months[-1]['label'] if chart_months else ''
    }

    income_stats = {
        'total_earned':              total_earned,
        'monthly_earned':            monthly_earned,
        'pending_payout':            pending_payout,
        'escrow_pending_amount':     escrow_pending_amount,
        'period_label':              period_label,
        'period_range':              period_range,
        'period_start':              f"01/{today.month:02d}/{today.year}",
        'period_end':                f"{last_day:02d}/{today.month:02d}/{today.year}",
        'monthly_contracts_count':   len(monthly_contracts),
        'completed_contracts_count': len(contracts_done),
        'active_contracts_count':    len(contracts_active),
        'escrow_pending_count':      len(contracts_pending_payment),
        'chart_data':                income_chart_data,
    }

    # ── 4. Ca làm sắp tới (Sắp xếp tăng dần theo thời điểm bắt đầu) ────────
    from datetime import datetime as dt_cls, time as time_cls
    from services.schedule import _parse_date, _parse_time
    now = dt_cls.now()
    now_time = now.time()

    WEEKDAYS_VN = {
        0: 'Thứ Hai',
        1: 'Thứ Ba',
        2: 'Thứ Tư',
        3: 'Thứ Năm',
        4: 'Thứ Sáu',
        5: 'Thứ Bảy',
        6: 'Chủ Nhật'
    }

    upcoming_shifts_list = []
    seen_contract_ids = set()

    # Nguồn 1: Các lịch đặt trong TranslatorSchedule (status reserved hoặc active)
    for sch in upcoming_schedules_all:
        if not sch.scheduled_date:
            continue
        # Bỏ qua ca đã qua trong ngày hôm nay nếu end_time đã kết thúc và không còn active
        if sch.scheduled_date == today and sch.end_time and sch.end_time < now_time and sch.status != 'active':
            continue

        c = sch.contract
        j = sch.job or (c.job if c else None)
        s = sch.service or (c.service if c else None)

        if c:
            seen_contract_ids.add(c.id)

        # Tiêu đề ca làm việc
        title = None
        if j and j.title:
            title = j.title
        elif s and s.name:
            title = s.name
        elif c:
            title = f"Hợp đồng phiên dịch #{c.id}"
        else:
            title = f"Ca phiên dịch #{sch.id}"

        # Hình thức làm việc & Địa điểm
        raw_location = (c.location if c and c.location else (j.event_location if j and j.event_location else '')).strip()
        is_onsite = bool(raw_location and not any(k in raw_location.lower() for k in ['online', 'từ xa', 'remote', 'zoom', 'teams', 'google meet']))
        work_mode = {
            'type': 'onsite' if is_onsite else 'online',
            'label': 'Trực tiếp' if is_onsite else 'Trực tuyến',
            'location': raw_location if is_onsite else 'Online / Từ xa'
        }

        # Trạng thái ca làm việc
        is_active_now = (sch.status == 'active' or (sch.scheduled_date == today and sch.start_time and sch.start_time <= now_time and sch.end_time and sch.end_time >= now_time))
        if is_active_now:
            status_meta = {
                'code': 'active',
                'label': 'Đang diễn ra',
                'badge_bg': 'bg-emerald-50',
                'badge_text': 'text-emerald-700',
                'badge_border': 'border-emerald-200',
                'dot_color': 'bg-emerald-500 animate-pulse'
            }
        elif sch.status == 'active':
            status_meta = {
                'code': 'confirmed',
                'label': 'Đã xác nhận',
                'badge_bg': 'bg-blue-50',
                'badge_text': 'text-blue-700',
                'badge_border': 'border-blue-200',
                'dot_color': 'bg-blue-500'
            }
        else:
            status_meta = {
                'code': 'reserved',
                'label': 'Chờ bắt đầu',
                'badge_bg': 'bg-amber-50',
                'badge_text': 'text-amber-700',
                'badge_border': 'border-amber-200',
                'dot_color': 'bg-amber-500'
            }

        # Nhãn thời gian tương đối
        delta_days = (sch.scheduled_date - today).days
        if delta_days == 0:
            relative_badge = 'Hôm nay'
            badge_color = 'bg-rose-50 text-rose-700 border-rose-200'
        elif delta_days == 1:
            relative_badge = 'Ngày mai'
            badge_color = 'bg-amber-50 text-amber-700 border-amber-200'
        elif delta_days <= 3:
            relative_badge = f'Trong {delta_days} ngày'
            badge_color = 'bg-blue-50 text-blue-700 border-blue-200'
        else:
            relative_badge = WEEKDAYS_VN.get(sch.scheduled_date.weekday(), f'+{delta_days} ngày')
            badge_color = 'bg-slate-100 text-slate-700 border-slate-200'

        start_str = sch.start_time.strftime('%H:%M') if sch.start_time else ''
        end_str = sch.end_time.strftime('%H:%M') if sch.end_time else ''
        time_display = f"{start_str} - {end_str}" if (start_str and end_str) else (start_str or 'Linh hoạt')

        if c:
            detail_url = url_for('transaction_detail', contract_id=c.id)
        elif j:
            detail_url = url_for('job_detail', job_id=j.id)
        else:
            detail_url = url_for('account_history')

        client_name = c.hirer.name if (c and c.hirer) else (j.hirer.name if (j and j.hirer) else None)
        category_name = j.display_category_text() if j else (s.name if s else 'Phiên dịch')

        upcoming_shifts_list.append({
            'id': sch.id,
            'contract_id': c.id if c else None,
            'job_id': j.id if j else None,
            'title': title,
            'scheduled_date': sch.scheduled_date,
            'date_display': sch.scheduled_date.strftime('%d/%m/%Y'),
            'day_of_week': WEEKDAYS_VN.get(sch.scheduled_date.weekday(), ''),
            'relative_badge': relative_badge,
            'badge_color': badge_color,
            'start_time': sch.start_time or time_cls(0, 0),
            'time_display': time_display,
            'work_mode': work_mode,
            'status': status_meta,
            'detail_url': detail_url,
            'client_name': client_name,
            'category_name': category_name,
            'price': c.agreed_price if c else None
        })

    # Nguồn 2: Bổ sung các hợp đồng đang thực hiện có lịch làm mà chưa tạo TranslatorSchedule
    for c in contracts_active + contracts_pending_payment:
        if c.id in seen_contract_ids:
            continue
        raw_d = _parse_date(c.scheduled_date)
        if not raw_d or raw_d < today:
            continue

        start_t = _parse_time(c.scheduled_time_start)
        end_t = _parse_time(c.scheduled_time_end)

        if raw_d == today and end_t and end_t < now_time:
            continue

        seen_contract_ids.add(c.id)
        j = c.job
        s = c.service
        title = j.title if (j and j.title) else (s.name if (s and s.name) else f"Hợp đồng phiên dịch #{c.id}")

        raw_location = (c.location or (j.event_location if j else '') or '').strip()
        is_onsite = bool(raw_location and not any(k in raw_location.lower() for k in ['online', 'từ xa', 'remote', 'zoom', 'teams', 'google meet']))
        work_mode = {
            'type': 'onsite' if is_onsite else 'online',
            'label': 'Trực tiếp' if is_onsite else 'Trực tuyến',
            'location': raw_location if is_onsite else 'Online / Từ xa'
        }

        if c.status in ('in_progress', 'active', 'escrow_held'):
            status_meta = {
                'code': 'confirmed',
                'label': 'Đang thực hiện (Escrow)',
                'badge_bg': 'bg-emerald-50',
                'badge_text': 'text-emerald-700',
                'badge_border': 'border-emerald-200',
                'dot_color': 'bg-emerald-500'
            }
        else:
            status_meta = {
                'code': 'pending_escrow',
                'label': 'Chờ ký quỹ Escrow',
                'badge_bg': 'bg-amber-50',
                'badge_text': 'text-amber-700',
                'badge_border': 'border-amber-200',
                'dot_color': 'bg-amber-500'
            }

        delta_days = (raw_d - today).days
        if delta_days == 0:
            relative_badge = 'Hôm nay'
            badge_color = 'bg-rose-50 text-rose-700 border-rose-200'
        elif delta_days == 1:
            relative_badge = 'Ngày mai'
            badge_color = 'bg-amber-50 text-amber-700 border-amber-200'
        elif delta_days <= 3:
            relative_badge = f'Trong {delta_days} ngày'
            badge_color = 'bg-blue-50 text-blue-700 border-blue-200'
        else:
            relative_badge = WEEKDAYS_VN.get(raw_d.weekday(), f'+{delta_days} ngày')
            badge_color = 'bg-slate-100 text-slate-700 border-slate-200'

        start_str = start_t.strftime('%H:%M') if start_t else (c.scheduled_time_start or '')
        end_str = end_t.strftime('%H:%M') if end_t else (c.scheduled_time_end or '')
        time_display = f"{start_str} - {end_str}" if (start_str and end_str) else (start_str or 'Linh hoạt')

        upcoming_shifts_list.append({
            'id': c.id,
            'contract_id': c.id,
            'job_id': j.id if j else None,
            'title': title,
            'scheduled_date': raw_d,
            'date_display': raw_d.strftime('%d/%m/%Y'),
            'day_of_week': WEEKDAYS_VN.get(raw_d.weekday(), ''),
            'relative_badge': relative_badge,
            'badge_color': badge_color,
            'start_time': start_t or time_cls(0, 0),
            'time_display': time_display,
            'work_mode': work_mode,
            'status': status_meta,
            'detail_url': url_for('transaction_detail', contract_id=c.id),
            'client_name': c.hirer.name if c.hirer else None,
            'category_name': j.display_category_text() if j else 'Phiên dịch',
            'price': c.agreed_price
        })

    # Sắp xếp tăng dần theo thời gian bắt đầu
    upcoming_shifts_list.sort(key=lambda x: (x['scheduled_date'], x['start_time'] or time_cls(0, 0)))
    total_upcoming_shifts = len(upcoming_shifts_list)
    upcoming_shifts = upcoming_shifts_list[:6]
    upcoming_schedules = upcoming_shifts

    # ── 5. Việc làm đề xuất (dùng matching service hiện có) ──────────────────
    has_profile_languages = bool(
        (profile and profile.languages and profile.languages.strip()) or
        (preference and preference.languages and preference.languages.strip()) or
        (preference and getattr(preference, 'language_pairs', None) and preference.language_pairs.strip())
    )

    recommended_jobs = []
    try:
        from services.matching import get_recommended_jobs_for_translator
        current_lang = session.get('lang') or request.cookies.get('lang') or 'vi'
        recommended_raw = get_recommended_jobs_for_translator(uid, 6, current_lang)
        if recommended_raw:
            job_ids = [r['job_id'] for r in recommended_raw]
            jobs_map = {j.id: j for j in Job.query.filter(Job.id.in_(job_ids)).all()}
            for r in recommended_raw:
                j = jobs_map.get(r['job_id'])
                if j and j.status == 'open' and not j.is_flagged:
                    loc = (j.event_location or '').strip()
                    is_onsite = bool(loc and not any(k in loc.lower() for k in ['online', 'từ xa', 'remote', 'zoom', 'teams', 'google meet']))

                    recommended_jobs.append({
                        'job': j,
                        'match_score': r.get('match_score', 0),
                        'reasons': r.get('reasons', []),
                        'is_matched': True,
                        'work_mode_label': 'Trực tiếp' if is_onsite else 'Trực tuyến',
                        'work_mode_type': 'onsite' if is_onsite else 'online',
                        'location_display': loc if is_onsite else 'Online / Từ xa',
                        'applicant_count': j.applicant_count,
                        'category_text': j.display_category_text(current_lang),
                    })
    except Exception as e:
        print(f"[interpreter_dashboard] recommended jobs error: {e}")
        recommended_jobs = []

    return render_template(
        'interpreter_dashboard.html',
        user=user,
        profile=profile,
        profile_completeness=profile_completeness,
        profile_missing=profile_missing,
        verification_status=verification_status,
        job_stats=job_stats,
        metrics=metrics,
        income_stats=income_stats,
        upcoming_schedules=upcoming_schedules,
        upcoming_shifts=upcoming_shifts,
        total_upcoming_shifts=total_upcoming_shifts,
        recommended_jobs=recommended_jobs,
        has_profile_languages=has_profile_languages,
        today=today,
    )

@app.route('/account/verification')
@login_required
def account_verification():
    """Điều hướng đến khu vực quản lý hồ sơ và chứng chỉ xác minh của phiên dịch viên."""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if user.role != 'translator':
        flash('Chức năng xác minh hồ sơ chỉ dành cho phiên dịch viên.', 'info')
        return redirect(url_for('account_profile'))
    return redirect(url_for('verification_status_page'))

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
    if 'user_id' in session and get_current_user():
        return redirect(url_for('index'))

    next_url = request.args.get('next') or request.form.get('next')

    def is_safe_redirect(url):
        return bool(url and url.startswith('/') and not url.startswith('//'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        try:
            try:
                user = User.query.filter_by(email=email).first()
            except SQLAlchemyError as first_err:
                # Kết nối cũ/hỏng: rollback, bỏ connection và thử lại 1 lần
                print(f"[AUTH SQL RETRY] {first_err}")
                db.session.rollback()
                if 'UndefinedColumn' in type(getattr(first_err, 'orig', first_err)).__name__:
                    _add_missing_columns()
                db.session.remove()
                db.engine.dispose()
                user = User.query.filter_by(email=email).first()
            if user:
                if not user.is_active:
                    flash(_t('flash.account_locked'), 'error')
                    return render_template('login.html', email=email, next_url=next_url)
                if getattr(user, 'role', '') == 'admin' and not getattr(user, 'is_admin', False):
                    flash('Tài khoản của bạn đã bị thu hồi quyền truy cập.', 'error')
                    return render_template('login.html', email=email, next_url=next_url)
                if check_password_hash(user.password_hash, password):
                    session.clear()
                    session.permanent = True
                    session['user_id'] = user.id  # SQL integer ID
                    try:
                        from services.account_security import register_user_session
                        register_user_session(user, request)
                    except Exception as sess_err:
                        print(f"[REGISTER SESSION WARNING] {sess_err}")
                    flash(_t('flash.login_success'), 'success')
                    # Role redirect
                    if user.is_admin:
                        session.clear()
                        flash("Tài khoản Quản trị vui lòng sử dụng cổng đăng nhập riêng.", "warning")
                        return redirect(url_for('admin_login'))
                    # Luôn luôn đưa về trang chủ công khai (giao diện khách) sau khi đăng nhập thành công
                    return redirect(url_for('index'))
                else:
                    flash(_t('flash.invalid_password'), 'error')
                    return render_template('login.html', email=email, next_url=next_url)
            else:
                flash(_t('flash.account_not_found'), 'error')
                return render_template('login.html', email=email, next_url=next_url)
        except SQLAlchemyError as e:
            import traceback
            print(f"[AUTH SQL ERROR] {type(e).__name__}: {e}")
            traceback.print_exc()
            db.session.rollback()
            flash(f"{_t('flash.system_overload')} [{type(e).__name__}]", 'error')
            return render_template('login.html', email=email, next_url=next_url)
        except Exception as e:
            print(f"[AUTH ERROR] {e}")
            flash(_t('flash.db_error'), 'error')
            return render_template('login.html', email=email, next_url=next_url)

    return render_template('login.html', next_url=next_url)


import secrets

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        # Luôn thông báo chung chung để tránh lộ email
        msg = "Nếu email hợp lệ, hướng dẫn khôi phục mật khẩu sẽ được gửi đến bạn."
        
        user = User.query.filter_by(email=email).first()
        if user and user.is_active:
            # Vô hiệu hóa token cũ
            old_tokens = PasswordResetToken.query.filter_by(user_id=user.id, is_used=False).all()
            for t in old_tokens:
                t.is_used = True
            
            # Tạo token mới
            token_str = secrets.token_urlsafe(32)
            token_hash = generate_password_hash(token_str)
            expires_at = datetime.utcnow() + timedelta(minutes=30)
            
            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at
            )
            db.session.add(reset_token)
            
            # Log nếu là admin
            if user.is_admin:
                from admin_auth import get_client_ip
                from models import AdminAuditLog, ADMIN_AUDIT_ACTIONS
                AdminAuditLog.log(
                    action=ADMIN_AUDIT_ACTIONS['SECURITY_ALERT'],
                    admin_id=user.id,
                    description=f'Admin yêu cầu khôi phục mật khẩu. Email: {user.email}',
                    ip_address=get_client_ip(),
                    user_agent=request.headers.get('User-Agent', '')[:512],
                )
                
            db.session.commit()
            
            # Gửi email
            from services.email import send_reset_password_email
            reset_url = url_for('reset_password', token=token_str, email=email, _external=True)
            success, err_msg = send_reset_password_email(user.email, reset_url)
            
            if not success:
                # Rollback nếu gửi fail
                db.session.delete(reset_token)
                db.session.commit()
                flash("Hệ thống email đang gặp sự cố. Vui lòng thử lại sau.", "error")
                return render_template('forgot_password.html')
                
        flash(msg, 'success')
        return redirect(url_for('login'))
        
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = request.args.get('email', '')
    if not email:
        flash("Liên kết không hợp lệ.", "error")
        return redirect(url_for('forgot_password'))
        
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Liên kết không hợp lệ.", "error")
        return redirect(url_for('forgot_password'))
        
    # Tìm token chưa sử dụng, chưa hết hạn
    valid_tokens = PasswordResetToken.query.filter_by(user_id=user.id, is_used=False).all()
    matched_token = None
    
    for t in valid_tokens:
        if t.is_valid() and check_password_hash(t.token_hash, token):
            matched_token = t
            break
            
    if not matched_token:
        flash("Liên kết đã hết hạn hoặc không hợp lệ. Vui lòng yêu cầu lại.", "error")
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if len(new_password) < 6:
            flash("Mật khẩu phải có ít nhất 6 ký tự.", "error")
            return render_template('reset_password.html', token=token, email=email)
            
        if new_password != confirm_password:
            flash("Mật khẩu xác nhận không khớp.", "error")
            return render_template('reset_password.html', token=token, email=email)
            
        # Cập nhật mật khẩu
        user.password_hash = generate_password_hash(new_password)
        
        # Vô hiệu hóa token
        matched_token.is_used = True
        
        # Vô hiệu hóa tất cả token khôi phục khác của user này
        for t in valid_tokens:
            t.is_used = True
            
        # Log nếu là admin
        if user.is_admin:
            from admin_auth import get_client_ip
            from models import AdminAuditLog, ADMIN_AUDIT_ACTIONS
            AdminAuditLog.log(
                action=ADMIN_AUDIT_ACTIONS['SECURITY_ALERT'],
                admin_id=user.id,
                description=f'Admin đã đổi mật khẩu thành công thông qua chức năng khôi phục. Email: {user.email}',
                ip_address=get_client_ip(),
                user_agent=request.headers.get('User-Agent', '')[:512],
            )
            
        db.session.commit()
        
        flash("Mật khẩu đã được đặt lại thành công. Vui lòng đăng nhập lại.", "success")
        return redirect(url_for('login'))
        
    return render_template('reset_password.html', token=token, email=email)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Register dùng SQL only.
    # Đăng ký phải atomic: User + Profile; nếu profile fail → rollback User.
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', '')

        if role not in ('hirer', 'translator'):
            flash(_t('flash.invalid_role'), 'error')
            return redirect(url_for('register'))

        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash(_t('flash.invalid_email'), 'error')
            return redirect(url_for('register'))

        if not password or len(password) < 6:
            flash(_t('flash.password_too_short'), 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash(_t('flash.email_exists'), 'error')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)

        try:
            new_user = User(
                name=name,
                email=email,
                password_hash=hashed_pw,
                phone=phone,
                role=role,
            )
            db.session.add(new_user)
            db.session.flush()  # Lấy new_user.id trước khi tạo profile

            # Tạo profile ngay trong cùng transaction (atomic)
            if role == 'translator':
                profile = TranslatorProfile(user_id=new_user.id)
                db.session.add(profile)
            elif role == 'hirer':
                hirer_profile = HirerProfile(user_id=new_user.id)
                db.session.add(hirer_profile)

            # Generate Email Verification Token
            import secrets
            token_str = secrets.token_urlsafe(32)
            token_hash = generate_password_hash(token_str)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            verif_token = EmailVerificationToken(
                user_id=new_user.id,
                token_hash=token_hash,
                expires_at=expires_at
            )
            db.session.add(verif_token)

            db.session.commit()
            
            # Gửi email xác minh (không để lỗi gửi email làm chặn đăng ký)
            try:
                from services.email import send_verification_email
                verify_url = url_for('verify_email', token=token_str, email=email, _external=True)
                send_verification_email(new_user.email, verify_url)
            except Exception as mail_err:
                print(f"[VERIFY EMAIL SEND ERROR] {mail_err}")
            
            # Tự động đăng nhập cho tài khoản vừa đăng ký để hiện ngay trang chủ có thanh điều hướng
            session.clear()
            session.permanent = True
            session['user_id'] = new_user.id
            try:
                from services.account_security import register_user_session
                register_user_session(new_user, request)
            except Exception as sess_err:
                print(f"[REGISTER SESSION WARNING] {sess_err}")
            
            flash("Đăng ký thành công! Chào mừng bạn đến với VietTranslate.", 'success')
            return redirect(url_for('index'))
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"[REGISTER SQL ERROR] {e}")
            flash(_t('flash.system_overload'), 'error')
            return redirect(url_for('register'))
        except Exception as e:
            db.session.rollback()
            print(f"[REGISTER ERROR] {e}")
            flash(_t('flash.db_error'), 'error')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/verify-email/<token>')
def verify_email(token):
    email = request.args.get('email', '').strip().lower()
    user = User.query.filter_by(email=email).first()
    
    if not user:
        flash("Email không tồn tại.", "error")
        return redirect(url_for('login'))
        
    if user.email_verified:
        flash("Email này đã được xác minh từ trước.", "info")
        return redirect(url_for('login'))
        
    tokens = EmailVerificationToken.query.filter_by(user_id=user.id, is_used=False).all()
    valid_token = None
    for t in tokens:
        if check_password_hash(t.token_hash, token) and t.expires_at > datetime.utcnow():
            valid_token = t
            break
            
    if not valid_token:
        flash("Liên kết xác minh không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu liên kết mới.", "error")
        return redirect(url_for('login'))
        
    # Đánh dấu token đã dùng và email đã xác minh
    valid_token.is_used = True
    user.email_verified = True
    db.session.commit()
    
    flash("Xác minh email thành công! Bạn có thể bắt đầu sử dụng đầy đủ các tính năng.", "success")
    return redirect(url_for('login'))

@app.route('/resend-verification-email', methods=['POST'])
def resend_verification_email():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Bạn cần đăng nhập để thực hiện.'}), 401
        
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Tài khoản không hợp lệ.'}), 400
        
    if user.email_verified:
        return jsonify({'success': False, 'message': 'Email đã được xác minh.'}), 400
        
    # Vô hiệu hóa token cũ
    old_tokens = EmailVerificationToken.query.filter_by(user_id=user.id, is_used=False).all()
    for t in old_tokens:
        t.is_used = True
        
    import secrets
    token_str = secrets.token_urlsafe(32)
    token_hash = generate_password_hash(token_str)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    new_token = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.session.add(new_token)
    db.session.commit()
    
    from services.email import send_verification_email
    verify_url = url_for('verify_email', token=token_str, email=user.email, _external=True)
    success, err_msg = send_verification_email(user.email, verify_url)
    
    if success:
        return jsonify({'success': True, 'message': 'Email xác minh mới đã được gửi.'})
    else:
        return jsonify({'success': False, 'message': 'Gửi email thất bại. Vui lòng thử lại sau.'}), 500

@app.route('/logout')
def logout():
    try:
        from services.account_security import revoke_user_session
        token = session.get('session_token')
        if token and 'user_id' in session:
            revoke_user_session(session['user_id'], token, token)
    except Exception as e:
        print(f"[LOGOUT REVOKE SESSION WARNING] {e}")
    session.clear()
    flash(_t('flash.logout_success'), 'success')
    return redirect(url_for('index'))

# ─── ACCOUNT & PROFILE OVERVIEW ───────────────────────────────────────────────

def compute_profile_completion(user):
    """Tính toán tiến độ hoàn thiện hồ sơ thực tế của phiên dịch viên dựa trên dữ liệu thực tế."""
    if not user or getattr(user, 'role', '') != 'translator':
        return None

    try:
        prof = getattr(user, 'profile', None)
        try:
            verif = getattr(user, 'latest_verification', None)
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
            verif = None

        criteria = [
            {
                'key': 'name',
                'title': 'Họ và tên định danh',
                'completed': bool(user.name and user.name.strip()),
                'action_tab': 'basic',
                'desc': 'Cập nhật họ tên pháp lý chính xác của bạn.'
            },
            {
                'key': 'avatar',
                'title': 'Ảnh đại diện cá nhân',
                'completed': bool(user.avatar or user.avatar_url),
                'action_tab': 'basic',
                'desc': 'Tải lên ảnh chân dung sắc nét để tăng độ tin cậy với khách hàng.'
            },
            {
                'key': 'phone',
                'title': 'Số điện thoại liên hệ',
                'completed': bool(user.phone and user.phone.strip()),
                'action_tab': 'basic',
                'desc': 'Cung cấp số điện thoại để nhận thông báo việc làm khẩn.'
            },
            {
                'key': 'title',
                'title': 'Tiêu đề nghề nghiệp / Chuyên môn',
                'completed': bool(prof and prof.title and prof.title.strip()),
                'action_tab': 'translator',
                'desc': 'Mô tả ngắn gọn vị trí chuyên môn của bạn (VD: Phiên dịch tiếng Hàn TOPIK 6).'
            },
            {
                'key': 'bio',
                'title': 'Giới thiệu bản thân & Kinh nghiệm',
                'completed': bool(prof and prof.bio and len(prof.bio.strip()) >= 20),
                'action_tab': 'translator',
                'desc': 'Viết đoạn giới thiệu ít nhất 20 ký tự về quá trình làm việc và thế mạnh.'
            },
            {
                'key': 'languages',
                'title': 'Ngôn ngữ thành thạo',
                'completed': bool(prof and prof.languages and prof.languages.strip()),
                'action_tab': 'translator',
                'desc': 'Lựa chọn các ngôn ngữ bạn có thể đảm nhận ca phiên dịch.'
            },
            {
                'key': 'services',
                'title': 'Gói dịch vụ & Bảng giá',
                'completed': bool((user and getattr(user, 'interpreter_services', None) and len(user.interpreter_services) > 0) or (prof and getattr(prof, 'services', None) and len(prof.services) > 0)),
                'action_tab': 'services',
                'desc': 'Thiết lập bảng giá dịch vụ để khách hàng có thể đặt trực tiếp.'
            },
            {
                'key': 'verification',
                'title': 'Hồ sơ xác minh & CV',
                'completed': bool(prof and (prof.is_verified or (verif and getattr(verif, 'status', None) in ('pending', 'approved', 'verified')))),
                'action_tab': 'verification',
                'desc': 'Gửi CV và chứng chỉ thẩm định để nhận tích xanh chính thức.'
            }
        ]

        completed_count = sum(1 for c in criteria if c['completed'])
        total_count = len(criteria)
        percentage = int(round((completed_count / total_count) * 100)) if total_count else 0
        missing_items = [c for c in criteria if not c['completed']]

        if prof and prof.is_verified:
            verification_state = 'verified'
        elif verif:
            v_status = getattr(verif, 'status', 'not_started')
            if v_status in ('approved', 'verified'):
                verification_state = 'verified'
            elif v_status in ('pending', 'in_review'):
                verification_state = 'pending'
            elif v_status in ('needs_revision', 'revision_requested'):
                verification_state = 'needs_revision'
            elif v_status == 'draft':
                verification_state = 'draft'
            elif v_status == 'rejected':
                verification_state = 'rejected'
            else:
                verification_state = v_status
        else:
            verification_state = 'not_started'

        return {
            'completed_count': completed_count,
            'total_count': total_count,
            'percentage': percentage,
            'criteria': criteria,
            'missing_items': missing_items,
            'verification_state': verification_state,
            'latest_verification': verif
        }
    except Exception as e:
        print(f"[compute_profile_completion error] {e}", file=sys.stderr)
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


class FallbackNotificationSetting:
    """Đối tượng NotificationSetting dự phòng an toàn khi CSDL bị lỗi hoặc đang đồng bộ."""
    def __init__(self, user_id=None):
        self.id = 0
        self.user_id = user_id
        self.notify_job_match = True
        self.notify_application_update = True
        self.notify_profile_view = True
        self.notify_schedule_reminder = True
        self.reminder_time_60m = True
        self.reminder_time_30m = True
        self.reminder_time_15m = False
        self.reminder_60m = True
        self.reminder_30m = True
        self.reminder_15m = False
        self.notify_income_update = True
        self.notify_security_alert = True
        self.notify_marketing = False

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'notify_job_match': True,
            'notify_application_update': True,
            'notify_profile_view': True,
            'notify_schedule_reminder': True,
            'reminder_time_60m': True,
            'reminder_time_30m': True,
            'reminder_time_15m': False,
            'reminder_60m': True,
            'reminder_30m': True,
            'reminder_15m': False,
            'notify_income_update': True,
            'notify_security_alert': True,
            'notify_marketing': False,
        }


def get_user_notification_setting(user_or_id):
    """Lấy hoặc khởi tạo NotificationSetting mặc định cho người dùng với cơ chế tự phục hồi schema."""
    from models import NotificationSetting
    user_id = user_or_id.id if hasattr(user_or_id, 'id') else int(user_or_id)

    # 1. Thử truy vấn thông thường
    try:
        setting = NotificationSetting.query.filter_by(user_id=user_id).first()
    except Exception as first_err:
        db.session.rollback()
        print(f"[get_user_notification_setting DB Error] {first_err}", file=sys.stderr)
        try:
            # Tự động khắc phục thiếu cột / thiếu bảng trong production DB (Supabase)
            _ensure_account_schema(force=True)
            db.session.remove()
            db.engine.dispose()
            setting = NotificationSetting.query.filter_by(user_id=user_id).first()
        except Exception as retry_err:
            db.session.rollback()
            print(f"[get_user_notification_setting Retry Error] {retry_err}", file=sys.stderr)
            return FallbackNotificationSetting(user_id=user_id)

    if not setting:
        try:
            setting = NotificationSetting(
                user_id=user_id,
                notify_job_match=True,
                notify_application_update=True,
                notify_profile_view=True,
                notify_schedule_reminder=True,
                reminder_time_60m=True,
                reminder_time_30m=True,
                reminder_time_15m=False,
                notify_income_update=True,
                notify_security_alert=True,
                notify_marketing=False
            )
            db.session.add(setting)
            db.session.commit()
        except Exception as add_err:
            db.session.rollback()
            print(f"[get_user_notification_setting Add Error] {add_err}", file=sys.stderr)
            try:
                _ensure_account_schema(force=True)
                db.session.remove()
                setting = NotificationSetting.query.filter_by(user_id=user_id).first()
            except Exception:
                db.session.rollback()
                return FallbackNotificationSetting(user_id=user_id)

    return setting or FallbackNotificationSetting(user_id=user_id)


def save_notification_settings_action(user):
    """Xử lý cập nhật tùy chọn thông báo (Notification Preferences) cho người dùng."""
    from models import NotificationSetting
    is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
               'application/json' in request.headers.get('Accept', '') or
               request.is_json)
    data = request.get_json(silent=True) if request.is_json else (request.form or {})

    try:
        setting = user.notification_setting or NotificationSetting.query.filter_by(user_id=user.id).first()
    except Exception:
        db.session.rollback()
        try:
            _ensure_account_schema(force=True)
            db.session.remove()
            setting = NotificationSetting.query.filter_by(user_id=user.id).first()
        except Exception:
            db.session.rollback()
            setting = None

    if not setting:
        setting = NotificationSetting(user_id=user.id)
        db.session.add(setting)

    # 1. Nếu gửi partial toggle qua AJAX (1 switch riêng lẻ)
    if 'field' in data and 'value' in data:
        field = data.get('field')
        val = data.get('value')
        if isinstance(val, str):
            val = val.lower() in ('1', 'true', 'on', 'yes')
        else:
            val = bool(val)

        if field == 'notify_job_match':
            setting.notify_job_match = val
        elif field == 'notify_application_update':
            setting.notify_application_update = val
        elif field == 'notify_profile_view':
            setting.notify_profile_view = val
        elif field == 'notify_schedule_reminder':
            setting.notify_schedule_reminder = val
        elif field in ('reminder_time_60m', 'reminder_60m'):
            setting.reminder_time_60m = val
        elif field in ('reminder_time_30m', 'reminder_30m'):
            setting.reminder_time_30m = val
        elif field in ('reminder_time_15m', 'reminder_15m'):
            setting.reminder_time_15m = val
        elif field in ('notify_income_update', 'notify_payout'):
            setting.notify_income_update = val
        elif field == 'notify_security_alert':
            # Nhóm Bảo mật: Luôn BẬT và KHÓA không cho phép tắt
            setting.notify_security_alert = True
        elif field == 'notify_marketing':
            setting.notify_marketing = val
    else:
        # 2. Cập nhật toàn bộ biểu mẫu
        if request.is_json:
            if 'notify_job_match' in data:
                setting.notify_job_match = bool(data.get('notify_job_match'))
            if 'notify_application_update' in data:
                setting.notify_application_update = bool(data.get('notify_application_update'))
            if 'notify_profile_view' in data:
                setting.notify_profile_view = bool(data.get('notify_profile_view'))
            if 'notify_schedule_reminder' in data:
                setting.notify_schedule_reminder = bool(data.get('notify_schedule_reminder'))
            if 'reminder_time_60m' in data or 'reminder_60m' in data:
                setting.reminder_time_60m = bool(data.get('reminder_time_60m', data.get('reminder_60m')))
            if 'reminder_time_30m' in data or 'reminder_30m' in data:
                setting.reminder_time_30m = bool(data.get('reminder_time_30m', data.get('reminder_30m')))
            if 'reminder_time_15m' in data or 'reminder_15m' in data:
                setting.reminder_time_15m = bool(data.get('reminder_time_15m', data.get('reminder_15m')))
            if 'notify_income_update' in data or 'notify_payout' in data:
                setting.notify_income_update = bool(data.get('notify_income_update', data.get('notify_payout')))
            setting.notify_security_alert = True  # Luôn BẬT và KHÓA
            if 'notify_marketing' in data:
                setting.notify_marketing = bool(data.get('notify_marketing'))
        else:
            # HTML Form submit
            setting.notify_job_match = ('notify_job_match' in data)
            setting.notify_application_update = ('notify_application_update' in data)
            setting.notify_profile_view = ('notify_profile_view' in data)
            setting.notify_schedule_reminder = ('notify_schedule_reminder' in data)
            setting.reminder_time_60m = ('reminder_time_60m' in data or 'reminder_60m' in data)
            setting.reminder_time_30m = ('reminder_time_30m' in data or 'reminder_30m' in data)
            setting.reminder_time_15m = ('reminder_time_15m' in data or 'reminder_15m' in data)
            setting.notify_income_update = ('notify_income_update' in data or 'notify_payout' in data)
            setting.notify_security_alert = True  # Luôn BẬT và KHÓA
            if 'notify_marketing' in data:
                setting.notify_marketing = ('notify_marketing' in data)

    setting.updated_at = datetime.utcnow()
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({'success': False, 'message': f'Lỗi khi lưu cài đặt: {str(e)}'}), 500
        flash('Đã xảy ra lỗi khi lưu cài đặt thông báo.', 'error')
        return redirect(url_for('account_profile', tab='security'))

    if is_ajax:
        return jsonify({
            'success': True,
            'message': 'Đã lưu cấu hình cài đặt thông báo thành công.',
            'settings': setting.to_dict()
        })
    flash('Cài đặt thông báo đã được lưu thành công.', 'success')
    return redirect(url_for('account_profile', tab='security'))


@app.route('/account', methods=['GET', 'POST'])
@app.route('/account/profile', methods=['GET', 'POST'])
@app.route('/account/overview', methods=['GET', 'POST'])
@login_required
def account_profile():
    # Đồng bộ schema Phân hệ Tài khoản (idempotent, an toàn trên cả Vercel/Supabase)
    _ensure_account_schema()

    # TASK 6: Account dùng SQL only.
    # TASK 9: Legacy session sẽ bị login_required redirect vì get_current_user() trả về None.
    uid = session.get('user_id')

    # TASK 9: Guard — nếu session không phải số nguyên (cũ/lỗi) → clear và redirect login
    if uid and not isinstance(uid, int):
        session.clear()
        flash(_t('flash.login_required'), 'warning')
        return redirect(url_for('login'))

    # SQL user
    user = User.query.get(uid)
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        action = request.form.get('action', 'basic')

        if action == 'basic':
            user.name = request.form.get('name', user.name).strip()
            user.phone = request.form.get('phone', user.phone or '').strip()

            # Tùy chọn: người dùng có thể gửi kèm file avatar trong form basic
            if 'avatar' in request.files and request.files['avatar'].filename:
                ok, res = save_user_avatar(request.files['avatar'], user.id, user.avatar)
                if ok:
                    user.avatar = res
                else:
                    flash(_t(res), 'error')

            db.session.commit()
            flash(_t('flash.profile_updated'), 'success')

        elif action == 'update_personal_profile':
            is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                       'application/json' in request.headers.get('Accept', '') or
                       request.is_json)

            # 1. RÀNG BUỘC ĐỊNH DANH ĐÃ XÁC MINH:
            # Nếu tài khoản đã được xác minh danh tính (is_verified == true), trường "Họ và tên" BẮT BUỘC
            # phải ở trạng thái Read-only (Disabled) và server không cho phép chỉnh sửa.
            is_identity_verified = bool(user.is_verified)
            if not is_identity_verified:
                new_name = request.form.get('name', '').strip()
                if not new_name or len(new_name) < 2:
                    msg = 'Họ và tên không được để trống và phải có ít nhất 2 ký tự.'
                    if is_ajax:
                        return jsonify({'success': False, 'message': msg}), 400
                    flash(msg, 'error')
                    return redirect(url_for('account_profile', tab='profile'))
                user.name = new_name
            # Nếu đã xác minh danh tính: tuyệt đối không cho phép đổi họ và tên từ form

            # 2. KIỂM TRA ĐỊNH DẠNG EMAIL
            email = request.form.get('email', '').strip().lower()
            EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if not email or not re.match(EMAIL_REGEX, email):
                msg = 'Email không hợp lệ. Vui lòng nhập đúng định dạng email (VD: user@example.com).'
                if is_ajax:
                    return jsonify({'success': False, 'message': msg}), 400
                flash(msg, 'error')
                return redirect(url_for('account_profile', tab='profile'))

            if email != user.email.lower():
                existing_email = User.query.filter(User.email.ilike(email), User.id != user.id).first()
                if existing_email:
                    msg = 'Địa chỉ email này đã được sử dụng bởi một tài khoản khác.'
                    if is_ajax:
                        return jsonify({'success': False, 'message': msg}), 400
                    flash(msg, 'error')
                    return redirect(url_for('account_profile', tab='profile'))
                user.email = email
                user.email_verified = False  # Đổi email thì cần xác thực lại

            # 3. KIỂM TRA ĐỊNH DẠNG SỐ ĐIỆN THOẠI
            phone = request.form.get('phone', '').strip()
            clean_phone = re.sub(r'[\s\-.]', '', phone)
            PHONE_REGEX = r'^(?:\+84|0)(?:3[2-9]|5[25689]|7[06-9]|8[1-9]|9[0-9])\d{7}$'
            if clean_phone:
                if not re.match(PHONE_REGEX, clean_phone):
                    msg = 'Số điện thoại không hợp lệ. Vui lòng nhập số điện thoại Việt Nam 10 chữ số (VD: 0912345678).'
                    if is_ajax:
                        return jsonify({'success': False, 'message': msg}), 400
                    flash(msg, 'error')
                    return redirect(url_for('account_profile', tab='profile'))
                user.phone = clean_phone
            else:
                user.phone = ''

            # 4. NGÀY SINH
            dob = request.form.get('date_of_birth', '').strip()
            if dob:
                try:
                    dob_date = datetime.strptime(dob, '%Y-%m-%d')
                    if dob_date > datetime.utcnow():
                        msg = 'Ngày sinh không thể lớn hơn ngày hiện tại.'
                        if is_ajax:
                            return jsonify({'success': False, 'message': msg}), 400
                        flash(msg, 'error')
                        return redirect(url_for('account_profile', tab='profile'))
                    user.date_of_birth = dob
                except ValueError:
                    msg = 'Ngày sinh không đúng định dạng (YYYY-MM-DD).'
                    if is_ajax:
                        return jsonify({'success': False, 'message': msg}), 400
                    flash(msg, 'error')
                    return redirect(url_for('account_profile', tab='profile'))
            else:
                user.date_of_birth = None

            # 5. KHU VỰC HOẠT ĐỘNG CHÍNH (TỈNH/THÀNH PHỐ)
            city = request.form.get('city', '').strip()
            user.city = city[:100] if city else None
            if user.preference:
                user.preference.city = user.city

            # 6. GIỚI THIỆU NGẮN (BIO)
            bio = request.form.get('bio', '').strip()
            user.bio = bio
            if user.profile:
                user.profile.bio = bio

            # 6.5. TIÊU ĐỀ CHUYÊN MÔN & CÔNG KHAI CV (TranslatorProfile)
            if user.role == 'translator':
                if not user.profile:
                    user.profile = TranslatorProfile(user_id=user.id)
                    db.session.add(user.profile)
                if 'title' in request.form:
                    user.profile.title = request.form.get('title', '').strip()[:200]
                if 'is_cv_public' in request.form or 'has_cv_public_field' in request.form:
                    user.profile.is_cv_public = (request.form.get('is_cv_public') in ('1', 'true', 'True', 'on'))

            # 7. SWITCH TOGGLE: CÔNG KHAI HỒ SƠ TRÊN DANH BẠ PHIÊN DỊCH VIÊN
            is_public_val = request.form.get('is_public_profile')
            is_public = (is_public_val in ('1', 'true', 'True', 'on'))
            user.is_public_profile = is_public
            if user.profile:
                user.profile.is_public = is_public

            # 8. XỬ LÝ ẢNH ĐẠI DIỆN
            if request.form.get('remove_avatar') == '1':
                delete_user_avatar(user.avatar)
                user.avatar = None
            elif 'avatar' in request.files and request.files['avatar'].filename:
                avatar_file = request.files['avatar']
                ok, res = save_user_avatar(avatar_file, user.id, user.avatar)
                if not ok:
                    msg = _t(res)
                    if is_ajax:
                        return jsonify({'success': False, 'message': msg}), 400
                    flash(msg, 'error')
                    return redirect(url_for('account_profile', tab='profile'))
                user.avatar = res

            # 9. LƯU THAY ĐỔI VỚI ROLLBACK NẾU THẤT BẠI
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                msg = 'Có lỗi xảy ra trong quá trình lưu dữ liệu. Dữ liệu hợp lệ trước đó vẫn được giữ nguyên.'
                if is_ajax:
                    return jsonify({'success': False, 'message': msg}), 500
                flash(msg, 'error')
                return redirect(url_for('account_profile', tab='profile'))

            msg = 'Cập nhật hồ sơ cá nhân thành công!'
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': msg,
                    'user': {
                        'name': user.name,
                        'email': user.email,
                        'phone': user.phone,
                        'date_of_birth': user.date_of_birth,
                        'city': user.city,
                        'bio': user.bio,
                        'title': user.profile.title if user.profile else '',
                        'is_cv_public': user.profile.is_cv_public if user.profile else False,
                        'is_public_profile': user.is_public_profile,
                        'avatar_url': user.avatar_url,
                        'initial': (user.name or 'U')[0].upper(),
                        'email_verified': user.email_verified,
                        'is_verified': user.is_verified,
                        'is_phone_verified': user.is_phone_verified
                    }
                })
            flash(msg, 'success')
            return redirect(url_for('account_profile', tab='profile'))

        elif action == 'update_profile_title':
            is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                       'application/json' in request.headers.get('Accept', '') or
                       request.is_json)
            new_title = request.form.get('title', '').strip()
            if not user.profile:
                user.profile = TranslatorProfile(user_id=user.id)
                db.session.add(user.profile)
            user.profile.title = new_title[:200]
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                if is_ajax:
                    return jsonify({'success': False, 'message': 'Không thể lưu tiêu đề chuyên môn.'}), 500
                flash('Không thể lưu tiêu đề chuyên môn.', 'error')
                return redirect(url_for('account_profile', tab='profile'))

            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': 'Đã cập nhật tiêu đề chuyên môn thành công!',
                    'title': user.profile.title or 'Chưa đặt tiêu đề chuyên môn'
                })
            flash('Đã cập nhật tiêu đề chuyên môn thành công!', 'success')
            return redirect(url_for('account_profile', tab='profile'))

        elif action == 'upload_avatar':
            file = request.files.get('avatar')
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
            ok, res = save_user_avatar(file, user.id, user.avatar)
            if not ok:
                msg = _t(res)
                if is_ajax:
                    return jsonify({'success': False, 'message': msg}), 400
                flash(msg, 'error')
                return redirect(url_for('account_profile'))

            try:
                user.avatar = res
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                msg = _t('flash.avatar_upload_failed')
                if is_ajax:
                    return jsonify({'success': False, 'message': msg}), 500
                flash(msg, 'error')
                return redirect(url_for('account_profile'))

            msg = _t('flash.avatar_updated')
            if is_ajax:
                return jsonify({'success': True, 'avatar_url': user.avatar_url, 'message': msg})
            flash(msg, 'success')
            return redirect(url_for('account_profile'))

        elif action == 'remove_avatar':
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
            delete_user_avatar(user.avatar)
            try:
                user.avatar = None
                db.session.commit()
            except Exception:
                db.session.rollback()
                msg = _t('flash.system_error')
                if is_ajax:
                    return jsonify({'success': False, 'message': msg}), 500
                flash(msg, 'error')
                return redirect(url_for('account_profile'))

            msg = _t('flash.avatar_removed')
            if is_ajax:
                return jsonify({'success': True, 'avatar_url': user.avatar_url, 'initial': (user.name or 'U')[0].upper(), 'message': msg})
            flash(msg, 'success')
            return redirect(url_for('account_profile'))

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

            # Quyền riêng tư & Công khai
            if 'is_public' in request.form:
                profile.is_public = (request.form.get('is_public') in ('1', 'on', 'true', 'True'))
            if 'is_cv_public' in request.form:
                profile.is_cv_public = (request.form.get('is_cv_public') in ('1', 'on', 'true', 'True'))

            # Cặp ngôn ngữ & Chiều phiên dịch
            if 'source_language' in request.form:
                profile.source_language = request.form.get('source_language', '').strip()
            if 'target_language' in request.form:
                profile.target_language = request.form.get('target_language', '').strip()
            if 'interpreting_direction' in request.form:
                profile.interpreting_direction = request.form.get('interpreting_direction', '').strip()
            if 'language_proficiency' in request.form:
                profile.language_proficiency = request.form.get('language_proficiency', '').strip()

            # Lĩnh vực chuyên môn & Hình thức làm việc
            if 'specializations' in request.form:
                profile.specializations = request.form.get('specializations', '').strip()
            if 'interpreting_types' in request.form:
                profile.interpreting_types = request.form.get('interpreting_types', '').strip()
            if 'work_modes' in request.form:
                profile.work_modes = request.form.get('work_modes', '').strip()

            # Học vấn & Chứng chỉ công khai
            if 'education_level' in request.form:
                profile.education_level = request.form.get('education_level', '').strip()
            if 'university' in request.form:
                profile.university = request.form.get('university', '').strip()
            if 'major' in request.form:
                profile.major = request.form.get('major', '').strip()
            if 'cert_name' in request.form:
                profile.cert_name = request.form.get('cert_name', '').strip()
            if 'cert_year' in request.form:
                cert_year_val = request.form.get('cert_year', '').strip()
                profile.cert_year = int(cert_year_val) if cert_year_val.isdigit() else None

            # Kinh nghiệm nghề nghiệp
            if 'experience_years' in request.form:
                exp_years_val = request.form.get('experience_years', '').strip()
                profile.experience_years = int(exp_years_val) if exp_years_val.isdigit() else 0
            if 'current_position' in request.form:
                profile.current_position = request.form.get('current_position', '').strip()
            if 'notable_clients' in request.form:
                profile.notable_clients = request.form.get('notable_clients', '').strip()
            if 'featured_projects' in request.form:
                profile.featured_projects = request.form.get('featured_projects', '').strip()

            # Đồng bộ từ hồ sơ xác minh nếu người dùng yêu cầu
            if request.form.get('sync_verification') == '1' and profile.latest_verification:
                verif = profile.latest_verification
                if verif.source_language and not profile.source_language:
                    profile.source_language = verif.source_language
                if verif.target_language and not profile.target_language:
                    profile.target_language = verif.target_language
                if verif.interpreting_direction and not profile.interpreting_direction:
                    profile.interpreting_direction = verif.interpreting_direction
                if verif.language_proficiency and not profile.language_proficiency:
                    profile.language_proficiency = verif.language_proficiency
                if verif.specializations and not profile.specializations:
                    profile.specializations = verif.specializations
                if verif.interpreting_types and not profile.interpreting_types:
                    profile.interpreting_types = verif.interpreting_types
                if verif.education_level and not profile.education_level:
                    profile.education_level = verif.education_level
                if verif.university and not profile.university:
                    profile.university = verif.university
                if verif.major and not profile.major:
                    profile.major = verif.major
                if verif.certificate_name and not profile.cert_name:
                    profile.cert_name = verif.certificate_name
                if verif.cert_year and not profile.cert_year:
                    profile.cert_year = verif.cert_year
                if verif.experience_years and not profile.experience_years:
                    profile.experience_years = verif.experience_years
                if verif.current_position and not profile.current_position:
                    profile.current_position = verif.current_position
                if verif.notable_clients and not profile.notable_clients:
                    profile.notable_clients = verif.notable_clients
                if verif.featured_projects and not profile.featured_projects:
                    profile.featured_projects = verif.featured_projects

            # Upload chứng chỉ (nếu có)
            cert_files = request.files.getlist('certificate_files')
            new_certs = []
            for file in cert_files:
                if file and file.filename:
                    ok, res = save_certificate_file(file, user.id)
                    if ok:
                        new_certs.append(res)
                    else:
                        flash(f"Lỗi tải chứng chỉ {file.filename}: {res}", 'warning')
            
            if new_certs:
                existing_certs = profile.certificates.split(',') if profile.certificates else []
                existing_certs.extend(new_certs)
                profile.certificates = ','.join(existing_certs)

            db.session.commit()
            flash(_t('flash.translator_profile_updated'), 'success')

        elif action == 'remove_certificate' and user.role == 'translator':
            filename = request.form.get('filename')
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
            profile = user.profile
            if profile and profile.certificates and filename:
                certs = profile.certificates.split(',')
                if filename in certs:
                    certs.remove(filename)
                    profile.certificates = ','.join(certs)
                    db.session.commit()
                    # Xóa file vật lý
                    filepath = os.path.join(app.root_path, 'static', 'uploads', 'certificates', filename)
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except OSError:
                            pass
                    if is_ajax:
                        return jsonify({'success': True})
                    flash('Đã xóa chứng chỉ', 'success')
            if is_ajax:
                return jsonify({'success': False, 'message': 'Không tìm thấy chứng chỉ'}), 400
            return redirect(url_for('account_profile'))

        elif action == 'translator_preference' and user.role == 'translator':
            pref = user.preference
            if not pref:
                pref = TranslatorPreference(translator_id=user.id)
                db.session.add(pref)
            
            pref.languages = ",".join(request.form.getlist('languages'))
            pref.service_types = ",".join(request.form.getlist('service_types'))
            pref.specialties = ",".join(f for f in HIRING_FIELDS if f in request.form.getlist('specialties'))
            pref.city = request.form.get('city', '').strip()[:100] or None
            pref.work_mode = request.form.get('work_mode') if request.form.get('work_mode') in ('onsite', 'online', 'both') else None
            pref.offers_certified = 'offers_certified' in request.form
            pref.notify_new_jobs = 'notify_new_jobs' in request.form
            pref.notify_messages = 'notify_messages' in request.form
            pref.notify_contracts = 'notify_contracts' in request.form
            pref.notify_reviews = 'notify_reviews' in request.form
            db.session.commit()
            flash(_t('flash.preferences_saved'), 'success')

        elif action in ('save_preferences', 'save_interpreter_preferences', 'interpreter_preference') and user.role == 'translator':
            data = request.get_json(silent=True) or request.form
            is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                       'application/json' in request.headers.get('Accept', '') or
                       request.is_json)
            return save_interpreter_preferences_data(user, data, is_ajax=is_ajax)

        elif action == 'hirer_profile' and user.role == 'hirer':
            profile = user.hirer_profile
            if not profile:
                profile = HirerProfile(user_id=user.id)
                db.session.add(profile)
            errors = _apply_hirer_profile_form(user, profile, request.form, request.files)
            if errors:
                db.session.rollback()
                for msg in errors:
                    flash(msg, 'error')
            else:
                db.session.commit()
                flash(_t('flash.hirer_profile_updated'), 'success')
                if profile.is_verified and profile.verification_status == 'verified':
                    flash('Hồ sơ đã được cập nhật thành công ✓', 'success')
                elif profile.verification_status == 'pending':
                    flash('Hồ sơ đã được lưu và gửi yêu cầu thẩm định tới Ban quản trị. Chức năng đăng tuyển sẽ được kích hoạt sau khi hồ sơ được duyệt.', 'info')
                    try:
                        from models import AdminNotification
                        existing_notif = AdminNotification.query.filter_by(
                            type='HIRER_VERIFICATION',
                            related_id=user.id,
                            is_read=False
                        ).first()
                        if not existing_notif:
                            db.session.add(AdminNotification(
                                type='HIRER_VERIFICATION',
                                title=f'Hồ sơ người đăng tuyển chờ duyệt: #{user.id}',
                                message=f'{user.name} ({user.email}) vừa nộp/cập nhật hồ sơ khách hàng.',
                                related_id=user.id,
                                url=url_for('admin_hirer_verify', hirer_id=user.id)
                            ))
                            db.session.commit()
                    except Exception:
                        pass
                elif profile.verification_status in ('rejected', 'revoked', 'suspended'):
                    flash('Hồ sơ người đăng tuyển của bạn hiện không ở trạng thái hợp lệ để gửi xét duyệt. Vui lòng liên hệ ban quản trị.', 'warning')

        elif action in ('save_notification_settings', 'notification_setting', 'notification_settings'):
            return save_notification_settings_action(user)

        elif action == 'change_password':
            old_pw = request.form.get('old_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            from services.account_security import change_user_password
            success, msg = change_user_password(user, old_pw, new_pw, confirm_pw)
            flash(msg, 'success' if success else 'error')
            return redirect(url_for('account_profile') + '?tab=security')

        elif action in ('revoke_session', 'logout_session'):
            target_id = request.form.get('session_id') or request.form.get('user_session_id')
            current_token = session.get('session_token')
            from services.account_security import revoke_user_session
            success, msg, is_current = revoke_user_session(user.id, target_id, current_token)
            if is_current:
                session.clear()
                flash('Bạn đã đăng xuất khỏi thiết bị này thành công.', 'info')
                return redirect(url_for('login'))
            flash(msg, 'success' if success else 'error')
            return redirect(url_for('account_profile') + '?tab=security')

        elif action in ('revoke_other_sessions', 'logout_other_sessions'):
            current_token = session.get('session_token')
            from services.account_security import revoke_all_other_sessions
            success, msg, count = revoke_all_other_sessions(user.id, current_token)
            flash(msg, 'success' if success else 'error')
            return redirect(url_for('account_profile') + '?tab=security')

        return redirect(url_for('account_profile'))

    current_lang = session.get('lang') or request.cookies.get('lang') or 'vi'
    default_tab = 'profile' if getattr(user, 'role', '') == 'translator' else 'basic'
    if request.path == '/account/overview':
        default_tab = 'profile'
    active_tab = request.args.get('tab', default_tab)
    if getattr(user, 'role', '') == 'translator' and active_tab in ('overview', 'basic'):
        active_tab = 'profile'
    if active_tab == 'hirer_profile':
        active_tab = 'hirer_verify'

    profile_completion = None
    unread_notifs_count = 0
    verification_documents = []
    from services.verification import DOCUMENT_POLICIES
    declared_language_pairs = []
    if getattr(user, 'role', '') == 'translator':
        from models import Notification
        try:
            unread_notifs_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
        except Exception:
            unread_notifs_count = 0
        try:
            profile_completion = compute_profile_completion(user)
            if user.latest_verification and hasattr(user.latest_verification, 'documents'):
                verification_documents = [d for d in user.latest_verification.documents if getattr(d, 'is_active', True)]
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            profile_completion = None

        try:
            seen_pairs = set()
            for svc in (user.interpreter_services or []):
                if svc.source_lang and svc.target_lang:
                    p = f"{svc.source_lang.strip()} ➔ {svc.target_lang.strip()}"
                    if p not in seen_pairs:
                        seen_pairs.add(p)
                        declared_language_pairs.append({
                            'pair': p,
                            'source_lang': svc.source_lang.strip(),
                            'target_lang': svc.target_lang.strip(),
                            'hourly_rate': svc.formatted_hourly_rate if svc.hourly_rate else None,
                            'session_rate': svc.formatted_session_rate if svc.session_rate else None,
                            'is_verified': svc.is_kyc_verified()
                        })
        except Exception as e:
            print(f"[declared_language_pairs error] {e}", file=sys.stderr)

    try:
        notification_setting = get_user_notification_setting(user)
    except Exception as e:
        db.session.rollback()
        print(f"[account_profile notification_setting error] {e}", file=sys.stderr)
        notification_setting = FallbackNotificationSetting(user_id=getattr(user, 'id', 0))

    # Lấy danh sách phiên đăng nhập (Mục 5.6.3)
    current_token = session.get('session_token')
    if not current_token and user and not app.config.get('TESTING'):
        try:
            from services.account_security import register_user_session
            register_user_session(user, request)
            current_token = session.get('session_token')
        except Exception:
            pass

    active_sessions = []
    try:
        from services.account_security import get_active_sessions
        active_sessions = get_active_sessions(user, current_token)
    except Exception as e:
        db.session.rollback()
        print(f"[account_profile active_sessions error] {e}", file=sys.stderr)
        active_sessions = []

    from services.account_support import (
        FAQ_TOPICS,
        FAQ_ITEMS,
        POLICY_DOCUMENTS,
        SUPPORT_CATEGORIES,
        get_user_tickets,
    )
    user_support_tickets = []
    try:
        user_support_tickets = get_user_tickets(user.id)
    except Exception as e:
        db.session.rollback()
        print(f"[account_profile user_support_tickets error] {e}", file=sys.stderr)
        user_support_tickets = []

    return render_template(
        'account_profile.html',
        user=user,
        LANGUAGES=get_localized_languages(current_lang),
        active_tab=active_tab,
        profile_completion=profile_completion,
        unread_notifs_count=unread_notifs_count,
        verification_documents=verification_documents,
        DOCUMENT_POLICIES=DOCUMENT_POLICIES,
        declared_language_pairs=declared_language_pairs,
        notification_setting=notification_setting,
        active_sessions=active_sessions,
        support_tickets=user_support_tickets,
        faq_topics=FAQ_TOPICS,
        faq_items=FAQ_ITEMS,
        policy_documents=POLICY_DOCUMENTS,
        support_categories=SUPPORT_CATEGORIES,
        today_str=datetime.utcnow().strftime('%Y-%m-%d')
    )



# ─── QUẢN LÝ DỊCH VỤ & BIỂU PHÍ PHIÊN DỊCH (MỤC 5.2) ─────────────────────────

def parse_positive_rate(val):
    """
    Chuyển đổi chuỗi giá tiền thành số nguyên dương (> 0).
    Hỗ trợ format tiền tệ VNĐ (ví dụ: '1.500.000', '1,500,000', '1500000 VNĐ').
    Trả về int nếu hợp lệ và > 0, ngược lại trả về None.
    """
    if val is None or val == '':
        return None
    cleaned = str(val).replace('.', '').replace(',', '').replace(' ', '').replace('VNĐ', '').replace('vnd', '').replace('đ', '').strip()
    if not cleaned:
        return None
    try:
        num = int(float(cleaned))
        return num if num > 0 else None
    except (ValueError, TypeError):
        return None


@app.route('/account/services/create', methods=['POST'])
@login_required
def account_service_create():
    """Tạo mới gói dịch vụ & biểu phí phiên dịch (Mục 5.2)."""
    uid = session.get('user_id')
    user = User.query.get(uid)
    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not user or user.role != 'translator':
        if is_ajax:
            return jsonify({'success': False, 'message': 'Chỉ phiên dịch viên mới có quyền quản lý dịch vụ.'}), 403
        flash('Chỉ phiên dịch viên mới có quyền quản lý dịch vụ.', 'error')
        return redirect(url_for('account_profile'))

    data = request.get_json(silent=True) or request.form

    source_lang = (data.get('source_lang') or '').strip()
    target_lang = (data.get('target_lang') or '').strip()
    interpreting_type = (data.get('interpreting_type') or '').strip()
    specialization = (data.get('specialization') or '').strip()
    raw_hourly = data.get('hourly_rate')
    raw_session = data.get('session_rate')
    is_active = data.get('is_active') in (True, 'true', 'True', '1', 'on', 1) if 'is_active' in data else True

    if not source_lang:
        msg = 'Vui lòng chọn ngôn ngữ nguồn.'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    if not target_lang:
        msg = 'Vui lòng chọn ngôn ngữ đích.'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    if source_lang.lower() == target_lang.lower():
        msg = 'Ngôn ngữ nguồn và ngôn ngữ đích không được trùng nhau.'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    if not interpreting_type:
        msg = 'Vui lòng chọn hình thức phiên dịch (Cabin, Nối tiếp, Tháp tùng hoặc Online).'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    hourly_rate = parse_positive_rate(raw_hourly)
    session_rate = parse_positive_rate(raw_session)

    # Ràng buộc: Mức giá phải là số nguyên dương (> 0)
    if raw_hourly and str(raw_hourly).strip() != '' and hourly_rate is None:
        msg = 'Mức thù lao theo giờ phải là số nguyên dương lớn hơn 0 (ví dụ: 1.500.000 VNĐ).'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    if raw_session and str(raw_session).strip() != '' and session_rate is None:
        msg = 'Mức thù lao theo ca/buổi phải là số nguyên dương lớn hơn 0 (ví dụ: 5.000.000 VNĐ).'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    if hourly_rate is None and session_rate is None:
        msg = 'Vui lòng nhập ít nhất một mức thù lao tham khảo (theo giờ hoặc theo ca) là số nguyên dương (> 0).'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    service = InterpreterService(
        user_id=user.id,
        source_lang=source_lang,
        target_lang=target_lang,
        interpreting_type=interpreting_type,
        specialization=specialization or 'Tổng quát / Đa ngành',
        hourly_rate=float(hourly_rate) if hourly_rate else None,
        session_rate=float(session_rate) if session_rate else None,
        currency='VND',
        is_active=is_active
    )
    db.session.add(service)
    db.session.commit()

    verif_status_label = 'Đã xác minh năng lực ✓' if service.is_kyc_verified() else 'Chưa xác minh'
    msg = f'Đã thêm gói dịch vụ "{source_lang} ➔ {target_lang}" thành công! Trạng thái: {verif_status_label}.'

    if is_ajax:
        return jsonify({
            'success': True,
            'message': msg,
            'service': service.to_dict()
        })
    flash(msg, 'success')
    return redirect(url_for('account_profile') + '?tab=services')


@app.route('/account/services/<int:service_id>/update', methods=['POST'])
@login_required
def account_service_update(service_id):
    """Cập nhật thông tin gói dịch vụ & biểu phí phiên dịch (Mục 5.2)."""
    uid = session.get('user_id')
    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    user = User.query.get(uid)
    if not user or user.role != 'translator':
        if is_ajax:
            return jsonify({'success': False, 'message': 'Không có quyền thực hiện.'}), 403
        flash('Không có quyền thực hiện.', 'error')
        return redirect(url_for('account_profile'))

    service = InterpreterService.query.filter_by(id=service_id, user_id=user.id).first()
    if not service:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Không tìm thấy gói dịch vụ.'}), 404
        flash('Không tìm thấy gói dịch vụ.', 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    data = request.get_json(silent=True) or request.form

    source_lang = (data.get('source_lang') or service.source_lang).strip()
    target_lang = (data.get('target_lang') or service.target_lang).strip()
    interpreting_type = (data.get('interpreting_type') or service.interpreting_type).strip()
    specialization = (data.get('specialization') if 'specialization' in data else service.specialization or '').strip()
    raw_hourly = data.get('hourly_rate') if 'hourly_rate' in data else service.hourly_rate
    raw_session = data.get('session_rate') if 'session_rate' in data else service.session_rate

    if not source_lang or not target_lang:
        msg = 'Cặp ngôn ngữ nguồn và đích không được để trống.'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    if source_lang.lower() == target_lang.lower():
        msg = 'Ngôn ngữ nguồn và ngôn ngữ đích không được trùng nhau.'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    hourly_rate = parse_positive_rate(raw_hourly)
    session_rate = parse_positive_rate(raw_session)

    if raw_hourly and str(raw_hourly).strip() != '' and hourly_rate is None:
        msg = 'Mức thù lao theo giờ phải là số nguyên dương lớn hơn 0 (ví dụ: 1.500.000 VNĐ).'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    if raw_session and str(raw_session).strip() != '' and session_rate is None:
        msg = 'Mức thù lao theo ca/buổi phải là số nguyên dương lớn hơn 0 (ví dụ: 5.000.000 VNĐ).'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    if hourly_rate is None and session_rate is None:
        msg = 'Vui lòng nhập ít nhất một mức thù lao tham khảo là số nguyên dương (> 0).'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    service.source_lang = source_lang
    service.target_lang = target_lang
    service.interpreting_type = interpreting_type
    service.specialization = specialization or 'Tổng quát / Đa ngành'
    service.hourly_rate = float(hourly_rate) if hourly_rate else None
    service.session_rate = float(session_rate) if session_rate else None

    if 'is_active' in data:
        service.is_active = data.get('is_active') in (True, 'true', 'True', '1', 'on', 1)

    db.session.commit()

    verif_status_label = 'Đã xác minh năng lực ✓' if service.is_kyc_verified() else 'Chưa xác minh'
    msg = f'Đã cập nhật gói dịch vụ thành công! Trạng thái: {verif_status_label}.'

    if is_ajax:
        return jsonify({
            'success': True,
            'message': msg,
            'service': service.to_dict()
        })
    flash(msg, 'success')
    return redirect(url_for('account_profile') + '?tab=services')


@app.route('/account/services/<int:service_id>/delete', methods=['POST'])
@login_required
def account_service_delete(service_id):
    """
    Xóa gói dịch vụ cung cấp (Mục 5.2).
    TUYỆT ĐỐI KHÔNG XÓA hay can thiệp vào bất kỳ tài liệu minh chứng,
    bằng cấp hay bản ghi nào trong module KYC (TranslatorVerification, VerificationDocument).
    """
    uid = session.get('user_id')
    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    user = User.query.get(uid)
    if not user or user.role != 'translator':
        if is_ajax:
            return jsonify({'success': False, 'message': 'Không có quyền thực hiện.'}), 403
        flash('Không có quyền thực hiện.', 'error')
        return redirect(url_for('account_profile'))

    service = InterpreterService.query.filter_by(id=service_id, user_id=user.id).first()
    if not service:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Gói dịch vụ không tồn tại hoặc đã bị xóa.'}), 404
        flash('Gói dịch vụ không tồn tại hoặc đã bị xóa.', 'warning')
        return redirect(url_for('account_profile') + '?tab=services')

    # Xóa CHỈ bản ghi InterpreterService này, bảo toàn 100% hồ sơ KYC
    service_name = f"{service.source_lang} ➔ {service.target_lang}"
    db.session.delete(service)
    db.session.commit()

    msg = f'Đã xóa gói dịch vụ "{service_name}" khỏi danh mục biểu phí. Dữ liệu tài liệu KYC của bạn được bảo toàn nguyên vẹn.'

    if is_ajax:
        return jsonify({
            'success': True,
            'message': msg,
            'deleted_id': service_id
        })
    flash(msg, 'success')
    return redirect(url_for('account_profile') + '?tab=services')


@app.route('/account/services/<int:service_id>/toggle', methods=['POST'])
@login_required
def account_service_toggle(service_id):
    """Bật/Tắt trạng thái nhận việc của từng dịch vụ riêng biệt."""
    uid = session.get('user_id')
    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    user = User.query.get(uid)
    if not user or user.role != 'translator':
        if is_ajax:
            return jsonify({'success': False, 'message': 'Không có quyền thực hiện.'}), 403
        flash('Không có quyền thực hiện.', 'error')
        return redirect(url_for('account_profile'))

    service = InterpreterService.query.filter_by(id=service_id, user_id=user.id).first()
    if not service:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Không tìm thấy gói dịch vụ.'}), 404
        flash('Không tìm thấy gói dịch vụ.', 'error')
        return redirect(url_for('account_profile') + '?tab=services')

    data = request.get_json(silent=True) or request.form
    if 'is_active' in data:
        service.is_active = data.get('is_active') in (True, 'true', 'True', '1', 'on', 1)
    else:
        service.is_active = not service.is_active

    db.session.commit()

    status_str = 'sẵn sàng nhận việc' if service.is_active else 'tạm dừng nhận việc'
    msg = f'Đã chuyển trạng thái dịch vụ sang "{status_str}".'

    if is_ajax:
        return jsonify({
            'success': True,
            'is_active': service.is_active,
            'message': msg
        })
    flash(msg, 'success')
    return redirect(url_for('account_profile') + '?tab=services')


@app.route('/account/services/sync-kyc', methods=['POST'])
@login_required
def account_service_sync_kyc():
    """Tự động đồng bộ các cặp ngôn ngữ và chuyên ngành đã được duyệt ở KYC vào danh sách dịch vụ."""
    uid = session.get('user_id')
    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    user = User.query.get(uid)
    if not user or user.role != 'translator':
        if is_ajax:
            return jsonify({'success': False, 'message': 'Không có quyền thực hiện.'}), 403
        flash('Không có quyền thực hiện.', 'error')
        return redirect(url_for('account_profile'))

    approved_verif = None
    if hasattr(user, 'verifications') and user.verifications:
        for v in user.verifications:
            if getattr(v, 'status', None) == 'approved':
                approved_verif = v
                break

    source_lang = None
    target_lang = None
    specs = []
    types = []

    if approved_verif:
        source_lang = approved_verif.source_language or 'Tiếng Việt'
        target_lang = approved_verif.target_language or approved_verif.primary_language or 'Tiếng Anh'
        if approved_verif.specializations:
            specs = [s.strip() for s in approved_verif.specializations.replace(';', ',').split(',') if s.strip()]
        if approved_verif.interpreting_types:
            types = [t.strip() for t in approved_verif.interpreting_types.replace(';', ',').split(',') if t.strip()]
    elif user.profile:
        source_lang = user.profile.source_language or 'Tiếng Việt'
        target_lang = user.profile.target_language
        if not target_lang and user.profile.languages:
            parts = [l.strip() for l in user.profile.languages.split(',') if l.strip()]
            target_lang = parts[0] if parts else 'Tiếng Anh'
        if user.profile.specializations:
            specs = [s.strip() for s in user.profile.specializations.replace(';', ',').split(',') if s.strip()]
        if user.profile.interpreting_types:
            types = [t.strip() for t in user.profile.interpreting_types.replace(';', ',').split(',') if t.strip()]

    if not source_lang or not target_lang:
        source_lang = 'Tiếng Việt'
        target_lang = 'Tiếng Anh'

    if not specs:
        specs = ['Kinh doanh & Thương mại']
    if not types:
        types = ['Dịch nối tiếp (Consecutive)', 'Dịch Cabin (Đồng thời)']

    created_count = 0
    for idx, sp in enumerate(specs[:3]):
        itype = types[idx % len(types)]
        exists = InterpreterService.query.filter_by(
            user_id=user.id,
            source_lang=source_lang,
            target_lang=target_lang,
            specialization=sp
        ).first()
        if not exists:
            new_svc = InterpreterService(
                user_id=user.id,
                source_lang=source_lang,
                target_lang=target_lang,
                interpreting_type=itype,
                specialization=sp,
                hourly_rate=1200000.0 if 'cabin' in itype.lower() else 800000.0,
                session_rate=4500000.0 if 'cabin' in itype.lower() else 3000000.0,
                currency='VND',
                is_active=True
            )
            db.session.add(new_svc)
            created_count += 1

    if created_count > 0:
        db.session.commit()
        msg = f'Đã tự động khởi tạo {created_count} gói dịch vụ phiên dịch từ hồ sơ đã thẩm định!'
    else:
        msg = 'Các gói dịch vụ từ hồ sơ thẩm định đã tồn tại trong danh mục của bạn.'

    if is_ajax:
        return jsonify({
            'success': True,
            'message': msg,
            'count': created_count,
            'services': [s.to_dict() for s in user.interpreter_services]
        })
    flash(msg, 'success')
    return redirect(url_for('account_profile') + '?tab=services')


# ─── TIÊU CHÍ NHẬN VIỆC & SMART MATCHING (MỤC 5.4) ───────────────────────────

def save_interpreter_preferences_data(user, data, is_ajax=False):
    """
    Hàm xử lý lưu và cập nhật tiêu chí nhận việc của phiên dịch viên (Mục 5.4).
    RÀNG BUỘC NGHIỆP VỤ BẮT BUỘC:
    Cập nhật tiêu chí chỉ dùng để gợi ý các job mới phù hợp (Smart Matching),
    tuyệt đối không được tự động hủy hoặc thay đổi các lịch ca đã xác nhận trước đó (TranslatorSchedule/Contract).
    """
    if not user or user.role != 'translator':
        msg = 'Chỉ phiên dịch viên mới có quyền thiết lập tiêu chí nhận việc.'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 403
        flash(msg, 'error')
        return redirect(url_for('account_profile'))

    # 1. Cặp ngôn ngữ mong muốn
    if isinstance(data.get('languages'), list):
        languages = [str(l).strip() for l in data.get('languages') if str(l).strip()]
    elif hasattr(data, 'getlist') and data.getlist('languages'):
        languages = [str(l).strip() for l in data.getlist('languages') if str(l).strip()]
    elif data.get('languages'):
        raw_langs = data.get('languages')
        if isinstance(raw_langs, list):
            languages = [str(l).strip() for l in raw_langs if str(l).strip()]
        else:
            try:
                parsed = json.loads(raw_langs)
                languages = [str(l).strip() for l in parsed if str(l).strip()] if isinstance(parsed, list) else [l.strip() for l in str(raw_langs).split(',') if l.strip()]
            except Exception:
                languages = [l.strip() for l in str(raw_langs).split(',') if l.strip()]
    else:
        languages = []

    # 2. Lĩnh vực sẵn sàng nhận việc
    if isinstance(data.get('specializations'), list):
        specializations = [str(s).strip() for s in data.get('specializations') if str(s).strip()]
    elif hasattr(data, 'getlist') and data.getlist('specializations'):
        specializations = [str(s).strip() for s in data.getlist('specializations') if str(s).strip()]
    elif data.get('specializations'):
        raw_specs = data.get('specializations')
        if isinstance(raw_specs, list):
            specializations = [str(s).strip() for s in raw_specs if str(s).strip()]
        else:
            try:
                parsed = json.loads(raw_specs)
                specializations = [str(s).strip() for s in parsed if str(s).strip()] if isinstance(parsed, list) else [s.strip() for s in str(raw_specs).split(',') if s.strip()]
            except Exception:
                specializations = [s.strip() for s in str(raw_specs).split(',') if s.strip()]
    else:
        specializations = []

    # 3. Hình thức làm việc & Khu vực
    mode_offline = data.get('mode_offline') in (True, 'true', 'True', '1', 'on', 1)
    mode_online = data.get('mode_online') in (True, 'true', 'True', '1', 'on', 1)
    raw_work_mode = (data.get('work_mode') or '').strip().lower()

    if mode_offline and mode_online:
        work_mode = 'both'
    elif mode_offline:
        work_mode = 'offline'
    elif mode_online:
        work_mode = 'online'
    elif raw_work_mode in ('both', 'offline', 'online'):
        work_mode = raw_work_mode
    else:
        work_mode = 'both'

    # Khu vực nhận việc trực tiếp (locations)
    if isinstance(data.get('locations'), list):
        locations = [str(loc).strip() for loc in data.get('locations') if str(loc).strip()]
    elif hasattr(data, 'getlist') and data.getlist('locations'):
        locations = [str(l).strip() for l in data.getlist('locations') if str(l).strip()]
    elif data.get('locations'):
        raw_locs = data.get('locations')
        if isinstance(raw_locs, list):
            locations = [str(l).strip() for l in raw_locs if str(l).strip()]
        else:
            try:
                parsed = json.loads(raw_locs)
                locations = [str(l).strip() for l in parsed if str(l).strip()] if isinstance(parsed, list) else [l.strip() for l in str(raw_locs).split(',') if l.strip()]
            except Exception:
                locations = [l.strip() for l in str(raw_locs).split(',') if l.strip()]
    else:
        locations = []

    # 4. Khoảng giá mong muốn (Min - Max VNĐ)
    raw_min = data.get('min_rate')
    raw_max = data.get('max_rate')
    min_rate = parse_positive_rate(raw_min)
    max_rate = parse_positive_rate(raw_max)

    if min_rate and max_rate and min_rate > max_rate:
        min_rate, max_rate = max_rate, min_rate

    allow_outside_rate = data.get('allow_outside_rate') in (True, 'true', 'True', '1', 'on', 1)

    # 5. Khung giờ sẵn sàng nhận ca trong tuần (Ca sáng, chiều, tối, cuối tuần)
    if isinstance(data.get('available_hours'), list):
        available_hours = [str(h).strip() for h in data.get('available_hours') if str(h).strip()]
    elif hasattr(data, 'getlist') and data.getlist('available_hours'):
        available_hours = [str(h).strip() for h in data.getlist('available_hours') if str(h).strip()]
    elif data.get('available_hours'):
        raw_hours = data.get('available_hours')
        if isinstance(raw_hours, list):
            available_hours = [str(h).strip() for h in raw_hours if str(h).strip()]
        else:
            try:
                parsed = json.loads(raw_hours)
                available_hours = [str(h).strip() for h in parsed if str(h).strip()] if isinstance(parsed, list) else [h.strip() for h in str(raw_hours).split(',') if h.strip()]
            except Exception:
                available_hours = [h.strip() for h in str(raw_hours).split(',') if h.strip()]
    else:
        available_hours = []

    # Lưu dữ liệu vào InterpreterPreference
    pref = user.interpreter_preference
    if not pref:
        pref = InterpreterPreference(user_id=user.id)
        db.session.add(pref)

    pref.set_languages_list(languages)
    pref.set_specializations_list(specializations)
    pref.work_mode = work_mode
    pref.set_locations_list(locations)
    pref.min_rate = float(min_rate) if min_rate else None
    pref.max_rate = float(max_rate) if max_rate else None
    pref.allow_outside_rate = allow_outside_rate
    pref.set_available_hours_list(available_hours)
    pref.updated_at = datetime.utcnow()

    # Ràng buộc nghiệp vụ: Cập nhật tiêu chí nhận việc không làm ảnh hưởng hay hủy bất kỳ lịch ca đã xác nhận nào
    # Toàn bộ TranslatorSchedule và Contract được giữ nguyên trọn vẹn 100%.

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        msg = 'Có lỗi xảy ra khi lưu tiêu chí nhận việc. Dữ liệu trước đó được bảo toàn.'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 500
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=preferences')

    # Kiểm tra các cặp ngôn ngữ thiếu biểu phí ở Tab Năng lực
    declared_svc_pairs = set()
    for s in (user.interpreter_services or []):
        if s.source_lang and s.target_lang:
            declared_svc_pairs.add(f"{s.source_lang.strip().lower()}➔{s.target_lang.strip().lower()}")
            declared_svc_pairs.add(f"{s.source_lang.strip().lower()}->{s.target_lang.strip().lower()}")
            declared_svc_pairs.add(f"{s.source_lang.strip().lower()}-{s.target_lang.strip().lower()}")

    missing_fee_pairs = []
    for p in languages:
        clean = p.replace(' ', '').lower()
        if clean not in declared_svc_pairs:
            missing_fee_pairs.append(p)

    msg = 'Đã lưu tiêu chí nhận việc thành công! Hệ thống Smart Matching sẽ áp dụng ngay cho các cơ hội việc làm mới.'
    warning_msg = None
    if missing_fee_pairs:
        warning_msg = f'Bạn chưa khai báo biểu phí cho ngôn ngữ này tại mục Năng lực ({", ".join(missing_fee_pairs[:2])}).'

    if is_ajax:
        return jsonify({
            'success': True,
            'message': msg,
            'warning': warning_msg,
            'missing_fee_pairs': missing_fee_pairs,
            'preference': pref.to_dict()
        })
    flash(msg, 'success')
    if warning_msg:
        flash(warning_msg, 'warning')
    return redirect(url_for('account_profile') + '?tab=preferences')


@app.route('/account/preferences/save', methods=['POST'])
@login_required
def account_preferences_save():
    """Endpoint nhận dữ liệu form hoặc Ajax để cập nhật InterpreterPreference."""
    uid = session.get('user_id')
    user = User.query.get(uid)
    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
    data = request.get_json(silent=True) or request.form
    return save_interpreter_preferences_data(user, data, is_ajax=is_ajax)


@app.route('/account/preferences/get', methods=['GET'])
@login_required
def account_preferences_get():
    """Endpoint API lấy cấu hình tiêu chí hiện tại của phiên dịch viên."""
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập.'}), 403
    pref = user.interpreter_preference
    return jsonify({
        'success': True,
        'preference': pref.to_dict() if pref else None
    })


# ─── GÓI DỊCH VỤ & QUYỀN LỢI (MỤC 5.5) ─────────────────────────────────────────

@app.route('/account/subscription/interest', methods=['POST'])
@login_required
def account_subscription_interest():
    """Ghi nhận đăng ký quan tâm gói Pro (Mục 5.5 - Xử lý an toàn khi chưa có cổng VNPAY/Momo)."""
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        return jsonify({'success': False, 'message': 'Người dùng không hợp lệ.'}), 401

    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
    data = request.get_json(silent=True) or request.form
    note = data.get('note', '').strip() if data else ''
    phone = data.get('phone', '').strip() if data else (user.phone or '')

    # TUYỆT ĐỐI KHÔNG thay đổi trạng thái thanh toán hoặc tạo giao dịch giả mạo.
    # Chỉ tạo thông báo hệ thống ghi nhận nguyện vọng danh sách chờ Early Bird.
    try:
        from models import Notification
        notif = Notification(
            user_id=user.id,
            title='Đăng ký quan tâm Gói Pro thành công',
            message='VietTranslate đã ghi nhận bạn vào danh sách ưu tiên trải nghiệm Gói Phiên Dịch Viên Chuyên Nghiệp (Pro). Chúng tôi sẽ gửi thông báo ưu đãi sớm nhất khi cổng thanh toán chính thức ra mắt!',
            type='SUBSCRIPTION_INTEREST'
        )
        db.session.add(notif)
        db.session.commit()
    except Exception as e:
        db.session.rollback()

    msg = 'Đã ghi nhận đăng ký quan tâm! VietTranslate sẽ gửi thông báo ưu đãi tới bạn ngay khi cổng thanh toán chính thức ra mắt.'
    if is_ajax:
        return jsonify({
            'success': True,
            'message': msg
        })
    flash(msg, 'success')
    return redirect(url_for('account_profile') + '?tab=subscription')


@app.route('/account/verification/submit', methods=['POST'])
@email_verified_required
def submit_verification():
    """Nhận và xử lý gửi hồ sơ xác minh phiên dịch viên tới Ban quản trị."""
    uid = session.get('user_id')
    user = User.query.get(uid)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '') or request.is_json

    if not user:
        if is_ajax:
            return jsonify({'success': False, 'message': _t('flash.account_not_found')}), 404
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('login'))

    if user.role != 'translator':
        msg = 'Chỉ tài khoản phiên dịch viên mới có quyền gửi hồ sơ xác minh.'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 403
        flash(msg, 'error')
        return redirect(url_for('account_profile'))

    from services.verification import submit_verification_for_review, submit_verification_request

    # Nếu người dùng gửi kèm file trực tiếp qua multipart form
    if request.files and any(f.filename for f in request.files.values()):
        ok, msg = submit_verification_request(user, request.form, request.files)
        if ok:
            flash(msg, 'success')
        else:
            flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=verification')

    # Dữ liệu JSON hoặc form POST
    if request.is_json:
        payload = request.json or {}
        form_data = payload.get('form_data') or payload
        confirmed = payload.get('confirmed') in (True, 'true', '1', 1, 'on')
    else:
        form_data = request.form.to_dict()
        confirmed = request.form.get('confirmed') in (True, 'true', '1', 1, 'on')

    ok, msg, meta = submit_verification_for_review(
        user,
        form_data=form_data,
        confirmed=confirmed,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string if request.user_agent else None
    )

    if not ok:
        if is_ajax:
            status_code = 409 if meta.get('is_duplicate') else 400
            return jsonify({
                'success': False,
                'message': msg,
                'errors': meta.get('errors', {}),
                'error_list': meta.get('error_list', [msg]),
                'is_duplicate': meta.get('is_duplicate', False)
            }), status_code

        for err in meta.get('error_list', [msg]):
            flash(err, 'error')
        return redirect(url_for('account_profile') + '?tab=verification')

    if is_ajax:
        return jsonify({
            'success': True,
            'message': msg,
            'version': meta.get('version'),
            'submitted_at': meta.get('submitted_at'),
            'redirect_url': url_for('account_profile') + '?tab=verification'
        }), 200

    flash(msg, 'success')
    return redirect(url_for('account_profile') + '?tab=verification')



# ─── TRANSLATOR VERIFICATION DOCUMENTS (PRIVATE STORAGE & RBAC) ───────────────

@app.route('/account/verification/documents/upload', methods=['POST'])
@email_verified_required
def upload_verification_document():
    """
    Endpoint tải lên tài liệu minh chứng cho hồ sơ xác minh phiên dịch viên.
    Hỗ trợ cả tải lên qua AJAX (tiến trình thời gian thực) và form submit thông thường.
    Kiểm tra quyền, kiểm tra chính sách loại tài liệu, chữ ký nhị phân (magic bytes)
    và dung lượng thực tế ở cấp máy chủ.
    Tài liệu được lưu trữ tại vùng riêng tư an toàn (Private Storage).
    LƯU Ý: Tải lên thành công KHÔNG đồng nghĩa tài liệu đã được xác minh.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Không tìm thấy thông tin tài khoản.'}), 401
        flash('Không tìm thấy thông tin tài khoản.', 'error')
        return redirect(url_for('login'))

    if user.role != 'translator':
        msg = 'Chỉ tài khoản phiên dịch viên mới có quyền tải lên tài liệu minh chứng.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': msg}), 403
        flash(msg, 'error')
        return redirect(url_for('account_profile'))

    from services.verification import save_private_document

    file = request.files.get('file') or request.files.get('document_file')
    doc_type = request.form.get('document_type') or request.form.get('doc_type')

    ok, doc, err = save_private_document(file, user, doc_type=doc_type)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')

    if not ok:
        if is_ajax:
            return jsonify({'success': False, 'message': err}), 400
        flash(err, 'error')
        return redirect(url_for('account_profile') + '?tab=verification')

    success_msg = f'Đã tải lên và lưu trữ an toàn tài liệu minh chứng "{doc.original_filename}".'
    notice_msg = 'Lưu ý: Tài liệu đang ở trạng thái Chờ thẩm định, chưa phải là Đã xác minh.'

    if is_ajax:
        return jsonify({
            'success': True,
            'message': success_msg,
            'notice': notice_msg,
            'document': doc.to_dict()
        }), 200

    flash(f"{success_msg} ({notice_msg})", 'success')
    return redirect(url_for('account_profile') + '?tab=verification')


@app.route('/account/verification/documents/<int:doc_id>/download')
@login_required
def download_verification_document(doc_id):
    """
    Endpoint tải xuống tài liệu minh chứng.
    Kiểm tra nghiêm ngặt quyền truy cập ở backend (RBAC):
    - Chỉ Chủ sở hữu hoặc Quản trị viên (Admin) mới có quyền tải xuống.
    - Người khác nhận mã lỗi 403 Forbidden.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        abort(401)

    doc = VerificationDocument.query.get_or_404(doc_id)

    from services.verification import can_user_access_document, resolve_document_file_path
    can_access, err = can_user_access_document(user, doc)
    if not can_access:
        abort(403)

    ftype, target = resolve_document_file_path(doc)
    if ftype == 'url':
        return redirect(target)
    elif ftype == 'file' and target:
        file_path = target
    else:
        abort(404)

    response = send_file(
        file_path,
        as_attachment=True,
        download_name=doc.original_filename,
        mimetype=doc.mime_type or 'application/octet-stream'
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'none'"
    response.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    return response


@app.route('/account/verification/documents/<int:doc_id>/view')
@login_required
def view_verification_document(doc_id):
    """
    Endpoint xem trước tài liệu minh chứng (PDF hoặc ảnh).
    Kiểm tra nghiêm ngặt quyền truy cập ở backend (RBAC).
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        abort(401)

    doc = VerificationDocument.query.get_or_404(doc_id)

    from services.verification import can_user_access_document, resolve_document_file_path
    can_access, err = can_user_access_document(user, doc)
    if not can_access:
        abort(403)

    ftype, target = resolve_document_file_path(doc)
    if ftype == 'url':
        return redirect(target)
    elif ftype == 'file' and target:
        file_path = target
    else:
        abort(404)

    response = send_file(
        file_path,
        as_attachment=False,
        download_name=doc.original_filename,
        mimetype=doc.mime_type or 'application/octet-stream'
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    return response


@app.route('/account/verification/documents/<int:doc_id>/delete', methods=['POST'])
@email_verified_required
def delete_verification_document_endpoint(doc_id):
    """
    Endpoint xóa/hủy tài liệu minh chứng nháp.
    Chỉ cho phép khi hồ sơ ở trạng thái được phép chỉnh sửa.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        abort(401)

    from services.verification import delete_private_document
    ok, msg = delete_private_document(doc_id, user)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    if not ok:
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile') + '?tab=verification')

    if is_ajax:
        return jsonify({'success': True, 'message': msg}), 200

    flash(msg, 'success')
    return redirect(url_for('account_profile') + '?tab=verification')


@app.route('/api/account/verification/documents', methods=['GET'])
@login_required
def get_verification_documents_api():
    """
    API trả về danh sách các tài liệu minh chứng của phiên dịch viên hiện tại,
    kèm chính sách tải tệp và trạng thái hồ sơ.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập.'}), 403

    from services.verification import DOCUMENT_POLICIES
    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()

    docs = []
    if verification:
        docs = [d.to_dict() for d in verification.documents if d.is_active]

    policies_data = {}
    for k, p in DOCUMENT_POLICIES.items():
        policies_data[k] = {
            'code': p['code'],
            'name': p['name'],
            'description': p['description'],
            'required': p['required'],
            'allowed_extensions': list(sorted(p['allowed_extensions'])),
            'max_size_mb': p['max_size_mb']
        }

    status = verification.status if verification else 'not_started'
    can_modify = status in ('draft', 'rejected', 'needs_revision', 'not_started', None)

    return jsonify({
        'success': True,
        'verification_status': status,
        'can_modify': can_modify,
        'documents': docs,
        'policies': policies_data
    })


@app.route('/account/verification/form', methods=['GET', 'POST'])
@app.route('/verification/apply', methods=['GET', 'POST'])
@email_verified_required
def verification_form():
    """
    Biểu mẫu nhiều bước khai báo thông tin xác minh phiên dịch viên (VietTranslate).
    Bao gồm 6 bước:
    1. Thông tin cá nhân
    2. Ngôn ngữ nguồn, ngôn ngữ đích và chiều phiên dịch
    3. Lĩnh vực chuyên môn & Hình thức dịch
    4. Học vấn và chứng chỉ
    5. Kinh nghiệm nghề nghiệp
    6. Xem lại thông tin (Review & Confirm Draft)
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('login'))

    if user.role != 'translator':
        flash('Biểu mẫu xác minh chỉ dành riêng cho tài khoản phiên dịch viên.', 'warning')
        return redirect(url_for('account_profile'))

    from services.verification import (
        get_or_create_verification_draft,
        validate_step_data,
        save_verification_draft
    )

    verification = get_or_create_verification_draft(user)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '') or request.is_json

    if request.method == 'POST':
        action = request.form.get('action') or (request.json.get('action') if request.is_json else 'save_draft')
        step = request.form.get('step', type=int) or (request.json.get('step') if request.is_json else verification.current_step or 1)
        
        # Lấy dữ liệu biểu mẫu
        if request.is_json:
            form_data = request.json or {}
        else:
            raw = request.form.to_dict(flat=False)
            form_data = {}
            for k, v in raw.items():
                if k in ('specializations', 'interpreting_types'):
                    form_data[k] = v
                elif len(v) == 1:
                    form_data[k] = v[0]
                else:
                    form_data[k] = v

        if action == 'save_draft':
            # Lưu nháp bất kỳ bước nào mà không bắt buộc hoàn thiện
            target_step = request.form.get('target_step', type=int) or (request.json.get('target_step') if request.is_json else step)
            ok, verif, err = save_verification_draft(user, form_data, target_step=target_step)
            if not ok:
                if is_ajax:
                    return jsonify({'success': False, 'message': err}), 500
                flash(err, 'error')
                return redirect(url_for('verification_form', step=step))
            
            last_saved = verif.updated_at.strftime('%H:%M:%S') if verif.updated_at else datetime.utcnow().strftime('%H:%M:%S')
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': f'Đã lưu nháp an toàn vào hệ thống lúc {last_saved}',
                    'last_saved': last_saved,
                    'current_step': verif.current_step,
                    'draft_data': verif.get_draft_dict()
                })
            flash(f'Đã lưu bản nháp thành công lúc {last_saved}', 'success')
            return redirect(url_for('verification_form', step=step))

        elif action == 'next_step':
            # Kiểm tra dữ liệu bước hiện tại
            is_valid, errors = validate_step_data(step, form_data)
            if not is_valid:
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'errors': errors,
                        'message': 'Vui lòng kiểm tra và sửa các trường thông tin chưa hợp lệ trước khi tiếp tục.'
                    }), 400
                for f_name, f_err in errors.items():
                    flash(f_err, 'error')
                return redirect(url_for('verification_form', step=step))

            # Hợp lệ -> Lưu nháp dữ liệu và tăng sang bước tiếp theo
            next_step = min(6, step + 1)
            ok, verif, err = save_verification_draft(user, form_data, target_step=next_step)
            if not ok:
                if is_ajax:
                    return jsonify({'success': False, 'message': err}), 500
                flash(err, 'error')
                return redirect(url_for('verification_form', step=step))

            last_saved = verif.updated_at.strftime('%H:%M:%S') if verif.updated_at else datetime.utcnow().strftime('%H:%M:%S')
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': 'Dữ liệu hợp lệ. Đã chuyển sang bước tiếp theo.',
                    'next_step': next_step,
                    'last_saved': last_saved,
                    'draft_data': verif.get_draft_dict()
                })
            return redirect(url_for('verification_form', step=next_step))

        elif action == 'goto_step':
            # Nhảy tới bước chỉ định (từ nút Sửa ở Bước 6 hoặc quay lại)
            target = request.form.get('target_step', type=int) or (request.json.get('target_step') if request.is_json else 1)
            if 1 <= target <= 6:
                save_verification_draft(user, form_data, target_step=target)
                if is_ajax:
                    return jsonify({'success': True, 'target_step': target})
                return redirect(url_for('verification_form', step=target))

        elif action == 'confirm_draft':
            # Xác nhận hoàn tất khai báo nháp, chuẩn bị cho giai đoạn nộp tài liệu sau này
            ok, verif, err = save_verification_draft(user, form_data, target_step=6)
            if not ok:
                if is_ajax:
                    return jsonify({'success': False, 'message': err}), 400
                flash(err, 'error')
                return redirect(url_for('verification_form', step=step))
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': 'Bản nháp hồ sơ xác minh đã được lưu trữ an toàn! Bạn có thể xem lại hoặc chỉnh sửa bất kỳ lúc nào.',
                    'redirect_url': url_for('account_profile') + '?tab=verification'
                })
            flash('Bản nháp hồ sơ xác minh đã được lưu trữ an toàn trong tài khoản của bạn.', 'success')
            return redirect(url_for('account_profile') + '?tab=verification')

        elif action == 'submit_verification':
            from services.verification import submit_verification_for_review
            confirmed = (form_data.get('confirmed') if isinstance(form_data, dict) else request.form.get('confirmed')) in (True, 'true', '1', 1, 'on')
            ok, msg, meta = submit_verification_for_review(
                user,
                form_data=form_data,
                confirmed=confirmed,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string if request.user_agent else None
            )
            if not ok:
                if is_ajax:
                    status_code = 409 if meta.get('is_duplicate') else 400
                    return jsonify({
                        'success': False,
                        'message': msg,
                        'errors': meta.get('errors', {}),
                        'error_list': meta.get('error_list', [msg]),
                        'is_duplicate': meta.get('is_duplicate', False)
                    }), status_code
                for err_text in meta.get('error_list', [msg]):
                    flash(err_text, 'error')
                return redirect(url_for('verification_form', step=6))

            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': msg,
                    'version': meta.get('version'),
                    'submitted_at': meta.get('submitted_at'),
                    'redirect_url': url_for('account_profile') + '?tab=verification'
                }), 200
            flash(msg, 'success')
            return redirect(url_for('account_profile') + '?tab=verification')

    # GET Request
    # Ưu tiên tham số URL ?step=X, nếu không thì lấy từ verification.current_step
    requested_step = request.args.get('step', type=int)
    active_step = requested_step if requested_step and 1 <= requested_step <= 6 else (verification.current_step or 1)
    
    current_lang = session.get('lang') or request.cookies.get('lang') or 'vi'
    draft_dict = verification.get_draft_dict()
    from services.verification import DOCUMENT_POLICIES
    verification_documents = [d for d in verification.documents if d.is_active] if verification else []

    return render_template(
        'verification_form.html',
        user=user,
        verification=verification,
        draft=draft_dict,
        active_step=active_step,
        LANGUAGES=get_localized_languages(current_lang),
        current_year=datetime.utcnow().year,
        verification_documents=verification_documents,
        DOCUMENT_POLICIES=DOCUMENT_POLICIES,
        is_pending=(getattr(verification, 'status', 'draft') == 'pending'),
        is_approved=(getattr(verification, 'status', 'draft') == 'approved')
    )


@app.route('/api/account/verification/check-eligibility', methods=['GET'])
@login_required
def check_verification_eligibility_api():
    """Kiểm tra điều kiện sẵn sàng gửi hồ sơ xác minh trước khi nộp."""
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập.'}), 403

    from services.verification import validate_verification_eligibility, TranslatorVerification
    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
    if not verification:
        return jsonify({
            'success': True,
            'is_eligible': False,
            'status': 'not_started',
            'errors': {'verification': 'Chưa khởi tạo hồ sơ.'},
            'error_list': ['Chưa khởi tạo hồ sơ nháp.'],
            'version': 0
        })

    is_eligible, errors_dict, error_messages = validate_verification_eligibility(
        verification,
        require_confirmation=False
    )
    return jsonify({
        'success': True,
        'is_eligible': is_eligible,
        'status': verification.status,
        'errors': errors_dict,
        'error_list': error_messages,
        'version': verification.submission_version or 0,
        'submitted_at': verification.submitted_at.strftime('%d/%m/%Y %H:%M') if verification.submitted_at else None
    })


# ─── TRANSLATOR VERIFICATION STATUS TRACKER ROUTES ────────────────────────────

@app.route('/account/verification/status', methods=['GET'])
@app.route('/verification/status', methods=['GET'])
@login_required
def verification_status_page():
    """
    Trang theo dõi trạng thái xác minh riêng biệt dành cho phiên dịch viên (VietTranslate).
    Lấy dữ liệu thực từ hồ sơ của tài khoản đang đăng nhập.
    Hiển thị đầy đủ:
    - Trạng thái tổng thể, ngày tạo và ngày gửi hồ sơ.
    - Tiến độ 6 bước hoàn thành, đang xử lý hoặc cần bổ sung.
    - Trạng thái từng hạng mục khi có dữ liệu.
    - Yêu cầu bổ sung và hướng dẫn của Admin.
    - Lý do từ chối nếu có.
    - Lịch sử các lần gửi và kết quả.
    - Hành động tiếp theo phù hợp với trạng thái hiện tại.
    Quy tắc an toàn:
    - Người dùng chỉ được xem hồ sơ của chính mình.
    - Không suy đoán dữ liệu thiếu.
    - Không lộ kết quả nội bộ không được phép.
    """
    uid = session.get('user_id')
    if uid and not isinstance(uid, int):
        session.clear()
        flash(_t('flash.login_required'), 'warning')
        return redirect(url_for('login'))

    user = User.query.get(uid)
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('login'))

    if user.role != 'translator':
        flash('Trang theo dõi trạng thái xác minh chỉ dành riêng cho tài khoản phiên dịch viên.', 'warning')
        return redirect(url_for('account_profile'))

    from services.verification import get_translator_verification_status_details
    data = get_translator_verification_status_details(user)

    return render_template('verification_status.html', user=user, data=data)


@app.route('/api/account/verification/status', methods=['GET'])
@login_required
def verification_status_api():
    """
    API JSON trả về toàn bộ dữ liệu trạng thái xác minh của phiên dịch viên hiện tại.
    Hỗ trợ tải động realtime qua AJAX.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập.'}), 403

    from services.verification import get_translator_verification_status_details
    data = get_translator_verification_status_details(user)

    return jsonify({'success': True, 'data': data})


# ─── TRANSLATOR VERIFICATION REVISION ROUTES ──────────────────────────────────

@app.route('/account/verification/revision', methods=['GET'])
@app.route('/verification/revision', methods=['GET'])
@login_required
def verification_revision_page():
    """
    Trang chuyên biệt cho quy trình bổ sung và gửi lại hồ sơ xác minh:
    - Hiển thị danh sách hạng mục Admin yêu cầu bổ sung thực tế.
    - Hiển thị lý do và hướng dẫn chi tiết cho từng hạng mục.
    - Cho phép sửa thông tin hoặc thay thế tài liệu tương ứng.
    - Không yêu cầu khai báo lại toàn bộ hồ sơ (dữ liệu cũ được pre-filled an toàn).
    - Kiểm tra quyền sửa nghiêm ngặt theo trạng thái hồ sơ.
    - Không cho phép người dùng tự xóa yêu cầu bổ sung hoặc tự đổi trạng thái.
    """
    uid = session.get('user_id')
    if uid and not isinstance(uid, int):
        session.clear()
        flash(_t('flash.login_required'), 'warning')
        return redirect(url_for('login'))

    user = User.query.get(uid)
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('login'))

    if user.role != 'translator':
        flash('Chức năng bổ sung hồ sơ xác minh chỉ dành riêng cho tài khoản phiên dịch viên.', 'warning')
        return redirect(url_for('account_profile'))

    from services.verification import get_verification_revision_details, can_user_revise_verification, TranslatorVerification
    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()

    can_rev, rev_err = can_user_revise_verification(user, verification)
    if not can_rev:
        flash(rev_err, 'warning')
        if not verification or getattr(verification, 'status', 'draft') in ('draft', 'not_started'):
            return redirect(url_for('verification_form'))
        return redirect(url_for('verification_status_page'))

    data = get_verification_revision_details(user)
    return render_template('verification_revision.html', user=user, data=data)


@app.route('/account/verification/revision/resubmit', methods=['POST'])
@app.route('/account/verification/resubmit', methods=['POST'])
@login_required
def verification_revision_resubmit():
    """
    Xử lý gửi lại hồ sơ sau khi bổ sung:
    - Hỗ trợ cả form submit multipart lẫn API JSON.
    - Lưu tài liệu thay thế vào Private Storage.
    - Cập nhật thông tin, tăng phiên bản và lập snapshot bất biến.
    - Bảo toàn phiên bản cũ và ghi nhận diff so sánh.
    - Chuyển hồ sơ về hàng đợi duyệt của Ban quản trị.
    - Ngăn chặn gửi lặp và xử lý rollback an toàn.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    is_json = request.is_json or 'application/json' in request.headers.get('Accept', '') or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not user or user.role != 'translator':
        if is_json:
            return jsonify({'success': False, 'message': 'Chỉ tài khoản phiên dịch viên mới có quyền gửi lại hồ sơ.'}), 403
        flash('Chỉ tài khoản phiên dịch viên mới có quyền gửi lại hồ sơ.', 'error')
        return redirect(url_for('account_profile'))

    from admin_auth import get_client_ip
    from services.verification import resubmit_verification, TranslatorVerification, can_user_revise_verification

    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
    can_rev, rev_err = can_user_revise_verification(user, verification)
    if not can_rev:
        st = getattr(verification, 'status', 'draft') if verification else 'not_started'
        code = 409 if st == 'pending' else (403 if st in ('approved', 'verified') else 400)
        if is_json:
            return jsonify({'success': False, 'message': rev_err, 'is_duplicate': bool(st == 'pending')}), code
        flash(rev_err, 'warning')
        return redirect(url_for('verification_status_page'))

    form_data = {}
    if request.is_json:
        form_data = request.get_json(silent=True) or {}
    else:
        form_data = request.form.to_dict()

    files = request.files

    ip = get_client_ip() if callable(get_client_ip) else request.remote_addr
    user_agent = request.headers.get('User-Agent', '')[:512]

    ok, msg, meta = resubmit_verification(
        user=user,
        form_data=form_data,
        files=files,
        ip_address=ip,
        user_agent=user_agent
    )

    if not ok:
        status_code = 409 if meta.get('is_duplicate') else 400
        if is_json:
            return jsonify({
                'success': False,
                'message': msg,
                'is_duplicate': meta.get('is_duplicate', False),
                'missing_items': meta.get('missing_items', []),
                'error_list': meta.get('error_list', [msg])
            }), status_code

        flash(msg, 'error')
        from services.verification import get_verification_revision_details
        data = get_verification_revision_details(user)
        data['error_message'] = msg
        data['missing_items'] = meta.get('missing_items', [])
        return render_template('verification_revision.html', user=user, data=data), 400

    if is_json:
        return jsonify({
            'success': True,
            'message': msg,
            'version': meta.get('version'),
            'previous_version': meta.get('previous_version'),
            'submitted_at': meta.get('submitted_at'),
            'status': meta.get('status')
        }), 200

    flash(msg, 'success')
    return redirect(url_for('verification_status_page'))


@app.route('/account/verification/revision/upload-document', methods=['POST'])
@login_required
def verification_revision_upload_document():
    """
    Endpoint tải lên tài liệu minh chứng thay thế từng tệp qua AJAX trong trang bổ sung hồ sơ:
    - Lưu vào Private Storage an toàn.
    - Cập nhật tài liệu cũ thành 'replaced'.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập.'}), 403

    from services.verification import TranslatorVerification, can_user_revise_verification, save_private_document

    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
    can_rev, rev_err = can_user_revise_verification(user, verification)
    if not can_rev:
        return jsonify({'success': False, 'message': rev_err}), 403

    doc_type = request.form.get('document_type')
    file = request.files.get('file') or request.files.get('document_file')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'Vui lòng chọn tệp tài liệu để tải lên.'}), 400

    ok, doc, err = save_private_document(file, user, doc_type=doc_type, verification=verification)
    if not ok:
        return jsonify({'success': False, 'message': err}), 400

    return jsonify({
        'success': True,
        'message': f'Đã tải lên tệp thay thế cho {doc.document_type.upper()} thành công.',
        'document': doc.to_dict()
    }), 200


@app.route('/api/account/verification/revision', methods=['GET'])
@login_required
def api_verification_revision_details():
    """
    API JSON trả về toàn bộ dữ liệu chi tiết phục vụ màn hình bổ sung hồ sơ.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập.'}), 403

    from services.verification import get_verification_revision_details
    data = get_verification_revision_details(user)
    return jsonify({'success': True, 'data': data})


@app.route('/api/account/verification/revision/resubmit', methods=['POST'])
@login_required
def api_verification_revision_resubmit():
    """
    API JSON gửi lại hồ sơ sau khi bổ sung.
    """
    return verification_revision_resubmit()


# ─── TRANSLATOR VERIFICATION NOTIFICATION CENTER ROUTES ───────────────────────

@app.route('/account/verification/notifications', methods=['GET'])
@app.route('/verification/notifications', methods=['GET'])
@login_required
def verification_notifications_page():
    """
    Trung tâm thông báo xác minh hồ sơ dành riêng cho phiên dịch viên (VietTranslate).
    Hiển thị thông báo gắn với các sự kiện thực tế:
    - Hồ sơ đã được gửi và tiếp nhận.
    - Admin yêu cầu bổ sung.
    - Hồ sơ được xác minh.
    - Hồ sơ bị từ chối.
    - Hồ sơ cần cập nhật hoặc xác minh lại khi chính sách yêu cầu.
    Hỗ trợ:
    - Đầy đủ tiêu đề, nội dung làm sạch (không chứa dữ liệu nhạy cảm), thời gian, trạng thái đọc.
    - Bộ lọc theo sự kiện và trạng thái đọc.
    - Trạng thái đang tải, lỗi kết nối và chưa có thông báo.
    - Đánh dấu đã đọc đơn lẻ và tất cả.
    - Điều hướng trực tiếp tới trang xử lý tương ứng.
    """
    uid = session.get('user_id')
    if uid and not isinstance(uid, int):
        session.clear()
        flash(_t('flash.login_required'), 'warning')
        return redirect(url_for('login'))

    user = User.query.get(uid)
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('login'))

    if user.role != 'translator':
        flash('Trung tâm thông báo xác minh chỉ dành riêng cho tài khoản phiên dịch viên.', 'warning')
        return redirect(url_for('account_profile'))

    from services.verification import get_translator_verification_notifications
    initial_data = get_translator_verification_notifications(user, status_filter='all', page=1)

    return render_template(
        'verification_notifications.html',
        user=user,
        initial_data=initial_data
    )


@app.route('/api/account/verification/notifications', methods=['GET'])
@login_required
def api_get_verification_notifications():
    """API JSON trả về danh sách thông báo xác minh hồ sơ của phiên dịch viên."""
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập.'}), 403

    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    from services.verification import get_translator_verification_notifications
    data = get_translator_verification_notifications(
        user, status_filter=status_filter, category_filter=category_filter, page=page, per_page=per_page
    )
    return jsonify({'success': True, 'data': data})


@app.route('/api/account/verification/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def api_read_verification_notification(notification_id):
    """API đánh dấu một thông báo xác minh cụ thể là đã đọc."""
    uid = session.get('user_id')
    from services.verification import mark_verification_notification_read
    ok, msg = mark_verification_notification_read(notification_id, uid)
    if not ok:
        return jsonify({'success': False, 'message': msg}), 400

    from models import Notification, VERIFICATION_NOTIFICATION_TYPES
    unread = Notification.query.filter(
        Notification.user_id == uid,
        Notification.type.in_(VERIFICATION_NOTIFICATION_TYPES),
        Notification.is_read == False
    ).count()
    return jsonify({'success': True, 'unread_count': unread})


@app.route('/api/account/verification/notifications/read-all', methods=['POST'])
@login_required
def api_read_all_verification_notifications():
    """API đánh dấu tất cả thông báo xác minh của phiên dịch viên là đã đọc."""
    uid = session.get('user_id')
    from services.verification import mark_all_verification_notifications_read
    ok, count = mark_all_verification_notifications_read(uid)
    return jsonify({'success': ok, 'updated_count': count, 'unread_count': 0})


@app.route('/api/account/verification/notifications/unread-count', methods=['GET'])
@login_required
def api_get_verification_notifications_unread_count():
    """API lấy số lượng thông báo xác minh chưa đọc của phiên dịch viên."""
    uid = session.get('user_id')
    from models import Notification, VERIFICATION_NOTIFICATION_TYPES
    unread = Notification.query.filter(
        Notification.user_id == uid,
        Notification.type.in_(VERIFICATION_NOTIFICATION_TYPES),
        Notification.is_read == False
    ).count()
    return jsonify({'success': True, 'unread_count': unread})


@app.route('/account/avatar/upload', methods=['POST'])
@login_required
def upload_avatar_endpoint():
    """Endpoint riêng biệt hỗ trợ tải ảnh đại diện qua AJAX hoặc form POST.
    TASK 7: Avatar upload dùng SQL only.
    """
    uid = session.get('user_id')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '') or request.is_json
    file = request.files.get('avatar')

    # TASK 9: Guard legacy/invalid session
    if uid and not isinstance(uid, int):
        session.clear()
        if is_ajax:
            return jsonify({'success': False, 'message': _t('flash.login_required')}), 401
        flash(_t('flash.login_required'), 'warning')
        return redirect(url_for('login'))

    user = User.query.get(uid)
    if not user:
        if is_ajax:
            return jsonify({'success': False, 'message': _t('flash.account_not_found')}), 404
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('account_profile'))

    ok, res = save_user_avatar(file, user.id, user.avatar)
    if not ok:
        msg = _t(res)
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('account_profile'))

    try:
        user.avatar = res
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        msg = _t('flash.avatar_upload_failed')
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 500
        flash(msg, 'error')
        return redirect(url_for('account_profile'))

    msg = _t('flash.avatar_updated')
    if is_ajax:
        return jsonify({'success': True, 'avatar_url': user.avatar_url, 'message': msg})
    flash(msg, 'success')
    return redirect(url_for('account_profile'))


@app.route('/account/avatar/remove', methods=['POST'])
@login_required
def remove_avatar_endpoint():
    """Endpoint gỡ ảnh đại diện tùy chỉnh trở về ảnh mặc định.
    TASK 7: Avatar remove dùng SQL only.
    """
    uid = session.get('user_id')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '') or request.is_json

    # TASK 9: Guard legacy/invalid session
    if uid and not isinstance(uid, int):
        session.clear()
        if is_ajax:
            return jsonify({'success': False, 'message': _t('flash.login_required')}), 401
        flash(_t('flash.login_required'), 'warning')
        return redirect(url_for('login'))

    user = User.query.get(uid)
    if not user:
        if is_ajax:
            return jsonify({'success': False, 'message': _t('flash.account_not_found')}), 404
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('account_profile'))

    delete_user_avatar(user.avatar)
    try:
        user.avatar = None
        db.session.commit()
    except Exception:
        db.session.rollback()
        msg = _t('flash.system_error')
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 500
        flash(msg, 'error')
        return redirect(url_for('account_profile'))

    msg = _t('flash.avatar_removed')
    if is_ajax:
        return jsonify({'success': True, 'avatar_url': user.avatar_url, 'initial': (user.name or 'U')[0].upper(), 'message': msg})
    flash(msg, 'success')
    return redirect(url_for('account_profile'))


def translator_accepts_job(translator, job):
    if translator.role != 'translator' or not translator.is_active:
        return False
        
    int_pref = getattr(translator, 'interpreter_preference', None)
    if int_pref:
        # 1. Kiểm tra cặp ngôn ngữ ưu tiên
        int_langs = int_pref.get_languages_list()
        if int_langs:
            import unicodedata
            def _clean(val):
                if not val:
                    return ''
                return unicodedata.normalize('NFKD', str(val)).encode('ASCII', 'ignore').decode('utf-8').lower().replace(' ', '')

            job_src = _clean(job.source_lang)
            job_tgt = _clean(job.target_lang)
            match_lang = False
            for p in int_langs:
                p_standard = p.replace('->', '➔').replace('>', '➔')
                if '➔' in p_standard:
                    parts = p_standard.split('➔', 1)
                    src_p, tgt_p = _clean(parts[0]), _clean(parts[1])
                    if (src_p == job_src and tgt_p == job_tgt) or (src_p == job_tgt and tgt_p == job_src):
                        match_lang = True
                        break
                else:
                    p_clean = _clean(p_standard)
                    if p_clean and (p_clean == job_src or p_clean == job_tgt):
                        match_lang = True
                        break
            if not match_lang:
                return False

        # 2. Kiểm tra hình thức làm việc (work_mode)
        job_loc = (job.event_location or '').lower()
        is_remote_job = 'online' in job_loc or 'tu xa' in job_loc or 'remote' in job_loc
        if int_pref.work_mode == 'online' and not is_remote_job:
            return False
        if int_pref.work_mode == 'offline' and is_remote_job:
            return False

        # 3. Kiểm tra khoảng thù lao nếu không cho phép nhận việc ngoài khoảng giá
        if int_pref.min_rate and not int_pref.allow_outside_rate:
            job_budget = job.budget_max or job.budget_min or 0
            if job_budget > 0 and job_budget < (int_pref.min_rate * 0.7):
                return False

        return True

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




@app.route('/account/history')
@login_required
def account_history():
    from datetime import date as date_cls
    import calendar
    user = get_current_user()
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('index'))

    status_filter = request.args.get('status')
    prop_filter = request.args.get('prop_status')
    period_filter = request.args.get('period')

    today = date_cls.today()
    first_of_month = today.replace(day=1)
    _, last_day = calendar.monthrange(today.year, today.month)
    end_of_month = today.replace(day=last_day)
    period_label = f"Tháng {today.month:02d}/{today.year}"

    if user.role == 'hirer':
        from services.transactions import list_hirer_transactions, STATUSES
        q = request.args.get('q', '').strip()[:100]
        status = status_filter if status_filter in STATUSES else ''
        page = request.args.get('page', 1, type=int) or 1
        rows, total, page, pages = list_hirer_transactions(user.id, q=q, status=status, page=page)
        # Tổng chi tính trên các hợp đồng đã thanh toán (đã vào escrow trở đi)
        paid = Contract.query.filter(Contract.hirer_id == user.id,
                                     Contract.status.in_(('in_progress', 'completed'))).all()
        finance = {
            'total': sum(c.agreed_price for c in paid),
            'paid_count': len(paid),
            'holding': sum(c.agreed_price for c in paid if c.status == 'in_progress'),
        }
        return render_template('account_history.html', user=user, contracts=[], proposals=[], finance=finance,
                               status_filter=status, prop_filter=prop_filter,
                               period_filter=period_filter, period_label=period_label,
                               tx_rows=rows, tx_total=total, tx_page=page, tx_pages=pages,
                               tx_q=q, tx_status=status, tx_statuses=STATUSES)
    else:
        query = Contract.query.filter_by(translator_id=user.id)
        if status_filter:
            if status_filter in ('in_progress', 'active', 'escrow_held'):
                query = query.filter(Contract.status.in_(['in_progress', 'active', 'escrow_held']))
            else:
                query = query.filter_by(status=status_filter)

        if period_filter == 'current_month':
            # Với hợp đồng đã hoàn tất, kỳ thống kê căn cứ vào ngày hoàn tất (updated_at)
            if status_filter == 'completed':
                query = query.filter(Contract.updated_at >= first_of_month)
            else:
                query = query.filter(
                    db.or_(Contract.updated_at >= first_of_month, Contract.created_at >= first_of_month)
                )

        contracts = query.order_by(Contract.created_at.desc()).all()

        prop_query = Proposal.query.filter_by(translator_id=user.id)
        if prop_filter:
            prop_query = prop_query.filter_by(status=prop_filter)
        proposals = prop_query.order_by(Proposal.created_at.desc()).all()

    filtered_income_total = sum(c.agreed_price for c in contracts if c.agreed_price)

    return render_template(
        'account_history.html',
        user=user,
        contracts=contracts,
        proposals=proposals,
        status_filter=status_filter,
        prop_filter=prop_filter,
        period_filter=period_filter,
        period_label=period_label,
        filtered_income_total=filtered_income_total
    )

@app.route('/account/history/<int:contract_id>')
@login_required
def account_transaction_detail(contract_id):
    user = get_current_user()
    if not user or user.role != 'hirer':
        abort(403)
    from services.transactions import get_hirer_transaction
    row, payments = get_hirer_transaction(user.id, contract_id)
    return render_template('account_transaction.html', user=user, row=row, payments=payments)


def _format_event_payload(
    event_id,
    schedule_id,
    contract,
    job,
    service,
    sch_date,
    start_time_obj,
    end_time_obj,
    buffer_before,
    buffer_after,
    raw_status,
    today,
    now_time,
    source_type='schedule'
):
    from datetime import datetime as dt_datetime, timedelta
    import re

    # 1. Tiêu đề công việc
    if job and job.title:
        title = job.title
    elif service and getattr(service, 'name', None):
        title = service.name
    elif contract:
        title = f"Hợp đồng phiên dịch #{contract.id}"
    else:
        title = f"Ca làm việc #{schedule_id or ''}"

    # 2. Ngôn ngữ & Chiều dịch
    language_pair = None
    source_lang = None
    target_lang = None
    if job:
        source_lang = getattr(job, 'source_lang', None)
        target_lang = getattr(job, 'target_lang', None)
        if source_lang and target_lang:
            language_pair = f"{source_lang} ➔ {target_lang}"
        elif source_lang or target_lang:
            language_pair = source_lang or target_lang
    elif service:
        source_lang = getattr(service, 'source_language', None)
        target_lang = getattr(service, 'target_language', None)
        if source_lang and target_lang:
            language_pair = f"{source_lang} ➔ {target_lang}"

    # 3. Chuyên ngành & Yêu cầu ca làm
    specialty = None
    requirements = None
    attachments_count = 0
    if job:
        specialty = getattr(job, 'specialty', None) or getattr(job, 'category', None)
        requirements = getattr(job, 'extra_requirements', None) or getattr(job, 'description', None)
        if requirements:
            requirements = requirements.strip()
        attachments_count = len(job.attachments) if getattr(job, 'attachments', None) else 0

    # 4. Hình thức & Địa điểm & Đường link họp online
    raw_location = (contract.location if contract else '') or (job.event_location if job else '') or ''
    raw_location = raw_location.strip()
    is_onsite = bool(raw_location and not any(k in raw_location.lower() for k in ['online', 'từ xa', 'remote', 'zoom', 'teams', 'google meet']))
    work_type = "Trực tiếp" if is_onsite else "Trực tuyến"
    location_display = raw_location if raw_location else ("Online / Từ xa" if not is_onsite else "Chưa cập nhật")

    meeting_url = None
    combined_text = f"{raw_location} {requirements or ''}"
    urls = re.findall(r'(https?://[^\s]+)', combined_text)
    if urls:
        meeting_url = urls[0]

    # 5. Thông tin Khách hàng
    hirer_name = None
    hirer_phone = None
    if contract and contract.hirer:
        hirer_name = contract.hirer.name
        hirer_phone = contract.hirer.phone
    elif job and job.hirer:
        hirer_name = job.hirer.name
        hirer_phone = job.hirer.phone

    # 6. Đánh giá thời gian & Trạng thái chuẩn nghiệp vụ
    is_today = (sch_date == today)
    is_upcoming_soon = (sch_date == today or sch_date == today + timedelta(days=1))
    is_past = (sch_date < today) or (is_today and end_time_obj < now_time)

    if contract:
        shift_info = contract.shift_status_info
        status_code = shift_info['code']
        status_label = shift_info['label']
        status_desc = shift_info.get('desc', '')
        badge_class = shift_info.get('badge_class', '')
        dot_class = shift_info.get('dot_class', '')
        can_checkin = is_today and shift_info.get('can_checkin', False)
        can_report_issue = shift_info.get('can_report_issue', False)
        can_deliver = shift_info.get('can_deliver', False)
        can_review = shift_info.get('can_review', False)
    else:
        if is_today and (start_time_obj <= now_time <= end_time_obj) and raw_status == 'active':
            status_code = 'in_progress'
            status_label = 'Đang diễn ra'
            status_desc = 'Ca làm đang trong khung giờ diễn ra hôm nay.'
            badge_class = 'bg-emerald-50 text-emerald-800 border-emerald-300'
            dot_class = 'bg-emerald-500 animate-pulse'
            can_checkin = True
            can_report_issue = True
            can_deliver = True
            can_review = False
        elif raw_status == 'reserved':
            status_code = 'escrow_pending'
            status_label = 'Chờ xác nhận'
            status_desc = 'Ca làm đang chờ bên tuyển dụng hoàn tất ký quỹ Escrow.'
            badge_class = 'bg-amber-50 text-amber-700 border-amber-200'
            dot_class = 'bg-amber-500'
            can_checkin = False
            can_report_issue = False
            can_deliver = False
            can_review = False
        elif raw_status == 'completed' or is_past:
            status_code = 'completed'
            status_label = 'Hoàn thành'
            status_desc = 'Ca làm đã hoàn tất.'
            badge_class = 'bg-emerald-50 text-emerald-700 border-emerald-200'
            dot_class = 'bg-emerald-500'
            can_checkin = False
            can_report_issue = False
            can_deliver = False
            can_review = True
        else:
            status_code = 'upcoming'
            status_label = 'Đã xác nhận'
            status_desc = 'Ca làm đã được chốt lịch và sẵn sàng thực hiện.'
            badge_class = 'bg-sky-50 text-sky-700 border-sky-200'
            dot_class = 'bg-sky-500'
            can_checkin = False
            can_report_issue = True
            can_deliver = False
            can_review = False

    is_ongoing = (status_code == 'in_progress')

    # 7. Tính thời lượng ca (Duration)
    duration_str = None
    try:
        dur_mins = (end_time_obj.hour * 60 + end_time_obj.minute) - (start_time_obj.hour * 60 + start_time_obj.minute)
        if dur_mins > 0:
            dur_h = dur_mins // 60
            dur_m = dur_mins % 60
            if dur_h > 0 and dur_m > 0:
                duration_str = f"{dur_h} giờ {dur_m} phút"
            elif dur_h > 0:
                duration_str = f"{dur_h} giờ"
            else:
                duration_str = f"{dur_m} phút"
    except Exception:
        pass

    # 8. Thù lao & Thanh toán Escrow
    agreed_price = contract.agreed_price if (contract and contract.agreed_price) else None
    platform_fee = contract.platform_fee if (contract and contract.agreed_price) else None
    net_amount = contract.translator_net_amount if (contract and contract.agreed_price) else None
    payment_status = contract.payment_status_info.get('label') if contract else None

    # 9. Lịch sử sự kiện quan trọng gần nhất
    events_log = []
    if contract and getattr(contract, 'events', None):
        for ev_item in sorted(contract.events, key=lambda x: x.created_at or dt_datetime.min, reverse=True)[:3]:
            events_log.append({
                'event_type': ev_item.event_type,
                'note': ev_item.note or '',
                'time': ev_item.created_at.strftime('%H:%M %d/%m/%Y') if ev_item.created_at else ''
            })

    # 10. URLs điều hướng an toàn
    transaction_url = url_for('transaction_detail', contract_id=contract.id) if contract else None
    job_detail_url = url_for('job_detail', job_id=job.id) if job else (url_for('job_detail', job_id=contract.job_id) if (contract and contract.job_id) else None)
    income_url = url_for('account_history') if (contract and status_code == 'completed') else None

    WEEKDAYS_VN = {
        0: 'Thứ Hai', 1: 'Thứ Ba', 2: 'Thứ Tư', 3: 'Thứ Năm',
        4: 'Thứ Sáu', 5: 'Thứ Bảy', 6: 'Chủ Nhật'
    }

    return {
        'id': event_id,
        'schedule_id': schedule_id,
        'contract_id': contract.id if contract else None,
        'job_id': job.id if job else (contract.job_id if contract else None),
        'title': title,
        'date': sch_date.strftime('%Y-%m-%d'),
        'date_display': sch_date.strftime('%d/%m/%Y'),
        'day_of_week': WEEKDAYS_VN.get(sch_date.weekday(), ''),
        'start_time': start_time_obj.strftime('%H:%M'),
        'end_time': end_time_obj.strftime('%H:%M'),
        'duration_str': duration_str,
        'status': status_code,
        'status_label': status_label,
        'status_desc': status_desc,
        'badge_class': badge_class,
        'dot_class': dot_class,
        'is_ongoing': is_ongoing,
        'is_past': is_past,
        'is_upcoming_soon': is_upcoming_soon,
        'location': location_display,
        'work_type': work_type,
        'meeting_url': meeting_url,
        'language_pair': language_pair,
        'specialty': specialty,
        'requirements': requirements,
        'attachments_count': attachments_count,
        'hirer_name': hirer_name or "Khách hàng VietTranslate",
        'hirer_phone': hirer_phone,
        'price': agreed_price,
        'net_amount': net_amount,
        'platform_fee': platform_fee,
        'payment_status': payment_status,
        'buffer_before': buffer_before or 0,
        'buffer_after': buffer_after or 30,
        'can_checkin': can_checkin,
        'can_report_issue': can_report_issue,
        'can_deliver': can_deliver,
        'can_review': can_review,
        'events_log': events_log,
        'transaction_url': transaction_url,
        'detail_url': job_detail_url,
        'income_url': income_url,
        'source': source_type
    }

def _get_translator_calendar_events(user_id):
    """
    Tập hợp và chuẩn hóa toàn bộ các sự kiện ca làm việc của phiên dịch viên.
    Bao gồm ca từ TranslatorSchedule và các Contract có lịch hợp lệ.
    """
    from datetime import date as dt_date, datetime as dt_datetime
    from services.schedule import _parse_date, _parse_time
    
    today = dt_date.today()
    now_dt = dt_datetime.now()
    now_time = now_dt.time()
    
    events = []
    seen_contract_ids = set()
    
    # Nguồn 1: TranslatorSchedule (chính thức)
    schedules = TranslatorSchedule.query.filter(
        TranslatorSchedule.translator_id == user_id,
        TranslatorSchedule.status != 'cancelled'
    ).order_by(TranslatorSchedule.scheduled_date.asc(), TranslatorSchedule.start_time.asc()).all()
    
    for sch in schedules:
        if not sch.scheduled_date or not sch.start_time or not sch.end_time:
            continue
            
        if getattr(sch, 'schedule_type', 'shift') == 'busy' or (not sch.contract_id and not sch.job_id and not sch.service_id):
            WEEKDAYS_VN = {
                0: 'Thứ Hai', 1: 'Thứ Ba', 2: 'Thứ Tư', 3: 'Thứ Năm',
                4: 'Thứ Sáu', 5: 'Thứ Bảy', 6: 'Chủ Nhật'
            }
            is_all_day = getattr(sch, 'is_all_day', False) or (sch.start_time.hour == 0 and sch.start_time.minute == 0 and sch.end_time.hour == 23 and sch.end_time.minute >= 50)
            dur_mins = (sch.end_time.hour * 60 + sch.end_time.minute) - (sch.start_time.hour * 60 + sch.start_time.minute)
            if is_all_day:
                busy_dur_str = 'Cả ngày'
            elif dur_mins > 0:
                dh = dur_mins // 60
                dm = dur_mins % 60
                if dh > 0 and dm > 0:
                    busy_dur_str = f"{dh} giờ {dm} phút"
                elif dh > 0:
                    busy_dur_str = f"{dh} giờ"
                else:
                    busy_dur_str = f"{dm} phút"
            else:
                busy_dur_str = 'Cả ngày'

            events.append({
                'id': f"busy_{sch.id}",
                'busy_id': sch.id,
                'schedule_id': sch.id,
                'contract_id': None,
                'job_id': None,
                'event_type': 'busy',
                'title': sch.note or "Thời gian không khả dụng",
                'note': sch.note or "",
                'date': sch.scheduled_date.strftime('%Y-%m-%d'),
                'date_display': sch.scheduled_date.strftime('%d/%m/%Y'),
                'day_of_week': WEEKDAYS_VN.get(sch.scheduled_date.weekday(), ''),
                'start_time': sch.start_time.strftime('%H:%M') if not is_all_day else '00:00',
                'end_time': sch.end_time.strftime('%H:%M') if not is_all_day else '23:59',
                'is_all_day': is_all_day,
                'duration_str': busy_dur_str,
                'status': 'busy',
                'status_label': 'Bận / Không khả dụng',
                'status_desc': 'Khoảng thời gian này bạn đã đánh dấu bận. Hệ thống sẽ chặn các lịch hẹn trùng giờ.',
                'badge_class': 'bg-slate-100 text-slate-700 border-slate-300',
                'dot_class': 'bg-slate-500',
                'work_type': 'Cá nhân',
                'location': 'Không khả dụng',
                'meeting_url': None,
                'is_ongoing': (sch.scheduled_date == today and sch.start_time <= now_time <= sch.end_time),
                'is_past': (sch.scheduled_date < today) or (sch.scheduled_date == today and sch.end_time < now_time),
                'can_checkin': False,
                'can_report_issue': False,
                'can_deliver': False,
                'can_review': False,
                'events_log': [],
                'source': 'busy'
            })
            continue

        c = sch.contract
        j = sch.job or (c.job if c else None)
        s = sch.service or (c.service if c else None)
        
        if c:
            seen_contract_ids.add(c.id)
            
        payload = _format_event_payload(
            event_id=f"sch_{sch.id}",
            schedule_id=sch.id,
            contract=c,
            job=j,
            service=s,
            sch_date=sch.scheduled_date,
            start_time_obj=sch.start_time,
            end_time_obj=sch.end_time,
            buffer_before=sch.buffer_before_minutes,
            buffer_after=sch.buffer_after_minutes,
            raw_status=sch.status,
            today=today,
            now_time=now_time,
            source_type='schedule'
        )
        events.append(payload)
        
    # Nguồn 2: Bổ sung các Contract có lịch làm việc mà chưa tạo TranslatorSchedule
    contracts = Contract.query.filter(
        Contract.translator_id == user_id,
        Contract.status.in_(['in_progress', 'active', 'escrow_held', 'completed', 'escrow_pending'])
    ).all()
    
    for c in contracts:
        if c.id in seen_contract_ids:
            continue
        c_date = _parse_date(c.scheduled_date)
        if not c_date:
            continue
        c_start = _parse_time(c.scheduled_time_start)
        c_end = _parse_time(c.scheduled_time_end)
        if not c_start or not c_end:
            continue
            
        seen_contract_ids.add(c.id)
        j = c.job
        s = c.service
        
        payload = _format_event_payload(
            event_id=f"ctr_{c.id}",
            schedule_id=None,
            contract=c,
            job=j,
            service=s,
            sch_date=c_date,
            start_time_obj=c_start,
            end_time_obj=c_end,
            buffer_before=0,
            buffer_after=30,
            raw_status=c.status,
            today=today,
            now_time=now_time,
            source_type='contract'
        )
        events.append(payload)
        
    events.sort(key=lambda x: (x['date'], x['start_time']))
    return events, schedules

@app.route('/my-schedule')
@login_required
def my_schedule():
    user = get_current_user()
    if not user or user.role != 'translator':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('index'))
    
    tab = request.args.get('tab', '').strip().lower()
    events_data, schedules = _get_translator_calendar_events(user.id)
    
    busy_schedules = TranslatorSchedule.query.filter(
        TranslatorSchedule.translator_id == user.id,
        TranslatorSchedule.schedule_type == 'busy',
        TranslatorSchedule.status != 'cancelled'
    ).order_by(TranslatorSchedule.scheduled_date.desc(), TranslatorSchedule.start_time.asc()).all()
    
    return render_template(
        'translator_schedule.html',
        user=user,
        schedules=schedules,
        events_data=events_data,
        current_tab=tab,
        busy_schedules=busy_schedules
    )

@app.route('/api/my-schedule')
@login_required
def api_my_schedule():
    user = get_current_user()
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
        
    events_data, _ = _get_translator_calendar_events(user.id)
    busy_schedules = TranslatorSchedule.query.filter(
        TranslatorSchedule.translator_id == user.id,
        TranslatorSchedule.schedule_type == 'busy',
        TranslatorSchedule.status != 'cancelled'
    ).order_by(TranslatorSchedule.scheduled_date.desc(), TranslatorSchedule.start_time.asc()).all()

    busy_list = [{
        'id': b.id,
        'date': b.scheduled_date.strftime('%Y-%m-%d') if b.scheduled_date else '',
        'date_display': b.scheduled_date.strftime('%d/%m/%Y') if b.scheduled_date else '',
        'start_time': b.start_time.strftime('%H:%M') if b.start_time else '00:00',
        'end_time': b.end_time.strftime('%H:%M') if b.end_time else '23:59',
        'is_all_day': bool(getattr(b, 'is_all_day', False)),
        'note': b.note or 'Bận việc riêng'
    } for b in busy_schedules]

    return jsonify({
        'success': True,
        'events': events_data,
        'busy_schedules': busy_list,
        'count': len(events_data)
    })

# ─── API QUẢN LÝ THỜI GIAN KHÔNG KHẢ DỤNG (3.3) ──────────────────────────────

@app.route('/api/my-schedule/busy-time', methods=['POST'])
@login_required
def api_add_busy_time():
    user = get_current_user()
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền thực hiện.'}), 403

    from services.schedule import _parse_date, _parse_time, datetime_intervals_overlap, build_effective_interval
    from datetime import timedelta, date as dt_date, time as dt_time

    data = request.get_json(silent=True) or request.form

    start_date_str = (data.get('start_date') or '').strip()
    end_date_str = (data.get('end_date') or '').strip() or start_date_str
    is_all_day = bool(data.get('is_all_day') in [True, 'true', '1', 1, 'on'])
    start_time_str = (data.get('start_time') or '').strip()
    end_time_str = (data.get('end_time') or '').strip()
    note = (data.get('note') or '').strip()

    if not start_date_str:
        return jsonify({'success': False, 'message': 'Vui lòng chọn ngày bắt đầu.'}), 400

    start_date = _parse_date(start_date_str)
    end_date = _parse_date(end_date_str)

    if not start_date or not end_date:
        return jsonify({'success': False, 'message': 'Định dạng ngày không hợp lệ.'}), 400

    if end_date < start_date:
        return jsonify({'success': False, 'message': 'Ngày kết thúc không được trước ngày bắt đầu.'}), 400

    if (end_date - start_date).days > 60:
        return jsonify({'success': False, 'message': 'Khoảng thời gian bận không được vượt quá 60 ngày liên tục.'}), 400

    if is_all_day:
        start_time_obj = dt_time(0, 0)
        end_time_obj = dt_time(23, 59)
    else:
        if not start_time_str or not end_time_str:
            return jsonify({'success': False, 'message': 'Vui lòng nhập giờ bắt đầu và giờ kết thúc.'}), 400
        start_time_obj = _parse_time(start_time_str)
        end_time_obj = _parse_time(end_time_str)
        if not start_time_obj or not end_time_obj:
            return jsonify({'success': False, 'message': 'Định dạng giờ không hợp lệ.'}), 400
        if start_date == end_date and end_time_obj <= start_time_obj:
            return jsonify({'success': False, 'message': 'Giờ kết thúc phải sau giờ bắt đầu.'}), 400

    # Kiểm tra xung đột với ca làm việc đã xác nhận (Contract / Shift)
    confirmed_schedules = TranslatorSchedule.query.filter(
        TranslatorSchedule.translator_id == user.id,
        TranslatorSchedule.status.in_(['reserved', 'active']),
        TranslatorSchedule.contract_id.isnot(None)
    ).all()

    active_contracts = Contract.query.filter(
        Contract.translator_id == user.id,
        Contract.status.in_(['in_progress', 'active', 'escrow_held', 'delivered', 'escrow_pending'])
    ).all()

    curr_d = start_date
    while curr_d <= end_date:
        busy_eff_start, busy_eff_end = build_effective_interval(curr_d, start_time_obj, end_time_obj, 0, 0)

        for sch in confirmed_schedules:
            if sch.scheduled_date == curr_d:
                sch_start, sch_end = build_effective_interval(
                    sch.scheduled_date, sch.start_time, sch.end_time,
                    getattr(sch, 'buffer_before_minutes', 0),
                    getattr(sch, 'buffer_after_minutes', 30)
                )
                if datetime_intervals_overlap(busy_eff_start, busy_eff_end, sch_start, sch_end):
                    job_name = sch.contract.job.title if (sch.contract and sch.contract.job) else f"Hợp đồng #{sch.contract_id}"
                    return jsonify({
                        'success': False,
                        'message': f'Không thể đặt thời gian bận do trùng với ca làm đã xác nhận: "{job_name}" ({sch.start_time.strftime("%H:%M")} - {sch.end_time.strftime("%H:%M")}) ngày {curr_d.strftime("%d/%m/%Y")}.'
                    }), 400

        for c in active_contracts:
            c_d = _parse_date(c.scheduled_date)
            if c_d == curr_d:
                c_st = _parse_time(c.scheduled_time_start)
                c_et = _parse_time(c.scheduled_time_end)
                if c_st and c_et:
                    c_start, c_end = build_effective_interval(c_d, c_st, c_et, 0, 30)
                    if datetime_intervals_overlap(busy_eff_start, busy_eff_end, c_start, c_end):
                        job_name = c.job.title if c.job else f"Hợp đồng #{c.id}"
                        return jsonify({
                            'success': False,
                            'message': f'Không thể đặt thời gian bận do trùng với ca làm đã xác nhận: "{job_name}" ({c_st.strftime("%H:%M")} - {c_et.strftime("%H:%M")}) ngày {curr_d.strftime("%d/%m/%Y")}.'
                        }), 400

        curr_d += timedelta(days=1)

    # Lưu bản ghi thời gian bận
    curr_d = start_date
    created_count = 0
    while curr_d <= end_date:
        existing_busy = TranslatorSchedule.query.filter_by(
            translator_id=user.id,
            scheduled_date=curr_d,
            schedule_type='busy'
        ).filter(TranslatorSchedule.status != 'cancelled').first()

        if existing_busy:
            existing_busy.start_time = start_time_obj
            existing_busy.end_time = end_time_obj
            existing_busy.is_all_day = is_all_day
            existing_busy.note = note or 'Bận việc riêng'
        else:
            new_busy = TranslatorSchedule(
                translator_id=user.id,
                contract_id=None,
                job_id=None,
                service_id=None,
                scheduled_date=curr_d,
                start_time=start_time_obj,
                end_time=end_time_obj,
                buffer_before_minutes=0,
                buffer_after_minutes=0,
                status='active',
                schedule_type='busy',
                note=note or 'Bận việc riêng',
                is_all_day=is_all_day
            )
            db.session.add(new_busy)
        created_count += 1
        curr_d += timedelta(days=1)

    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'Đã thiết lập thời gian không khả dụng ({created_count} ngày) thành công.'
    })


@app.route('/api/my-schedule/busy-time/<int:busy_id>', methods=['PUT', 'POST'])
@login_required
def api_update_busy_time(busy_id):
    user = get_current_user()
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền thực hiện.'}), 403

    busy = TranslatorSchedule.query.get_or_404(busy_id)
    if busy.translator_id != user.id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa bản ghi này.'}), 403

    if busy.contract_id is not None:
        return jsonify({'success': False, 'message': 'Không thể sửa ca làm việc qua chức năng này.'}), 400

    from services.schedule import _parse_date, _parse_time, datetime_intervals_overlap, build_effective_interval
    from datetime import time as dt_time

    data = request.get_json(silent=True) or request.form

    date_str = (data.get('date') or data.get('start_date') or '').strip()
    is_all_day = bool(data.get('is_all_day') in [True, 'true', '1', 1, 'on'])
    start_time_str = (data.get('start_time') or '').strip()
    end_time_str = (data.get('end_time') or '').strip()
    note = (data.get('note') or '').strip()

    if not date_str:
        return jsonify({'success': False, 'message': 'Vui lòng chọn ngày.'}), 400

    parsed_date = _parse_date(date_str)
    if not parsed_date:
        return jsonify({'success': False, 'message': 'Định dạng ngày không hợp lệ.'}), 400

    if is_all_day:
        start_time_obj = dt_time(0, 0)
        end_time_obj = dt_time(23, 59)
    else:
        if not start_time_str or not end_time_str:
            return jsonify({'success': False, 'message': 'Vui lòng nhập giờ bắt đầu và giờ kết thúc.'}), 400
        start_time_obj = _parse_time(start_time_str)
        end_time_obj = _parse_time(end_time_str)
        if not start_time_obj or not end_time_obj:
            return jsonify({'success': False, 'message': 'Định dạng giờ không hợp lệ.'}), 400
        if end_time_obj <= start_time_obj:
            return jsonify({'success': False, 'message': 'Giờ kết thúc phải sau giờ bắt đầu.'}), 400

    # Kiểm tra xung đột với ca làm việc đã xác nhận (loại trừ chính busy_id)
    busy_eff_start, busy_eff_end = build_effective_interval(parsed_date, start_time_obj, end_time_obj, 0, 0)

    confirmed_schedules = TranslatorSchedule.query.filter(
        TranslatorSchedule.translator_id == user.id,
        TranslatorSchedule.status.in_(['reserved', 'active']),
        TranslatorSchedule.contract_id.isnot(None),
        TranslatorSchedule.id != busy_id
    ).all()

    for sch in confirmed_schedules:
        if sch.scheduled_date == parsed_date:
            sch_start, sch_end = build_effective_interval(
                sch.scheduled_date, sch.start_time, sch.end_time,
                getattr(sch, 'buffer_before_minutes', 0),
                getattr(sch, 'buffer_after_minutes', 30)
            )
            if datetime_intervals_overlap(busy_eff_start, busy_eff_end, sch_start, sch_end):
                job_name = sch.contract.job.title if (sch.contract and sch.contract.job) else f"Hợp đồng #{sch.contract_id}"
                return jsonify({
                    'success': False,
                    'message': f'Thời gian mới bị trùng với ca làm đã xác nhận: "{job_name}" ({sch.start_time.strftime("%H:%M")} - {sch.end_time.strftime("%H:%M")}).'
                }), 400

    active_contracts = Contract.query.filter(
        Contract.translator_id == user.id,
        Contract.status.in_(['in_progress', 'active', 'escrow_held', 'delivered', 'escrow_pending'])
    ).all()

    for c in active_contracts:
        c_d = _parse_date(c.scheduled_date)
        if c_d == parsed_date:
            c_st = _parse_time(c.scheduled_time_start)
            c_et = _parse_time(c.scheduled_time_end)
            if c_st and c_et:
                c_start, c_end = build_effective_interval(c_d, c_st, c_et, 0, 30)
                if datetime_intervals_overlap(busy_eff_start, busy_eff_end, c_start, c_end):
                    job_name = c.job.title if c.job else f"Hợp đồng #{c.id}"
                    return jsonify({
                        'success': False,
                        'message': f'Thời gian mới bị trùng với ca làm đã xác nhận: "{job_name}" ({c_st.strftime("%H:%M")} - {c_et.strftime("%H:%M")}).'
                    }), 400

    busy.scheduled_date = parsed_date
    busy.start_time = start_time_obj
    busy.end_time = end_time_obj
    busy.is_all_day = is_all_day
    busy.note = note or 'Bận việc riêng'
    busy.schedule_type = 'busy'
    busy.status = 'active'

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Đã cập nhật thời gian bận thành công.'
    })


@app.route('/api/my-schedule/busy-time/<int:busy_id>', methods=['DELETE'])
@login_required
def api_delete_busy_time(busy_id):
    user = get_current_user()
    if not user or user.role != 'translator':
        return jsonify({'success': False, 'message': 'Không có quyền thực hiện.'}), 403

    busy = TranslatorSchedule.query.get_or_404(busy_id)
    if busy.translator_id != user.id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền xóa bản ghi này.'}), 403

    if busy.contract_id is not None:
        return jsonify({'success': False, 'message': 'Không thể xóa ca làm việc qua chức năng này.'}), 400

    db.session.delete(busy)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Đã xóa thời gian bận thành công.'
    })

# ─── INTERPRETER INCOME MODULE (PHÂN HỆ THU NHẬP PHIÊN DỊCH VIÊN) ────────────

@app.route('/interpreter/income')
@login_required
def interpreter_income_root():
    user = get_current_user()
    if not user or user.role != 'translator':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('index'))
    return redirect(url_for('interpreter_income_overview'))

@app.route('/interpreter/income/overview')
@login_required
def interpreter_income_overview():
    user = get_current_user()
    if not user or user.role != 'translator':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('index'))

    import calendar
    from datetime import datetime as dt_cls, date as date_cls, timedelta

    # VN Timezone offset: UTC + 7
    # Calculations are done using Vietnam date/time conventions and converted to UTC for DB queries.
    now_utc = dt_cls.utcnow()
    now_vn = now_utc + timedelta(hours=7)
    today_vn = now_vn.date()

    period = request.args.get('period', 'current_month')
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()

    start_date_vn = None
    end_date_vn = None
    period_label = ""

    if period == 'last_month':
        # Tháng trước: từ ngày 1 đến ngày cuối cùng của tháng trước
        first_of_this_month = today_vn.replace(day=1)
        last_day_of_prev_month = first_of_this_month - timedelta(days=1)
        start_date_vn = last_day_of_prev_month.replace(day=1)
        end_date_vn = last_day_of_prev_month
        period_label = f"Tháng trước ({start_date_vn.strftime('%m/%Y')})"
    elif period == 'custom':
        # Khoảng ngày tùy chọn
        try:
            if start_date_str:
                start_date_vn = dt_cls.strptime(start_date_str, '%Y-%m-%d').date()
            if end_date_str:
                end_date_vn = dt_cls.strptime(end_date_str, '%Y-%m-%d').date()

            if start_date_vn and end_date_vn and start_date_vn > end_date_vn:
                start_date_vn, end_date_vn = end_date_vn, start_date_vn
                start_date_str, end_date_str = start_date_vn.strftime('%Y-%m-%d'), end_date_vn.strftime('%Y-%m-%d')

            if start_date_vn and end_date_vn:
                period_label = f"Từ {start_date_vn.strftime('%d/%m/%Y')} đến {end_date_vn.strftime('%d/%m/%Y')}"
            elif start_date_vn:
                period_label = f"Từ ngày {start_date_vn.strftime('%d/%m/%Y')}"
            elif end_date_vn:
                period_label = f"Đến ngày {end_date_vn.strftime('%d/%m/%Y')}"
            else:
                period = 'current_month'
        except ValueError:
            period = 'current_month'

    if period == 'current_month':
        start_date_vn = today_vn.replace(day=1)
        _, last_day = calendar.monthrange(today_vn.year, today_vn.month)
        end_date_vn = today_vn.replace(day=last_day)
        period_label = f"Tháng này ({today_vn.strftime('%m/%Y')})"

    # Convert VN dates to UTC range for filtering
    start_dt_utc = dt_cls.combine(start_date_vn, dt_cls.min.time()) - timedelta(hours=7) if start_date_vn else None
    end_dt_utc = dt_cls.combine(end_date_vn, dt_cls.max.time()) - timedelta(hours=7) if end_date_vn else None

    # Query all contracts for this translator excluding cancelled contracts
    all_contracts_query = Contract.query.filter(
        Contract.translator_id == user.id,
        Contract.status != 'cancelled'
    )
    all_contracts = all_contracts_query.order_by(Contract.created_at.desc()).all()

    # Filter contracts into mutually exclusive groups and apply date boundaries
    # Quy tắc ngày:
    # - Hợp đồng completed/reviewed: ngày giải ngân căn cứ theo updated_at (hoặc created_at nếu không có)
    # - Hợp đồng delivered, in_progress, escrow_held: ngày căn cứ theo event_sort_date hoặc created_at
    filtered_contracts = []

    total_gross = 0          # Tổng thu nhập gộp (100% agreed_price của các ca đã thanh toán trong kỳ)
    total_net = 0            # Thu nhập ròng thực nhận (90% translator_net_amount của các ca đã thanh toán trong kỳ)
    total_platform_fee = 0   # Phí nền tảng (10%)
    pending_payout = 0       # Đang chờ thanh toán (delivered)
    in_escrow = 0            # Đang xử lý / tạm giữ trong Escrow (in_progress, active, escrow_held)
    paid_count = 0
    pending_count = 0
    escrow_count = 0

    for c in all_contracts:
        is_completed = c.status in ('completed', 'reviewed')
        is_pending = c.status == 'delivered'
        is_escrow = c.status in ('in_progress', 'active', 'escrow_held')

        # Determine reference date for filtering
        if is_completed:
            ref_dt = c.updated_at or c.created_at
        else:
            if hasattr(c, 'event_sort_date') and c.event_sort_date:
                ref_dt = dt_cls.combine(c.event_sort_date, dt_cls.min.time())
            else:
                ref_dt = c.created_at

        # Check if contract falls into the selected period
        in_period = True
        if ref_dt:
            if start_dt_utc and ref_dt < start_dt_utc:
                in_period = False
            if end_dt_utc and ref_dt > end_dt_utc:
                in_period = False

        if in_period:
            filtered_contracts.append(c)
            agreed = c.agreed_price or 0
            net = c.translator_net_amount or int(agreed * 0.9)
            fee = c.platform_fee or int(agreed * 0.1)

            if is_completed:
                total_gross += agreed
                total_net += net
                total_platform_fee += fee
                paid_count += 1
            elif is_pending:
                pending_payout += net
                pending_count += 1
            elif is_escrow:
                in_escrow += net
                escrow_count += 1

    return render_template(
        'income_overview.html',
        user=user,
        contracts=filtered_contracts,
        period=period,
        period_label=period_label,
        start_date_str=start_date_str or (start_date_vn.strftime('%Y-%m-%d') if start_date_vn else ''),
        end_date_str=end_date_str or (end_date_vn.strftime('%Y-%m-%d') if end_date_vn else ''),
        total_gross=total_gross,
        total_net=total_net,
        total_platform_fee=total_platform_fee,
        pending_payout=pending_payout,
        in_escrow=in_escrow,
        paid_count=paid_count,
        pending_count=pending_count,
        escrow_count=escrow_count,
        total_contract_count=len(filtered_contracts)
    )

@app.route('/interpreter/income/details')
@login_required
def interpreter_income_details():
    user = get_current_user()
    if not user or user.role != 'translator':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('index'))

    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    # Query all active contracts for current interpreter
    query = Contract.query.filter(
        Contract.translator_id == user.id,
        Contract.status != 'cancelled'
    )

    # Filter by financial status
    if status_filter == 'paid':
        query = query.filter(Contract.status.in_(['completed', 'reviewed']))
    elif status_filter == 'escrow_held':
        query = query.filter(Contract.status.in_(['in_progress', 'active', 'escrow_held']))
    elif status_filter == 'delivered':
        query = query.filter(Contract.status == 'delivered')

    # Filter by search term q
    if q:
        safe_q = f"%{q}%"
        query = query.outerjoin(Job, Contract.job_id == Job.id).filter(
            db.or_(
                Contract.id.cast(db.String).ilike(safe_q),
                Job.title.ilike(safe_q)
            )
        )

    contracts = query.order_by(Contract.created_at.desc()).all()

    # Calculate metrics for the displayed list
    total_displayed_net = sum(c.translator_net_amount or int((c.agreed_price or 0) * 0.9) for c in contracts)
    total_displayed_gross = sum(c.agreed_price or 0 for c in contracts)
    total_displayed_fee = sum(c.platform_fee or int((c.agreed_price or 0) * 0.1) for c in contracts)

    return render_template(
        'income_details.html',
        user=user,
        contracts=contracts,
        q=q,
        status_filter=status_filter,
        total_displayed_net=total_displayed_net,
        total_displayed_gross=total_displayed_gross,
        total_displayed_fee=total_displayed_fee,
        total_count=len(contracts)
    )


@app.route('/interpreter/income/payouts')
@login_required
def interpreter_income_payouts():
    user = get_current_user()
    if not user or user.role != 'translator':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('index'))

    status_filter = request.args.get('status', 'all').strip()
    q = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()

    try:
        from services.projects import build_timeline
        from models import ContractEvent, PaymentTransaction, Report

        # Lấy tất cả hợp đồng của phiên dịch viên hiện tại (bảo đảm quyền truy cập)
        all_contracts = Contract.query.filter(
            Contract.translator_id == user.id
        ).order_by(Contract.created_at.desc()).all()

        # Bộ đếm số lượng theo giai đoạn tiến độ
        counts = {
            'all': len(all_contracts),
            'delivered': 0,          # Chờ nghiệm thu & giải ngân
            'escrow_held': 0,        # Đang giữ trong Escrow an toàn
            'completed': 0,          # Đã giải ngân thành công
            'revision_requested': 0, # Yêu cầu chỉnh sửa / Tạm giữ
            'escrow_pending': 0,     # Chờ khách ký quỹ
            'cancelled': 0           # Đã hủy / Hoàn tiền
        }

        # Tổng hợp số liệu tài chính theo nhóm trạng thái
        metrics = {
            'total_paid_net': 0,
            'total_delivered_net': 0,
            'total_escrow_held_net': 0,
            'total_revision_net': 0,
            'total_gross': 0,
            'total_fee': 0
        }

        for c in all_contracts:
            net = c.translator_net_amount or int((c.agreed_price or 0) * 0.9)
            gross = c.agreed_price or 0
            fee = c.platform_fee or int(gross * 0.1)

            if c.status in ['completed', 'reviewed']:
                counts['completed'] += 1
                metrics['total_paid_net'] += net
                metrics['total_gross'] += gross
                metrics['total_fee'] += fee
            elif c.status == 'delivered':
                counts['delivered'] += 1
                metrics['total_delivered_net'] += net
                metrics['total_gross'] += gross
                metrics['total_fee'] += fee
            elif c.status == 'revision_requested':
                counts['revision_requested'] += 1
                metrics['total_revision_net'] += net
                metrics['total_gross'] += gross
                metrics['total_fee'] += fee
            elif c.status in ['in_progress', 'active', 'escrow_held']:
                counts['escrow_held'] += 1
                metrics['total_escrow_held_net'] += net
                metrics['total_gross'] += gross
                metrics['total_fee'] += fee
            elif c.status == 'escrow_pending':
                counts['escrow_pending'] += 1
            elif c.status == 'cancelled':
                counts['cancelled'] += 1

        # Lọc danh sách theo status_filter
        if status_filter == 'delivered':
            filtered = [c for c in all_contracts if c.status == 'delivered']
        elif status_filter == 'escrow_held':
            filtered = [c for c in all_contracts if c.status in ['in_progress', 'active', 'escrow_held']]
        elif status_filter == 'completed':
            filtered = [c for c in all_contracts if c.status in ['completed', 'reviewed']]
        elif status_filter == 'revision_requested':
            filtered = [c for c in all_contracts if c.status == 'revision_requested']
        elif status_filter == 'escrow_pending':
            filtered = [c for c in all_contracts if c.status == 'escrow_pending']
        elif status_filter == 'cancelled':
            filtered = [c for c in all_contracts if c.status == 'cancelled']
        else:
            filtered = list(all_contracts)

        # Lọc theo từ khóa tìm kiếm (mã ca, tiêu đề công việc)
        if q:
            q_clean = q.lower().strip()
            filtered = [
                c for c in filtered
                if q_clean in str(c.id).lower()
                or (c.job and q_clean in c.job.title.lower())
                or (f"ca-{c.id}" in q_clean.replace(" ", ""))
                or (f"#ca-{c.id}" in q_clean.replace(" ", ""))
            ]

        # Sắp xếp
        if sort_by == 'oldest':
            filtered.sort(key=lambda c: c.created_at or datetime.min)
        elif sort_by == 'amount_desc':
            filtered.sort(key=lambda c: c.translator_net_amount or 0, reverse=True)
        elif sort_by == 'amount_asc':
            filtered.sort(key=lambda c: c.translator_net_amount or 0)
        else:  # 'newest' mặc định
            filtered.sort(key=lambda c: c.created_at or datetime.min, reverse=True)

        # Đóng gói dữ liệu bổ trợ cho từng hợp đồng
        contract_items = []
        for c in filtered:
            # Xác định các bước pipeline (1: Ký quỹ, 2: Thực hiện ca, 3: Bàn giao & Nghiệm thu, 4: Giải ngân)
            if c.status in ['completed', 'reviewed']:
                stage_step = 4
                stage_code = 'completed'
                stage_label = 'Đã giải ngân Escrow'
                stage_badge = 'bg-emerald-50 text-emerald-700 border-emerald-200'
                stage_dot = 'bg-emerald-500'
                stage_desc = 'Bên tuyển dụng đã nghiệm thu thành công. Thù lao 90% đã được giải ngân an toàn.'
            elif c.status == 'delivered':
                stage_step = 3
                stage_code = 'delivered'
                stage_label = 'Chờ nghiệm thu & Giải ngân'
                stage_badge = 'bg-purple-50 text-purple-700 border-purple-200'
                stage_dot = 'bg-purple-500 animate-pulse'
                stage_desc = 'Bạn đã bàn giao ca làm. Đang chờ khách hàng nghiệm thu để kích hoạt giải ngân.'
            elif c.status == 'revision_requested':
                stage_step = 3
                stage_code = 'revision_requested'
                stage_label = 'Yêu cầu chỉnh sửa / Tạm giữ'
                stage_badge = 'bg-amber-50 text-amber-800 border-amber-300'
                stage_dot = 'bg-amber-500'
                stage_desc = 'Khách hàng yêu cầu rà soát bổ sung. Thù lao đang tạm thời đóng băng trong Escrow.'
            elif c.status in ['in_progress', 'active', 'escrow_held']:
                stage_step = 2
                stage_code = 'escrow_held'
                stage_label = 'Đang giữ Escrow an toàn'
                stage_badge = 'bg-sky-50 text-sky-700 border-sky-200'
                stage_dot = 'bg-sky-500'
                stage_desc = 'Khách hàng đã ký quỹ 100% vào Escrow. Tiền được đảm bảo trong thời gian diễn ra ca làm.'
            elif c.status == 'escrow_pending':
                stage_step = 1
                stage_code = 'escrow_pending'
                stage_label = 'Chờ khách ký quỹ'
                stage_badge = 'bg-slate-100 text-slate-600 border-slate-200'
                stage_dot = 'bg-slate-400'
                stage_desc = 'Ca làm đã chốt, đang chờ bên tuyển dụng hoàn tất nạp tiền ký quỹ vào hệ thống.'
            elif c.status == 'cancelled':
                stage_step = 0
                stage_code = 'cancelled'
                stage_label = 'Đã hủy / Hoàn tiền'
                stage_badge = 'bg-rose-50 text-rose-700 border-rose-200'
                stage_dot = 'bg-rose-500'
                stage_desc = 'Ca làm đã bị hủy. Khoản thanh toán (nếu có) được hoàn trả theo quy định.'
            else:
                stage_step = 1
                stage_code = 'unknown'
                stage_label = 'Đang xử lý'
                stage_badge = 'bg-slate-100 text-slate-600 border-slate-200'
                stage_dot = 'bg-slate-400'
                stage_desc = 'Trạng thái giao dịch đang được cập nhật.'

            # Lấy thông tin thanh toán Escrow thực tế nếu có
            pay_tx = PaymentTransaction.query.filter_by(contract_id=c.id).order_by(PaymentTransaction.id.desc()).first()

            # Lấy ghi chú chỉnh sửa mới nhất nếu có
            last_rev = None
            if c.status == 'revision_requested':
                last_rev = ContractEvent.query.filter_by(
                    contract_id=c.id, event_type='revision_requested'
                ).order_by(ContractEvent.created_at.desc(), ContractEvent.id.desc()).first()

            # Lấy timeline các mốc thời gian thực tế
            timeline = build_timeline(c)

            # Kiểm tra xem có khiếu nại đang xử lý cho hợp đồng này không
            active_report = Report.query.filter(
                Report.related_contract_id == c.id,
                Report.status.in_(['new', 'investigating'])
            ).first()

            contract_items.append({
                'contract': c,
                'stage_step': stage_step,
                'stage_code': stage_code,
                'stage_label': stage_label,
                'stage_badge': stage_badge,
                'stage_dot': stage_dot,
                'stage_desc': stage_desc,
                'payment': pay_tx,
                'last_revision': last_rev,
                'timeline': timeline,
                'active_report': active_report
            })

        return render_template(
            'income_payouts.html',
            user=user,
            items=contract_items,
            counts=counts,
            metrics=metrics,
            status_filter=status_filter,
            q=q,
            sort_by=sort_by,
            total_displayed=len(contract_items),
            has_error=False
        )

    except Exception as e:
        flash('Có lỗi khi tải danh sách thanh toán. Vui lòng thử lại sau.', 'error')
        return render_template(
            'income_payouts.html',
            user=user,
            items=[],
            counts={'all': 0, 'delivered': 0, 'escrow_held': 0, 'completed': 0, 'revision_requested': 0, 'escrow_pending': 0, 'cancelled': 0},
            metrics={'total_paid_net': 0, 'total_delivered_net': 0, 'total_escrow_held_net': 0, 'total_revision_net': 0, 'total_gross': 0, 'total_fee': 0},
            status_filter=status_filter,
            q=q,
            sort_by=sort_by,
            total_displayed=0,
            has_error=True
        )

@app.route('/interpreter/income/transactions')
@login_required
def interpreter_income_transactions():
    user = get_current_user()
    if not user or user.role != 'translator':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('index'))

    status_filter = request.args.get('status', 'all').strip()
    period_filter = request.args.get('period', 'all').strip()
    q = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 15

    try:
        from models import PaymentTransaction, Contract, Job

        # Base query: Chỉ lấy giao dịch thuộc hợp đồng mà user là phiên dịch viên (bảo đảm quyền truy cập)
        base_query = PaymentTransaction.query.join(
            Contract, PaymentTransaction.contract_id == Contract.id
        ).filter(
            Contract.translator_id == user.id
        )

        # Tính toán bộ đếm và chỉ số KPI tài chính trên toàn bộ giao dịch của người dùng
        all_txs = base_query.all()
        counts = {
            'all': len(all_txs),
            'completed': 0,
            'escrow_pending': 0,
            'refunded': 0
        }
        metrics = {
            'total_paid_net': 0,
            'total_escrow_held_gross': 0,
            'total_refunded_gross': 0,
            'total_transactions': len(all_txs)
        }

        for tx in all_txs:
            net = tx.contract.translator_net_amount or int((tx.contract.agreed_price or 0) * 0.9)
            gross = tx.amount or (tx.contract.agreed_price or 0)
            if tx.status == 'completed':
                counts['completed'] += 1
                metrics['total_paid_net'] += net
            elif tx.status == 'escrow_pending':
                counts['escrow_pending'] += 1
                metrics['total_escrow_held_gross'] += gross
            elif tx.status == 'refunded':
                counts['refunded'] += 1
                metrics['total_refunded_gross'] += gross

        # Áp dụng bộ lọc trạng thái
        filter_query = base_query
        if status_filter != 'all':
            filter_query = filter_query.filter(PaymentTransaction.status == status_filter)

        # Áp dụng bộ lọc thời gian
        if period_filter == 'current_month':
            now = datetime.utcnow()
            first_day = datetime(now.year, now.month, 1)
            filter_query = filter_query.filter(PaymentTransaction.created_at >= first_day)
        elif period_filter == 'last_month':
            now = datetime.utcnow()
            first_this_month = datetime(now.year, now.month, 1)
            last_month_end = first_this_month - timedelta(seconds=1)
            first_last_month = datetime(last_month_end.year, last_month_end.month, 1)
            filter_query = filter_query.filter(
                PaymentTransaction.created_at >= first_last_month,
                PaymentTransaction.created_at < first_this_month
            )

        # Áp dụng tìm kiếm q (Mã GD, Ref, Mã hợp đồng, Tên ca làm)
        if q:
            q_clean = f"%{q}%"
            filter_query = filter_query.outerjoin(Job, Contract.job_id == Job.id).filter(
                db.or_(
                    PaymentTransaction.id.cast(db.String).ilike(q_clean),
                    PaymentTransaction.transaction_ref.ilike(q_clean),
                    Contract.id.cast(db.String).ilike(q_clean),
                    Job.title.ilike(q_clean)
                )
            )

        # Áp dụng sắp xếp
        if sort_by == 'oldest':
            filter_query = filter_query.order_by(PaymentTransaction.created_at.asc(), PaymentTransaction.id.asc())
        elif sort_by == 'amount_desc':
            filter_query = filter_query.order_by(PaymentTransaction.amount.desc(), PaymentTransaction.id.desc())
        elif sort_by == 'amount_asc':
            filter_query = filter_query.order_by(PaymentTransaction.amount.asc(), PaymentTransaction.id.asc())
        else:  # 'newest' mặc định
            filter_query = filter_query.order_by(PaymentTransaction.created_at.desc(), PaymentTransaction.id.desc())

        # Phân trang
        pagination = filter_query.paginate(page=page, per_page=per_page, error_out=False)
        transactions = pagination.items

        # Đóng gói dữ liệu hiển thị chi tiết cho từng dòng giao dịch
        tx_items = []
        for tx in transactions:
            c = tx.contract
            net_amt = c.translator_net_amount or int((c.agreed_price or tx.amount or 0) * 0.9)
            fee_amt = c.platform_fee or int((c.agreed_price or tx.amount or 0) * 0.1)
            gross_amt = tx.amount or (c.agreed_price or 0)

            if tx.status == 'completed':
                status_label = 'Đã giải ngân'
                status_badge = 'bg-emerald-50 text-emerald-700 border-emerald-200'
                status_dot = 'bg-emerald-500'
                type_label = 'Giải ngân thù lao'
                type_badge = 'bg-emerald-100/70 text-emerald-800'
            elif tx.status == 'escrow_pending':
                status_label = 'Đang giữ Escrow'
                status_badge = 'bg-sky-50 text-sky-700 border-sky-200'
                status_dot = 'bg-sky-500'
                type_label = 'Ký quỹ bảo đảm'
                type_badge = 'bg-sky-100/70 text-sky-800'
            elif tx.status == 'refunded':
                status_label = 'Đã hoàn tiền'
                status_badge = 'bg-rose-50 text-rose-700 border-rose-200'
                status_dot = 'bg-rose-500'
                type_label = 'Hoàn trả hủy ca'
                type_badge = 'bg-rose-100/70 text-rose-800'
            else:
                status_label = 'Chờ xử lý'
                status_badge = 'bg-slate-100 text-slate-600 border-slate-200'
                status_dot = 'bg-slate-400'
                type_label = 'Giao dịch thanh toán'
                type_badge = 'bg-slate-100 text-slate-700'

            tx_items.append({
                'tx': tx,
                'contract': c,
                'net_amount': net_amt,
                'fee_amount': fee_amt,
                'gross_amount': gross_amt,
                'status_label': status_label,
                'status_badge': status_badge,
                'status_dot': status_dot,
                'type_label': type_label,
                'type_badge': type_badge
            })

        return render_template(
            'income_transactions.html',
            user=user,
            tx_items=tx_items,
            pagination=pagination,
            counts=counts,
            metrics=metrics,
            status_filter=status_filter,
            period_filter=period_filter,
            q=q,
            sort_by=sort_by,
            has_error=False
        )

    except Exception as e:
        flash('Có lỗi khi tải lịch sử giao dịch. Vui lòng thử lại sau.', 'error')
        return render_template(
            'income_transactions.html',
            user=user,
            tx_items=[],
            pagination=None,
            counts={'all': 0, 'completed': 0, 'escrow_pending': 0, 'refunded': 0},
            metrics={'total_paid_net': 0, 'total_escrow_held_gross': 0, 'total_refunded_gross': 0, 'total_transactions': 0},
            status_filter=status_filter,
            period_filter=period_filter,
            q=q,
            sort_by=sort_by,
            has_error=True
        )

@app.route('/interpreter/income/bank-info', methods=['GET', 'POST'])
@login_required
def interpreter_income_bank_info():
    user = get_current_user()
    if not user or user.role != 'translator':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('index'))

    from services.payout_methods import (
        get_payout_methods,
        get_supported_banks,
        get_user_payout_data,
        add_payout_method,
        set_default_payout_method,
        delete_payout_method
    )

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            bank_code = request.form.get('bank_code')
            account_number = request.form.get('account_number')
            account_holder_name = request.form.get('account_holder_name')
            branch = request.form.get('branch', '')
            set_as_default = bool(request.form.get('set_as_default'))

            success, msg_or_obj = add_payout_method(
                user_id=user.id,
                bank_code=bank_code,
                account_number=account_number,
                account_holder_name=account_holder_name,
                branch=branch,
                set_as_default=set_as_default
            )
            if success:
                flash(f"Đã thêm tài khoản ngân hàng {msg_or_obj.get('bank_short_name')} thành công.", "success")
            else:
                flash(msg_or_obj, "error")
            return redirect(url_for('interpreter_income_bank_info'))

        elif action == 'set_default':
            method_id = request.form.get('method_id')
            success, msg = set_default_payout_method(user.id, method_id)
            if success:
                flash(msg, "success")
            else:
                flash(msg, "error")
            return redirect(url_for('interpreter_income_bank_info'))

        elif action == 'delete':
            method_id = request.form.get('method_id')
            success, msg = delete_payout_method(user.id, method_id)
            if success:
                flash(msg, "success")
            else:
                flash(msg, "error")
            return redirect(url_for('interpreter_income_bank_info'))

        else:
            flash("Thao tác không hợp lệ.", "error")
            return redirect(url_for('interpreter_income_bank_info'))

    # Xử lý GET: Lấy danh sách phương thức, lịch sử và số hợp đồng đang chờ giải ngân
    user_payout_data = get_user_payout_data(user.id)
    methods = user_payout_data.get("methods", [])
    history = user_payout_data.get("history", [])
    supported_banks = get_supported_banks()

    pending_payout_count = Contract.query.filter(
        Contract.translator_id == user.id,
        Contract.status.in_(['in_progress', 'delivered'])
    ).count()

    return render_template(
        'income_bank_info.html',
        user=user,
        methods=methods,
        history=history,
        supported_banks=supported_banks,
        pending_payout_count=pending_payout_count,
        subpage_title="Thông tin nhận tiền",
        subpage_code="bank_info"
    )

@app.route('/my-team')
@login_required
def my_team():
    """Đội của tôi: các PDV khách hàng đã từng thuê (hợp đồng đã thanh toán), để tìm và book lại."""
    user = get_current_user()
    if not user or user.role != 'hirer':
        flash('Chỉ khách hàng mới có danh sách "Đội của tôi".', 'warning')
        return redirect(url_for('index'))
    contracts = (Contract.query
                 .filter(Contract.hirer_id == user.id,
                         Contract.status.in_(('in_progress', 'completed')))
                 .order_by(Contract.created_at.desc()).all())
    team = {}
    for c in contracts:  # mới nhất trước
        entry = team.setdefault(c.translator_id, {
            'user': c.translator, 'profile': c.translator.profile,
            'count': 0, 'spent': 0, 'last': c.created_at})
        entry['count'] += 1
        entry['spent'] += c.agreed_price
    members = sorted(team.values(), key=lambda m: m['last'] or datetime.min, reverse=True)
    members_json = []
    for m in members:
        p = m['profile']
        members_json.append({
            'name': m['user'].name,
            'avatar': m['user'].avatar_url,
            'title': p.title if p else '',
            'languages': p.languages if p else '',
            'bio': p.bio if p else '',
            'rating': p.rating or 0 if p else 0,
            'reviews': p.total_reviews or 0 if p else 0,
            'response': p.response_time if p else '',
            'count': m['count'],
            'spent': '{:,}'.format(m['spent']).replace(',', '.'),
            'last': m['last'].strftime('%d/%m/%Y') if m['last'] else '',
            'profile_url': url_for('translator_profile', profile_id=p.id) if p else '',
        })
    return render_template('my_team.html', members=members, members_json=members_json)


@app.route('/invoice/<int:contract_id>')
@login_required
def contract_invoice(contract_id):
    """Hóa đơn thuê PDV của một hợp đồng (bản in được / lưu PDF qua trình duyệt)."""
    contract = Contract.query.get_or_404(contract_id)
    from services.permissions import require_contract_access
    require_contract_access(session['user_id'], contract)
    if contract.status not in ('in_progress', 'completed'):
        flash('Hợp đồng chưa thanh toán nên chưa có hóa đơn.', 'warning')
        return redirect(url_for('account_history'))
    platform_fee = int(contract.agreed_price * 0.10)
    return render_template('invoice.html', contract=contract,
                           platform_fee=platform_fee,
                           translator_receives=contract.agreed_price - platform_fee)


# ─── FLOW 1: TÌM PHIÊN DỊCH VIÊN ──────────────────────────────────────────────

@app.route('/translator')
@app.route('/translators')
def translator_list():
    lang = request.args.get('lang', '')
    rating_filter = request.args.get('rating', '')
    demo_filter = request.args.get('demo', '')
    page = request.args.get('page', 1, type=int)
    per_page = 9

    query = TranslatorProfile.query.join(User).filter(
        User.is_active == True,
        db.or_(TranslatorProfile.is_public == True, TranslatorProfile.is_public.is_(None))
    )
    if demo_filter == 'hide':
        query = query.filter(TranslatorProfile.is_demo != True, TranslatorProfile.is_verified == True)
    elif demo_filter == 'only':
        query = query.filter(TranslatorProfile.is_demo == True)
    else:
        query = query.filter(db.or_(TranslatorProfile.is_verified == True, TranslatorProfile.is_demo == True))

    if lang:
        safe_lang = lang.replace('%', r'\%').replace('_', r'\_')
        query = query.filter(TranslatorProfile.languages.ilike(f'%{safe_lang}%'))
    if rating_filter:
        query = query.filter(TranslatorProfile.rating >= float(rating_filter))

    pagination = query.order_by(TranslatorProfile.rating.desc(), TranslatorProfile.id.asc()).paginate(page=page, per_page=per_page, error_out=False)
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


def _translator_card(p, favorite_ids=frozenset()):
    """Dữ liệu công khai của một hồ sơ phiên dịch viên (không có email/điện thoại)."""
    prices = [s.basic_price for s in p.services if s.basic_price]
    if not prices:
        if getattr(p, 'hourly_rate', None):
            prices.append(int(p.hourly_rate))
        if getattr(p, 'daily_rate', None):
            prices.append(int(p.daily_rate))
    if not prices and p.user and hasattr(p.user, 'interpreter_services'):
        for isvc in p.user.interpreter_services:
            if getattr(isvc, 'is_active', True):
                if getattr(isvc, 'hourly_rate', None):
                    prices.append(int(isvc.hourly_rate))
                if getattr(isvc, 'session_rate', None):
                    prices.append(int(isvc.session_rate))
    min_days = None
    for s in p.services:
        for field in (s.basic_delivery, s.standard_delivery, s.premium_delivery):
            nums = re.findall(r'\d+', field or '')
            if nums and (min_days is None or int(nums[0]) < min_days):
                min_days = int(nums[0])
    split = lambda v: [x.strip() for x in (v or '').split(',') if x.strip()]
    specialties = sorted({s.category.strip() for s in p.services if s.category and s.category.strip()})
    if not specialties:
        specialties = p.display_specializations
    pairs = sorted({s.languages.strip() for s in p.services if s.languages and s.languages.strip()})
    if not pairs:
        src = p.display_source_language
        tgt = p.display_target_language
        if src and tgt:
            pairs = [f"{src} - {tgt}"]
    name = p.user.name or ''
    city = (p.user.city if p.user and p.user.city else '') or getattr(p, 'service_areas', None) or 'Hà Nội'
    return {
        'id': p.id,
        'user_id': p.user_id,
        'name': name,
        'avatar_url': p.avatar_url,
        'initial': name[0].upper() if name else '?',
        'title': p.title or '',
        'bio': p.bio or (p.user.bio if p.user else '') or '',
        'languages': split(p.languages),
        'language_pairs': pairs,
        'specialties': specialties,
        'badges': split(p.badges),
        'experience_years': p.display_experience_years,
        'rating': float(p.rating or 0),
        'total_reviews': p.total_reviews or 0,
        'total_jobs': p.total_jobs or 0,
        'response_time': p.response_time or '',
        'min_price': min(prices) if prices else None,
        'max_price': max(prices) if prices else None,
        'completion_days': min_days,
        'is_verified': bool(p.is_verified),
        'is_demo': bool(getattr(p, 'is_demo', False)),
        'location': city,
        'country': getattr(p, 'country', 'Việt Nam'),
        'work_modes': p.display_work_modes,
        'employment_preference': getattr(p, 'employment_preference', 'Freelance'),
        'availability_status': getattr(p, 'availability_status', 'Sẵn sàng nhận việc'),
        'currency': getattr(p, 'currency', 'VND'),
        'hourly_rate': getattr(p, 'hourly_rate', None),
        'daily_rate': getattr(p, 'daily_rate', None),
        'is_favorite': p.user_id in favorite_ids,
        'profile_url': url_for('translator_profile', profile_id=p.id),
        'chat_url': url_for('direct_chat', translator_user_id=p.user_id),
    }


def _translator_listed(p):
    """Hồ sơ được phép hiển thị công khai: tài khoản hoạt động và không đặt chế độ riêng tư."""
    return bool(p.user and p.user.is_active and getattr(p, 'is_public', True) is not False)


def _favorites_hirer():
    user = get_current_user()
    if not user or user.role != 'hirer' or isinstance(user.id, str):
        return None
    return user


def _current_favorite_ids():
    """Tập translator user_id mà khách đang đăng nhập đã lưu (rỗng nếu không phải hirer)."""
    user = _favorites_hirer()
    if not user:
        return frozenset()
    return frozenset(r[0] for r in db.session.query(FavoriteTranslator.translator_id).filter_by(hirer_id=user.id).all())


@app.route('/api/translators')
def api_translators():
    """JSON API cho tìm kiếm/lọc phía client. Chỉ trả dữ liệu hồ sơ công khai của tài khoản đang hoạt động."""
    try:
        from sqlalchemy.orm import joinedload
        demo_filter = request.args.get('demo', '')
        query = TranslatorProfile.query.options(
            joinedload(TranslatorProfile.user), joinedload(TranslatorProfile.services)
        ).join(User).filter(
            User.is_active == True,
            db.or_(TranslatorProfile.is_public == True, TranslatorProfile.is_public.is_(None))
        )
        if demo_filter == 'hide':
            query = query.filter(TranslatorProfile.is_demo != True, TranslatorProfile.is_verified == True)
        elif demo_filter in ('only', 'demo'):
            query = query.filter(TranslatorProfile.is_demo == True)
        else:
            query = query.filter(db.or_(TranslatorProfile.is_verified == True, TranslatorProfile.is_demo == True))

        profiles = query.order_by(TranslatorProfile.rating.desc(), TranslatorProfile.id.asc()).all()
        fav = _current_favorite_ids()
        return jsonify([_translator_card(p, fav) for p in profiles if _translator_listed(p)])
    except Exception as e:
        import traceback
        print(f"Error in api_translators: {e}\n{traceback.format_exc()}", file=sys.stderr)
        db.session.rollback()
        return jsonify({'error': 'server_error'}), 500


def _api_csrf_ok():
    from admin_auth import validate_csrf_token
    return validate_csrf_token(request.headers.get('X-CSRF-Token'))


@app.route('/api/favorites', methods=['GET'])
@login_required
def api_favorites_list():
    user = _favorites_hirer()
    if not user:
        return jsonify({'error': 'forbidden'}), 403
    from sqlalchemy.orm import joinedload
    rows = (FavoriteTranslator.query.filter_by(hirer_id=user.id)
            .order_by(FavoriteTranslator.created_at.desc()).all())
    ids = [r.translator_id for r in rows]
    profiles = {}
    if ids:
        for p in TranslatorProfile.query.options(joinedload(TranslatorProfile.user), joinedload(TranslatorProfile.services)) \
                .filter(TranslatorProfile.user_id.in_(ids)).all():
            profiles[p.user_id] = p
    fav = frozenset(ids)
    items = [_translator_card(profiles[i], fav) for i in ids
             if i in profiles and _translator_listed(profiles[i])]
    return jsonify({'items': items})


@app.route('/api/favorites/<int:profile_id>', methods=['POST', 'DELETE'])
@login_required
def api_favorite_toggle(profile_id):
    user = _favorites_hirer()
    if not user:
        return jsonify({'error': 'forbidden'}), 403
    if not _api_csrf_ok():
        return jsonify({'error': 'csrf'}), 403
    profile = db.session.get(TranslatorProfile, profile_id)
    if not profile or not _translator_listed(profile):
        return jsonify({'error': 'not_found'}), 404
    existing = FavoriteTranslator.query.filter_by(hirer_id=user.id, translator_id=profile.user_id).first()
    try:
        if request.method == 'POST' and not existing:
            db.session.add(FavoriteTranslator(hirer_id=user.id, translator_id=profile.user_id))
            db.session.commit()
        elif request.method == 'DELETE' and existing:
            db.session.delete(existing)
            db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        # Race: bản ghi đã được thêm bởi request song song — coi như thành công
        if request.method == 'POST' and FavoriteTranslator.query.filter_by(hirer_id=user.id, translator_id=profile.user_id).first():
            return jsonify({'is_favorite': True})
        return jsonify({'error': 'server_error'}), 500
    return jsonify({'is_favorite': request.method == 'POST'})


@app.route('/api/my-open-jobs')
@login_required
def api_my_open_jobs():
    user = _favorites_hirer()
    if not user:
        return jsonify({'error': 'forbidden'}), 403
    jobs = Job.query.filter_by(hirer_id=user.id, status='open').order_by(Job.created_at.desc()).limit(50).all()
    return jsonify({'items': [{'id': j.id, 'title': j.title} for j in jobs]})


@app.route('/saved-translators')
@login_required
def saved_translators():
    user = _favorites_hirer()
    if not user:
        flash(_t('flash.hirer_only_post'), 'error')
        return redirect(url_for('index'))
    return render_template('saved_translators.html')


@app.route('/translator/<int:profile_id>')
def translator_profile(profile_id):
    """
    Trang hồ sơ nghề nghiệp chuyên sâu của phiên dịch viên.
    Kiểm tra quyền xem nghiêm ngặt:
    - Hồ sơ công khai & tài khoản hoạt động: khách vãng lai và mọi người xem được.
    - Hồ sơ riêng tư / chưa đủ điều kiện công khai:
      + Chính chủ hoặc Admin: Xem ở chế độ Xem trước (Preview Mode) kèm hướng dẫn hoàn thiện.
      + Khách ngoài: Không công khai ngoài ý muốn, hiển thị trang thông báo riêng tư.
    - Hồ sơ bị hạn chế / khóa: Từ chối truy cập (403) kèm thông báo an toàn.
    """
    profile = TranslatorProfile.query.get_or_404(profile_id)
    
    viewer_id = session.get('user_id')
    viewer = User.query.get(viewer_id) if viewer_id else None
    admin_id = session.get('admin_id')
    is_owner = bool(viewer and viewer.id == profile.user_id)
    is_admin = bool((viewer and getattr(viewer, 'is_admin', False)) or admin_id)

    can_view, is_preview_mode, access_reason = profile.can_view_public(viewer=viewer, is_admin_session=bool(admin_id))

    if not can_view:
        is_restricted = bool(profile.user and not getattr(profile.user, 'is_active', True))
        status_code = 403 if is_restricted else 200
        return render_template(
            'translator_profile_restricted.html',
            profile=profile,
            is_restricted=is_restricted,
            is_private=(getattr(profile, 'is_public', True) is False),
            access_reason=access_reason
        ), status_code
    # Reviews received by this translator (lọc bỏ các đánh giá đã bị Admin ẩn)
    reviews = Review.query.filter_by(reviewee_id=profile.user_id, is_hidden=False).order_by(Review.created_at.desc()).limit(10).all()
    verification = profile.latest_verification
    is_verified = bool(profile.is_verified)

    return render_template(
        'translator_profile.html',
        profile=profile,
        reviews=reviews,
        is_owner=is_owner,
        is_admin=is_admin,
        is_preview_mode=is_preview_mode,
        access_reason=access_reason,
        is_verified=is_verified,
        verification=verification
    )

@app.route('/translator/<int:profile_id>/cv')
def view_public_cv(profile_id):
    """
    Endpoint xem / tải CV chuyên môn công khai của phiên dịch viên.
    Chỉ cho phép khi:
    - Hồ sơ có bật cờ is_cv_public = True, HOẶC
    - Người xem là chính chủ hồ sơ hoặc Quản trị viên (Admin), HOẶC
    - Người xem là Người thuê (Hirer) mà phiên dịch viên đã nộp báo giá vào công việc của họ hoặc có Hợp đồng.
    Bảo mật nghiêm ngặt:
    - Chỉ phục vụ tài liệu loại 'cv'.
    - TUYỆT ĐỐI KHÔNG BAO GIỜ phục vụ 'id_card', hộ chiếu hoặc tài liệu định danh riêng tư.
    """
    profile = TranslatorProfile.query.get_or_404(profile_id)
    viewer_id = session.get('user_id')
    viewer = User.query.get(viewer_id) if viewer_id else None
    admin_id = session.get('admin_id')
    is_owner = bool(viewer and viewer.id == profile.user_id)
    is_admin = bool((viewer and getattr(viewer, 'is_admin', False)) or admin_id)

    if profile.user and not getattr(profile.user, 'is_active', True) and not is_admin:
        abort(403)

    # Kiểm tra xem người xem có phải là người thuê có quan hệ công việc với phiên dịch viên này không
    is_hirer_with_relation = False
    if viewer and viewer.role == 'hirer':
        has_prop = Proposal.query.join(Job).filter(
            Proposal.translator_id == profile.user_id,
            Job.hirer_id == viewer.id
        ).first()
        if has_prop:
            is_hirer_with_relation = True
        else:
            has_contract = Contract.query.filter_by(
                hirer_id=viewer.id,
                translator_id=profile.user_id
            ).first()
            if has_contract:
                is_hirer_with_relation = True

    can_view = bool(profile.is_cv_public or is_owner or is_admin or is_hirer_with_relation)
    if not can_view:
        flash('Phiên dịch viên chưa thiết lập công khai tài liệu CV.', 'warning')
        return redirect(url_for('translator_profile', profile_id=profile.id))

    cv_doc = profile.active_cv_document if (is_owner or is_admin or is_hirer_with_relation) else profile.public_cv_document

    # Nếu chưa tìm thấy qua active_cv_document, kiểm tra thêm trong các verifications
    if not cv_doc and profile.user:
        for v in (profile.user.verifications or []):
            if hasattr(v, 'documents'):
                for d in v.documents:
                    if d.document_type == 'cv' and getattr(d, 'is_active', True):
                        cv_doc = d
                        break
            if cv_doc:
                break

    if not cv_doc:
        flash('Chưa có tệp CV nào được tải lên cho hồ sơ này.', 'info')
        return redirect(url_for('translator_profile', profile_id=profile.id))

    if cv_doc.document_type != 'cv':
        abort(403)

    from services.verification import resolve_document_file_path
    ftype, target = resolve_document_file_path(cv_doc)

    if ftype == 'url':
        return redirect(target)
    elif ftype == 'file' and target:
        file_path = target
    else:
        # Kiểm tra thêm nếu có cv_url trực tiếp trên verification
        verif = profile.latest_verification
        if verif and verif.cv_url and verif.cv_url.startswith(('http://', 'https://')):
            return redirect(verif.cv_url)
        abort(404)

    mode = request.args.get('mode', 'view')
    as_attachment = (mode == 'download')

    response = send_file(
        file_path,
        as_attachment=as_attachment,
        download_name=cv_doc.original_filename or 'CV_ChuyenNghiep.pdf',
        mimetype=cv_doc.mime_type or 'application/pdf'
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'none'"
    response.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    return response

@app.route('/hirer/<int:hirer_id>')
def hirer_profile(hirer_id):
    user = User.query.get_or_404(hirer_id)
    if user.role != 'hirer':
        abort(404)
        
    profile = user.hirer_profile
    
    from services.permissions import can_view_profile
    if profile and not can_view_profile(profile, get_current_user()):
        abort(404)
    
    from services.hirer import get_hirer_stats
    stats = get_hirer_stats(hirer_id)
    reviews = Review.query.filter_by(reviewee_id=hirer_id, is_hidden=False).order_by(Review.created_at.desc()).limit(10).all()

    is_verified = bool(profile and profile.is_verified)
    viewer = get_current_user()
    is_owner = bool(viewer and getattr(viewer, 'id', None) == user.id)
    return render_template('hirer_profile.html', user=user, profile=profile, reviews=reviews, stats=stats,
                           total_jobs=stats['total_jobs'], completed_contracts=stats['completed_contracts'],
                           is_verified=is_verified, is_owner=is_owner)

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
        'id': m.id, 'sender_id': m.sender_id, 'sender_name': m.sender.name if m.sender else '',
        'content': m.content, 'image_url': getattr(m, 'image_url', None),
        'time': m.created_at.strftime('%H:%M %d/%m') if m.created_at else ''
    } for m in msgs])

@app.route('/api/direct-messages/<int:other_user_id>', methods=['POST'])
@login_required
def send_direct_message(other_user_id):
    me = session['user_id']
    data = request.get_json(silent=True) or {}
    content = str(data.get('content') or '').strip()
    image_url = str(data.get('image_url') or '').strip()
    ok_msg, err = _validate_chat_payload(content, image_url, me)
    if not ok_msg:
        return jsonify({'status': 'error', 'message': err}), 400
    if other_user_id == me:
        return jsonify({'status': 'error', 'message': 'Không thể nhắn cho chính mình.'}), 400
    receiver = db.session.get(User, other_user_id)
    if not receiver or not receiver.is_active:
        return jsonify({'status': 'error', 'message': 'Người nhận không tồn tại hoặc đã bị khóa.'}), 404

    # sender luôn lấy từ phiên đăng nhập; không nhận sender_id từ client
    msg = DirectMessage(sender_id=me, receiver_id=other_user_id,
                        content=content or '[Hình ảnh]', image_url=image_url or None)
    db.session.add(msg)
    sender = db.session.get(User, me)
    if sender:
        from services.notifications import should_notify
        if should_notify(receiver, 'NEW_MESSAGE'):
            try:
                create_notification(
                    user_id=other_user_id, notification_type='NEW_MESSAGE', title='Bạn có tin nhắn mới',
                    message=f'{sender.name} đã gửi cho bạn một tin nhắn.',
                    url=url_for('messages_page', c=f'd:{me}'))
            except Exception as e:
                print(f"Error creating notification: {e}")
    db.session.commit()
    return jsonify({'status': 'ok', 'id': msg.id})


CHAT_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
CHAT_IMAGE_MAX_BYTES = 5 * 1024 * 1024
CHAT_TEXT_MAX = 2000
CHAT_IMAGE_FOLDER = os.getenv('CHAT_IMAGE_FOLDER') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'chat_images')
if os.environ.get('VERCEL') == '1' or _is_memory_db:
    CHAT_IMAGE_FOLDER = '/tmp/chat_images'
try:
    os.makedirs(CHAT_IMAGE_FOLDER, exist_ok=True)
except OSError as e:
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError(f"[CRITICAL] Failed to create CHAT_IMAGE_FOLDER at {CHAT_IMAGE_FOLDER}: {e}")
    CHAT_IMAGE_FOLDER = '/tmp/chat_images'
    os.makedirs(CHAT_IMAGE_FOLDER, exist_ok=True)
_CHAT_IMG_URL = re.compile(r'^/chat-image/(\d+)_[0-9a-f]{32}\.(png|jpg|jpeg|gif|webp)$')
_CHAT_IMG_LEGACY = re.compile(r'^/static/uploads/chat_images/[\w.\-]+$')
_CHAT_IMG_DATA = re.compile(r'^data:image/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+$')
_IMG_MAGIC = {'png': (b'\x89PNG',), 'jpg': (b'\xff\xd8',), 'jpeg': (b'\xff\xd8',), 'gif': (b'GIF8',), 'webp': (b'RIFF',)}


def allowed_chat_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in CHAT_IMAGE_EXTENSIONS


def _validate_chat_payload(content, image_url, me):
    """Kiểm tra nội dung/ảnh tin nhắn. Ảnh phải là ảnh do chính người gửi tải lên (hoặc dữ liệu cũ hợp lệ)."""
    if not content and not image_url:
        return False, 'Tin nhắn trống.'
    if len(content) > CHAT_TEXT_MAX:
        return False, f'Tin nhắn quá dài (tối đa {CHAT_TEXT_MAX} ký tự).'
    if image_url:
        m = _CHAT_IMG_URL.match(image_url)
        if m:
            if int(m.group(1)) != me:
                return False, 'Ảnh không hợp lệ.'
        elif _CHAT_IMG_LEGACY.match(image_url):
            pass
        elif _CHAT_IMG_DATA.match(image_url) and len(image_url) <= int(CHAT_IMAGE_MAX_BYTES * 1.4):
            pass
        else:
            return False, 'Ảnh không hợp lệ.'
    return True, ''


@app.route('/api/chat/upload-image', methods=['POST'])
@login_required
def upload_chat_image():
    """Tải ảnh cho chat. Kiểm tra loại + nội dung + dung lượng; lưu riêng tư, tên ngẫu nhiên."""
    me = session['user_id']
    if isinstance(me, str):
        return jsonify({'status': 'error', 'message': 'Tài khoản không hỗ trợ tải ảnh.'}), 403
    file = request.files.get('image')
    if not file or file.filename == '':
        return jsonify({'status': 'error', 'message': 'Chưa chọn tệp.'}), 400
    if not allowed_chat_image(file.filename):
        return jsonify({'status': 'error', 'message': 'Chỉ hỗ trợ ảnh PNG, JPG, GIF, WEBP.'}), 400
    ext = file.filename.rsplit('.', 1)[1].lower()
    data = file.read(CHAT_IMAGE_MAX_BYTES + 1)
    if not data:
        return jsonify({'status': 'error', 'message': 'Tệp rỗng.'}), 400
    if len(data) > CHAT_IMAGE_MAX_BYTES:
        return jsonify({'status': 'error', 'message': 'Ảnh vượt quá 5MB.'}), 400
    if not data.startswith(_IMG_MAGIC[ext]):
        return jsonify({'status': 'error', 'message': 'Nội dung tệp không phải ảnh hợp lệ.'}), 400

    if os.environ.get('VERCEL') == '1' or app.config.get('UPLOAD_FOLDER') == '/tmp':
        import base64
        mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}[ext]
        return jsonify({'status': 'ok', 'image_url': f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"})

    name = f'{me}_{_uuid.uuid4().hex}.{ext}'
    with open(os.path.join(CHAT_IMAGE_FOLDER, name), 'wb') as f:
        f.write(data)
    return jsonify({'status': 'ok', 'image_url': f'/chat-image/{name}'})


@app.route('/chat-image/<name>')
@login_required
def serve_private_chat_image(name):
    """Ảnh chat riêng tư: chỉ người tải lên hoặc thành viên của hội thoại có ảnh đó mới xem được."""
    m = re.match(r'^(\d+)_[0-9a-f]{32}\.(png|jpg|jpeg|gif|webp)$', name)
    me = session['user_id']
    if not m or isinstance(me, str):
        abort(404)
    url = f'/chat-image/{name}'
    allowed = int(m.group(1)) == me
    if not allowed:
        allowed = DirectMessage.query.filter(
            DirectMessage.image_url == url,
            db.or_(DirectMessage.sender_id == me, DirectMessage.receiver_id == me)).first() is not None
    if not allowed:
        cids = [c.id for c in Contract.query.filter(db.or_(Contract.hirer_id == me, Contract.translator_id == me)).all()]
        allowed = bool(cids) and Message.query.filter(Message.image_url == url, Message.contract_id.in_(cids)).first() is not None
    path = os.path.join(CHAT_IMAGE_FOLDER, name)
    if not allowed or not os.path.exists(path):
        abort(404)
    resp = send_from_directory(CHAT_IMAGE_FOLDER, name)
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Cache-Control'] = 'private, max-age=3600'
    return resp


@app.route('/static/uploads/chat_images/<path:filename>')
def serve_chat_image(filename):
    """Phục vụ file ảnh chat trực tiếp để tránh lỗi 404."""
    chat_img_dir = os.path.join(basedir, 'static', 'uploads', 'chat_images')
    if os.path.exists(os.path.join(chat_img_dir, filename)):
        return send_from_directory(chat_img_dir, filename)
    if os.path.exists(os.path.join('/tmp', filename)):
        return send_from_directory('/tmp', filename)
    abort(404)


@app.route('/static/uploads/avatars/<path:filename>')
@app.route('/uploads/avatars/<path:filename>')
def serve_avatar_image(filename):
    """Phục vụ file ảnh đại diện (avatar) trực tiếp từ mọi thư mục lưu trữ khả dĩ."""
    filename = secure_filename(filename) if filename else ''
    if not filename:
        abort(404)

    candidate_folders = []
    # 1. AVATAR_UPLOAD_FOLDER cấu hình (e.g. /var/lib/viettranslate/uploads/avatars trên VPS)
    avatar_dir = app.config.get('AVATAR_UPLOAD_FOLDER')
    if avatar_dir:
        candidate_folders.append(avatar_dir)

    # 2. UPLOAD_FOLDER/avatars
    upload_dir = app.config.get('UPLOAD_FOLDER')
    if upload_dir:
        candidate_folders.append(os.path.join(upload_dir, 'avatars'))
        candidate_folders.append(upload_dir)

    # 3. static/uploads/avatars trong root_path và basedir
    candidate_folders.append(os.path.join(app.root_path, 'static', 'uploads', 'avatars'))
    candidate_folders.append(os.path.join(basedir, 'static', 'uploads', 'avatars'))

    # 4. Thư mục persistent cố định trên VPS
    candidate_folders.append('/var/lib/viettranslate/uploads/avatars')
    candidate_folders.append('/var/lib/viettranslate/uploads')

    # 5. Thư mục tạm
    candidate_folders.append('/tmp/avatars')
    candidate_folders.append('/tmp')

    for folder in candidate_folders:
        if folder and os.path.isdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                resp = send_from_directory(folder, filename)
                resp.headers['Cache-Control'] = 'public, max-age=86400'
                return resp

    abort(404)




# ─── MESSAGES PAGE ─────────────────────────────────────────────────────────────

@app.route('/messages')
@login_required
def messages_page():
    return render_template('messages.html')

@app.route('/api/messages/conversations')
@login_required
def api_conversations():
    """Danh sách hội thoại của người dùng: tin nhắn riêng (theo người) + tin nhắn dự án (theo hợp đồng).

    Mỗi hội thoại là một mục riêng để tổng số chưa đọc luôn khớp với badge trên header.
    Hỗ trợ ?q= để tìm theo tên, dự án hoặc nội dung tin nhắn cuối.
    """
    me = session['user_id']
    if isinstance(me, str):
        return jsonify([])
    q = (request.args.get('q') or '').strip().lower()
    items = []

    def fmt(dt):
        return dt.strftime('%H:%M %d/%m') if dt else ''

    # ── 1. Tin nhắn riêng ──
    dms = (DirectMessage.query.filter(db.or_(DirectMessage.sender_id == me, DirectMessage.receiver_id == me))
           .order_by(DirectMessage.created_at.desc(), DirectMessage.id.desc()).all())
    last_dm, unread_dm = {}, {}
    for dm in dms:
        other = dm.receiver_id if dm.sender_id == me else dm.sender_id
        last_dm.setdefault(other, dm)
        if dm.receiver_id == me and not dm.is_read:
            unread_dm[other] = unread_dm.get(other, 0) + 1
    users = {u.id: u for u in User.query.filter(User.id.in_(list(last_dm))).all()} if last_dm else {}
    for other, dm in last_dm.items():
        u = users.get(other)
        if not u:
            continue
        items.append({'key': f'd:{other}', 'type': 'direct', 'other_user_id': other, 'other_name': u.name,
                      'other_initial': (u.name[:1] or '?').upper(), 'project': '',
                      'last_message': dm.content or '', 'last_time': dm.created_at, 'last_time_str': fmt(dm.created_at),
                      'unread_count': unread_dm.get(other, 0), 'url': url_for('direct_chat', translator_user_id=other)})

    # ── 2. Tin nhắn theo dự án (hợp đồng) ──
    contracts = Contract.query.filter(db.or_(Contract.hirer_id == me, Contract.translator_id == me)).all()
    cmap = {c.id: c for c in contracts}
    if cmap:
        last_ids = dict(db.session.query(Message.contract_id, db.func.max(Message.id))
                        .filter(Message.contract_id.in_(list(cmap))).group_by(Message.contract_id).all())
        unread_c = dict(db.session.query(Message.contract_id, db.func.count(Message.id))
                        .filter(Message.contract_id.in_(list(cmap)), Message.sender_id != me, Message.is_read == False)
                        .group_by(Message.contract_id).all())
        last_msgs = {m.id: m for m in Message.query.filter(Message.id.in_(list(last_ids.values()))).all()} if last_ids else {}
        from services.projects import project_title
        for cid, mid in last_ids.items():
            c, m = cmap[cid], last_msgs.get(mid)
            other = c.translator_id if c.hirer_id == me else c.hirer_id
            u = db.session.get(User, other)
            if not u or not m:
                continue
            url = url_for('project_detail', contract_id=cid) if c.hirer_id == me else url_for('transaction_detail', contract_id=cid)
            items.append({'key': f'c:{cid}', 'type': 'contract', 'other_user_id': other, 'other_name': u.name,
                          'other_initial': (u.name[:1] or '?').upper(), 'project': project_title(c), 'contract_id': cid,
                          'last_message': m.content or '', 'last_time': m.created_at, 'last_time_str': fmt(m.created_at),
                          'unread_count': unread_c.get(cid, 0), 'url': url})

    if q:
        items = [i for i in items if q in (i['other_name'] or '').lower() or q in (i['project'] or '').lower()
                 or q in (i['last_message'] or '').lower()]
    items.sort(key=lambda x: x['last_time'] or datetime.min, reverse=True)
    for i in items:
        i['updated_at'] = i['last_time'].isoformat() if i['last_time'] else None
        del i['last_time']
    return jsonify(items)

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
            if contract.status == 'awaiting_translator':
                return redirect(url_for('transaction_detail', contract_id=contract.id))
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


@app.route('/book-interpreter/<int:interpreter_service_id>', methods=['GET', 'POST'])
@login_required
def book_interpreter(interpreter_service_id):
    isvc = InterpreterService.query.get_or_404(interpreter_service_id)
    rate_type = request.args.get('rate_type', 'hourly')
    
    if rate_type == 'session' and isvc.session_rate:
        price = int(isvc.session_rate)
        rate_label = 'Theo ca / buổi'
    else:
        rate_type = 'hourly'
        price = int(isvc.hourly_rate or isvc.session_rate or 0)
        rate_label = 'Theo giờ'

    current_user = get_current_user()
    if not current_user:
        flash(_t('flash.login_required'), 'warning')
        return redirect(url_for('login'))
        
    translator = isvc.user
    if not translator or getattr(translator, 'role', '') != 'translator' or not getattr(translator, 'is_active', True):
        flash(_t('flash.translator_inactive'), 'error')
        return redirect(url_for('translators'))

    if current_user.id == translator.id:
        flash(_t('flash.cannot_hire_self'), 'error')
        profile = getattr(translator, 'translator_profile', None)
        if profile:
            return redirect(url_for('translator_profile', profile_id=profile.id))
        return redirect(url_for('translators'))

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
                interpreter_service_id=isvc.id
            )
            flash(_t('flash.service_booked'), 'success')
            if contract.status == 'awaiting_translator':
                return redirect(url_for('transaction_detail', contract_id=contract.id))
            return redirect(url_for('payment_mockup', contract_id=contract.id))
            
        except (BookingConflictError, BookingValidationError, ScheduleCheckError) as e:
            flash(str(e), 'error')
            return redirect(url_for('book_interpreter', interpreter_service_id=isvc.id, rate_type=rate_type))
            
        except Exception as e:
            import logging
            logging.exception('Error in book_interpreter: %s', e)
            flash(_t('flash.system_error'), 'error')
            return redirect(url_for('book_interpreter', interpreter_service_id=isvc.id, rate_type=rate_type))

    profile = getattr(translator, 'translator_profile', None)
    return render_template(
        'book_interpreter.html',
        isvc=isvc,
        translator=translator,
        profile=profile,
        rate_type=rate_type,
        rate_label=rate_label,
        price=price
    )


# ─── FLOW 2: JOB BOARD ─────────────────────────────────────────────────────────

# ─── CLIENT REQUEST MANAGEMENT (Task 02) ───────────────────────────────────────

import uuid as _uuid
from flask import send_from_directory

JOB_FILES_FOLDER = os.getenv('JOB_FILES_FOLDER') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'job_files')
if os.environ.get('VERCEL') == '1' or _is_memory_db:
    JOB_FILES_FOLDER = '/tmp/job_files'
try:
    os.makedirs(JOB_FILES_FOLDER, exist_ok=True)
except OSError as e:
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError(f"[CRITICAL] Failed to create JOB_FILES_FOLDER at {JOB_FILES_FOLDER}: {e}")
    JOB_FILES_FOLDER = '/tmp/job_files'
    os.makedirs(JOB_FILES_FOLDER, exist_ok=True)

DELIVERABLE_FOLDER = os.getenv('DELIVERABLE_FOLDER') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'deliverables')
if os.environ.get('VERCEL') == '1' or _is_memory_db:
    DELIVERABLE_FOLDER = '/tmp/deliverables'
try:
    os.makedirs(DELIVERABLE_FOLDER, exist_ok=True)
except OSError as e:
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError(f"[CRITICAL] Failed to create DELIVERABLE_FOLDER at {DELIVERABLE_FOLDER}: {e}")
    DELIVERABLE_FOLDER = '/tmp/deliverables'
    os.makedirs(DELIVERABLE_FOLDER, exist_ok=True)

JOB_FILE_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'png', 'jpg', 'jpeg', 'zip'}
JOB_FILE_MAX_BYTES = 10 * 1024 * 1024
JOB_FILE_MAX_COUNT = 5
JOB_LANGS = ['Tiếng Việt', 'Tiếng Anh', 'Tiếng Nhật', 'Tiếng Hàn', 'Tiếng Trung', 'Tiếng Pháp', 'Tiếng Đức',
             'Tiếng Nga', 'Tiếng Thái', 'Tiếng Bồ Đào Nha', 'Tiếng Tây Ban Nha']
JOB_SERVICE_TYPES = {
    'translation': {'document_translation': 'Dịch tài liệu', 'website_translation': 'Dịch website',
                    'subtitle': 'Dịch phụ đề', 'proofreading': 'Hiệu đính', 'localization': 'Bản địa hóa',
                    'other_translation': 'Dịch thuật khác'},
    'interpretation_other': {'conference': 'Phiên dịch hội nghị / Cabin', 'meeting': 'Phiên dịch họp / Đàm phán',
                             'business': 'Phiên dịch kinh doanh / Thương mại', 'travel': 'Phiên dịch du lịch',
                             'escort': 'Phiên dịch tháp tùng', 'event': 'Phiên dịch sự kiện',
                             'other_interpretation': 'Dịch vụ khác'},
}
JOB_SPECIALTIES = ['Pháp lý', 'Y tế', 'Kỹ thuật', 'Tài chính - Kế toán', 'Kinh doanh', 'Công nghệ thông tin',
                   'Giáo dục', 'Du lịch', 'Marketing', 'Chung / Khác']
JOB_LOCKED_FIELDS = ('source_lang', 'target_lang', 'category_group', 'service_type', 'budget_type', 'budget_min', 'budget_max')


def _csrf_ok():
    from admin_auth import validate_csrf_token
    return validate_csrf_token(request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token'))


def _require_hirer():
    user = get_current_user()
    if not user or user.role != 'hirer' or isinstance(user.id, str):
        return None
    return user


def _owned_job_or_404(user, job_id):
    """Chỉ trả về job thuộc user; job của người khác trả 404 để không lộ sự tồn tại."""
    job = Job.query.get_or_404(job_id)
    if job.hirer_id != user.id:
        abort(404)
    return job


def job_edit_policy(job, proposal_count=None):
    """Quy tắc nghiệp vụ: ai được sửa/đóng/hủy và trường nào bị khóa."""
    n = Proposal.query.filter_by(job_id=job.id).count() if proposal_count is None else proposal_count
    is_open = job.status == 'open'
    return {
        'proposal_count': n,
        'can_edit': job.status in ('open', 'pending'),   # pending: chờ duyệt / cần chỉnh sửa / bị từ chối
        'can_close': is_open,
        'can_cancel': job.status in ('open', 'closed', 'pending'),
        'locked': is_open and n > 0,   # đã có báo giá → khóa ngôn ngữ, loại dịch vụ, ngân sách
    }


MODERATION_LABELS = {'pending': 'Chờ duyệt', 'needs_revision': 'Cần chỉnh sửa', 'rejected': 'Bị từ chối',
                     'flagged': 'Bị gắn cờ'}


def job_status_label(job):
    """Nhãn trạng thái hiển thị cho khách: job chờ duyệt thì hiện theo kết quả kiểm duyệt."""
    if job.status == 'pending':
        return MODERATION_LABELS.get(job.moderation_status or 'pending', 'Chờ duyệt')
    return JOB_STATUS_LABELS.get(job.status, job.status or '')


def _schedule_entries_from_form(form):
    ds, ss, es = form.getlist('scheduled_date[]'), form.getlist('start_time[]'), form.getlist('end_time[]')
    return [{'scheduled_date': d.strip(), 'start_time': s.strip(), 'end_time': e.strip()}
            for d, s, e in zip(ds, ss, es) if d.strip() or s.strip() or e.strip()]


def _schedule_rows_for_job(job):
    from models import get_job_schedule_entries
    try:
        return [{'scheduled_date': e['scheduled_date'], 'start_time': e['start_time'], 'end_time': e['end_time']}
                for e in get_job_schedule_entries(job)]
    except Exception:
        return []


def _save_job_schedule(job, entries):
    from models import JobSchedule
    for old in list(job.schedules):
        db.session.delete(old)
    for e in entries:
        db.session.add(JobSchedule(job_id=job.id,
                                   scheduled_date=datetime.strptime(e['scheduled_date'], '%Y-%m-%d').date(),
                                   start_time=e['start_time'][:5], end_time=e['end_time'][:5]))


def _submit_for_moderation(job, user, is_new):
    """Đưa job vào hàng chờ duyệt (giống quy trình đăng job của hệ thống)."""
    import json
    from services.job_moderation import evaluate_job_39_criteria
    job.status = 'pending'
    job.moderation_status = 'pending'
    job.submission_version = 1 if is_new else (job.submission_version or 1) + 1
    summary_label = 'Chờ kiểm duyệt'
    try:
        result = evaluate_job_39_criteria(job)
        job.moderation_checklist_data = json.dumps(result)
        summary_label = result.get('summary_label', 'Chờ kiểm duyệt')
    except Exception as e:
        app.logger.warning(f"Error evaluating 39 criteria for job {job.id}: {e}")
        job.moderation_checklist_data = json.dumps({'summary_label': 'Chờ kiểm duyệt', 'error': str(e)})

    try:
        from models import AdminNotification
        db.session.add(AdminNotification(
            type='NEW_JOB',
            title=(f'Job mới chờ duyệt: #{job.id}' if is_new else f'Job cập nhật chờ duyệt lại: #{job.id}'),
            message=f'{user.name} vừa {"nộp" if is_new else "cập nhật"} job "{job.title}". Kết quả: {summary_label}',
            related_id=job.id, url=url_for('admin_job_review', job_id=job.id)))
    except Exception as e:
        app.logger.warning(f"Failed to create AdminNotification for job {job.id}: {e}")


def _int_or_none(v):
    v = (str(v) if v is not None else '').strip().replace(',', '')
    return int(v) if v.isdigit() else None


def validate_job_form(form, existing=None, locked=False):
    """Validate phía server. Trả về (data, errors)."""
    errors, d = {}, {}
    g = lambda k: (form.get(k) or '').strip()

    d['title'] = g('title')
    if not (5 <= len(d['title']) <= 200):
        errors['title'] = 'Tên yêu cầu phải từ 5 đến 200 ký tự.'
    d['description'] = g('description')
    if not (20 <= len(d['description']) <= 5000):
        errors['description'] = 'Mô tả phải từ 20 đến 5000 ký tự.'
    d['specialty'] = g('specialty')
    if d['specialty'] and d['specialty'] not in JOB_SPECIALTIES:
        errors['specialty'] = 'Lĩnh vực không hợp lệ.'
    d['extra_requirements'] = g('extra_requirements')
    if len(d['extra_requirements']) > 2000:
        errors['extra_requirements'] = 'Yêu cầu bổ sung tối đa 2000 ký tự.'

    if locked:
        for f in JOB_LOCKED_FIELDS:
            d[f] = getattr(existing, f)
        group = existing.display_category_group
        d['category_group'] = group
        d['service_type'] = existing.display_service_type
        d.pop('category', None)
    else:
        group, stype = g('category_group'), g('service_type')
        if group not in JOB_SERVICE_TYPES:
            errors['category_group'] = 'Vui lòng chọn dịch tài liệu hoặc phiên dịch.'
        elif stype not in JOB_SERVICE_TYPES[group]:
            errors['service_type'] = 'Loại dịch vụ không hợp lệ.'
        d['category_group'], d['service_type'] = group, stype
        d['category'] = JOB_SERVICE_TYPES.get(group, {}).get(stype, '')
        d['source_lang'], d['target_lang'] = g('source_lang'), g('target_lang')
        if d['source_lang'] not in JOB_LANGS or d['target_lang'] not in JOB_LANGS:
            errors['source_lang'] = 'Vui lòng chọn ngôn ngữ nguồn và đích.'
        elif d['source_lang'] == d['target_lang']:
            errors['target_lang'] = 'Ngôn ngữ đích phải khác ngôn ngữ nguồn.'
        bt = g('budget_type') or 'negotiable'
        d['budget_type'] = bt
        bmin, bmax = _int_or_none(form.get('budget_min')), _int_or_none(form.get('budget_max'))
        if bt == 'fixed':
            if not bmin or bmin <= 0:
                errors['budget_min'] = 'Nhập ngân sách lớn hơn 0.'
            bmax = None
        elif bt == 'range':
            if not bmin or not bmax or bmin <= 0 or bmax < bmin:
                errors['budget_max'] = 'Nhập khoảng ngân sách hợp lệ (tối đa ≥ tối thiểu > 0).'
        elif bt == 'negotiable':
            bmin, bmax = 0, None
        else:
            errors['budget_type'] = 'Loại ngân sách không hợp lệ.'
        if (bmin and bmin > 10**10) or (bmax and bmax > 10**10):
            errors['budget_min'] = 'Ngân sách quá lớn.'
        d['budget_min'], d['budget_max'] = bmin or 0, bmax

    is_translation = group == 'translation'
    wc = g('word_count')
    d['word_count'] = None
    if wc:
        n = _int_or_none(wc)
        if not n or n <= 0 or n > 10_000_000:
            errors['word_count'] = 'Khối lượng phải là số nguyên dương.'
        d['word_count'] = n

    dl = g('deadline')
    d['deadline'] = None
    if dl:
        try:
            parsed = datetime.strptime(dl, '%Y-%m-%d').date()
            unchanged = existing is not None and existing.deadline == parsed
            if parsed < date.today() and not unchanged:
                errors['deadline'] = 'Deadline không được ở quá khứ.'
            elif parsed > date.today() + timedelta(days=730):
                errors['deadline'] = 'Deadline quá xa (tối đa 2 năm).'
            d['deadline'] = parsed
        except ValueError:
            errors['deadline'] = 'Deadline không hợp lệ.'

    d['event_location'] = g('event_location')[:200]
    d['_entries'] = []
    if not is_translation:
        from models import validate_schedule_entries
        entries = _schedule_entries_from_form(form)
        ok_s, s_errs = validate_schedule_entries(entries)
        if not ok_s:
            errors['schedule'] = ' '.join(e['message'] for e in s_errs)
        else:
            d['_entries'] = entries
        first = entries[0] if entries else {}
        d['event_date'] = first.get('scheduled_date', '')
        d['event_time_start'] = first.get('start_time', '')[:5]
        d['event_time_end'] = first.get('end_time', '')[:5]
        if not d['event_location']:
            errors['event_location'] = 'Vui lòng nhập địa điểm (hoặc "Trực tuyến").'
    else:
        d['event_date'] = d['event_time_start'] = d['event_time_end'] = d['event_location'] = ''
    return d, errors


def _detect_ok(ext, head):
    ole = (b'\xd0\xcf\x11\xe0',)
    sig = {'pdf': (b'%PDF',), 'png': (b'\x89PNG',), 'jpg': (b'\xff\xd8',), 'jpeg': (b'\xff\xd8',),
           'zip': (b'PK',), 'docx': (b'PK',), 'xlsx': (b'PK',), 'pptx': (b'PK',),
           'doc': ole, 'xls': ole, 'ppt': ole}
    return ext not in sig or any(head.startswith(s) for s in sig[ext])


def validate_job_files(files, existing_count=0):
    """Kiểm tra tệp tải lên. Trả về (list[(file, ext, size)], error|None)."""
    files = [f for f in files if f and f.filename]
    if existing_count + len(files) > JOB_FILE_MAX_COUNT:
        return [], f'Tối đa {JOB_FILE_MAX_COUNT} tệp tham khảo cho mỗi yêu cầu.'
    out = []
    for f in files:
        name = secure_filename(f.filename) or ''
        ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
        if ext not in JOB_FILE_EXTENSIONS:
            return [], f'Tệp "{f.filename}" không được hỗ trợ. Cho phép: ' + ', '.join(sorted(JOB_FILE_EXTENSIONS)) + '.'
        f.stream.seek(0, 2)
        size = f.stream.tell()
        f.stream.seek(0)
        if size == 0:
            return [], f'Tệp "{f.filename}" rỗng.'
        if size > JOB_FILE_MAX_BYTES:
            return [], f'Tệp "{f.filename}" vượt quá 10MB.'
        head = f.stream.read(8)
        f.stream.seek(0)
        if not _detect_ok(ext, head):
            return [], f'Nội dung tệp "{f.filename}" không khớp với định dạng .{ext}.'
        out.append((f, ext, size))
    return out, None


def save_job_files(job, validated):
    saved = []
    try:
        for f, ext, size in validated:
            stored = f'{_uuid.uuid4().hex}.{ext}'
            f.save(os.path.join(JOB_FILES_FOLDER, stored))
            saved.append(stored)
            db.session.add(JobAttachment(job_id=job.id, original_name=(secure_filename(f.filename) or stored)[:255],
                                         stored_name=stored, size=size))
    except Exception:
        for s in saved:
            try:
                os.remove(os.path.join(JOB_FILES_FOLDER, s))
            except OSError:
                pass
        raise


def _job_form_values(job):
    if not job:
        return {}
    return {
        'title': job.title, 'description': job.description, 'category_group': job.display_category_group,
        'service_type': job.display_service_type, 'source_lang': job.source_lang, 'target_lang': job.target_lang,
        'specialty': job.specialty or '', 'word_count': job.word_count or '', 'budget_type': job.budget_type or 'negotiable',
        'budget_min': job.budget_min or '', 'budget_max': job.budget_max or '', 'extra_requirements': job.extra_requirements or '',
        'deadline': job.deadline.isoformat() if job.deadline else '', 'event_date': job.event_date or '',
        'event_time_start': job.event_time_start or '', 'event_time_end': job.event_time_end or '',
        'event_location': job.event_location or '',
    }


def _issue_form_token():
    tokens = session.get('job_form_tokens', [])
    t = _uuid.uuid4().hex
    session['job_form_tokens'] = (tokens + [t])[-5:]
    return t


def _render_job_form(job=None, values=None, errors=None, policy=None, status=200, rows=None, hirer_verified=True):
    html = render_template('post_job.html', job=job, values=values if values is not None else _job_form_values(job),
                           errors=errors or {}, policy=policy, form_token=_issue_form_token(),
                           service_types=JOB_SERVICE_TYPES, langs=JOB_LANGS, specialties=JOB_SPECIALTIES,
                           attachments=job.attachments if job else [], max_files=JOB_FILE_MAX_COUNT,
                           today=date.today().isoformat(),
                           schedule_rows=rows if rows is not None else (_schedule_rows_for_job(job) if job else []),
                           hirer_verified=hirer_verified)
    return html, status


@app.errorhandler(413)
def handle_too_large(e):
    flash('Tổng dung lượng tải lên vượt quá 16MB. Vui lòng chọn tệp nhỏ hơn.', 'error')
    return redirect(request.referrer or url_for('my_jobs'))


@app.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    user = get_current_user()
    if not user or user.role != 'hirer':
        flash(_t('flash.hirer_only_post'), 'error')
        return redirect(url_for('index'))
    if isinstance(user.id, str):
        flash('Tài khoản này chưa hỗ trợ đăng yêu cầu.', 'error')
        return redirect(url_for('index'))

    from services.hirer_verification import can_hirer_post_job
    can_post, cannot_post_reason, _within7 = can_hirer_post_job(user)

    if request.method == 'GET':
        return _render_job_form(hirer_verified=can_post)

    if not can_post:
        try:
            create_notification(user_id=user.id, notification_type='VERIFICATION_REQUIRED',
                                title='Cần xác minh tài khoản để đăng yêu cầu', message=cannot_post_reason or 'Hoàn tất xác minh người đăng tuyển để đăng yêu cầu.',
                                url=url_for('account_profile', tab='hirer_verify'))
            db.session.commit()
        except Exception:
            db.session.rollback()
        flash(cannot_post_reason, 'error')
        return redirect(url_for('account_profile', tab='hirer_verify'))

    token = request.form.get('form_token', '')
    tokens = session.get('job_form_tokens', [])
    if token not in tokens:
        flash('Yêu cầu này đã được gửi hoặc biểu mẫu đã hết hạn. Vui lòng kiểm tra danh sách yêu cầu.', 'warning')
        return redirect(url_for('my_jobs'))
    if not _csrf_ok():
        flash('Phiên làm việc không hợp lệ. Vui lòng thử lại.', 'error')
        return redirect(url_for('post_job'))

    data, errors = validate_job_form(request.form)
    validated, file_err = validate_job_files(request.files.getlist('files'))
    if file_err:
        errors['files'] = file_err
    if errors:
        return _render_job_form(values=request.form.to_dict(), errors=errors, status=400,
                                rows=_schedule_entries_from_form(request.form), hirer_verified=can_post)

    # Token dùng một lần: ngăn gửi trùng
    session['job_form_tokens'] = [t for t in tokens if t != token]
    try:
        entries = data.pop('_entries', [])
        job = Job(hirer_id=user.id, **data)
        db.session.add(job)
        db.session.flush()
        _save_job_schedule(job, entries)
        _submit_for_moderation(job, user, is_new=True)
        save_job_files(job, validated)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"[post_job error] Failed to save job for user {user.id}: {e}", exc_info=True)
        session['job_form_tokens'] = tokens
        return _render_job_form(values=request.form.to_dict(),
                                errors={'_form': 'Không thể lưu yêu cầu. Vui lòng kiểm tra lại thông tin và thử lại.'}, status=500,
                                rows=_schedule_entries_from_form(request.form), hirer_verified=can_post)

    # Job chỉ hiện cho phiên dịch viên và được thông báo sau khi admin duyệt
    flash('Yêu cầu đã gửi, đang chờ admin duyệt theo tiêu chuẩn an toàn.', 'success')
    return redirect(url_for('job_detail', job_id=job.id))


@app.route('/my-jobs')
@login_required
def my_jobs():
    current = get_current_user()
    if current and current.role == 'translator':
        return redirect(url_for('job_statistics'))
    user = _require_hirer()
    if not user:
        flash(_t('flash.hirer_only_post'), 'error')
        return redirect(url_for('index'))
    q = (request.args.get('q') or '').strip()[:100]
    status = request.args.get('status', '')
    lang = request.args.get('lang', '')
    service = request.args.get('service', '')
    page = max(request.args.get('page', 1, type=int) or 1, 1)

    query = Job.query.filter_by(hirer_id=user.id)
    if q:
        safe = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.filter(Job.title.ilike(f'%{safe}%', escape='\\'))
    if status in JOB_STATUS_LABELS:
        query = query.filter(Job.status == status)
    if lang in JOB_LANGS:
        query = query.filter(db.or_(Job.source_lang == lang, Job.target_lang == lang))
    if service in JOB_SERVICE_TYPES:
        query = query.filter(Job.category_group == service)
    pagination = query.order_by(Job.created_at.desc(), Job.id.desc()).paginate(page=page, per_page=10, error_out=False)
    ids = [j.id for j in pagination.items]
    counts = dict(db.session.query(Proposal.job_id, db.func.count(Proposal.id))
                  .filter(Proposal.job_id.in_(ids)).group_by(Proposal.job_id).all()) if ids else {}
    rows = [{'job': j, 'label': job_status_label(j), 'proposals': counts.get(j.id, 0),
             'policy': job_edit_policy(j, counts.get(j.id, 0))}
            for j in pagination.items]
    total_all = Job.query.filter_by(hirer_id=user.id).count()
    return render_template('my_jobs.html', rows=rows, pagination=pagination, q=q, status=status, lang=lang,
                           service=service, langs=JOB_LANGS, service_types=JOB_SERVICE_TYPES,
                           status_labels=JOB_STATUS_LABELS, total_all=total_all)


@app.route('/my-jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@app.route('/job/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    user = _require_hirer()
    if not user:
        flash(_t('flash.hirer_only_post'), 'error')
        return redirect(url_for('index'))
    job = _owned_job_or_404(user, job_id)
    policy = job_edit_policy(job)
    if not policy['can_edit']:
        flash('Yêu cầu này không còn ở trạng thái cho phép chỉnh sửa.', 'error')
        return redirect(url_for('job_detail', job_id=job.id))

    if request.method == 'GET':
        return _render_job_form(job=job, policy=policy)

    if not _csrf_ok():
        flash('Phiên làm việc không hợp lệ. Vui lòng thử lại.', 'error')
        return redirect(url_for('edit_job', job_id=job.id))
    data, errors = validate_job_form(request.form, existing=job, locked=policy['locked'])
    remove_ids = {int(x) for x in request.form.getlist('remove_attachment') if x.isdigit()}
    keep_count = len([a for a in job.attachments if a.id not in remove_ids])
    validated, file_err = validate_job_files(request.files.getlist('files'), existing_count=keep_count)
    if file_err:
        errors['files'] = file_err
    if errors:
        return _render_job_form(job=job, values={**_job_form_values(job), **request.form.to_dict()}, errors=errors,
                                policy=policy, status=400, rows=_schedule_entries_from_form(request.form))

    removed_files = []
    try:
        entries = data.pop('_entries', [])
        for k, v in data.items():
            setattr(job, k, v)
        if entries or data.get('category_group') == 'translation' or job.display_category_group == 'translation':
            _save_job_schedule(job, entries)
        _submit_for_moderation(job, user, is_new=False)   # sửa job → duyệt lại phiên bản mới
        for a in list(job.attachments):
            if a.id in remove_ids:
                removed_files.append(a.stored_name)
                db.session.delete(a)
        save_job_files(job, validated)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[edit_job error] {e}")
        return _render_job_form(job=job, values={**_job_form_values(job), **request.form.to_dict()},
                                errors={'_form': 'Không thể lưu thay đổi. Vui lòng thử lại.'}, policy=policy, status=500)
    for s in removed_files:
        try:
            os.remove(os.path.join(JOB_FILES_FOLDER, s))
        except OSError:
            pass
    flash('Đã cập nhật yêu cầu và chuyển vào hàng chờ duyệt lại.', 'success')
    return redirect(url_for('job_detail', job_id=job.id))


def _change_job_status(job_id, action):
    user = _require_hirer()
    if not user:
        abort(403)
    job = _owned_job_or_404(user, job_id)
    if not _csrf_ok():
        flash('Phiên làm việc không hợp lệ. Vui lòng thử lại.', 'error')
        return redirect(request.referrer or url_for('my_jobs'))
    policy = job_edit_policy(job)
    if not policy['can_' + action]:
        flash('Không thể thực hiện thao tác này với trạng thái hiện tại của yêu cầu.', 'error')
        return redirect(request.referrer or url_for('my_jobs'))
    job.status = 'closed' if action == 'close' else 'cancelled'
    job.closed_at = datetime.utcnow()
    if action == 'cancel':
        job.moderation_status = 'archived'
        Proposal.query.filter_by(job_id=job.id, status='pending').update({'status': 'rejected'})
    db.session.commit()
    flash('Đã đóng nhận báo giá cho yêu cầu.' if action == 'close' else 'Đã hủy yêu cầu.', 'success')
    return redirect(request.referrer or url_for('my_jobs'))


@app.route('/my-jobs/<int:job_id>/close', methods=['POST'])
@login_required
def close_job(job_id):
    return _change_job_status(job_id, 'close')


@app.route('/my-jobs/<int:job_id>/cancel', methods=['POST'])
@login_required
def cancel_job(job_id):
    return _change_job_status(job_id, 'cancel')


def can_view_job_files(user, job):
    if not user or isinstance(user.id, str):
        return False
    if user.id == job.hirer_id or user.is_admin:
        return True
    if user.role == 'translator':
        return bool(Proposal.query.filter_by(job_id=job.id, translator_id=user.id).first()
                    or Contract.query.filter_by(job_id=job.id, translator_id=user.id).first())
    return False


@app.route('/job-attachment/<int:attachment_id>')
@login_required
def job_attachment(attachment_id):
    att = JobAttachment.query.get_or_404(attachment_id)
    if not can_view_job_files(get_current_user(), att.job):
        abort(404)
    resp = send_from_directory(JOB_FILES_FOLDER, att.stored_name, as_attachment=True, download_name=att.original_name)
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Cache-Control'] = 'private, no-store'
    return resp


# ─── TRANG THỐNG KÊ CÔNG VIỆC (QUẢN LÝ VÒNG ĐỜI CÔNG VIỆC PHIÊN DỊCH VIÊN) ───────────

@app.route('/job-statistics', endpoint='job_statistics')
@app.route('/job-stats', endpoint='job_stats')
@login_required
def job_statistics():
    user = get_current_user()
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('index'))
    if user.role != 'translator':
        flash('Trang này dành riêng cho tài khoản phiên dịch viên.', 'warning')
        return redirect(url_for('my_jobs'))

    tab = request.args.get('tab', 'all').strip().lower()
    filter_param = request.args.get('filter', '').strip().lower()
    if filter_param in ['active', 'contracts']:
        tab = 'accepted'
    elif filter_param in ['completed']:
        tab = 'completed'
    elif filter_param in ['saved']:
        tab = 'saved'

    status_filter = request.args.get('status', 'all').strip().lower()
    acceptance_filter = request.args.get('acceptance', 'all').strip().lower()
    payment_filter = request.args.get('payment', 'all').strip().lower()
    time_range = request.args.get('time_range', 'all').strip().lower()
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'newest').strip().lower()

    # Truy vấn dữ liệu thực tế từ database
    all_user_proposals = Proposal.query.filter_by(translator_id=user.id).order_by(Proposal.created_at.desc()).all()
    all_user_contracts = Contract.query.filter_by(translator_id=user.id).order_by(Contract.created_at.desc()).all()

    try:
        saved_records = SavedJob.query.filter_by(user_id=user.id).order_by(SavedJob.created_at.desc()).all()
        saved_jobs = [s.job for s in saved_records if s.job]
    except Exception:
        db.session.rollback()
        saved_records = []
        saved_jobs = []

    # 1. Thống kê theo chuẩn nghiệp vụ (Không hard-code, không trùng lặp)
    total_applications = len(all_user_proposals)

    # Đang chờ phản hồi / đang xem xét / cần phản hồi / được chọn chờ xác nhận
    pending_review_proposals = [p for p in all_user_proposals if p.effective_status in ['pending', 'reviewing', 'needs_response', 'selected']]
    pending_review_count = len(pending_review_proposals)

    # Ca làm việc đã nhận chính thức (hợp đồng đã tạo và sẵn sàng/ký quỹ)
    accepted_upcoming_contracts = [c for c in all_user_contracts if c.shift_status_info['code'] in ['escrow_pending', 'upcoming']]
    accepted_count = len(accepted_upcoming_contracts)

    in_progress_contracts = [c for c in all_user_contracts if c.shift_status_info['code'] == 'in_progress']
    in_progress_count = len(in_progress_contracts)

    delivered_contracts = [c for c in all_user_contracts if c.status == 'delivered']
    delivered_count = len(delivered_contracts)

    completed_contracts = [c for c in all_user_contracts if c.status in ['completed', 'reviewed']]
    completed_count = len(completed_contracts)

    rejected_proposals = [p for p in all_user_proposals if p.effective_status == 'rejected']
    withdrawn_proposals = [p for p in all_user_proposals if p.effective_status == 'withdrawn']
    closed_proposals = [p for p in all_user_proposals if p.effective_status == 'job_closed']
    cancelled_contracts = [c for c in all_user_contracts if c.status == 'cancelled']
    non_continuing_count = len(rejected_proposals) + len(withdrawn_proposals) + len(closed_proposals) + len(cancelled_contracts)

    # Thống kê tài chính
    total_net_earned = sum((getattr(c, 'translator_net_amount', 0) or 0) for c in completed_contracts)
    total_gross_earned = sum((getattr(c, 'agreed_price', 0) or 0) for c in completed_contracts)
    total_platform_fee = sum((getattr(c, 'platform_fee', 0) or 0) for c in completed_contracts)
    total_held_escrow = sum((getattr(c, 'translator_net_amount', 0) or 0) for c in delivered_contracts)

    rated_reviews = []
    for c in completed_contracts:
        try:
            cr = getattr(c, 'client_review', None)
            if cr and getattr(cr, 'rating', None):
                rated_reviews.append(cr)
        except Exception:
            pass
    avg_rating = round(sum(r.rating for r in rated_reviews) / len(rated_reviews), 1) if rated_reviews else 0.0
    total_reviews_count = len(rated_reviews)

    # Thống kê số lượng theo 8 trạng thái đề xuất (hỗ trợ pill filters)
    proposal_status_counts = {
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
        if eff in proposal_status_counts:
            proposal_status_counts[eff] += 1

    # Thống kê số lượng theo trạng thái ca làm
    contract_status_counts = {
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
        if code in contract_status_counts:
            contract_status_counts[code] += 1

    # Sub-counts cho tab Đã nhận
    accepted_sub_counts = {
        'all': accepted_count,
        'escrow_pending': len([c for c in accepted_upcoming_contracts if c.shift_status_info['code'] == 'escrow_pending']),
        'upcoming': len([c for c in accepted_upcoming_contracts if c.shift_status_info['code'] == 'upcoming']),
    }

    # Sub-counts cho tab Đang thực hiện (bao gồm ca đang diễn ra & ca chờ xác nhận hoàn thành)
    in_progress_total = in_progress_count + delivered_count
    in_progress_sub_counts = {
        'all': in_progress_total,
        'in_progress': in_progress_count,
        'delivered': delivered_count,
    }

    # Sub-counts cho tab Không tiếp tục
    cancelled_sub_counts = {
        'all': non_continuing_count,
        'rejected': len(rejected_proposals),
        'withdrawn': len(withdrawn_proposals),
        'job_closed': len(closed_proposals),
        'cancelled': len(cancelled_contracts),
    }

    metrics = {
        'total_applications': total_applications,
        'pending_review': pending_review_count,
        'accepted': accepted_count,
        'in_progress': in_progress_count,
        'in_progress_total': in_progress_total,
        'delivered': delivered_count,
        'completed': completed_count,
        'non_continuing': non_continuing_count,
        'saved': len(saved_jobs),
        'total_net_earned': total_net_earned,
        'total_gross_earned': total_gross_earned,
        'total_platform_fee': total_platform_fee,
        'total_held_escrow': total_held_escrow,
        'avg_rating': avg_rating,
        'total_reviews_count': total_reviews_count,
    }

    tab_counts = {
        'all': len(all_user_contracts) + len([p for p in all_user_proposals if p.effective_status != 'accepted']),
        'applied': len(all_user_proposals),
        'accepted': accepted_count,
        'in_progress': in_progress_total,
        'delivered': delivered_count,
        'completed': completed_count,
        'cancelled': non_continuing_count,
        'saved': len(saved_jobs),
    }

    # Xử lý lọc và chuẩn bị danh sách hiển thị theo Tab
    items = []
    
    def matches_search(title_text, extra_text=""):
        if not search_query:
            return True
        sq = search_query.lower()
        return sq in (title_text or '').lower() or sq in (extra_text or '').lower()

    if tab == 'applied':
        if status_filter != 'all':
            proposals_pool = [p for p in all_user_proposals if p.effective_status == status_filter]
        else:
            proposals_pool = all_user_proposals
        
        for p in proposals_pool:
            title = p.job.title if p.job else ''
            loc = p.job.event_location if p.job else ''
            if matches_search(title, loc):
                items.append({
                    'type': 'proposal',
                    'data': p,
                    'created_at': p.created_at or datetime.min,
                    'sort_date': p.created_at or datetime.min,
                    'price': p.price or 0,
                    'status_info': p.status_info,
                    'title': title
                })

    elif tab == 'accepted':
        contracts_pool = accepted_upcoming_contracts
        if status_filter != 'all':
            contracts_pool = [c for c in contracts_pool if c.shift_status_info['code'] == status_filter]

        for c in contracts_pool:
            title = c.job.title if c.job else (c.service.name if c.service else f'Ca #{c.id}')
            loc = c.location or ''
            if matches_search(title, f"{loc} #{c.id}"):
                items.append({
                    'type': 'contract',
                    'data': c,
                    'created_at': c.created_at or datetime.min,
                    'sort_date': c.event_sort_date or datetime.min,
                    'price': c.agreed_price or 0,
                    'status_info': c.shift_status_info,
                    'title': title
                })

    elif tab == 'in_progress':
        contracts_pool = []
        if status_filter in ['all', 'in_progress']:
            contracts_pool.extend(in_progress_contracts)
        if status_filter in ['all', 'delivered']:
            contracts_pool.extend(delivered_contracts)

        for c in contracts_pool:
            title = c.job.title if c.job else (c.service.name if c.service else f'Ca #{c.id}')
            loc = c.location or ''
            if matches_search(title, f"{loc} #{c.id}"):
                items.append({
                    'type': 'contract',
                    'data': c,
                    'created_at': c.created_at or datetime.min,
                    'sort_date': c.event_sort_date or datetime.min,
                    'price': c.agreed_price or 0,
                    'status_info': c.shift_status_info,
                    'title': title
                })

    elif tab == 'delivered':
        for c in delivered_contracts:
            title = c.job.title if c.job else (c.service.name if c.service else f'Ca #{c.id}')
            loc = c.location or ''
            if matches_search(title, f"{loc} #{c.id}"):
                items.append({
                    'type': 'contract',
                    'data': c,
                    'created_at': c.created_at or datetime.min,
                    'sort_date': c.event_sort_date or datetime.min,
                    'price': c.agreed_price or 0,
                    'status_info': c.shift_status_info,
                    'title': title
                })

    elif tab == 'completed':
        contracts_pool = completed_contracts
        if acceptance_filter == 'accepted':
            contracts_pool = [c for c in contracts_pool if c.status in ['completed', 'reviewed']]
        elif acceptance_filter == 'pending':
            contracts_pool = [c for c in contracts_pool if c.status == 'delivered']

        if payment_filter == 'paid':
            contracts_pool = [c for c in contracts_pool if c.status in ['completed', 'reviewed']]
        elif payment_filter == 'escrow_held':
            contracts_pool = [c for c in contracts_pool if c.status == 'delivered']

        today = date.today()
        if time_range == 'this_month':
            contracts_pool = [c for c in contracts_pool if getattr(c, 'event_sort_date', None) and c.event_sort_date.year == today.year and c.event_sort_date.month == today.month]
        elif time_range == 'last_month':
            last_m = today.month - 1 if today.month > 1 else 12
            last_y = today.year if today.month > 1 else today.year - 1
            contracts_pool = [c for c in contracts_pool if getattr(c, 'event_sort_date', None) and c.event_sort_date.year == last_y and c.event_sort_date.month == last_m]
        elif time_range == 'this_year':
            contracts_pool = [c for c in contracts_pool if getattr(c, 'event_sort_date', None) and c.event_sort_date.year == today.year]

        for c in contracts_pool:
            title = c.job.title if c.job else (c.service.name if c.service else f'Ca #{c.id}')
            loc = c.location or ''
            field = (c.job.specialty or c.job.category or '') if c.job else ''
            hirer_name = c.hirer.name if c.hirer else ''
            if matches_search(title, f"{loc} #{c.id} {field} {hirer_name}"):
                items.append({
                    'type': 'contract',
                    'data': c,
                    'created_at': c.created_at or datetime.min,
                    'sort_date': c.event_sort_date or datetime.min,
                    'price': c.agreed_price or 0,
                    'net_price': c.translator_net_amount or 0,
                    'status_info': c.shift_status_info,
                    'acceptance_info': c.acceptance_status_info,
                    'payment_info': c.payment_status_info,
                    'review': c.client_review,
                    'title': title
                })

    elif tab == 'cancelled':
        proposals_pool = []
        if status_filter in ['all', 'rejected']:
            proposals_pool.extend(rejected_proposals)
        if status_filter in ['all', 'withdrawn']:
            proposals_pool.extend(withdrawn_proposals)
        if status_filter in ['all', 'job_closed']:
            proposals_pool.extend(closed_proposals)

        for p in proposals_pool:
            title = p.job.title if p.job else ''
            loc = p.job.event_location if p.job else ''
            if matches_search(title, loc):
                items.append({
                    'type': 'proposal',
                    'data': p,
                    'created_at': p.created_at or datetime.min,
                    'sort_date': p.created_at or datetime.min,
                    'price': p.price or 0,
                    'status_info': p.status_info,
                    'title': title
                })

        if status_filter in ['all', 'cancelled']:
            for c in cancelled_contracts:
                title = c.job.title if c.job else (c.service.name if c.service else f'Ca #{c.id}')
                loc = c.location or ''
                if matches_search(title, f"{loc} #{c.id}"):
                    items.append({
                        'type': 'contract',
                        'data': c,
                        'created_at': c.created_at or datetime.min,
                        'sort_date': c.event_sort_date or datetime.min,
                        'price': c.agreed_price or 0,
                        'status_info': c.shift_status_info,
                        'title': title
                    })

    elif tab == 'saved':
        for j in saved_jobs:
            if matches_search(j.title, j.event_location or ''):
                items.append({
                    'type': 'saved_job',
                    'data': j,
                    'created_at': j.created_at or datetime.min,
                    'sort_date': j.created_at or datetime.min,
                    'price': j.budget or 0,
                    'title': j.title
                })

    else:  # tab == 'all'
        for c in all_user_contracts:
            title = c.job.title if c.job else (c.service.name if c.service else f'Ca #{c.id}')
            loc = c.location or ''
            if matches_search(title, f"{loc} #{c.id}"):
                items.append({
                    'type': 'contract',
                    'data': c,
                    'created_at': c.created_at or datetime.min,
                    'sort_date': c.event_sort_date or datetime.min,
                    'price': c.agreed_price or 0,
                    'status_info': c.shift_status_info,
                    'title': title
                })
        for p in all_user_proposals:
            if p.effective_status != 'accepted':
                title = p.job.title if p.job else ''
                loc = p.job.event_location if p.job else ''
                if matches_search(title, loc):
                    items.append({
                        'type': 'proposal',
                        'data': p,
                        'created_at': p.created_at or datetime.min,
                        'sort_date': p.created_at or datetime.min,
                        'price': p.price or 0,
                        'status_info': p.status_info,
                        'title': title
                    })

    # Sắp xếp danh sách items an toàn (hỗ trợ date & datetime không bị lỗi so sánh)
    from datetime import time as _dt_time
    def _to_dt(val):
        if not val:
            return datetime.min
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            return datetime.combine(val, _dt_time.min)
        return datetime.min

    if sort_by == 'oldest':
        items.sort(key=lambda x: _to_dt(x.get('created_at')))
    elif sort_by == 'price_desc':
        items.sort(key=lambda x: (x.get('price') or 0), reverse=True)
    elif sort_by == 'price_asc':
        items.sort(key=lambda x: (x.get('price') or 0))
    elif sort_by == 'top_rated':
        items.sort(key=lambda x: (x.get('review').rating if (x.get('review') and getattr(x.get('review'), 'rating', None)) else 0), reverse=True)
    elif sort_by == 'event_asc':
        items.sort(key=lambda x: _to_dt(x.get('sort_date')))
    elif sort_by == 'event_desc':
        items.sort(key=lambda x: _to_dt(x.get('sort_date')), reverse=True)
    else:  # 'newest'
        items.sort(key=lambda x: _to_dt(x.get('created_at')), reverse=True)

    # Phân trang (Pagination)
    import math
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    per_page = 15
    total_items = len(items)
    total_pages = max(1, math.ceil(total_items / per_page))
    if page > total_pages:
        page = total_pages
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paged_items = items[start_idx:end_idx]

    return render_template('job_statistics.html',
        items=paged_items,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        per_page=per_page,
        tab=tab,
        metrics=metrics,
        tab_counts=tab_counts,
        proposal_status_counts=proposal_status_counts,
        contract_status_counts=contract_status_counts,
        accepted_sub_counts=accepted_sub_counts,
        in_progress_sub_counts=in_progress_sub_counts,
        cancelled_sub_counts=cancelled_sub_counts,
        status_filter=status_filter,
        acceptance_filter=acceptance_filter,
        payment_filter=payment_filter,
        time_range=time_range,
        search_query=search_query,
        sort_by=sort_by
    )


@app.route('/applied-jobs', endpoint='applied_jobs')
@login_required
def applied_jobs():
    args = dict(request.args)
    if 'tab' not in args:
        args['tab'] = 'applied'
    return redirect(url_for('job_statistics', **args))


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
            'redirect_url': url_for('job_statistics', tab='accepted')
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
def api_reject_proposal(proposal_id):
    """
    Hợp nhất luồng từ chối báo giá (Task 2.3).
    Hỗ trợ cả JSON payload {reason: ..., note: ...} và Form POST {note: ...}.
    Kiểm tra quyền sở hữu công việc, trạng thái hợp lệ, CSRF token và thông báo cho phiên dịch viên.
    """
    user = _require_hirer()
    if not user:
        return jsonify({'ok': False, 'success': False, 'message': 'Chỉ khách thuê mới thực hiện được thao tác này.'}), 403
    
    token = request.headers.get('X-CSRF-Token') or request.form.get('_csrf_token')
    if token and not _csrf_ok():
        return jsonify({'ok': False, 'success': False, 'message': 'Phiên làm việc không hợp lệ. Vui lòng tải lại trang.'}), 403

    reason = ''
    if request.is_json:
        data = request.get_json(silent=True) or {}
        reason = (data.get('reason') or data.get('note') or '').strip()
    else:
        reason = (request.form.get('reason') or request.form.get('note') or '').strip()

    from services.proposals import reject_proposal_for_hirer, ProposalError
    try:
        prop = reject_proposal_for_hirer(proposal_id, user.id, note=reason)
        if hasattr(prop, 'client_note'):
            prop.client_note = reason or 'Cảm ơn bạn đã quan tâm. Chúng tôi đã chọn ứng viên khác phù hợp hơn.'
            db.session.commit()
        return jsonify({
            'ok': True,
            'success': True,
            'message': 'Đã từ chối đề xuất thành công.'
        })
    except ProposalError as e:
        return jsonify({'ok': False, 'success': False, 'message': e.message}), e.status
    except Exception as e:
        db.session.rollback()
        import logging
        logging.exception(f"Lỗi khi từ chối proposal #{proposal_id}: {e}")
        return jsonify({'ok': False, 'success': False, 'message': 'Đã xảy ra lỗi hệ thống khi từ chối đề xuất.'}), 500


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
    args = dict(request.args)
    if 'tab' not in args:
        args['tab'] = 'accepted'
    return redirect(url_for('job_statistics', **args))


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
    args = dict(request.args)
    if 'tab' not in args:
        args['tab'] = 'completed'
    return redirect(url_for('job_statistics', **args))


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
    sort = request.args.get('sort', '')
    page = request.args.get('page', 1, type=int)
    recommended = request.args.get('recommended')
    per_page = request.args.get('per_page', 120, type=int)

    # Lấy các công việc đang mở, đã duyệt, không bị gắn cờ và còn trong thời hạn ứng tuyển
    today = date.today()
    base_query = Job.query.join(User, Job.hirer_id == User.id).filter(
        Job.status == 'open',
        Job.moderation_status == 'approved',
        db.or_(Job.is_flagged == False, Job.is_flagged == None),
        User.is_active == True,
        db.or_(Job.deadline.is_(None), Job.deadline >= today)
    )

    total_open_jobs = base_query.count()

    user = get_current_user()
    rec_map = {}
    is_rec_mode = bool(recommended)

    if is_rec_mode:
        if not user:
            flash('Vui lòng đăng nhập bằng tài khoản phiên dịch viên để xem danh sách việc làm phù hợp.', 'info')
            return redirect(url_for('login', next=request.url))
        if user.role != 'translator':
            flash('Chức năng "Việc làm phù hợp" dành riêng cho tài khoản phiên dịch viên.', 'info')
            return redirect(url_for('job_list'))

        from services.matching import get_recommended_jobs_for_translator
        try:
            current_lang = session.get('lang') or request.cookies.get('lang') or 'vi'
            rec_list = get_recommended_jobs_for_translator(user.id, limit=100, lang=current_lang)
            rec_map = {r['job_id']: r for r in rec_list}
            if rec_map:
                query = base_query.filter(Job.id.in_(list(rec_map.keys())))
            else:
                query = base_query.filter(Job.id == -1)
        except Exception as e:
            import logging
            logging.error(f"Error fetching recommended jobs in job_list: {e}")
            query = base_query.filter(Job.id == -1)
    else:
        query = base_query

    if lang:
        safe_lang = lang.replace('%', r'\%').replace('_', r'\_')
        query = query.filter(db.or_(Job.source_lang.ilike(f'%{safe_lang}%'), Job.target_lang.ilike(f'%{safe_lang}%')))

    if sort == 'budget_desc':
        query = query.order_by(Job.budget_min.desc())
    elif sort == 'budget_asc':
        query = query.order_by(Job.budget_min.asc())
    elif not is_rec_mode or sort:
        query = query.order_by(Job.created_at.desc())

    # Lấy toàn bộ danh sách hợp lệ để client-side filter & pagination hoạt động đầy đủ
    all_jobs = query.all()

    # Gắn điểm số phù hợp và lý do gợi ý vào từng job object
    for j in all_jobs:
        if j.id in rec_map:
            j.match_score = rec_map[j.id].get('match_score', 0)
            j.match_reasons = rec_map[j.id].get('reasons', [])
        else:
            j.match_score = None
            j.match_reasons = []

    # Nếu đang ở chế độ xem việc phù hợp và không chọn sort khác thì sắp xếp theo điểm match_score
    if is_rec_mode and not sort:
        all_jobs.sort(key=lambda j: (j.match_score or 0, j.created_at or datetime.min), reverse=True)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template(
        'job_list.html',
        jobs=all_jobs,
        pagination=pagination,
        lang_filter=lang,
        LANGUAGES=LANGUAGES,
        is_recommended=is_rec_mode,
        total_open_jobs=total_open_jobs,
        recommended_count=len(rec_map) if is_rec_mode else 0
    )

@app.route('/job/<int:job_id>', methods=['GET', 'POST'])
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    # ── 0. Access Control ─────────────────────────────────────────────────
    user = get_current_user()
    from services.permissions import can_view_job
    if not can_view_job(job, user):
        flash('Bài đăng này đang chờ duyệt, bị ẩn hoặc tài khoản người đăng không hoạt động.', 'warning')
        return redirect(url_for('index'))

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
        from services.schedule import check_job_schedule_conflicts

        try:
            result = check_job_schedule_conflicts(job, user.id)
            if result.get('has_schedule') and not result.get('available'):
                # Tìm ngày đầu tiên bị trùng để báo lỗi
                for day in result.get('days', []):
                    if not day.get('available'):
                        flash(f'Bạn đã có lịch công việc khác vào ngày {day["date_display"]} '
                              f'({day["conflict_start"]}–{day["conflict_end"]}). '
                              f'Vui lòng kiểm tra lịch của bạn.', 'error')
                        break
                return render_template(
                    'job_detail.html', job=job, form_data=request.form,
                    is_saved=is_saved, existing_proposal=existing_proposal,
                    is_expired=is_expired, profile_incomplete=profile_incomplete,
                    profile_missing_fields=profile_missing_fields
                )
        except Exception as e:
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
        price_raw = (request.form.get('price') or '').strip()
        if not price_raw.isdigit() or int(price_raw) <= 0 or int(price_raw) > 10**10:
            flash('Vui lòng nhập giá đề xuất lớn hơn 0.', 'error')
            return render_template('job_detail.html', job=job, form_data=request.form, is_saved=is_saved, existing_proposal=existing_proposal, is_expired=is_expired, profile_incomplete=profile_incomplete, profile_missing_fields=profile_missing_fields)
        valid_until = None
        if (request.form.get('valid_until') or '').strip():
            try:
                valid_until = datetime.strptime(request.form['valid_until'].strip(), '%Y-%m-%d').date()
            except ValueError:
                valid_until = None
            if valid_until is None or valid_until < date.today():
                flash('Ngày hết hạn báo giá không hợp lệ hoặc đã ở quá khứ.', 'error')
                return render_template('job_detail.html', job=job, form_data=request.form, is_saved=is_saved, existing_proposal=existing_proposal, is_expired=is_expired, profile_incomplete=profile_incomplete, profile_missing_fields=profile_missing_fields)
        field = lambda k, n=2000: (request.form.get(k) or '').strip()[:n]
        try:
            proposal = Proposal(
                job_id=job.id,
                translator_id=user.id,
                cover_letter=field('cover_letter', 5000),
                price=int(price_raw),
                time_estimate=time_estimate_str,
                scope=field('scope') or None,
                delivery_terms=field('delivery_terms') or None,
                revision_terms=field('revision_terms') or None,
                valid_until=valid_until,
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

    is_owner = bool(user and user.id == job.hirer_id)
    from services.proposals import build_proposal_views, job_accepts_selection, effective_status, PROPOSAL_STATUS_LABELS
    return render_template(
        'job_detail.html', job=job, is_saved=is_saved,
        existing_proposal=existing_proposal,
        my_proposal_label=(PROPOSAL_STATUS_LABELS.get(effective_status(existing_proposal)) if existing_proposal else ''),
        proposal_views=build_proposal_views(job) if is_owner else [],
        selectable=job_accepts_selection(job),
        is_expired=is_expired,
        profile_incomplete=profile_incomplete,
        profile_missing_fields=profile_missing_fields,
        is_owner=is_owner,
        can_view_files=can_view_job_files(user, job),
        job_policy=job_edit_policy(job) if is_owner else None,
        status_label=job_status_label(job)
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
    schedule conflict with this job's dates/times. Backend still re-validates
    at proposal submission — this is for UI feedback only.
    """
    from services.schedule import check_job_schedule_conflicts
    
    job = Job.query.get_or_404(job_id)
    result = check_job_schedule_conflicts(job, session['user_id'])

    if not result['has_schedule']:
        return jsonify({'available': True, 'reason': 'no_schedule'})

    # result trả về dạng:
    # {
    #     'available': bool,
    #     'has_schedule': True,
    #     'days': [
    #         { 'date': '...', 'date_display': '...', 'available': bool, 'message': '...', 'conflict_start': '...', 'conflict_end': '...' }
    #     ]
    # }
    return jsonify(result)

# ─── CONTRACT / BUSINESS PROCESS ───────────────────────────────────────────────

@app.route('/accept-proposal/<int:proposal_id>', methods=['POST'])
@login_required
def accept_proposal(proposal_id):
    """Chấp nhận báo giá (form POST). Logic dùng chung với API: services.proposals."""
    from services.proposals import accept_proposal_for_hirer, ProposalError
    prop = db.session.get(Proposal, proposal_id)
    back = url_for('job_detail', job_id=prop.job_id) if prop else url_for('index')
    if not _csrf_ok():
        flash('Phiên làm việc không hợp lệ. Vui lòng thử lại.', 'error')
        return redirect(back)
    try:
        contract = accept_proposal_for_hirer(proposal_id, session['user_id'])
    except ProposalError as e:
        flash(e.message, 'error')
        return redirect(back)
    flash('Đã chấp nhận báo giá! Vui lòng thanh toán để bắt đầu.', 'success')
    return redirect(url_for('payment_mockup', contract_id=contract.id))


def _proposal_api_guard():
    user = _require_hirer()
    if not user:
        return None, (jsonify({'ok': False, 'message': 'Chỉ khách thuê mới thực hiện được thao tác này.'}), 403)
    if not _csrf_ok():
        return None, (jsonify({'ok': False, 'message': 'Phiên làm việc không hợp lệ. Vui lòng tải lại trang.'}), 403)
    return user, None


@app.route('/api/proposals/<int:proposal_id>/accept', methods=['POST'])
@login_required
def api_accept_proposal(proposal_id):
    from services.proposals import accept_proposal_for_hirer, ProposalError
    user, err = _proposal_api_guard()
    if err:
        return err
    try:
        contract = accept_proposal_for_hirer(proposal_id, user.id)
    except ProposalError as e:
        return jsonify({'ok': False, 'message': e.message}), e.status
    return jsonify({'ok': True, 'message': 'Đã chấp nhận báo giá. Vui lòng thanh toán để bắt đầu.',
                    'redirect': url_for('payment_mockup', contract_id=contract.id)})



@app.route('/api/jobs/<int:job_id>/proposals')
@login_required
def api_job_proposals(job_id):
    from services.proposals import build_proposal_views
    user = _require_hirer()
    job = db.session.get(Job, job_id)
    if not user or not job or job.hirer_id != user.id:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({'items': build_proposal_views(job)})


# ─── CLIENT PROJECT MANAGEMENT (Task 05) ───────────────────────────────────────

def _project_status_clause(key):
    """Điều kiện SQL cho bộ lọc theo trạng thái hiển thị."""
    has_files = Contract.deliverables.any()
    if key == 'pending_payment':
        return Contract.status == 'escrow_pending'
    if key == 'in_progress':
        return db.and_(Contract.status.in_(('in_progress', 'active', 'escrow_held')), ~has_files)
    if key == 'awaiting_acceptance':
        return db.and_(Contract.status == 'in_progress', has_files)
    if key in ('awaiting_translator', 'revision_requested', 'completed', 'cancelled'):
        return Contract.status == key
    return None


@app.route('/my-projects')
@login_required
def my_projects():
    from services.projects import DISPLAY_STATUS, display_status, project_title, language_pair, project_deadline
    user = _require_hirer()
    if not user:
        flash(_t('flash.hirer_only_post'), 'error')
        return redirect(url_for('index'))
    q = (request.args.get('q') or '').strip()[:100]
    status = request.args.get('status', '')
    page = max(request.args.get('page', 1, type=int) or 1, 1)

    query = (Contract.query.filter(Contract.hirer_id == user.id)
             .outerjoin(Job, Contract.job_id == Job.id).outerjoin(Service, Contract.service_id == Service.id))
    if q:
        safe = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.filter(db.or_(Job.title.ilike(f'%{safe}%', escape='\\'), Service.name.ilike(f'%{safe}%', escape='\\')))
    clause = _project_status_clause(status) if status in DISPLAY_STATUS else None
    if clause is not None:
        query = query.filter(clause)
    pagination = query.order_by(Contract.created_at.desc(), Contract.id.desc()).paginate(page=page, per_page=10, error_out=False)
    rows = []
    for c in pagination.items:
        key, label = display_status(c)
        rows.append({'c': c, 'title': project_title(c), 'pair': language_pair(c), 'status': key, 'label': label,
                     'translator': c.translator.name if c.translator else '—', 'deadline': project_deadline(c)})
    total_all = Contract.query.filter_by(hirer_id=user.id).count()
    return render_template('my_projects.html', rows=rows, pagination=pagination, q=q, status=status,
                           status_labels=DISPLAY_STATUS, total_all=total_all)


@app.route('/my-projects/<int:contract_id>')
@login_required
def project_detail(contract_id):
    from services.projects import (display_status, stage_index, STAGES, project_title, language_pair,
                                   project_deadline, build_timeline)
    from models import get_job_schedule_entries
    user = _require_hirer()
    if not user:
        flash(_t('flash.hirer_only_post'), 'error')
        return redirect(url_for('index'))
    c = db.session.get(Contract, contract_id)
    if not c or c.hirer_id != user.id:
        abort(404)
    deliverables = sorted(c.deliverables, key=lambda d: d.created_at or datetime.min, reverse=True)
    key, label = display_status(c, len(deliverables))
    proposal = db.session.get(Proposal, c.proposal_id) if c.proposal_id else None
    profile = c.translator.profile if c.translator else None
    payments = PaymentTransaction.query.filter_by(contract_id=c.id).all()
    if any(p.status == 'completed' for p in payments):
        pay_label = 'Đã giải ngân cho phiên dịch viên'
    elif any(p.status == 'escrow_pending' for p in payments):
        pay_label = 'Đã thanh toán vào Escrow (đang được giữ)'
    elif any(p.status == 'refunded' for p in payments):
        pay_label = 'Đã hoàn tiền'
    else:
        pay_label = 'Chưa thanh toán'
    last_revision = (ContractEvent.query.filter_by(contract_id=c.id, event_type='revision_requested')
                     .order_by(ContractEvent.created_at.desc(), ContractEvent.id.desc()).first())
    deadline = project_deadline(c)
    days_left = (deadline - date.today()).days if deadline and c.status in ('in_progress', 'revision_requested', 'escrow_pending') else None
    schedule = []
    if c.job:
        try:
            schedule = get_job_schedule_entries(c.job)
        except Exception:
            schedule = []
    my_review = Review.query.filter_by(contract_id=c.id, reviewer_id=user.id).first()
    return render_template('project_detail.html', c=c, title=project_title(c), pair=language_pair(c),
                           status_key=key, status_label=label, stage=stage_index(c, len(deliverables)), stages=STAGES,
                           deliverables=deliverables, proposal=proposal, profile=profile, deadline=deadline,
                           days_left=days_left, schedule=schedule, timeline=build_timeline(c), pay_label=pay_label,
                           last_revision=last_revision, my_review=my_review,
                           attachments=(c.job.attachments if c.job else []))


@app.route('/deliverable/<int:deliverable_id>')
@login_required
def download_deliverable(deliverable_id):
    """Tải tệp bàn giao — chỉ các bên của hợp đồng (hoặc admin). Không có URL công khai."""
    d = Deliverable.query.get_or_404(deliverable_id)
    from services.permissions import can_access_contract
    if not can_access_contract(session['user_id'], d.contract):
        abort(404)
    name = os.path.basename(d.filepath or '')
    folder = DELIVERABLE_FOLDER if os.path.exists(os.path.join(DELIVERABLE_FOLDER, name)) else app.config['UPLOAD_FOLDER']
    if not name or not os.path.exists(os.path.join(folder, name)):
        abort(404)
    resp = send_from_directory(folder, name, as_attachment=True, download_name=d.filename)
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Cache-Control'] = 'private, no-store'
    return resp


def _project_api_guard():
    user = _require_hirer()
    if not user:
        return None, (jsonify({'ok': False, 'message': 'Chỉ khách thuê của dự án mới thực hiện được thao tác này.'}), 403)
    if not _csrf_ok():
        return None, (jsonify({'ok': False, 'message': 'Phiên làm việc không hợp lệ. Vui lòng tải lại trang.'}), 403)
    return user, None


@app.route('/api/projects/<int:contract_id>/accept-delivery', methods=['POST'])
@login_required
def api_project_accept_delivery(contract_id):
    from services.projects import accept_delivery, ProjectError
    user, err = _project_api_guard()
    if err:
        return err
    try:
        accept_delivery(contract_id, user.id)
    except ProjectError as e:
        return jsonify({'ok': False, 'message': e.message}), e.status
    return jsonify({'ok': True, 'message': 'Đã xác nhận hoàn thành dự án.'})


@app.route('/api/projects/<int:contract_id>/request-revision', methods=['POST'])
@login_required
def api_project_request_revision(contract_id):
    from services.projects import request_revision, ProjectError
    user, err = _project_api_guard()
    if err:
        return err
    try:
        request_revision(contract_id, user.id, request.form.get('note', ''))
    except ProjectError as e:
        return jsonify({'ok': False, 'message': e.message}), e.status
    return jsonify({'ok': True, 'message': 'Đã gửi yêu cầu chỉnh sửa cho phiên dịch viên.'})


@app.route('/api/projects/<int:contract_id>')
@login_required
def api_project_summary(contract_id):
    from services.projects import display_status, project_title, language_pair, project_deadline
    user = _require_hirer()
    c = db.session.get(Contract, contract_id)
    if not user or not c or c.hirer_id != user.id:
        return jsonify({'error': 'not_found'}), 404
    key, label = display_status(c)
    dl = project_deadline(c)
    return jsonify({'id': c.id, 'title': project_title(c), 'status': key, 'status_label': label,
                    'translator': c.translator.name if c.translator else None, 'language_pair': language_pair(c),
                    'agreed_price': c.agreed_price, 'deadline': dl.isoformat() if dl else None,
                    'deliverables': len(c.deliverables)})


@app.route('/payment-mockup/<int:contract_id>', methods=['GET', 'POST'])
@login_required
def payment_mockup(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    from services.permissions import require_contract_access
    require_contract_access(session['user_id'], contract)

    if session['user_id'] != contract.hirer_id:
        abort(403)
    if contract.status != 'escrow_pending':
        if contract.status == 'awaiting_translator':
            flash('Phiên dịch viên chưa xác nhận lịch, bạn chưa thể thanh toán.', 'warning')
        else:
            flash('Hợp đồng này không ở trạng thái chờ thanh toán.', 'error')
        return redirect(url_for('transaction_detail', contract_id=contract.id))

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
            db.session.add(ContractEvent(contract_id=contract.id, actor_id=contract.hirer_id, event_type='paid'))
            db.session.add(PaymentTransaction(
                contract_id=contract.id, user_id=contract.hirer_id,
                amount=contract.agreed_price, status='escrow_pending',
                payment_method='mockup'))
            create_notification(
                user_id=contract.translator_id, notification_type='PAYMENT_RECEIVED',
                title='Khách đã thanh toán vào Escrow',
                message=f'{contract.hirer.name} đã thanh toán {contract.agreed_price:,} VND vào Escrow. Bạn có thể bắt đầu thực hiện.',
                url=url_for('transaction_detail', contract_id=contract.id), related_contract_id=contract.id)
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
            schedules = TranslatorSchedule.query.filter_by(contract_id=contract.id).all()
            for s in schedules:
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
        if contract.status not in ('in_progress', 'revision_requested'):
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

        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        file.stream.seek(0, 2)
        size = file.stream.tell()
        file.stream.seek(0)
        if size == 0 or size > JOB_FILE_MAX_BYTES:
            flash('Tệp rỗng hoặc vượt quá 10MB.', 'error')
            return redirect(url_for('transaction_detail', contract_id=contract.id))
        head = file.stream.read(8)
        file.stream.seek(0)
        if not _detect_ok(ext, head):
            flash('Nội dung tệp không khớp với định dạng khai báo.', 'error')
            return redirect(url_for('transaction_detail', contract_id=contract.id))
        stored_name = f'{_uuid.uuid4().hex}.{ext}'
        filepath = os.path.join(DELIVERABLE_FOLDER, stored_name)

        try:
            file.save(filepath)
        except Exception:
            flash('Lỗi khi tải file lên máy chủ.', 'error')
            return redirect(url_for('transaction_detail', contract_id=contract.id))

        try:
            deliverable = Deliverable(
                contract_id=contract.id,
                filename=filename,
                filepath=stored_name
            )
            message = Message(
                contract_id=contract.id,
                sender_id=session['user_id'],
                content=f'📎 Đã gửi tệp: {filename}'
            )

            db.session.add(deliverable)
            db.session.add(message)
            from services.projects import record_delivery
            record_delivery(contract, session['user_id'])
            db.session.flush()

            from services.projects import project_title
            create_notification(
                user_id=contract.hirer_id,
                notification_type='DELIVERABLE_UPLOADED',
                title='Có tệp bàn giao mới — cần nghiệm thu',
                message=f'{contract.translator.name} đã bàn giao tệp "{filename}" cho "{project_title(contract)}". Vui lòng kiểm tra và nghiệm thu.',
                url=url_for('project_detail', contract_id=contract.id),
                related_contract_id=contract.id
            )

            db.session.commit()
            flash('Đã gửi tài liệu thành công.', 'success')
        except Exception:
            db.session.rollback()
            flash('Lỗi hệ thống khi lưu tài liệu.', 'error')

        return redirect(url_for('transaction_detail', contract_id=contract.id))

    return render_template('transaction_detail.html', contract=contract)

@app.route('/contract/<int:contract_id>/<action>', methods=['POST'])
@login_required
def contract_action(contract_id, action):
    """PDV xác nhận/từ chối lịch; hirer hoặc PDV hủy hợp đồng."""
    if action not in ('accept', 'decline', 'cancel'):
        abort(404)
    contract = Contract.query.with_for_update().get_or_404(contract_id)
    from services.permissions import require_contract_access
    from services.contract_flow import (ContractFlowError, accept_booking,
                                        decline_booking, cancel_contract)
    require_contract_access(session['user_id'], contract)
    try:
        if action == 'accept':
            accept_booking(contract, session['user_id'])
            flash('Đã xác nhận lịch. Đang chờ khách thanh toán.', 'success')
        elif action == 'decline':
            decline_booking(contract, session['user_id'])
            flash('Đã từ chối yêu cầu đặt lịch.', 'success')
        else:
            pct = cancel_contract(contract, session['user_id'])
            flash('Đã hủy hợp đồng.' + (f' Khách được hoàn {pct}% số tiền đã thanh toán.' if pct else ''), 'success')
    except ContractFlowError as e:
        db.session.rollback()
        flash(str(e), 'error')
    return redirect(url_for('transaction_detail', contract_id=contract_id))

@app.route('/approve-contract/<int:contract_id>', methods=['POST'])
@login_required
def approve_contract(contract_id):
    """Nghiệm thu (form POST cũ). Logic dùng chung với API: services.projects."""
    from services.projects import accept_delivery, ProjectError
    contract = Contract.query.get_or_404(contract_id)
    from services.permissions import require_contract_access
    require_contract_access(session['user_id'], contract)
    if session['user_id'] == contract.hirer_id:
        if not _csrf_ok():
            flash('Phiên làm việc không hợp lệ. Vui lòng thử lại.', 'error')
        else:
            try:
                accept_delivery(contract.id, session['user_id'])
                if contract.schedule:
                    contract.schedule.status = 'completed'
                    db.session.commit()
                flash('Nghiệm thu thành công! Tiền Escrow đã được giải ngân.', 'success')
            except ProjectError as e:
                flash(e.message, 'error')
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

        if reviewer_id == contract.translator_id:
            # Phiên dịch viên đánh giá khách -> tính lại điểm của khách từ các review hiển thị
            db.session.flush()
            from services.hirer import recalculate_hirer_rating
            recalculate_hirer_rating(contract.hirer_id)

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

    return jsonify([{'id': m.id, 'sender_id': m.sender_id, 'sender_name': m.sender.name if m.sender else '',
                     'content': m.content, 'image_url': getattr(m, 'image_url', None),
                     'time': m.created_at.strftime('%H:%M %d/%m') if m.created_at else ''} for m in msgs])

@app.route('/api/jobs/<int:job_id>/report', methods=['POST'])
@login_required
def report_job(job_id):
    """
    Phiên dịch viên hoặc người dùng gửi báo cáo vi phạm về Job.
    Task 8.1: Khi đạt đủ 3 báo cáo độc lập từ 3 người dùng khác nhau,
    Job sẽ tự động bị gắn cờ (is_flagged=True, moderation_status='flagged') và tạm ẩn.
    """
    job = Job.query.get_or_404(job_id)
    user = get_current_user()
    
    data = request.get_json() or {}
    reason = data.get('reason', '').strip()
    description = data.get('description', '').strip()
    evidence_url = data.get('evidence_url', '').strip()

    if not reason:
        return jsonify({'status': 'error', 'message': 'Vui lòng chọn lý do báo cáo.'}), 400

    # Kiểm tra xem user này đã gửi báo cáo cho job này chưa (chống gửi lặp)
    existing_report = Report.query.filter_by(
        reporter_id=user.id, target_type='job', target_id=job.id
    ).first()
    if existing_report:
        return jsonify({'status': 'error', 'message': 'Bạn đã gửi báo cáo cho công việc này rồi.'}), 400

    report = Report(
        reporter_id=user.id,
        target_type='job',
        target_id=job.id,
        reason=reason,
        description=description,
        evidence_url=evidence_url or None,
        related_job_id=job.id,
        status='new'
    )
    db.session.add(report)
    db.session.flush()

    # Đếm số người báo cáo độc lập
    distinct_reporters_count = db.session.query(
        db.func.count(db.func.distinct(Report.reporter_id))
    ).filter(Report.target_type == 'job', Report.target_id == job.id).scalar()

    auto_flagged = False
    if distinct_reporters_count >= 3:
        job.is_flagged = True
        job.moderation_status = 'flagged'
        auto_flagged = True
        
        AdminAuditLog.log(
            action=ADMIN_AUDIT_ACTIONS['FLAG_JOB'],
            target_type='job',
            target_id=job.id,
            description=f'Hệ thống tự động tạm ẩn và gắn cờ Job #{job.id} sau khi nhận đủ 3 báo cáo độc lập.',
            extra_data={'distinct_reporters': distinct_reporters_count}
        )
        
        try:
            from models import AdminNotification
            db.session.add(AdminNotification(
                type='NEW_REPORT',
                title=f'Cảnh báo: Job #{job.id} bị tự động gắn cờ',
                message=f'Công việc "{job.title}" đã nhận đủ {distinct_reporters_count} báo cáo độc lập và đã được tạm ẩn tự động khỏi sàn.',
                related_id=job.id,
                url=url_for('admin_job_review', job_id=job.id)
            ))
        except Exception:
            pass

    db.session.commit()
    return jsonify({
        'status': 'ok',
        'message': 'Cảm ơn bạn đã gửi báo cáo. Ban quản trị sẽ rà soát nội dung này.',
        'auto_flagged': auto_flagged
    })

@app.route('/api/messages/<int:contract_id>', methods=['POST'])
@login_required
def send_message(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    sender_id = session['user_id']
    from services.permissions import require_contract_access
    require_contract_access(sender_id, contract)

    data = request.get_json(silent=True) or {}
    content = str(data.get('content') or '').strip()
    image_url = str(data.get('image_url') or '').strip()
    ok_msg, err = _validate_chat_payload(content, image_url, sender_id)
    if not ok_msg:
        return jsonify({'status': 'error', 'message': err}), 400

    # TASK 8.3: QUÉT TIN NHẮN PHÁT HIỆN LIÊN HỆ NGOÀI / THANH TOÁN NGOÀI (C1/C2)
    from services.job_moderation import scan_text_violations
    viols = scan_text_violations(content)
    has_warning = bool(viols)
    warning_msg = ('Lưu ý: Tin nhắn chứa thông tin liên hệ hoặc thanh toán ngoài nền tảng. VietTranslate khuyến cáo '
                   'chỉ giao dịch qua hệ thống để đảm bảo an toàn Escrow.') if viols else None

    msg = Message(contract_id=contract_id, sender_id=sender_id,
                  content=content or '[Hình ảnh]', image_url=image_url or None)
    db.session.add(msg)
    db.session.flush()

    receiver_id = contract.translator_id if sender_id == contract.hirer_id else contract.hirer_id
    receiver = db.session.get(User, receiver_id)
    sender = db.session.get(User, sender_id)
    if receiver and sender:
        from services.notifications import should_notify
        if should_notify(receiver, 'NEW_MESSAGE'):
            try:
                create_notification(
                    user_id=receiver_id, notification_type='NEW_MESSAGE', title='Bạn có tin nhắn mới',
                    message=f'{sender.name} đã gửi cho bạn một tin nhắn trong dự án.',
                    url=url_for('messages_page', c=f'c:{contract.id}'), related_contract_id=contract.id)
            except Exception as e:
                print(f"Error creating notification: {e}")
    db.session.commit()
    return jsonify({'status': 'ok', 'id': msg.id, 'has_warning': has_warning, 'warning_message': warning_msg})


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
@admin_login_required
@require_permission('view_dashboard')
def admin_dashboard():
    stats = {
        'total_users': User.query.filter_by(is_admin=False).count(),
        'total_translators': TranslatorProfile.query.count(),
        'pending_verify': TranslatorProfile.query.filter_by(is_verified=False).count(),
        'open_jobs': Job.query.filter(Job.status == 'open', db.or_(Job.is_flagged == False, Job.is_flagged == None)).count(),
        'flagged_jobs': Job.query.filter_by(is_flagged=True).count(),
        'active_contracts': Contract.query.filter_by(status='in_progress').count(),
        'completed_contracts': Contract.query.filter_by(status='completed').count(),
    }
    recent_users = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).limit(5).all()
    recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
    return render_template('admin_dashboard.html', stats=stats, recent_users=recent_users, recent_jobs=recent_jobs)

@app.route('/admin/jobs')
@admin_login_required
@require_permission('view_jobs')
def admin_jobs():
    status_filter = request.args.get('status', 'all')
    from services.job_moderation import evaluate_job_39_criteria
    
    # Lấy tất cả job để đánh giá tiêu chí
    all_jobs = Job.query.order_by(Job.created_at.desc()).all()
    
    job_items = []
    pending_count = 0
    critical_count = 0
    
    for job in all_jobs:
        eval_res = evaluate_job_39_criteria(job)
        is_pending = bool((job.moderation_status == 'pending' or (job.status == 'pending' and job.moderation_status not in ('approved', 'rejected', 'archived', 'flagged'))) and not job.is_flagged)
        is_critical = (eval_res['total_critical'] > 0)
        
        if is_pending:
            pending_count += 1
        if is_critical and not job.is_flagged:
            critical_count += 1
            
        # Áp dụng bộ lọc
        include = True
        if status_filter == 'pending':
            include = is_pending
        elif status_filter == 'critical':
            include = is_critical
        elif status_filter == 'needs_revision':
            include = (job.moderation_status == 'needs_revision' or (eval_res['total_warnings'] > 0 and is_pending))
        elif status_filter == 'open':
            include = (job.moderation_status == 'approved' or job.status == 'open') and not job.is_flagged
        elif status_filter == 'rejected':
            include = bool(job.moderation_status == 'rejected')
        elif status_filter == 'flagged':
            include = bool(job.is_flagged or job.moderation_status == 'flagged')
        elif status_filter == 'archived':
            include = (job.moderation_status == 'archived' or job.status == 'archived')
            
        if include:
            job_items.append({'job': job, 'eval': eval_res})
            
    return render_template(
        'admin_jobs.html',
        job_items=job_items,
        status_filter=status_filter,
        pending_count=pending_count,
        critical_count=critical_count
    )

@app.route('/admin/jobs/<int:job_id>/review', methods=['GET'])
@admin_login_required
@require_permission('view_jobs')
def admin_job_review(job_id):
    """Màn hình chi tiết xét duyệt Job theo chuẩn Hình 3."""
    job = Job.query.get_or_404(job_id)
    from services.job_moderation import evaluate_job_39_criteria
    eval_result = evaluate_job_39_criteria(job)
    return render_template('admin_job_review.html', job=job, eval_result=eval_result)

@app.route('/admin/jobs/<int:job_id>/moderate', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('approve_job')
def admin_moderate_job(job_id):
    """Ra quyết định kiểm duyệt Job (Duyệt, Yêu cầu sửa, Từ chối)."""
    job = Job.query.get_or_404(job_id)
    decision = (request.form.get('decision') or '').strip()
    ALLOWED_DECISIONS = ('approve', 'needs_revision', 'reject')
    if not decision or decision not in ALLOWED_DECISIONS:
        flash('Quyết định kiểm duyệt không hợp lệ hoặc bị thiếu.', 'error')
        return redirect(url_for('admin_job_review', job_id=job.id))

    from services.job_moderation import evaluate_job_39_criteria
    import json
    
    # Kiểm tra ghi đè tiêu chí thủ công C7
    chk_c7 = (request.form.get('chk_C7') == '1')
    manual_overrides = {'C7': chk_c7}
    eval_res = evaluate_job_39_criteria(job, manual_overrides=manual_overrides)
    job.moderation_checklist_data = json.dumps(eval_res)
    job.moderated_at = datetime.utcnow()
    job.moderated_by = session.get('admin_id')

    admin_user = get_current_user()
    
    if decision == 'approve':
        job.moderation_status = 'approved'
        job.status = 'open'
        job.is_flagged = False
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS['APPROVE_JOB'],
            target_type='job',
            target_id=job.id,
            description=f'Phê duyệt job "{job.title}" (ID={job.id}) đạt kiểm duyệt.',
            extra_data={'checklist_summary': eval_res['summary_label']}
        )
        # Gửi thông báo cho Hirer
        if job.hirer:
            try:
                from app import create_notification
                create_notification(
                    user_id=job.hirer_id,
                    notification_type='JOB_APPROVED',
                    title='Công việc đã được phê duyệt',
                    message=f'Công việc "{job.title}" của bạn đã được kiểm duyệt và hiển thị công khai.',
                    url=url_for('job_detail', job_id=job.id),
                    related_job_id=job.id
                )
            except Exception:
                pass
        # Gửi thông báo cho các phiên dịch viên phù hợp trên sàn
        try:
            from services.matching import notify_matching_translators_for_new_job
            notify_matching_translators_for_new_job(job)
        except Exception:
            pass
        flash('Đã phê duyệt công việc thành công. Job đã hiển thị công khai.', 'success')
        
    elif decision == 'needs_revision':
        notes = request.form.get('revision_notes', '').strip()
        job.moderation_status = 'needs_revision'
        job.status = 'pending'
        job.moderation_notes = notes
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS['REQUEST_JOB_REVISION'],
            target_type='job',
            target_id=job.id,
            description=f'Yêu cầu chỉnh sửa job "{job.title}" (ID={job.id})',
            extra_data={'notes': notes}
        )
        if job.hirer:
            try:
                from app import create_notification
                create_notification(
                    user_id=job.hirer_id,
                    notification_type='JOB_NEEDS_REVISION',
                    title='Yêu cầu chỉnh sửa công việc',
                    message=f'Job "{job.title}" cần chỉnh sửa: {notes}',
                    url=url_for('job_detail', job_id=job.id),
                    related_job_id=job.id
                )
            except Exception:
                pass
        flash('Đã gửi yêu cầu chỉnh sửa tới người đăng tuyển.', 'warning')
        
    elif decision == 'reject':
        reason = request.form.get('rejection_reason', '').strip()
        job.moderation_status = 'rejected'
        job.status = 'closed'
        job.moderation_notes = reason
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS['REJECT_JOB'],
            target_type='job',
            target_id=job.id,
            description=f'Từ chối job "{job.title}" (ID={job.id})',
            extra_data={'reason': reason}
        )
        if job.hirer:
            try:
                from app import create_notification
                create_notification(
                    user_id=job.hirer_id,
                    notification_type='JOB_REJECTED',
                    title='Công việc bị từ chối phê duyệt',
                    message=f'Job "{job.title}" đã bị từ chối: {reason}',
                    url=url_for('job_detail', job_id=job.id),
                    related_job_id=job.id
                )
            except Exception:
                pass
        flash('Đã từ chối công việc.', 'error')

    db.session.commit()
    return redirect(url_for('admin_jobs'))

@app.route('/admin/jobs/<int:job_id>/edit-title', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('approve_job')
def admin_edit_job_title(job_id):
    """Admin sửa nhẹ định dạng tiêu đề (D3)."""
    job = Job.query.get_or_404(job_id)
    old_title = job.title
    new_title = request.form.get('new_title', '').strip()
    if new_title and len(new_title) >= 10:
        job.title = new_title
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS['UPDATE_JOB_TITLE'],
            target_type='job',
            target_id=job.id,
            description=f'Admin chuẩn hóa tiêu đề job #{job.id}',
            extra_data={'old_title': old_title, 'new_title': new_title}
        )
        db.session.commit()
        flash('Đã cập nhật tiêu đề chuẩn hóa cho bài đăng.', 'success')
    else:
        flash('Tiêu đề mới không hợp lệ (tối thiểu 10 ký tự).', 'error')
    return redirect(url_for('admin_job_review', job_id=job.id))

@app.route('/admin/jobs/<int:job_id>/archive', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('approve_job')
def admin_archive_job(job_id):
    """Lưu trữ job an toàn (ẩn khỏi danh sách nhưng bảo toàn báo giá & hợp đồng)."""
    job = Job.query.get_or_404(job_id)
    job.moderation_status = 'archived'
    job.status = 'archived'
    _audit_log(
        action=ADMIN_AUDIT_ACTIONS['ARCHIVE_JOB'],
        target_type='job',
        target_id=job.id,
        description=f'Lưu trữ an toàn job #{job.id} "{job.title}"',
    )
    db.session.commit()
    flash(f'Đã chuyển bài đăng #{job.id} sang trạng thái Lưu trữ an toàn.', 'success')
    return redirect(url_for('admin_jobs'))

@app.route('/admin/jobs/<int:job_id>/flag', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('flag_job')
def admin_flag_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_flagged = not job.is_flagged
    if job.is_flagged:
        job.moderation_status = 'flagged'
    else:
        job.moderation_status = 'approved' if job.status == 'open' else 'pending'
        
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

@app.route('/admin/jobs/<int:job_id>/approve', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('approve_job')
def admin_approve_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.status = 'open'
    job.moderation_status = 'approved'
    job.is_flagged = False
    _audit_log(
        action=ADMIN_AUDIT_ACTIONS['APPROVE_JOB'],
        target_type='job',
        target_id=job.id,
        description=f'Phê duyệt job "{job.title}" (ID={job.id})',
    )
    db.session.commit()
    # Gửi thông báo cho các phiên dịch viên phù hợp trên sàn
    try:
        from services.matching import notify_matching_translators_for_new_job
        notify_matching_translators_for_new_job(job)
    except Exception:
        pass
    flash('Đã phê duyệt bài đăng thành công.', 'success')
    return redirect(url_for('admin_jobs'))

@app.route('/admin/jobs/<int:job_id>/delete', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('reject_job')
def admin_delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    
    # 1. BẢO TỒN DỮ LIỆU GIAO DỊCH (TASK 9 CASCADE PROTECTION)
    from models import Contract, Proposal, PaymentTransaction
    if Contract.query.filter_by(job_id=job.id).count() > 0:
        flash('Không thể xóa vĩnh viễn job đã có Hợp đồng. Vui lòng chọn "Lưu trữ" hoặc "Tạm ẩn" để bảo toàn dữ liệu.', 'error')
        return redirect(url_for('admin_jobs'))
        
    if Proposal.query.filter_by(job_id=job.id).count() > 0:
        flash('Không thể xóa vĩnh viễn job đã nhận Báo giá (Proposal). Vui lòng chọn "Lưu trữ" để bảo toàn lịch sử ứng tuyển.', 'error')
        return redirect(url_for('admin_jobs'))
        
    # Xử lý dependencies phụ
    from models import Notification, TranslatorSchedule, Report, JobSchedule
    Notification.query.filter_by(related_job_id=job.id).update({'related_job_id': None})
    Report.query.filter_by(related_job_id=job.id).update({'related_job_id': None})
    TranslatorSchedule.query.filter_by(job_id=job.id).update({'job_id': None})
    JobSchedule.query.filter_by(job_id=job.id).delete()
    
    _audit_log(
        action=ADMIN_AUDIT_ACTIONS['DELETE_JOB'],
        target_type='job',
        target_id=job.id,
        description=f'Xóa vĩnh viễn job "{job.title}" (ID={job.id}) của hirer {job.hirer.name if job.hirer else ""}',
    )
    db.session.delete(job)
    db.session.commit()
    flash('Đã xoá vĩnh viễn bài đăng thành công.', 'success')
    return redirect(url_for('admin_jobs'))

# ─── ADMIN HIRER VERIFICATION ROUTES ──────────────────────────────────────────

@app.route('/admin/hirers')
@admin_login_required
@require_permission('view_hirers')
def admin_hirers():
    """Danh sách người đăng tuyển và tiến độ xác minh X1–X8."""
    status_filter = request.args.get('status', 'all')
    from services.hirer_verification import evaluate_hirer_criteria
    from models import HirerProfile
    
    users = User.query.filter_by(role='hirer', is_admin=False).order_by(User.created_at.desc()).all()
    hirer_items = []
    pending_count = 0
    
    for u in users:
        p = u.hirer_profile
        ev = evaluate_hirer_criteria(u, p)
        is_pending = bool(p and p.verification_status == 'pending')
        if is_pending:
            pending_count += 1
            
        include = True
        if status_filter == 'pending':
            include = is_pending
        elif status_filter == 'verified':
            include = bool(p and p.verification_status == 'verified' and p.is_verified)
        elif status_filter == 'needs_revision':
            include = bool(p and p.verification_status == 'needs_revision')
        elif status_filter == 'rejected':
            include = bool(p and p.verification_status in ('rejected', 'revoked', 'suspended'))
        elif status_filter == 'unverified':
            include = bool(not p or p.verification_status in ('unverified', None, ''))
            
        if include:
            hirer_items.append({'user': u, 'profile': p, 'eval': ev})
            
    return render_template(
        'admin_hirers.html',
        hirer_items=hirer_items,
        status_filter=status_filter,
        pending_count=pending_count
    )

@app.route('/admin/hirers/<int:hirer_id>/verify', methods=['GET'])
@admin_login_required
@require_permission('view_hirers')
def admin_hirer_verify(hirer_id):
    """Màn hình thẩm định người đăng tuyển theo chuẩn Hình 1."""
    hirer = User.query.get_or_404(hirer_id)
    if hirer.role != 'hirer':
        abort(404)
    from services.hirer_verification import evaluate_hirer_criteria
    profile = hirer.hirer_profile
    eval_result = evaluate_hirer_criteria(hirer, profile)
    return render_template('admin_hirer_verify.html', hirer=hirer, profile=profile, eval_result=eval_result)

@app.route('/admin/hirers/<int:hirer_id>/review', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('verify_hirer')
def admin_hirer_review_action(hirer_id):
    """Xử lý quyết định xác minh người đăng (Xác minh, Bổ sung, Từ chối, Thu hồi)."""
    hirer = User.query.get_or_404(hirer_id)
    action = (request.form.get('action') or '').strip()
    reason = request.form.get('reason', '').strip()
    
    ALLOWED_ACTIONS = ('verify', 'needs_revision', 'reject', 'revoke')
    if not action or action not in ALLOWED_ACTIONS:
        flash('Hành động xét duyệt không hợp lệ hoặc bị thiếu.', 'error')
        return redirect(url_for('admin_hirer_verify', hirer_id=hirer_id))
    
    profile = hirer.hirer_profile
    if not profile:
        profile = HirerProfile(user_id=hirer.id)
        db.session.add(profile)
        
    chk_x3 = (request.form.get('chk_X3') == '1')
    from services.hirer_verification import evaluate_hirer_criteria
    import json
    eval_res = evaluate_hirer_criteria(hirer, profile, manual_overrides={'X3': chk_x3})
    profile.verification_checklist_data = json.dumps(eval_res)
    
    if action == 'verify':
        profile.verification_status = 'verified'
        profile.is_verified = True
        profile.verified_at = datetime.utcnow()
        hirer.verified_at = datetime.utcnow()
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS['VERIFY_HIRER'],
            target_type='user',
            target_id=hirer.id,
            description=f'Admin xác minh người đăng tuyển: {hirer.name} ({hirer.email})',
            extra_data={'checklist': eval_res}
        )
        try:
            from app import create_notification
            create_notification(
                user_id=hirer.id,
                notification_type='VERIFICATION_APPROVED',
                title='Tài khoản đã được xác minh thành công',
                message='Hồ sơ người đăng tuyển của bạn đã được xác minh. Bạn đã có thể đăng tin tuyển dụng!',
                url=url_for('post_job')
            )
        except Exception:
            pass
        flash(f'Đã cấp xác minh thành công cho người đăng tuyển {hirer.name}.', 'success')
        
    elif action == 'needs_revision':
        profile.verification_status = 'needs_revision'
        profile.is_verified = False
        profile.rejection_reason = reason
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS['REQUEST_HIRER_REVISION'],
            target_type='user',
            target_id=hirer.id,
            description=f'Yêu cầu bổ sung hồ sơ người đăng: {hirer.name}',
            extra_data={'reason': reason}
        )
        try:
            from app import create_notification
            create_notification(
                user_id=hirer.id,
                notification_type='VERIFICATION_NEEDS_REVISION',
                title='Yêu cầu bổ sung hồ sơ người đăng',
                message=f'Hồ sơ của bạn cần bổ sung: {reason}',
                url=url_for('account_profile', tab='hirer_verify')
            )
        except Exception:
            pass
        flash(f'Đã gửi yêu cầu bổ sung thông tin tới {hirer.name}.', 'warning')
        
    elif action == 'reject':
        profile.verification_status = 'rejected'
        profile.is_verified = False
        profile.rejection_reason = reason
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS['REJECT_HIRER'],
            target_type='user',
            target_id=hirer.id,
            description=f'Từ chối xác minh người đăng tuyển: {hirer.name}',
            extra_data={'reason': reason}
        )
        try:
            from app import create_notification
            create_notification(
                user_id=hirer.id,
                notification_type='VERIFICATION_REJECTED',
                title='Hồ sơ xác minh bị từ chối',
                message=f'Yêu cầu xác minh của bạn đã bị từ chối: {reason}',
                url=url_for('account_profile', tab='hirer_verify')
            )
        except Exception:
            pass
        flash(f'Đã từ chối xác minh người đăng {hirer.name}.', 'error')

    elif action == 'revoke':
        profile.verification_status = 'revoked'
        profile.is_verified = False
        profile.rejection_reason = reason
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS['REVOKE_HIRER'],
            target_type='user',
            target_id=hirer.id,
            description=f'Thu hồi quyền xác minh người đăng tuyển: {hirer.name}',
            extra_data={'reason': reason}
        )
        try:
            from app import create_notification
            create_notification(
                user_id=hirer.id,
                notification_type='VERIFICATION_REVOKED',
                title='Quyền xác minh đã bị thu hồi',
                message=f'Quyền xác minh của bạn đã bị thu hồi: {reason}',
                url=url_for('account_profile', tab='hirer_verify')
            )
        except Exception:
            pass
        flash(f'Đã thu hồi xác minh người đăng {hirer.name}.', 'warning')

    db.session.commit()
    return redirect(url_for('admin_hirers'))


@app.route('/admin/users')
@admin_login_required
@require_permission('view_users')
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
@admin_login_required
@csrf_protected
@require_permission('lock_user')
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
@admin_login_required
@require_permission('view_translators')
def admin_translators():
    show = request.args.get('show', 'pending')
    from models import TranslatorVerification
    verifications_query = TranslatorVerification.query.order_by(TranslatorVerification.created_at.desc())
    pending_verifications = TranslatorVerification.query.filter_by(status='pending').order_by(TranslatorVerification.created_at.desc()).all()

    if show == 'verified':
        profiles = TranslatorProfile.query.filter_by(is_verified=True).all()
        active_verifications = []
    elif show == 'all':
        profiles = TranslatorProfile.query.all()
        active_verifications = verifications_query.all()
    elif show == 'rejected':
        profiles = []
        active_verifications = TranslatorVerification.query.filter_by(status='rejected').order_by(TranslatorVerification.created_at.desc()).all()
    else:  # 'pending'
        profiles = TranslatorProfile.query.filter_by(is_verified=False).all()
        active_verifications = pending_verifications

    return render_template(
        'admin_translators.html',
        profiles=profiles,
        show=show,
        verifications=active_verifications,
        pending_count=len(pending_verifications)
    )

@app.route('/admin/translators/<int:profile_id>/verify', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('verify_translator')
def admin_verify_translator(profile_id):
    profile = TranslatorProfile.query.get_or_404(profile_id)
    action = request.form.get('action')
    profile.is_verified = (action == 'verify')

    # Đồng bộ với bản ghi TranslatorVerification nếu có
    from models import TranslatorVerification
    verif = TranslatorVerification.query.filter_by(user_id=profile.user_id).order_by(TranslatorVerification.created_at.desc()).first()
    if verif:
        verif.status = 'approved' if profile.is_verified else 'rejected'
        verif.reviewed_at = datetime.utcnow()
        verif.reviewed_by = session.get('admin_id')

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

@app.route('/admin/verifications/<int:verification_id>', methods=['GET'])
@admin_login_required
@require_permission('verify_translator')
def admin_verification_detail(verification_id):
    from models import TranslatorVerification
    import json
    verification = TranslatorVerification.query.get_or_404(verification_id)
    checklist_data = {}
    if verification.checklist_data:
        try:
            checklist_data = json.loads(verification.checklist_data)
        except Exception:
            pass
    return render_template('admin_verification_detail.html', verification=verification, checklist_data=checklist_data)

@app.route('/admin/verifications/<int:verification_id>/<action>', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('verify_translator')
def admin_review_verification(verification_id, action):
    """Phê duyệt hoặc từ chối yêu cầu xác minh của phiên dịch viên."""
    from services.verification import review_verification_request
    from admin_auth import get_client_ip

    admin = getattr(g, 'current_admin', None) or User.query.get(session.get('admin_id'))
    reason = request.form.get('reason', '')
    
    if action == 'policy_update':
        from services.verification import request_policy_reverification
        verification = TranslatorVerification.query.get_or_404(verification_id)
        policy_name = request.form.get('policy_name', 'Chính sách xác minh năng lực định kỳ')
        ok, msg, notif = request_policy_reverification(
            translator_user=verification.user,
            reason=reason,
            policy_name=policy_name,
            admin_user=admin,
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent', '')[:512]
        )
        if ok:
            flash(msg, 'success')
        else:
            flash(msg, 'error')
        return redirect(url_for('admin_translators', show='pending'))

    checklist_keys = ['A1', 'A2', 'A3', 'A4', 'A5', 'B1', 'B2', 'B3', 'B4', 'C1', 'C2', 'C3', 'C4', 'C5', 'D1', 'D2']
    checklist_data = {key: (request.form.get(f'chk_{key}') == 'on') for key in checklist_keys}

    ok, msg = review_verification_request(
        verification_id=verification_id,
        admin_user=admin,
        action=action,
        reason=reason,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent', '')[:512],
        checklist_data=checklist_data
    )
    if ok:
        flash(msg, 'success')
    else:
        flash(msg, 'error')
    return redirect(url_for('admin_translators', show='pending' if action == 'reject' else 'verified'))

@app.route('/admin/verifications/<int:verification_id>/request-policy-update', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('verify_translator')
def admin_request_policy_update(verification_id):
    """Admin gửi yêu cầu phiên dịch viên cập nhật hoặc xác minh lại theo chính sách."""
    from services.verification import request_policy_reverification
    from admin_auth import get_client_ip

    admin = getattr(g, 'current_admin', None) or User.query.get(session.get('admin_id'))
    reason = request.form.get('reason', 'Chính sách nền tảng định kỳ yêu cầu cập nhật hoặc xác minh lại hồ sơ.')
    policy_name = request.form.get('policy_name', 'Chính sách xác minh năng lực định kỳ')
    verification = TranslatorVerification.query.get_or_404(verification_id)

    ok, msg, notif = request_policy_reverification(
        translator_user=verification.user,
        reason=reason,
        policy_name=policy_name,
        admin_user=admin,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent', '')[:512]
    )
    if ok:
        flash(msg, 'success')
    else:
        flash(msg, 'error')
    return redirect(url_for('admin_translators', show='pending'))

@app.route('/admin/reports')
@admin_login_required
@require_permission('view_reports')
def admin_reports():
    status_filter = request.args.get('status', 'new')
    query = Report.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    reports = query.order_by(Report.created_at.desc()).all()
    return render_template('admin_reports.html', reports=reports, status_filter=status_filter)

@app.route('/admin/reports/<int:report_id>/<action>', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('resolve_report')
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
        if report.reporter_id:
            try:
                from app import create_notification
                notif_msg = f'Khiếu nại #{report.id} của bạn đã được giải quyết.'
                if note:
                    notif_msg += f' Nội dung phản hồi: {note}'
                create_notification(
                    user_id=report.reporter_id,
                    notification_type='SYSTEM',
                    title='Khiếu nại đã được xử lý',
                    message=notif_msg,
                    url=url_for('notifications_page')
                )
            except Exception:
                pass
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
        if report.reporter_id:
            try:
                from app import create_notification
                notif_msg = f'Khiếu nại #{report.id} của bạn đã được xem xét và không đủ căn cứ xử lý.'
                if reason:
                    notif_msg += f' Lý do: {reason}'
                create_notification(
                    user_id=report.reporter_id,
                    notification_type='SYSTEM',
                    title='Kết quả xử lý khiếu nại',
                    message=notif_msg,
                    url=url_for('notifications_page')
                )
            except Exception:
                pass
    else:
        abort(400)
        
    db.session.commit()
    flash(msg, 'success')
    return redirect(url_for('admin_reports'))

@app.route('/admin/proposals')
@admin_login_required
@require_permission('view_proposals')
def admin_proposals():
    status_filter = request.args.get('status', 'all')
    query = Proposal.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    proposals = query.order_by(Proposal.created_at.desc()).all()
    return render_template('admin_proposals.html', proposals=proposals, status_filter=status_filter)

@app.route('/admin/contracts')
@admin_login_required
@require_permission('view_contracts')
def admin_contracts():
    status_filter = request.args.get('status', 'all')
    query = Contract.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    contracts = query.order_by(Contract.created_at.desc()).all()
    return render_template('admin_contracts.html', contracts=contracts, status_filter=status_filter)

@app.route('/admin/schedules')
@admin_login_required
@require_permission('view_schedules')
def admin_schedules():
    status_filter = request.args.get('status', 'all')
    contract_id = request.args.get('contract_id', type=int)
    query = TranslatorSchedule.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if contract_id:
        query = query.filter_by(contract_id=contract_id)
    
    schedules = query.order_by(TranslatorSchedule.scheduled_date.desc(), TranslatorSchedule.start_time.desc()).all()
    return render_template('admin_schedules.html', schedules=schedules, status_filter=status_filter, contract_id=contract_id)

@app.route('/admin/reviews')
@admin_login_required
@require_permission('view_reviews')
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
@admin_login_required
@csrf_protected
@require_permission('hide_review')
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
    
    if r.reviewee and r.reviewee.role == 'hirer':
        db.session.flush()
        from services.hirer import recalculate_hirer_rating
        recalculate_hirer_rating(r.reviewee_id)
    elif r.reviewee and r.reviewee.role == 'translator':
        db.session.flush()
        t_prof = r.reviewee.profile
        if t_prof:
            valid_reviews = Review.query.filter_by(reviewee_id=r.reviewee_id, is_hidden=False).all()
            if valid_reviews:
                t_prof.rating = round(sum(rev.rating for rev in valid_reviews) / len(valid_reviews), 2)
                t_prof.total_reviews = len(valid_reviews)
            else:
                t_prof.rating = 0.0
                t_prof.total_reviews = 0

    db.session.commit()
    flash(msg, 'success')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/payments')
@admin_login_required
@require_permission('view_payments')
def admin_payments():
    status_filter = request.args.get('status', 'all')
    query = PaymentTransaction.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
        
    payments = query.order_by(PaymentTransaction.created_at.desc()).all()
    return render_template('admin_payments.html', payments=payments, status_filter=status_filter)

@app.route('/admin/payments/<int:payment_id>/refund', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('refund_payment')
def admin_refund_payment(payment_id):
    p = PaymentTransaction.query.get_or_404(payment_id)
    if p.status != 'escrow_pending' and p.status != 'completed':
        flash('Chỉ có thể hoàn tiền các giao dịch ở trạng thái escrow_pending hoặc completed.', 'error')
        return redirect(url_for('admin_payments'))
        
    p.status = 'refunded'
    if p.contract:
        p.contract.status = 'cancelled' # hoặc trạng thái tương ứng
        for uid_, url_ in ((p.contract.hirer_id, url_for('project_detail', contract_id=p.contract.id)),
                           (p.contract.translator_id, url_for('transaction_detail', contract_id=p.contract.id))):
            create_notification(user_id=uid_, notification_type='PAYMENT_REFUNDED', title='Giao dịch được hoàn tiền',
                                message=f'Giao dịch của hợp đồng #{p.contract.id} đã được hoàn tiền và hợp đồng bị hủy.',
                                url=url_, related_contract_id=p.contract.id)

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
@admin_login_required
@require_permission('view_notifications')
def admin_notifications():
    show_filter = request.args.get('show', 'all')
    query = AdminNotification.query
    if show_filter == 'unread':
        query = query.filter_by(is_read=False)
        
    notifications = query.order_by(AdminNotification.created_at.desc()).all()
    return render_template('admin_notifications.html', notifications=notifications, show=show_filter)

@app.route('/admin/notifications/<int:notif_id>/read', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('view_notifications')
def admin_notifications_read(notif_id):
    n = AdminNotification.query.get_or_404(notif_id)
    n.is_read = True
    db.session.commit()
    return redirect(url_for('admin_notifications'))

@app.route('/admin/notifications/read-all', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('view_notifications')
def admin_notifications_mark_all():
    AdminNotification.query.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('admin_notifications'))

@app.route('/admin/audit')
@admin_login_required
@require_permission('view_audit_logs')
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
@admin_login_required
@require_permission('manage_admins')
def admin_admins():
    from admin_auth import ROLE_DESCRIPTIONS, ROLE_PERMISSIONS, PERMISSION_GROUPS
    admins = User.query.filter_by(is_admin=True).order_by(User.created_at.desc()).all()
    # Danh sách người dùng tiềm năng chưa phải admin để hỗ trợ thăng cấp
    candidates = User.query.filter_by(is_admin=False, is_active=True).order_by(User.name.asc()).limit(150).all()
    return render_template(
        'admin_admins.html',
        admins=admins,
        candidates=candidates,
        role_descriptions=ROLE_DESCRIPTIONS,
        role_permissions=ROLE_PERMISSIONS,
        permission_groups=PERMISSION_GROUPS
    )

@app.route('/admin/admins/add', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('manage_admins')
def admin_add_admin():
    role = getattr(g, 'admin_role', None)
    if role != 'super_admin':
        flash('Chỉ Super Admin mới có quyền thêm Admin cấp dưới.', 'error')
        return redirect(url_for('admin_admins'))
        
    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''
    admin_role = request.form.get('admin_role')
    
    if not name or not email:
        flash('Vui lòng nhập đầy đủ họ tên và email.', 'error')
        return redirect(url_for('admin_admins'))
        
    # Chỉ cho phép tạo các role cấp dưới
    if admin_role not in ['moderator', 'support', 'finance']:
        flash('Chức vụ không hợp lệ. Vui lòng chọn vai trò cấp dưới hợp lệ.', 'error')
        return redirect(url_for('admin_admins'))
        
    if len(password) < 8:
        flash('Mật khẩu tạm thời phải có tối thiểu 8 ký tự.', 'error')
        return redirect(url_for('admin_admins'))
        
    existing = User.query.filter_by(email=email).first()
    if existing:
        if existing.is_admin:
            flash('Email này đã là tài khoản Admin trong hệ thống.', 'error')
        else:
            flash(f'Tài khoản "{existing.name}" ({email}) đã có sẵn. Vui lòng chọn mục "Thăng cấp Người dùng" để cấp quyền Admin.', 'warning')
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
        action=ADMIN_AUDIT_ACTIONS.get('CREATE_ADMIN', 'CREATE_ADMIN'),
        target_type='admin',
        target_id=new_admin.id,
        description=f"Tạo mới tài khoản Admin cấp dưới: {email} ({admin_role})"
    )
    
    flash(f'Thêm thành công Admin {name} với vai trò {admin_role.capitalize()}.', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/promote', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('manage_admins')
def admin_promote_admin():
    role = getattr(g, 'admin_role', None)
    if role != 'super_admin':
        flash('Chỉ Super Admin mới có quyền thăng cấp Admin.', 'error')
        return redirect(url_for('admin_admins'))
        
    user_id = request.form.get('user_id')
    admin_role = request.form.get('admin_role')
    
    if admin_role not in ['moderator', 'support', 'finance']:
        flash('Chức vụ không hợp lệ.', 'error')
        return redirect(url_for('admin_admins'))
        
    target_user = User.query.get_or_404(user_id)
    if target_user.is_admin:
        flash('Tài khoản này đã mang quyền Admin từ trước.', 'warning')
        return redirect(url_for('admin_admins'))
        
    target_user.is_admin = True
    target_user.admin_role = admin_role
    db.session.commit()
    
    _audit_log(
        action=ADMIN_AUDIT_ACTIONS.get('PROMOTE_TO_ADMIN', 'PROMOTE_TO_ADMIN'),
        target_type='admin',
        target_id=target_user.id,
        description=f"Thăng cấp người dùng {target_user.email} ({target_user.name}) thành Admin vai trò {admin_role}"
    )
    
    flash(f'Đã cấp quyền Admin ({admin_role.capitalize()}) cho tài khoản {target_user.name}!', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/<int:admin_id>/edit', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('manage_admins')
def admin_edit_admin(admin_id):
    role = getattr(g, 'admin_role', None)
    if role != 'super_admin':
        flash('Chỉ Super Admin mới có quyền chỉnh sửa thông tin Admin.', 'error')
        return redirect(url_for('admin_admins'))
        
    target_admin = User.query.get_or_404(admin_id)
    if getattr(target_admin, 'admin_role', None) == 'super_admin' and target_admin.id != session.get('admin_id'):
        flash('Không thể chỉnh sửa tài khoản Super Admin khác.', 'error')
        return redirect(url_for('admin_admins'))
        
    name = (request.form.get('name') or '').strip()
    new_role = request.form.get('admin_role')
    
    if getattr(target_admin, 'admin_role', None) != 'super_admin':
        if new_role not in ['moderator', 'support', 'finance']:
            flash('Vai trò phân quyền không hợp lệ.', 'error')
            return redirect(url_for('admin_admins'))
        old_role = target_admin.admin_role
        target_admin.admin_role = new_role
    else:
        old_role = 'super_admin'
        
    if name:
        target_admin.name = name
        
    db.session.commit()
    
    _audit_log(
        action=ADMIN_AUDIT_ACTIONS.get('CHANGE_PERMISSION', 'CHANGE_PERMISSION'),
        target_type='admin',
        target_id=target_admin.id,
        description=f"Cập nhật Admin {target_admin.email}: vai trò {old_role} -> {target_admin.admin_role}"
    )
    
    flash(f'Đã cập nhật thông tin Admin {target_admin.name} thành công.', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/<int:admin_id>/reset-password', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('manage_admins')
def admin_reset_admin_password(admin_id):
    role = getattr(g, 'admin_role', None)
    if role != 'super_admin':
        flash('Chỉ Super Admin mới có quyền đặt lại mật khẩu Admin cấp dưới.', 'error')
        return redirect(url_for('admin_admins'))
        
    target_admin = User.query.get_or_404(admin_id)
    if getattr(target_admin, 'admin_role', None) == 'super_admin' and target_admin.id != session.get('admin_id'):
        flash('Không thể đặt lại mật khẩu của Super Admin khác qua giao diện này.', 'error')
        return redirect(url_for('admin_admins'))
        
    new_password = (request.form.get('password') or '').strip()
    if len(new_password) < 8:
        flash('Mật khẩu mới phải có tối thiểu 8 ký tự.', 'error')
        return redirect(url_for('admin_admins'))
        
    target_admin.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    _audit_log(
        action=ADMIN_AUDIT_ACTIONS.get('ADMIN_PASSWORD_RESET', 'ADMIN_PASSWORD_RESET'),
        target_type='admin',
        target_id=target_admin.id,
        description=f"Đặt lại mật khẩu cho Admin: {target_admin.email}"
    )
    
    flash(f'Đã đặt lại mật khẩu mới cho Admin {target_admin.name} ({target_admin.email}) thành công.', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/<int:admin_id>/toggle', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('manage_admins')
def admin_toggle_admin_status(admin_id):
    role = getattr(g, 'admin_role', None)
    if role != 'super_admin':
        flash('Chỉ Super Admin mới có quyền khóa/mở khóa Admin.', 'error')
        return redirect(url_for('admin_admins'))
        
    target_admin = User.query.get_or_404(admin_id)
    if target_admin.id == session.get('admin_id'):
        flash('Không thể tự vô hiệu hóa tài khoản của chính mình.', 'error')
        return redirect(url_for('admin_admins'))
        
    if getattr(target_admin, 'admin_role', None) == 'super_admin':
        flash('Không thể vô hiệu hóa tài khoản Super Admin.', 'error')
        return redirect(url_for('admin_admins'))
        
    target_admin.is_active = not target_admin.is_active
    db.session.commit()
    
    if not target_admin.is_active:
        msg = f'Đã vô hiệu hóa tài khoản Admin {target_admin.name}'
        action_key = ADMIN_AUDIT_ACTIONS.get('ADMIN_ACCESS_BLOCKED', 'ADMIN_ACCESS_BLOCKED')
    else:
        msg = f'Đã kích hoạt lại tài khoản Admin {target_admin.name}'
        action_key = ADMIN_AUDIT_ACTIONS.get('ADMIN_ACCESS_RESTORED', 'ADMIN_ACCESS_RESTORED')
        
    _audit_log(
        action=action_key,
        target_type='admin',
        target_id=target_admin.id,
        description=f'{msg}: {target_admin.email}'
    )
    
    flash(msg, 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/<int:admin_id>/revoke', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('manage_admins')
def admin_revoke_admin_status(admin_id):
    role = getattr(g, 'admin_role', None)
    if role != 'super_admin':
        flash('Chỉ Super Admin mới có quyền thu hồi tư cách Admin.', 'error')
        return redirect(url_for('admin_admins'))
        
    target_admin = User.query.get_or_404(admin_id)
    if target_admin.id == session.get('admin_id'):
        flash('Không thể tự thu hồi tư cách Admin của chính mình.', 'error')
        return redirect(url_for('admin_admins'))
        
    if getattr(target_admin, 'admin_role', None) == 'super_admin':
        flash('Không thể thu hồi tư cách của Super Admin.', 'error')
        return redirect(url_for('admin_admins'))
        
    target_admin.is_admin = False
    target_admin.admin_role = None
    if target_admin.role == 'admin':
        target_admin.role = 'user'
    db.session.commit()
    
    _audit_log(
        action=ADMIN_AUDIT_ACTIONS.get('ADMIN_PRIVILEGES_REVOKED', 'ADMIN_PRIVILEGES_REVOKED'),
        target_type='admin',
        target_id=target_admin.id,
        description=f'Đã thu hồi tư cách Admin vĩnh viễn: {target_admin.email}'
    )
    
    flash(f'Đã thu hồi tư cách Admin vĩnh viễn khỏi tài khoản {target_admin.name} ({target_admin.email}).', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/<int:admin_id>/activity')
@admin_login_required
@require_permission('manage_admins')
def admin_admin_activity(admin_id):
    target_admin = User.query.get_or_404(admin_id)
    logs = AdminAuditLog.query.filter_by(admin_id=admin_id).order_by(AdminAuditLog.created_at.desc()).limit(20).all()
    return jsonify({
        'success': True,
        'admin_name': target_admin.name,
        'admin_email': target_admin.email,
        'admin_role': target_admin.admin_role,
        'logs': [{
            'id': l.id,
            'action': l.action,
            'description': l.description or '',
            'ip_address': l.ip_address or '—',
            'created_at': l.created_at.strftime('%d/%m/%Y %H:%M:%S') if l.created_at else ''
        } for l in logs]
    })

@app.route('/admin/search')
@admin_login_required
@require_permission('view_dashboard')
def admin_search():
    q = request.args.get('q', '').strip()
    results = {'users': [], 'jobs': [], 'contracts': []}
    
    if len(q) >= 2:
        from admin_auth import _has_permission
        role = getattr(g, 'admin_role', None)
        
        # Search users
        if _has_permission(role, 'view_users'):
            results['users'] = User.query.filter(
                db.or_(
                    User.name.ilike(f'%{q}%'),
                    User.email.ilike(f'%{q}%')
                )
            ).limit(20).all()
        
        # Search jobs
        if _has_permission(role, 'view_jobs'):
            results['jobs'] = Job.query.filter(
                db.or_(
                    Job.title.ilike(f'%{q}%'),
                    Job.description.ilike(f'%{q}%')
                )
            ).limit(20).all()
        
        # Search contracts (by ID if numeric)
        if _has_permission(role, 'view_contracts'):
            if q.isdigit():
                c = Contract.query.get(int(q))
                if c:
                    results['contracts'].append(c)
                
    return render_template('admin_search.html', query=q, results=results)

# ─── NOTIFICATION API & PREFERENCES ─────────────────────────────────────────

def is_notification_allowed(user_id, notification_type):
    """
    Kiểm tra cài đặt NotificationSetting của người dùng trước khi tạo bản ghi thông báo mới.
    Cấu hình này làm điều kiện kiểm tra (flag) trước khi hệ thống tạo bản ghi thông báo mới vào Notification Center.
    """
    try:
        from models import NotificationSetting
        setting = NotificationSetting.query.filter_by(user_id=user_id).first()
        if not setting:
            return True

        ntype = str(notification_type or '').upper()

        # 1. Nhóm Công việc
        if ntype in ('JOB_MATCH', 'NEW_JOB_MATCH', 'JOB_INVITATION', 'MATCHING_JOB'):
            return bool(setting.notify_job_match) if setting.notify_job_match is not None else True

        if ntype in ('JOB_APPLICATION', 'APPLICATION_COUNT', 'PROPOSAL_ACCEPTED', 'PROPOSAL_REJECTED',
                     'PROPOSAL_UPDATE', 'APPLICATION_STATUS', 'CONTRACT_CREATED', 'CONTRACT_COMPLETED'):
            return bool(setting.notify_application_update) if setting.notify_application_update is not None else True

        if ntype in ('PROFILE_VIEW', 'PROFILE_VIEWED', 'PROFILE_VISIT'):
            return bool(setting.notify_profile_view) if setting.notify_profile_view is not None else True

        # 2. Nhóm Lịch trình
        if ntype in ('SCHEDULE_REMINDER', 'BOOKING_REMINDER', 'APPOINTMENT_REMINDER', 'TRANSLATOR_SCHEDULE_REMINDER'):
            return bool(setting.notify_schedule_reminder) if setting.notify_schedule_reminder is not None else True

        # 3. Nhóm Thu nhập
        if ntype in ('PAYMENT', 'PAYMENT_RELEASED', 'PAYMENT_REFUNDED', 'PAYOUT', 'PAYOUT_UPDATE',
                     'INCOME_UPDATE', 'ESCROW_RELEASE', 'PAYMENT_RECEIVED'):
            return bool(setting.notify_income_update) if setting.notify_income_update is not None else True

        # 4. Nhóm Bảo mật & Hệ thống: Luôn BẬT và KHÓA không cho tắt
        if ntype in ('SECURITY_ALERT', 'LOGIN_ALERT', 'PASSWORD_CHANGED', 'SECURITY_WARNING',
                     'UNUSUAL_LOGIN', 'DEVICE_LOGIN', 'VERIFICATION_REQUIRED', 'VERIFICATION_SUBMITTED',
                     'VERIFICATION_RESUBMITTED', 'VERIFICATION_NEEDS_REVISION', 'VERIFICATION_APPROVED',
                     'VERIFICATION_REJECTED', 'VERIFICATION_POLICY_UPDATE_REQUIRED'):
            return True

        # Tiếp thị / Khuyến mại
        if ntype in ('MARKETING', 'PROMOTION', 'PLATFORM_EVENT'):
            return bool(setting.notify_marketing) if setting.notify_marketing is not None else False

        return True
    except Exception as e:
        print(f"[Notification Flag Check Error] {e}", file=sys.stderr)
        return True


def create_notification(user_id, notification_type, title, message, url=None, related_job_id=None, related_contract_id=None, related_review_id=None, related_proposal_id=None, force=False):
    """Tạo thông báo. Nếu đã có thông báo CHƯA ĐỌC cùng người nhận/loại/liên kết thì làm mới thay vì tạo thêm
    (một sự kiện xử lý nhiều lần, hoặc nhiều tin nhắn liên tiếp, chỉ cho một thông báo).
    Kiểm tra điều kiện cấu hình (flag) trong NotificationSetting trước khi ghi vào Notification Center."""
    if not force and not is_notification_allowed(user_id, notification_type):
        return None

    from models import Notification
    existing = Notification.query.filter_by(
        user_id=user_id, type=notification_type, is_read=False, url=url,
        related_job_id=related_job_id, related_contract_id=related_contract_id,
        related_review_id=related_review_id, related_proposal_id=related_proposal_id).first()
    if existing:
        existing.title = title
        existing.message = message
        existing.created_at = datetime.utcnow()
        return existing
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


@app.route('/api/account/notification-settings', methods=['GET', 'POST', 'PATCH'])
@login_required
def api_notification_settings():
    """API lấy và cập nhật cài đặt cấu hình thông báo (Notification Preferences)."""
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        return jsonify({'success': False, 'message': 'Không tìm thấy người dùng'}), 404

    setting = get_user_notification_setting(user)
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'settings': setting.to_dict()
        })

    return save_notification_settings_action(user)


# ─── BẢO MẬT TÀI KHOẢN & QUẢN LÝ PHIÊN (MỤC 5.6.2 & 5.6.3) ───────────────────

@app.route('/api/account/change-password', methods=['POST'])
@login_required
def api_account_change_password():
    """API đổi mật khẩu tài khoản an toàn (Mục 5.6.2)."""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Không tìm thấy thông tin tài khoản'}), 404

    data = request.get_json(silent=True) or request.form
    old_pw = (data.get('old_password') or '').strip()
    new_pw = (data.get('new_password') or '').strip()
    confirm_pw = (data.get('confirm_password') or '').strip()

    from services.account_security import change_user_password
    success, msg = change_user_password(user, old_pw, new_pw, confirm_pw)
    if not success:
        return jsonify({'success': False, 'message': msg}), 400

    return jsonify({'success': True, 'message': msg})


@app.route('/api/account/sessions', methods=['GET'])
@login_required
def api_account_sessions():
    """API lấy danh sách phiên đăng nhập của người dùng (Mục 5.6.3)."""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Không tìm thấy thông tin tài khoản'}), 404

    from services.account_security import get_active_sessions
    current_token = session.get('session_token')
    sessions = get_active_sessions(user, current_token)
    return jsonify({
        'success': True,
        'sessions': sessions,
        'total': len(sessions)
    })


@app.route('/api/account/sessions/revoke', methods=['POST'])
@login_required
def api_account_revoke_session():
    """API thu hồi / hủy một phiên làm việc cụ thể ở backend (Mục 5.6.3)."""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Không tìm thấy thông tin tài khoản'}), 404

    data = request.get_json(silent=True) or request.form
    target_id = data.get('session_id') or data.get('id')
    if not target_id:
        return jsonify({'success': False, 'message': 'Thiếu mã định danh phiên làm việc.'}), 400

    current_token = session.get('session_token')
    from services.account_security import revoke_user_session
    success, msg, is_current = revoke_user_session(user.id, target_id, current_token)
    if not success:
        return jsonify({'success': False, 'message': msg}), 400

    if is_current:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Bạn đã đăng xuất khỏi thiết bị này thành công.',
            'is_current': True,
            'redirect_url': url_for('login')
        })

    return jsonify({
        'success': True,
        'message': msg,
        'is_current': False
    })


@app.route('/api/account/sessions/revoke-others', methods=['POST'])
@login_required
def api_account_revoke_other_sessions():
    """API thu hồi / đăng xuất toàn bộ các thiết bị khác ở backend (Mục 5.6.3)."""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Không tìm thấy thông tin tài khoản'}), 404

    current_token = session.get('session_token')
    from services.account_security import revoke_all_other_sessions
    success, msg, count = revoke_all_other_sessions(user.id, current_token)
    if not success:
        return jsonify({'success': False, 'message': msg}), 400

    return jsonify({
        'success': True,
        'message': msg,
        'revoked_count': count
    })

@app.route('/notifications')
@login_required
def notifications_page():
    return render_template('notifications.html')

@app.route('/api/notifications', methods=['GET'])
@login_required
def api_get_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    filter_type = request.args.get('filter') or request.args.get('category')
    from models import Notification, VERIFICATION_NOTIFICATION_TYPES
    from services.verification import VERIFICATION_NOTIF_CONFIG
    from sqlalchemy import or_

    query = Notification.query.filter_by(user_id=session['user_id'])
    if filter_type:
        filter_type = filter_type.strip().lower()
        if filter_type == 'verification':
            query = query.filter(or_(
                Notification.type.in_(VERIFICATION_NOTIFICATION_TYPES),
                Notification.type.like('VERIFICATION_%')
            ))
        elif filter_type == 'job':
            query = query.filter(or_(
                Notification.type.like('%JOB%'),
                Notification.type.like('PROPOSAL%')
            ))
        elif filter_type == 'message':
            query = query.filter(Notification.type.like('%MESSAGE%'))
        elif filter_type == 'contract':
            query = query.filter(or_(
                Notification.type.like('%CONTRACT%'),
                Notification.type.like('PAYMENT%'),
                Notification.type.like('PROJECT%'),
                Notification.type.like('DELIVERABLE%'),
                Notification.type.like('REVISION%')
            ))
        elif filter_type == 'review':
            query = query.filter(Notification.type.like('%REVIEW%'))
        elif filter_type == 'unread':
            query = query.filter_by(is_read=False)

    pagination = query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for n in pagination.items:
        vcfg = VERIFICATION_NOTIF_CONFIG.get(n.type) if n.type in VERIFICATION_NOTIF_CONFIG else None
        item_data = {
            'id': n.id,
            'type': n.type,
            'title': n.title,
            'message': n.message,
            'url': n.url or (vcfg.get('default_url') if vcfg else None),
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat() if n.created_at else None
        }
        if vcfg:
            item_data['category'] = vcfg.get('category', 'verification')
            item_data['type_label'] = vcfg.get('label', 'Xác minh hồ sơ')
            item_data['badge_class'] = vcfg.get('badge_class', 'bg-blue-50 text-blue-700 border-blue-200')
            item_data['icon_kind'] = vcfg.get('icon_kind', 'submitted')
            item_data['action_label'] = vcfg.get('action_label', 'Xem chi tiết')
            item_data['severity'] = vcfg.get('severity', 'info')
        items.append(item_data)

    return jsonify({
        'notifications': items,
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
# ─── CLIENT DASHBOARD ──────────────────────────────────────────────────────────

JOB_STATUS_LABELS = {'open': 'Đang mở', 'pending': 'Chờ duyệt', 'archived': 'Đã lưu trữ', 'closed': 'Đã đóng', 'cancelled': 'Đã hủy',
                     'contracted': 'Đã chọn phiên dịch viên', 'in_progress': 'Đang thực hiện', 'completed': 'Hoàn tất'}
CONTRACT_STATUS_LABELS = {'escrow_pending': 'Chờ thanh toán Escrow', 'awaiting_translator': 'Chờ phiên dịch viên xác nhận',
                          'revision_requested': 'Yêu cầu chỉnh sửa', 'in_progress': 'Đang thực hiện',
                          'completed': 'Hoàn tất', 'cancelled': 'Đã huỷ'}


def build_client_dashboard(user):
    """Gom dữ liệu dashboard của một khách thuê (chỉ dữ liệu thuộc user.id)."""
    from models import Notification
    uid = user.id

    open_jobs = Job.query.filter_by(hirer_id=uid, status='open').count()
    new_proposals = Notification.query.filter_by(user_id=uid, type='JOB_APPLICATION', is_read=False).count()
    in_progress = Contract.query.filter_by(hirer_id=uid, status='in_progress').count()

    # Chờ nghiệm thu = hợp đồng đang thực hiện đã có tài liệu bàn giao
    awaiting_contracts = Contract.query.filter(
        Contract.hirer_id == uid, Contract.status == 'in_progress',
        Contract.deliverables.any()
    ).order_by(Contract.updated_at.desc()).all()
    escrow_pending = Contract.query.filter_by(hirer_id=uid, status='escrow_pending') \
        .order_by(Contract.created_at.desc()).all()

    dm_unread = DirectMessage.query.filter_by(receiver_id=uid, is_read=False).count()
    contract_ids = [c.id for c in Contract.query.with_entities(Contract.id).filter_by(hirer_id=uid).all()]
    contract_unread = Message.query.filter(
        Message.contract_id.in_(contract_ids), Message.sender_id != uid, Message.is_read == False
    ).count() if contract_ids else 0
    unread_messages = dm_unread + contract_unread

    # Yêu cầu gần đây
    jobs = Job.query.filter_by(hirer_id=uid).order_by(Job.created_at.desc()).limit(5).all()
    counts = {}
    if jobs:
        counts = dict(db.session.query(Proposal.job_id, db.func.count(Proposal.id))
                      .filter(Proposal.job_id.in_([j.id for j in jobs])).group_by(Proposal.job_id).all())
    lang = session.get('lang') or request.cookies.get('lang') or 'vi'
    recent_requests = [{
        'title': j.title,
        'language_pair': ' → '.join(x for x in (j.source_lang, j.target_lang) if x),
        'service': j.display_category_text(lang),
        'created_at': j.created_at.strftime('%d/%m/%Y') if j.created_at else '',
        'proposal_count': counts.get(j.id, 0),
        'status': j.status,
        'status_label': job_status_label(j),
        'url': url_for('job_detail', job_id=j.id),
    } for j in jobs]

    # Dự án gần đây
    contracts = Contract.query.filter_by(hirer_id=uid).order_by(Contract.created_at.desc()).limit(5).all()
    recent_projects = []
    for c in contracts:
        deadline = c.job.deadline.strftime('%d/%m/%Y') if c.job and c.job.deadline else (c.scheduled_date or '')
        recent_projects.append({
            'title': c.job.title if c.job else (c.service.name if c.service else f'Hợp đồng #{c.id}'),
            'translator': c.translator.name if c.translator else '',
            'deadline': deadline,
            'status': c.status,
            'status_label': CONTRACT_STATUS_LABELS.get(c.status, c.status or ''),
            'url': url_for('project_detail', contract_id=c.id),
        })

    # Hoạt động gần đây: chỉ các thông báo hệ thống thực sự lưu
    notifs = Notification.query.filter_by(user_id=uid).order_by(Notification.created_at.desc()).limit(8).all()
    activities = [{
        'title': n.title, 'message': n.message, 'type': n.type, 'is_read': bool(n.is_read),
        'created_at': n.created_at.strftime('%d/%m/%Y %H:%M') if n.created_at else '',
        'url': n.url or url_for('notifications_page'),
    } for n in notifs]

    # Việc cần xử lý (chỉ hiện khi điều kiện thực tế đúng)
    tasks = []
    if new_proposals:
        first = Notification.query.filter_by(user_id=uid, type='JOB_APPLICATION', is_read=False) \
            .order_by(Notification.created_at.desc()).first()
        tasks.append({'title': f'Xem {new_proposals} báo giá mới',
                      'desc': 'Phiên dịch viên vừa ứng tuyển vào yêu cầu của bạn.',
                      'url': (first.url if first and first.url else url_for('my_jobs')),
                      'cta': 'Xem báo giá', 'level': 'info'})
    for c in awaiting_contracts:
        name = c.job.title if c.job else f'Hợp đồng #{c.id}'
        tasks.append({'title': f'Nghiệm thu: {name}', 'desc': 'Phiên dịch viên đã bàn giao tài liệu, đang chờ bạn xác nhận.',
                      'url': url_for('project_detail', contract_id=c.id), 'cta': 'Nghiệm thu', 'level': 'warn'})
    for c in escrow_pending:
        name = c.job.title if c.job else f'Hợp đồng #{c.id}'
        tasks.append({'title': f'Thanh toán Escrow: {name}', 'desc': 'Hoàn tất thanh toán để dự án được bắt đầu.',
                      'url': url_for('payment_mockup', contract_id=c.id), 'cta': 'Thanh toán', 'level': 'warn'})
    if unread_messages:
        tasks.append({'title': f'{unread_messages} tin nhắn chưa đọc', 'desc': 'Phản hồi phiên dịch viên để dự án không bị chậm.',
                      'url': url_for('messages_page'), 'cta': 'Mở tin nhắn', 'level': 'info'})
    hp = user.hirer_profile
    if not user.phone or not hp or not (hp.company and hp.location):
        tasks.append({'title': 'Bổ sung thông tin hồ sơ', 'desc': 'Hồ sơ đầy đủ giúp phiên dịch viên tin tưởng bạn hơn.',
                      'url': url_for('account_profile'), 'cta': 'Cập nhật hồ sơ', 'level': 'neutral'})

    return {
        'stats': {
            'open_requests': open_jobs, 'new_proposals': new_proposals, 'in_progress': in_progress,
            'awaiting_acceptance': len(awaiting_contracts), 'unread_messages': unread_messages,
        },
        'recent_requests': recent_requests,
        'recent_projects': recent_projects,
        'activities': activities,
        'tasks': tasks,
    }


EMPTY_DASHBOARD = {
    'stats': {'open_requests': 0, 'new_proposals': 0, 'in_progress': 0, 'awaiting_acceptance': 0, 'unread_messages': 0},
    'recent_requests': [], 'recent_projects': [], 'activities': [], 'tasks': [],
}


@app.route('/dashboard')
@login_required
def client_dashboard():
    user = get_current_user()
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('index'))
    if user.role != 'hirer':
        flash(_t('flash.hirer_only_post'), 'error')
        return redirect(url_for('index'))
    return render_template('client_dashboard.html', user=user)


@app.route('/api/dashboard/summary')
@login_required
def api_dashboard_summary():
    user = get_current_user()
    if not user or user.role != 'hirer':
        return jsonify({'error': 'forbidden'}), 403
    if isinstance(user.id, str):  # tài khoản MongoDB: chưa có dữ liệu SQL
        return jsonify(EMPTY_DASHBOARD)
    try:
        return jsonify(build_client_dashboard(user))
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"[dashboard SQLError] {e}")
        return jsonify({'error': 'db_error'}), 500


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
                    'specialty': getattr(job, 'specialty', '') or '',
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
    if not translator.profile or not translator.profile.is_verified:
        return jsonify({'status': 'error', 'message': 'Phiên dịch viên chưa được xác minh hồ sơ.'}), 400
        
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


# ─── PHÂN HỆ TRỢ GIÚP & HỖ TRỢ (MỤC 5.7) ──────────────────────────────────────

@app.route('/account/support/tickets/create', methods=['POST'])
@login_required
def create_support_ticket_endpoint():
    """
    Endpoint tạo yêu cầu hỗ trợ mới (Mục 5.7.3).
    Hỗ trợ cả gửi qua AJAX (FormData có tệp ảnh) lẫn Form POST truyền thống.
    Tái sử dụng File Upload Service từ module KYC để xử lý ảnh đính kèm.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Không tìm thấy thông tin tài khoản.'}), 401
        flash('Không tìm thấy thông tin tài khoản.', 'error')
        return redirect(url_for('login'))

    is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
               'application/json' in request.headers.get('Accept', '') or 
               request.is_json)

    category = request.form.get('category')
    title = request.form.get('title')
    description = request.form.get('description')
    attachment_file = (request.files.get('attachment') or 
                       request.files.get('screenshot') or 
                       request.files.get('file'))

    from services.account_support import create_support_ticket
    ok, ticket, err = create_support_ticket(
        user=user,
        category=category,
        title=title,
        description=description,
        attachment_file=attachment_file
    )

    if not ok:
        if is_ajax:
            return jsonify({'success': False, 'message': err}), 400
        flash(err, 'error')
        return redirect(url_for('account_profile') + '?tab=support')

    success_msg = f'Đã gửi yêu cầu hỗ trợ #{ticket.ticket_code} thành công! Ban Quản trị sẽ tiếp nhận và phản hồi sớm.'
    if is_ajax:
        return jsonify({
            'success': True,
            'message': success_msg,
            'ticket': ticket.to_dict()
        }), 201

    flash(success_msg, 'success')
    return redirect(url_for('account_profile') + '?tab=support')


@app.route('/account/support/tickets/<string:ticket_code>', methods=['GET'])
@login_required
def get_support_ticket_endpoint(ticket_code):
    """
    Endpoint lấy chi tiết ticket và khung xem phản hồi từ Ban Quản trị (Mục 5.7.3).
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        return jsonify({'success': False, 'message': 'Không tìm thấy thông tin tài khoản.'}), 401

    from services.account_support import get_ticket_by_code
    ticket, err = get_ticket_by_code(ticket_code, user)
    if not ticket:
        status_code = 404 if 'Không tìm thấy' in (err or '') else 403
        return jsonify({'success': False, 'message': err}), status_code

    return jsonify({
        'success': True,
        'ticket': ticket.to_dict()
    }), 200


@app.route('/account/support/attachment/<path:filename>')
@login_required
def view_support_attachment(filename):
    """
    Endpoint xem / tải ảnh chụp màn hình minh chứng của ticket hỗ trợ.
    Tái sử dụng Private Storage từ KYC (get_private_verification_folder).
    Kiểm tra bảo mật RBAC: Chỉ người tạo ticket hoặc Quản trị viên mới được phép truy cập.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        abort(401)

    clean_filename = os.path.basename(filename)

    # Kiểm tra quyền truy cập ở cấp cơ sở dữ liệu
    if getattr(user, 'role', '') != 'admin':
        ticket = SupportTicket.query.filter(
            SupportTicket.user_id == user.id,
            SupportTicket.attachment_url.like(f"%{clean_filename}%")
        ).first()
        if not ticket:
            abort(403)

    from services.verification import get_private_verification_folder
    file_path = os.path.join(get_private_verification_folder(), clean_filename)
    if not os.path.exists(file_path):
        abort(404)

    ext = clean_filename.rsplit('.', 1)[-1].lower() if '.' in clean_filename else ''
    mimetype = 'application/pdf' if ext == 'pdf' else (f'image/{ext}' if ext in ('png', 'jpeg', 'jpg', 'webp') else 'application/octet-stream')

    response = send_file(
        file_path,
        as_attachment=False,
        download_name=clean_filename,
        mimetype=mimetype
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'private, max-age=3600'
    return response


@app.route('/account/support/policy/<string:doc_key>', methods=['GET'])
@login_required
def get_support_policy_doc(doc_key):
    """
    Endpoint lấy toàn văn điều khoản / chính sách (chỉ xem / read-only) (Mục 5.7.2).
    """
    from services.account_support import POLICY_DOCUMENTS
    doc = next((d for d in POLICY_DOCUMENTS if d['key'] == doc_key), None)
    if not doc:
        return jsonify({'success': False, 'message': 'Không tìm thấy tài liệu điều khoản.'}), 404

    return jsonify({
        'success': True,
        'document': doc
    }), 200


@app.route('/account/support/tickets/<string:ticket_code>/reply', methods=['POST'])
@login_required
def reply_support_ticket_endpoint(ticket_code):
    """
    Endpoint phản hồi ticket hỗ trợ từ Ban Quản trị / Quản trị viên.
    """
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        return jsonify({'success': False, 'message': 'Không tìm thấy tài khoản.'}), 401

    if getattr(user, 'role', '') != 'admin':
        return jsonify({'success': False, 'message': 'Chỉ Ban Quản trị mới có quyền gửi phản hồi chính thức.'}), 403

    data = request.get_json(silent=True) or request.form
    reply_text = data.get('reply_text') or data.get('message') or ''
    new_status = data.get('status', 'resolved')

    from services.account_support import admin_respond_to_ticket
    ok, ticket, err = admin_respond_to_ticket(ticket_code, reply_text, new_status)
    if not ok:
        return jsonify({'success': False, 'message': err}), 400

    return jsonify({
        'success': True,
        'message': f'Đã gửi phản hồi cho ticket #{ticket.ticket_code} thành công!',
        'ticket': ticket.to_dict()
    }), 200


# Khiếu nại đơn thuê (routes: /disputes, /dispute/<id>, /admin/disputes...)
import disputes as _disputes
_disputes.register(app)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
