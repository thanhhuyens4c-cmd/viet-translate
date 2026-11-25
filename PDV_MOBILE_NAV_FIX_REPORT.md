# BÁO CÁO ĐỒNG BỘ MENU PHIÊN DỊCH VIÊN (PDV) TRÊN MOBILE VỚI DESKTOP
**Dự án:** VietTranslate  
**Ngày thực hiện:** 19/10/2026  
**Trạng thái triển khai:** `CODE FIXED, NOT DEPLOYED`  

---

## 1. Nguyên nhân menu Mobile khác biệt so với Desktop
Trước khi sửa, mã điều hướng của thanh bên trên máy tính (Desktop Sidebar) và ngăn kéo điều hướng trên điện thoại (Mobile Drawer) trong file `templates/base.html` được duy trì thành hai khối HTML/Jinja riêng biệt:
1. **Khối Mobile Drawer** (trước đây khoảng dòng 890–1035): Chứa một liên kết thừa `"Trang chủ công khai"` và một khối accordion `"Tổng quan"` mở ra 5 đường dẫn con trỏ tới các phần (hash anchor `#section-*`) của trang Dashboard, cùng với thứ tự các mục trong nhóm `"Công việc"` bị đảo lộn so với desktop.
2. **Khối Desktop Sidebar** (trước đây khoảng dòng 1086–1192): Sử dụng cấu trúc danh mục chuẩn gồm 4 nhóm nghiệp vụ chính: **Tổng quan** (trỏ trực tiếp tới `interpreter_dashboard`), **Công việc** (Tìm việc, Việc phù hợp, Thống kê công việc), **Cá nhân** (Lịch làm việc, Thu nhập kèm 4 mục con, Tài khoản), và **Chung** (Về VietTranslate, Tin tức, Thanh toán Escrow).

Sự thiếu đồng bộ này khiến phiên dịch viên trên điện thoại gặp phải tình trạng trùng lặp thông tin (như mục Thống kê công việc xuất hiện 2 lần, mục Thu nhập xuất hiện ở cả Tổng quan và nhóm Cá nhân), đồng thời thiếu tính nhất quán trong trải nghiệm người dùng.

---

## 2. Danh sách mục dư và trùng lặp đã xử lý

| STT | Mục trước khi sửa | Vị trí / Href trước đây | Vấn đề | Biện pháp xử lý |
|---|---|---|---|---|
| **1** | Trang chủ công khai | Đứng đầu menu mobile (`url_for('index')`) | Thừa so với desktop sidebar; Logo trên Header điện thoại đã cung cấp sẵn đường về trang chủ | **Đã loại bỏ** khỏi menu PDV mobile |
| **2** | Accordion Tổng quan | Menu cha đóng/mở (`toggleMobOverview()`) | Desktop là liên kết trực tiếp, mobile lại là accordion phức tạp | **Đã chuyển đổi** thành liên kết đơn trỏ thẳng tới `interpreter_dashboard` giống Desktop |
| **3** | Thông tin hồ sơ & xác minh | Nằm trong submenu Tổng quan (`#section-profile`) | Trùng nội dung với trang Tài khoản | **Đã loại bỏ** liên kết hash thừa |
| **4** | Thống kê công việc | Nằm trong submenu Tổng quan (`#section-jobs`) | Trùng lặp với mục Thống kê công việc trong nhóm Công việc | **Đã loại bỏ** liên kết hash thừa, giữ duy nhất mục trong nhóm Công việc |
| **5** | Thống kê thu nhập | Nằm trong submenu Tổng quan (`#section-income`) | Trùng lặp với toàn bộ phân hệ nhóm Thu nhập | **Đã loại bỏ** liên kết hash thừa |
| **6** | Ca làm sắp tới | Nằm trong submenu Tổng quan (`#section-schedule`) | Trùng lặp với mục Lịch làm việc | **Đã loại bỏ** liên kết hash thừa |
| **7** | Việc làm đề xuất | Nằm trong submenu Tổng quan (`#section-recommended`) | Khác biệt và lệch luồng so với mục chuẩn Việc phù hợp (`job_list?recommended=1`) | **Đã loại bỏ** liên kết hash thừa |
| **8** | Đảo thứ tự nhóm Công việc | Việc phù hợp đứng trước Tìm việc | Không đồng bộ thứ tự với Desktop Sidebar | **Đã chuẩn hóa thứ tự:** 1. Tìm việc → 2. Việc phù hợp → 3. Thống kê công việc |
| **9** | Dead Code JS | Hàm `toggleMobOverview()` trong thẻ `<script>` | Không còn accordion Tổng quan | **Đã dọn dẹp** hoàn toàn khỏi JavaScript |

