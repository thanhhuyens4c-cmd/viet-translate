import unicodedata
from models import Job, Proposal, Contract, TranslatorPreference, TranslatorProfile, User
from datetime import datetime, date

def translator_is_available_for_job(translator_id, job):
    """Kiểm tra lịch làm việc của phiên dịch viên xem có bị trùng với job hay không."""
    try:
        from services.schedule import check_job_schedule_conflicts
        res = check_job_schedule_conflicts(job, translator_id)
        if not res.get('has_schedule'):
            return True, "Không có lịch cố định"
        if not res.get('available'):
            first_conflict = next(
                (d.get('message') for d in res.get('days', []) if not d.get('available') and d.get('message')),
                "Trùng lịch làm việc đã có"
            )
            return False, first_conflict
        return True, "Có lịch trống"
    except Exception as e:
        import logging
        logging.error(f"Error checking schedule for translator {translator_id} on job {getattr(job, 'id', '?')}: {e}")
        return True, "Lịch chưa xác định"

def normalize_text(value):
    if not value:
        return ''
    return unicodedata.normalize('NFKD', str(value)).encode('ASCII', 'ignore').decode('utf-8').lower().strip()

CITY_ALIASES = {
    'hn': ('ha noi', 'hanoi'),
    'hcm': ('ho chi minh', 'hcm', 'sai gon', 'saigon'),
    'dn': ('da nang',),
    'hp': ('hai phong',),
    'ct': ('can tho',),
}

def canonical_city(value):
    text = normalize_text(value)
    for key, aliases in CITY_ALIASES.items():
        if any(a in text for a in aliases):
            return key
    return text

SPECIALTY_DOMAINS = {
    'medical': {
        'name_vi': 'Y tế & Dược phẩm',
        'name_en': 'Healthcare & Medicine',
        'keywords': ['y te', 'duoc', 'benh vien', 'suc khoe', 'bac si', 'lam sang', 'nha khoa', 'medical', 'pharma', 'health', 'clinic', 'medicine', 'hospital', 'y duoc', 'dieu tri'],
    },
    'legal': {
        'name_vi': 'Pháp lý & Luật',
        'name_en': 'Legal & Contracts',
        'keywords': ['phap ly', 'hop dong', 'toa an', 'luat', 'cong chung', 'tranh chap', 'to tung', 'legal', 'law', 'contract', 'court', 'litigation', 'tu phap', 'ban quyen'],
    },
    'technical': {
        'name_vi': 'Kỹ thuật & Công nghệ',
        'name_en': 'Engineering & IT',
        'keywords': ['ky thuat', 'cong nghe', 'it', 'phan mem', 'che tao', 'co khi', 'xay dung', 'dien tu', 'technical', 'technology', 'engineering', 'software', 'construction', 'may moc', 'ban ve', 'lap trinh'],
    },
    'finance': {
        'name_vi': 'Tài chính & Ngân hàng',
        'name_en': 'Finance & Banking',
        'keywords': ['tai chinh', 'ngan hang', 'ke toan', 'kiem toan', 'dau tu', 'chung khoan', 'finance', 'banking', 'accounting', 'audit', 'securities', 'bao cao tai chinh', 'thue'],
    },
    'business': {
        'name_vi': 'Thương mại & Kinh doanh',
        'name_en': 'Business & Commerce',
        'keywords': ['thuong mai', 'kinh doanh', 'xuat nhap khau', 'marketing', 'dam phan', 'ban hang', 'business', 'commerce', 'trade', 'marketing', 'sales', 'logistics', 'b2b', 'hoi cho'],
    },
    'conference': {
        'name_vi': 'Hội nghị & Sự kiện',
        'name_en': 'Conference & Events',
        'keywords': ['hoi nghi', 'hoi thao', 'su kien', 'cabin', 'song song', 'dien dan', 'conference', 'seminar', 'summit', 'event', 'convention', 'thap tung', 'dien thuyet'],
    },
    'tourism': {
        'name_vi': 'Văn hóa & Du lịch',
        'name_en': 'Tourism & Culture',
        'keywords': ['du lich', 'van hoa', 'huong dan vien', 'khach san', 'am thuc', 'tourism', 'culture', 'travel', 'hospitality', 'culinary', 'di tich', 'le hoi'],
    },
    'education': {
        'name_vi': 'Giáo dục & Đào tạo',
        'name_en': 'Education & Training',
        'keywords': ['giao duc', 'dao tao', 'du hoc', 'giang day', 'hoc thuat', 'education', 'training', 'academic', 'teaching', 'luan van', 'nghien cuu'],
    }
}

