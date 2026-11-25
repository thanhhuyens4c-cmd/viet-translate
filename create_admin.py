#!/usr/bin/env python3
"""
create_admin.py — CLI tạo tài khoản Admin cho VietTranslate.

CÁCH DÙNG:
    python create_admin.py

Script sẽ hỏi email, tên, mật khẩu và tạo tài khoản Admin trong database.
Mật khẩu được hash bằng werkzeug — KHÔNG bao giờ lưu plain text.

YÊU CẦU:
    - Phải chạy từ thư mục gốc của project (cùng với app.py).
    - Database phải được khởi tạo trước (chạy app.py một lần hoặc tự tạo DB).
    - KHÔNG chạy trên môi trường production nếu không bắt buộc.

BẢO MẬT:
    - Script này không expose qua HTTP.
    - Chỉ Super Admin hoặc người có quyền truy cập server mới chạy được.
    - Mọi việc tạo Admin được khuyến nghị ghi lại thủ công vào Audit Log.
"""

import os
import sys
import getpass
import re

# Đảm bảo import được từ thư mục project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_email(email):
    """Kiểm tra định dạng email cơ bản."""
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password):
    """
    Kiểm tra mật khẩu đủ mạnh:
    - Tối thiểu 12 ký tự
    - Có chữ hoa, chữ thường, số
    Trả về (is_valid, reason).
    """
    if len(password) < 12:
        return False, 'Mật khẩu phải có ít nhất 12 ký tự.'
    if not re.search(r'[A-Z]', password):
        return False, 'Mật khẩu phải có ít nhất một chữ hoa.'
    if not re.search(r'[a-z]', password):
        return False, 'Mật khẩu phải có ít nhất một chữ thường.'
    if not re.search(r'[0-9]', password):
        return False, 'Mật khẩu phải có ít nhất một chữ số.'
    return True, 'ok'


def main():
    print()
    print('=' * 60)
    print('  VietTranslate — Tạo tài khoản Admin')
    print('=' * 60)
    print()
    print('⚠️  Script này chỉ dành cho việc tạo Admin đầu tiên.')
    print('    Không chia sẻ thông tin đăng nhập Admin với bất kỳ ai.')
    print()

    # Nhập thông tin
    name = input('Tên hiển thị Admin: ').strip()
    if not name:
        print('❌ Tên không được để trống.')
        sys.exit(1)

    email = input('Email Admin: ').strip().lower()
    if not validate_email(email):
        print('❌ Email không hợp lệ.')
        sys.exit(1)

    print()
    print('Yêu cầu mật khẩu: ít nhất 12 ký tự, có chữ hoa, thường, số.')
    password = getpass.getpass('Mật khẩu (ẩn): ')
    if not password:
        print('❌ Mật khẩu không được để trống.')
        sys.exit(1)

    pw_valid, pw_reason = validate_password(password)
    if not pw_valid:
        print(f'❌ {pw_reason}')
        sys.exit(1)

    password_confirm = getpass.getpass('Xác nhận mật khẩu (ẩn): ')
    if password != password_confirm:
        print('❌ Mật khẩu xác nhận không khớp.')
        sys.exit(1)

    print()
    print(f'  Tên: {name}')
    print(f'  Email: {email}')
    print(f'  Role: super_admin')
    print()

    confirm = input('Xác nhận tạo tài khoản Admin? [yes/no]: ').strip().lower()
    if confirm not in ('yes', 'y'):
        print('Đã hủy.')
        sys.exit(0)

    print()
    print('Đang kết nối database...')

    try:
        from app import app
        from models import db, User
        from werkzeug.security import generate_password_hash
    except ImportError as e:
        print(f'❌ Không thể import app: {e}')
        print('   Hãy chắc chắn chạy script từ thư mục gốc project.')
        sys.exit(1)

    with app.app_context():
        # Kiểm tra số lượng Super Admin
        super_admins = User.query.filter_by(is_admin=True, admin_role='super_admin').all()
        if len(super_admins) >= 1:
            print('❌ Hệ thống đã có Super Admin. Không thể tạo thêm Super Admin thứ 2 qua script này.')
            print('   Để tạo các Admin cấp dưới (Moderator, Support, Finance...), hãy đăng nhập bằng Super Admin và dùng giao diện Web.')
            sys.exit(1)
            
        print('⚠️  Đang thiết lập tài khoản Super Admin đầu tiên của hệ thống...')

        # Kiểm tra email đã tồn tại chưa
        existing = User.query.filter_by(email=email).first()
        if existing:
            if existing.is_admin:
                print(f'❌ Email {email} đã có tài khoản Admin.')
                sys.exit(1)
            else:
                # User thường muốn nâng lên Admin
                print(f'⚠️  Email {email} đã tồn tại với role={existing.role}.')
                upgrade = input('Nâng lên Admin? [yes/no]: ').strip().lower()
                if upgrade not in ('yes', 'y'):
                    print('Đã hủy.')
                    sys.exit(0)
                existing.is_admin = True
                existing.role = 'admin'
                existing.admin_role = 'super_admin'
                existing.is_active = True
                existing.password_hash = generate_password_hash(password)
                db.session.commit()
                print()
                print('✅ Đã nâng quyền Admin thành công!')
                print(f'   Email: {email}')
                print(f'   Đăng nhập tại: /admin/login')
                return

        # Tạo tài khoản Admin mới
        hashed_pw = generate_password_hash(password)
        admin_user = User(
            name=name,
            email=email,
            password_hash=hashed_pw,
            role='admin',
            is_admin=True,
            admin_role='super_admin',
            is_active=True,
        )
        db.session.add(admin_user)
        db.session.commit()

        print()
        print('✅ Tài khoản Admin đã được tạo thành công!')
        print(f'   Tên: {name}')
        print(f'   Email: {email}')
        print(f'   Đăng nhập tại: /admin/login')
        print()
        print('   ⚠️  Ghi nhớ email và mật khẩu này ở nơi an toàn.')
        print('       Không lưu mật khẩu dưới dạng plain text.')
        print()


if __name__ == '__main__':
    main()
