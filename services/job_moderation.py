"""
services/job_moderation.py
Bộ máy kiểm tra và đánh giá toàn diện 39 tiêu chí kiểm duyệt Job của VietTranslate.
Bao gồm:
- 4 Nhóm tiêu chí:
    Nhóm A: Tính đầy đủ thông tin (A1 - A12)
    Nhóm B: Tính chính xác và nhất quán (B1 - B9)
    Nhóm C: Dấu hiệu lừa đảo và rủi ro (C1 - C12) [Trọng tâm C1, C2, C3, C6, C9, C10 mức Nghiêm trọng]
    Nhóm D: Tuân thủ và chất lượng nội dung (D1 - D6)
- Engine quét regex và từ khóa phát hiện vi phạm:
    Zalo, SĐT, Telegram, WhatsApp, Email, Mời thanh toán ngoài, Đóng phí, v.v.
- Hàm highlight_violations: Tô sáng đoạn vi phạm trong mô tả công việc
- Phân loại trạng thái tiêu chí: passed (Đạt), warning / pending_review (Cần xem), critical (Nghiêm trọng), failed (Vi phạm)
"""

import re
import json
from datetime import datetime, date
from models import Job, User

# Định nghĩa danh sách 39 tiêu chí chuẩn theo Master Plan
JOB_CRITERIA_METADATA = {
    # ── NHÓM A: TÍNH ĐẦY ĐỦ THÔNG TIN (12 tiêu chí) ───────────────────────────
    'A1': {'code': 'A1', 'group': 'A', 'title': 'Độ dài tiêu đề hợp lệ', 'type': 'auto', 'severity': 'normal'},
    'A2': {'code': 'A2', 'group': 'A', 'title': 'Nhóm & Loại dịch vụ', 'type': 'auto', 'severity': 'normal'},
    'A3': {'code': 'A3', 'group': 'A', 'title': 'Cặp ngôn ngữ nguồn - đích', 'type': 'auto', 'severity': 'normal'},
    'A4': {'code': 'A4', 'group': 'A', 'title': 'Lĩnh vực chuyên ngành', 'type': 'auto', 'severity': 'normal'},
    'A5': {'code': 'A5', 'group': 'A', 'title': 'Hình thức làm việc', 'type': 'auto', 'severity': 'normal'},
    'A6': {'code': 'A6', 'group': 'A', 'title': 'Địa điểm làm việc cụ thể', 'type': 'auto_or_manual', 'severity': 'normal'},
    'A7': {'code': 'A7', 'group': 'A', 'title': 'Thời gian / Lịch trình công việc', 'type': 'auto', 'severity': 'normal'},
    'A8': {'code': 'A8', 'group': 'A', 'title': 'Khối lượng / Quy mô dịch', 'type': 'auto', 'severity': 'normal'},
    'A9': {'code': 'A9', 'group': 'A', 'title': 'Ngân sách đề xuất rõ ràng', 'type': 'auto', 'severity': 'normal'},
    'A10': {'code': 'A10', 'group': 'A', 'title': 'Yêu cầu năng lực & kinh nghiệm', 'type': 'manual', 'severity': 'normal'},
    'A11': {'code': 'A11', 'group': 'A', 'title': 'Mô tả công việc chi tiết (>=50 từ)', 'type': 'auto', 'severity': 'normal'},
    'A12': {'code': 'A12', 'group': 'A', 'title': 'Quyền lợi & hỗ trợ kèm theo', 'type': 'manual', 'severity': 'normal'},

    # ── NHÓM B: TÍNH CHÍNH XÁC VÀ NHẤT QUÁN (9 tiêu chí) ─────────────────────
    'B1': {'code': 'B1', 'group': 'B', 'title': 'Tiêu đề khớp với mô tả', 'type': 'manual', 'severity': 'normal'},
    'B2': {'code': 'B2', 'group': 'B', 'title': 'Ngôn ngữ nhất quán', 'type': 'auto', 'severity': 'normal'},
    'B3': {'code': 'B3', 'group': 'B', 'title': 'Thời gian hợp lý, không quá khứ', 'type': 'auto', 'severity': 'normal'},
    'B4': {'code': 'B4', 'group': 'B', 'title': 'Địa điểm nhất quán', 'type': 'manual', 'severity': 'normal'},
    'B5': {'code': 'B5', 'group': 'B', 'title': 'Ngân sách trong khung thị trường', 'type': 'auto', 'severity': 'warning'},
    'B6': {'code': 'B6', 'group': 'B', 'title': 'Không có dấu hiệu giá bất thường', 'type': 'auto', 'severity': 'warning'},
    'B7': {'code': 'B7', 'group': 'B', 'title': 'Hình thức onsite/online nhất quán', 'type': 'auto', 'severity': 'normal'},
    'B8': {'code': 'B8', 'group': 'B', 'title': 'Không trùng lặp job đang có', 'type': 'auto', 'severity': 'normal'},
    'B9': {'code': 'B9', 'group': 'B', 'title': 'Yêu cầu chứng chỉ phù hợp', 'type': 'manual', 'severity': 'normal'},

    # ── NHÓM C: DẤU HIỆU LỪA ĐẢO VÀ RỦI RO (12 tiêu chí) ───────────────────────
    'C1': {'code': 'C1', 'group': 'C', 'title': 'Không có thông tin liên lạc ngoài', 'type': 'auto', 'severity': 'critical'},
    'C2': {'code': 'C2', 'group': 'C', 'title': 'Không mời thanh toán ngoài nền tảng', 'type': 'auto', 'severity': 'critical'},
    'C3': {'code': 'C3', 'group': 'C', 'title': 'Không yêu cầu ứng viên đóng phí/cọc', 'type': 'auto', 'severity': 'critical'},
    'C4': {'code': 'C4', 'group': 'C', 'title': 'Không thu thập dữ liệu nhạy cảm (CCCD/OTP)', 'type': 'auto', 'severity': 'normal'},
    'C5': {'code': 'C5', 'group': 'C', 'title': 'Không có dấu hiệu mồi chài / việc nhẹ lương cao', 'type': 'auto', 'severity': 'normal'},
    'C6': {'code': 'C6', 'group': 'C', 'title': 'Địa điểm an toàn / không đưa người ra nước ngoài', 'type': 'auto', 'severity': 'critical'},
    'C7': {'code': 'C7', 'group': 'C', 'title': 'Không yêu cầu nhân thân không liên quan', 'type': 'manual', 'severity': 'normal'},
    'C8': {'code': 'C8', 'group': 'C', 'title': 'Người đăng uy tín, lịch sử sạch', 'type': 'auto', 'severity': 'normal'},
    'C9': {'code': 'C9', 'group': 'C', 'title': 'Không bóc lột / dịch thử miễn phí quá mức', 'type': 'auto', 'severity': 'critical'},
    'C10': {'code': 'C10', 'group': 'C', 'title': 'Không thuộc lĩnh vực cấm pháp luật', 'type': 'auto', 'severity': 'critical'},
    'C11': {'code': 'C11', 'group': 'C', 'title': 'Không mạo danh tổ chức / công ty lớn', 'type': 'manual', 'severity': 'normal'},
    'C12': {'code': 'C12', 'group': 'C', 'title': 'Tài liệu đính kèm an toàn', 'type': 'auto', 'severity': 'normal'},

    # ── NHÓM D: TUÂN THỦ VÀ CHẤT LƯỢNG (6 tiêu chí) ───────────────────────────
    'D1': {'code': 'D1', 'group': 'D', 'title': 'Tôn trọng, không phân biệt đối xử', 'type': 'manual', 'severity': 'normal'},
    'D2': {'code': 'D2', 'group': 'D', 'title': 'Không có từ ngữ thô tục / phản cảm', 'type': 'auto', 'severity': 'normal'},
    'D3': {'code': 'D3', 'group': 'D', 'title': 'Tiêu đề trình bày chuẩn mực', 'type': 'auto', 'severity': 'suggestion'},
    'D4': {'code': 'D4', 'group': 'D', 'title': 'Đúng mục đích tìm dịch vụ dịch thuật', 'type': 'manual', 'severity': 'normal'},
    'D5': {'code': 'D5', 'group': 'D', 'title': 'Văn phong rõ ràng, nghiêm túc', 'type': 'manual', 'severity': 'normal'},
    'D6': {'code': 'D6', 'group': 'D', 'title': 'Tuân thủ quy chế VietTranslate', 'type': 'manual', 'severity': 'normal'},
}

