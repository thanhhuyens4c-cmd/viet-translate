"""
VietTranslate - Payout Methods Service
Quản lý phương thức nhận tiền (thông tin tài khoản ngân hàng thụ hưởng) của phiên dịch viên.
Hỗ trợ lưu trữ trực tiếp trong PostgreSQL (qua SQLAlchemy ORM) đảm bảo tính toàn vẹn ACID giữa các Gunicorn workers,
đồng thời tương thích ngược với fallback file khi chạy kiểm thử độc lập ngoài context.
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from threading import Lock

_file_lock = Lock()

# Danh mục các ngân hàng thương mại phổ biến tại Việt Nam
SUPPORTED_BANKS = [
    {"code": "VCB", "short_name": "Vietcombank", "name": "Ngân hàng TMCP Ngoại thương Việt Nam"},
    {"code": "CTG", "short_name": "VietinBank", "name": "Ngân hàng TMCP Công thương Việt Nam"},
    {"code": "BIDV", "short_name": "BIDV", "name": "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam"},
    {"code": "VBA", "short_name": "Agribank", "name": "Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam"},
    {"code": "TCB", "short_name": "Techcombank", "name": "Ngân hàng TMCP Kỹ thương Việt Nam"},
    {"code": "MB", "short_name": "MB Bank", "name": "Ngân hàng TMCP Quân đội"},
    {"code": "ACB", "short_name": "ACB", "name": "Ngân hàng TMCP Á Châu"},
    {"code": "VPB", "short_name": "VPBank", "name": "Ngân hàng TMCP Việt Nam Thịnh Vượng"},
    {"code": "TPB", "short_name": "TPBank", "name": "Ngân hàng TMCP Tiên Phong"},
    {"code": "STB", "short_name": "Sacombank", "name": "Ngân hàng TMCP Sài Gòn Thương Tín"},
    {"code": "HDB", "short_name": "HDBank", "name": "Ngân hàng TMCP Phát triển TP.HCM"},
    {"code": "VIB", "short_name": "VIB", "name": "Ngân hàng TMCP Quốc tế Việt Nam"},
    {"code": "SHB", "short_name": "SHB", "name": "Ngân hàng TMCP Sài Gòn - Hà Nội"},
    {"code": "MSB", "short_name": "MSB", "name": "Ngân hàng TMCP Hàng Hải Việt Nam"},
    {"code": "OCB", "short_name": "OCB", "name": "Ngân hàng TMCP Phương Đông"},
    {"code": "LPB", "short_name": "LPBank", "name": "Ngân hàng TMCP Lộc Phát Việt Nam"},
    {"code": "SEAB", "short_name": "SeABank", "name": "Ngân hàng TMCP Đông Nam Á"},
    {"code": "BAB", "short_name": "Bac A Bank", "name": "Ngân hàng TMCP Bắc Á"},
]

def _is_db_active():
    """Kiểm tra xem ứng dụng có đang trong Flask Application Context và có thể dùng DB không."""
    try:
        from flask import has_app_context
        if not has_app_context():
            return False
        from models import db
        return db.session is not None
    except Exception:
        return False

def _get_store_path():
    """Lấy đường dẫn tệp JSON lưu trữ phương thức nhận tiền (fallback)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    instance_dir = os.path.join(base_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    return os.path.join(instance_dir, 'interpreter_payout_methods.json')

def mask_account_number(account_number: str) -> str:
    """Che số tài khoản ngân hàng, chỉ hiển thị 4 chữ số cuối (Ví dụ: •••• •••• •••• 6789)."""
    if not account_number:
        return ""
    clean = str(account_number).strip()
    if len(clean) <= 4:
        return "•••• " + clean
    last4 = clean[-4:]
    return f"•••• •••• •••• {last4}"

def normalize_account_holder_name(name: str) -> str:
    """Chuẩn hóa tên chủ tài khoản thành in hoa không khoảng trắng thừa."""
    if not name:
        return ""
    return " ".join(str(name).strip().split()).upper()

def get_supported_banks():
    """Trả về danh mục các ngân hàng hỗ trợ."""
    return list(SUPPORTED_BANKS)

def _read_data() -> dict:
    """Đọc toàn bộ dữ liệu từ tệp lưu trữ (fallback)."""
    path = _get_store_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _write_data(data: dict) -> bool:
    """Ghi dữ liệu an toàn (atomic write) vào tệp lưu trữ (fallback)."""
    path = _get_store_path()
    tmp_path = path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False

def get_user_payout_data(user_id) -> dict:
    """Lấy toàn bộ dữ liệu phương thức và lịch sử của một người dùng."""
    if _is_db_active():
        try:
            from models import PayoutMethod, PayoutHistory
            methods = PayoutMethod.query.filter_by(user_id=int(user_id)).order_by(PayoutMethod.created_at.asc()).all()
            history = PayoutHistory.query.filter_by(user_id=int(user_id)).order_by(PayoutHistory.created_at.desc()).all()
            return {
                "methods": [m.to_dict() for m in methods],
                "history": [h.to_dict() for h in history]
            }
        except Exception:
            pass

    with _file_lock:
        data = _read_data()
        key = str(user_id)
        return data.get(key, {"methods": [], "history": []})

def get_payout_methods(user_id) -> list:
    """Lấy danh sách các phương thức nhận tiền của một phiên dịch viên."""
    user_data = get_user_payout_data(user_id)
    return user_data.get("methods", [])

def get_default_payout_method(user_id) -> dict:
    """Lấy phương thức nhận tiền mặc định của phiên dịch viên."""
    if _is_db_active():
        try:
            from models import PayoutMethod
            pm = PayoutMethod.query.filter_by(user_id=int(user_id), is_default=True).first()
            if not pm:
                pm = PayoutMethod.query.filter_by(user_id=int(user_id)).order_by(PayoutMethod.created_at.asc()).first()
            return pm.to_dict() if pm else None
        except Exception:
            pass

    methods = get_payout_methods(user_id)
    for m in methods:
        if m.get("is_default"):
            return m
    return methods[0] if methods else None

def get_payout_method_by_id(user_id, method_id: str):
    """Tìm phương thức nhận tiền theo mã ID và xác thực quyền sở hữu."""
    if _is_db_active():
        try:
            from models import PayoutMethod
            pm = PayoutMethod.query.filter_by(user_id=int(user_id), id=str(method_id)).first()
            return pm.to_dict() if pm else None
        except Exception:
            pass

    methods = get_payout_methods(user_id)
    for m in methods:
        if m.get("id") == str(method_id):
            return m
    return None

def add_payout_method(user_id, bank_code: str, account_number: str, account_holder_name: str, branch: str = "", set_as_default: bool = False):
    """
    Thêm phương thức nhận tiền mới.
    Kiểm tra hợp lệ dữ liệu và ghi vào store an toàn (PostgreSQL ORM hoặc fallback JSON).
    """
    bank_code = str(bank_code or '').strip().upper()
    account_number = str(account_number or '').strip()
    account_holder_name = normalize_account_holder_name(account_holder_name)
    branch = str(branch or '').strip()

    # 1. Kiểm tra ngân hàng
    matched_bank = next((b for b in SUPPORTED_BANKS if b["code"].upper() == bank_code), None)
    if not matched_bank:
        return False, "Vui lòng chọn ngân hàng hợp lệ từ danh sách hỗ trợ."

    # 2. Kiểm tra số tài khoản (6 - 20 chữ số)
    if not re.match(r'^\d{6,20}$', account_number):
        return False, "Số tài khoản ngân hàng không hợp lệ (phải gồm 6 đến 20 chữ số liên tục)."

    # 3. Kiểm tra tên chủ tài khoản
    if len(account_holder_name) < 3 or len(account_holder_name) > 100:
        return False, "Tên chủ tài khoản phải từ 3 đến 100 ký tự."

    # 4. Kiểm tra độ dài chi nhánh
    if len(branch) > 120:
        return False, "Tên chi nhánh không được vượt quá 120 ký tự."

    # 5. Xử lý lưu trữ
    if _is_db_active():
        try:
            from models import db, PayoutMethod, PayoutHistory
            u_id = int(user_id)
            existing = PayoutMethod.query.filter_by(user_id=u_id, bank_code=matched_bank["code"], account_number=account_number).first()
            if existing:
                return False, f"Tài khoản {matched_bank['short_name']} với số tài khoản này đã tồn tại trong danh sách của bạn."

            count = PayoutMethod.query.filter_by(user_id=u_id).count()
            should_be_default = (count == 0) or bool(set_as_default)

            if should_be_default:
                PayoutMethod.query.filter_by(user_id=u_id).update({PayoutMethod.is_default: False})

            method_id = f"pm_{uuid.uuid4().hex[:12]}"
            masked = mask_account_number(account_number)

            new_method = PayoutMethod(
                id=method_id,
                user_id=u_id,
                bank_code=matched_bank["code"],
                bank_short_name=matched_bank["short_name"],
                bank_name=matched_bank["name"],
                account_number=account_number,
                masked_account_number=masked,
                account_holder_name=account_holder_name,
                branch=branch,
                is_default=should_be_default,
                status="active",
                status_label="Khai báo hợp lệ · Đang hoạt động"
            )
            db.session.add(new_method)

            history_entry = PayoutHistory(
                user_id=u_id,
                method_id=method_id,
                action="add",
                bank=matched_bank["short_name"],
                masked_account=masked,
                summary=f"Đã thêm tài khoản {matched_bank['short_name']} ({masked})"
            )
            db.session.add(history_entry)
            db.session.commit()
            return True, new_method.to_dict()
        except Exception as e:
            from models import db
            db.session.rollback()
            return False, f"Lỗi hệ thống khi lưu phương thức nhận tiền: {str(e)}"

    with _file_lock:
        data = _read_data()
        key = str(user_id)
        user_record = data.get(key, {"methods": [], "history": []})
        methods = user_record.get("methods", [])
        history = user_record.get("history", [])

        # Kiểm tra trùng lặp số tài khoản cùng ngân hàng
        for existing in methods:
            if existing.get("bank_code") == matched_bank["code"] and existing.get("account_number") == account_number:
                return False, f"Tài khoản {matched_bank['short_name']} với số tài khoản này đã tồn tại trong danh sách của bạn."

        # Nếu chưa có phương thức nào, phương thức đầu tiên bắt buộc là mặc định
        is_first = (len(methods) == 0)
        should_be_default = is_first or bool(set_as_default)

        if should_be_default:
            for m in methods:
                m["is_default"] = False

        now_iso = datetime.now(timezone.utc).isoformat()
        method_id = f"pm_{uuid.uuid4().hex[:12]}"
        masked = mask_account_number(account_number)

        new_method = {
            "id": method_id,
            "bank_code": matched_bank["code"],
            "bank_short_name": matched_bank["short_name"],
            "bank_name": matched_bank["name"],
            "account_number": account_number,
            "masked_account_number": masked,
            "account_holder_name": account_holder_name,
            "branch": branch,
            "is_default": should_be_default,
            "status": "active",
            "status_label": "Khai báo hợp lệ · Đang hoạt động",
            "created_at": now_iso,
            "updated_at": now_iso
        }

        methods.append(new_method)
        history.append({
            "action": "add",
            "method_id": method_id,
            "bank": matched_bank["short_name"],
            "masked_account": masked,
            "timestamp": now_iso,
            "summary": f"Đã thêm tài khoản {matched_bank['short_name']} ({masked})"
        })

        user_record["methods"] = methods
        user_record["history"] = history
        data[key] = user_record

        if _write_data(data):
            return True, new_method
        else:
            return False, "Không thể lưu thông tin vào hệ thống. Vui lòng thử lại sau."

def set_default_payout_method(user_id, method_id: str):
    """Đặt một phương thức làm phương thức nhận tiền mặc định."""
    method_id = str(method_id).strip()

    if _is_db_active():
        try:
            from models import db, PayoutMethod, PayoutHistory
            u_id = int(user_id)
            target = PayoutMethod.query.filter_by(user_id=u_id, id=method_id).first()
            if not target:
                return False, "Phương thức nhận tiền không tồn tại hoặc bạn không có quyền thao tác."

            if target.is_default:
                return True, "Phương thức này hiện đã là phương thức mặc định."

            PayoutMethod.query.filter_by(user_id=u_id).update({PayoutMethod.is_default: False})
            target.is_default = True
            target.updated_at = datetime.utcnow()

            history_entry = PayoutHistory(
                user_id=u_id,
                method_id=method_id,
                action="set_default",
                bank=target.bank_short_name,
                masked_account=target.masked_account_number,
                summary=f"Đặt {target.bank_short_name} ({target.masked_account_number}) làm mặc định"
            )
            db.session.add(history_entry)
            db.session.commit()
            return True, "Đã cập nhật phương thức nhận tiền mặc định thành công."
        except Exception as e:
            from models import db
            db.session.rollback()
            return False, f"Lỗi hệ thống khi cập nhật phương thức mặc định: {str(e)}"

    with _file_lock:
        data = _read_data()
        key = str(user_id)
        user_record = data.get(key, {"methods": [], "history": []})
        methods = user_record.get("methods", [])
        history = user_record.get("history", [])

        target = None
        for m in methods:
            if m.get("id") == method_id:
                target = m
                break

        if not target:
            return False, "Phương thức nhận tiền không tồn tại hoặc bạn không có quyền thao tác."

        if target.get("is_default"):
            return True, "Phương thức này hiện đã là phương thức mặc định."

        for m in methods:
            m["is_default"] = (m.get("id") == method_id)
            if m.get("id") == method_id:
                m["updated_at"] = datetime.now(timezone.utc).isoformat()

        now_iso = datetime.now(timezone.utc).isoformat()
        history.append({
            "action": "set_default",
            "method_id": method_id,
            "bank": target.get("bank_short_name"),
            "masked_account": target.get("masked_account_number"),
            "timestamp": now_iso,
            "summary": f"Đặt {target.get('bank_short_name')} ({target.get('masked_account_number')}) làm mặc định"
        })

        user_record["methods"] = methods
        user_record["history"] = history
        data[key] = user_record

        if _write_data(data):
            return True, "Đã cập nhật phương thức nhận tiền mặc định thành công."
        else:
            return False, "Không thể cập nhật phương thức mặc định. Vui lòng thử lại sau."

def delete_payout_method(user_id, method_id: str):
    """Xóa một phương thức nhận tiền. Nếu là mặc định và còn tài khoản khác, tự động chuyển mặc định sang tài khoản đầu tiên còn lại."""
    method_id = str(method_id).strip()

    if _is_db_active():
        try:
            from models import db, PayoutMethod, PayoutHistory
            u_id = int(user_id)
            target = PayoutMethod.query.filter_by(user_id=u_id, id=method_id).first()
            if not target:
                return False, "Phương thức nhận tiền không tồn tại hoặc bạn không có quyền thao tác."

            was_default = target.is_default
            bank_short = target.bank_short_name
            masked = target.masked_account_number

            db.session.delete(target)

            if was_default:
                remaining = PayoutMethod.query.filter(PayoutMethod.user_id == u_id, PayoutMethod.id != method_id).order_by(PayoutMethod.created_at.asc()).first()
                if remaining:
                    remaining.is_default = True
                    remaining.updated_at = datetime.utcnow()

            history_entry = PayoutHistory(
                user_id=u_id,
                method_id=method_id,
                action="delete",
                bank=bank_short,
                masked_account=masked,
                summary=f"Đã xóa tài khoản {bank_short} ({masked})"
            )
            db.session.add(history_entry)
            db.session.commit()
            return True, "Đã xóa phương thức nhận tiền thành công."
        except Exception as e:
            from models import db
            db.session.rollback()
            return False, f"Lỗi hệ thống khi xóa phương thức nhận tiền: {str(e)}"

    with _file_lock:
        data = _read_data()
        key = str(user_id)
        user_record = data.get(key, {"methods": [], "history": []})
        methods = user_record.get("methods", [])
        history = user_record.get("history", [])

        target_idx = None
        for idx, m in enumerate(methods):
            if m.get("id") == method_id:
                target_idx = idx
                break

        if target_idx is None:
            return False, "Phương thức nhận tiền không tồn tại hoặc bạn không có quyền thao tác."

        target = methods.pop(target_idx)
        was_default = target.get("is_default", False)

        # Nếu phương thức bị xóa là mặc định và vẫn còn phương thức khác, chỉ định phương thức đầu tiên làm mặc định mới
        if was_default and len(methods) > 0:
            methods[0]["is_default"] = True
            methods[0]["updated_at"] = datetime.now(timezone.utc).isoformat()

        now_iso = datetime.now(timezone.utc).isoformat()
        history.append({
            "action": "delete",
            "method_id": method_id,
            "bank": target.get("bank_short_name"),
            "masked_account": target.get("masked_account_number"),
            "timestamp": now_iso,
            "summary": f"Đã xóa tài khoản {target.get('bank_short_name')} ({target.get('masked_account_number')})"
        })

        user_record["methods"] = methods
        user_record["history"] = history
        data[key] = user_record

        if _write_data(data):
            return True, "Đã xóa phương thức nhận tiền thành công."
        else:
            return False, "Không thể xóa phương thức nhận tiền. Vui lòng thử lại sau."
