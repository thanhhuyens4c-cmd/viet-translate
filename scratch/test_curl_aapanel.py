import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

script = """
echo '=== 1. CURL WITH COOKIE AND FOLLOW REDIRECTS ==='
curl -k -c /tmp/cookies.txt -b /tmp/cookies.txt -L -i https://127.0.0.1:10604/9254df4a

echo '=== 2. BT DEFAULT ==='
bt default
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
