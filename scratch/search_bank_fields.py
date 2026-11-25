with open('templates/account_profile.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'bank_name' in line or 'bank_account_number' in line:
        print(f"{i+1}: {line.strip()}")
