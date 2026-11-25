import time, sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')
from app import app
from models import db, User
from flask import render_template

with app.app_context():
    trans = User.query.filter_by(role='translator').first()
    
    # Let's time render_template
    from app import compute_profile_completion, get_localized_languages, FallbackNotificationSetting
    from services.verification import DOCUMENT_POLICIES
    from services.account_security import get_active_sessions
    from services.account_support import (
        FAQ_TOPICS, FAQ_ITEMS, POLICY_DOCUMENTS, SUPPORT_CATEGORIES, get_user_tickets
    )
    import datetime

    t0 = time.perf_counter()
    profile_completion = compute_profile_completion(trans)
    verification_documents = []
    if trans.latest_verification and hasattr(trans.latest_verification, 'documents'):
        verification_documents = [d for d in trans.latest_verification.documents if getattr(d, 'is_active', True)]
    active_sessions = get_active_sessions(trans, 'test')
    user_support_tickets = get_user_tickets(trans.id)
    t_data = time.perf_counter() - t0
    print(f'Data prep time: {t_data*1000:.2f} ms')

    # Warm up Jinja2
    with app.test_request_context('/account/profile'):
        t0 = time.perf_counter()
        html = render_template(
            'account_profile.html',
            user=trans,
            LANGUAGES=get_localized_languages('vi'),
            active_tab='profile',
            profile_completion=profile_completion,
            unread_notifs_count=0,
            verification_documents=verification_documents,
            active_cv_document=getattr(trans, 'active_cv_document', None),
            DOCUMENT_POLICIES=DOCUMENT_POLICIES,
            declared_language_pairs=[],
            notification_setting=FallbackNotificationSetting(user_id=trans.id),
            active_sessions=active_sessions,
            support_tickets=user_support_tickets,
            faq_topics=FAQ_TOPICS,
            faq_items=FAQ_ITEMS,
            policy_documents=POLICY_DOCUMENTS,
            support_categories=SUPPORT_CATEGORIES,
            today_str=datetime.datetime.utcnow().strftime('%Y-%m-%d')
        )
        t_render = time.perf_counter() - t0
        print(f'Render template time: {t_render*1000:.2f} ms | Output size: {len(html)/1024:.1f} KB')