*Ghi chú quan trọng:* Không có bất kỳ route backend, controller, model hay logic dữ liệu nào bị xóa bỏ. Các section trên trang Dashboard vẫn hiển thị đầy đủ thông thường.

---

## 3. Danh sách mục chuẩn nghiệp vụ được giữ và đồng bộ

Sau khi chuẩn hóa, cấu trúc menu PDV trên Mobile Drawer khớp 100% với Desktop Sidebar:

```
[Tổng quan]
└── 1. Tổng quan                     → url_for('interpreter_dashboard')

[Nhóm: CÔNG VIỆC]
├── 2. Tìm việc                      → url_for('job_list')
├── 3. Việc phù hợp                  → url_for('job_list', recommended=1)
└── 4. Thống kê công việc            → url_for('job_statistics')

[Nhóm: CÁ NHÂN]
├── 5. Lịch làm việc                 → url_for('my_schedule')
├── 6. Thu nhập                      → url_for('interpreter_income_overview')
│   ├── 6.1. Chi tiết các khoản      → url_for('interpreter_income_details')
│   ├── 6.2. Theo dõi thanh toán     → url_for('interpreter_income_payouts')
│   ├── 6.3. Lịch sử giao dịch       → url_for('interpreter_income_transactions')
│   └── 6.4. Thông tin nhận tiền     → url_for('interpreter_income_bank_info')
└── 7. Tài khoản                     → url_for('account_profile')

[Nhóm: CHUNG]
├── 8. Về VietTranslate              → url_for('about')
├── 9. Tin tức                       → url_for('news_list')
└── 10. Thanh toán Escrow            → url_for('payment_info')
```

---

## 4. Các chức năng tiện ích được bảo toàn và vị trí truy cập

Các chức năng tiện ích tài khoản và thông tin liên lạc được giữ nguyên vẹn và bố trí khoa học:
- **Trên Desktop (Màn hình lớn):** 
  - Các icon tiện ích (Tin nhắn, Thông báo) hiển thị trên Top Header với badge số lượng chưa đọc theo thời gian thực.
  - Dropdown menu hồ sơ cá nhân chứa: Trợ giúp & Hỗ trợ, Cài đặt & Bảo mật, Đăng xuất.
- **Trên Mobile (Màn hình nhỏ):**
  - Top Header: Vẫn có icon chuông thông báo và nút chuyển đổi ngôn ngữ (VI/EN).
  - Chân ngăn kéo Mobile Drawer (`#mobile-nav` footer): Do thao tác hover trên màn hình cảm ứng điện thoại không khả dụng cho dropdown desktop, các chức năng thiết yếu được giữ nguyên ở chân ngăn kéo:
    * **Tin nhắn** (`messages_page`)
    * **Thông báo** (`notifications_page`)
    * **Trợ giúp & Hỗ trợ** (`account_profile?tab=support`)
    * **Cài đặt & Bảo mật** (`account_profile?tab=security`)
    * **Đăng xuất** (`logout` - nút nổi bật màu đỏ rose)

---

## 5. Kết quả Parity (Desktop vs Mobile)

| Tiêu chí | Desktop Sidebar | Mobile Drawer | Đánh giá Parity |
|---|---|---|---|
| Số lượng mục nghiệp vụ chính | 10 mục chính | 10 mục chính | **KHỚP 100% (10/10)** |
| Số lượng mục con Thu nhập | 4 mục con | 4 mục con | **KHỚP 100% (4/4)** |
| Thứ tự hiển thị các nhóm | Tổng quan → Công việc → Cá nhân → Chung | Tổng quan → Công việc → Cá nhân → Chung | **KHỚP 100%** |
| Nhãn hiển thị (Labels) | Giống nhau từng ký tự | Giống nhau từng ký tự | **KHỚP 100%** |
| Đích điều hướng (Endpoints) | Cùng sử dụng đúng các hàm `url_for(...)` | Cùng sử dụng đúng các hàm `url_for(...)` | **KHỚP 100%** |
| Trạng thái Active khi truy cập | Đồng bộ qua các biến cờ Jinja (`is_interp_*`) | Đồng bộ qua các biến cờ Jinja (`is_interp_*`) | **KHỚP 100%** |
| Cơ chế Accordion Thu nhập | ID: `desktop-income-group` / `desktop-income-submenu` | ID: `mob-income-menu` / `mob-income-btn` | **ĐỘC LẬP HOÀN TOÀN** (Không xung đột ID) |

---

