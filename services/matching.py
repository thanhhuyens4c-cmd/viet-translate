import unicodedata
from models import Job, Proposal, Contract, TranslatorPreference, TranslatorProfile, User
from datetime import datetime

def translator_is_available_for_job(translator_id, job):
    from services.schedule import (
        parse_job_datetime,
        is_schedule_complete,
        check_translator_schedule_conflict
    )
    
    try:
        parsed = parse_job_datetime(job)
    except Exception as e:
        import logging
        logging.error(f"Cannot parse schedule for job {job.id}: {e}")
        return False, "Thời gian không hợp lệ"
        
    if not is_schedule_complete(parsed):
        return True, "Không có lịch cố định"
        
    try:
        result = check_translator_schedule_conflict(
            translator_id=translator_id,
            scheduled_date=parsed['date'],
            start_time=parsed['start_time'],
            end_time=parsed['end_time']
        )
    except Exception as e:
        import logging
        logging.error(f"Error checking schedule for translator {translator_id}: {e}")
        return False, "Lỗi kiểm tra lịch"
        
    if result['conflict']:
        return False, result['message']
        
    return True, "Có lịch trống"

def normalize_text(value):
    if not value:
        return ''
    return unicodedata.normalize('NFKD', str(value)).encode('ASCII', 'ignore').decode('utf-8').lower().strip()

def calculate_job_match_score(translator, job, lang='vi'):
    from translations import t as t_lookup
    # Base score 0 to 100
    score = 0
    reasons = []
    
    # 1. Language (40 points)
    pref = translator.preference
    prof = translator.profile
    
    source_norm = normalize_text(job.source_lang)
    target_norm = normalize_text(job.target_lang)
    exact_pair = f"{source_norm}>{target_norm}".replace(' ', '')
    reverse_pair = f"{target_norm}>{source_norm}".replace(' ', '')
    
    if pref and getattr(pref, 'language_pairs', None):
        pairs_str = pref.language_pairs
        pairs = [normalize_text(p).replace(' ', '') for p in pairs_str.split(',')]
        
        if exact_pair in pairs:
            score += 40
            reasons.append(t_lookup('match_reasons.exact_language_pair', lang))
        elif reverse_pair in pairs:
            score += 20
            reasons.append(t_lookup('match_reasons.reverse_language_pair', lang))
        else:
            translator_langs = set()
            for p in pairs:
                if '>' in p:
                    src, tgt = p.split('>', 1)
                    translator_langs.add(src)
                    translator_langs.add(tgt)
            if source_norm in translator_langs or target_norm in translator_langs:
                score += 10
                reasons.append(t_lookup('match_reasons.partial_language', lang))
    else:
        translator_langs = []
        if pref and getattr(pref, 'languages', None):
            translator_langs = [normalize_text(l) for l in pref.languages.split(',')]
        elif prof and prof.languages:
            translator_langs = [normalize_text(l) for l in prof.languages.split(',')]

        if source_norm in translator_langs and target_norm in translator_langs:
            score += 40
            reasons.append(t_lookup('match_reasons.language_match', lang))
        elif source_norm in translator_langs or target_norm in translator_langs:
            score += 20
            reasons.append(t_lookup('match_reasons.partial_language', lang))

    # 2. Service Type (25 points)
    job_group = job.display_category_group
    job_type = job.display_service_type
    
    pref_services = []
    if pref and getattr(pref, 'service_types', None):
        pref_services = [normalize_text(s) for s in pref.service_types.split(',')]
        
    exact_match_texts = []
    group_match_texts = []
    
    if job_group == 'translation':
        group_match_texts.append(normalize_text('Dịch thuật'))
    else:
        group_match_texts.append(normalize_text('Phiên dịch'))
        
    if job_type in ['meeting']:
        exact_match_texts.append(normalize_text('Hội họp'))
    elif job_type in ['business']:
        exact_match_texts.append(normalize_text('Kinh doanh'))
    elif job_type in ['travel']:
        exact_match_texts.append(normalize_text('Du lịch'))
    elif job_type in ['event']:
        exact_match_texts.append(normalize_text('Sự kiện'))
    elif job_type in ['conference', 'escort']:
        group_match_texts.append(normalize_text('Phiên dịch'))
    elif job_type == 'other_interpretation':
        exact_match_texts.append(normalize_text('Khác'))

    if pref_services:
        if any(s in pref_services for s in exact_match_texts):
            score += 25
            reasons.append(t_lookup('match_reasons.exact_job_type', lang))
        elif any(s in pref_services for s in group_match_texts):
            score += 15
            reasons.append(t_lookup('match_reasons.group_match', lang))
    else:
        score += 25
        
    # 3. Experience (15 points)
    exp_score = 0
    if prof:
        if prof.is_verified:
            exp_score += 5
        if prof.total_jobs and prof.total_jobs >= 5:
            exp_score += 5
        elif prof.total_jobs and prof.total_jobs > 0:
            exp_score += 2
        if prof.rating and prof.rating >= 4.5:
            exp_score += 5
        elif prof.rating and prof.rating >= 4.0:
            exp_score += 3
    
    exp_score = min(exp_score, 15)
    score += exp_score
    if exp_score >= 10:
        reasons.append(t_lookup('match_reasons.experience_match', lang))
        
    # 4. Location (10 points)
    loc_score = 10
    job_loc_norm = normalize_text(job.event_location)
    
    if job_loc_norm:
        if "online" in job_loc_norm or "tu xa" in job_loc_norm:
            reasons.append(t_lookup('match_reasons.remote_work', lang))
        elif prof and prof.bio and normalize_text(prof.bio):
            bio_norm = normalize_text(prof.bio)
            if "ha noi" in job_loc_norm and "ha noi" not in bio_norm:
                loc_score = 5
            elif "ho chi minh" in job_loc_norm and "ho chi minh" not in bio_norm and "hcm" not in bio_norm:
                loc_score = 5
            else:
                reasons.append(t_lookup('match_reasons.location_match', lang))
        else:
            pass # No penalty if lack of info
    score += loc_score

    # 5. Budget (10 points)
    budget_score = 10
    if job.budget_min and prof:
        min_price = min([s.basic_price for s in prof.services if s.basic_price], default=None)
        if min_price and job.budget_min < (min_price * 0.7):
            budget_score = 5
        elif min_price and job.budget_min >= min_price:
            reasons.append(t_lookup('match_reasons.budget_match', lang))
    score += budget_score

    # Limit score to 100
    score = min(score, 100)

    return score, reasons

