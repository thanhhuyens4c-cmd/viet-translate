import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

script = """
echo '=== 1. PATCH FLASK/__INIT__.PY ==='
/www/server/panel/pyenv/bin/python3 -c "
import flask
init_file = flask.__file__
content = open(init_file, 'r').read()
patch_code = '''
# aaPanel compatibility patch for Flask 2.3+
from .app import Flask
if not hasattr(Flask, 'session_cookie_name'):
    Flask.session_cookie_name = property(lambda self: self.config.get('SESSION_COOKIE_NAME', 'session'))
'''
if 'session_cookie_name' not in content:
    with open(init_file, 'a') as f:
        f.write(patch_code)
    print('SUCCESS: Appended compatibility property to flask/__init__.py!')
else:
    print('Already present in flask/__init__.py')
"

echo '=== 2. PATCH FLASK_SESSION/SESSIONS.PY DIRECTLY ==='
sed -i 's/app\.session_cookie_name/getattr(app, "session_cookie_name", app.config.get("SESSION_COOKIE_NAME", "session"))/g' /www/server/panel/class/flask_session/sessions.py
echo 'flask_session/sessions.py updated.'

echo '=== 3. VERIFY WITH PYTHON ==='
/www/server/panel/pyenv/bin/python3 -c "
import flask
app = flask.Flask('test')
print('app.session_cookie_name:', app.session_cookie_name)
"

echo '=== 4. RESTART BT PANEL ==='
bt restart
sleep 2

echo '=== 5. TEST CURL TO AAPANEL ==='
curl -k -s -D - https://127.0.0.1:10604/9254df4a | head -n 20
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