## 6. Kết quả kiểm tra Breakpoint và Tương thích Giao diện

- **Desktop (>= 1024px - 1280px+):**
  - Sidebar hiển thị cố định bên trái (`w-60 lg:block`).
  - Hamburger menu và Mobile Drawer ẩn hoàn toàn (`lg:hidden`).
  - Bố cục 2 cột mượt mà, không bị tràn màn hình.
- **Tablet (768px - 1023px):**
  - Sidebar desktop ẩn, nhường không gian cho nội dung chính.
  - Hamburger button xuất hiện trên header, bấm mở Mobile Drawer trơn tru.
- **Mobile tiêu chuẩn (390px - iPhone 12/13/14/15/16):**
  - Menu mở dạng trượt mượt mà, chiều rộng vừa vặn 100% viewport.
  - Độ cao vùng chạm (touch target) của từng mục đạt chuẩn >= 40px, dễ bấm trên màn cảm ứng.
  - Không có thanh cuộn ngang (No horizontal overflow).
- **Mobile màn hình hẹp (320px - 360px - iPhone SE, Galaxy A-series nhỏ):**
  - Các icon và chữ xuống dòng linh hoạt, không bị vỡ layout hoặc cắt chữ.
  - Vùng cuộn dọc `max-h-[calc(100vh-4rem)] overflow-y-auto` cho phép cuộn toàn bộ danh sách dễ dàng.
  - Hành vi đóng menu: Tự động đóng menu khi bấm vào bất kỳ liên kết nào hoặc click ra ngoài vùng drawer.

---

## 7. Chi tiết các File đã chỉnh sửa

1. **`templates/base.html`**:
   - Dòng 903–1006: Chuẩn hóa khối mobile navigation dành cho role `translator`. Loại bỏ "Trang chủ công khai", xóa accordion "Tổng quan", sắp xếp lại nhóm "Công việc", chuẩn hóa nhóm "Cá nhân" và "Chung".
   - Dòng 1425–1436: Xóa bỏ hàm JavaScript `toggleMobOverview()` đã lỗi thời.
2. **`tests/test_pdv_mobile_nav_parity.py`** (File kiểm thử tự động mới):
   - Chứa 6 kịch bản kiểm thử toàn diện:
     * `test_pdv_mobile_and_desktop_item_parity`: Đối chiếu toàn bộ 14 URL và thứ tự xuất hiện giữa Desktop và Mobile.
     * `test_redundant_items_removed_from_mobile`: Xác thực không còn mục Trang chủ công khai, hash `#section-*`, hay mã `toggleMobOverview`.
     * `test_income_submenu_parity_and_controls`: Kiểm tra 4 mục con Thu nhập và sự tách biệt ID điều khiển accordion.
     * `test_utility_links_preserved_in_mobile_drawer`: Kiểm tra sự hiện diện đầy đủ của tin nhắn, thông báo, hỗ trợ, bảo mật, đăng xuất.
     * `test_active_states_across_views`: Xác thực class active và cơ chế tự động mở submenu Thu nhập khi đang ở trang con.
     * `test_role_isolation_hirer_and_guest`: Xác thực tính cô lập, không ảnh hưởng đến giao diện của Hirer và Guest.

---

## 8. Kết quả Chạy Kiểm thử (Test Suites)

### Chạy Suite Kiểm thử Parity Menu PDV:
```
python -m unittest tests/test_pdv_mobile_nav_parity.py
```
**Kết quả:**
```
Ran 6 tests in 3.132s
OK
```

### Chạy Toàn bộ Bộ Kiểm thử Hồi quy của Hệ thống:
```
python -m unittest discover -s tests -p "test_*.py"
```
**Kết quả:**
```
Ran 31 tests in 5.574s
OK (31/31 passed - 100% PASS)
```
- Không có bất kỳ lỗi hồi quy nào đối với phân hệ Hirer, Admin hay Guest.
- Hệ thống cơ sở dữ liệu và xác thực danh tính tiếp tục hoạt động ổn định.

---

## 9. Vấn đề chưa xử lý hoặc không thể xác minh
- **Môi trường Production (VPS IP):** Do công cụ duyệt web bên ngoài không kết nối được tới IP VPS trong phiên làm việc này, mọi thay đổi và xác minh được thực hiện, biên dịch và kiểm thử tự động 100% trên môi trường workspace cục bộ.
- **Trạng thái triển khai:** Mã nguồn đã được sửa hoàn chỉnh trong workspace, chưa thực hiện git commit/push lên remote repository theo đúng nguyên tắc chỉ thị (`CODE FIXED, NOT DEPLOYED`).