def calculate_client_fit(pref, hirer_profile, job, lang='vi'):
    """Điểm tối đa 12: ngành (5) + hình thức làm việc (3) + chứng nhận (4)."""
    from translations import t as t_lookup
    reasons = []
    total = 0.0

    # Ngành
    from services.hirer import hirer_expertise_fields
    specialties = {s.strip() for s in (getattr(pref, 'specialties', None) or '').split(',') if s.strip()} if pref else set()
    needed_fields = hirer_expertise_fields(hirer_profile)
    if needed_fields and specialties:
        if needed_fields & specialties:
            total += 5
            reasons.append(t_lookup('match_reasons.industry_match', lang))
    else:
        total += 3

    # Hình thức làm việc (job ghi online thì coi như online)
    job_loc = normalize_text(job.event_location)
    job_mode = 'online' if ('online' in job_loc or 'tu xa' in job_loc) else (hirer_profile.work_mode if hirer_profile else None)
    t_mode = getattr(pref, 'work_mode', None) if pref else None
    if job_mode and t_mode:
        if t_mode == 'both' or job_mode == 'both' or job_mode == t_mode:
            total += 3
            reasons.append(t_lookup('match_reasons.mode_match', lang))
    else:
        total += 1.8

    # Chứng nhận / công chứng
    if hirer_profile and hirer_profile.needs_certified:
        if pref and pref.offers_certified:
            total += 4
            reasons.append(t_lookup('match_reasons.certified_match', lang))
        elif not pref:
            total += 2.4
    else:
        total += 4

    return int(round(total)), reasons

