import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort, Response, g, send_from_directory, send_file
from models import db, User, TranslatorProfile, HirerProfile, TranslatorPreference, Service, Job, Proposal, Contract, Message, DirectMessage, Deliverable, Review, LANGUAGES, LoginAttempt, AdminAuditLog, ADMIN_AUDIT_ACTIONS, Report, PaymentTransaction, AdminNotification, TranslatorSchedule, JobSchedule, get_job_schedule_entries, validate_schedule_entries, VerificationDocument, TranslatorVerification
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
    if os.environ.get('VERCEL') == '1' or os.environ.get('RENDER'):
        # TASK 10: Production (Vercel/Render) — BẮT BUỘC có DATABASE_URL trỏ tới Supabase PostgreSQL.
        # Không fallback sang SQLite memory trong production.
        _platform = 'Vercel' if os.environ.get('VERCEL') else 'Render'
        error_msg = (
            f"[CRITICAL] Chạy trên {_platform} nhưng DATABASE_URL chưa được cấu hình! "
            "Database production phải là Supabase PostgreSQL. "
            "Hãy vào Dashboard → Environment Variables → thêm DATABASE_URL."
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

UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
if os.environ.get('VERCEL') == '1' or _is_memory_db:
    UPLOAD_FOLDER = '/tmp'
else:
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except OSError:
        UPLOAD_FOLDER = '/tmp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

AVATAR_UPLOAD_FOLDER = os.path.join('static', 'uploads', 'avatars')
if os.environ.get('VERCEL') == '1' or _is_memory_db:
    AVATAR_UPLOAD_FOLDER = '/tmp/avatars'
try:
    os.makedirs(AVATAR_UPLOAD_FOLDER, exist_ok=True)
except OSError:
    AVATAR_UPLOAD_FOLDER = '/tmp'
app.config['AVATAR_UPLOAD_FOLDER'] = AVATAR_UPLOAD_FOLDER

# Thư mục lưu trữ tài liệu riêng tư (Private Storage - Hoàn toàn ngoài static webroot)
PRIVATE_STORAGE_FOLDER = os.getenv('PRIVATE_STORAGE_FOLDER', os.path.join(basedir, 'instance', 'storage', 'private_verifications'))
if os.environ.get('VERCEL') == '1' or _is_memory_db:
    PRIVATE_STORAGE_FOLDER = '/tmp/private_verifications'
try:
    os.makedirs(PRIVATE_STORAGE_FOLDER, exist_ok=True)
except OSError:
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

    import time
    clean_uid = str(user_id)
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"avatar_u{clean_uid}_{int(time.time())}.{ext}"
    folder = app.config.get('AVATAR_UPLOAD_FOLDER', os.path.join('static', 'uploads', 'avatars'))
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    try:
        if current_avatar and not current_avatar.startswith('http') and not current_avatar.startswith('/static/avatars/'):
            old_base = os.path.basename(current_avatar)
            old_path = os.path.join(folder, old_base)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass
        file.save(filepath)
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
    folder = os.path.join(app.root_path, 'static', 'uploads', 'certificates')
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
        return
    folder = app.config.get('AVATAR_UPLOAD_FOLDER', os.path.join('static', 'uploads', 'avatars'))
    if not current_avatar.startswith('http') and not current_avatar.startswith('/static/avatars/'):
        old_base = os.path.basename(current_avatar)
        old_path = os.path.join(folder, old_base)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

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
        # Tự động thêm cột image_url nếu DB đã tồn tại từ trước chưa có cột này
        from sqlalchemy import text
        with db.engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE message ADD COLUMN image_url TEXT"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE direct_message ADD COLUMN image_url TEXT"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE message ALTER COLUMN image_url TYPE TEXT"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE direct_message ALTER COLUMN image_url TYPE TEXT"))
                conn.commit()
            except Exception:
                pass
    except Exception as e:
        print(f"[DB] db.create_all() error: {e}", file=sys.stderr)
        return

    # Tự động đồng bộ cột avatar nếu chưa tồn tại trong bảng user
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'user' in inspector.get_table_names():
            user_cols = [c['name'] for c in inspector.get_columns('user')]
            if 'avatar' not in user_cols:
                with db.engine.connect() as conn:
                    try:
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN avatar VARCHAR(255)'))
                        conn.commit()
                    except Exception:
                        conn.execute(text('ALTER TABLE user ADD COLUMN avatar VARCHAR(255)'))
                        conn.commit()
    except Exception:
        pass

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
        from models import TranslatorVerification
        badges['admin_badge_pending_translators'] = TranslatorProfile.query.filter_by(is_verified=False).count()
        badges['admin_badge_pending_verifications'] = TranslatorVerification.query.filter_by(status='pending').count()
        badges['admin_badge_flagged_jobs'] = Job.query.filter_by(is_flagged=True).count()
        badges['admin_badge_reports'] = Report.query.filter_by(status='new').count()
        badges['admin_badge_notifications'] = AdminNotification.query.filter_by(is_read=False).count()
    except SQLAlchemyError:
        badges = {
            'admin_badge_pending_translators': 0,
            'admin_badge_pending_verifications': 0,
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
        return User.query.get(uid)
    except SQLAlchemyError as e:
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
    latest_jobs = Job.query.filter(Job.status == 'open', db.or_(Job.is_flagged == False, Job.is_flagged == None)).order_by(Job.created_at.desc()).limit(4).all()
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
    # Login dùng SQL only.
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        try:
            user = User.query.filter_by(email=email).first()
            if user:
                if not user.is_active:
                    flash(_t('flash.account_locked'), 'error')
                    return render_template('login.html', email=email)
                if check_password_hash(user.password_hash, password):
                    session.clear()
                    session.permanent = True
                    session['user_id'] = user.id  # SQL integer ID
                    flash(_t('flash.login_success'), 'success')
                    # TASK 4A: Role redirect
                    if user.is_admin:
                        return redirect(url_for('admin_dashboard'))
                    return redirect(url_for('index'))
                else:
                    flash(_t('flash.invalid_password'), 'error')
                    return render_template('login.html', email=email)
            else:
                flash(_t('flash.account_not_found'), 'error')
                return render_template('login.html', email=email)
        except SQLAlchemyError as e:
            print(f"[AUTH SQL ERROR] {e}")
            flash(_t('flash.system_overload'), 'error')
            return render_template('login.html', email=email)
        except Exception as e:
            print(f"[AUTH ERROR] {e}")
            flash(_t('flash.db_error'), 'error')
            return render_template('login.html', email=email)

    return render_template('login.html')

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

            db.session.commit()
            flash(_t('flash.register_success'), 'success')
            return redirect(url_for('login'))
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

@app.route('/logout')
def logout():
    session.clear()
    flash(_t('flash.logout_success'), 'success')
    return redirect(url_for('index'))

# ─── ACCOUNT & PROFILE OVERVIEW ───────────────────────────────────────────────

def compute_profile_completion(user):
    """Tính toán tiến độ hoàn thiện hồ sơ thực tế của phiên dịch viên dựa trên dữ liệu thực tế."""
    if not user or getattr(user, 'role', '') != 'translator':
        return None

    prof = getattr(user, 'profile', None)
    verif = getattr(user, 'latest_verification', None)

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
            'completed': bool(prof and getattr(prof, 'services', None) and len(prof.services) > 0),
            'action_tab': 'translator',
            'desc': 'Thiết lập bảng giá dịch vụ để khách hàng có thể đặt trực tiếp.'
        },
        {
            'key': 'verification',
            'title': 'Hồ sơ xác minh & CV',
            'completed': bool(prof and (prof.is_verified or (verif and verif.status in ('pending', 'approved', 'verified')))),
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
        if verif.status in ('approved', 'verified'):
            verification_state = 'verified'
        elif verif.status in ('pending', 'in_review'):
            verification_state = 'pending'
        elif verif.status in ('needs_revision', 'revision_requested'):
            verification_state = 'needs_revision'
        elif verif.status == 'draft':
            verification_state = 'draft'
        elif verif.status == 'rejected':
            verification_state = 'rejected'
        else:
            verification_state = verif.status
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


@app.route('/account', methods=['GET', 'POST'])
@app.route('/account/profile', methods=['GET', 'POST'])
@app.route('/account/overview', methods=['GET', 'POST'])
@login_required
def account_profile():
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
    default_tab = 'overview' if getattr(user, 'role', '') == 'translator' else 'basic'
    if request.path == '/account/overview':
        default_tab = 'overview'
    active_tab = request.args.get('tab', default_tab)

    profile_completion = None
    unread_notifs_count = 0
    verification_documents = []
    from services.verification import DOCUMENT_POLICIES
    if getattr(user, 'role', '') == 'translator':
        from models import Notification
        try:
            unread_notifs_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
        except Exception:
            unread_notifs_count = 0
        profile_completion = compute_profile_completion(user)
        if user.latest_verification:
            verification_documents = [d for d in user.latest_verification.documents if d.is_active]

    return render_template(
        'account_profile.html',
        user=user,
        LANGUAGES=get_localized_languages(current_lang),
        active_tab=active_tab,
        profile_completion=profile_completion,
        unread_notifs_count=unread_notifs_count,
        verification_documents=verification_documents,
        DOCUMENT_POLICIES=DOCUMENT_POLICIES
    )


@app.route('/account/verification/submit', methods=['POST'])
@login_required
def submit_verification():
    """Nhận và xử lý hồ sơ xác minh phiên dịch viên (CV, chứng chỉ, thông tin năng lực)."""
    uid = session['user_id']
    user = User.query.get(uid)
    if not user:
        flash(_t('flash.account_not_found'), 'error')
        return redirect(url_for('account_profile'))

    from services.verification import submit_verification_request
    ok, msg = submit_verification_request(user, request.form, request.files)
    if ok:
        flash(msg, 'success')
    else:
        flash(msg, 'error')
    return redirect(url_for('account_profile') + '?tab=verification')


# ─── TRANSLATOR VERIFICATION DOCUMENTS (PRIVATE STORAGE & RBAC) ───────────────

@app.route('/account/verification/documents/upload', methods=['POST'])
@login_required
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

    from services.verification import can_user_access_document, get_private_verification_folder
    can_access, err = can_user_access_document(user, doc)
    if not can_access:
        abort(403)

    file_path = doc.storage_path
    if not file_path or not os.path.isabs(file_path):
        file_path = os.path.join(get_private_verification_folder(), doc.stored_filename)

    if not os.path.exists(file_path):
        fallback_path = os.path.join(get_private_verification_folder(), doc.stored_filename)
        if os.path.exists(fallback_path):
            file_path = fallback_path
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

    from services.verification import can_user_access_document, get_private_verification_folder
    can_access, err = can_user_access_document(user, doc)
    if not can_access:
        abort(403)

    file_path = doc.storage_path
    if not file_path or not os.path.isabs(file_path):
        file_path = os.path.join(get_private_verification_folder(), doc.stored_filename)

    if not os.path.exists(file_path):
        fallback_path = os.path.join(get_private_verification_folder(), doc.stored_filename)
        if os.path.exists(fallback_path):
            file_path = fallback_path
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
@login_required
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
@login_required
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
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': 'Bản nháp hồ sơ xác minh đã được lưu trữ an toàn! Bạn có thể xem lại hoặc chỉnh sửa bất kỳ lúc nào.',
                    'redirect_url': url_for('account_profile') + '?tab=verification'
                })
            flash('Bản nháp hồ sơ xác minh đã được lưu trữ an toàn trong tài khoản của bạn.', 'success')
            return redirect(url_for('account_profile') + '?tab=verification')

    # GET Request
    # Ưu tiên tham số URL ?step=X, nếu không thì lấy từ verification.current_step
    requested_step = request.args.get('step', type=int)
    active_step = requested_step if requested_step and 1 <= requested_step <= 6 else (verification.current_step or 1)
    
    current_lang = session.get('lang') or request.cookies.get('lang') or 'vi'
    draft_dict = verification.get_draft_dict()

    return render_template(
        'verification_form.html',
        user=user,
        verification=verification,
        draft=draft_dict,
        active_step=active_step,
        LANGUAGES=get_localized_languages(current_lang),
        current_year=datetime.utcnow().year
    )


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

