#!/usr/bin/env python3
"""
==============================================================================
Script: webhook_receiver.py
Purpose: GitHub Webhook Receiver bảo mật chuẩn HMAC-SHA256 để Auto-Deploy.
Tham khảo tiêu chuẩn bảo mật và vận hành:
1. Xác thực HMAC-SHA256 signature (X-Hub-Signature-256) chống giả mạo request.
2. Lọc chính xác sự kiện: chỉ nhận 'push' event trên branch 'refs/heads/main'.
3. Phản hồi HTTP 200 tức thì cho GitHub (< 500ms) để chống GitHub Webhook timeout (10s).
4. Kích hoạt script deploy chạy nền (Asynchronous / Non-blocking).
5. Chỉ sử dụng thư viện tiêu chuẩn của Python 3 (không phụ thuộc pip bên ngoài).
==============================================================================
"""

import os
import sys
import json
import hmac
import hashlib
import logging
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- CẤU HÌNH ---
PORT = int(os.getenv("WEBHOOK_PORT", "9000"))
HOST = os.getenv("WEBHOOK_HOST", "127.0.0.1")  # Mặc định lắng nghe localhost để Nginx reverse proxy
SECRET = os.getenv("WEBHOOK_SECRET", "")       # Khóa bí mật cấu hình trên GitHub Webhook
DEPLOY_SCRIPT = os.getenv("DEPLOY_SCRIPT", "/usr/local/bin/deploy_viettranslate.sh")
LOG_FILE = os.getenv("WEBHOOK_LOG", "/var/log/viettranslate_webhook.log")

# Thiết lập ghi log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8") if os.access("/var/log", os.W_OK) else logging.NullHandler()
    ]
)

def run_deploy_async(commit_sha, author):
    """Thực thi script deploy trong tiến trình riêng biệt để không chặn webhook"""
    logging.info(f"🚀 [WORKER] Bắt đầu kích hoạt deploy cho commit {commit_sha} bởi {author}...")
    try:
        # Chạy script bash deploy độc lập
        proc = subprocess.Popen(
            ["bash", DEPLOY_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        stdout, _ = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"✅ [WORKER] Deploy hoàn tất thành công (Exit code 0).")
        else:
            logging.error(f"❌ [WORKER] Deploy thất bại với exit code {proc.returncode}!\nChi tiết: {stdout[-500:]}")
    except Exception as e:
        logging.exception(f"❌ [WORKER] Lỗi ngoại lệ khi thực thi deploy script: {e}")


def verify_signature(secret: str, payload_bytes: bytes, signature_header: str) -> bool:
    """Xác thực HMAC SHA-256 từ header X-Hub-Signature-256 của GitHub"""
    if not secret:
        # Nếu chưa cấu hình secret thì cảnh báo bảo mật
        logging.warning("⚠️ [SECURITY] WEBHOOK_SECRET chưa được thiết lập! Khuyến nghị cấu hình ngay.")
        return True

    if not signature_header:
        logging.warning("❌ [AUTH] Thiếu header X-Hub-Signature-256.")
        return False

    parts = signature_header.split("sha256=")
    if len(parts) != 2:
        logging.warning("❌ [AUTH] Định dạng chữ ký không đúng (cần bắt đầu bằng sha256=).")
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    # Sử dụng compare_digest chống tấn công dò thời gian (Timing Attack)
    return hmac.compare_digest(expected_signature, parts[1])


class WebhookHandler(BaseHTTPRequestHandler):
    server_version = "VietTranslateWebhook/1.0"

    def _send_response_json(self, status_code: int, data: dict):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_GET(self):
        """Endpoint kiểm tra trạng thái hoạt động của receiver"""
        self._send_response_json(200, {
            "status": "healthy",
            "message": "VietTranslate Webhook Receiver is running.",
            "target_branch": "main"
        })

    def do_POST(self):
        # 1. Kiểm tra URL path
        if self.path not in ("/webhook", "/webhook/", "/"):
            self._send_response_json(404, {"error": "Not Found"})
            return

        # 2. Đọc raw body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            self._send_response_json(400, {"error": "Missing or empty request body"})
            return

        payload_bytes = self.rfile.read(content_length)

        # 3. Xác thực chữ ký GitHub HMAC-SHA256
        sig_header = self.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(SECRET, payload_bytes, sig_header):
            logging.warning("⛔ [SECURITY] Chữ ký HMAC không hợp lệ! Từ chối yêu cầu.")
            self._send_response_json(403, {"error": "Invalid signature"})
            return

        # 4. Phân loại sự kiện GitHub (X-GitHub-Event)
        event = self.headers.get("X-GitHub-Event", "push")
        if event == "ping":
            logging.info("🏓 Nhận sự kiện 'ping' từ GitHub. Kết nối Webhook hoạt động bình thường!")
            self._send_response_json(200, {"message": "pong"})
            return

        if event != "push":
            logging.info(f"ℹ️ Bỏ qua sự kiện không phải push: {event}")
            self._send_response_json(200, {"message": f"Ignored event: {event}"})
            return

        # 5. Phân tích nội dung JSON payload
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            logging.error(f"❌ Không thể parse JSON payload: {e}")
            self._send_response_json(400, {"error": "Invalid JSON format"})
            return

        ref = payload.get("ref", "")
        expected_ref = "refs/heads/main"

        # 6. Kiểm tra xem có đúng là push vào branch main không
        if ref != expected_ref:
            logging.info(f"ℹ️ Push tới branch '{ref}'. Bỏ qua vì chỉ auto-deploy '{expected_ref}'.")
            self._send_response_json(200, {
                "message": f"Push on branch '{ref}' ignored. Only '{expected_ref}' is deployed."
            })
            return

        after_commit = payload.get("after", "unknown")
        author = payload.get("pusher", {}).get("name", "unknown")
        commit_msg = payload.get("head_commit", {}).get("message", "").strip().split("\n")[0]

        logging.info(f"🔔 Nhận push hợp lệ vào main | Commit: {after_commit[:7]} | Tác giả: {author} | Msg: {commit_msg}")

        # 7. Trả về phản hồi 200 OK ngay lập tức cho GitHub
        self._send_response_json(200, {
            "status": "accepted",
            "message": "Deployment triggered in background",
            "commit": after_commit,
            "branch": "main"
        })

        # 8. Kích hoạt tiến trình deploy ngầm (Asynchronous Thread)
        deploy_thread = threading.Thread(
            target=run_deploy_async,
            args=(after_commit[:7], author),
            daemon=True
        )
        deploy_thread.start()


def main():
    server = HTTPServer((HOST, PORT), WebhookHandler)
    logging.info(f"🚀 VietTranslate GitHub Webhook Receiver đang lắng nghe tại {HOST}:{PORT}")
    logging.info(f"📁 Deploy Script: {DEPLOY_SCRIPT}")
    logging.info(f"🔒 HMAC Secret: {'ĐÃ CẤU HÌNH' if SECRET else 'CHƯA CẤU HÌNH (Khuyến nghị thêm secret)'}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Đang dừng Webhook Receiver...")
        server.server_close()


if __name__ == "__main__":
    main()
