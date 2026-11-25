# -*- coding: utf-8 -*-
"""
seed_100_jobs.py
Idempotent script to seed 100 diverse, realistic interpreter jobs into VietTranslate.
Run via: python seed_100_jobs.py
"""

import sys
import os
import json
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

# Đảm bảo đường dẫn import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, HirerProfile, TranslatorProfile, Job, Proposal

DEMO_HIRERS = [
    {
        'email': 'hirer_vtech@viettranslate.demo',
        'name': 'Tập đoàn Công nghệ V-Tech',
        'company': 'V-Tech Solutions & AI Lab',
        'title': 'Trưởng phòng Hợp tác Quốc tế',
        'location': 'Tòa nhà Keangnam, Cầu Giấy, Hà Nội'
    },
    {
        'email': 'hirer_medical@viettranslate.demo',
        'name': 'Bệnh viện Đa khoa Quốc tế Hạnh Phúc',
        'company': 'Hạnh Phúc International Hospital',
        'title': 'Ban Hợp tác Y khoa & Chuyển giao Công nghệ',
        'location': 'Quận 1, TP. Hồ Chí Minh'
    },
    {
        'email': 'hirer_lexpartners@viettranslate.demo',
        'name': 'Hãng Luật Quốc tế LexPartners',
        'company': 'LexPartners Law Firm LLC',
        'title': 'Luật sư Điều hành & Trọng tài viên',
        'location': 'Bitexco Financial Tower, Quận 1, TP.HCM'
    },
    {
        'email': 'hirer_apexmanuf@viettranslate.demo',
        'name': 'Tổ hợp Chế tạo Apex Precision',
        'company': 'Apex Precision Manufacturing Co.',
        'title': 'Giám đốc Vận hành Nhà máy',
        'location': 'KCN DEEP C, Đình Vũ, Hải Phòng'
    },
    {
        'email': 'hirer_vinastruct@viettranslate.demo',
        'name': 'Công ty CP Đầu tư & Hạ tầng Vinastruct',
        'company': 'Vinastruct Infrastructure Group',
        'title': 'Ban Quản lý Dự án Giao thông & Metro',
        'location': 'TP. Thủ Đức, TP. Hồ Chí Minh'
    },
    {
        'email': 'hirer_mekongcap@viettranslate.demo',
        'name': 'Quỹ Đầu tư & Quản lý Tài sản Mekong',
        'company': 'Mekong Capital & Ventures',
        'title': 'Giám đốc Thẩm định Đầu tư M&A',
        'location': 'Lotte Center, Ba Đình, Hà Nội'
    },
    {
        'email': 'hirer_saigontour@viettranslate.demo',
        'name': 'Saigon Global Travel & Hospitality',
        'company': 'Saigon Global Luxury Tours',
        'title': 'Quản lý Dịch vụ VIP & Famtrip',
        'location': 'Quận 3, TP. Hồ Chí Minh'
    },
    {
        'email': 'hirer_diplomacy@viettranslate.demo',
        'name': 'Viện Đối ngoại & Hợp tác Phát triển Á - Âu',
        'company': 'Institute for Asian-European Diplomacy',
        'title': 'Điều phối viên Dự án ODA',
        'location': 'Hoàn Kiếm, Hà Nội'
    },
    {
        'email': 'hirer_greenpower@viettranslate.demo',
        'name': 'Tập đoàn Năng lượng Xanh GreenPower',
        'company': 'GreenPower Renewables & Offshore',
        'title': 'Trưởng ban Kỹ thuật Dự án Điện gió',
        'location': 'Vũng Tàu, Bà Rịa - Vũng Tàu'
    },
    {
        'email': 'hirer_transglobal@viettranslate.demo',
        'name': 'Hãng Giao nhận Vận tải TransGlobal',
        'company': 'TransGlobal Freight & Marine Logistics',
        'title': 'Giám đốc Khai thác Cảng & Chuỗi cung ứng',
        'location': 'Khu ngoại quan Cái Mép, Bà Rịa - Vũng Tàu'
    },
    {
        'email': 'hirer_vasepfood@viettranslate.demo',
        'name': 'Hiệp hội Thực phẩm & Nông sản Sạch V-Agri',
        'company': 'V-Agri Food Export Alliance',
        'title': 'Phụ trách Xúc tiến Thương mại Quốc tế',
        'location': 'Ninh Kiều, Cần Thơ'
    },
    {
        'email': 'hirer_edu_intl@viettranslate.demo',
        'name': 'Tổ chức Giáo dục Quốc tế Global Pathway',
        'company': 'Global Pathway Education',
        'title': 'Giám đốc Tuyển sinh & Liên kết Đại học',
        'location': 'Hải Châu, Đà Nẵng'
    }
]

