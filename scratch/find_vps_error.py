import subprocess

commands = """
echo "=== SEARCH FOR 3c01dbcc / 3C01DBCC ==="
grep -rni "3c01dbcc" /var/log/ /tmp/ /www/wwwroot/ /root/ 2>/dev/null | head -n 30

echo "=== RECENT GUNICORN / FLASK LOGS ==="
journalctl -u viettranslate -n 100 --no-pager 2>/dev/null || true
if [ -f /var/log/gunicorn.log ]; then tail -n 50 /var/log/gunicorn.log; fi
if [ -f /var/log/viettranslate.log ]; then tail -n 50 /var/log/viettranslate.log; fi
find /www/wwwroot/ -name "*.log" -exec tail -n 20 {} + 2>/dev/null
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
