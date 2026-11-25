import re

def apply_admin_security():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Thêm import nếu chưa có
    if 'from admin_auth import' not in content:
        content = content.replace(
            "from flask import Flask",
            "from admin_auth import admin_login_required, csrf_protected, require_permission\nfrom flask import Flask"
        )

    # Dictionary map từ function name sang permission
    perm_map = {
        'admin_dashboard': 'view_dashboard',
        'admin_jobs': 'view_jobs',
        'admin_flag_job': 'flag_job',
        'admin_approve_job': 'approve_job',
        'admin_delete_job': 'reject_job',
        'admin_users': 'view_users',
        'admin_toggle_user': 'lock_user',
        'admin_translators': 'view_translators',
        'admin_verify_translator': 'verify_translator',
        'admin_reports': 'view_reports',
        'admin_resolve_report': 'resolve_report',
        'admin_reject_report': 'reject_report',
        'admin_reviews': 'view_reviews',
        'admin_hide_review': 'hide_review',
        'admin_restore_review': 'restore_review',
        'admin_proposals': 'view_proposals',
        'admin_contracts': 'view_contracts',
        'admin_schedules': 'view_schedules',
        'admin_audit_logs': 'view_audit_logs',
        'admin_notifications': 'view_notifications',
        'admin_payments': 'view_payments',
        'admin_refund_payment': 'refund_payment',
        'admin_settings': 'super_admin' # Ví dụ mặc định
    }

    def replacer(match):
        route_decl = match.group(1)
        is_post = "methods=['POST']" in route_decl or 'methods=["POST"]' in route_decl
        func_name = match.group(2)
        
        perm = perm_map.get(func_name, 'view_dashboard')
        
        decorators = ["@admin_login_required"]
        if is_post:
            decorators.append("@csrf_protected")
        if perm:
            decorators.append(f"@require_permission('{perm}')")
            
        decorators_str = "\n".join(decorators)
        return f"{route_decl}\n{decorators_str}\ndef {func_name}"

    # Regex bắt tất cả các route có @admin_required
    # Pattern: (@app\.route[^\n]+)\n@admin_required\ndef ([a-zA-Z0-9_]+)
    pattern = re.compile(r'(@app\.route[^\n]+)\n@admin_required\ndef ([a-zA-Z0-9_]+)')
    
    new_content = pattern.sub(replacer, content)

    # Loại bỏ admin_required def cũ nếu không còn dùng
    # Nhưng kệ nó vì có thể import lỗi
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ Đã cập nhật thành công Admin Auth (RBAC, CSRF, Session) cho tất cả các route!")

if __name__ == '__main__':
    apply_admin_security()