def get_recommended_jobs_for_translator(user_id, limit=10, lang='vi'):
    from app import translator_accepts_job
    from translations import t as t_lookup
    translator = User.query.get(user_id)
    if not translator or translator.role != 'translator' or not translator.is_active:
        return []
        
    open_jobs = Job.query.filter_by(status='open', is_flagged=False).all()
    
    scored_jobs = []
    for job in open_jobs:
        if Proposal.query.filter_by(job_id=job.id, translator_id=user_id).first():
            continue
            
        if not translator_accepts_job(translator, job):
            continue
            
        # check schedule conflict
        available, availability_reason = translator_is_available_for_job(user_id, job)
        if not available:
            continue

        score, reasons = calculate_job_match_score(translator, job, lang)
        if score > 0:
            if available:
                reasons.append(t_lookup('match_reasons.schedule_free', lang))

            scored_jobs.append({
                'job_id': job.id,
                'match_score': score,
                'reasons': reasons,
                'created_at': job.created_at
            })
            
    scored_jobs.sort(key=lambda x: (x['match_score'], x['created_at']), reverse=True)
    
    return [{'job_id': x['job_id'], 'match_score': x['match_score'], 'reasons': x['reasons']} for x in scored_jobs[:limit]]

def calculate_translator_match_score(translator, job, lang='vi'):
    # This is symmetric to calculate_job_match_score
    return calculate_job_match_score(translator, job, lang)

