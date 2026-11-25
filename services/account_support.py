"""
services/account_support.py
Phân hệ Trợ giúp & Hỗ trợ (Mục 5.7):
1. FAQ & Hướng dẫn (5.7.1): Accordion theo 4 chủ đề chính:
   - Nhận thù lao (Escrow & thanh toán)
   - Quy tắc hủy ca (Quy định & bồi thường)
   - Giải quyết tranh chấp (Trọng tài & khiếu nại)
   - Đổi thông tin định danh (KYC & bảo vệ danh tính)
2. Điều khoản & Chính sách (5.7.2):
   - Danh sách tài liệu chính thức (chỉ xem / read-only).
3. Gửi & Theo dõi Ticket (5.7.3):
   - Tự động sinh mã ticket duy nhất (ví dụ: TK-10293).
   - Tái sử dụng File Upload Service từ module KYC (magic bytes, private storage, Supabase storage).
   - Theo dõi trạng thái: Đã tiếp nhận (open), Đang xử lý (in_progress), Đã giải quyết (resolved).
   - Khung xem phản hồi từ Ban Quản trị.
"""

from __future__ import annotations

import os
import sys
import secrets
import random
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

from models import db, User, SupportTicket
from services.verification import (
    detect_file_type_from_bytes,
    get_private_verification_folder,
    format_file_size,
)

# ─── CÁC CHỦ ĐỀ HỖ TRỢ ĐƯỢC PHÉP ─────────────────────────────────────────────

SUPPORT_CATEGORIES = {
    'compensation': {
        'code': 'compensation',
        'title': 'Nhận thù lao & Escrow',
        'badge_class': 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
        'icon': 'cash'
    },
    'cancellation': {
        'code': 'cancellation',
        'title': 'Quy tắc hủy ca & Bồi thường',
        'badge_class': 'bg-amber-50 text-amber-700 border-amber-200/80',
        'icon': 'calendar-x'
    },
    'dispute': {
        'code': 'dispute',
        'title': 'Giải quyết tranh chấp & Khiếu nại',
        'badge_class': 'bg-rose-50 text-rose-700 border-rose-200/80',
        'icon': 'shield-alert'
    },
    'identity': {
        'code': 'identity',
        'title': 'Đổi thông tin định danh & KYC',
        'badge_class': 'bg-indigo-50 text-indigo-700 border-indigo-200/80',
        'icon': 'identification'
    },
    'technical': {
        'code': 'technical',
        'title': 'Sự cố kỹ thuật & Đăng nhập',
        'badge_class': 'bg-sky-50 text-sky-700 border-sky-200/80',
        'icon': 'cpu'
    },
    'other': {
        'code': 'other',
        'title': 'Yêu cầu hỗ trợ khác',
        'badge_class': 'bg-slate-100 text-slate-700 border-slate-200/80',
        'icon': 'question'
    }
}

ALLOWED_TICKET_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
MAX_TICKET_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ─── 5.7.1: FAQ & HƯỚNG DẪN CHI TIẾT ──────────────────────────────────────────

FAQ_TOPICS = [
    {
        'id': 'compensation',
        'title': 'Nhận thù lao',
        'description': 'Quy trình ký quỹ Escrow, thanh toán, biểu phí và thời gian nhận tiền về tài khoản ngân hàng.',
        'icon': 'cash',
        'color': 'emerald'
    },
    {
        'id': 'cancellation',
        'title': 'Quy tắc hủy ca',
        'description': 'Mức đền bù khi khách hủy ca, quy định báo bận khẩn cấp và mức phạt vi phạm cam kết.',
        'icon': 'calendar-x',
        'color': 'amber'
    },
    {
        'id': 'dispute',
        'title': 'Giải quyết tranh chấp',
        'description': 'Quy trình trọng tài, bảo vệ quyền lợi hợp đồng và hòa giải khi khách hàng từ chối nghiệm thu.',
        'icon': 'shield-alert',
        'color': 'rose'
    },
    {
        'id': 'identity',
        'title': 'Đổi thông tin định danh',
        'description': 'Thủ tục cập nhật CCCD, đổi họ tên pháp lý, bổ sung chứng chỉ và xác minh lại hồ sơ KYC.',
        'icon': 'identification',
        'color': 'indigo'
    }
]