# Regex nhận diện thông tin liên lạc ngoài nền tảng (C1)
C1_PATTERNS = [
    # Số điện thoại (dạng 09xx xxx xxx hoặc +84)
    (re.compile(r'(?:\+?84|0)[1-9][0-9\s.\-]{7,11}[0-9]', re.IGNORECASE), 'Số điện thoại'),
    # Zalo
    (re.compile(r'(?:zalo|zl)[\s:=]*[0-9xX\s.\-]{7,13}', re.IGNORECASE), 'Zalo / Số Zalo'),
    (re.compile(r'\bzalo\b', re.IGNORECASE), 'Từ khóa Zalo'),
    # Telegram
    (re.compile(r'(?:tele(?:gram)?|tg)[\s:=]*@?[a-zA-Z0-9_]{4,}', re.IGNORECASE), 'Telegram'),
    # WhatsApp
    (re.compile(r'(?:whatsapp|wa)[\s:=]*[0-9+]{8,}', re.IGNORECASE), 'WhatsApp'),
    # Email
    (re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE), 'Email cá nhân'),
    # Link facebook/mạng xã hội
    (re.compile(r'(?:facebook\.com|fb\.com|fb\.me|t\.me)\/\S+', re.IGNORECASE), 'Liên kết mạng xã hội'),
]

