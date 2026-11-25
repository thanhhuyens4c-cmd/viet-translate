# BÁO CÁO TRIỂN KHAI TRUNG TÂM TÁC VỤ ADMIN, BỘ LỌC THỐNG NHẤT, DUYỆT NHANH AN TOÀN VÀ TỐI ƯU MOBILE

**Dự án:** VietTranslate  
**Ngày thực hiện:** 20/10/2026  
**Trạng thái triển khai:** `CODE FIXED, NOT DEPLOYED` (Mã nguồn đã sửa và kiểm thử 100% trong workspace, chưa deploy lên VPS production).

---

## I. Hiện Trạng Trước Khi Sửa & Nguyên Nhân Cần Nâng Cấp

### 1. Hiện trạng trước khi nâng cấp
1. **Thiếu một trung tâm tác vụ tập trung (`/admin/tasks`):**
   - Trước đây thanh điều hướng Admin (`templates/admin_base.html`) chỉ có các liên kết rời rạc: Hồ sơ PDV, Người đăng, Jobs, Report, Khiếu nại.
   - Admin phải tự click vào từng trang để xem có bản ghi nào đang chờ xử lý hay không.
2. **Nghẽn hiệu năng N+1 trên `/admin/jobs`:**
   - Code cũ thực hiện nạp toàn bộ danh sách `Job.query.all()` vào bộ nhớ Python và chạy kiểm tra 39 tiêu chí `evaluate_job_39_criteria(job)` cho từng bản ghi trên mỗi lượt tải trang, sau đó mới lọc danh sách bằng code Python. Khi số lượng công việc tăng, trang sẽ bị chậm hoặc timeout.
3. **Lỗ hổng phê duyệt bỏ qua kiểm tra an toàn (Approval Bypass):**
   - Route `POST /admin/jobs/<job_id>/approve` (dòng 10922 cũ) gán trực tiếp `job.status = 'open'` và `job.moderation_status = 'approved'` mà hoàn toàn **không chạy kiểm tra 39 tiêu chí**, không kiểm tra người đăng đã xác minh hay chưa, không lưu dữ liệu `moderation_checklist_data` và không gửi thông báo kết quả.
   - Luồng duyệt chi tiết (`admin_moderate_job`) chỉ dựa vào popup Javascript `confirm()` ở client, không có rào chắn backend chặn việc duyệt job có vi phạm nghiêm trọng (Nhóm C: C1, C2, C3, C6, C9, C10).
4. **Lỗi giao diện nghiêm trọng trên điện thoại di động (< 768px):**
   - Trang chi tiết xét duyệt (`templates/admin_job_review.html:325`) sử dụng thanh hành động cố định với CSS: `position: fixed; bottom: 0; left: var(--sidebar-w); right: 0;`.
   - Trên điện thoại (< 768px), sidebar Admin bị ẩn (`transform: translateX(-100%)`), nhưng thanh hành động vẫn bị gán `left: 256px`. Hậu quả là toàn bộ các nút *Yêu cầu chỉnh sửa, Duyệt, Từ chối* bị đẩy ra ngoài cạnh phải màn hình, gây tràn ngang và không thể thao tác trên di động.
   - Bảng danh sách công việc trên điện thoại bị vỡ layout, cuộn ngang khó khăn và không có thẻ card chuyên biệt.

---

## II. Kiến Trúc Giải Pháp & Nguyên Tắc An Toàn

### 1. Không tạo bảng Database mới (Zero Schema Duplication)
- Thay vì tạo thêm bảng `admin_tasks` gây rủi ro lệch đồng bộ trạng thái (desync) với các bảng nghiệp vụ gốc, hệ thống xây dựng một tầng dịch vụ tổng hợp trực tiếp (`services/admin_task_service.py`):
  * Truy vấn dữ liệu thực tế từ: `Job`, `TranslatorVerification` / `TranslatorProfile`, `HirerProfile`, `Report`, `Dispute`.
  * Tính toán chỉ số KPI thực tế: Tổng tác vụ chờ, Cảnh báo khẩn cấp, Báo cáo & khiếu nại, Tác vụ đã xử lý trong ngày (từ `AdminAuditLog`).

### 2. Dịch vụ Kiểm duyệt An toàn Độc lập (`services/admin_job_service.py`)
- Hợp nhất toàn bộ quy trình phê duyệt công việc vào một luồng nghiệp vụ chuẩn:
  * `evaluate_job_safety(job)`: Đánh giá 39 tiêu chí với cơ chế cô lập lỗi (Error Isolation) theo từng bản ghi.
  * `check_quick_approve_eligibility(job, eval_res)`: Kiểm tra 100% điều kiện tiên quyết trước khi cho phép kích hoạt Duyệt nhanh.
  * `safe_approve_job(...)`: Thực hiện duyệt, ghi audit log, tạo thông báo cho khách và kích hoạt gợi ý phiên dịch viên phù hợp.