@app.route('/my-schedule')
@login_required
def my_schedule():
    user = get_current_user()
    if not user or user.role != 'translator':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('index'))
    
    # Lấy các lịch sắp tới của phiên dịch viên
    schedules = TranslatorSchedule.query.filter(
        TranslatorSchedule.translator_id == user.id,
        TranslatorSchedule.status != 'cancelled'
    ).order_by(TranslatorSchedule.scheduled_date.asc(), TranslatorSchedule.start_time.asc()).all()
    
    return render_template('translator_schedule.html', user=user, schedules=schedules)

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
        latest_jobs = Job.query.filter(Job.status == 'open', db.or_(Job.is_flagged == False, Job.is_flagged == None)).order_by(Job.created_at.desc()).limit(4).all()
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
        'id': m.id, 'sender_id': m.sender_id, 'sender_name': m.sender.name if m.sender else '',
        'content': m.content, 'image_url': getattr(m, 'image_url', None),
        'time': m.created_at.strftime('%H:%M %d/%m') if m.created_at else ''
    } for m in msgs])

@app.route('/api/direct-messages/<int:other_user_id>', methods=['POST'])
@login_required
def send_direct_message(other_user_id):
    content = request.json.get('content', '').strip()
    image_url = request.json.get('image_url', '').strip()
    me = session['user_id']
    
    if (not content and not image_url) or other_user_id == me:
        return jsonify({'status': 'error'}), 400
        
    receiver = User.query.get(other_user_id)
    if not receiver:
        return jsonify({'status': 'error'}), 400
        
    msg = DirectMessage(
        sender_id=me, receiver_id=other_user_id,
        content=content or ('[Hình ảnh]' if image_url else ''),
        image_url=image_url or None
    )
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


