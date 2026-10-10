import logging
from datetime import datetime, timedelta
from models import User, Contract, TranslatorSchedule, Job, Proposal
from services.schedule import normalize_schedule_datetime, is_schedule_complete, check_translator_schedule_conflict, ScheduleCheckError

logger = logging.getLogger(__name__)

TRANSLATOR_CONFIRM_HOURS = 24

class BookingConflictError(Exception):
    pass

class BookingValidationError(Exception):
    pass

def create_contract_booking(
    *,
    hirer_id,
    translator_id,
    agreed_price,
    scheduled_date,
    start_time,
    end_time,
    location=None,
    job_id=None,
    service_id=None,
    proposal_id=None,
):
    from app import db
    from sqlalchemy.exc import IntegrityError
    
    try:
        current_user = User.query.get(hirer_id)
        if not current_user:
            raise BookingValidationError("Người thuê không tồn tại.")

        translator = User.query.get(translator_id)
        if not translator or getattr(translator, 'role', '') != 'translator' or not getattr(translator, 'is_active', True):
            raise BookingValidationError("Phiên dịch viên này hiện không hoạt động hoặc không tồn tại.")

        if current_user.id == translator.id:
            raise BookingValidationError("Bạn không thể tự thuê chính mình.")

        job = None
        if job_id:
            job = (
                Job.query
                .with_for_update()
                .filter_by(id=job_id)
                .first()
            )
            if not job:
                raise BookingValidationError("Công việc không tồn tại.")
            if job.status != 'open':
                raise BookingConflictError("Công việc này không còn mở.")
                
            existing = Contract.query.filter_by(job_id=job_id).first()
            if existing:
                raise BookingConflictError("Công việc này đã được tạo hợp đồng.")

        # Đặt trực tiếp qua dịch vụ: phiên dịch viên phải xác nhận trước khi khách thanh toán.
        # Đặt qua đề xuất (job) thì PDV đã chủ động ứng tuyển nên bỏ qua bước này.
        needs_confirmation = bool(service_id) and not job_id

        contract = Contract(
            job_id=job_id,
            proposal_id=proposal_id,
            service_id=service_id,
            hirer_id=hirer_id,
            translator_id=translator.id,
            agreed_price=agreed_price,
            scheduled_date=scheduled_date,
            scheduled_time_start=start_time,
            scheduled_time_end=end_time,
            location=location or '',
            status='awaiting_translator' if needs_confirmation else 'escrow_pending'
        )
        db.session.add(contract)
        db.session.flush()

        from services.scheduling import reserve_slot, SlotTakenError
        from services.schedule import parse_job_all_schedule_entries
        
        try:
            if job:
                entries = parse_job_all_schedule_entries(job)
                if entries:
                    for entry in entries:
                        reserve_slot(
                            translator_id=translator.id,
                            scheduled_date=entry['date_str'],
                            start_time=entry['start_time'].strftime('%H:%M'),
                            end_time=entry['end_time'].strftime('%H:%M'),
                            contract_id=contract.id,
                            job_id=job_id,
                            service_id=service_id
                        )
            else:
                # Direct booking without job
                if scheduled_date and start_time and end_time:
                    reserve_slot(
                        translator_id=translator.id,
                        scheduled_date=scheduled_date,
                        start_time=start_time,
                        end_time=end_time,
                        contract_id=contract.id,
                        job_id=job_id,
                        service_id=service_id
                    )
        except SlotTakenError as e:
            db.session.rollback()
            raise BookingConflictError(str(e))
        except Exception as e:
            db.session.rollback()
            if isinstance(e, ScheduleCheckError):
                raise BookingValidationError(str(e))
            raise BookingValidationError(str(e))

        if needs_confirmation:
            schedule.expires_at = datetime.utcnow() + timedelta(hours=TRANSLATOR_CONFIRM_HOURS)

        if proposal_id:
            proposal = Proposal.query.get(proposal_id)
            if proposal:
                proposal.status = 'accepted'

        if job:
            job.status = 'contracted'

        from app import create_notification
        from services.notifications import should_notify
        if should_notify(translator, 'CONTRACT_CREATED'):
            try:
                create_notification(
                    user_id=translator.id,
                    notification_type='CONTRACT_CREATED',
                    title='Yêu cầu đặt lịch mới' if needs_confirmation else 'Hợp đồng mới được tạo',
                    message=(f'Khách hàng {current_user.name} muốn đặt lịch với bạn. '
                             f'Vui lòng xác nhận trong {TRANSLATOR_CONFIRM_HOURS} giờ.') if needs_confirmation
                            else f'Khách hàng {current_user.name} đã đặt lịch với bạn.',
                    url=f'/transaction/{contract.id}',
                    related_contract_id=contract.id
                )
            except Exception:
                pass

        db.session.commit()
        return contract

    except IntegrityError:
        db.session.rollback()
        raise BookingConflictError("Công việc này vừa được người khác đặt hoặc đã xảy ra lỗi toàn vẹn dữ liệu.")
    except (BookingConflictError, BookingValidationError, ScheduleCheckError):
        db.session.rollback()
        raise

    except Exception as e:
        db.session.rollback()
        logger.exception("Unexpected error during create_contract_booking: %s", e)
        raise BookingValidationError("đã xảy ra lỗi hệ thống khi tạo hợp đồng.") from e
