"""
services/cert_verifier.py
Module bóc tách và thẩm định chứng chỉ trực tuyến từ mã QR / Digital Badge.
Hoạt động cực nhẹ (Lightweight), không dùng Headless Browser, tối ưu cho VPS 1 vCPU / 2GB RAM.
100% độc lập, sử dụng httpx (hoặc urllib tiêu chuẩn) và HTMLParser có sẵn trong Python.
Hỗ trợ:
- Open Badges v2/v3 JSON-LD specification.
- Open Graph Meta Tags fallback.
- Thuật toán so khớp tên không phân biệt dấu tiếng Việt.
"""

from __future__ import annotations
import re
import json
import socket
import ipaddress
import difflib
import unicodedata
import urllib.parse
from html.parser import HTMLParser
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

try:
    import httpx
except ImportError:
    httpx = None

from services.cert_whitelist import is_whitelisted_domain, get_issuer_display_name, normalize_cert_url

MAX_HTML_DOWNLOAD_BYTES = 2 * 1024 * 1024
DEFAULT_HTTP_TIMEOUT = 5.0  # giây


class CertMetadataHTMLParser(HTMLParser):
    """
    Parser HTML tiêu chuẩn bằng thư viện tích hợp sẵn của Python.
    Bóc tách toàn bộ thẻ script JSON-LD và các thẻ meta Open Graph.
    """
    def __init__(self):
        super().__init__()
        self.in_json_ld = False
        self.json_ld_scripts: List[str] = []
        self.meta_tags: Dict[str, str] = {}
        self._current_script_text: List[str] = []

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        attr_dict = {k.lower(): v for k, v in attrs if k}

        if tag_lower == 'script':
            script_type = attr_dict.get('type', '').lower().strip()
            if script_type == 'application/ld+json':
                self.in_json_ld = True
                self._current_script_text = []
        elif tag_lower == 'meta':
            prop = attr_dict.get('property', '') or attr_dict.get('name', '')
            content = attr_dict.get('content', '')
            if prop and content:
                self.meta_tags[prop.lower().strip()] = content.strip()

    def handle_data(self, data):
        if self.in_json_ld:
            self._current_script_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self.in_json_ld:
            self.in_json_ld = False
            self.json_ld_scripts.append(''.join(self._current_script_text))


def remove_accents(input_str: str) -> str:
    """
    Chuẩn hóa và loại bỏ toàn bộ dấu tiếng Việt, chuyển thành chữ thường.
    Hỗ trợ cả ký tự 'đ' và 'Đ'.
    """
    if not input_str or not isinstance(input_str, str):
        return ""
    cleaned = input_str.replace('đ', 'd').replace('Đ', 'D')
    nfkd_form = unicodedata.normalize('NFKD', cleaned)
    res = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    res = re.sub(r'[^a-zA-Z0-9\s]', ' ', res)
    return re.sub(r'\s+', ' ', res).lower().strip()


def calculate_name_match(name1: str, name2: str) -> Tuple[bool, float, str]:
    """
    So khớp họ tên giữa tài khoản người dùng và thông tin trích xuất trên chứng chỉ.
    Áp dụng mô hình 3 vùng độ tin cậy (Confidence Zones):
    - 'high' (score >= 0.85): Đủ điều kiện xem xét tự duyệt.
    - 'medium' (0.60 <= score < 0.85): Thiếu tên đệm hoặc đảo thứ tự chưa trọn vẹn -> Cần Admin kiểm tra.
    - 'low' (score < 0.60): Sai lệch lớn hoặc khác người -> Không tự duyệt.

    Returns:
        (is_match: bool, match_score: float, confidence_zone: str)
    """
    n1 = remove_accents(name1)
    n2 = remove_accents(name2)
    if not n1 or not n2:
        return False, 0.0, 'low'

    if n1 == n2:
        return True, 1.0, 'high'

    words1 = [w for w in n1.split() if w]
    words2 = [w for w in n2.split() if w]
    if not words1 or not words2:
        return False, 0.0, 'low'

    set1 = set(words1)
    set2 = set(words2)

    # Nếu tập từ giống hệt nhau (chỉ khác thứ tự như "Nguyen Van A" vs "A Nguyen Van")
    if set1 == set2:
        return True, 1.0, 'high'

    intersect = set1.intersection(set2)
    union = set1.union(set2)
    jaccard = len(intersect) / len(union) if union else 0.0

    # Kiểm tra họ (từ đầu) và tên chính (từ cuối)
    first_name_match = (words1[-1] == words2[-1] or words1[-1] in set2 or words2[-1] in set1)
    last_name_match = (words1[0] == words2[0] or words1[0] in set2 or words2[0] in set1)

    # Đo độ tương đồng chuỗi tổng thể
    seq_ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
    sorted_seq_ratio = difflib.SequenceMatcher(None, ' '.join(sorted(words1)), ' '.join(sorted(words2))).ratio()
    best_seq = max(seq_ratio, sorted_seq_ratio)

    combined_score = round(0.5 * jaccard + 0.5 * best_seq, 2)

    # Phân loại vào 3 vùng
    # Nếu họ khác nhau hoàn toàn mà không có từ họ nào trùng thì hạ độ tin cậy để tránh nhầm người nhà
    if words1[0] != words2[0] and words1[0] not in set2 and words2[0] not in set1:
        if combined_score > 0.70:
            combined_score = 0.65  # Hạ về vùng medium để Admin kiểm tra

    if combined_score >= 0.85 and (first_name_match or last_name_match):
        return True, combined_score, 'high'
    elif combined_score >= 0.60:
        return False, combined_score, 'medium'
    else:
        return False, combined_score, 'low'


