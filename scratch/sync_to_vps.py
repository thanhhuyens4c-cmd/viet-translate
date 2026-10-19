import subprocess
import os

files_to_sync = [
    ("app.py", "/www/wwwroot/157.66.100.101/app.py"),
    ("templates/admin_jobs.html", "/www/wwwroot/157.66.100.101/templates/admin_jobs.html"),
    ("templates/admin_job_review.html", "/www/wwwroot/157.66.100.101/templates/admin_job_review.html"),
    ("services/admin_job_service.py", "/www/wwwroot/157.66.100.101/services/admin_job_service.py"),
    ("templates/admin_hirer_verify.html", "/www/wwwroot/157.66.100.101/templates/admin_hirer_verify.html"),
    ("templates/admin_verification_detail.html", "/www/wwwroot/157.66.100.101/templates/admin_verification_detail.html"),
    ("templates/translator_list.html", "/www/wwwroot/157.66.100.101/templates/translator_list.html"),
]

pscp_bin = r"C:\Program Files\PuTTY\pscp.exe"
plink_bin = r"C:\Program Files\PuTTY\plink.exe"
host = "root@103.161.118.158"
pw = "@Sieutoc!ZX!1*vxuUEGA"
hostkey = "SHA256:ZHXHJTiY7My+bY5AqRr3NrHAjc30l0J7AcLFLuBbZSE"

print("--- Uploading files to VPS ---")
for local, remote in files_to_sync:
    print(f"Uploading {local} -> {remote}")
    res = subprocess.run([
        pscp_bin,
        "-pw", pw,
        "-hostkey", hostkey,
        local,
        f"{host}:{remote}"
    ], capture_output=True, text=True, errors='ignore')
    if res.returncode != 0:
        print(f"FAILED {local}: {res.stderr}")
    else:
        print(f"OK {local}")

print("\n--- Fixing permissions & restarting service on VPS ---")
remote_cmd = """
chown -R www:www /www/wwwroot/157.66.100.101/app.py /www/wwwroot/157.66.100.101/templates /www/wwwroot/157.66.100.101/services
systemctl restart viettranslate
systemctl is-active viettranslate
"""

res = subprocess.run([
    plink_bin,
    "-ssh", host,
    "-pw", pw,
    "-hostkey", hostkey,
    remote_cmd
], capture_output=True, text=True, errors='ignore')

print("Remote command output:\n", res.stdout)
if res.stderr:
    print("Remote stderr:\n", res.stderr)
