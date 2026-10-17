import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

commands = """
echo "=== NGINX SSL & DOMAIN CONFIG ==="
grep -rn "server_name" /www/server/panel/vhost/nginx/ /etc/nginx/ 2>/dev/null || true

echo "=== CHECK ALL ACCESS LOGS FOR POST TO /webhook IN LAST 2 DAYS ==="
grep -E "POST /webhook" /www/wwwlogs/* 2>/dev/null || true

echo "=== CHECK ACCESS LOGS WITH GITHUB IN USER AGENT ==="
grep -i "github" /www/wwwlogs/* 2>/dev/null || true
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