DEMO_TRANSLATORS = [
    {
        'name': 'Lê Văn Cường', 'email': 'trans_en@test.com', 'lang': 'Tiếng Anh',
        'title': 'Biên/Phiên dịch viên tiếng Anh cấp cao (IELTS 8.5 / Cabin)',
        'bio': '10 năm kinh nghiệm dịch cabin hội nghị quốc tế, đàm phán hợp đồng thương mại và tài chính.'
    },
    {
        'name': 'Trần Thị Bích', 'email': 'trans_jp@test.com', 'lang': 'Tiếng Nhật',
        'title': 'Phiên dịch tiếng Nhật thương mại & kỹ thuật sản xuất (JLPT N1)',
        'bio': '8 năm làm việc tại Tokyo, chuyên dịch chuyển giao công nghệ tự động hóa và M&A.'
    },
    {
        'name': 'Phạm Thị Dung', 'email': 'trans_kr@test.com', 'lang': 'Tiếng Hàn',
        'title': 'Phiên dịch tiếng Hàn Quốc chuyên nghiệp (TOPIK 6)',
        'bio': 'Kinh nghiệm dịch tháp tùng các tập đoàn Hàn Quốc, sự kiện văn hóa và y tế thẩm mỹ.'
    },
    {
        'name': 'Hoàng Minh Đức', 'email': 'trans_cn@test.com', 'lang': 'Tiếng Trung',
        'title': 'Phiên dịch tiếng Trung thương mại & công nghiệp (HSK 6)',
        'bio': 'Chuyên phiên dịch đàm phán xuất nhập khẩu nông sản, nhà máy và thương mại điện tử.'
    },
    {
        'name': 'Nguyễn Thị Mai Hương', 'email': 'trans_fr@test.com', 'lang': 'Tiếng Pháp',
        'title': 'Phiên dịch cabin tiếng Pháp ngoại giao & y khoa (DALF C1)',
        'bio': 'Thạc sĩ Ngôn ngữ Paris, nhiều năm phiên dịch hội thảo y tế và hợp tác ODA Pháp - Việt.'
    },
    {
        'name': 'Vũ Đình Khoa', 'email': 'trans_de@test.com', 'lang': 'Tiếng Đức',
        'title': 'Phiên dịch kỹ thuật & cơ khí chế tạo tiếng Đức (Goethe C1)',
        'bio': 'Kỹ sư cơ khí tốt nghiệp tại Stuttgart, chuyên sâu về ô tô, tự động hóa và năng lượng tái tạo.'
    },
    {
        'name': 'Đặng Thị Thanh Hà', 'email': 'trans_ru@test.com', 'lang': 'Tiếng Nga',
        'title': 'Phiên dịch tiếng Nga dầu khí, hàng hải & du lịch (TRKI 3)',
        'bio': 'Hơn 12 năm phiên dịch dự án dầu khí Vietsovpetro và các đoàn ngoại giao Nga.'
    },
    {
        'name': 'Lý Hoàng Nam', 'email': 'trans_th@test.com', 'lang': 'Tiếng Thái',
        'title': 'Phiên dịch thương mại & bán lẻ tiếng Thái Lan',
        'bio': 'Tốt nghiệp ĐH Chulalongkorn, chuyên dịch xúc tiến thương mại F&B và du lịch Thái - Việt.'
    },
    {
        'name': 'Bùi Quang Huy', 'email': 'trans_pt@test.com', 'lang': 'Tiếng Bồ Đào Nha',
        'title': 'Phiên dịch tiếng Bồ Đào Nha thương mại nông nghiệp & thủy sản',
        'bio': 'Chuyên gia dịch thuật hồ sơ xuất nhập khẩu và giao thương thị trường Brazil và Nam Mỹ.'
    },
    {
        'name': 'Ngô Thị Lan Anh', 'email': 'trans_es@test.com', 'lang': 'Tiếng Tây Ban Nha',
        'title': 'Phiên dịch tiếng Tây Ban Nha du lịch, văn hóa & thương mại (DELE C1)',
        'bio': '7 năm thông dịch các hội thảo văn hóa, khảo sát thị trường tiêu dùng và đoàn khách quốc tế.'
    }
]

