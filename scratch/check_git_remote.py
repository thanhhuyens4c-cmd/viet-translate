import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

commands = """
echo "=== GIT CONFIG ON VPS ==="
cd /www/wwwroot/157.66.100.101
git config -l
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
