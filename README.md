
# VietTranslate - Nền tảng Thuê Phiên Dịch Viên

> 🌐 **Website trực tuyến (Live Demo):** [https://viet-translate-beta.vercel.app/](https://viet-translate-beta.vercel.app/)

Đây là phiên bản prototype của nền tảng kết nối Người thuê dịch thuật và Phiên dịch viên (Freelancer), được xây dựng bằng Python (Flask) và Tailwind CSS.

## Tính năng (MVP)
1. **Luồng Xác thực:** Đăng ký (chọn vai trò Khách / Phiên dịch viên), Đăng nhập (mock OTP & Social login).
2. **Luồng 1 - Tìm Phiên dịch viên:** Danh sách phiên dịch viên, lọc theo ngôn ngữ, đánh giá. Xem chi tiết hồ sơ (dịch vụ, giá, đánh giá).
3. **Luồng 2 - Tìm việc & Bidding:** Khách hàng đăng Job, Phiên dịch viên duyệt danh sách Job và gửi Đề xuất (Báo giá).
4. **Quản lý Tài khoản:** Xem thông tin cá nhân, lịch sử giao dịch.
5. **Mô phỏng quy trình 8 bước:** Giao diện quản lý trạng thái hợp đồng (Escrow, Thực hiện, Giải ngân).

## Yêu cầu hệ thống
- Python 3.8 trở lên.

## Hướng dẫn cài đặt và chạy

1. **Cài đặt thư viện:**
   Mở terminal trong thư mục dự án và chạy lệnh:
   ```bash
   pip install -r requirements.txt
   ```

2. **Khởi tạo dữ liệu mẫu (Mock data):**
   Chạy script để tạo database (SQLite) và thêm dữ liệu giả:
   ```bash
   python seed_data.py
   ```

3. **Khởi động Server:**
   ```bash
   python app.py
   ```

4. **Trải nghiệm:**
   Mở trình duyệt và truy cập `http://127.0.0.1:5000`
   
   Bạn có thể đăng nhập bằng các tài khoản mẫu đã tạo:
   - **Tài khoản Người Thuê:** Email: `hirer@test.com` / Mật khẩu: `123456`
   - **Tài khoản Phiên dịch viên 1:** Email: `trans1@test.com` / Mật khẩu: `123456`
   - **Tài khoản Phiên dịch viên 2:** Email: `trans2@test.com` / Mật khẩu: `123456`

## Công nghệ sử dụng
- **Backend:** Flask, Flask-SQLAlchemy (SQLite)
- **Frontend:** HTML5, Tailwind CSS (via CDN), Vanilla JavaScript