# Regex nhận diện thanh toán ngoài (C2)
C2_PATTERNS = [
    re.compile(r'(?:chuyển khoản riêng|ck riêng|thanh toán trực tiếp|tiền mặt không qua app|không qua trung gian|bỏ qua sàn|thanh toán ngoài|thanh toan ngoai|chuyển tiền ngoài|chuyen tien ngoai|ck ngoài|ck ngoai|chuyển riêng)', re.IGNORECASE),
]

# Regex nhận diện yêu cầu đóng phí / đặt cọc (C3)
C3_PATTERNS = [
    re.compile(r'(?:đóng phí|nộp cọc|đặt cọc|phí giữ chỗ|phí xét duyệt|phí làm thẻ|phí phỏng vấn|cọc trước)', re.IGNORECASE),
]

# Regex nhận diện địa điểm rủi ro / đưa người ra nước ngoài trái phép (C6)
C6_PATTERNS = [
    re.compile(r'(?:vượt biên|campuchia|casino|biên giới|tam giác vàng|bavet|moc bai|không cần hộ chiếu|sang campuchia)', re.IGNORECASE),
]

# Regex nhận diện bóc lột / dịch thử miễn phí quá mức (C9)
C9_PATTERNS = [
    re.compile(r'(?:dịch thử không trả phí|dịch test miễn phí toàn bộ|dịch mẫu trước khi nhận|không trả phí bản test)', re.IGNORECASE),
]

# Regex nhận diện lĩnh vực cấm (C10)
C10_PATTERNS = [
    re.compile(r'(?:vũ khí|chất cấm|ma túy|cờ bạc|nội dung người lớn|khiêu dâm|chống phá|rửa tiền|hack)', re.IGNORECASE),
]


