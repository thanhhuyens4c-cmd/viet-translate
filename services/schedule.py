"""
Schedule helpers for VietTranslate.

Provides safe parsing of the legacy String-typed date/time fields stored on
Job and Contract, and normalises them into proper Python date/time objects
that can be used to populate TranslatorSchedule.

Policy:
  - Never raise/crash on bad data.
  - Log all parsing failures to stderr (Flask will capture them in debug mode).
  - Return None for any field that cannot be parsed.
"""
import logging
from datetime import date, time, datetime

class ScheduleCheckError(Exception):
    pass


logger = logging.getLogger(__name__)

# ─── Common date/time format patterns ────────────────────────────────────────
DATE_FMTS = [
    '%Y-%m-%d',      # ISO  – "2024-11-30"
    '%d/%m/%Y',      # VN   – "30/11/2024"
    '%d-%m-%Y',      # dash – "30-11-2024"
    '%Y/%m/%d',
    '%d.%m.%Y',
]

TIME_FMTS = [
    '%H:%M',          # "08:30"
    '%H:%M:%S',       # "08:30:00"
    '%I:%M %p',       # "08:30 AM"
    '%H.%M',          # "08.30"
]


def _parse_date(value) -> date | None:
    """Try to parse *value* into a date. Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in DATE_FMTS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    logger.warning("TranslatorSchedule: could not parse date %r", raw)
    return None


def _parse_time(value) -> time | None:
    """Try to parse *value* into a time. Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in TIME_FMTS:
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    logger.warning("TranslatorSchedule: could not parse time %r", raw)
    return None


def normalize_schedule_datetime(date_value, start_value, end_value):
    """
    Normalise (potentially String) date/time inputs.

    Returns:
        (parsed_date, parsed_start, parsed_end)
        Any element may be None if parsing failed; callers must check.
    """
    d = _parse_date(date_value)
    t_start = _parse_time(start_value)
    t_end = _parse_time(end_value)

    # If we are missing any component, this is a partial or empty schedule.
    # We do NOT raise an error here because a job might only have a deadline date, not a scheduled event time.
    if not d or not t_start or not t_end:
        return d, t_start, t_end

    if t_end <= t_start:
        raise ScheduleCheckError("Thời gian kết thúc phải sau thời gian bắt đầu.")

    return d, t_start, t_end


def parse_job_datetime(job):
    """
    Extract and normalise schedule fields from a Job instance.

    Reads the legacy String fields:
      job.event_date, job.event_time_start, job.event_time_end

    Returns:
        dict with keys 'date', 'start_time', 'end_time'
        (values are proper Python objects or None)
    """
    try:
        d, t_start, t_end = normalize_schedule_datetime(
            getattr(job, 'event_date', None),
            getattr(job, 'event_time_start', None),
            getattr(job, 'event_time_end', None),
        )
        return {'date': d, 'start_time': t_start, 'end_time': t_end}
    except Exception as exc:
        logger.exception("parse_job_datetime error for job_id=%s", getattr(job, 'id', '?'))
        if isinstance(exc, ScheduleCheckError):
            raise
        raise ScheduleCheckError("Không thể xác minh ngày giờ công việc.") from exc


def parse_contract_datetime(contract):
    """
    Extract and normalise schedule fields from a Contract instance.

    Reads the legacy String fields:
      contract.scheduled_date, contract.scheduled_time_start, contract.scheduled_time_end

    Returns:
        dict with keys 'date', 'start_time', 'end_time'
    """
    try:
        d, t_start, t_end = normalize_schedule_datetime(
            getattr(contract, 'scheduled_date', None),
            getattr(contract, 'scheduled_time_start', None),
            getattr(contract, 'scheduled_time_end', None),
        )
        return {'date': d, 'start_time': t_start, 'end_time': t_end}
    except Exception as exc:
        logger.exception("parse_contract_datetime error for contract_id=%s", getattr(contract, 'id', '?'))
        if isinstance(exc, ScheduleCheckError):
            raise
        raise ScheduleCheckError("Không thể xác minh ngày giờ hợp đồng.") from exc


