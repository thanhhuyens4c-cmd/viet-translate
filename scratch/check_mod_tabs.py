import re, sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/account_profile.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()[:4167]

for idx, line in enumerate(lines):
    if any(k in line.lower() for k in ['cv', 'verification', 'giấy tờ', 'xác minh', 'bằng cấp', 'chứng chỉ']):
        if idx > 480: # inside tabs
            print(f'{idx+1}: {line.strip()[:90]}')
