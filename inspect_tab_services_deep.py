with open('templates/account_profile.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
m = re.search(r'id=["\']tab-services["\']', text)
if m:
    start = m.start()
    # find next tab or 5000 chars
    next_tab = text.find('id="tab-', start + 20)
    print("Tab-services length:", next_tab - start if next_tab != -1 else "end of file")
    content = text[start:next_tab if next_tab != -1 else start + 8000]
    
    # Check for form fields in tab-services
    print("\nForms and inputs in tab-services:")
    for line in content.split('\n'):
        if '<form' in line or 'name=' in line or 'action=' in line or 'languages' in line:
            print("  ", line.strip()[:120])
