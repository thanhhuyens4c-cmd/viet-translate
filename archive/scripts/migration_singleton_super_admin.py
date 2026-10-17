"""
migration_singleton_super_admin.py — Kiểm tra và tạo ràng buộc duy nhất cho Super Admin.
"""
import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_migration():
    print('[MIGRATION] Đảm bảo duy nhất 1 Super Admin')
    try:
        from app import app
        from models import db, User
    except ImportError as e:
        print(f'[ERROR] Import thất bại: {e}')
        sys.exit(1)
        
    with app.app_context():
        # Kiểm tra số lượng Super Admin
        super_admins = User.query.filter_by(is_admin=True, admin_role='super_admin').all()
        if len(super_admins) > 1:
            print('[ERROR] Dữ liệu vi phạm quy tắc: Đang có nhiều hơn 1 Super Admin!')
            print('Vui lòng xác nhận tài khoản nào được giữ quyền cao nhất và hạ quyền các tài khoản khác (chuyển admin_role thành moderator hoặc None) trước khi chạy migration này.')
            for sa in super_admins:
                print(f' - ID: {sa.id}, Email: {sa.email}')
            sys.exit(1)
            
        print('[MIGRATION] Dữ liệu hợp lệ. Tiến hành tạo Partial Unique Index...')
        
        try:
            db.session.execute(text('''
                CREATE UNIQUE INDEX IF NOT EXISTS unique_super_admin 
                ON "user" (is_admin) 
                WHERE admin_role = 'super_admin';
            '''))
            db.session.commit()
            print('[MIGRATION] Đã tạo Unique Index thành công.')
        except Exception as e:
            db.session.rollback()
            print(f'[ERROR] Lỗi khi tạo index: {e}')
        
if __name__ == '__main__':
    run_migration()
