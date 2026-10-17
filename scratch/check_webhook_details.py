import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

commands = """
echo "=== 1. SYSTEMD STATUS OF viettranslate-webhook.service ==="
systemctl status viettranslate-webhook.service --no-pager

echo "=== 2. RECENT JOURNAL LOGS OF WEBHOOK SERVICE ==="
journalctl -u viettranslate-webhook.service -n 50 --no-pager

echo "=== 3. WEBHOOK RECEIVER SCRIPT (/usr/local/bin/webhook_deploy.py) ==="
cat /usr/local/bin/webhook_deploy.py

echo "=== 4. GIT LATEST COMMIT ON VPS VS REMOTE GITHUB ==="
cd /www/wwwroot/157.66.100.101
echo "Current HEAD on VPS:"
git log -3 --oneline
echo "Fetching origin to see latest remote commits:"
git fetch origin main 2>&1
echo "Origin main HEAD:"
git log origin/main -3 --oneline
"""

cmd = [
    r"C:\Program Files\PuTTY\plink.exe",
    "-ssh", "root@103.161.118.158",
    "-pw", "@Sieutoc!ZX!1*vxuUEGA",
    "-hostkey", "SHA256:ZHXHJTiY7My+bY5AqRr3NrHAjc30l0J7AcLFLuBbZSE",
    commands
]

res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
print("STDOUT:\n", res.stdout)
if res.stderr:
    print("STDERR:\n", res.stderr)