FAQ_ITEMS = [
    # 1. Nhận thù lao
    {
        'id': 'faq-comp-1',
        'topic': 'compensation',
        'topic_title': 'Nhận thù lao',
        'question': 'Tiền thù lao phiên dịch được thanh toán và giải ngân như thế nào sau ca làm?',
        'answer': 'Khi khách hàng đặt lịch phiên dịch, 100% kinh phí hợp đồng sẽ được nạp vào tài khoản ký quỹ an toàn (Escrow) của VietTranslate. Sau khi kết thúc ca dịch, khách hàng có 48 giờ để xác nhận nghiệm thu. Sau khi nghiệm thu (hoặc hệ thống tự động nghiệm thu nếu quá 48 giờ mà không có khiếu nại), toàn bộ thù lao sẽ được giải ngân ngay vào số dư ví khả dụng của phiên dịch viên.'
    },
    {
        'id': 'faq-comp-2',
        'topic': 'compensation',
        'topic_title': 'Nhận thù lao',
        'question': 'Cơ chế Escrow bảo vệ quyền lợi nhận thù lao của tôi như thế nào?',
        'answer': 'Cơ chế Escrow đảm bảo số tiền thù lao đã được thanh toán và tạm giữ độc lập tại VietTranslate trước khi bạn bắt đầu ca dịch. Khách hàng không thể tự ý hủy hợp đồng để quỵt thù lao sau khi bạn đã hoàn thành công việc. Điều này loại bỏ hoàn toàn rủi ro bùng thù lao hoặc thanh toán chậm trễ.'
    },
    {
        'id': 'faq-comp-3',
        'topic': 'compensation',
        'topic_title': 'Nhận thù lao',
        'question': 'Thời gian rút tiền về tài khoản ngân hàng cá nhân mất bao lâu?',
        'answer': 'Lệnh rút tiền từ ví VietTranslate về tài khoản ngân hàng Việt Nam (qua cổng Napas 24/7) thường được xử lý hoàn tất trong vòng 15 đến 30 phút. Đối với các yêu cầu rút tiền vào dịp lễ tết hoặc ca đêm, giao dịch có thể mất tối đa 24 giờ làm việc.'
    },
    {
        'id': 'faq-comp-4',
        'topic': 'compensation',
        'topic_title': 'Nhận thù lao',
        'question': 'Nền tảng VietTranslate áp dụng mức phí hoa hồng là bao nhiêu?',
        'answer': 'Phí dịch vụ nền tảng dao động từ 5% đến 12% tùy thuộc vào cấp bậc tài khoản (tài khoản Thành viên Basic hoặc Tài khoản Pro) và tổng giá trị hợp đồng. Tỷ lệ chiết khấu và số tiền thực nhận luôn được hiển thị minh bạch trước khi bạn gửi báo giá cho khách hàng.'
    },

    # 2. Quy tắc hủy ca
    {
        'id': 'faq-canc-1',
        'topic': 'cancellation',
        'topic_title': 'Quy tắc hủy ca',
        'question': 'Nếu khách hàng hủy ca đột xuất, tôi có được nhận tiền đền bù không?',
        'answer': 'Có. VietTranslate áp dụng chính sách bảo vệ phiên dịch viên nghiêm ngặt: (1) Nếu khách hủy trước từ 24h - 48h: bạn nhận 25% thù lao; (2) Hủy trước dưới 24h: bạn nhận 50% thù lao; (3) Hủy trước dưới 6h hoặc khi bạn đã có mặt tại điểm phiên dịch: bạn nhận đủ 100% thù lao từ nguồn quỹ Escrow đã ký quỹ.'
    },
    {
        'id': 'faq-canc-2',
        'topic': 'cancellation',
        'topic_title': 'Quy tắc hủy ca',
        'question': 'Nếu tôi gặp trường hợp bất khả kháng không thể tham gia ca dịch thì quy trình ra sao?',
        'answer': 'Trong trường hợp khẩn cấp (ốm đau đột xuất, sự cố y tế, tai nạn), bạn cần bấm nút "Báo bận khẩn cấp" trên ứng dụng trước ít nhất 12 giờ và cung cấp minh chứng hợp lệ. VietTranslate sẽ kích hoạt mạng lưới điều phối phiên dịch viên dự phòng để tiếp quản ca dịch nhằm hạn chế tối đa gián đoạn cho khách hàng.'
    },
    {
        'id': 'faq-canc-3',
        'topic': 'cancellation',
        'topic_title': 'Quy tắc hủy ca',
        'question': 'Việc tự ý hủy ca dịch ảnh hưởng như thế nào đến tài khoản của tôi?',
        'answer': 'Hủy ca không báo trước hoặc hủy sát giờ không có lý do bất khả kháng được coi là vi phạm nghiêm trọng: bị trừ 20 điểm uy tín (Trust Score), tạm ẩn hồ sơ khỏi danh bạ tìm kiếm trong 7 ngày, và có thể phải bồi hoàn 30% giá trị hợp đồng để hỗ trợ chi phí tìm người thay thế.'
    },
    {
        'id': 'faq-canc-4',
        'topic': 'cancellation',
        'topic_title': 'Quy tắc hủy ca',
        'question': 'Khách hàng yêu cầu làm thêm giờ (Overtime) so với thời lượng hợp đồng thì tính thế nào?',
        'answer': 'Mọi thời gian làm thêm ngoài khung giờ hợp đồng ban đầu được tính với hệ số 1.5x so với đơn giá tiêu chuẩn. Bạn cần gửi yêu cầu phụ phí phát sinh trên hệ thống để khách hàng xác nhận ký quỹ bổ sung, tránh thỏa thuận ngoài luồng không được bảo vệ.'
    },

    # 3. Giải quyết tranh chấp
    {
        'id': 'faq-disp-1',
        'topic': 'dispute',
        'topic_title': 'Giải quyết tranh chấp',
        'question': 'Làm gì khi khách hàng từ chối ký nghiệm thu hoặc chê chất lượng dịch thuật?',
        'answer': 'Bạn không cần hoang mang. Hãy vào chi tiết Hợp đồng và nhấn nút "Mở tranh chấp hợp đồng" hoặc tạo Ticket tại Tab này trong vòng 72 giờ. Khi tranh chấp được kích hoạt, toàn bộ quỹ Escrow sẽ được khóa bảo lưu và Ban Trọng tài VietTranslate sẽ vào cuộc xem xét.'
    },
    {
        'id': 'faq-disp-2',
        'topic': 'dispute',
        'topic_title': 'Giải quyết tranh chấp',
        'question': 'Quy trình trọng tài và hòa giải tranh chấp của VietTranslate gồm những bước nào?',
        'answer': 'Quy trình gồm 3 bước minh bạch: (1) Thu thập minh chứng từ cả 2 phía trong 48 giờ; (2) Ban Giám định Chuyên môn độc lập phân tích chất lượng dựa trên ghi âm, tài liệu và biên bản làm việc; (3) Ban Quản trị đưa ra phán quyết phân bổ quỹ Escrow công bằng trong vòng 3 ngày làm việc.'
    },
    {
        'id': 'faq-disp-3',
        'topic': 'dispute',
        'topic_title': 'Giải quyết tranh chấp',
        'question': 'Tôi cần chuẩn bị những minh chứng gì để chứng minh ca dịch thành công?',
        'answer': 'Minh chứng bao gồm: (1) Định vị check-in có mặt đúng giờ; (2) Lịch sử tin nhắn trao đổi trên hệ thống; (3) Bản ghi âm ca dịch (nếu hai bên đã đồng ý); (4) Tài liệu biên bản nghiệm thu hoặc chữ ký xác nhận của đại diện khách hàng tại hiện trường.'
    },
    {
        'id': 'faq-disp-4',
        'topic': 'dispute',
        'topic_title': 'Giải quyết tranh chấp',
        'question': 'Chi phí cho dịch vụ trọng tài hòa giải tranh chấp là bao nhiêu?',
        'answer': 'VietTranslate cung cấp dịch vụ trọng tài và hòa giải hoàn toàn MIỄN PHÍ cho mọi hợp đồng giao dịch chính thức qua nền tảng. Chúng tôi cam kết bảo vệ sự công bằng tối đa cho cả phiên dịch viên lẫn khách hàng.'
    },

    # 4. Đổi thông tin định danh
    {
        'id': 'faq-iden-1',
        'topic': 'identity',
        'topic_title': 'Đổi thông tin định danh',
        'question': 'Tại sao trường Họ và tên và CCCD bị khóa sau khi đã xác minh danh tính?',
        'answer': 'Nhằm tuân thủ quy định pháp luật về giao kết hợp đồng điện tử và ngăn chặn hành vi mạo danh, cho thuê tài khoản, sau khi hồ sơ đã vượt qua thẩm định (Verified), các trường định danh nòng cốt sẽ tự động chuyển sang chế độ Chỉ xem (Disabled) để bảo vệ quyền sở hữu của chính bạn.'
    },
    {
        'id': 'faq-iden-2',
        'topic': 'identity',
        'topic_title': 'Đổi thông tin định danh',
        'question': 'Tôi vừa làm lại thẻ CCCD gắn chip mới hoặc đổi tên pháp lý thì cập nhật thế nào?',
        'answer': 'Bạn hãy gửi một Ticket hỗ trợ ngay tại Tab này, chọn chủ đề "Đổi thông tin định danh & KYC", đính kèm ảnh chụp 2 mặt của thẻ CCCD mới cùng giấy xác nhận thay đổi (nếu đổi tên). Bộ phận Thẩm định sẽ kiểm tra đối chiếu và mở khóa quyền cập nhật trong vòng 24 giờ làm việc.'
    },
    {
        'id': 'faq-iden-3',
        'topic': 'identity',
        'topic_title': 'Đổi thông tin định danh',
        'question': 'Tôi có thể tải lên thêm chứng chỉ ngoại ngữ mới (IELTS, HSK, TOPIK...) không?',
        'answer': 'Có. Bạn có thể vào Tab "Năng lực & Bảng giá" hoặc Tab "Xác minh hồ sơ" để tải lên bằng cấp / chứng chỉ mới bất kỳ lúc nào. Chứng chỉ mới sẽ được kiểm tra chữ ký nhị phân và gửi tới chuyên viên thẩm định để gắn huy hiệu xác thực lên hồ sơ công khai.'
    },
    {
        'id': 'faq-iden-4',
        'topic': 'identity',
        'topic_title': 'Đổi thông tin định danh',
        'question': 'Thời gian thẩm định lại thông tin định danh sau khi cập nhật là bao lâu?',
        'answer': 'Hồ sơ bổ sung hoặc cập nhật thông tin định danh thường được Ban Thẩm định VietTranslate xử lý trong vòng 1 đến 2 ngày làm việc. Bạn sẽ nhận được thông báo qua chuông hệ thống và email ngay khi hồ sơ được duyệt hoàn tất.'
    }
]


