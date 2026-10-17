#!/usr/bin/env bash
# ==============================================================================
# Script: deploy_viettranslate.sh (Zero-Downtime Auto-Deploy)
# Giải quyết triệt để lỗi 502 Bad Gateway:
# 1. Cơ chế flock chống chạy đè tiến trình
# 2. Tự động phục hồi cờ thực thi (+x) cho Python và Virtualenv
# 3. Pre-check cú pháp Python trước khi chạm vào service đang chạy
# 4. Graceful Reload (SIGHUP) - không downtime
# 5. Tự động kiểm tra Health Check & Rollback an toàn nếu commit mới lỗi
# ==============================================================================

set -euo pipefail

PROJECT_DIR="/www/wwwroot/157.66.100.101"
SERVICE_NAME="viettranslate.service"
LOCK_FILE="/var/lock/viettranslate_deploy.lock"
LOG_FILE="/var/log/viettranslate_deploy.log"
BRANCH="main"

mkdir -p "$(dirname "$LOCK_FILE")" 2>/dev/null || true
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================================="
log "🚀 [DEPLOY] Bắt đầu triển khai tự động..."

# --- 1. CHỐNG XUNG ĐỘT (FILE LOCK) ---
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    log "⚠️ [LOCK] Có một tiến trình deploy đang chạy. Bỏ qua yêu cầu trùng lặp."
    exit 0
fi

cd "$PROJECT_DIR" || { log "❌ Không tìm thấy thư mục $PROJECT_DIR"; exit 1; }

# Đảm bảo quyền thực thi cho Python hệ thống và Virtualenv ngay từ đầu
chmod +x /usr/bin/python3* /usr/bin/pip* 2>/dev/null || true
if [ -d "$PROJECT_DIR/venv/bin" ]; then
    chmod +x "$PROJECT_DIR/venv/bin/"* 2>/dev/null || true
fi

# Lưu lại commit hiện tại để sẵn sàng Rollback nếu có sự cố
PREV_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "HEAD")
log "ℹ️ [GIT] Commit hiện tại: $PREV_COMMIT"

# --- 2. ĐỒNG BỘ MÃ NGUỒN TỪ GITHUB ---
log "📥 [GIT] Đang fetch mã nguồn từ GitHub origin/$BRANCH..."
git fetch origin "$BRANCH"
NEW_COMMIT=$(git rev-parse "origin/$BRANCH")

if [ "$PREV_COMMIT" = "$NEW_COMMIT" ]; then
    log "✅ [GIT] Mã nguồn đã ở bản mới nhất ($NEW_COMMIT). Kết thúc."
    log "=========================================================="
    exit 0
fi

# Áp dụng code mới
git reset --hard "origin/$BRANCH"
git clean -fd -e .env -e instance/ -e venv/ -e private_storage/ -e uploads/

# Đảm bảo lại quyền sau khi git reset
chmod +x /usr/bin/python3* /usr/bin/pip* 2>/dev/null || true
if [ -d "$PROJECT_DIR/venv/bin" ]; then
    chmod +x "$PROJECT_DIR/venv/bin/"* 2>/dev/null || true
fi

# Dọn cache pyc
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

VENV_PY="$PROJECT_DIR/venv/bin/python3"
VENV_PIP="$PROJECT_DIR/venv/bin/pip"

# --- 3. CẬP NHẬT THƯ VIỆN (CHỈ KHI REQUIREMENTS THAY ĐỔI) ---
if git diff --name-only "$PREV_COMMIT" "$NEW_COMMIT" | grep -q "^requirements.txt$"; then
    log "📦 [PIP] Phát hiện thay đổi trong requirements.txt. Đang cài đặt..."
    if [ -f "$VENV_PIP" ]; then
        "$VENV_PIP" install -r "$PROJECT_DIR/requirements.txt" --quiet --no-cache-dir
    fi
fi

# --- 4. PRE-CHECK CÚ PHÁP PYTHON (CHỐNG LỖI 502 DO BUG CODE) ---
log "🔍 [CHECK] Kiểm tra cú pháp mã nguồn mới..."
if [ -f "$VENV_PY" ]; then
    if ! "$VENV_PY" -m compileall -q "$PROJECT_DIR/app.py" "$PROJECT_DIR/models.py" "$PROJECT_DIR/config.py" "$PROJECT_DIR/services" 2>&1 | tee -a "$LOG_FILE"; then
        log "❌ [CRITICAL] Phát hiện lỗi cú pháp trong code mới! Đang hủy deploy và rollback về $PREV_COMMIT..."
        git reset --hard "$PREV_COMMIT"
        log "🛡️ [ROLLBACK] Đã giữ nguyên phiên bản cũ an toàn. Dịch vụ không bị ảnh hưởng."
        exit 1
    fi
    log "✅ [CHECK] Cú pháp mã nguồn hợp lệ."
fi

# --- 5. CHẠY MIGRATION CƠ SỞ DỮ LIỆU NẾU CÓ ---
if [ -f "$PROJECT_DIR/migrations/migrate_payout_to_db.py" ]; then
    log "🗄️ [DB] Kiểm tra migration..."
    "$VENV_PY" "$PROJECT_DIR/migrations/migrate_payout_to_db.py" >> "$LOG_FILE" 2>&1 || true
fi

# --- 6. PHÂN QUYỀN CHUẨN XÁC ---
log "🔒 [PERM] Phân quyền chuẩn cho thư mục web..."
chown -R www:www "$PROJECT_DIR"
chmod +x "$PROJECT_DIR/venv/bin/"* 2>/dev/null || true
chmod 600 "$PROJECT_DIR/.env" 2>/dev/null || true

# --- 7. TÁI KHỞI ĐỘNG DỊCH VỤ AN TOÀN (ZERO DOWNTIME RELOAD) ---
log "🔄 [RELOAD] Nạp lại mã nguồn cho $SERVICE_NAME..."
# Ưu tiên gửi tín hiệu SIGHUP để Gunicorn reload mà không đóng kết nối socket
if systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl kill -s HUP "$SERVICE_NAME" 2>/dev/null || systemctl restart "$SERVICE_NAME"
else
    systemctl start "$SERVICE_NAME"
fi

# Chờ 3 giây để worker mới nạp hoàn tất
sleep 3

# --- 8. KIỂM TRA SỨC KHỎE (HEALTH CHECK & AUTO-ROLLBACK) ---
log "🩺 [HEALTH] Kiểm tra phản hồi website..."
HEALTH_OK=0
for i in {1..5}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:5000/" || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
        HEALTH_OK=1
        log "✅ [HEALTH] Dịch vụ phản hồi tốt (HTTP $HTTP_CODE) ở lần kiểm tra $i."
        break
    fi
    log "⏳ [HEALTH] Lần $i: HTTP $HTTP_CODE. Chờ 2 giây..."
    sleep 2
done

if [ "$HEALTH_OK" -eq 0 ]; then
    log "❌ [ALERT] Dịch vụ trả về HTTP $HTTP_CODE sau khi deploy! Đang kích hoạt AUTO-ROLLBACK..."
    git reset --hard "$PREV_COMMIT"
    systemctl restart "$SERVICE_NAME"
    log "⚠️ [ROLLBACK] Đã khôi phục về commit cũ $PREV_COMMIT để bảo vệ website."
    exit 1
fi

log "🎉 [SUCCESS] Triển khai commit $NEW_COMMIT thành công! Website hoạt động bình thường."
log "=========================================================="
exit 0
