import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

commands = """
echo "=== 1. NGINX ACCESS LOGS FOR /webhook ==="
grep "webhook" /www/wwwlogs/* 2>/dev/null | tail -n 30 || true

echo "=== 2. TEST LOCAL WEBHOOK WITH CURL ==="
curl -s http://127.0.0.1:9000/
echo ""
curl -s http://127.0.0.1/webhook
echo ""
curl -s http://103.161.118.158/webhook
echo ""

echo "=== 3. CHECK PUBLIC ACCESS TO /webhook ==="
curl -s -I http://103.161.118.158/webhook
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
