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


def calculate_name_match(name1: str, name2: str) -> Tuple[bool, float]:
    """
    So khớp họ tên giữa tài khoản người dùng và thông tin trích xuất trên chứng chỉ.
    Xử lý được thứ tự viết tên (VD: "Nguyen Van A" vs "Van A Nguyen" hoặc "A Nguyen").

    Returns:
        (is_match: bool, match_score: float)
    """
    n1 = remove_accents(name1)
    n2 = remove_accents(name2)
    if not n1 or not n2:
        return False, 0.0

    if n1 == n2:
        return True, 1.0

    words1 = set(n1.split())
    words2 = set(n2.split())
    if not words1 or not words2:
        return False, 0.0

    intersect = words1.intersection(words2)
    smaller_len = min(len(words1), len(words2))

    # Nếu tất cả các từ của một tên nằm trọn trong tên còn lại
    if len(intersect) == smaller_len and smaller_len >= 2:
        score = len(intersect) / max(len(words1), len(words2))
        return True, round(score, 2)

    # Chỉ số tương đồng Jaccard
    jaccard = len(intersect) / len(words1.union(words2))
    if jaccard >= 0.5:
        return True, round(jaccard, 2)

    return False, round(jaccard, 2)


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


def fetch_url_html(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Thực hiện HTTP GET an toàn, giới hạn timeout và dung lượng byte tải về.
    Sử dụng httpx (hoặc urllib.request fallback).
    Returns: (html_text, error_message)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 VietTranslate-Verifier/1.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8'
    }

    if httpx is not None:
        try:
            with httpx.Client(timeout=DEFAULT_HTTP_TIMEOUT, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                if response.status_code != 200:
                    return None, f"Máy chủ đơn vị cấp phản hồi mã lỗi HTTP {response.status_code}"

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
                    content = response.read(MAX_HTML_DOWNLOAD_BYTES)
                    html_text = content.decode('utf-8', errors='replace')
                    return html_text, None
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
    2. Tải HTML an toàn (0đ).
    3. Bóc tách dữ liệu JSON-LD / Open Graph.
    4. Đối soát họ tên người dùng và tính hợp lệ.

    Returns: Dict kết quả chuẩn hóa
    """
    url = normalize_cert_url(raw_url)
    if not url:
        return {
            'success': False,
            'is_valid': False,
            'error': 'Đường dẫn chứng chỉ không hợp lệ hoặc bị để trống.',
            'raw_url': raw_url
        }

    # 1. Kiểm tra Domain Whitelist
    is_whitelisted, issuer_key = is_whitelisted_domain(url)
    if not is_whitelisted:
        return {
            'success': False,
            'is_valid': False,
            'error': 'Tên miền không thuộc danh mục tổ chức cấp chứng chỉ được công nhận.',
            'raw_url': url
        }

    issuer_display_name = get_issuer_display_name(issuer_key)

    # 2. Tải HTML
    html_text, err = fetch_url_html(url)
    if err or not html_text:
        return {
            'success': False,
            'is_valid': False,
            'issuer_key': issuer_key,
            'issuer_name': issuer_display_name,
            'error': err or 'Không thể tải nội dung trang xác thực.',
            'raw_url': url
        }

    # 3. Bóc tách dữ liệu
    extracted = extract_cert_data_from_html(html_text, source_url=url)

    cert_name = extracted.get('cert_name') or declared_cert_name or 'Chứng chỉ đã xác thực'
    recipient_name = extracted.get('recipient_name') or ''
    issued_date = extracted.get('issued_date') or ''
    is_expired = extracted.get('is_expired', False)

    # 4. Đối soát họ tên
    name_match = False
    match_score = 0.0
    if recipient_name and user_name:
        name_match, match_score = calculate_name_match(user_name, recipient_name)

    is_valid = bool(cert_name) and not is_expired
    if recipient_name:
        is_valid = is_valid and (name_match or match_score >= 0.5)

    return {
        'success': True,
        'is_valid': is_valid,
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
