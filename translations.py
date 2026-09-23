# -*- coding: utf-8 -*-
"""
VietTranslate Internationalization (i18n) Module
Contains localized string dictionaries for Vietnamese (vi) and English (en),
along with helper functions for string lookup and dynamic language list localization.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

# Base directory for i18n
I18N_DIR = os.path.join(os.path.dirname(__file__), 'i18n')

TRANSLATIONS = {}

def load_translations():
    global TRANSLATIONS
    for lang in ['vi', 'en']:
        file_path = os.path.join(I18N_DIR, f"{lang}.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                TRANSLATIONS[lang] = json.load(f)
        except Exception as e:
            logger.error(f"[i18n] Failed to load {lang}.json: {e}")
            TRANSLATIONS[lang] = {}

# Load initially
load_translations()

def t(key, lang='vi', **kwargs):
    """
    Look up a translation string using a dot-separated key (e.g. 'nav.home').
    Supports string formatting via **kwargs.
    Falls back to 'vi' if language is not supported, or returns [Missing: lang.key] if key is not found.
    """
    if lang not in TRANSLATIONS:
        lang = 'vi'
    
    parts = key.split('.')
    current = TRANSLATIONS.get(lang, {})
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            logger.warning(f"[i18n] Missing key: {lang}.{key}")
            return f"[Missing: {lang}.{key}]"
    
    if isinstance(current, str):
        if kwargs:
            try:
                return current.format(**kwargs)
            except KeyError as e:
                logger.error(f"[i18n] Format KeyError for key '{key}': {e}")
                return current
            except Exception as e:
                logger.error(f"[i18n] Format Exception for key '{key}': {e}")
                return current
        return current
    
    logger.warning(f"[i18n] Key '{lang}.{key}' does not point to a string.")
    return f"[Missing: {lang}.{key}]"


# ─── Language List Configuration ───
LANGUAGES = [
    {'code': 'vi', 'slug': 'tieng-viet', 'name': 'Tiếng Việt', 'en_name': 'Vietnamese', 'flag': '🇻🇳'},
    {'code': 'en', 'slug': 'tieng-anh', 'name': 'Tiếng Anh', 'en_name': 'English', 'flag': '🇬🇧'},
    {'code': 'ja', 'slug': 'tieng-nhat', 'name': 'Tiếng Nhật', 'en_name': 'Japanese', 'flag': '🇯🇵'},
    {'code': 'ko', 'slug': 'tieng-han', 'name': 'Tiếng Hàn', 'en_name': 'Korean', 'flag': '🇰🇷'},
    {'code': 'zh', 'slug': 'tieng-trung', 'name': 'Tiếng Trung', 'en_name': 'Chinese', 'flag': '🇨🇳'},
    {'code': 'fr', 'slug': 'tieng-phap', 'name': 'Tiếng Pháp', 'en_name': 'French', 'flag': '🇫🇷'},
    {'code': 'de', 'slug': 'tieng-duc', 'name': 'Tiếng Đức', 'en_name': 'German', 'flag': '🇩🇪'},
    {'code': 'ru', 'slug': 'tieng-nga', 'name': 'Tiếng Nga', 'en_name': 'Russian', 'flag': '🇷🇺'},
    {'code': 'th', 'slug': 'tieng-thai', 'name': 'Tiếng Thái', 'en_name': 'Thai', 'flag': '🇹🇭'},
    {'code': 'es', 'slug': 'tieng-tay-ban-nha', 'name': 'Tiếng Tây Ban Nha', 'en_name': 'Spanish', 'flag': '🇪🇸'},
    {'code': 'pt', 'slug': 'tieng-bo-dao-nha', 'name': 'Tiếng Bồ Đào Nha', 'en_name': 'Portuguese', 'flag': '🇵🇹'},
    {'code': 'km', 'slug': 'tieng-khmer', 'name': 'Tiếng Khmer', 'en_name': 'Khmer', 'flag': '🇰🇭'},
    {'code': 'lo', 'slug': 'tieng-lao', 'name': 'Tiếng Lào', 'en_name': 'Lao', 'flag': '🇱🇦'},
]

def get_localized_languages(lang='vi'):
    """
    Returns the list of supported languages with names localized for the current interface.
    """
    localized = []
    for item in LANGUAGES:
        loc = item.copy()
        if lang == 'en':
            loc['display_name'] = loc['en_name']
        else:
            loc['display_name'] = loc['name']
        localized.append(loc)
    return localized


def get_language_display_name(name, lang='vi'):
    """
    Maps a stored Vietnamese language name (e.g. 'Tiếng Nhật', as saved on Job/Service
    records) to its localized display name. Falls back to the original value when the
    active language is Vietnamese or when no match is found (e.g. free-text values).
    """
    if lang != 'en' or not name:
        return name
    for item in LANGUAGES:
        if item['name'] == name:
            return item['en_name']
    return name