# ─── 5.7.2: DANH SÁCH ĐIỀU KHOẢN & CHÍNH SÁCH (CHỈ XEM) ──────────────────────

POLICY_DOCUMENTS = [
    {
        'key': 'operating_regulations',
        'code': 'QC-VTL-2024',
        'title': 'Quy chế Hoạt động Sàn Giao dịch VietTranslate',
        'version': '3.2 (Ban hành 01/2024)',
        'summary': 'Nguyên tắc vận hành, quyền và nghĩa vụ pháp lý của phiên dịch viên và khách hàng, các hành vi bị cấm trên nền tảng.',
        'tag': 'Quy chế chung',
        'badge_color': 'blue',
        'articles': [
            {
                'title': 'Điều 1. Phạm vi áp dụng & Định nghĩa',
                'content': 'Quy chế này quy định về quyền hạn, trách nhiệm và nghĩa vụ của các bên tham gia giao dịch kết nối dịch thuật thông qua nền tảng trực tuyến VietTranslate. Áp dụng cho toàn bộ Phiên dịch viên tự do, Doanh nghiệp cung ứng và Khách hàng đăng ký tài khoản.'
            },
            {
                'title': 'Điều 2. Nguyên tắc giao kết và thực hiện dịch vụ',
                'content': 'Mọi thỏa thuận cung cấp dịch vụ phiên dịch phải được ghi nhận trên hợp đồng điện tử của hệ thống. Các bên cam kết thực hiện đúng thời gian, địa điểm, ngôn ngữ và yêu cầu chuyên môn đã xác nhận.'
            },
            {
                'title': 'Điều 3. Các hành vi nghiêm cấm',
                'content': 'Tuyệt đối cấm hành vi giao dịch ngoài luồng nhằm trốn tránh phí dịch vụ và cơ chế bảo vệ Escrow; cấm hành vi cho thuê, chuyển nhượng tài khoản đã xác minh danh tính; cấm tiết lộ bí mật thương mại của khách hàng.'
            },
            {
                'title': 'Điều 4. Cơ chế xử lý vi phạm',
                'content': 'Thành viên vi phạm quy chế sẽ bị xử lý theo các mức: Cảnh cáo, tạm đình chỉ nhận việc từ 7 - 30 ngày, khấu trừ tiền ký quỹ bồi thường hoặc khóa tài khoản vĩnh viễn tùy theo mức độ nghiêm trọng.'
            }
        ]
    },
    {
        'key': 'escrow_regulations',
        'code': 'QC-ESC-2024',
        'title': 'Quy chế Thanh toán & Ký quỹ Bảo đảm Escrow',
        'version': '2.1 (Ban hành 03/2024)',
        'summary': 'Quy định chi tiết cơ chế nạp tiền, tạm giữ ký quỹ, tự động giải ngân và bảo vệ dòng tiền hợp đồng cho phiên dịch viên.',
        'tag': 'Thanh toán & Ví',
        'badge_color': 'emerald',
        'articles': [
            {
                'title': 'Điều 1. Bản chất cơ chế Ký quỹ Escrow',
                'content': 'Toàn bộ khoản tiền thù lao thỏa thuận trong hợp đồng dịch vụ bắt buộc phải được khách hàng nạp đủ vào tài khoản ký quỹ trung gian của VietTranslate trước khi phiên dịch viên bắt đầu thực hiện ca làm.'
            },
            {
                'title': 'Điều 2. Điều kiện giải ngân thù lao',
                'content': 'Khoản tiền ký quỹ sẽ được giải ngân sang ví phiên dịch viên ngay khi: (a) Khách hàng bấm nút Xác nhận nghiệm thu; hoặc (b) Sau 48 giờ kể từ khi ca dịch kết thúc mà khách hàng không có khiếu nại tranh chấp hợp lệ.'
            },
            {
                'title': 'Điều 3. Quy định rút tiền về ngân hàng',
                'content': 'Phiên dịch viên có quyền rút số dư khả dụng về bất kỳ tài khoản ngân hàng chính chủ nào tại Việt Nam. VietTranslate áp dụng hạn mức rút tối thiểu 100.000 VNĐ/giao dịch và tối đa 100.000.000 VNĐ/ngày.'
            }
        ]
    },
    {
        'key': 'cancellation_policy',
        'code': 'CS-HC-2024',
        'title': 'Chính sách Hủy ca Dịch & Mức Phí Bồi thường',
        'version': '2.0 (Ban hành 02/2024)',
        'summary': 'Mức đền bù cho phiên dịch viên khi khách hủy đột xuất, quy trình xử lý trường hợp bất khả kháng và chế tài vi phạm cam kết.',
        'tag': 'Hủy ca & Bồi thường',
        'badge_color': 'amber',
        'articles': [
            {
                'title': 'Điều 1. Khách hàng hủy ca đột xuất',
                'content': 'Trường hợp khách hàng đơn phương hủy ca dịch: Nếu hủy trước 24h - 48h được hoàn 75% kinh phí (bồi thường 25% cho phiên dịch); nếu hủy trước dưới 24h được hoàn 50% (bồi thường 50%); nếu hủy trước dưới 6h hoặc phiên dịch viên đã có mặt, khách không được hoàn tiền (phiên dịch nhận 100% thù lao).'
            },
            {
                'title': 'Điều 2. Phiên dịch viên hủy ca đột xuất',
                'content': 'Phiên dịch viên đơn phương hủy ca dưới 24 giờ mà không có lý do bất khả kháng sẽ bị trừ 20 điểm uy tín, tạm khóa quyền ứng tuyển trong 7 ngày và chịu mức phạt tương đương 30% giá trị ca dịch để bù đắp thiệt hại phát sinh.'
            },
            {
                'title': 'Điều 3. Trường hợp bất khả kháng',
                'content': 'Các sự kiện bất khả kháng gồm: Thiên tai, dịch bệnh, tai nạn y tế khẩn cấp có xác nhận của cơ quan thẩm quyền. Khi đó hợp đồng được chấm dứt mà không áp dụng chế tài bồi thường, tiền ký quỹ được hoàn trả cho khách hàng.'
            }
        ]
    },
    {
        'key': 'privacy_policy',
        'code': 'CS-BM-2024',
        'title': 'Chính sách Bảo mật & Xử lý Dữ liệu Cá nhân',
        'version': '1.5 (Tuân thủ NĐ 13/2023/NĐ-CP)',
        'summary': 'Cam kết bảo mật dữ liệu CCCD, chứng chỉ, hợp đồng và lịch sử giao dịch. Lưu trữ riêng tư an toàn, không rò rỉ cho bên thứ ba.',
        'tag': 'Bảo mật dữ liệu',
        'badge_color': 'indigo',
        'articles': [
            {
                'title': 'Điều 1. Loại dữ liệu thu thập & Mục đích',
                'content': 'VietTranslate chỉ thu thập dữ liệu căn cước (CCCD/Hộ chiếu), sơ yếu lý lịch (CV), chứng chỉ ngoại ngữ và thông tin tài khoản ngân hàng phục vụ duy nhất cho mục đích xác thực danh tính (KYC) và chi trả thù lao theo pháp luật.'
            },
            {
                'title': 'Điều 2. Vùng lưu trữ riêng tư & Mã hóa',
                'content': 'Toàn bộ tệp ảnh căn cước và tài liệu minh chứng được lưu trữ trên hệ thống Private Storage tách biệt hoàn toàn khỏi thư mục công khai, áp dụng cơ chế xác thực quyền sở hữu và mã hóa đường truyền SSL/TLS 256-bit.'
            },
            {
                'title': 'Điều 3. Cam kết không chia sẻ dữ liệu',
                'content': 'VietTranslate cam kết tuyệt đối không bán, trao đổi hoặc tiết lộ thông tin cá nhân của người dùng cho bất kỳ bên thứ ba nào vì mục đích quảng cáo hoặc thương mại.'
            }
        ]
    },
    {
        'key': 'quality_standards',
        'code': 'QC-TC-2024',
        'title': 'Tiêu chuẩn Dịch thuật & Quy tắc Ứng xử Nghề nghiệp',
        'version': '1.8 (Ban hành 12/2023)',
        'summary': 'Chuẩn mực tác phong, trang phục, bảo mật thông tin buổi dịch (NDA) và chất lượng dịch thuật chuẩn xác.',
        'tag': 'Tiêu chuẩn chất lượng',
        'badge_color': 'purple',
        'articles': [
            {
                'title': 'Điều 1. Trang phục và tác phong làm việc',
                'content': 'Phiên dịch viên có mặt tại địa điểm tối thiểu 15 phút trước giờ bắt đầu; tuân thủ trang phục lịch sự, chuyên nghiệp theo tính chất sự kiện (Suit, công sở, hoặc trang phục bảo hộ nếu dịch tại nhà máy).'
            },
            {
                'title': 'Điều 2. Tính trung thực và chuẩn xác',
                'content': 'Dịch đúng nội dung, ngữ nghĩa và sắc thái phát biểu; không thêm thắt quan điểm cá nhân; giữ thái độ trung lập trong các cuộc đàm phán, tranh tụng hoặc phiên họp thương mại.'
            },
            {
                'title': 'Điều 3. Bảo mật thông tin phiên dịch (NDA)',
                'content': 'Mọi tài liệu, nội dung trao đổi trong phiên dịch là bí mật kinh doanh của khách hàng. Nghiêm cấm ghi âm, chụp ảnh tài liệu nội bộ nếu không được khách hàng cho phép bằng văn bản.'
            }
        ]
    },
    {
        'key': 'dispute_resolution',
        'code': 'CS-TC-2024',
        'title': 'Quy trình Giải quyết Tranh chấp & Trọng tài Nền tảng',
        'version': '2.2 (Ban hành 02/2024)',
        'summary': 'Trình tự thụ lý tranh chấp hợp đồng, căn cứ đánh giá chất lượng và cơ chế thi hành quyết định trọng tài hòa giải.',
        'tag': 'Trọng tài & Khiếu nại',
        'badge_color': 'rose',
        'articles': [
            {
                'title': 'Điều 1. Thời hiệu gửi khiếu nại',
                'content': 'Hai bên có quyền mở tranh chấp hợp đồng trong vòng 72 giờ kể từ thời điểm kết thúc ca dịch. Sau 72 giờ không có tranh chấp, hệ thống tự động giải ngân và miễn trừ khiếu nại phát sinh sau.'
            },
            {
                'title': 'Điều 2. Hội đồng thẩm định độc lập',
                'content': 'Ban Trọng tài của VietTranslate gồm các chuyên gia ngôn ngữ giàu kinh nghiệm sẽ trực tiếp thẩm định tài liệu, bản ghi âm và chứng cứ để đưa ra kết luận về mức độ hoàn thành công việc.'
            },
            {
                'title': 'Điều 3. Hiệu lực thi hành',
                'content': 'Quyết định phân bổ quỹ ký quỹ Escrow của Ban Quản trị VietTranslate là phán quyết cuối cùng có hiệu lực thực thi ngay lập tức trong phạm vi nền tảng.'
            }
        ]
    }
]