def extract_cert_data_from_html(html_text: str, source_url: str = "") -> Dict[str, Any]:
    """
    Bóc tách thông tin chứng chỉ từ nội dung HTML:
    1. Ưu tiên: Thẻ JSON-LD chuẩn Open Badges specification.
    2. Fallback: Thẻ Open Graph meta tags.
    """
    result = {
        'cert_name': '',
        'recipient_name': '',
        'issuer_name': '',
        'issued_date': '',
        'expires_date': '',
        'is_expired': False,
        'raw_description': '',
        'parse_method': 'none'
    }

    if not html_text:
        return result

    parser = CertMetadataHTMLParser()
    try:
        parser.feed(html_text)
    except Exception:
        pass

    # ─── BƯỚC 1: TÌM KIẾM THẺ JSON-LD (OPEN BADGES) ──────────────────────────
    for raw_content in parser.json_ld_scripts:
        try:
            if not raw_content.strip():
                continue
            data = json.loads(raw_content)

            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                if '@graph' in data and isinstance(data['@graph'], list):
                    items = data['@graph']
                else:
                    items = [data]

            for item in items:
                if not isinstance(item, dict):
                    continue

                recipient = item.get('recipient') or item.get('recipientProfile')
                badge = item.get('badge')
                name = item.get('name')

                # Trích xuất tên người nhận
                rec_name = ''
                if isinstance(recipient, dict):
                    rec_name = recipient.get('name') or recipient.get('identity') or recipient.get('hashedIdentity') or ''
                elif isinstance(recipient, str):
                    rec_name = recipient

                # Trích xuất tên chứng chỉ
                c_name = ''
                if isinstance(badge, dict):
                    c_name = badge.get('name') or ''
                    if not result['issuer_name']:
                        issuer_obj = badge.get('issuer')
                        if isinstance(issuer_obj, dict):
                            result['issuer_name'] = issuer_obj.get('name', '')
                        elif isinstance(issuer_obj, str):
                            result['issuer_name'] = issuer_obj
                if not c_name and name:
                    c_name = name

                # Trích xuất ngày cấp
                issued = item.get('issuedOn') or item.get('dateCreated') or item.get('validFrom') or ''
                expires = item.get('expires') or item.get('validUntil') or ''

                if rec_name or c_name:
                    if rec_name and not result['recipient_name']:
                        result['recipient_name'] = str(rec_name).strip()
                    if c_name and not result['cert_name']:
                        result['cert_name'] = str(c_name).strip()
                    if issued and not result['issued_date']:
                        result['issued_date'] = str(issued)[:10]
                    if expires and not result['expires_date']:
                        result['expires_date'] = str(expires)[:10]

                    result['parse_method'] = 'json-ld'
        except Exception:
            continue

    # ─── BƯỚC 2: FALLBACK SANG OPEN GRAPH META TAGS ─────────────────────────
    og_title = parser.meta_tags.get('og:title', '')
    og_desc = parser.meta_tags.get('og:description', '')
    og_site = parser.meta_tags.get('og:site_name', '')

    if not result['cert_name'] and og_title:
        result['cert_name'] = og_title
        if result['parse_method'] == 'none':
            result['parse_method'] = 'open-graph'

    if not result['issuer_name'] and og_site:
        result['issuer_name'] = og_site

    result['raw_description'] = og_desc

    if not result['recipient_name'] and (og_title or og_desc):
        text_to_search = f"{og_title}. {og_desc}"
        match_issued_to = re.search(r'issued\s+to\s+([A-Za-z0-9\sÀ-ỹ]+?)(?:\s+by|\s+on|\.|\,|$)', text_to_search, re.IGNORECASE)
        if match_issued_to:
            result['recipient_name'] = match_issued_to.group(1).strip()
        else:
            match_cert_for = re.search(r'certified\s+([A-Za-z0-9\sÀ-ỹ]+?)(?:\s+by|\s+on|\.|\,|$)', text_to_search, re.IGNORECASE)
            if match_cert_for:
                result['recipient_name'] = match_cert_for.group(1).strip()

    if result['expires_date']:
        try:
            exp_dt = datetime.strptime(result['expires_date'], '%Y-%m-%d')
            if exp_dt < datetime.utcnow():
                result['is_expired'] = True
        except Exception:
            pass

    return result


