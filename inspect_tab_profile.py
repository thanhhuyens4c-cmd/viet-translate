with open('templates/account_profile.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
m = re.search(r'id=["\']tab-profile["\']', text)
if m:
    start = m.start()
    next_tab = text.find('id="tab-', start + 20)
    print("Found tab-profile! Length:", next_tab - start if next_tab != -1 else "end of file")
    content = text[start:next_tab if next_tab != -1 else start + 8000]
    for line in content.split('\n'):
        if '<form' in line or 'name=' in line or 'languages' in line:
            print("  ", line.strip()[:120])
else:
    print("Not found tab-profile")
