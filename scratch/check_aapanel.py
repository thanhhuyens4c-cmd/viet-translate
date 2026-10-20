import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

script = """
/www/server/panel/pyenv/bin/python3 -c "
import flask
print('aaPanel Flask file:', flask.__file__)
print('Has session_cookie_name?', hasattr(flask.Flask, 'session_cookie_name'))
"
"""

cmd = [
    r'C:\Program Files\PuTTY\plink.exe',
    '-ssh', 'root@103.161.118.158',
    '-pw', '@Sieutoc!ZX!1*vxuUEGA',
    '-hostkey', 'SHA256:ZHXHJTiY7My+bY5AqRr3NrHAjc30l0J7AcLFLuBbZSE',
    script
]
res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
print(res.stdout)
if res.stderr:
    print('STDERR:', res.stderr)
