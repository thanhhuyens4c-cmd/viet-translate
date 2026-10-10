import os
import sys

# Đảm bảo có thể import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Contract, TranslatorSchedule
from services.schedule import parse_contract_datetime, is_schedule_complete
from datetime import datetime

def migrate_legacy_schedules():
    with app.app_context():
        # Lấy tất cả Contract đang không bị hủy
        contracts = Contract.query.filter(~Contract.status.in_(['cancelled', 'failed'])).all()
        migrated_count = 0

        for contract in contracts:
            # Kiểm tra xem Contract này đã có Schedule nào chưa
            existing = TranslatorSchedule.query.filter_by(contract_id=contract.id).first()
            if existing:
                continue
            
            # Phân tích ngày giờ từ Contract cũ
            parsed = parse_contract_datetime(contract)
            if not is_schedule_complete(parsed):
                # Thử lấy từ Job nếu Contract bị thiếu
                if contract.job:
                    from services.schedule import parse_job_datetime
                    parsed = parse_job_datetime(contract.job)
                
            if is_schedule_complete(parsed):
                status = 'active'
                if contract.status == 'completed':
                    status = 'completed'
                elif contract.status == 'escrow_pending':
                    status = 'reserved'

                schedule = TranslatorSchedule(
                    translator_id=contract.translator_id,
                    contract_id=contract.id,
                    job_id=contract.job_id,
                    service_id=contract.service_id,
                    scheduled_date=parsed['date'],
                    start_time=parsed['start_time'],
                    end_time=parsed['end_time'],
                    status=status,
                    created_at=contract.created_at or datetime.utcnow()
                )
                db.session.add(schedule)
                migrated_count += 1
        
        if migrated_count > 0:
            db.session.commit()
            print(f"✅ Đã tạo bù {migrated_count} lịch làm việc (TranslatorSchedule) cho các Hợp đồng cũ.")
        else:
            print("✅ Không có Hợp đồng cũ nào cần tạo bù lịch (tất cả đã có lịch hoặc không có thời gian).")

if __name__ == '__main__':
    migrate_legacy_schedules()