def calculate_job_match_score(translator, job, lang='vi'):
    """
    Tính điểm phù hợp của công việc với phiên dịch viên (thang điểm 0 - 100):
    1. Cặp ngôn ngữ (Language Match): 30 điểm
    2. Chuyên môn & Lĩnh vực yêu cầu (Specialization Match): 25 điểm
    3. Trình độ học vấn, chứng chỉ & kinh nghiệm (Qualifications & Experience): 15 điểm
    4. Hình thức phiên dịch & Dịch vụ (Service Type): 12 điểm
    5. Địa điểm & Hình thức làm việc (Location & Work Mode): 10 điểm
    6. Ngân sách & Thù lao (Budget Match): 8 điểm
    """
    from translations import t as t_lookup
    score = 0
    reasons = []
    
    int_pref = getattr(translator, 'interpreter_preference', None)
    pref = getattr(translator, 'preference', None)
    prof = getattr(translator, 'profile', None)

    # ─────────────────────────────────────────────────────────────
    # 1. Cặp ngôn ngữ (30 điểm)
    # ─────────────────────────────────────────────────────────────
    source_norm = normalize_text(job.source_lang)
    target_norm = normalize_text(job.target_lang)
    exact_pair = f"{source_norm}>{target_norm}".replace(' ', '')
    reverse_pair = f"{target_norm}>{source_norm}".replace(' ', '')

    lang_scored = False
    if int_pref and hasattr(int_pref, 'get_languages_list') and int_pref.get_languages_list():
        int_pairs = [normalize_text(p.replace('->', '>').replace('➔', '>')).replace(' ', '') for p in int_pref.get_languages_list() if p.strip()]
        if exact_pair in int_pairs:
            score += 30
            reasons.append(t_lookup('match_reasons.exact_language_pair', lang))
            lang_scored = True
        elif reverse_pair in int_pairs:
            score += 18
            reasons.append(t_lookup('match_reasons.reverse_language_pair', lang))
            lang_scored = True
        else:
            langs = set()
            for p in int_pairs:
                if '>' in p:
                    for part in p.split('>'):
                        langs.add(part)
                else:
                    langs.add(p)
            if source_norm in langs and target_norm in langs:
                score += 26
                reasons.append(t_lookup('match_reasons.language_match', lang))
                lang_scored = True
            elif source_norm in langs or target_norm in langs:
                score += 10
                reasons.append(t_lookup('match_reasons.partial_language', lang))
                lang_scored = True

    if not lang_scored and pref and getattr(pref, 'language_pairs', None):
        pairs = [normalize_text(p).replace(' ', '') for p in pref.language_pairs.split(',') if p.strip()]
        if exact_pair in pairs:
            score += 30
            reasons.append(t_lookup('match_reasons.exact_language_pair', lang))
            lang_scored = True
        elif reverse_pair in pairs:
            score += 18
            reasons.append(t_lookup('match_reasons.reverse_language_pair', lang))
            lang_scored = True
        else:
            translator_langs = set()
            for p in pairs:
                if '>' in p:
                    src_p, tgt_p = p.split('>', 1)
                    translator_langs.add(src_p)
                    translator_langs.add(tgt_p)
            if source_norm in translator_langs and target_norm in translator_langs:
                score += 26
                reasons.append(t_lookup('match_reasons.language_match', lang))
                lang_scored = True
            elif source_norm in translator_langs or target_norm in translator_langs:
                score += 10
                reasons.append(t_lookup('match_reasons.partial_language', lang))
                lang_scored = True

    if not lang_scored:
        translator_langs = []
        if pref and getattr(pref, 'languages', None):
            translator_langs = [normalize_text(l) for l in pref.languages.split(',') if l.strip()]
        elif prof and prof.languages:
            translator_langs = [normalize_text(l) for l in prof.languages.split(',') if l.strip()]
        
        # Thêm ngôn ngữ từ trường source_language / target_language của profile
        if prof and getattr(prof, 'source_language', None):
            translator_langs.append(normalize_text(prof.source_language))
        if prof and getattr(prof, 'target_language', None):
            translator_langs.append(normalize_text(prof.target_language))

        if source_norm in translator_langs and target_norm in translator_langs:
            score += 30
            reasons.append(t_lookup('match_reasons.language_match', lang))
        elif source_norm in translator_langs or target_norm in translator_langs:
            score += 12
            reasons.append(t_lookup('match_reasons.partial_language', lang))

    # ─────────────────────────────────────────────────────────────
    # 2. Lĩnh vực chuyên môn & Yêu cầu đề bài (25 điểm)
    # ─────────────────────────────────────────────────────────────
    # Tổng hợp các lĩnh vực chuyên môn của phiên dịch viên
    translator_specs = []
    if prof:
        if hasattr(prof, 'display_specializations') and prof.display_specializations:
            translator_specs.extend([normalize_text(s) for s in prof.display_specializations])
        elif prof.specializations:
            translator_specs.extend([normalize_text(s) for s in prof.specializations.split(',') if s.strip()])
        if getattr(prof, 'major', None):
            translator_specs.append(normalize_text(prof.major))
        if getattr(prof, 'bio', None):
            translator_specs.append(normalize_text(prof.bio))
    if pref and getattr(pref, 'specialties', None):
        translator_specs.extend([normalize_text(s) for s in pref.specialties.split(',') if s.strip()])

    translator_specs_str = ' '.join(translator_specs)

    # Tổng hợp thông tin lĩnh vực của công việc
    job_specialty_norm = normalize_text(getattr(job, 'specialty', '') or '')
    job_title_norm = normalize_text(job.title or '')
    job_desc_norm = normalize_text(job.description or '')
    job_extra_norm = normalize_text(getattr(job, 'extra_requirements', '') or '')
    job_all_text = f"{job_specialty_norm} {job_title_norm} {job_desc_norm} {job_extra_norm}"

    matched_domain_name = None
    strong_spec_match = False
    keyword_spec_match = False

    # So khớp qua từ điển SPECIALTY_DOMAINS
    for dom_key, dom_data in SPECIALTY_DOMAINS.items():
        domain_name = dom_data['name_en'] if lang == 'en' else dom_data['name_vi']
        # Kiểm tra nếu job thuộc lĩnh vực này
        job_has_domain = (
            any(k in job_specialty_norm for k in dom_data['keywords']) or
            (dom_key in job_specialty_norm) or
            any(k in job_title_norm for k in dom_data['keywords'])
        )
        trans_has_domain = (
            any(k in translator_specs_str for k in dom_data['keywords']) or
            (dom_key in translator_specs_str)
        )
        if job_has_domain and trans_has_domain:
            matched_domain_name = domain_name
            strong_spec_match = True
            break
        elif not strong_spec_match and any(k in job_all_text for k in dom_data['keywords']) and trans_has_domain:
            matched_domain_name = domain_name
            keyword_spec_match = True

    if strong_spec_match:
        score += 25
        reason_text = f"Đúng chuyên môn: {matched_domain_name}" if lang == 'vi' else f"Specialization match: {matched_domain_name}"
        reasons.append(reason_text)
    elif keyword_spec_match:
        score += 18
        reason_text = f"Phù hợp lĩnh vực: {matched_domain_name}" if lang == 'vi' else f"Industry match: {matched_domain_name}"
        reasons.append(reason_text)
    elif job_specialty_norm and any(job_specialty_norm in s for s in translator_specs):
        score += 25
        reasons.append(t_lookup('match_reasons.specialty_match', lang))
    elif not job_specialty_norm:
        # Công việc tổng hợp hoặc không giới hạn lĩnh vực chuyên sâu
        score += 12
    else:
        # Có yêu cầu chuyên môn nhưng chưa trùng
        score += 4

    # ─────────────────────────────────────────────────────────────
    # 3. Trình độ học vấn, chứng chỉ & năng lực (15 điểm)
    # ─────────────────────────────────────────────────────────────
    prof_score = 0
    if prof:
        # Năng lực ngoại ngữ
        proficiency = normalize_text(getattr(prof, 'language_proficiency', '') or '')
        if any(p in proficiency for p in ['c2', 'c1', 'ban ngu', 'native', 'chuyen nghiep']):
            prof_score += 5
            reasons.append("Trình độ ngôn ngữ thành thạo (C1/C2/Bản ngữ)" if lang == 'vi' else "Fluent proficiency (C1/C2/Native)")
        elif 'b2' in proficiency:
            prof_score += 3

        # Học vấn & Chứng chỉ
        has_edu = bool(getattr(prof, 'education_level', None) and any(e in normalize_text(prof.education_level) for e in ['cu nhan', 'thac si', 'tien si', 'dai hoc', 'bachelor', 'master', 'phd']))
        has_cert = bool(getattr(prof, 'cert_name', None) or getattr(prof, 'certificates', None))
        if has_edu or has_cert:
            prof_score += 4
            reasons.append(t_lookup('match_reasons.qualification_match', lang))

        # Đã xác thực danh tính & chứng chỉ (Verified)
        if getattr(prof, 'is_verified', False):
            prof_score += 3
            reasons.append(t_lookup('match_reasons.verified_match', lang))

        # Kinh nghiệm & Đánh giá
        exp_years = getattr(prof, 'experience_years', 0) or 0
        rating = getattr(prof, 'rating', 0.0) or 0.0
        if exp_years >= 3 or rating >= 4.5 or (getattr(prof, 'total_jobs', 0) or 0) >= 5:
            prof_score += 3
            reasons.append(t_lookup('match_reasons.experience_match', lang))
        elif exp_years >= 1 or rating >= 4.0:
            prof_score += 2

    score += min(prof_score, 15)

    # ─────────────────────────────────────────────────────────────
    # 4. Hình thức phiên dịch & Dịch vụ (12 điểm)
    # ─────────────────────────────────────────────────────────────
    job_group = job.display_category_group
    job_type = job.display_service_type
    
    pref_services = []
    if pref and getattr(pref, 'service_types', None):
        pref_services = [normalize_text(s) for s in pref.service_types.split(',') if s.strip()]
        
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
            score += 12
            reasons.append(t_lookup('match_reasons.exact_job_type', lang))
        elif any(s in pref_services for s in group_match_texts):
            score += 8
            reasons.append(t_lookup('match_reasons.group_match', lang))
        else:
            score += 5
    else:
        score += 10

    # ─────────────────────────────────────────────────────────────
    # 5. Địa điểm & Phương thức làm việc (10 điểm)
    # ─────────────────────────────────────────────────────────────
    hirer_profile = None
    try:
        hirer_profile = job.hirer.hirer_profile if job.hirer else None
    except Exception:
        hirer_profile = None

    job_loc_norm = normalize_text(job.event_location) or (normalize_text(hirer_profile.location) if hirer_profile else '')
    if job_loc_norm:
        if any(k in job_loc_norm for k in ["online", "tu xa", "toan quoc", "remote", "zoom", "teams"]):
            score += 10
            reasons.append(t_lookup('match_reasons.remote_work', lang))
        elif int_pref and hasattr(int_pref, 'get_locations_list') and int_pref.get_locations_list():
            matched_loc = any(normalize_text(loc) in job_loc_norm or job_loc_norm in normalize_text(loc) or 'toan quoc' in normalize_text(loc) for loc in int_pref.get_locations_list())
            if matched_loc:
                score += 10
                reasons.append(t_lookup('match_reasons.location_match', lang))
            elif getattr(int_pref, 'work_mode', None) == 'online':
                score += 4
            else:
                score += 5
        elif pref and getattr(pref, 'city', None):
            if canonical_city(pref.city) and canonical_city(pref.city) == canonical_city(job_loc_norm):
                score += 10
                reasons.append(t_lookup('match_reasons.location_match', lang))
            elif getattr(pref, 'work_mode', None) == 'online':
                score += 4
            else:
                score += 5
        elif prof and getattr(prof, 'bio', None) and normalize_text(prof.bio):
            bio_norm = normalize_text(prof.bio)
            if "ha noi" in job_loc_norm and "ha noi" in bio_norm:
                score += 10
                reasons.append(t_lookup('match_reasons.location_match', lang))
            elif ("ho chi minh" in job_loc_norm or "hcm" in job_loc_norm) and ("ho chi minh" in bio_norm or "hcm" in bio_norm):
                score += 10
                reasons.append(t_lookup('match_reasons.location_match', lang))
            else:
                score += 6
        else:
            score += 7
    else:
        score += 8

    # ─────────────────────────────────────────────────────────────
    # 6. Ngân sách & Mức thù lao (8 điểm)
    # ─────────────────────────────────────────────────────────────
    budget_ref = job.budget_min or (getattr(hirer_profile, 'typical_budget_min', None) if hirer_profile else None)
    if budget_ref and prof and getattr(prof, 'services', None):
        min_price = min([s.basic_price for s in prof.services if s.basic_price], default=None)
        if min_price and budget_ref >= min_price:
            score += 8
            reasons.append(t_lookup('match_reasons.budget_match', lang))
        elif min_price and budget_ref >= (min_price * 0.7):
            score += 5
        else:
            score += 3
    else:
        score += 6

    # Capped at 100
    score = min(max(score, 0), 100)
    return score, reasons

