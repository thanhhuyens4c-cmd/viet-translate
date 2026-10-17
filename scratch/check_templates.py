import re
import sys

def check_template(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = {
        'if': ('{% if ', '{% endif %}'),
        'for': ('{% for ', '{% endfor %}'),
        'block': ('{% block ', '{% endblock %}'),
    }

    print(f"=== Checking: {filepath} ===")
    has_error = False
    for name, (open_pattern, close_pattern) in blocks.items():
        open_count = len(re.findall(re.escape(open_pattern), content))
        close_count = len(re.findall(re.escape(close_pattern), content))
        print(f"  {name.upper()}: {open_count} open, {close_count} close")
        if open_count != close_count:
            print(f"  [ERROR] Mismatched {name} tags: {open_count} vs {close_count}")
            has_error = True

    return not has_error

templates = [
    'templates/income_base.html',
    'templates/income_overview.html',
    'templates/income_details.html',
    'templates/income_payouts.html',
    'templates/income_transactions.html',
    'templates/income_bank_info.html',
]

all_ok = True
for t in templates:
    ok = check_template(t)
    if not ok:
        all_ok = False

if all_ok:
    print("\nALL TEMPLATES BALANCED & SYNTACTICALLY VALID!")
else:
    sys.exit(1)
