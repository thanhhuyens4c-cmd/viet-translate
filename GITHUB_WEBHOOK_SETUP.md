# Hướng Dẫn Thiết Lập Tự Động Deploy Qua GitHub Webhook (Auto-Deploy)

Tài liệu này cung cấp giải pháp tự động triển khai mã nguồn (Auto-Deploy) từ GitHub branch `main` lên VPS Ubuntu 24.04 (chạy Nginx/Gunicorn/aaPanel).

---

## 1. So Sánh Các Phương Pháp Triển Khai Webhook Phổ Biến

| Tiêu chí | Cách 1: Python Webhook Daemon (Khuyên dùng) | Cách 2: Plugin WebHook của aaPanel | Cách 3: adnanh/webhook (Golang) |
| :--- | :--- | :--- | :--- |
| **Bảo mật** | ⭐⭐⭐ Chữ ký HMAC SHA-256 chuẩn GitHub | ⭐⭐ Khóa URL token tĩnh (`access_key`) | ⭐⭐⭐ HMAC SHA-256 |
| **Phản hồi GitHub** | Siêu nhanh (< 500ms, chạy deploy nền) | Trung bình (tùy thời gian chạy script) | Siêu nhanh |
| **Xử lý xung đột** | Có `flock` chống 2 deploy chạy đè lên nhau | Chạy tuần tự theo hàng đợi aaPanel | Cần cấu hình thêm |
| **Độ phụ thuộc** | Chỉ dùng thư viện có sẵn của Python 3 | Phụ thuộc App Store aaPanel | Cần cài gói deb `webhook` |

---

## 2. Chi Tiết Kiến Trúc Phương Pháp 1 (Khuyên Dùng)

Phương pháp này bao gồm 3 thành phần chính đã được chuẩn bị sẵn trong thư mục `scripts/`:

1. **[`scripts/deploy_viettranslate.sh`](file:///c:/Users/ASUS/Desktop/Bài tập nhóm/viet-translate/scripts/deploy_viettranslate.sh)**:
   - Cơ chế file lock (`flock`) chống xung đột khi push nhiều commit liên tục.
   - `git fetch` và `git reset --hard origin/main` để đồng bộ code sạch, loại bỏ file tạm hoặc cache `.pyc`.
   - Bảo toàn an toàn `.env`, thư mục upload và database.
   - Kiểm tra `requirements.txt`, chỉ cài đặt package nếu có thư viện mới.
   - Restart dịch vụ Gunicorn và kiểm tra Health Check (HTTP 200).
   - Ghi nhật ký đầy đủ ra `/var/log/viettranslate_deploy.log`.

2. **[`scripts/webhook_receiver.py`](file:///c:/Users/ASUS/Desktop/Bài tập nhóm/viet-translate/scripts/webhook_receiver.py)**:
   - Nhận request từ GitHub, giải mã và so khớp chữ ký bí mật `X-Hub-Signature-256`.
   - Lọc chính xác: chỉ kích hoạt khi push vào branch `refs/heads/main`.
   - Trả lời HTTP `200 OK` ngay lập tức cho GitHub (tránh bị lỗi timeout 10 giây).
   - Đẩy lệnh deploy vào luồng chạy ngầm (Background Thread).

3. **[`scripts/viettranslate-webhook.service`](file:///c:/Users/ASUS/Desktop/Bài tập nhóm/viet-translate/scripts/viettranslate-webhook.service)**:
   - Quản trị tiến trình webhook bằng Systemd trên Linux, tự khởi động lại khi gặp sự cố hoặc reboot VPS.

---

## 3. Các Bước Cài Đặt Trên VPS (Chỉ Chạy Khi Được Phép)

### Bước 1: Sao chép script deploy vào hệ thống
```bash
sudo cp /www/wwwroot/157.66.100.101/scripts/deploy_viettranslate.sh /usr/local/bin/deploy_viettranslate.sh
sudo chmod +x /usr/local/bin/deploy_viettranslate.sh
```

### Bước 2: Thiết lập dịch vụ Systemd cho Webhook Receiver
```bash
sudo cp /www/wwwroot/157.66.100.101/scripts/viettranslate-webhook.service /etc/systemd/system/viettranslate-webhook.service
sudo systemctl daemon-reload
sudo systemctl enable viettranslate-webhook.service
sudo systemctl restart viettranslate-webhook.service
sudo systemctl status viettranslate-webhook.service --no-pager
```

### Bước 3: Cấu hình Nginx chuyển tiếp Webhook URL
Thêm đoạn sau vào file cấu hình Nginx của website (trong aaPanel -> Website -> Settings -> Nginx Config hoặc Reverse Proxy):

```nginx
location /webhook {
    proxy_pass http://127.0.0.1:9000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;
    proxy_set_header X-GitHub-Event $http_x_github_event;
}
```
Reload lại Nginx:
```bash
nginx -s reload
```

---

## 4. Cấu Hình Webhook Trên GitHub Repository

1. Truy cập vào kho chứa GitHub của bạn:
   `https://github.com/thanhhuyens4c-cmd/viet-translate/settings/hooks`
2. Nhấn nút **Add webhook**.
3. Điền các thông số:
   - **Payload URL**: `http://103.161.118.158/webhook` *(hoặc tên miền nếu đã trỏ domain)*
   - **Content type**: Chọn `application/json` *(Rất quan trọng, không chọn application/x-www-form-urlencoded)*
   - **Secret**: Nhập chuỗi secret: `viettranslate-deploy-2026`
   - **SSL verification**: Chọn `Disable` nếu chưa cài SSL Let's Encrypt cho IP, hoặc `Enable` nếu dùng Domain có SSL.
   - **Which events would you like to trigger this webhook?**: Chọn `Just the push event`.
   - **Active**: Tích chọn `Active`.
4. Nhấn **Add webhook**. GitHub sẽ gửi 1 ping test thử (dấu tích xanh `✓ 200` là thành công).

---

## 5. Tùy Chọn Thay Thế: Thiết Lập Bằng WebHook Plugin Của aaPanel

Nếu bạn thích sử dụng giao diện trực quan của aaPanel:
1. Vào **aaPanel** -> mục **App Store** -> tìm và cài đặt plugin **WebHook**.
2. Mở plugin **WebHook** -> nhấn **Add Hook**:
   - Tên: `Deploy-VietTranslate`
   - Script Code:
     ```bash
     bash /usr/local/bin/deploy_viettranslate.sh
     ```
3. aaPanel sẽ cấp cho bạn một đường link Webhook dạng:
   `http://103.161.118.158:8888/hook?access_key=XXXXX&param=viettranslate`
4. Lấy link này dán vào **Payload URL** trên GitHub Webhook.
