# BÁO CÁO RÀ SOÁT ĐỐI CHIẾU HỆ THỐNG ĐIỀU HƯỚNG PHIÊN DỊCH VIÊN (PDV)
## VIETTRANSLATE: DESKTOP SIDEBAR vs. MOBILE NAVIGATION DRAWER

> **Tài liệu kiểm toán mã nguồn:** `PDV_MOBILE_NAV_AUDIT.md`  
> **Thời điểm kiểm tra:** 19/10/2026  
> **Tập tin nguồn đối chiếu:** `templates/base.html` (Mobile: dòng 902–1091, Desktop: dòng 1173–1261)  
> **Trạng thái Git:** Branch `main`, working tree clean, commit gần nhất `5e6e835`.

---

## 1. DANH SÁCH MENU DESKTOP CHUẨN (ROLE: TRANSLATOR)
Dựa trên khối `<aside>` dành cho `current_user.role == 'translator'` trong `templates/base.html`:

| STT | Nhóm hiển thị | Tên mục | Endpoint / URL | Icon SVG | Điều kiện Active |
|:---:|:---|:---|:---|:---:|:---|
| 1 | *(Độc lập)* | **Tổng quan** | `url_for('interpreter_dashboard')` | Home | `is_interp_overview` |
| 2 | **CÔNG VIỆC** | **Tìm việc** | `url_for('job_list')` | Search | `is_interp_browse` |
| 3 | **CÔNG VIỆC** | **Việc phù hợp** | `url_for('job_list', recommended=1)` | Stars/Sparkles | `is_interp_rec` |
| 4 | **CÔNG VIỆC** | **Thống kê công việc** | `url_for('job_statistics')` | Chart Bar | `is_interp_stats` |
| 5 | **CÁ NHÂN** | **Lịch làm việc** | `url_for('my_schedule')` | Calendar | `is_interp_schedule` |
| 6 | **CÁ NHÂN** | **Thu nhập** *(Mục cha kèm menu con)* | `url_for('interpreter_income_overview')` | Currency | `is_income_overview` / `is_interp_income` |
| 6.1 | CÁ NHÂN / Thu nhập | *Chi tiết các khoản* | `url_for('interpreter_income_details')` | None (Thụt lề) | `endpoint == 'interpreter_income_details'` |
| 6.2 | CÁ NHÂN / Thu nhập | *Theo dõi thanh toán* | `url_for('interpreter_income_payouts')` | None (Thụt lề) | `endpoint == 'interpreter_income_payouts'` |
| 6.3 | CÁ NHÂN / Thu nhập | *Lịch sử giao dịch* | `url_for('interpreter_income_transactions')` | None (Thụt lề) | `endpoint == 'interpreter_income_transactions'` |
| 6.4 | CÁ NHÂN / Thu nhập | *Thông tin nhận tiền* | `url_for('interpreter_income_bank_info')` | None (Thụt lề) | `endpoint == 'interpreter_income_bank_info'` |
| 7 | **CÁ NHÂN** | **Tài khoản** | `url_for('account_profile')` | User | `is_interp_account` |
| 8 | **CHUNG** | **Về VietTranslate** | `url_for('about')` | Info | `is_guest_about` |
| 9 | **CHUNG** | **Tin tức** | `url_for('news_list')` | Newspaper | `is_guest_news` |
| 10 | **CHUNG** | **Thanh toán Escrow** | `url_for('payment_info')` | Shield Check | `is_guest_payment` |

*Ghi chú: Toàn bộ danh sách chuẩn gồm 10 mục chính, trong đó mục Thu nhập có 4 mục con.*

---

## 2. DANH SÁCH MENU MOBILE HIỆN TẠI (ROLE: TRANSLATOR)
Dựa trên khối `#mobile-nav` dành cho `current_user.role == 'translator'` trong `templates/base.html`:

