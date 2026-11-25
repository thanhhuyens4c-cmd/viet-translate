with open('templates/account_profile.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

tab_starts = []
for idx, line in enumerate(lines):
    if '<div id="tab-' in line:
        tab_starts.append((idx + 1, line.strip()[:60]))

tab_starts.append((len(lines), 'END'))
for i in range(len(tab_starts) - 1):
    start_line, label = tab_starts[i]
    end_line = tab_starts[i+1][0]
    count = end_line - start_line
    print(f'{label:<40} Lines {start_line:4d} - {end_line:4d} ({count:4d} lines)')