CHAT_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_chat_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in CHAT_IMAGE_EXTENSIONS

@app.route('/api/chat/upload-image', methods=['POST'])
@login_required
def upload_chat_image():
    """Upload ảnh cho chat. Trả về URL ảnh đã lưu."""
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400

    if not allowed_chat_image(file.filename):
        return jsonify({'status': 'error', 'message': 'File type not allowed'}), 400

    # Nếu đang chạy trên môi trường Vercel hoặc filesystem tạm / read-only:
    # Trả về trực tiếp Base64 Data URI để lưu và hiển thị trực tiếp 100%,
    # không phụ thuộc vào filesystem ephemeral của serverless.
    if os.environ.get('VERCEL') == '1' or app.config.get('UPLOAD_FOLDER') == '/tmp':
        import base64
        ext = file.filename.rsplit('.', 1)[1].lower()
        mime_map = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}
        mime = mime_map.get(ext, 'image/jpeg')
        file_bytes = file.read()
        b64_str = base64.b64encode(file_bytes).decode('utf-8')
        image_url = f"data:{mime};base64,{b64_str}"
        return jsonify({'status': 'ok', 'image_url': image_url})

    # Môi trường server thường / local: Lưu vào static/uploads/chat_images
    chat_img_dir = os.path.join(basedir, 'static', 'uploads', 'chat_images')
    try:
        os.makedirs(chat_img_dir, exist_ok=True)
    except OSError:
        chat_img_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'chat_images')
        os.makedirs(chat_img_dir, exist_ok=True)

    # Tạo tên file duy nhất
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"chat_{session['user_id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.{ext}"
    filename = secure_filename(unique_name)
    filepath = os.path.join(chat_img_dir, filename)
    file.save(filepath)

    image_url = f'/static/uploads/chat_images/{filename}'
    return jsonify({'status': 'ok', 'image_url': image_url})