| STT | Khối / Nhóm | Tên mục | Endpoint / Href thực tế | Trạng thái kỹ thuật |
|:---:|:---|:---|:---|:---|
| M1 | *(Độc lập)* | Trang chủ công khai | `url_for('index')` | Khác biệt so với desktop |
| M2 | Accordion | Tổng quan *(Nút bấm mở menu con)* | `onclick="toggleMobOverview()"` | Khác biệt so với desktop (Dạng accordion) |
| M2.1| Submenu Tổng quan | Thông tin hồ sơ và xác minh | `url_for('account_profile')` | Liên kết con trong accordion |
| M2.2| Submenu Tổng quan | Thống kê công việc | `url_for('interpreter_dashboard')#section-jobs` | Neo trang dashboard |
| M2.3| Submenu Tổng quan | Thống kê thu nhập | `url_for('interpreter_dashboard')#section-income` | Neo trang dashboard |
| M2.4| Submenu Tổng quan | Ca làm sắp tới | `url_for('interpreter_dashboard')#section-schedule` | Neo trang dashboard |
| M2.5| Submenu Tổng quan | Việc làm đề xuất | `url_for('interpreter_dashboard')#section-recommended` | Neo trang dashboard |
| M3 | Công việc | Tìm việc | `url_for('job_list')` | Khớp desktop |
| M4 | Công việc | Thống kê công việc | `url_for('job_statistics')` | Nằm trước Việc phù hợp (Lệch thứ tự) |
| M5 | Công việc | Việc phù hợp | `url_for('job_list', recommended=1)` | Nằm sau Thống kê công việc (Lệch thứ tự) |
| M6 | Cá nhân | Lịch làm việc | `url_for('my_schedule')` | Khớp desktop |
| M7 | Cá nhân | Thu nhập *(Mục cha kèm menu con)* | `url_for('interpreter_income_overview')` | Khớp desktop |
| M7.1| Submenu Thu nhập | Chi tiết các khoản | `url_for('interpreter_income_details')` | Khớp desktop |
| M7.2| Submenu Thu nhập | Theo dõi thanh toán | `url_for('interpreter_income_payouts')` | Khớp desktop |
| M7.3| Submenu Thu nhập | Lịch sử giao dịch | `url_for('interpreter_income_transactions')` | Khớp desktop |
| M7.4| Submenu Thu nhập | Thông tin nhận tiền | `url_for('interpreter_income_bank_info')` | Khớp desktop |
| M8 | Cá nhân | Tài khoản | `url_for('account_profile')` | Khớp desktop |
| M9 | Chức năng dùng chung | Về VietTranslate | `url_for('about')` | Khớp desktop |
| M10| Chức năng dùng chung | Tin tức | `url_for('news_list')` | Khớp desktop |
| M11| Chức năng dùng chung | Thanh toán Escrow | `url_for('payment_info')` | Khớp desktop |
| M12| Chân drawer chung | Tin nhắn | `url_for('messages_page')` | Tiện ích chung cho logged in user |
| M13| Chân drawer chung | Thông báo | `url_for('notifications_page')` | Tiện ích chung cho logged in user |
| M14| Chân drawer chung | Trợ giúp & Hỗ trợ | `url_for('account_profile', tab='support')` | Tiện ích chung cho logged in user |
| M15| Chân drawer chung | Cài đặt & Bảo mật | `url_for('account_profile', tab='security')` | Tiện ích chung cho logged in user |
| M16| Chân drawer chung | Đăng xuất | `url_for('logout')` | Tiện ích thiết yếu |

---

## 3. BẢNG ĐỐI CHIẾU KHÁC BIỆT & ĐỀ XUẤT XỬ LÝ

