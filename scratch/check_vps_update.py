import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

commands = """
echo "=== 1. GIT STATUS & LATEST COMMIT ON VPS ==="
cd /www/wwwroot/157.66.100.101 && git status && git log -1 --oneline
echo "--- Remote origin url ---"
git remote -v

echo "=== 2. WEBHOOK SERVICES / PROCESSES ==="
ps aux | grep -E "webhook|deploy|gunicorn|viettranslate" | grep -v grep

echo "=== 3. SYSTEMD SERVICES ==="
systemctl status webhook --no-pager 2>&1 || true
echo "--- viettranslate.service ---"
systemctl status viettranslate --no-pager 2>&1 || true

echo "=== 4. CRON JOBS ==="
crontab -l 2>&1 || true
ls -la /etc/cron.d/ 2>&1 || true

echo "=== 5. DEPLOY LOGS ==="
if [ -f /var/log/viettranslate_deploy.log ]; then
    tail -n 30 /var/log/viettranslate_deploy.log
else
    echo "No /var/log/viettranslate_deploy.log found"
fi

echo "=== 6. WEBHOOK NGINX ROUTE ==="
grep -rn "webhook" /www/server/panel/vhost/nginx/ /etc/nginx/ 2>/dev/null || true
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
