import re, sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/account_profile.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for idx, line in enumerate(lines):
    if 'id="tab-' in line:
        print(f'{idx+1}: {line.strip()[:100]}')
