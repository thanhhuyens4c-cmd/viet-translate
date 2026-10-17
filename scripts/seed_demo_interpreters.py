#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed script to generate and deploy exactly 100 unique demo interpreter profiles
for Viettranslate.

Idempotent: Re-running this script updates existing demo profiles without creating duplicates.
Real accounts are never touched.

Strict 10 Languages:
1. Tiếng Anh (English)
2. Tiếng Trung (Chinese)
3. Tiếng Nhật (Japanese)
4. Tiếng Hàn (Korean)
5. Tiếng Pháp (French)
6. Tiếng Đức (German)
7. Tiếng Nga (Russian)
8. Tiếng Tây Ban Nha (Spanish)
9. Tiếng Thái (Thai)
10. Tiếng Bồ Đào Nha (Portuguese)
(Paired with Tiếng Việt or global pairs among them).
"""

import sys
import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import (
    User,
    TranslatorProfile,
    Service,
    InterpreterService,
    InterpreterPreference,
    TranslatorPreference,
    TranslatorVerification,
)

# ─── 100 DIVERSE DEMO PROFILES SPECIFICATION (STRICT 10 LANGUAGES) ────────────
LANG_DATA = [
    # 1-18: Vietnamese - English (18)
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt, Tiếng Pháp", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh, Tiếng Nhật", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt, Tiếng Đức", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Anh", "pair": "Tiếng Việt - Tiếng Anh", "langs": "Tiếng Việt, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Việt", "pair": "Tiếng Anh - Tiếng Việt", "langs": "Tiếng Anh, Tiếng Việt", "nat": "Tiếng Việt"},

    # 19-33: Vietnamese - Chinese (15)
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Trung"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Trung"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},
    {"src": "Tiếng Trung", "tgt": "Tiếng Việt", "pair": "Tiếng Trung - Tiếng Việt", "langs": "Tiếng Trung, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Trung", "pair": "Tiếng Việt - Tiếng Trung", "langs": "Tiếng Việt, Tiếng Trung", "nat": "Tiếng Việt"},

    # 34-48: Vietnamese - Japanese (15)
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Nhật"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Nhật"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Nhật"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Nhật"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nhật", "tgt": "Tiếng Việt", "pair": "Tiếng Nhật - Tiếng Việt", "langs": "Tiếng Nhật, Tiếng Việt", "nat": "Tiếng Nhật"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nhật", "pair": "Tiếng Việt - Tiếng Nhật", "langs": "Tiếng Việt, Tiếng Nhật", "nat": "Tiếng Việt"},

    # 49-63: Vietnamese - Korean (15)
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn", "nat": "Tiếng Việt"},
    {"src": "Tiếng Hàn", "tgt": "Tiếng Việt", "pair": "Tiếng Hàn - Tiếng Việt", "langs": "Tiếng Hàn, Tiếng Việt", "nat": "Tiếng Hàn"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Hàn", "tgt": "Tiếng Việt", "pair": "Tiếng Hàn - Tiếng Việt", "langs": "Tiếng Hàn, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn", "nat": "Tiếng Việt"},
    {"src": "Tiếng Hàn", "tgt": "Tiếng Việt", "pair": "Tiếng Hàn - Tiếng Việt", "langs": "Tiếng Hàn, Tiếng Việt", "nat": "Tiếng Hàn"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn", "nat": "Tiếng Việt"},
    {"src": "Tiếng Hàn", "tgt": "Tiếng Việt", "pair": "Tiếng Hàn - Tiếng Việt", "langs": "Tiếng Hàn, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn", "nat": "Tiếng Việt"},
    {"src": "Tiếng Hàn", "tgt": "Tiếng Việt", "pair": "Tiếng Hàn - Tiếng Việt", "langs": "Tiếng Hàn, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn", "nat": "Tiếng Việt"},
    {"src": "Tiếng Hàn", "tgt": "Tiếng Việt", "pair": "Tiếng Hàn - Tiếng Việt", "langs": "Tiếng Hàn, Tiếng Việt", "nat": "Tiếng Hàn"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn", "nat": "Tiếng Việt"},
    {"src": "Tiếng Hàn", "tgt": "Tiếng Việt", "pair": "Tiếng Hàn - Tiếng Việt", "langs": "Tiếng Hàn, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Hàn", "pair": "Tiếng Việt - Tiếng Hàn", "langs": "Tiếng Việt, Tiếng Hàn", "nat": "Tiếng Việt"},

    # 64-71: Vietnamese - French (8)
    {"src": "Tiếng Việt", "tgt": "Tiếng Pháp", "pair": "Tiếng Việt - Tiếng Pháp", "langs": "Tiếng Việt, Tiếng Pháp", "nat": "Tiếng Việt"},
    {"src": "Tiếng Pháp", "tgt": "Tiếng Việt", "pair": "Tiếng Pháp - Tiếng Việt", "langs": "Tiếng Pháp, Tiếng Việt", "nat": "Tiếng Pháp"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Pháp", "pair": "Tiếng Việt - Tiếng Pháp", "langs": "Tiếng Việt, Tiếng Pháp, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Pháp", "tgt": "Tiếng Việt", "pair": "Tiếng Pháp - Tiếng Việt", "langs": "Tiếng Pháp, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Pháp", "pair": "Tiếng Việt - Tiếng Pháp", "langs": "Tiếng Việt, Tiếng Pháp", "nat": "Tiếng Việt"},
    {"src": "Tiếng Pháp", "tgt": "Tiếng Việt", "pair": "Tiếng Pháp - Tiếng Việt", "langs": "Tiếng Pháp, Tiếng Việt", "nat": "Tiếng Pháp"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Pháp", "pair": "Tiếng Việt - Tiếng Pháp", "langs": "Tiếng Việt, Tiếng Pháp", "nat": "Tiếng Việt"},
    {"src": "Tiếng Pháp", "tgt": "Tiếng Việt", "pair": "Tiếng Pháp - Tiếng Việt", "langs": "Tiếng Pháp, Tiếng Việt", "nat": "Tiếng Pháp"},

    # 72-79: Vietnamese - German (8)
    {"src": "Tiếng Việt", "tgt": "Tiếng Đức", "pair": "Tiếng Việt - Tiếng Đức", "langs": "Tiếng Việt, Tiếng Đức", "nat": "Tiếng Việt"},
    {"src": "Tiếng Đức", "tgt": "Tiếng Việt", "pair": "Tiếng Đức - Tiếng Việt", "langs": "Tiếng Đức, Tiếng Việt", "nat": "Tiếng Đức"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Đức", "pair": "Tiếng Việt - Tiếng Đức", "langs": "Tiếng Việt, Tiếng Đức, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Đức", "tgt": "Tiếng Việt", "pair": "Tiếng Đức - Tiếng Việt", "langs": "Tiếng Đức, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Đức", "pair": "Tiếng Việt - Tiếng Đức", "langs": "Tiếng Việt, Tiếng Đức", "nat": "Tiếng Việt"},
    {"src": "Tiếng Đức", "tgt": "Tiếng Việt", "pair": "Tiếng Đức - Tiếng Việt", "langs": "Tiếng Đức, Tiếng Việt", "nat": "Tiếng Đức"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Đức", "pair": "Tiếng Việt - Tiếng Đức", "langs": "Tiếng Việt, Tiếng Đức", "nat": "Tiếng Việt"},
    {"src": "Tiếng Đức", "tgt": "Tiếng Việt", "pair": "Tiếng Đức - Tiếng Việt", "langs": "Tiếng Đức, Tiếng Việt", "nat": "Tiếng Đức"},

    # 80-85: Vietnamese - Russian (6)
    {"src": "Tiếng Việt", "tgt": "Tiếng Nga", "pair": "Tiếng Việt - Tiếng Nga", "langs": "Tiếng Việt, Tiếng Nga", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nga", "tgt": "Tiếng Việt", "pair": "Tiếng Nga - Tiếng Việt", "langs": "Tiếng Nga, Tiếng Việt", "nat": "Tiếng Nga"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nga", "pair": "Tiếng Việt - Tiếng Nga", "langs": "Tiếng Việt, Tiếng Nga, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nga", "tgt": "Tiếng Việt", "pair": "Tiếng Nga - Tiếng Việt", "langs": "Tiếng Nga, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Nga", "pair": "Tiếng Việt - Tiếng Nga", "langs": "Tiếng Việt, Tiếng Nga", "nat": "Tiếng Việt"},
    {"src": "Tiếng Nga", "tgt": "Tiếng Việt", "pair": "Tiếng Nga - Tiếng Việt", "langs": "Tiếng Nga, Tiếng Việt", "nat": "Tiếng Nga"},

    # 86-90: Vietnamese - Thai (5)
    {"src": "Tiếng Việt", "tgt": "Tiếng Thái", "pair": "Tiếng Việt - Tiếng Thái", "langs": "Tiếng Việt, Tiếng Thái", "nat": "Tiếng Việt"},
    {"src": "Tiếng Thái", "tgt": "Tiếng Việt", "pair": "Tiếng Thái - Tiếng Việt", "langs": "Tiếng Thái, Tiếng Việt", "nat": "Tiếng Thái"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Thái", "pair": "Tiếng Việt - Tiếng Thái", "langs": "Tiếng Việt, Tiếng Thái, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Thái", "tgt": "Tiếng Việt", "pair": "Tiếng Thái - Tiếng Việt", "langs": "Tiếng Thái, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Thái", "pair": "Tiếng Việt - Tiếng Thái", "langs": "Tiếng Việt, Tiếng Thái", "nat": "Tiếng Việt"},

    # 91-95: Vietnamese - Spanish (5)
    {"src": "Tiếng Việt", "tgt": "Tiếng Tây Ban Nha", "pair": "Tiếng Việt - Tiếng Tây Ban Nha", "langs": "Tiếng Việt, Tiếng Tây Ban Nha", "nat": "Tiếng Việt"},
    {"src": "Tiếng Tây Ban Nha", "tgt": "Tiếng Việt", "pair": "Tiếng Tây Ban Nha - Tiếng Việt", "langs": "Tiếng Tây Ban Nha, Tiếng Việt", "nat": "Tiếng Tây Ban Nha"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Tây Ban Nha", "pair": "Tiếng Việt - Tiếng Tây Ban Nha", "langs": "Tiếng Việt, Tiếng Tây Ban Nha, Tiếng Anh", "nat": "Tiếng Việt"},
    {"src": "Tiếng Tây Ban Nha", "tgt": "Tiếng Việt", "pair": "Tiếng Tây Ban Nha - Tiếng Việt", "langs": "Tiếng Tây Ban Nha, Tiếng Việt", "nat": "Tiếng Việt"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Tây Ban Nha", "pair": "Tiếng Việt - Tiếng Tây Ban Nha", "langs": "Tiếng Việt, Tiếng Tây Ban Nha", "nat": "Tiếng Việt"},

    # 96-98: Vietnamese - Portuguese (3)
    {"src": "Tiếng Việt", "tgt": "Tiếng Bồ Đào Nha", "pair": "Tiếng Việt - Tiếng Bồ Đào Nha", "langs": "Tiếng Việt, Tiếng Bồ Đào Nha", "nat": "Tiếng Việt"},
    {"src": "Tiếng Bồ Đào Nha", "tgt": "Tiếng Việt", "pair": "Tiếng Bồ Đào Nha - Tiếng Việt", "langs": "Tiếng Bồ Đào Nha, Tiếng Việt", "nat": "Tiếng Bồ Đào Nha"},
    {"src": "Tiếng Việt", "tgt": "Tiếng Bồ Đào Nha", "pair": "Tiếng Việt - Tiếng Bồ Đào Nha", "langs": "Tiếng Việt, Tiếng Bồ Đào Nha, Tiếng Anh", "nat": "Tiếng Việt"},

    # 99-100: Global pairs among the 10 languages (2)
    {"src": "Tiếng Anh", "tgt": "Tiếng Nhật", "pair": "Tiếng Anh - Tiếng Nhật", "langs": "Tiếng Anh, Tiếng Nhật", "nat": "Tiếng Nhật"},
    {"src": "Tiếng Anh", "tgt": "Tiếng Trung", "pair": "Tiếng Anh - Tiếng Trung", "langs": "Tiếng Anh, Tiếng Trung", "nat": "Tiếng Trung"},
]

# 20 Diverse Industry Specializations
INDUSTRIES = [
    "Đàm phán kinh doanh & Thương mại",
    "Pháp lý & Hợp đồng",
    "Y tế & Chăm sóc sức khỏe",
    "Du lịch & Khách sạn",
    "Sản xuất & Kỹ thuật công nghiệp",
    "Xây dựng & Bất động sản",
    "Công nghệ thông tin & Phần mềm",
    "Giáo dục & Đào tạo",
    "Xuất nhập khẩu & Logistics",
    "Tài chính & Ngân hàng",
    "Sự kiện, Triển lãm & Hội nghị",
    "Ô tô & Tự động hóa",
    "Marketing & Truyền thông",
    "Hội nghị cấp cao & Ngoại giao",
    "Nông nghiệp & Chế biến thực phẩm",
    "Năng lượng & Môi trường",
    "Bán lẻ & Chuỗi cung ứng",
    "Điện tử & Bán dẫn",
    "Khoa học kỹ thuật & Nghiên cứu",
    "Hàng không & Vận tải quốc tế",
]

# Vietnamese Locations
LOCATIONS = [
    # Hà Nội (35)
    *([("Hà Nội", "Việt Nam", "Hà Nội và các tỉnh phía Bắc", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)")] * 15),
    *([("Hà Nội", "Việt Nam", "Hà Nội & Bắc Bộ", "Hỗn hợp (Hybrid)")] * 10),
    *([("Hà Nội", "Việt Nam", "Hà Nội & lân cận", "Trực tiếp tại địa điểm (On-site)")] * 5),
    *([("Hà Nội", "Việt Nam", "Toàn quốc & Trực tuyến", "Trực tuyến / Từ xa (Online)")] * 5),

    # TP. Hồ Chí Minh (35)
    *([("TP. Hồ Chí Minh", "Việt Nam", "TP.HCM & các tỉnh Đông Nam Bộ", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)")] * 15),
    *([("TP. Hồ Chí Minh", "Việt Nam", "TP.HCM, Bình Dương, Đồng Nai", "Hỗn hợp (Hybrid)")] * 10),
    *([("TP. Hồ Chí Minh", "Việt Nam", "TP.HCM & lân cận", "Trực tiếp tại địa điểm (On-site)")] * 5),
    *([("TP. Hồ Chí Minh", "Việt Nam", "Toàn quốc & Trực tuyến", "Trực tuyến / Từ xa (Online)")] * 5),

    # Đà Nẵng (8)
    ("Đà Nẵng", "Việt Nam", "Đà Nẵng, Quảng Nam, Huế", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)"),
    ("Đà Nẵng", "Việt Nam", "Đà Nẵng & miền Trung", "Hỗn hợp (Hybrid)"),
    ("Đà Nẵng", "Việt Nam", "Đà Nẵng", "Trực tiếp tại địa điểm (On-site)"),
    ("Đà Nẵng", "Việt Nam", "Đà Nẵng & Remote", "Trực tuyến / Từ xa (Online)"),
    ("Đà Nẵng", "Việt Nam", "Đà Nẵng, Hội An", "Hỗn hợp (Hybrid)"),
    ("Đà Nẵng", "Việt Nam", "Đà Nẵng", "Trực tiếp tại địa điểm (On-site)"),
    ("Đà Nẵng", "Việt Nam", "Đà Nẵng & miền Trung", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)"),
    ("Đà Nẵng", "Việt Nam", "Đà Nẵng", "Hỗn hợp (Hybrid)"),

    # Hải Phòng (5)
    ("Hải Phòng", "Việt Nam", "Hải Phòng, KCN Đình Vũ, Quảng Ninh", "Trực tiếp tại địa điểm (On-site)"),
    ("Hải Phòng", "Việt Nam", "Hải Phòng & Hải Dương", "Hỗn hợp (Hybrid)"),
    ("Hải Phòng", "Việt Nam", "Hải Phòng", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)"),
    ("Hải Phòng", "Việt Nam", "Hải Phòng, Cát Bà", "Trực tiếp tại địa điểm (On-site)"),
    ("Hải Phòng", "Việt Nam", "Hải Phòng & Remote", "Trực tuyến / Từ xa (Online)"),

    # Bắc Ninh (4)
    ("Bắc Ninh", "Việt Nam", "Bắc Ninh, KCN Yên Phong, Quế Võ", "Trực tiếp tại địa điểm (On-site)"),
    ("Bắc Ninh", "Việt Nam", "Bắc Ninh & Hà Nội", "Hỗn hợp (Hybrid)"),
    ("Bắc Ninh", "Việt Nam", "Bắc Ninh, Bắc Giang", "Trực tiếp tại địa điểm (On-site)"),
    ("Bắc Ninh", "Việt Nam", "Bắc Ninh", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)"),

    # Quảng Ninh (3)
    ("Quảng Ninh", "Việt Nam", "Hạ Long, Cẩm Phả, Móng Cái", "Trực tiếp tại địa điểm (On-site)"),
    ("Quảng Ninh", "Việt Nam", "Quảng Ninh & Hải Phòng", "Hỗn hợp (Hybrid)"),
    ("Quảng Ninh", "Việt Nam", "Móng Cái, cửa khẩu quốc tế", "Trực tiếp tại địa điểm (On-site)"),

    # Bình Dương (4)
    ("Bình Dương", "Việt Nam", "Thủ Dầu Một, KCN VSIP 1 & 2, Mỹ Phước", "Trực tiếp tại địa điểm (On-site)"),
    ("Bình Dương", "Việt Nam", "Bình Dương, TP.HCM", "Hỗn hợp (Hybrid)"),
    ("Bình Dương", "Việt Nam", "Bình Dương, Bến Cát, Tân Uyên", "Trực tiếp tại địa điểm (On-site)"),
    ("Bình Dương", "Việt Nam", "Bình Dương", "Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)"),

    # Đồng Nai (3)
    ("Đồng Nai", "Việt Nam", "Biên Hòa, KCN Amata, Nhơn Trạch", "Trực tiếp tại địa điểm (On-site)"),
    ("Đồng Nai", "Việt Nam", "Đồng Nai, TP.HCM", "Hỗn hợp (Hybrid)"),
    ("Đồng Nai", "Việt Nam", "Đồng Nai, Long Thành", "Trực tiếp tại địa điểm (On-site)"),

    # Vũng Tàu (3)
    ("Vũng Tàu", "Việt Nam", "TP. Vũng Tàu, Phú Mỹ, Cảng Cái Mép", "Trực tiếp tại địa điểm (On-site)"),
    ("Vũng Tàu", "Việt Nam", "Bà Rịa - Vũng Tàu & TP.HCM", "Hỗn hợp (Hybrid)"),
    ("Vũng Tàu", "Việt Nam", "Vũng Tàu & Remote", "Trực tuyến / Từ xa (Online)"),

    # Huế (3)
    ("Huế", "Việt Nam", "TP. Huế & các điểm di sản", "Trực tiếp tại địa điểm (On-site)"),
    ("Huế", "Việt Nam", "Huế, Đà Nẵng", "Hỗn hợp (Hybrid)"),
    ("Huế", "Việt Nam", "Huế & Remote", "Trực tuyến / Từ xa (Online)"),

    # Nha Trang (2)
    ("Nha Trang", "Việt Nam", "Nha Trang, Cam Ranh", "Trực tiếp tại địa điểm (On-site)"),
    ("Nha Trang", "Việt Nam", "Nha Trang & các resort ven biển", "Hỗn hợp (Hybrid)"),
]

# 100 Unique Names
NAMES = [
    "Nguyễn Minh Tuấn", "Trần Thị Bích Ngọc", "Lê Hoàng Long", "Phạm Hải Đăng",
    "Hoàng Mai Phương", "Vũ Quốc Cường", "Đặng Thùy Dương", "Bùi Anh Khoa",
    "Đỗ Minh Châu", "Hồ Thanh Tùng", "Ngô Kim Ngân", "Dương Văn Hùng",
    "Lý Quỳnh Nga", "Phan Gia Huy", "Võ Thị Ánh Tuyết", "Trịnh Đình Trọng",
    "Mai Thục Trinh", "Đoàn Văn Khánh", "Lâm Mỹ Hạnh", "Lương Đức Minh",
    "Nguyễn Bảo Trâm", "Trần Hữu Thắng", "Lê Thanh Hằng", "Phạm Trọng Tín",
    "Hoàng Thu Trang", "Vũ Nhật Nam", "Đặng Yến Nhi", "Bùi Thế Hiển",
    "Đỗ Phương Linh", "Hồ Văn Đạt", "Ngô Bảo Ngọc", "Dương Kiều Oanh",
    "Lý Hạo Nhiên", "Phan Cẩm Tú", "Võ Minh Khang", "Trịnh Mỹ Uyên",
    "Mai Văn Phước", "Đoàn Hồng Nhung", "Lâm Quốc Việt", "Lương Thảo Nguyên",
    "Nguyễn Trọng Đại", "Trần Như Ý", "Lê Quang Vinh", "Phạm Diệu Thảo",
    "Hoàng Tiến Đạt", "Vũ Mỹ Dung", "Đặng Khắc Duy", "Bùi Thu Hiền",
    "Đỗ Thành Công", "Hồ Xuân Trường", "Ngô Thị Cẩm Vân", "Dương Minh Trí",
    "Lý Lan Chi", "Phan Thanh Sơn", "Võ Thị Diễm My", "Trịnh Hùng Dũng",
    "Mai Bảo Châu", "Đoàn Đình Hưng", "Lâm Thu Thủy", "Lương Văn Quyết",
    "Nguyễn Hoài Thương", "Trần Đức Toàn", "Lê Kiều Trang", "Phạm Văn Thiện",
    "Hoàng Thảo Vy", "Vũ Gia Khiêm", "Đặng Tường Vy", "Bùi Văn Quý",
    "Đỗ Hương Giang", "Hồ Nguyên Khôi", "Ngô Thị Kim Tuyến", "Dương Quốc Dũng",
    "Lý Thị Thảo", "Phan Văn Nam", "Võ Cẩm Ly", "Trịnh Ngọc Sơn",
    "Mai Hoàng Lan", "Đoàn Văn Phúc", "Lâm Khánh Chi", "Lương Hoài Nam",
    "Nguyễn Ngọc Khánh", "Trần Thùy Trang", "Lê Đức Nhân", "Phạm Thúy Hằng",
    "Hoàng Minh Quân", "Vũ Thanh Mai", "Đặng Hữu Phúc", "Bùi Ngọc Ánh",
    "Đỗ Trọng Hiếu", "Hồ Thúy Kiều", "Ngô Đình Trí", "Dương Yến Trang",
    "Lý Văn Hậu", "Phan Thu Thảo", "Võ Tuấn Kiệt", "Trịnh Thùy Linh",
    "Mai Văn Thịnh", "Đoàn Phương Mai", "Lâm Bá Thông", "Lương Diệu Linh"
]

# Avatar Assets (10 static images in project)
AVATAR_ASSETS = [
    "/static/avatars/avatar_dung.jpg",
    "/static/avatars/avatar_ha.jpg",
    "/static/avatars/avatar_bich.jpg",
    "/static/avatars/avatar_cuong.jpg",
    "/static/avatars/avatar_duc.jpg",
    "/static/avatars/avatar_huong.jpg",
    "/static/avatars/avatar_khoa.jpg",
    "/static/avatars/avatar_nam.jpg",
    "/static/avatars/avatar_huy.jpg",
    "/static/avatars/avatar_lananh.jpg",
]

# Universities
UNIVERSITIES = [
    ("Đại học Ngoại ngữ - ĐHQGHN", "Ngôn ngữ học ứng dụng"),
    ("Đại học Ngoại thương (FTU)", "Tiếng Anh Thương mại"),
    ("Đại học Hà Nội (HANU)", "Biên phiên dịch Chuyên nghiệp"),
    ("Đại học KHXH&NV - ĐHQG TP.HCM", "Ngôn ngữ & Văn hóa Quốc tế"),
    ("Đại học Bách Khoa Hà Nội", "Kỹ thuật & Ngoại ngữ chuyên ngành"),
    ("Đại học Sư phạm TP.HCM", "Sư phạm & Dịch thuật Ngoại ngữ"),
    ("Đại học Kinh tế Quốc dân (NEU)", "Kinh tế đối ngoại & Ngoại ngữ"),
    ("Học viện Ngoại giao (DAV)", "Quan hệ Quốc tế & Ngoại giao"),
]

# Language-specific Certificates (Strict 10 languages)
CERTIFICATES_MAP = {
    "Tiếng Anh": [("IELTS 8.5 Academic", 2022), ("IELTS 8.0 Academic", 2023), ("TOEIC 985/990", 2021), ("IELTS 7.5 Academic", 2023)],
    "Tiếng Trung": [("HSK 6 (285/300) & HSKK Cao cấp", 2022), ("HSK 6 (270/300)", 2023), ("HSK 5 (260/300)", 2021), ("HSK 6", 2024)],
    "Tiếng Nhật": [("JLPT N1 (172/180)", 2022), ("JLPT N1 (160/180)", 2023), ("JLPT N2 (165/180)", 2021), ("JLPT N1", 2024)],
    "Tiếng Hàn": [("TOPIK 6 (Cấp cao nhất)", 2022), ("TOPIK 6 (Điểm xuất sắc)", 2023), ("TOPIK 5 (220/300)", 2021), ("TOPIK 6", 2024)],
    "Tiếng Pháp": [("DALF C1", 2022), ("DELF B2", 2023), ("DALF C2", 2021), ("DALF C1", 2024)],
    "Tiếng Đức": [("Goethe-Zertifikat C1", 2022), ("TestDaF TDN 5", 2023), ("Goethe-Zertifikat B2", 2021), ("Goethe C1", 2024)],
    "Tiếng Nga": [("ТРКИ C1", 2022), ("ТРКИ B2", 2023), ("ТРКИ C2", 2020), ("ТРКИ C1", 2024)],
    "Tiếng Tây Ban Nha": [("DELE C1", 2022), ("DELE B2", 2023), ("DELE C2", 2021), ("DELE C1", 2024)],
    "Tiếng Thái": [("Chứng chỉ tiếng Thái Cấp cao - Chulalongkorn", 2022), ("Kiểm tra trực tiếp - Đạt chuẩn thương mại", 2023), ("Tiếng Thái Thương mại Nâng cao", 2021)],
    "Tiếng Bồ Đào Nha": [("CELPE-Bras Cấp Avançado", 2022), ("CELPE-Bras Intermediário Superior", 2023), ("CELPE-Bras Avançado", 2021)],
}

EMPLOYMENT_PREFS = [
    "Freelance (Tự do)",
    "Hợp đồng theo dự án",
    "Bán thời gian (Part-time)",
    "Toàn thời gian (Full-time)",
]

AVAILABILITY_STATUSES = [
    "Sẵn sàng nhận việc ngay",
    "Nhận đặt lịch trước 3-5 ngày",
    "Sẵn sàng công tác xa",
    "Nhận dự án trực tuyến & tại chỗ",
    "Chỉ nhận việc cuối tuần",
]

INTERPRETING_TYPES_LIST = [
    "Phiên dịch nối tiếp (Consecutive), Đàm phán kinh doanh (Business Meeting)",
    "Phiên dịch cabin / Song song (Simultaneous), Phiên dịch nối tiếp (Consecutive)",
    "Phiên dịch tháp tùng (Escort), Phiên dịch trực tuyến (Online)",
    "Đàm phán kinh doanh (Business Meeting), Phiên dịch sự kiện (Event)",
    "Phiên dịch trực tuyến / Từ xa (Online), Phiên dịch hội thảo (Conference)",
    "Phiên dịch nối tiếp (Consecutive), Phiên dịch hiện trường (On-site)",
]

def build_experience_tiers():
    tiers = []

    # 15 Junior (0-2 yrs)
    junior_configs = [
        {"y": 1, "jobs": 0, "rating": 0.0, "rev": 0, "h_rate": 300000, "d_rate": 2000000, "level": "Cử nhân"},
        {"y": 1, "jobs": 2, "rating": 4.0, "rev": 2, "h_rate": 350000, "d_rate": 2200000, "level": "Cử nhân"},
        {"y": 2, "jobs": 3, "rating": 4.2, "rev": 3, "h_rate": 400000, "d_rate": 2500000, "level": "Cử nhân"},
        {"y": 1, "jobs": 1, "rating": 3.8, "rev": 1, "h_rate": 300000, "d_rate": 2000000, "level": "Cử nhân"},
        {"y": 2, "jobs": 5, "rating": 4.4, "rev": 4, "h_rate": 450000, "d_rate": 2800000, "level": "Cử nhân"},
        {"y": 1, "jobs": 0, "rating": 0.0, "rev": 0, "h_rate": 350000, "d_rate": 2200000, "level": "Cử nhân"},
        {"y": 2, "jobs": 4, "rating": 4.3, "rev": 3, "h_rate": 400000, "d_rate": 2600000, "level": "Cử nhân"},
        {"y": 2, "jobs": 5, "rating": 4.5, "rev": 5, "h_rate": 500000, "d_rate": 3000000, "level": "Cử nhân"},
        {"y": 1, "jobs": 2, "rating": 4.1, "rev": 2, "h_rate": 350000, "d_rate": 2300000, "level": "Cử nhân"},
        {"y": 2, "jobs": 4, "rating": 4.2, "rev": 4, "h_rate": 420000, "d_rate": 2700000, "level": "Cử nhân"},
        {"y": 1, "jobs": 1, "rating": 3.9, "rev": 1, "h_rate": 320000, "d_rate": 2100000, "level": "Cử nhân"},
        {"y": 2, "jobs": 3, "rating": 4.3, "rev": 3, "h_rate": 400000, "d_rate": 2500000, "level": "Cử nhân"},
        {"y": 1, "jobs": 0, "rating": 0.0, "rev": 0, "h_rate": 300000, "d_rate": 2000000, "level": "Cử nhân"},
        {"y": 2, "jobs": 5, "rating": 4.4, "rev": 4, "h_rate": 450000, "d_rate": 2800000, "level": "Cử nhân"},
        {"y": 2, "jobs": 4, "rating": 4.2, "rev": 3, "h_rate": 400000, "d_rate": 2600000, "level": "Cử nhân"},
    ]
    for cfg in junior_configs:
        tiers.append({
            "years": cfg["y"],
            "level": cfg["level"],
            "title_pfx": "Phiên dịch viên triển vọng",
            "jobs": cfg["jobs"],
            "rating": cfg["rating"],
            "rev": cfg["rev"],
            "h_rate": float(cfg["h_rate"]),
            "d_rate": float(cfg["d_rate"]),
            "p_basic": int(cfg["d_rate"]),
            "p_std": int(cfg["d_rate"] * 1.8),
            "p_prem": int(cfg["d_rate"] * 3.0),
        })

    # 35 Mid-level (3-5 yrs)
    for i in range(35):
        y = 3 + (i % 3)
        jobs = 12 + (i * 2) % 25
        rev = int(jobs * 0.75)
        rating = round(4.4 + ((i * 3) % 5) * 0.1, 1)
        if rating > 4.9:
            rating = 4.8
        base_h = 600000 + ((i * 7) % 8) * 80000
        base_d = 4000000 + ((i * 5) % 8) * 500000
        level = "Thạc sĩ" if i % 4 == 0 else "Cử nhân"
        tiers.append({
            "years": y,
            "level": level,
            "title_pfx": "Phiên dịch viên chuyên nghiệp",
            "jobs": jobs,
            "rating": rating,
            "rev": rev,
            "h_rate": float(base_h),
            "d_rate": float(base_d),
            "p_basic": int(base_d),
            "p_std": int(base_d * 1.7),
            "p_prem": int(base_d * 2.8),
        })

    # 35 Senior (6-10 yrs)
    for i in range(35):
        y = 6 + (i % 5)
        jobs = 38 + (i * 3) % 45
        rev = int(jobs * 0.78)
        rating = round(4.7 + ((i * 2) % 4) * 0.1, 1)
        if rating > 5.0:
            rating = 5.0
        base_h = 1000000 + ((i * 9) % 9) * 120000
        base_d = 7500000 + ((i * 6) % 8) * 800000
        level = "Tiến sĩ" if i % 7 == 0 else ("Thạc sĩ" if i % 2 == 0 else "Cử nhân")
        tiers.append({
            "years": y,
            "level": level,
            "title_pfx": "Chuyên gia phiên dịch cao cấp",
            "jobs": jobs,
            "rating": rating,
            "rev": rev,
            "h_rate": float(base_h),
            "d_rate": float(base_d),
            "p_basic": int(base_d),
            "p_std": int(base_d * 1.8),
            "p_prem": int(base_d * 2.9),
        })

    # 15 Expert (11-18 yrs)
    for i in range(15):
        y = 11 + (i % 7)
        jobs = 90 + (i * 6) % 75
        rev = int(jobs * 0.8)
        rating = 5.0 if i % 3 != 0 else 4.9
        base_h = 1800000 + ((i * 11) % 7) * 250000
        base_d = 13000000 + ((i * 8) % 6) * 1500000
        level = "Tiến sĩ" if i % 3 == 0 else "Thạc sĩ"
        tiers.append({
            "years": y,
            "level": level,
            "title_pfx": "Chuyên gia phiên dịch cabin kỳ cựu",
            "jobs": jobs,
            "rating": rating,
            "rev": rev,
            "h_rate": float(base_h),
            "d_rate": float(base_d),
            "p_basic": int(base_d),
            "p_std": int(base_d * 1.7),
            "p_prem": int(base_d * 2.7),
        })

    return tiers

ALL_TIERS = build_experience_tiers()


def generate_profile_data(idx):
    """Tạo dữ liệu chi tiết, thực tế và độc nhất cho hồ sơ thứ idx (0-99)."""
    lang_info = LANG_DATA[idx % len(LANG_DATA)]
    ind_primary = INDUSTRIES[idx % len(INDUSTRIES)]
    ind_secondary = INDUSTRIES[(idx + 7) % len(INDUSTRIES)]
    loc_city, loc_country, loc_area, loc_mode = LOCATIONS[idx % len(LOCATIONS)]
    name = NAMES[idx % len(NAMES)]
    exp = ALL_TIERS[idx % len(ALL_TIERS)]
    uni, major = UNIVERSITIES[idx % len(UNIVERSITIES)]

    # Certificate
    primary_tgt = lang_info["tgt"] if lang_info["tgt"] != "Tiếng Việt" else lang_info["src"]
    cert_options = CERTIFICATES_MAP.get(primary_tgt, [("Chứng chỉ Năng lực Ngôn ngữ Chuyên nghiệp", 2022)])
    cert_name, cert_year = cert_options[idx % len(cert_options)]

    # Proficiency
    y = exp["years"]
    if y <= 2:
        proficiency = "Thành thạo chuyên nghiệp (B2+/C1)"
    elif y <= 5:
        proficiency = "Thành thạo cao cấp (C1/C2)"
    elif y <= 10:
        proficiency = "Thành thạo xuất sắc (C2/Bản ngữ)"
    else:
        proficiency = "Chuyên gia bản ngữ / Cabin chuẩn Quốc tế"

    types = INTERPRETING_TYPES_LIST[idx % len(INTERPRETING_TYPES_LIST)]
    emp_pref = EMPLOYMENT_PREFS[idx % len(EMPLOYMENT_PREFS)]
    avail_stat = AVAILABILITY_STATUSES[idx % len(AVAILABILITY_STATUSES)]

    title = f"{exp['title_pfx']} {lang_info['pair']} | Chuyên ngành {ind_primary}"

    bio = (
        f"Phiên dịch viên chuyên nghiệp với {y} năm kinh nghiệm thực chiến trong cặp ngôn ngữ "
        f"{lang_info['pair']}, am hiểu sâu sắc thuật ngữ chuyên ngành {ind_primary} và {ind_secondary}. "
        f"Đã từng tham gia nhiều buổi hội nghị, đàm phán hợp đồng song phương và khảo sát hiện trường kỹ thuật. "
        f"Kỹ năng phản xạ nhanh, bảo mật thông tin tuyệt đối và tác phong làm việc chuẩn mực. "
        f"Sẵn sàng nhận lịch làm việc tại khu vực {loc_city} cũng như các dự án trực tuyến qua Zoom/Teams."
    )

    notable_clients = f"Tập đoàn đa quốc gia ngành {ind_primary}, Đối tác FDI tại {loc_city}, Ban tổ chức sự kiện quốc tế"
    featured_projects = f"Dự án đàm phán hợp đồng hợp tác {ind_primary}; Hội thảo xúc tiến thương mại {ind_secondary}"

    # Verification and Badges logic (75% Verified, 15% Partially verified, 10% Unverified)
    # Premium: 20% of profiles have Premium badge
    is_premium = (idx % 5 == 0)  # 20 profiles (0, 5, 10, ...)

    if idx < 75:
        # Verified
        is_verified = True
        verification_status = "approved"
        badge_list = ["Đã xác minh danh tính", "Đã kiểm tra kỹ năng"]
        if exp["rating"] >= 4.8 and exp["jobs"] >= 30:
            badge_list.append("Top Rated")
        if is_premium:
            badge_list.append("Premium PDV")
    elif idx < 90:
        # Partially verified
        is_verified = False
        verification_status = "pending" if idx < 85 else "revision"
        badge_list = ["Đang xác minh hồ sơ KYC"]
        if is_premium:
            badge_list.append("Premium PDV")
    else:
        # Unverified
        is_verified = False
        verification_status = "draft"
        badge_list = []
        if is_premium:
            badge_list.append("Premium PDV")

    badges_str = ", ".join(badge_list)

    # Standardized email format
    email = f"pdv{idx+1:03d}@demo.viettranslate.local"
    # Safe demo phone
    phone = f"0901000{idx+1:03d}"
    # Valid existing avatar
    avatar = AVATAR_ASSETS[idx % len(AVATAR_ASSETS)]

    return {
        "email": email,
        "legacy_email": f"demo_interpreter_{idx+1:03d}@viettranslate.demo",
        "name": name,
        "phone": phone,
        "avatar": avatar,
        "title": title,
        "bio": bio,
        "languages": lang_info["langs"],
        "source_language": lang_info["src"],
        "target_language": lang_info["tgt"],
        "interpreting_direction": "Hai chiều (Song phương)",
        "language_proficiency": proficiency,
        "native_language": lang_info["nat"],
        "specializations": f"{ind_primary}, {ind_secondary}",
        "interpreting_types": types,
        "work_modes": loc_mode,
        "city": loc_city,
        "country": loc_country,
        "service_areas": loc_area,
        "education_level": exp["level"],
        "university": uni,
        "major": major,
        "cert_name": cert_name,
        "cert_year": cert_year,
        "experience_years": y,
        "current_position": f"Phiên dịch viên {lang_info['tgt']} – {ind_primary}",
        "notable_clients": notable_clients,
        "featured_projects": featured_projects,
        "badges": badges_str,
        "rating": exp["rating"],
        "total_reviews": exp["rev"],
        "total_jobs": exp["jobs"],
        "hourly_rate": exp["h_rate"],
        "daily_rate": exp["d_rate"],
        "currency": "VND",
        "employment_preference": emp_pref,
        "availability_status": avail_stat,
        "basic_price": exp["p_basic"],
        "standard_price": exp["p_std"],
        "premium_price": exp["p_prem"],
        "is_verified": is_verified,
        "verification_status": verification_status,
        "is_premium": is_premium,
        "ind_primary": ind_primary,
        "ind_secondary": ind_secondary,
    }


def seed_demo_interpreters():
    """Tạo hoặc cập nhật đúng 100 hồ sơ phiên dịch viên demo."""
    with app.app_context():
        print("[SEED] Bắt đầu khởi tạo/đồng bộ 100 hồ sơ phiên dịch viên demo...")

        created_users = 0
        updated_users = 0
        default_pw_hash = generate_password_hash("Demo@123456", method="pbkdf2:sha256")

        try:
            for i in range(100):
                data = generate_profile_data(i)

                # Idempotency check: Find existing demo user by standardized email or legacy email
                user = User.query.filter_by(email=data["email"]).first()
                if not user:
                    user = User.query.filter_by(email=data["legacy_email"]).first()

                if not user:
                    user = User(
                        email=data["email"],
                        name=data["name"],
                        password_hash=default_pw_hash,
                        phone=data["phone"],
                        role="translator",
                        is_admin=False,
                        is_active=True,
                        is_demo=True,
                        email_verified=True,
                        avatar=data["avatar"],
                        city=data["city"],
                        bio=data["bio"],
                        is_public_profile=True,
                    )
                    db.session.add(user)
                    db.session.flush()
                    created_users += 1
                else:
                    user.email = data["email"]
                    user.name = data["name"]
                    user.phone = data["phone"]
                    user.role = "translator"
                    user.is_active = True
                    user.is_demo = True
                    user.avatar = data["avatar"]
                    user.city = data["city"]
                    user.bio = data["bio"]
                    user.is_public_profile = True
                    updated_users += 1

                # 1. TranslatorProfile
                profile = TranslatorProfile.query.filter_by(user_id=user.id).first()
                if not profile:
                    profile = TranslatorProfile(user_id=user.id)
                    db.session.add(profile)

                profile.title = data["title"]
                profile.bio = data["bio"]
                profile.languages = data["languages"]
                profile.source_language = data["source_language"]
                profile.target_language = data["target_language"]
                profile.interpreting_direction = data["interpreting_direction"]
                profile.language_proficiency = data["language_proficiency"]
                profile.native_language = data["native_language"]
                profile.specializations = data["specializations"]
                profile.interpreting_types = data["interpreting_types"]
                profile.work_modes = data["work_modes"]
                profile.education_level = data["education_level"]
                profile.university = data["university"]
                profile.major = data["major"]
                profile.cert_name = data["cert_name"]
                profile.cert_year = data["cert_year"]
                profile.certificates = f"{data['cert_name']} ({data['cert_year']})"
                profile.experience_years = data["experience_years"]
                profile.current_position = data["current_position"]
                profile.notable_clients = data["notable_clients"]
                profile.featured_projects = data["featured_projects"]
                profile.badges = data["badges"]
                profile.rating = data["rating"]
                profile.total_reviews = data["total_reviews"]
                profile.total_jobs = data["total_jobs"]
                profile.response_time = "Trong vòng 1 giờ"
                profile.is_verified = data["is_verified"]
                profile.is_demo = True
                profile.is_public = True
                profile.is_cv_public = False
                profile.hourly_rate = data["hourly_rate"]
                profile.daily_rate = data["daily_rate"]
                profile.currency = data["currency"]
                profile.employment_preference = data["employment_preference"]
                profile.availability_status = data["availability_status"]
                profile.service_areas = data["service_areas"]
                profile.country = data["country"]
                db.session.flush()

                # 2. TranslatorVerification (KYC module)
                verif = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
                if not verif:
                    verif = TranslatorVerification(user_id=user.id)
                    db.session.add(verif)

                verif.full_name = data["name"]
                verif.phone = data["phone"]
                verif.location = data["city"]
                verif.bio = data["bio"]
                verif.source_language = data["source_language"]
                verif.target_language = data["target_language"]
                verif.interpreting_direction = data["interpreting_direction"]
                verif.language_proficiency = data["language_proficiency"]
                verif.specializations = data["specializations"]
                verif.interpreting_types = data["interpreting_types"]
                verif.education_level = data["education_level"]
                verif.university = data["university"]
                verif.major = data["major"]
                verif.certificate_type = data["cert_name"].split()[0]
                verif.certificate_name = data["cert_name"]
                verif.cert_year = data["cert_year"]
                verif.experience_years = data["experience_years"]
                verif.current_position = data["current_position"]
                verif.notable_clients = data["notable_clients"]
                verif.featured_projects = data["featured_projects"]
                verif.status = data["verification_status"]
                if data["is_verified"]:
                    verif.current_step = 5
                    verif.reviewed_at = datetime.utcnow()
                elif data["verification_status"] in ["pending", "revision"]:
                    verif.current_step = 5
                    verif.submitted_at = datetime.utcnow()
                    if data["verification_status"] == "revision":
                        verif.rejection_reason = "Vui lòng bổ sung bản scan rõ nét hơn của chứng chỉ ngôn ngữ."
                else:
                    verif.current_step = 1

                # 3. Service Package (Used for search cards, pricing breakdown, and booking)
                svc = Service.query.filter_by(profile_id=profile.id).first()
                if not svc:
                    svc = Service(profile_id=profile.id)
                    db.session.add(svc)
                svc.name = f"Dịch vụ phiên dịch {data['ind_primary']}"
                svc.description = f"Gói dịch vụ phiên dịch {data['languages']} chuyên sâu ngành {data['ind_primary']} cho cuộc họp, đàm phán hoặc sự kiện."
                svc.languages = data["languages"]
                svc.category = data["ind_primary"]
                svc.basic_price = data["basic_price"]
                svc.standard_price = data["standard_price"]
                svc.premium_price = data["premium_price"]
                svc.basic_delivery = "1 ngày"
                svc.standard_delivery = "2 ngày"
                svc.premium_delivery = "3 ngày"

                # 4. InterpreterService (Phân hệ Mục V)
                isvc = InterpreterService.query.filter_by(user_id=user.id).first()
                if not isvc:
                    isvc = InterpreterService(user_id=user.id)
                    db.session.add(isvc)
                isvc.source_lang = data["source_language"]
                isvc.target_lang = data["target_language"]
                isvc.interpreting_type = data["interpreting_types"].split(",")[0].strip()
                isvc.specialization = data["ind_primary"]
                isvc.hourly_rate = data["hourly_rate"]
                isvc.session_rate = data["daily_rate"]
                isvc.currency = data["currency"]
                isvc.is_active = True

                # 5. InterpreterPreference (Phân hệ Mục 5.4)
                ipref = InterpreterPreference.query.filter_by(user_id=user.id).first()
                if not ipref:
                    ipref = InterpreterPreference(user_id=user.id)
                    db.session.add(ipref)
                lang_pairs_list = [
                    f"{data['source_language']} > {data['target_language']}",
                    f"{data['target_language']} > {data['source_language']}",
                ]
                ipref.set_languages_list(lang_pairs_list)
                ipref.specializations = data["specializations"]
                ipref.work_mode = "both"
                ipref.min_rate = data["hourly_rate"]
                ipref.max_rate = data["daily_rate"]
                ipref.locations = data["city"]

                # 6. TranslatorPreference (Smart Matching & Account Preferences)
                tpref = TranslatorPreference.query.filter_by(translator_id=user.id).first()
                if not tpref:
                    tpref = TranslatorPreference(translator_id=user.id)
                    db.session.add(tpref)
                tpref.languages = data["languages"]
                tpref.language_pairs = f"{data['source_language']} > {data['target_language']}, {data['target_language']} > {data['source_language']}"
                tpref.service_types = "Phiên dịch, Đàm phán thương mại, Hội họp, Sự kiện"
                tpref.specialties = data["specializations"]
                tpref.city = data["city"]
                tpref.work_mode = "both"
                tpref.offers_certified = True
                tpref.notify_new_jobs = True
                tpref.notify_messages = True
                tpref.notify_contracts = True
                tpref.notify_reviews = True

            db.session.commit()
            print(f"[SEED HOÀN TẤT] Tạo mới: {created_users}, Cập nhật: {updated_users}.")

            total_demo = TranslatorProfile.query.filter_by(is_demo=True).count()
            total_verified = TranslatorProfile.query.filter_by(is_demo=True, is_verified=True).count()
            total_profiles = TranslatorProfile.query.count()
            print(f"[DATABASE STATUS] Tổng số hồ sơ demo: {total_demo} (Verified: {total_verified}), Tổng hồ sơ toàn hệ thống: {total_profiles}")

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Quá trình seed gặp lỗi, đã rollback: {e}")
            raise


if __name__ == "__main__":
    seed_demo_interpreters()