| Mục trên Mobile | Vấn đề phát hiện | Phân loại | Hướng xử lý đề xuất |
|:---|:---|:---:|:---|
| **Trang chủ công khai** | Desktop sidebar không có mục này. Logo trên sticky header luôn sẵn sàng đưa người dùng về `/`. | **MỤC DƯ** | **Loại bỏ** khỏi menu PDV trên mobile; logo trên header vẫn bảo đảm chức năng về trang chủ. |
| **Tổng quan (Accordion)** | Desktop chỉ là 1 liên kết đơn trỏ tới `interpreter_dashboard`. Mobile lại tạo accordion mở 5 shortcut neo. | **KHÁC ĐÍCH & DƯ** | **Chuyển thành 1 mục Tổng quan duy nhất** trỏ trực tiếp tới `interpreter_dashboard`, có active state đầy đủ, bỏ accordion. |
| **Thông tin hồ sơ và xác minh** | Nằm trong accordion Tổng quan, trùng lặp với mục "Tài khoản" (`account_profile`). | **MỤC TRÙNG** | **Loại bỏ** liên kết trùng trong accordion; giữ mục "Tài khoản" chuẩn. |
| **Thống kê công việc (Submenu)** | Neo vào `#section-jobs` của dashboard, trong khi nhóm "Công việc" đã có trang riêng `job_statistics`. | **MỤC TRÙNG / SAI ĐÍCH** | **Loại bỏ** liên kết neo; giữ mục "Thống kê công việc" chuẩn trong nhóm Công việc. |
| **Thống kê thu nhập (Submenu)** | Neo vào `#section-income` của dashboard, trùng lặp với cả phân hệ "Thu nhập" ngay bên dưới. | **MỤC TRÙNG / SAI ĐÍCH** | **Loại bỏ** liên kết neo; giữ phân hệ "Thu nhập" chuẩn. |
| **Ca làm sắp tới (Submenu)** | Neo vào `#section-schedule` của dashboard, trùng lặp chức năng với "Lịch làm việc" (`my_schedule`). | **MỤC TRÙNG / SAI ĐÍCH** | **Loại bỏ** liên kết neo; giữ mục "Lịch làm việc" chuẩn. |
| **Việc làm đề xuất (Submenu)** | Neo vào `#section-recommended` của dashboard, khác đích với mục "Việc phù hợp" (`job_list?recommended=1`). | **MỤC TRÙNG / SAI ĐÍCH** | **Loại bỏ** liên kết neo; giữ mục "Việc phù hợp" theo chuẩn desktop. |
| **Thứ tự nhóm Công việc** | Mobile đang xếp: *Tìm việc -> Thống kê công việc -> Việc phù hợp*. Desktop là: *Tìm việc -> Việc phù hợp -> Thống kê công việc*. | **LỆCH THỨ TỰ** | **Đổi lại thứ tự** theo đúng chuẩn desktop: 1. Tìm việc, 2. Việc phù hợp, 3. Thống kê công việc. |
| **Thu nhập và 4 mục con** | Đã có đủ 4 mục con: Chi tiết các khoản, Theo dõi thanh toán, Lịch sử giao dịch, Thông tin nhận tiền. | **KHỚP CHUẨN** | **Giữ nguyên**, đảm bảo ID điều khiển độc lập (`mob-income-btn`, `mob-income-menu`) và active state mượt mà. |
| **Nhóm Chung** | Về VietTranslate, Tin tức, Thanh toán Escrow. | **KHỚP CHUẨN** | **Giữ nguyên**, đảm bảo nhãn và thứ tự giống desktop. |
| **Các tiện ích chung ở chân drawer** | Tin nhắn, Thông báo, Trợ giúp, Cài đặt & Bảo mật, Đăng xuất. | **BẢO TOÀN THIẾT YẾU** | **Bảo toàn** ở chân mobile drawer để đảm bảo người dùng trên màn hình cảm ứng có thể Đăng xuất, Cài đặt và Hỗ trợ thuận tiện (do avatar dropdown trên mobile không thể dùng hover). |

---

## 4. TỔNG HỢP CÁC FILE DỰ KIẾN THAY ĐỔI
1. **`templates/base.html`**:
   - Tinh chỉnh nhánh `{% elif current_user and current_user.role == 'translator' %}` trong `#mobile-nav`:
     - Xóa liên kết dư "Trang chủ công khai".
     - Thay accordion "Tổng quan" bằng liên kết đơn chuẩn giống desktop sidebar (`side-link`).
     - Sắp xếp lại nhóm "Công việc": `Tìm việc` -> `Việc phù hợp` -> `Thống kê công việc`.
     - Giữ nguyên nhóm "Cá nhân": `Lịch làm việc`, `Thu nhập` (kèm 4 mục con), `Tài khoản`.
     - Giữ nguyên nhóm "Chung": `Về VietTranslate`, `Tin tức`, `Thanh toán Escrow`.
     - Xóa helper JavaScript `toggleMobOverview()` không còn sử dụng để tránh dead code.
2. **`tests/test_pdv_mobile_nav_parity.py`**:
   - Viết test suite kiểm tra tự động đảm bảo:
     - Khớp 100% danh sách mục giữa desktop sidebar và mobile drawer của role translator.
     - Không còn liên kết neo `#section-` dư thừa.
     - Các role khác (hirer, guest, admin) không bị ảnh hưởng.