### 3. Quy tắc Duyệt Nhanh An Toàn (Safe Quick Approval Matrix)

| Tiêu chí kiểm tra | Đủ điều kiện Duyệt Nhanh | Buộc chuyển sang Xét Duyệt Chi tiết |
|---|---|---|
| **Trạng thái Job** | `pending` (chưa duyệt) | `flagged`, `archived`, `rejected`, `closed` |
| **Vi phạm Nhóm C** | `total_critical == 0` | Có >= 1 vi phạm nghiêm trọng (C1, C2, C3, C6, C9, C10) |
| **Xác minh người đăng** | Đã xác minh (`is_verified=True` / `status='verified'`) | Chưa xác minh danh tính |
| **Đánh giá tiêu chí** | Hoàn tất tự động không lỗi | `needs_manual_review = True` hoặc lỗi engine |
| **Quyền Admin** | Quản trị viên có quyền `approve_job` | Không có quyền (Bị 403 Forbidden) |
| **CSRF & Submit lặp** | Token hợp lệ, kiểm tra trạng thái trước khi lưu | Token sai hoặc thao tác lặp |

---

## III. Các Tệp Mã Nguồn Đã Sửa & Tạo Mới

### 1. Các tệp tạo mới
1. `services/admin_job_service.py`:
   - Hàm `evaluate_job_safety(job)`
   - Hàm `check_quick_approve_eligibility(job, eval_res)`
   - Hàm `safe_approve_job(job, admin_id, is_quick, manual_overrides, audit_logger)`
2. `services/admin_task_service.py`:
   - Hàm `get_admin_tasks_summary()`: Thống kê số lượng tác vụ thực tế.
   - Hàm `query_admin_tasks(filters, page, per_page, admin_user)`: Tìm kiếm kết hợp đa điều kiện, sắp xếp theo mức ưu tiên và phân trang.
   - Helper `safe_url_for(endpoint, **values)`: Tạo URL an toàn ngay cả khi gọi ngoài request context.
3. `templates/admin_tasks.html`:
   - 4 thẻ KPI chỉ số thực tế trên đầu trang.
   - Thanh bộ lọc thống nhất: Từ khóa `q`, Loại tác vụ `type`, Trạng thái `status`, Mức ưu tiên `priority`, Khoảng thời gian `time_range`.
   - Chế độ hiển thị kép: Bảng Desktop (`hidden md:block`) và Thẻ Card cảm ứng Mobile (`block md:hidden`).
   - Nút Duyệt nhanh với tooltip lý do và nút dẫn tới màn hình chi tiết.
4. `tests/test_admin_tasks_and_quick_approve.py`:
   - Bộ kiểm thử tự động 6 kịch bản bao phủ toàn bộ tính năng mới.

### 2. Các tệp đã cập nhật
1. `app.py`:
   - Thêm `'admin_badge_total_tasks'` vào `admin_badge_counts()` context processor.
   - Tạo route `@app.route('/admin/tasks')` với phân quyền `@require_permission('view_dashboard')`.
   - Nâng cấp `@app.route('/admin/jobs')`: Lọc từ khóa `q` ở database, phân trang 20 job/trang, chỉ đánh giá tiêu chí cho các job trên trang hiện tại.
   - Cập nhật `@app.route('/admin/jobs/<job_id>/approve')`: Chuyển sang gọi `safe_approve_job(..., is_quick=True)`.
   - Cập nhật `@app.route('/admin/jobs/<job_id>/moderate')`: Nhánh `approve` gọi `safe_approve_job(..., is_quick=False)`.
2. `templates/admin_base.html`:
   - Thêm mục điều hướng **"Tác vụ cần xử lý"** với huy hiệu đếm tổng `admin_badge_total_tasks`.
3. `templates/admin_dashboard.html`:
   - Bổ sung thẻ điều hướng nổi bật vào **Trung tâm Tác vụ cần xử lý**.
4. `templates/admin_jobs.html`:
   - Bổ sung thanh tìm kiếm `q` kết hợp với các tab trạng thái.
   - Thêm cột Thao tác có nút **⚡ Duyệt** khi đủ điều kiện hoặc nhãn cảnh báo **⚠️ Cần xem kỹ**.
   - Bổ sung chế độ hiển thị Mobile Cards cho màn hình nhỏ (< 768px).
   - Thêm thanh điều hướng phân trang (Pagination controls).