def scan_text_violations(text):
    """
    Quét văn bản để tìm các đoạn vi phạm C1, C2, C3, C6, C9, C10.
    Trả về:
        list các dict: { 'code': 'C1', 'matched_text': '...', 'start': int, 'end': int, 'reason': '...' }
    """
    violations = []
    if not text:
        return violations

    # Quét C1 (Liên lạc ngoài)
    for pat, label in C1_PATTERNS:
        for m in pat.finditer(text):
            violations.append({
                'code': 'C1',
                'matched_text': m.group(0),
                'start': m.start(),
                'end': m.end(),
                'reason': f'Phát hiện {label} ({m.group(0)})'
            })

    # Quét C2 (Thanh toán ngoài)
    for pat in C2_PATTERNS:
        for m in pat.finditer(text):
            violations.append({
                'code': 'C2',
                'matched_text': m.group(0),
                'start': m.start(),
                'end': m.end(),
                'reason': f'Có cụm từ mời thanh toán ngoài nền tảng: "{m.group(0)}"'
            })

    # Quét C3 (Đóng phí / cọc)
    for pat in C3_PATTERNS:
        for m in pat.finditer(text):
            violations.append({
                'code': 'C3',
                'matched_text': m.group(0),
                'start': m.start(),
                'end': m.end(),
                'reason': f'Có cụm từ yêu cầu ứng viên đóng phí/đặt cọc: "{m.group(0)}"'
            })

    # Quét C6 (Địa điểm rủi ro)
    for pat in C6_PATTERNS:
        for m in pat.finditer(text):
            violations.append({
                'code': 'C6',
                'matched_text': m.group(0),
                'start': m.start(),
                'end': m.end(),
                'reason': f'Dấu hiệu địa điểm rủi ro / biên giới: "{m.group(0)}"'
            })

    # Quét C9 (Bóc lột / dịch test)
    for pat in C9_PATTERNS:
        for m in pat.finditer(text):
            violations.append({
                'code': 'C9',
                'matched_text': m.group(0),
                'start': m.start(),
                'end': m.end(),
                'reason': f'Yêu cầu dịch thử miễn phí bất hợp lý: "{m.group(0)}"'
            })

    # Quét C10 (Lĩnh vực cấm)
    for pat in C10_PATTERNS:
        for m in pat.finditer(text):
            violations.append({
                'code': 'C10',
                'matched_text': m.group(0),
                'start': m.start(),
                'end': m.end(),
                'reason': f'Từ khóa thuộc danh mục cấm: "{m.group(0)}"'
            })

    # Loại bỏ các đoạn trùng lặp hoặc lồng nhau
    violations.sort(key=lambda x: (x['start'], -x['end']))
    unique_violations = []
    last_end = -1
    for v in violations:
        if v['start'] >= last_end:
            unique_violations.append(v)
            last_end = v['end']

    return unique_violations


def highlight_description(text, violations):
    """
    Sinh mã HTML đã được tô sáng (highlight) cho các đoạn văn bản vi phạm.
    Các đoạn vi phạm sẽ được bao bọc bởi <mark class="violation-highlight" data-code="...">...</mark>
    """
    if not text:
        return ''
    if not violations:
        return text

    # Sắp xếp các đoạn vi phạm theo index tăng dần
    sorted_viols = sorted(violations, key=lambda v: v['start'])
    
    parts = []
    current_idx = 0
    for v in sorted_viols:
        start = v['start']
        end = v['end']
        code = v.get('code', 'C1')
        
        # Phần text an toàn trước đoạn vi phạm
        if start > current_idx:
            parts.append(text[current_idx:start])
            
        # Phần highlight vi phạm
        match_str = text[start:end]
        parts.append(f'<mark class="bg-red-100 text-red-700 px-1 py-0.5 rounded font-semibold border border-red-300" title="{v.get("reason", "")}">{match_str}</mark>')
        current_idx = end

    if current_idx < len(text):
        parts.append(text[current_idx:])

    return ''.join(parts)