def is_safe_destination(url: str) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra bảo mật URL:
    - Bắt buộc giao thức http hoặc https.
    - Phân giải DNS và kiểm tra IP không được thuộc các dải private, loopback, link-local, multicast.
    - Ngăn chặn triệt để SSRF (Server-Side Request Forgery).
    """
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = (parsed.hostname or '').strip().lower()
        if not hostname:
            return False, "Không xác định được hostname từ URL."

        if parsed.scheme.lower() not in ('http', 'https'):
            return False, f"Giao thức '{parsed.scheme}' không được hỗ trợ."

        if parsed.username or parsed.password:
            return False, "URL chứa thông tin xác thực nhúng không an toàn."

        # Chặn các hostname localhost tường minh
        if hostname in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
            return False, "Không cho phép truy vấn máy chủ cục bộ (localhost)."

        # Phân giải IP
        try:
            addr_info = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return False, "Không thể phân giải tên miền (DNS lookup failed)."

        if not addr_info:
            return False, "Không tìm thấy địa chỉ IP cho tên miền này."

        for item in addr_info:
            ip_str = item[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or 
                    ip_obj.is_multicast or ip_obj.is_reserved or ip_obj.is_unspecified):
                    return False, f"Địa chỉ IP đích ({ip_str}) thuộc dải mạng nội bộ hoặc không an toàn (SSRF Blocked)."
            except ValueError:
                return False, f"Địa chỉ IP ({ip_str}) không hợp lệ."

        return True, None
    except Exception as e:
        return False, f"Lỗi kiểm tra an toàn URL: {str(e)[:100]}"


def fetch_url_html(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Thực hiện HTTP GET an toàn, kiểm tra SSRF trước khi gửi request.
    Giới hạn timeout 5s và dung lượng tối đa 2MB.
    Returns: (html_text, error_message)
    """
    is_safe, ssrf_err = is_safe_destination(url)
    if not is_safe:
        return None, f"Bị chặn bởi bộ lọc an toàn SSRF: {ssrf_err}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 VietTranslate-Verifier/1.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8'
    }

    if httpx is not None:
        try:
            with httpx.Client(timeout=DEFAULT_HTTP_TIMEOUT, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 404:
                    return None, "HTTP_404_NOT_FOUND"
                if response.status_code != 200:
                    return None, f"Máy chủ đơn vị cấp phản hồi mã lỗi HTTP {response.status_code}"

                # Kiểm tra sau redirect URL có bị trỏ về IP nội bộ không
                final_url = str(response.url)
                is_final_safe, final_ssrf_err = is_safe_destination(final_url)
                if not is_final_safe:
                    return None, f"Chuyển hướng (Redirect) không an toàn: {final_ssrf_err}"

                content = response.content[:MAX_HTML_DOWNLOAD_BYTES]
                html_text = content.decode('utf-8', errors='replace')
                return html_text, None
        except httpx.TimeoutException:
            return None, "Yêu cầu kết nối quá thời gian chờ (Timeout sau 5s)"
        except httpx.ConnectError:
            return None, "Không thể kết nối đến máy chủ của trang web đích"
        except Exception as e:
            return None, f"Lỗi truy xuất đường dẫn: {str(e)[:100]}"
    else:
        # Fallback chuẩn thư viện tiêu chuẩn Python urllib
        import urllib.request
        import urllib.error
        import ssl
        try:
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=DEFAULT_HTTP_TIMEOUT) as response:
                    final_url = response.geturl()
                    is_final_safe, final_ssrf_err = is_safe_destination(final_url)
                    if not is_final_safe:
                        return None, f"Chuyển hướng (Redirect) không an toàn: {final_ssrf_err}"

                    content = response.read(MAX_HTML_DOWNLOAD_BYTES)
                    html_text = content.decode('utf-8', errors='replace')
                    return html_text, None
            except urllib.error.HTTPError as http_err:
                if http_err.code == 404:
                    return None, "HTTP_404_NOT_FOUND"
                return None, f"Máy chủ phản hồi mã lỗi HTTP {http_err.code}"
            except urllib.error.URLError as url_err:
                if isinstance(url_err.reason, ssl.SSLError) or 'certificate verify failed' in str(url_err.reason):
                    unverified_ctx = ssl._create_unverified_context()
                    with urllib.request.urlopen(req, timeout=DEFAULT_HTTP_TIMEOUT, context=unverified_ctx) as response:
                        content = response.read(MAX_HTML_DOWNLOAD_BYTES)
                        html_text = content.decode('utf-8', errors='replace')
                        return html_text, None
                raise
        except Exception as e:
            return None, f"Lỗi kết nối urllib: {str(e)[:100]}"