def seed_100_jobs():
    """Hàm nạp dữ liệu chính."""
    print("=== BẮT ĐẦU NẠP 100 VIỆC LÀM PHIÊN DỊCH VÀO VIETTRANSLATE ===")

    # 1. Đảm bảo Hirers tồn tại
    hirer_users = []
    for h in DEMO_HIRERS:
        user = User.query.filter_by(email=h['email']).first()
        if not user:
            user = User(
                name=h['name'],
                email=h['email'],
                password_hash=generate_password_hash('123456'),
                role='hirer',
                is_active=True
            )
            db.session.add(user)
            db.session.flush()

        profile = HirerProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            profile = HirerProfile(
                user_id=user.id,
                company=h['company'],
                title=h['title'],
                location=h['location'],
                rating=4.9
            )
            db.session.add(profile)
        hirer_users.append(user)

    db.session.commit()
    print(f"-> Đã đảm bảo {len(hirer_users)} tài khoản Nhà tuyển dụng (Hirers) sẵn sàng.")

    # 2. Đảm bảo Translators tồn tại
    translator_map = {}
    for t in DEMO_TRANSLATORS:
        user = User.query.filter_by(email=t['email']).first()
        if not user:
            user = User(
                name=t['name'],
                email=t['email'],
                password_hash=generate_password_hash('123456'),
                role='translator',
                is_active=True
            )
            db.session.add(user)
            db.session.flush()

        profile = TranslatorProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            profile = TranslatorProfile(
                user_id=user.id,
                title=t['title'],
                bio=t['bio'],
                languages=f"Tiếng Việt, {t['lang']}",
                rating=4.9,
                total_reviews=18,
                total_jobs=24,
                is_verified=True
            )
            db.session.add(profile)
        translator_map[t['lang']] = user

    db.session.commit()
    print(f"-> Đã đảm bảo {len(translator_map)} Phiên dịch viên (Translators) với đầy đủ ngôn ngữ.")

    # 3. Đọc danh sách 100 jobs từ jobs_data.json
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jobs_data.json')
    if not os.path.exists(json_path):
        print(f"LỖI: Không tìm thấy file {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        jobs_data = json.load(f)

    print(f"-> Đọc thành công {len(jobs_data)} cấu hình việc làm từ jobs_data.json.")

    base_date = date.today()
    now = datetime.utcnow()

    added_jobs_count = 0
    skipped_jobs_count = 0
    added_proposals_count = 0

    for idx, item in enumerate(jobs_data):
        existing_job = Job.query.filter_by(title=item['title']).first()
        if existing_job:
            skipped_jobs_count += 1
            continue

        hirer = hirer_users[item['hirer_index'] % len(hirer_users)]
        created_at = now - timedelta(days=item.get('days_ago', 0), hours=idx % 12, minutes=idx * 7 % 60)
        deadline = base_date + timedelta(days=item.get('deadline_days', 10))

        job = Job(
            hirer_id=hirer.id,
            title=item['title'],
            description=item['description'],
            category=item.get('category', 'Hội nghị'),
            category_group=item.get('category_group', 'interpretation_other'),
            service_type=item.get('service_type', 'conference'),
            source_lang=item['source_lang'],
            target_lang=item['target_lang'],
            budget_type=item['budget_type'],
            budget_min=item['budget_min'],
            budget_max=item.get('budget_max'),
            event_date=item['event_date'],
            event_time_start=item.get('event_time_start', '08:30'),
            event_time_end=item.get('event_time_end', '17:00'),
            event_location=item['event_location'],
            deadline=deadline,
            status='open',
            moderation_status='approved',
            is_flagged=False,
            created_at=created_at
        )
        db.session.add(job)
        db.session.flush()
        added_jobs_count += 1

        # Gán báo giá/hồ sơ ứng tuyển (proposals) mẫu để hiển thị chân thực
        # Số lượng proposals từ 0 đến 4
        prop_count = (idx * 3 + 1) % 5  # 0, 1, 2, 3, 4
        relevant_trans = []
        if item['source_lang'] in translator_map:
            relevant_trans.append(translator_map[item['source_lang']])
        if item['target_lang'] in translator_map and translator_map[item['target_lang']] not in relevant_trans:
            relevant_trans.append(translator_map[item['target_lang']])

        for p_idx, trans in enumerate(relevant_trans[:prop_count]):
            prop = Proposal(
                job_id=job.id,
                translator_id=trans.id,
                cover_letter=f"Tôi có trên 5 năm kinh nghiệm phiên dịch chuyên sâu trong lĩnh vực này và hoàn toàn đáp ứng tốt yêu cầu công việc. Rất mong được hợp tác cùng Quý công ty!",
                price=job.budget_min or 1500000,
                time_estimate="Theo đúng lịch trình",
                status='pending',
                created_at=created_at + timedelta(hours=2 + p_idx)
            )
            db.session.add(prop)
            added_proposals_count += 1

    db.session.commit()

    total_jobs = Job.query.count()
    open_jobs = Job.query.filter_by(status='open', is_flagged=False).count()

    print(f"\n=== KẾT QUẢ NẠP DỮ LIỆU ===")
    print(f"+ Số việc làm mới thêm: {added_jobs_count}")
    print(f"+ Số việc làm đã có từ trước (bỏ qua): {skipped_jobs_count}")
    print(f"+ Số báo giá/ứng tuyển (proposals) được tạo: {added_proposals_count}")
    print(f"+ Tổng số việc làm trong database: {total_jobs}")
    print(f"+ Tổng số việc làm đang MỞ (open) trên sàn: {open_jobs}")
    print("=== HOÀN TẤT THÀNH CÔNG ===")

if __name__ == '__main__':
    with app.app_context():
        seed_100_jobs()
