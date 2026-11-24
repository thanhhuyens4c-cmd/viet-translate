with open('templates/account_profile.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Scanning for forms and tabs around line 4425:")
for i in range(4425, 0, -1):
    line = lines[i]
    if 'id="tab-' in line or 'id=\'tab-' in line or '<form' in line:
        print(f"Line {i+1}: {line.strip()[:100]}")
        if 'tab-' in line:
            break

print("\nScanning forward for form closing or submit button:")
for i in range(4425, min(len(lines), 4700)):
    line = lines[i]
    if '</form>' in line or 'type="submit"' in line:
        print(f"Line {i+1}: {line.strip()[:100]}")
