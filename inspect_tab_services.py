with open('templates/account_profile.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
m = re.search(r'id=["\']tab-services["\']', text)
if m:
    start = m.start()
    print("Found tab-services:")
    print(text[start:start+3000])
else:
    print("Not found tab-services")
