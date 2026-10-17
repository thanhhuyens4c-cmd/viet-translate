import os
import re
import json

templates_dir = 'templates'
vi_json = 'i18n/vi.json'
en_json = 'i18n/en.json'

with open(vi_json, 'r', encoding='utf-8') as f:
    vi_data = json.load(f)
with open(en_json, 'r', encoding='utf-8') as f:
    en_data = json.load(f)

if 'auto' not in vi_data:
    vi_data['auto'] = {}
    en_data['auto'] = {}

def get_key(vi_text):
    import string
    # create a safe key from vi_text
    key = vi_text.lower()
    for c in string.punctuation:
        key = key.replace(c, '')
    key = key.replace(' ', '_')
    # keep it short
    key = key[:20].strip('_')
    if not key:
        key = "str"
    # Ensure uniqueness
    base_key = key
    counter = 1
    while base_key in vi_data['auto'] and vi_data['auto'][base_key] != vi_text:
        base_key = f"{key}_{counter}"
        counter += 1
    return base_key

# Regex for {{ 'vi' if current_lang == 'vi' else 'en' }}
# We'll use a function to process each match
pattern_1 = re.compile(r"\{\{\s*'([^']+)'\s*if\s*current_lang\s*==\s*'vi'\s*else\s*'([^']+)'\s*\}\}")
pattern_2 = re.compile(r'\{\{\s*"([^"]+)"\s*if\s*current_lang\s*==\s*\'vi\'\s*else\s*"([^"]+)"\s*\}\}')
# For cases like ( 'vi' if current_lang == 'vi' else 'en' )
pattern_3 = re.compile(r"\(\s*'([^']+)'\s*if\s*current_lang\s*==\s*'vi'\s*else\s*'([^']+)'\s*\)")
pattern_4 = re.compile(r'\(\s*"([^"]+)"\s*if\s*current_lang\s*==\s*\'vi\'\s*else\s*"([^"]+)"\s*\)')

def replacer(match):
    vi_text = match.group(1)
    en_text = match.group(2)
    key = get_key(vi_text)
    vi_data['auto'][key] = vi_text
    en_data['auto'][key] = en_text
    return f"{{{{ t('auto.{key}') }}}}"

def replacer_paren(match):
    vi_text = match.group(1)
    en_text = match.group(2)
    key = get_key(vi_text)
    vi_data['auto'][key] = vi_text
    en_data['auto'][key] = en_text
    return f"t('auto.{key}')"

for root, dirs, files in os.walk(templates_dir):
    for filename in files:
        if filename.endswith('.html'):
            filepath = os.path.join(root, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            orig = content
            content = pattern_1.sub(replacer, content)
            content = pattern_2.sub(replacer, content)
            content = pattern_3.sub(replacer_paren, content)
            content = pattern_4.sub(replacer_paren, content)
            
            if content != orig:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated {filepath}")

with open(vi_json, 'w', encoding='utf-8') as f:
    json.dump(vi_data, f, ensure_ascii=False, indent=2)
with open(en_json, 'w', encoding='utf-8') as f:
    json.dump(en_data, f, ensure_ascii=False, indent=2)

print("Done template replacements.")