@app.route('/static/uploads/chat_images/<path:filename>')
def serve_chat_image(filename):
    """Phục vụ file ảnh chat trực tiếp để tránh lỗi 404."""
    chat_img_dir = os.path.join(basedir, 'static', 'uploads', 'chat_images')
    if os.path.exists(os.path.join(chat_img_dir, filename)):
        return send_from_directory(chat_img_dir, filename)
    if os.path.exists(os.path.join('/tmp', filename)):
        return send_from_directory('/tmp', filename)
    abort(404)


@app.route('/tmp/<path:filename>')
def serve_tmp_file(filename):
    """Phục vụ file từ thư mục /tmp nếu có."""
    if os.path.exists(os.path.join('/tmp', filename)):
        return send_from_directory('/tmp', filename)
    abort(404)


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

        # ── Collect Multi-day Schedule ──────────────────────────────
        scheduled_dates = request.form.getlist('scheduled_date[]')
        start_times = request.form.getlist('start_time[]')
        end_times = request.form.getlist('end_time[]')

        entries = []
        for d, st, et in zip(scheduled_dates, start_times, end_times):
            if d or st or et: # Bỏ qua các dòng trống hoàn toàn
                entries.append({
                    'scheduled_date': d,
                    'start_time': st,
                    'end_time': et
                })

        # Validate schedule
        from models import validate_schedule_entries
        is_valid, errors = validate_schedule_entries(entries)
        if not is_valid:
            for err in errors:
                flash(err['message'], 'error')
            return render_template('post_job.html', LANGUAGES=LANGUAGES, form_data=request.form)

        # Fallback for legacy fields (lấy ngày đầu tiên)
        legacy_date = entries[0]['scheduled_date'] if entries else ''
        legacy_start = entries[0]['start_time'] if entries else ''
        legacy_end = entries[0]['end_time'] if entries else ''

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
            event_date=legacy_date,
            event_time_start=legacy_start,
            event_time_end=legacy_end,
            event_location=request.form.get('event_location', ''),
            deadline=deadline,
            status='pending'
        )
        db.session.add(job)
        db.session.flush() # Để lấy job.id

        # Lưu chi tiết vào JobSchedule
        from models import JobSchedule
        from services.schedule import _parse_time
        for entry in entries:
            parsed_date = datetime.strptime(entry['scheduled_date'].strip(), '%Y-%m-%d').date()
            parsed_start = _parse_time(entry['start_time'].strip())
            parsed_end = _parse_time(entry['end_time'].strip())
            if parsed_date and parsed_start and parsed_end:
                js = JobSchedule(
                    job_id=job.id,
                    scheduled_date=parsed_date,
                    start_time=parsed_start,
                    end_time=parsed_end
                )
                db.session.add(js)

        db.session.commit()

        # Notify matching translators (safe, won't block job creation if fails)
        from services.matching import notify_matching_translators_for_new_job
        notify_matching_translators_for_new_job(job)

        flash(_t('flash.job_posted'), 'success')
        return redirect(url_for('job_detail', job_id=job.id))
        
    return render_template('post_job.html', LANGUAGES=LANGUAGES, form_data={})

