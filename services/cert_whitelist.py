"""
services/cert_whitelist.py
Định nghĩa danh sách tên miền tin cậy (Domain Whitelist) cho việc xác thực
chứng chỉ trực tuyến qua mã QR và Digital Badge.

Ngăn chặn triệt để các hành vi giả mạo, phishing, hoặc dẫn link về các nền tảng
không chính thức (như Google Drive, Dropbox, trang web cá nhân).
"""

from __future__ import annotations
import urllib.parse
from typing import Tuple, Optional, Dict, List

# Danh mục các tổ chức cấp chứng chỉ và các tên miền chính thức hợp lệ
OFFICIAL_CERT_WHITELIST: Dict[str, Dict[str, any]] = {
    'credly': {
        'display_name': 'Credly (Digital Badge)',
        'domains': ['credly.com', 'www.credly.com'],
        'icon': 'credly',
        'badge_color': 'emerald'
    },
    'accredible': {
        'display_name': 'Accredible (Credential.net)',
        'domains': ['accredible.com', 'credential.net', 'www.credential.net'],
        'icon': 'accredible',
        'badge_color': 'blue'
    },
    'coursera': {
        'display_name': 'Coursera Verified Certificate',
        'domains': ['coursera.org', 'www.coursera.org'],
        'icon': 'coursera',
        'badge_color': 'indigo'
    },
    'ielts_idp': {
        'display_name': 'IDP IELTS Verification',
        'domains': ['idp.com', 'ielts.idp.com', 'www.idp.com'],
        'icon': 'ielts',
        'badge_color': 'rose'
    },
    'ielts_bc': {
        'display_name': 'British Council IELTS',
        'domains': ['britishcouncil.org', 'takeielts.britishcouncil.org', 'www.britishcouncil.org'],
        'icon': 'ielts',
        'badge_color': 'rose'
    },
    'cambridge': {
        'display_name': 'Cambridge English Assessment',
        'domains': ['cambridgeenglish.org', 'certstat.cambridgeenglish.org', 'www.cambridgeenglish.org'],
        'icon': 'cambridge',
        'badge_color': 'purple'
    },
    'ets_toeic': {
        'display_name': 'IIG Việt Nam / ETS (TOEIC & TOEFL)',
        'domains': ['iigvietnam.com', 'www.iigvietnam.com', 'ets.org', 'www.ets.org'],
        'icon': 'toeic',
        'badge_color': 'amber'
    },
    'certif_id': {
        'display_name': 'Certif-ID Blockchain',
        'domains': ['certif-id.com', 'www.certif-id.com'],
        'icon': 'blockchain',
        'badge_color': 'cyan'
    },
    'gov_vn': {
        'display_name': 'Hệ thống Văn bằng Quốc gia / Bộ GD&ĐT (gov.vn)',
        'domains': ['gov.vn', 'moet.gov.vn', 'dichvucong.gov.vn'],
        'icon': 'gov',
        'badge_color': 'emerald'
    }
}


def normalize_cert_url(raw_url: str) -> Optional[str]:
    """
    Chuẩn hóa và làm sạch chuỗi URL tra cứu chứng chỉ.
    Bảo vệ chống inject script hoặc khoảng trắng rác.
    """
    if not raw_url or not isinstance(raw_url, str):
        return None
    url = raw_url.strip()
    if not (url.startswith('http://') or url.startswith('https://')):
        # Tự động thêm https:// nếu thiếu scheme
        if '://' in url:
            return None  # Không chấp nhận ftp://, javascript://, v.v.
        url = 'https://' + url
    return url


def is_whitelisted_domain(raw_url: str) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra một URL có thuộc danh sách tên miền của tổ chức uy tín hay không.

    Thuật toán an toàn:
    - Bóc tách hostname chuẩn từ urlparse.
    - Kiểm tra hostname có kết thúc bằng tên miền tin cậy (exact match hoặc subdomain của domain).
    - Ngăn chặn hoàn toàn Subdomain Spoofing (ví dụ: credly.com.attacker.com) và Phishing (fakecredly.com).

    Returns:
        (is_valid: bool, issuer_key: Optional[str])
    """
    url = normalize_cert_url(raw_url)
    if not url:
        return False, None

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False, None

    # Chỉ chấp nhận giao thức an toàn http / https
    if parsed.scheme.lower() not in ('http', 'https'):
        return False, None

    hostname = (parsed.hostname or '').lower().strip()
    if not hostname:
        return False, None

    for issuer_key, info in OFFICIAL_CERT_WHITELIST.items():
        for trusted_domain in info['domains']:
            trusted_domain = trusted_domain.lower().strip()
            # Khớp chính xác (exact match)
            if hostname == trusted_domain:
                return True, issuer_key
            # Hoặc là subdomain hợp lệ (ví dụ: sub.credential.net hoặc verify.idp.com)
            if hostname.endswith('.' + trusted_domain):
                return True, issuer_key

    return False, None


def get_issuer_info(issuer_key: str) -> Dict[str, any]:
    """
    Lấy thông tin hiển thị của đơn vị cấp chứng chỉ.
    """
    if not issuer_key or issuer_key not in OFFICIAL_CERT_WHITELIST:
        return {
            'display_name': 'Đơn vị cấp khác / Thủ công',
            'icon': 'badge',
            'badge_color': 'slate'
        }
    return OFFICIAL_CERT_WHITELIST[issuer_key]


def get_issuer_display_name(issuer_key: str) -> str:
    """
    Lấy tên hiển thị rút gọn của đơn vị cấp.
    """
    info = get_issuer_info(issuer_key)
    return info.get('display_name', 'Đơn vị ngoài danh mục')