def verify_certificate(
    user_name: str,
    raw_url: str,
    declared_cert_name: str = ""
) -> Dict[str, Any]:
    """
    Quy trình kiểm thực toàn diện cho một chứng chỉ:
    1. Kiểm tra Domain Whitelist.
    2. Chống SSRF & Tải HTML an toàn (0đ).
    3. Bóc tách dữ liệu JSON-LD / Open Graph.
    4. Đối soát họ tên theo 3 vùng tin cậy (high, medium, low).
    5. Đánh giá trạng thái chứng chỉ: 'verified', 'manual_review', 'expired', 'revoked', 'unable_to_verify', 'not_verified'.

    Returns: Dict kết quả chuẩn hóa
    """
    url = normalize_cert_url(raw_url)
    if not url:
        return {
            'success': False,
            'is_valid': False,
            'cert_status': 'not_verified',
            'confidence_zone': 'low',
            'error': 'Đường dẫn chứng chỉ không hợp lệ hoặc bị để trống.',
            'raw_url': raw_url
        }

    # 1. Kiểm tra Domain Whitelist
    is_whitelisted, issuer_key = is_whitelisted_domain(url)
    if not is_whitelisted:
        return {
            'success': False,
            'is_valid': False,
            'cert_status': 'not_verified',
            'confidence_zone': 'low',
            'error': 'Tên miền không thuộc danh mục tổ chức cấp chứng chỉ được công nhận.',
            'raw_url': url
        }

    issuer_display_name = get_issuer_display_name(issuer_key)

    # 2. Tải HTML an toàn (chống SSRF)
    html_text, err = fetch_url_html(url)
    if err or not html_text:
        cert_status = 'revoked' if err == "HTTP_404_NOT_FOUND" else 'unable_to_verify'
        err_msg = 'Chứng chỉ không tồn tại hoặc đã bị thu hồi (Mã 404).' if err == "HTTP_404_NOT_FOUND" else (err or 'Không thể tải nội dung trang xác thực.')
        return {
            'success': False,
            'is_valid': False,
            'cert_status': cert_status,
            'confidence_zone': 'low',
            'issuer_key': issuer_key,
            'issuer_name': issuer_display_name,
            'error': err_msg,
            'raw_url': url
        }

    # 3. Bóc tách dữ liệu
    extracted = extract_cert_data_from_html(html_text, source_url=url)

    cert_name = extracted.get('cert_name') or declared_cert_name or 'Chứng chỉ đã xác thực'
    recipient_name = extracted.get('recipient_name') or ''
    issued_date = extracted.get('issued_date') or ''
    is_expired = extracted.get('is_expired', False)

    # 4. Đối soát họ tên theo 3 vùng
    name_match = False
    match_score = 0.0
    confidence_zone = 'low'
    if recipient_name and user_name:
        name_match, match_score, confidence_zone = calculate_name_match(user_name, recipient_name)
    elif not recipient_name:
        # Nếu trang web không ghi tên người nhận (chỉ ghi tên chứng chỉ công khai)
        confidence_zone = 'medium'

    # 5. Xác định trạng thái chứng chỉ cuối cùng
    if is_expired:
        cert_status = 'expired'
        is_valid = False
    elif not bool(cert_name):
        cert_status = 'not_verified'
        is_valid = False
    elif confidence_zone == 'high':
        cert_status = 'verified'
        is_valid = True
    elif confidence_zone == 'medium':
        cert_status = 'manual_review'
        is_valid = False
    else:  # 'low'
        cert_status = 'not_verified'
        is_valid = False

    return {
        'success': True,
        'is_valid': is_valid,
        'cert_status': cert_status,
        'confidence_zone': confidence_zone,
        'issuer_key': issuer_key,
        'issuer_name': issuer_display_name,
        'cert_name': cert_name,
        'recipient_name': recipient_name,
        'name_match': name_match,
        'name_match_score': match_score,
        'issued_date': issued_date,
        'is_expired': is_expired,
        'raw_url': url,
        'parse_method': extracted.get('parse_method', 'none'),
        'error': None
    }
