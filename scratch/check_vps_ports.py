import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

commands = """
echo "=== 1. LISTENING PORTS (PORT 9000?) ==="
ss -tulpn | grep -E "9000|5000|nginx" || netstat -tulpn | grep 9000 || true

echo "=== 2. WEBHOOK CONFIG & SCRIPTS ON VPS ==="
find /etc/systemd/system /usr/local/bin /root /var/scripts -name "*webhook*" -o -name "*deploy*" 2>/dev/null || true

echo "=== 3. AA-PANEL CRON & TASKS ==="
cat /www/server/cron/a50afd8f7d0e95dc2fd7bbbcfdcccd82 2>/dev/null || true

echo "=== 4. WEBHOOK LOGS & NGINX 0_webhook.conf ==="
cat /www/server/panel/vhost/nginx/proxy/157.66.100.101/0_webhook.conf 2>/dev/null || true

echo "=== 5. CHECK WEBHOOK DAEMON STATUS ==="
systemctl list-units | grep -i webhook || true
ps aux | grep -i webhook || true
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