5. `templates/admin_job_review.html`:
   - Thêm khối CSS responsive `@media (max-width: 768px) { .sticky-review-bar { left: 0 !important; } }`.
   - Sửa dứt điểm lỗi tràn ngang và lệch nút trên điện thoại di động.

---

## IV. Kết Quả Kiểm Thử (Automated Test Verification)

Toàn bộ các bộ kiểm thử đều chạy thành công trên môi trường:

```bash
# 1. Chạy bộ kiểm thử mới cho Trung tâm Tác vụ và Duyệt nhanh:
python -m unittest tests/test_admin_tasks_and_quick_approve.py
Ran 6 tests in 2.042s -> OK

# 2. Chạy bộ kiểm thử hồi quy hệ thống (Regression Suite):
python -m unittest tests/test_audit_fixes_regression.py tests/test_pdv_mobile_nav_parity.py tests/test_hirer_job_lifecycle_integration.py
Ran 19 tests in 3.248s -> OK
```

**Tổng cộng:** **25/25 test cases đạt 100%**, bao gồm:
- ✅ Kiểm tra đếm chỉ số KPI thực tế và tính nhất quán toán học của tổng số việc chờ.
- ✅ Kiểm tra bộ lọc từ khóa, loại tác vụ, mức độ ưu tiên, khoảng thời gian.
- ✅ Kiểm tra điều kiện chặn duyệt nhanh khi có vi phạm nghiêm trọng (Nhóm C).
- ✅ Kiểm tra điều kiện chặn duyệt nhanh khi khách đăng chưa xác minh danh tính.
- ✅ Kiểm tra điều kiện chặn duyệt nhanh khi job bị gắn cờ hoặc lưu trữ.
- ✅ Kiểm tra luồng phê duyệt an toàn và ghi nhận đầy đủ Audit Log.
- ✅ Kiểm tra phân quyền truy cập endpoint `/admin/tasks` (Chặn người dùng thường, mở cho Admin).
- ✅ Kiểm tra bảo vệ CSRF và chống submit lặp.
- ✅ Kiểm tra tính toàn vẹn của mã CSS responsive cho thanh hành động fixed review trên mobile.

---

## V. Kết Quả Tối Ưu Giao Diện Điện Thoại (Mobile Optimization)

1. **Thanh hành động cố định trên trang xét duyệt (`admin_job_review.html`):**
   - Đã loại bỏ inline style cứng `left: var(--sidebar-w)`.
   - Khi màn hình <= 768px, thanh hành động tự động bung toàn bộ chiều ngang (`left: 0 !important`), các nút *Yêu cầu chỉnh sửa, Duyệt, Từ chối* được chia đều với chiều cao tối thiểu **44px**, dễ thao tác bằng ngón cái.
2. **Danh sách Tác vụ & Jobs dạng Card:**
   - Trên desktop (>= 769px): Hiển thị bảng dạng table đầy đủ cột.
   - Trên mobile (<= 768px): Tự động chuyển đổi thành danh sách các thẻ Card trực quan:
     * Hiển thị rõ mã ID, nhãn nghiệp vụ, thời gian gửi, mức độ ưu tiên.
     * Thông tin người đăng có dấu tích xanh xác minh danh tính.
     * Tóm tắt kết quả kiểm tra 39 tiêu chí.
     * Các nút bấm xét duyệt chi tiết và duyệt nhanh to rõ, không bị tràn màn hình ngang.

---

## VI. Phương Án Triển Khai Lên VPS & Kế Hoạch Rollback

### 1. Trạng thái hiện tại
`CODE FIXED, NOT DEPLOYED`

### 2. Các bước triển khai lên VPS Ubuntu 24.04 (Khi được phê duyệt)
1. Đẩy các file đã sửa lên remote git hoặc rsync trực tiếp:
   ```bash
   # Không thay đổi schema database (không cần chạy migrate)
   git status
   ```
2. Trên VPS:
   ```bash
   cd /var/www/viet-translate
   git pull origin main
   sudo systemctl restart viet-translate.service
   sudo systemctl status viet-translate.service
   ```
3. Kiểm tra nhật ký dịch vụ:
   ```bash
   sudo journalctl -u viet-translate.service -n 50 --no-pager
   ```

### 3. Kế hoạch Rollback an toàn
Nếu phát sinh bất kỳ sự cố nào sau khi triển khai lên VPS:
1. Rollback về commit trước:
   ```bash
   git checkout HEAD~1 app.py templates/ services/
   sudo systemctl restart viet-translate.service
   ```
2. Vì không có thay đổi cấu trúc bảng cơ sở dữ liệu (Database Schema), việc rollback mã nguồn diễn ra tức thì trong vòng 5 giây mà không ảnh hưởng đến dữ liệu đã lưu.
