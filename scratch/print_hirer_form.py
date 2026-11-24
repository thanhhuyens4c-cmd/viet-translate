with open('templates/account_profile.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
m = re.search(r'name=[\'"]action[\'"]\s+value=[\'"]hirer_profile[\'"]', text)
start = text.rfind('<form', 0, m.start())
end = text.find('</form>', m.start())
print(text[start:end+7])