def get_recommended_translators_for_job(job_id, limit=10, lang='vi'):
    from translations import t as t_lookup
    job = Job.query.get(job_id)
    if not job or job.status != 'open':
        return []

    # Get all active translators
    active_translators = User.query.filter_by(role='translator', is_active=True).all()
    
    scored_translators = []
    for translator in active_translators:
        # Check if they already proposed
        if Proposal.query.filter_by(job_id=job.id, translator_id=translator.id).first():
            continue
            
        available, availability_reason = translator_is_available_for_job(translator.id, job)
        if not available:
            continue
            
        try:
            score, reasons = calculate_translator_match_score(translator, job, lang)
            if score > 0:
                if available:
                    reasons.append(t_lookup('match_reasons.schedule_free', lang))
                scored_translators.append({
                    'translator': translator,
                    'score': score,
                    'reasons': reasons
                })
        except Exception as e:
            # Safe matching
            print(f"Matching error for translator {translator.id}: {e}")
            continue
            
    scored_translators.sort(key=lambda x: (x['score'], x['translator'].created_at), reverse=True)
    
    results = []
    for x in scored_translators[:limit]:
        t = x['translator']
        prof = t.profile
        min_price = min([s.basic_price for s in prof.services if s.basic_price], default=None) if prof else None
        
        results.append({
            'translator_id': t.id,
            'profile_id': prof.id if prof else 0,
            'name': t.name,
            'avatar_initial': t.name[0].upper() if t.name else '?',
            'languages': prof.languages if prof else '',
            'title': prof.title if prof else '',
            'rating': prof.rating if prof else 0.0,
            'total_reviews': prof.total_reviews if prof else 0,
            'is_verified': prof.is_verified if prof else False,
            'min_price': min_price,
            'match_score': x['score'],
            'reasons': x['reasons']
        })
        
    return results

def notify_matching_translators_for_new_job(job):
    """
    Find eligible translators for a newly created job and send them a notification.
    Must not crash the job creation process.
    """
    try:
        from models import User, Notification, Proposal
        from app import translator_accepts_job, create_notification, db
        from services.schedule import parse_job_datetime, is_schedule_complete, check_translator_schedule_conflict
        from flask import url_for

        active_translators = User.query.filter_by(role='translator', is_active=True).all()
        parsed_schedule = parse_job_datetime(job)
        has_schedule = is_schedule_complete(parsed_schedule)

        for translator in active_translators:
            try:
                # 1. Check Preference
                if not translator_accepts_job(translator, job):
                    continue

                from services.notifications import should_notify
                if not should_notify(translator, 'JOB_MATCH'):
                    continue

                # 2. Check Proposal
                if Proposal.query.filter_by(job_id=job.id, translator_id=translator.id).first():
                    continue

                # 3. Check Schedule
                if has_schedule:
                    try:
                        conflict_res = check_translator_schedule_conflict(
                            translator_id=translator.id,
                            scheduled_date=parsed_schedule['date'],
                            start_time=parsed_schedule['start_time'],
                            end_time=parsed_schedule['end_time']
                        )
                        if conflict_res.get('conflict'):
                            continue
                    except Exception:
                        continue

                # 4. Check Score >= 70
                score, _ = calculate_translator_match_score(translator, job)
                if score < 70:
                    continue

                # 5. Check if notification already exists
                existing_notif = Notification.query.filter_by(
                    user_id=translator.id,
                    type='JOB_MATCH',
                    related_job_id=job.id
                ).first()
                if existing_notif:
                    continue

                # 6. Create Notification
                target_lang_display = job.target_lang or "Khác"
                create_notification(
                    user_id=translator.id,
                    notification_type='JOB_MATCH',
                    title='Có việc mới phù hợp với bạn',
                    message=f'Khách hàng đang tìm Phiên dịch {target_lang_display} cho một công việc phù hợp với hồ sơ của bạn.',
                    url=url_for('job_detail', job_id=job.id),
                    related_job_id=job.id
                )
                db.session.commit()
            except Exception as inner_e:
                import logging
                logging.error(f"Error notifying translator {translator.id} for job {job.id}: {inner_e}")
                continue

    except Exception as e:
        import logging
        logging.error(f"Error in notify_matching_translators_for_new_job for job {getattr(job, 'id', '?')}: {e}")