def get_recommended_jobs_for_translator(user_id, limit=50, lang='vi'):
    """
    Trả về danh sách công việc đề xuất phù hợp nhất cho phiên dịch viên,
    được xếp hạng theo điểm tương thích (match_score) giảm dần.
    """
    from app import translator_accepts_job, db
    from translations import t as t_lookup
    
    translator = User.query.get(user_id)
    if not translator or translator.role != 'translator' or not translator.is_active:
        return []

    today = date.today()
    # Lấy các việc đang mở, đã duyệt, không bị gắn cờ và còn thời hạn
    open_jobs = Job.query.join(User, Job.hirer_id == User.id).filter(
        Job.status == 'open',
        Job.moderation_status == 'approved',
        db.or_(Job.is_flagged == False, Job.is_flagged == None),
        User.is_active == True,
        db.or_(Job.deadline.is_(None), Job.deadline >= today)
    ).all()

    # Tập hợp các công việc translator đã gửi báo giá (bỏ qua không gợi ý lại)
    proposed_job_ids = {p.job_id for p in Proposal.query.filter_by(translator_id=user_id).all()}

    scored_jobs = []
    for job in open_jobs:
        if job.id in proposed_job_ids:
            continue

        if not translator_accepts_job(translator, job):
            continue

        # Kiểm tra xung đột lịch làm việc
        available, avail_msg = translator_is_available_for_job(user_id, job)
        if not available:
            # Loại bỏ công việc bị trùng lịch với ca làm việc đã có
            continue

        try:
            score, reasons = calculate_job_match_score(translator, job, lang)
            if score >= 35:
                if available and (job.event_date or (hasattr(job, 'schedules') and job.schedules)):
                    reasons.append(t_lookup('match_reasons.schedule_free', lang))

                scored_jobs.append({
                    'job_id': job.id,
                    'match_score': score,
                    'reasons': reasons,
                    'created_at': job.created_at or datetime.utcnow()
                })
        except Exception as e:
            import logging
            logging.error(f"Error calculating match score for job {job.id}: {e}")
            continue

    # Sắp xếp ưu tiên: điểm phù hợp cao nhất -> công việc mới nhất
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

    # Get all active and verified translators
    active_translators = User.query.join(TranslatorProfile).filter(
        User.role == 'translator', 
        User.is_active == True,
        TranslatorProfile.is_verified == True
    ).all()
    
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
            'avatar_url': t.avatar_url,
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