# ─── 5.7.3: HÀM TẢI TỆP TÁI SỬ DỤNG KYC UPLOAD HELPER ─────────────────────────

def save_ticket_attachment(file_storage, user) -> tuple[bool, str | None, str | None]:
    """
    TÁI SỬ DỤNG HOÀN TOÀN FILE UPLOAD SERVICE / HELPER TỪ MODULE KYC (services.verification):
    - Đọc nội dung nhị phân (bytes) và khôi phục con trỏ stream (.seek(0)).
    - Kiểm tra chữ ký nhị phân thực tế máy chủ (magic bytes qua detect_file_type_from_bytes).
    - Giới hạn dung lượng an toàn (tối đa 10MB).
    - Sinh tên tệp ngẫu nhiên bảo mật (tránh lộ thông tin cá nhân).
    - Lưu vào Private Storage Folder (get_private_verification_folder()) và Supabase nếu có.
    - KHÔNG cài đặt thêm bất kỳ thư viện lưu trữ mới nào.
    Trả về: (thành_công: bool, url_truy_cập: str, lỗi: str)
    """
    if not file_storage or not getattr(file_storage, 'filename', None):
        return True, None, None  # Tệp đính kèm không bắt buộc

    raw_filename = file_storage.filename.strip()
    if not raw_filename or '.' not in raw_filename:
        return False, None, "Tệp đính kèm thiếu phần mở rộng hợp lệ (ví dụ: .png, .jpg, .pdf)."

    ext = raw_filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_TICKET_EXTENSIONS:
        allowed_str = ', '.join([e.upper() for e in sorted(ALLOWED_TICKET_EXTENSIONS)])
        return False, None, f"Định dạng .{ext} không được hỗ trợ. Vui lòng chọn ảnh hoặc tài liệu: {allowed_str}."

    try:
        file_bytes = file_storage.read()
        file_storage.seek(0)
    except Exception as e:
        return False, None, f"Lỗi đọc nội dung tệp: {str(e)}"

    size = len(file_bytes)
    if size == 0:
        return False, None, "Tệp tải lên rỗng (0 bytes). Vui lòng chọn tệp có nội dung."

    if size > MAX_TICKET_FILE_SIZE:
        curr_mb = size / (1024 * 1024)
        return False, None, f"Kích thước tệp ({curr_mb:.1f} MB) vượt quá giới hạn cho phép (10 MB)."

    # Kiểm tra magic bytes ở cấp máy chủ (reused from KYC verification)
    detected_type = detect_file_type_from_bytes(file_bytes)
    if not detected_type:
        return False, None, "Nội dung tệp không an toàn hoặc không vượt qua kiểm tra chữ ký nhị phân."

    valid_types = {'jpeg', 'png', 'webp', 'pdf'}
    if detected_type not in valid_types:
        return False, None, f"Nội dung tệp thực tế ({detected_type.upper()}) không phù hợp với ảnh chụp màn hình hoặc tài liệu hỗ trợ."

    # Xác định MIME type
    if detected_type == 'pdf':
        mime_type = 'application/pdf'
    elif detected_type == 'jpeg':
        mime_type = 'image/jpeg'
    elif detected_type == 'png':
        mime_type = 'image/png'
    elif detected_type == 'webp':
        mime_type = 'image/webp'
    else:
        mime_type = mimetypes.guess_type(raw_filename)[0] or 'application/octet-stream'

    unique_token = secrets.token_hex(16)
    stored_filename = f"pdoc_ticket_{unique_token}.{ext}"

    # Supabase Storage (nếu được cấu hình sẵn trong KYC module)
    supabase_stored = False
    try:
        from supabase_client import get_supabase_client
        sb = get_supabase_client()
        if sb:
            res = sb.storage.from_('verification_documents').upload(
                path=stored_filename,
                file=file_bytes,
                file_options={"content-type": mime_type}
            )
            if res:
                supabase_stored = True
    except Exception:
        supabase_stored = False

    # Luôn lưu vào Private Storage an toàn (reused get_private_verification_folder())
    private_folder = get_private_verification_folder()
    local_path = os.path.join(private_folder, stored_filename)
    try:
        with open(local_path, 'wb') as f:
            f.write(file_bytes)
    except Exception as e:
        print(f"[TICKET ATTACHMENT ERROR] Failed to write local file: {e}", file=sys.stderr)
        if not supabase_stored:
            return False, None, "Không thể lưu trữ tệp trên vùng an toàn máy chủ. Vui lòng thử lại."

    # URL nội bộ bảo mật (được kiểm tra quyền sở hữu khi tải / xem)
    attachment_url = f"/account/support/attachment/{stored_filename}"
    return True, attachment_url, None