@app.route('/jobs')
def job_list():
    lang = request.args.get('lang', '')
    budget = request.args.get('budget', '')
    sort = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = Job.query.filter(Job.status == 'open', db.or_(Job.is_flagged == False, Job.is_flagged == None))
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

    # ── 0. Access Control ─────────────────────────────────────────────────
    user = get_current_user()
    is_owner = user and (user.id == job.hirer_id)
    is_admin_user = session.get(ADMIN_SESSION_KEY) is not None

    if job.is_flagged or job.status == 'pending':
        if not (is_owner or is_admin_user):
            flash('Bài đăng này đang chờ duyệt hoặc đã bị khoá.', 'warning')
            return redirect(url_for('index'))

    if request.method == 'POST':
        # ── 1. Login & Role guard ─────────────────────────────────────────────
        user = get_current_user()
        if not user:
            flash(_t('flash.login_required'), 'warning')
            return redirect(url_for('login'))
        if user.role != 'translator':
            flash(_t('flash.translator_only_apply'), 'error')
            return redirect(url_for('job_detail', job_id=job.id))
            
        if job.status != 'open':
            flash(_t('flash.job_closed'), 'error')
            return redirect(url_for('job_detail', job_id=job.id))
            
        if user.id == job.hirer_id:
            flash(_t('flash.cannot_apply_own_job'), 'error')
            return redirect(url_for('job_detail', job_id=job.id))

        # ── 2. Duplicate proposal guard ───────────────────────────────────────
        existing_proposal = Proposal.query.filter_by(
            job_id=job.id, translator_id=session['user_id']
        ).first()
        if existing_proposal:
            flash(_t('flash.already_applied'), 'warning')
            return redirect(url_for('job_detail', job_id=job.id))

        # ── 3. Schedule conflict check ────────────────────────────────────────
        from services.schedule import check_job_schedule_conflicts

        try:
            result = check_job_schedule_conflicts(job, session['user_id'])
            if result.get('has_schedule') and not result.get('available'):
                # Tìm ngày đầu tiên bị trùng để báo lỗi
                for day in result.get('days', []):
                    if not day.get('available'):
                        flash(f'Bạn đã có lịch công việc khác vào ngày {day["date_display"]} '
                              f'({day["conflict_start"]}–{day["conflict_end"]}). '
                              f'Vui lòng kiểm tra lịch của bạn.', 'error')
                        break
                return render_template('job_detail.html', job=job, form_data=request.form)
        except Exception as e:
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
            cover_letter=request.form.get('cover_letter', ''),
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

    return jsonify([{'id': m.id, 'sender_id': m.sender_id, 'sender_name': m.sender.name if m.sender else '',
                     'content': m.content, 'image_url': getattr(m, 'image_url', None),
                     'time': m.created_at.strftime('%H:%M %d/%m') if m.created_at else ''} for m in msgs])