def is_schedule_complete(parsed: dict) -> bool:
    """Return True only when all three parsed fields are valid."""
    return all(parsed.get(k) is not None for k in ('date', 'start_time', 'end_time'))


# ─── Conflict Checker ─────────────────────────────────────────────────────────

def build_effective_interval(
    scheduled_date,
    start_time,
    end_time,
    buffer_before_minutes=0,
    buffer_after_minutes=0,
):
    """
    Return datetime start/end sau khi áp dụng buffer.
    Không dùng .time() để tránh lỗi vượt ngày.
    """
    from datetime import datetime, timedelta
    from datetime import time as dt_time

    def _to_time(t):
        if isinstance(t, dt_time):
            return t
        if isinstance(t, str):
            h, m = t.strip().split(':')
            return dt_time(int(h), int(m))
        raise ValueError(f'Unsupported time type: {type(t)}')

    dt_start = datetime.combine(scheduled_date, _to_time(start_time))
    dt_end = datetime.combine(scheduled_date, _to_time(end_time))

    effective_start = dt_start - timedelta(minutes=buffer_before_minutes)
    effective_end = dt_end + timedelta(minutes=buffer_after_minutes)

    return effective_start, effective_end

def datetime_intervals_overlap(
    new_start,
    new_end,
    existing_start,
    existing_end,
):
    return (
        new_start < existing_end
        and new_end > existing_start
    )

def check_translator_schedule_conflict(
    translator_id,
    scheduled_date,
    start_time,
    end_time,
    buffer_before_minutes=None,
    buffer_after_minutes=None,
    exclude_contract_id=None,
):
    """
    Check whether a proposed time-slot conflicts with an existing
    TranslatorSchedule entry for the same translator on the same date.
    """
    from models import TranslatorSchedule

    if buffer_before_minutes is None:
        buffer_before_minutes = 0
    if buffer_after_minutes is None:
        buffer_after_minutes = 30

    try:
        # Apply buffers to the *new* slot so we detect near-misses
        effective_start, effective_end = build_effective_interval(
            scheduled_date,
            start_time,
            end_time,
            buffer_before_minutes,
            buffer_after_minutes
        )

        # Fetch all non-cancelled schedules for this translator on that date
        existing = (
            TranslatorSchedule.query
            .filter_by(translator_id=translator_id, scheduled_date=scheduled_date)
            .filter(TranslatorSchedule.status != 'cancelled')
            .all()
        )

        for entry in existing:
            # Skip the entry we're rescheduling
            if exclude_contract_id and entry.contract_id == exclude_contract_id:
                continue

            entry_effective_start, entry_effective_end = build_effective_interval(
                entry.scheduled_date,
                entry.start_time,
                entry.end_time,
                getattr(entry, 'buffer_before_minutes', 0),
                getattr(entry, 'buffer_after_minutes', 30)
            )

            if datetime_intervals_overlap(effective_start, effective_end,
                                          entry_effective_start, entry_effective_end):
                return {
                    'conflict': True,
                    'existing_contract_id': entry.contract_id,
                    'start_time': entry.start_time.strftime('%H:%M'),
                    'end_time':   entry.end_time.strftime('%H:%M'),
                    'message': (
                        f'Phiên dịch viên đã có lịch trong khoảng thời gian này '
                        f'({entry.start_time.strftime("%H:%M")}–'
                        f'{entry.end_time.strftime("%H:%M")}).'
                    ),
                }

        return {'conflict': False}

    except Exception as exc:
        logger.exception("Schedule conflict check failed for translator_id=%s", translator_id)
        if isinstance(exc, ScheduleCheckError):
            raise
        raise ScheduleCheckError("Không thể xác minh lịch của phiên dịch viên.") from exc