# ─── 5.7.3: HÀM QUẢN LÝ VÀ THEO DÕI TICKET HỖ TRỢ ────────────────────────────

def generate_unique_ticket_code() -> str:
    """
    Tự động tạo mã định danh duy nhất (ví dụ: TK-10293).
    Kiểm tra trùng lặp trong cơ sở dữ liệu để đảm bảo tính duy nhất 100%.
    """
    for _ in range(50):
        random_num = random.randint(10000, 99999)
        code = f"TK-{random_num}"
        existing = SupportTicket.query.filter_by(ticket_code=code).first()
        if not existing:
            return code
    
    # Dự phòng timestamp nếu ngẫu nhiên bị va chạm nhiều
    ts_code = f"TK-{int(datetime.utcnow().timestamp()) % 100000:05d}"
    return ts_code


def create_support_ticket(
    user: User,
    category: str,
    title: str,
    description: str,
    attachment_file=None
) -> tuple[bool, SupportTicket | None, str | None]:
    """
    Tạo yêu cầu hỗ trợ mới cho người dùng (Mục 5.7.3):
    - Kiểm tra tính hợp lệ của chủ đề, tiêu đề và nội dung.
    - Tải và lưu trữ ảnh chụp màn hình bằng đúng File Upload Service hiện có.
    - Sinh mã ticket định danh duy nhất (TK-xxxxx).
    - Lưu vào bảng SupportTicket với trạng thái mặc định 'open' (Đã tiếp nhận).
    """
    if not user:
        return False, None, "Vui lòng đăng nhập để gửi yêu cầu hỗ trợ."

    category = (category or '').strip().lower()
    if category not in SUPPORT_CATEGORIES:
        return False, None, "Chủ đề yêu cầu hỗ trợ không hợp lệ. Vui lòng chọn trong danh sách hỗ trợ."

    title = (title or '').strip()
    if not title or len(title) < 5:
        return False, None, "Tiêu đề yêu cầu hỗ trợ phải có ít nhất 5 ký tự."
    if len(title) > 255:
        return False, None, "Tiêu đề yêu cầu hỗ trợ không được vượt quá 255 ký tự."

    description = (description or '').strip()
    if not description or len(description) < 10:
        return False, None, "Nội dung chi tiết phải có ít nhất 10 ký tự để chuyên viên có thể hỗ trợ hiệu quả."

    # Xử lý tệp đính kèm nếu có
    attachment_url = None
    if attachment_file and getattr(attachment_file, 'filename', None):
        ok, att_url, err = save_ticket_attachment(attachment_file, user)
        if not ok:
            return False, None, err
        attachment_url = att_url

    ticket_code = generate_unique_ticket_code()

    try:
        ticket = SupportTicket(
            ticket_code=ticket_code,
            user_id=user.id,
            category=category,
            title=title,
            description=description,
            attachment_url=attachment_url,
            status='open',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(ticket)
        db.session.commit()
        return True, ticket, None
    except Exception as e:
        db.session.rollback()
        print(f"[CREATE TICKET ERROR] {e}", file=sys.stderr)
        return False, None, "Đã xảy ra lỗi trong quá trình tạo phiếu hỗ trợ. Vui lòng thử lại sau."


def get_user_tickets(user_id: int, status: str = None) -> list[SupportTicket]:
    """Lấy danh sách ticket hỗ trợ của chính người dùng, sắp xếp mới nhất lên đầu."""
    try:
        query = SupportTicket.query.filter_by(user_id=user_id)
        if status and status in ('open', 'in_progress', 'resolved', 'closed'):
            query = query.filter_by(status=status)
        return query.order_by(SupportTicket.created_at.desc()).all()
    except Exception:
        db.session.rollback()
        return []


def get_ticket_by_code(ticket_code: str, user: User) -> tuple[SupportTicket | None, str | None]:
    """
    Lấy thông tin chi tiết một ticket theo mã định danh.
    Kiểm tra nghiêm ngặt quyền truy cập: chỉ chủ sở hữu hoặc admin mới được xem.
    """
    if not user:
        return None, "Vui lòng đăng nhập để xem thông tin ticket."

    ticket = SupportTicket.query.filter_by(ticket_code=ticket_code).first()
    if not ticket:
        return None, f"Không tìm thấy yêu cầu hỗ trợ với mã {ticket_code}."

    # Kiểm tra quyền truy cập
    if ticket.user_id != user.id and getattr(user, 'role', '') != 'admin':
        return None, "Bạn không có quyền truy cập vào phiếu hỗ trợ này."

    return ticket, None


def admin_respond_to_ticket(
    ticket_code: str,
    reply_text: str,
    new_status: str = 'resolved'
) -> tuple[bool, SupportTicket | None, str | None]:
    """
    Ban Quản trị / Hỗ trợ viên phản hồi ticket:
    - Cập nhật admin_reply, admin_reply_at.
    - Cập nhật trạng thái (in_progress hoặc resolved).
    """
    ticket = SupportTicket.query.filter_by(ticket_code=ticket_code).first()
    if not ticket:
        return False, None, f"Không tìm thấy ticket {ticket_code}."

    reply_text = (reply_text or '').strip()
    if not reply_text:
        return False, None, "Nội dung phản hồi không được để trống."

    ticket.admin_reply = reply_text
    ticket.admin_reply_at = datetime.utcnow()
    ticket.updated_at = datetime.utcnow()

    if new_status in ('open', 'in_progress', 'resolved', 'closed'):
        ticket.status = new_status

    try:
        db.session.commit()
        return True, ticket, None
    except Exception as e:
        db.session.rollback()
        return False, None, str(e)