@app.route('/api/messages/<int:contract_id>', methods=['POST'])
@login_required
def send_message(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    sender_id = session['user_id']
    from services.permissions import require_contract_access
    require_contract_access(sender_id, contract)

    content = request.json.get('content', '').strip()
    image_url = request.json.get('image_url', '').strip()
    if content or image_url:
        db.session.add(Message(
            contract_id=contract_id, sender_id=sender_id,
            content=content or ('[Hình ảnh]' if image_url else ''),
            image_url=image_url or None
        ))
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
    query = Job.query
    if status_filter == 'flagged':
        query = query.filter_by(is_flagged=True)
    elif status_filter == 'open':
        query = query.filter(Job.status == 'open', db.or_(Job.is_flagged == False, Job.is_flagged == None))
    elif status_filter == 'pending':
        query = query.filter(Job.status == 'pending', db.or_(Job.is_flagged == False, Job.is_flagged == None))
    elif status_filter == 'completed':
        query = query.filter_by(status='completed')
    jobs = query.order_by(Job.created_at.desc()).all()
    return render_template('admin_jobs.html', jobs=jobs, status_filter=status_filter)

@app.route('/admin/jobs/<int:job_id>/flag', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('flag_job')
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

@app.route('/admin/jobs/<int:job_id>/approve', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('approve_job')
def admin_approve_job(job_id):
    job = Job.query.get_or_404(job_id)
    if job.status == 'pending':
        job.status = 'open'
        _audit_log(
            action=ADMIN_AUDIT_ACTIONS.get('UPDATE_JOB_STATUS', 'UPDATE_JOB_STATUS'),
            target_type='job',
            target_id=job.id,
            description=f'Phê duyệt job "{job.title}" (ID={job.id})',
        )
        db.session.commit()
        flash('Đã phê duyệt bài đăng thành công.', 'success')
    else:
        flash('Bài đăng không ở trạng thái chờ duyệt.', 'warning')
    return redirect(url_for('admin_jobs'))

@app.route('/admin/jobs/<int:job_id>/delete', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('reject_job')
def admin_delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    
    # 1. Kiểm tra dependency quan trọng: Hợp đồng
    from models import Contract
    contracts = Contract.query.filter_by(job_id=job.id).all()
    if contracts:
        flash('Không thể xóa vĩnh viễn bài đăng đã có hợp đồng. Vui lòng sử dụng "Gắn cờ/Ẩn".', 'error')
        return redirect(url_for('admin_jobs'))
        
    # 2. Xử lý dependencies phụ
    from models import Notification, TranslatorSchedule, Proposal, Report, JobSchedule
    
    # SET NULL cho các lịch sử (không xóa lịch sử)
    Notification.query.filter_by(related_job_id=job.id).update({'related_job_id': None})
    Report.query.filter_by(related_job_id=job.id).update({'related_job_id': None})
    TranslatorSchedule.query.filter_by(job_id=job.id).update({'job_id': None})
    
    # Xóa dọn dẹp các data ăn theo
    Proposal.query.filter_by(job_id=job.id).delete()
    JobSchedule.query.filter_by(job_id=job.id).delete()
    
    _audit_log(
        action=ADMIN_AUDIT_ACTIONS['DELETE_JOB'],
        target_type='job',
        target_id=job.id,
        description=f'Xóa vĩnh viễn job "{job.title}" (ID={job.id}) của hirer {job.hirer.name}',
    )
    db.session.delete(job)
    db.session.commit()
    flash('Đã xoá vĩnh viễn bài đăng an toàn.', 'success')
    return redirect(url_for('admin_jobs'))

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

@app.route('/admin/verifications/<int:verification_id>/<action>', methods=['POST'])
@admin_required
def admin_review_verification(verification_id, action):
    """Phê duyệt hoặc từ chối yêu cầu xác minh của phiên dịch viên."""
    from services.verification import review_verification_request
    from admin_auth import get_client_ip

    admin = getattr(g, 'current_admin', None) or User.query.get(session.get('admin_id'))
    reason = request.form.get('reason', '')

    ok, msg = review_verification_request(
        verification_id=verification_id,
        admin_user=admin,
        action=action,
        reason=reason,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent', '')[:512]
    )
    if ok:
        flash(msg, 'success')
    else:
        flash(msg, 'error')
    return redirect(url_for('admin_translators', show='pending' if action == 'reject' else 'verified'))

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
@require_permission('view_dashboard')
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
@require_permission('view_dashboard')
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
@require_permission('view_dashboard')
def admin_notifications_read(notif_id):
    n = AdminNotification.query.get_or_404(notif_id)
    n.is_read = True
    db.session.commit()
    return redirect(url_for('admin_notifications'))

@app.route('/admin/notifications/read-all', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('view_dashboard')
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
@require_permission('view_dashboard')
def admin_admins():
    # Only super_admin or users with manage_admins can see all details easily
    # But let's allow all admins to view the list, just restrict actions in UI
    admins = User.query.filter_by(is_admin=True, role='admin').all()
    return render_template('admin_admins.html', admins=admins)

@app.route('/admin/admins/add', methods=['POST'])
@admin_login_required
@csrf_protected
@require_permission('view_dashboard')
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
@admin_login_required
@csrf_protected
@require_permission('view_dashboard')
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
@admin_login_required
@require_permission('view_dashboard')
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
    recommended = get_recommended_jobs_for_translator(session['user_id'], limit, current_lang)
    return jsonify(recommended)

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