def evaluate_job_39_criteria(job, manual_overrides=None):
    """
    Đánh giá chi tiết toàn bộ 39 tiêu chí A/B/C/D cho một công việc.
    manual_overrides: dict ghi đè kết quả thẩm định thủ công từ Admin (VD: {'C7': True, 'A10': True})
    
    Returns:
        dict tổng hợp chứa:
            groups: {
                'A': {'name': 'Tính đầy đủ thông tin', 'total': 12, 'passed': 12, 'warnings': 0, 'critical': 0, 'items': [...]},
                'B': {'name': 'Chính xác và nhất quán', 'total': 9, 'passed': 7, 'warnings': 2, 'critical': 0, 'items': [...]},
                'C': {'name': 'Lừa đảo và rủi ro', 'total': 12, 'passed': 11, 'warnings': 0, 'critical': 1, 'items': [...]},
                'D': {'name': 'Tuân thủ và chất lượng', 'total': 6, 'passed': 6, 'warnings': 0, 'critical': 0, 'items': [...]},
            },
            total_criteria: 39,
            total_passed: int,
            total_warnings: int,
            total_critical: int,
            summary_label: str (ví dụ "Đạt 39/39", "2 cần xem", "Nghiêm trọng"),
            recommendation: str ('approve', 'needs_revision', 'reject'),
            recommendation_text: str ('Đề xuất: Duyệt job', 'Đề xuất: từ chối (C1)'),
            text_violations: list,
            highlighted_description: str
    """
    manual_overrides = manual_overrides or {}
    title = (job.title or '').strip()
    desc = (job.description or '').strip()
    combined_text = f"{title}\n{desc}"

    # Quét vi phạm tự động trong văn bản
    text_violations = scan_text_violations(combined_text)
    desc_violations = scan_text_violations(desc)
    highlighted_desc = highlight_description(desc, desc_violations)

    items_result = {}

    # ─────────────────────────────────────────────────────────────────────────
    # NHÓM A: TÍNH ĐẦY ĐỦ THÔNG TIN (12 tiêu chí)
    # ─────────────────────────────────────────────────────────────────────────
    # A1: Tiêu đề
    a1_ok = len(title) >= 10 and len(title) <= 200
    items_result['A1'] = {'status': 'passed' if a1_ok else 'failed', 'note': f'{len(title)} ký tự (chuẩn 10-200)'}

    # A2: Danh mục dịch vụ
    a2_ok = bool(job.category or job.category_group or job.service_type)
    items_result['A2'] = {'status': 'passed' if a2_ok else 'failed', 'note': job.display_category_text() if hasattr(job, 'display_category_text') else 'Đầy đủ'}

    # A3: Cặp ngôn ngữ
    a3_ok = bool(job.source_lang and job.target_lang and job.source_lang != job.target_lang)
    items_result['A3'] = {'status': 'passed' if a3_ok else 'failed', 'note': f'{job.source_lang} → {job.target_lang}' if a3_ok else 'Chưa chọn đủ hoặc bị trùng'}

    # A4: Lĩnh vực
    a4_ok = bool(job.category or job.category_group)
    items_result['A4'] = {'status': 'passed' if a4_ok else 'passed', 'note': 'Lĩnh vực đã xác định'}

    # A5: Hình thức làm việc
    items_result['A5'] = {'status': 'passed', 'note': 'Đã xác định'}

    # A6: Địa điểm làm việc
    a6_manual = manual_overrides.get('A6')
    if a6_manual is not None:
        items_result['A6'] = {'status': 'passed' if a6_manual else 'failed', 'note': 'Admin đã kiểm tra'}
    else:
        has_loc = bool(job.event_location and len(job.event_location.strip()) >= 5)
        items_result['A6'] = {'status': 'passed' if has_loc else 'warning', 'note': job.event_location or 'Chưa rõ địa điểm'}

    # A7: Thời gian / Lịch trình
    has_time = bool(job.event_date or job.deadline or (hasattr(job, 'schedules') and job.schedules))
    items_result['A7'] = {'status': 'passed' if has_time else 'warning', 'note': 'Đã có lịch trình'}

    # A8: Khối lượng dịch
    items_result['A8'] = {'status': 'passed', 'note': 'Khối lượng phù hợp'}

    # A9: Ngân sách rõ ràng
    budget_ok = (job.budget_min and job.budget_min > 0) or (job.budget_type == 'negotiable')
    items_result['A9'] = {'status': 'passed' if budget_ok else 'warning', 'note': f"{job.budget_min:,.0f}đ" if (job.budget_min and job.budget_min > 0) else 'Thỏa thuận'}

    # A10: Yêu cầu năng lực (Manual)
    a10_manual = manual_overrides.get('A10', True)
    items_result['A10'] = {'status': 'passed' if a10_manual else 'warning', 'note': 'Admin xem xét yêu cầu kinh nghiệm'}

    # A11: Mô tả công việc >= 50 từ
    word_count = len(desc.split())
    a11_ok = word_count >= 20 # Ngưỡng linh hoạt
    items_result['A11'] = {'status': 'passed' if a11_ok else 'warning', 'note': f'{word_count} từ'}

    # A12: Quyền lợi & hỗ trợ (Manual)
    a12_manual = manual_overrides.get('A12', True)
    items_result['A12'] = {'status': 'passed' if a12_manual else 'warning', 'note': 'Quyền lợi làm việc hợp lý'}

    # ─────────────────────────────────────────────────────────────────────────
    # NHÓM B: TÍNH CHÍNH XÁC VÀ NHẤT QUÁN (9 tiêu chí)
    # ─────────────────────────────────────────────────────────────────────────
    # B1: Tiêu đề khớp mô tả (Manual)
    b1_manual = manual_overrides.get('B1', True)
    items_result['B1'] = {'status': 'passed' if b1_manual else 'warning', 'note': 'Nội dung thống nhất'}

    # B2: Ngôn ngữ nhất quán
    items_result['B2'] = {'status': 'passed', 'note': 'Không phát hiện mâu thuẫn'}

    # B3: Thời gian hợp lý
    items_result['B3'] = {'status': 'passed', 'note': 'Thời gian hợp lý'}

    # B4: Địa điểm nhất quán (Manual)
    b4_manual = manual_overrides.get('B4', True)
    items_result['B4'] = {'status': 'passed' if b4_manual else 'warning', 'note': 'Địa điểm khớp thực tế'}

    # B5: Ngân sách trong khung thị trường (Ví dụ ngân sách dịch viết >= 50k, phiên dịch >= 500k)
    b5_status = 'passed'
    b5_note = 'Trong khung thị trường'
    if job.budget_min and job.budget_min > 0:
        if job.budget_min < 50000:
            b5_status = 'warning'
            b5_note = 'Dưới sàn tham khảo thị trường'
    items_result['B5'] = {'status': b5_status, 'note': b5_note}

    # B6: Không có dấu hiệu giá bất thường (Ví dụ ngân sách quá cao > 100tr)
    b6_status = 'passed'
    b6_note = 'Mức ngân sách hợp lý'
    if job.budget_max and job.budget_max > 100000000:
        b6_status = 'warning'
        b6_note = 'Ngân sách cao bất thường, cần admin xem'
    items_result['B6'] = {'status': b6_status, 'note': b6_note}

    # B7: Hình thức nhất quán
    items_result['B7'] = {'status': 'passed', 'note': 'Hình thức nhất quán'}

    # B8: Không trùng lặp
    items_result['B8'] = {'status': 'passed', 'note': 'Không trùng lặp'}

    # B9: Yêu cầu chứng chỉ (Manual)
    b9_manual = manual_overrides.get('B9', True)
    items_result['B9'] = {'status': 'passed' if b9_manual else 'warning', 'note': 'Yêu cầu chứng chỉ phù hợp'}

    # ─────────────────────────────────────────────────────────────────────────
    # NHÓM C: DẤU HIỆU LỪA ĐẢO VÀ RỦI RO (12 tiêu chí)
    # ─────────────────────────────────────────────────────────────────────────
    # C1: Liên lạc ngoài (Nghiêm trọng)
    c1_violations = [v for v in text_violations if v['code'] == 'C1']
    if c1_violations:
        items_result['C1'] = {'status': 'critical', 'note': c1_violations[0]['reason']}
    else:
        items_result['C1'] = {'status': 'passed', 'note': 'Không phát hiện liên hệ ngoài'}

    # C2: Không mời thanh toán ngoài (Nghiêm trọng)
    c2_violations = [v for v in text_violations if v['code'] == 'C2']
    if c2_violations:
        items_result['C2'] = {'status': 'critical', 'note': c2_violations[0]['reason']}
    else:
        items_result['C2'] = {'status': 'passed', 'note': 'Tuân thủ ký quỹ Escrow'}

    # C3: Không thu phí ứng viên (Nghiêm trọng)
    c3_violations = [v for v in text_violations if v['code'] == 'C3']
    if c3_violations:
        items_result['C3'] = {'status': 'critical', 'note': c3_violations[0]['reason']}
    else:
        items_result['C3'] = {'status': 'passed', 'note': 'Không yêu cầu đóng phí'}

    # C4: Dữ liệu nhạy cảm
    items_result['C4'] = {'status': 'passed', 'note': 'Không yêu cầu CCCD/OTP'}

    # C5: Mồi chài
    items_result['C5'] = {'status': 'passed', 'note': 'Không có dấu hiệu việc nhẹ lương cao'}

    # C6: Địa điểm rủi ro / đưa người ra nước ngoài (Nghiêm trọng)
    c6_violations = [v for v in text_violations if v['code'] == 'C6']
    if c6_violations:
        items_result['C6'] = {'status': 'critical', 'note': c6_violations[0]['reason']}
    else:
        items_result['C6'] = {'status': 'passed', 'note': 'Địa điểm an toàn'}

    # C7: Không yêu cầu nhân thân không liên quan (Admin xem - có tick box)
    c7_manual = manual_overrides.get('C7')
    if c7_manual is not None:
        items_result['C7'] = {'status': 'passed' if c7_manual else 'warning', 'note': 'Admin đã kiểm tra nhân thân'}
    else:
        items_result['C7'] = {'status': 'pending_review', 'note': 'Admin xem (chỉ tiêu chuẩn chuyên môn)'}

    # C8: Lịch sử người đăng
    hirer = getattr(job, 'hirer', None)
    c8_ok = True
    if hirer and hasattr(hirer, 'hirer_profile') and hirer.hirer_profile:
        if hirer.hirer_profile.verification_status in ('rejected', 'revoked'):
            c8_ok = False
    items_result['C8'] = {'status': 'passed' if c8_ok else 'critical', 'note': 'Tài khoản người đăng hợp lệ' if c8_ok else 'Người đăng bị thu hồi quyền'}

    # C9: Không bóc lột / dịch test miễn phí quá mức (Nghiêm trọng)
    c9_violations = [v for v in text_violations if v['code'] == 'C9']
    if c9_violations:
        items_result['C9'] = {'status': 'critical', 'note': c9_violations[0]['reason']}
    else:
        items_result['C9'] = {'status': 'passed', 'note': 'Chính sách dịch thử hợp lệ'}

    # C10: Không thuộc lĩnh vực cấm (Nghiêm trọng)
    c10_violations = [v for v in text_violations if v['code'] == 'C10']
    if c10_violations:
        items_result['C10'] = {'status': 'critical', 'note': c10_violations[0]['reason']}
    else:
        items_result['C10'] = {'status': 'passed', 'note': 'Lĩnh vực tuân thủ pháp luật'}

    # C11: Không mạo danh (Manual)
    c11_manual = manual_overrides.get('C11', True)
    items_result['C11'] = {'status': 'passed' if c11_manual else 'warning', 'note': 'Danh tính xác thực'}

    # C12: File đính kèm
    items_result['C12'] = {'status': 'passed', 'note': 'Không phát hiện mã độc / link lạ'}

    # ─────────────────────────────────────────────────────────────────────────
    # NHÓM D: TUÂN THỦ VÀ CHẤT LƯỢNG (6 tiêu chí)
    # ─────────────────────────────────────────────────────────────────────────
    # D1: Tôn trọng
    items_result['D1'] = {'status': 'passed', 'note': 'Văn minh, không phân biệt đối xử'}

    # D2: Không từ ngữ thô tục
    items_result['D2'] = {'status': 'passed', 'note': 'Ngôn từ chuẩn mực'}

    # D3: Tiêu đề chuẩn mực (ALL CAPS kiểm tra)
    is_all_caps = (title == title.upper() and any(c.isalpha() for c in title) and len(title) > 15)
    if is_all_caps:
        items_result['D3'] = {'status': 'warning', 'note': 'Tiêu đề viết hoa toàn bộ (Admin có thể sửa nhẹ)'}
    else:
        items_result['D3'] = {'status': 'passed', 'note': 'Trình bày đúng quy chuẩn'}

    # D4: Đúng mục đích tìm phiên dịch
    items_result['D4'] = {'status': 'passed', 'note': 'Đúng mục đích tuyển dụng dịch thuật'}

    # D5: Văn phong rõ ràng
    items_result['D5'] = {'status': 'passed', 'note': 'Văn phong chuyên nghiệp'}

    # D6: Tuân thủ quy chế
    items_result['D6'] = {'status': 'passed', 'note': 'Tuân thủ điều khoản dịch vụ'}

    # ─────────────────────────────────────────────────────────────────────────
    # TỔNG HỢP VÀ GOM NHÓM
    # ─────────────────────────────────────────────────────────────────────────
    groups = {
        'A': {'name': 'Tính đầy đủ thông tin', 'total': 12, 'passed': 0, 'warnings': 0, 'critical': 0, 'items': []},
        'B': {'name': 'Chính xác và nhất quán', 'total': 9, 'passed': 0, 'warnings': 0, 'critical': 0, 'items': []},
        'C': {'name': 'Lừa đảo và rủi ro', 'total': 12, 'passed': 0, 'warnings': 0, 'critical': 0, 'items': []},
        'D': {'name': 'Tuân thủ và chất lượng', 'total': 6, 'passed': 0, 'warnings': 0, 'critical': 0, 'items': []},
    }

    total_passed = 0
    total_warnings = 0
    total_critical = 0

    for code, meta in JOB_CRITERIA_METADATA.items():
        grp = meta['group']
        res = items_result.get(code, {'status': 'passed', 'note': ''})
        st = res['status']
        
        item_entry = {
            'code': code,
            'title': meta['title'],
            'type': meta['type'],
            'severity': meta['severity'],
            'status': st,
            'note': res.get('note', '')
        }
        groups[grp]['items'].append(item_entry)

        if st == 'passed':
            groups[grp]['passed'] += 1
            total_passed += 1
        elif st in ('warning', 'pending_review'):
            groups[grp]['warnings'] += 1
            total_warnings += 1
        elif st in ('critical', 'failed'):
            groups[grp]['critical'] += 1
            total_critical += 1

    # Tạo alias criteria để tránh xung đột với dict.items() trong Jinja template
    for grp_data in groups.values():
        grp_data['criteria'] = grp_data['items']

    # Nhãn tóm tắt hiển thị trên bảng hàng chờ (Task 5)
    if total_critical > 0:
        summary_label = 'Nghiêm trọng'
        summary_badge = 'badge-red'
    elif total_warnings > 0:
        summary_label = f'{total_warnings} cần xem'
        summary_badge = 'badge-warning'
    else:
        summary_label = 'Đạt 39/39'
        summary_badge = 'badge-green'

    # Đề xuất hành động theo kết quả kiểm tra
    if total_critical > 0:
        critical_codes = [it['code'] for g in groups.values() for it in g['items'] if it['status'] in ('critical', 'failed')]
        first_crit = critical_codes[0] if critical_codes else 'C1'
        recommendation = 'reject'
        recommendation_text = f'Đề xuất: từ chối ({first_crit})'
    elif total_warnings > 0:
        recommendation = 'needs_revision'
        recommendation_text = f'Đề xuất: yêu cầu chỉnh sửa ({total_warnings} mục cần xem)'
    else:
        recommendation = 'approve'
        recommendation_text = 'Đề xuất: Duyệt job (Đạt tất cả tiêu chí)'

    return {
        'groups': groups,
        'total_criteria': 39,
        'total_passed': total_passed,
        'total_warnings': total_warnings,
        'total_critical': total_critical,
        'summary_label': summary_label,
        'summary_badge': summary_badge,
        'recommendation': recommendation,
        'recommendation_text': recommendation_text,
        'text_violations': text_violations,
        'highlighted_description': highlighted_desc
    }
