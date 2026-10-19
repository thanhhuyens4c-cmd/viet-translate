# BÁO CÁO KIỂM TOÁN VÀ ĐÁNH GIÁ TRẠNG THÁI JOB (ADMIN_JOB_STATUS_AUDIT.md)
**Dự án:** VietTranslate (Nền tảng kết nối Phiên dịch viên & Khách hàng)  
**Ngày thực hiện:** 20/10/2026  
**Trạng thái:** HOÀN THÀNH AUDIT — CHUẨN BỊ TRIỂN KHAI CODE  

---

## I. TỔNG QUAN VÀ MỤC ĐÍCH KIỂM TOÁN
Kiểm toán toàn diện vòng đời công việc (Job Lifecycle) và quy trình kiểm duyệt (Job Moderation) trên hệ thống VietTranslate nhằm:
1. Giải quyết triệt để sự mâu thuẫn giữa hai chiều trạng thái: **Trạng thái kiểm duyệt** (`moderation_status`) và **Vòng đời công việc** (`status`).
2. Bảo đảm bài đăng đã được Admin duyệt hợp lệ sẽ rời khỏi hàng chờ "Chờ duyệt" và xuất hiện chính xác tại danh sách "Đang hoạt động".
3. **Ngăn chặn tuyệt đối rủi ro Admin vô tình "hồi sinh" các job đã bị Người thuê (Hirer) gỡ, đóng hoặc hủy tuyển dụng.**
4. Chuẩn hóa bộ lọc Admin, trang hiển thị công khai cho phiên dịch viên (`/jobs`), API gợi ý việc làm (`/api/jobs/recommended`), và trang quản lý của khách (`/my-jobs`).
5. Bảo toàn 100% dữ liệu lịch sử, báo giá (Proposals), hợp đồng (Contracts) và kiểm toán (Audit Logs) — không xóa cứng dữ liệu.

---

## II. SƠ ĐỒ WORKFLOW VÀ KIẾN TRÚC TRẠNG THÁI HIỆN TẠI

### 1. Hai chiều trạng thái trong Schema `models.py`
Model `Job` (dòng 669–740 trong `models.py`) sở hữu các trường cốt lõi:
- `status`: `VARCHAR(20)`, mặc định trong model là `'open'`. Biểu diễn **vòng đời công việc**:
  - `'pending'`: Chờ duyệt hoặc đang chỉnh sửa bổ sung.
  - `'open'`: Đang mở tuyển công khai, chấp nhận báo giá.
  - `'closed'`: Người thuê đóng nhận báo giá.
  - `'cancelled'`: Người thuê hủy yêu cầu tuyển dụng.
  - `'contracted'`: Đã chốt hợp đồng với phiên dịch viên.
  - `'in_progress'`: Đang trong tiến độ dịch thuật / sự kiện.
  - `'completed'`: Đã hoàn tất công việc và nghiệm thu.
  - `'archived'`: Đã lưu trữ an toàn.
- `moderation_status`: `VARCHAR(20)`, mặc định là `'pending'`. Biểu diễn **kết quả kiểm duyệt nội dung**:
  - `'pending'`: Đang chờ Admin xem xét.
  - `'approved'`: Admin đã phê duyệt đạt chuẩn.
  - `'needs_revision'`: Admin yêu cầu sửa đổi nội dung.
  - `'rejected'`: Admin từ chối duyệt bài đăng.
  - `'flagged'`: Bị gắn cờ vi phạm (tự động hoặc thủ công).
  - `'archived'`: Đã đưa vào lưu trữ kiểm duyệt.
- `closed_at`: `DateTime`, ghi nhận chính xác thời điểm đóng / gỡ công việc.
- `is_flagged`: `Boolean`, cờ chặn hiển thị khẩn cấp khi phát hiện vi phạm.
- `moderated_at`, `moderated_by`, `moderation_notes`, `moderation_checklist_data`: Lưu trữ nhật ký quyết định và kết quả quét 39 tiêu chí.

### 2. Các điểm đọc / ghi trạng thái trong hệ thống
| Route / Service | Tác vụ | Trường ghi nhận | Hành vi thực tế |
|---|---|---|---|
| `app.py:post_job` -> `_submit_for_moderation` | Hirer đăng job mới | `job.status = 'pending'`, `job.moderation_status = 'pending'` | Đưa vào hàng chờ duyệt, chạy 39 tiêu chí |
| `app.py:edit_job` -> `_submit_for_moderation` | Hirer sửa job | `job.status = 'pending'`, `job.moderation_status = 'pending'` | Chuyển lại về hàng chờ duyệt (version mới) |
| `app.py:_change_job_status` (action='close') | Hirer đóng nhận báo giá | `job.status = 'closed'`, `job.closed_at = datetime.utcnow()` | Đóng tuyển dụng, giữ nguyên `moderation_status` |
| `app.py:_change_job_status` (action='cancel') | Hirer hủy job | `job.status = 'cancelled'`, `job.closed_at = datetime.utcnow()`, `job.moderation_status = 'archived'` | Hủy bài đăng, tự động từ chối proposal pending |
| `services/admin_job_service.py:safe_approve_job` | Admin duyệt nhanh / chi tiết | `job.moderation_status = 'approved'`, `job.status = 'open'`, `job.is_flagged = False` | **RỦI RO CAO**: Ghi đè `status='open'` bất kể job đã bị Hirer đóng (`closed_at != None`) |
| `app.py:admin_moderate_job` (needs_revision) | Admin yêu cầu sửa | `job.moderation_status = 'needs_revision'`, `job.status = 'pending'` | Giữ ở hàng chờ cần sửa |
| `app.py:admin_moderate_job` (reject) | Admin từ chối | `job.moderation_status = 'rejected'`, `job.status = 'closed'` | Đóng job vĩnh viễn |
| `app.py:admin_flag_job` | Admin gắn cờ / khôi phục | `job.is_flagged = True/False`, `job.moderation_status = 'flagged'/'approved'` | Tạm ẩn / mở lại |
| `services/booking.py` | Tạo hợp đồng | `job.status = 'contracted'` | Chuyển sang trạng thái đã chốt phiên dịch viên |
| `services/projects.py` | Hoàn thành dự án | `job.status = 'completed'` | Chuyển sang trạng thái hoàn tất |

---

## III. NGUYÊN NHÂN CÁC TRẠNG THÁI KHÔNG NHẤT QUÁN & RỦI RO NGHIỆP VỤ

### 1. Ba rủi ro nghiêm trọng được xác nhận qua kiểm toán mã nguồn
1. **Mâu thuẫn trạng thái và hiển thị sai trên giao diện Admin:**
   - Trong `app.py:admin_jobs`, tab "Đã duyệt" (`status='open'`) lọc bằng điều kiện:
     ```python
     query.filter(db.or_(Job.moderation_status == 'approved', Job.status == 'open'))
     ```
   - Trong `templates/admin_jobs.html`, badge hiển thị:
     ```jinja2
     {% elif job.moderation_status == 'approved' or job.status == 'open' %}
     <span class="badge badge-blue">Đã duyệt</span>
     ```
   - **Hậu quả:** Một job có `status='open'` nhưng `moderation_status='pending'` vẫn bị gắn nhãn "Đã duyệt" và hiển thị trong tab đã duyệt, làm Admin tưởng lầm bài đăng đã thông qua.
2. **Duyệt bài làm "hồi sinh" job đã bị người thuê gỡ/đóng:**
   - Khi Hirer bấm đóng job (`/my-jobs/<id>/close`), hệ thống gán `job.status = 'closed'` và `job.closed_at = now`.
   - Nhưng trong `services/admin_job_service.py:safe_approve_job`, khi Admin thực hiện phê duyệt, hàm tự động gán:
     ```python
     job.status = 'open'
     ```
   - `safe_approve_job` **hoàn toàn không kiểm tra `job.closed_at` hoặc việc Hirer đã đóng/hủy bài**. Nếu Admin duyệt muộn hoặc mở lại màn hình, job đã đóng lập tức bị mở lại công khai trái ý muốn của khách.
3. **Job đã đóng/hủy nhưng vẫn sót lại trong hàng chờ "Chờ duyệt":**
   - Bộ lọc tab "Chờ duyệt" trong `app.py:admin_jobs` và `services/admin_task_service.py` chỉ kiểm tra:
     ```python
     db.or_(Job.moderation_status == 'pending', db.and_(Job.status == 'pending', Job.moderation_status.is_(None)))
     ```
   - Bộ lọc **không loại trừ `job.status == 'closed'` hoặc `job.closed_at is not None`**.
   - **Hậu quả:** Nếu Hirer đóng bài khi job đang ở trạng thái pending, job đó vẫn tiếp tục nằm trong hàng chờ "Chờ duyệt" của Admin, gây lãng phí thời gian và nhầm lẫn thao tác.

---

## IV. KIỂM TOÁN DỮ LIỆU THỰC TẾ TRÊN DATABASE (LOCAL AUDIT)
Thực hiện truy vấn kiểm tra toàn bộ 179 bản ghi Job hiện có trong cơ sở dữ liệu:
```
Tổng số jobs: 179
- status='open', mod='approved', flagged=False, has_closed_at=False: 101 jobs (Hợp lệ, đang hoạt động)
- status='pending', mod='pending', flagged=False, has_closed_at=False: 46 jobs (Hợp lệ, đang chờ duyệt)
- status='open', mod='pending', flagged=False, has_closed_at=False: 14 jobs (BẤT THƯỜNG: status open nhưng chưa duyệt!)
- status='open', mod='flagged', flagged=True, has_closed_at=False: 1 job (Đang bị gắn cờ)
- status='contracted', mod='pending', flagged=False, has_closed_at=False: 17 jobs (Đã chốt hợp đồng từ trước)
```
*Nhận xét:* 14 bản ghi có `status='open'` nhưng `moderation_status='pending'` phát sinh do các lệnh tạo bản ghi trực tiếp tận dụng default column `status='open'` của SQLAlchemy thay vì đi qua luồng `_submit_for_moderation`.

---

## V. THIẾT KẾ ĐẶC TẢ STATE MACHINE CHUẨN HÓA

### 1. Nguyên tắc tách biệt hai chiều
1. **Quyết định kiểm duyệt (`moderation_status`)**: Phản ánh nội dung bài đăng có tuân thủ quy định hay không (`pending`, `approved`, `needs_revision`, `rejected`, `flagged`, `archived`).
2. **Vòng đời tuyển dụng (`status`, `closed_at`)**: Phản ánh nhu cầu tuyển dụng thực tế của khách thuê (`pending`, `open`, `closed`, `cancelled`, `contracted`, `in_progress`, `completed`, `archived`).
3. **Quy tắc bất khả xâm phạm:** Quyết định phê duyệt của Admin **chỉ cập nhật kết quả kiểm duyệt**; nó **không được phép ghi đè ý định gỡ/đóng công việc của người thuê**.

### 2. Ma trận chuyển trạng thái chuẩn hóa
| Trạng thái trước thao tác | Hành động / Sự kiện | Trạng thái sau thao tác | Xuất hiện "Chờ duyệt"? | Xuất hiện "Đang hoạt động"? |
|---|---|---|---|---|
| Chờ duyệt (`pending`), chưa gỡ | Admin duyệt thành công | `moderation_status='approved'`, `status='open'` | **Không** | **Có** (đủ điều kiện) |
| Chờ duyệt (`pending`), **đã gỡ/đóng** | Admin duyệt thành công | `moderation_status='approved'`, `status='closed'`, giữ nguyên `closed_at` | **Không** | **Không** (không mở lại) |
| Chờ duyệt (`pending`) | Admin yêu cầu sửa | `moderation_status='needs_revision'`, `status='pending'` | Không (vào nhóm Cần sửa) | Không |
| Chờ duyệt (`pending`) | Admin từ chối | `moderation_status='rejected'`, `status='closed'` | **Không** | **Không** |
| Chờ duyệt (`pending`) | Khách thuê gỡ/đóng bài | `status='closed'`, `closed_at=now` | **Không** (rời hàng chờ ngay) | **Không** |
| Đang hoạt động (`open` & `approved`) | Khách thuê gỡ/đóng bài | `status='closed'`, `closed_at=now` | Không | **Không** (rời danh sách ngay) |
| Đang hoạt động | Job bị gắn cờ vi phạm | `is_flagged=True`, `moderation_status='flagged'` | Không vào pending thường; vào hàng chờ Flagged | **Không** (tạm ẩn ngay) |
| Bất kỳ | Đã chốt hợp đồng / hoàn tất | `status='contracted'` / `'completed'` | Không | Không |

---

## VI. CÁC ĐIỂM CẦN SỬA ĐỔI TRONG MÃ NGUỒN
1. **`services/admin_job_service.py`**:
   - `check_quick_approve_eligibility`: Chặn duyệt nhanh nếu `job.closed_at is not None` hoặc `job.status in ('closed', 'cancelled', 'contracted', 'completed', 'archived')`.
   - `safe_approve_job`:
     * Kiểm tra trạng thái vòng đời mới nhất từ database.
     * Nếu job đã bị đóng/gỡ (`closed_at is not None` hoặc `status in ('closed', 'cancelled')`): Ghi nhận `moderation_status = 'approved'`, nhưng **giữ nguyên `status = 'closed'`/`'cancelled'`**, không đổi sang `'open'`, không phát thông báo job mở công khai.
     * Chỉ kích hoạt `job.status = 'open'` khi job đang ở trạng thái hợp lệ (`status == 'pending'` hoặc chưa bị đóng).
2. **`app.py`**:
   - Route `admin_jobs`:
     * Tab "Chờ duyệt" (`pending`): Chỉ lấy job `moderation_status == 'pending'`, `is_flagged == False`, và **bắt buộc `status != 'closed'`, `status != 'cancelled'`, `closed_at.is_(None)`**.
     * Đổi tab "Đã duyệt" thành **"Đang hoạt động"** (`open` hoặc `active`): Bắt buộc thỏa mãn đồng thời: `moderation_status == 'approved'`, `status == 'open'`, `closed_at.is_(None)`, `is_flagged == False`.
     * Bổ sung tab **"Đã đóng / Ngừng HĐ"** (`closed`): Lấy các job `status in ('closed', 'cancelled')` hoặc `closed_at.isnot(None)` để Admin tiện tra cứu lịch sử.
   - Route `job_list`, `api_recommended_jobs`: Bổ sung điều kiện `Job.closed_at.is_(None)` và `Job.moderation_status == 'approved'` đồng nhất.
3. **`services/admin_task_service.py`**:
   - Đồng bộ điều kiện tính `pending_jobs_count` và truy vấn task job để loại trừ các job đã bị đóng/gỡ khỏi hàng chờ duyệt.
4. **`templates/admin_jobs.html`**:
   - Đổi nhãn tab "Đã duyệt" thành "Đang hoạt động", thêm tab "Đã đóng".
   - Sửa hiển thị badge trạng thái tại bảng desktop và mobile: Không gán nhãn "Đã duyệt" khi `moderation_status == 'pending'` dù `status == 'open'`.

---

## VII. ĐÁNH GIÁ RỦI RO HỒI QUY VÀ KẾ HOẠCH BẢO ĐẢM AN TOÀN
- **Tính tương thích:** Không thay đổi cấu trúc bảng database (schema giữ nguyên), sử dụng trọn vẹn các trường có sẵn (`status`, `moderation_status`, `closed_at`, `is_flagged`).
- **Bảo toàn dữ liệu:** Không xóa bất kỳ bản ghi Job, Proposal, Contract hay Audit Log nào.
- **Kiểm thử hồi quy:** Viết bộ kiểm thử chuyên biệt `tests/test_job_status_moderation_lifecycle.py` xác minh đầy đủ các kịch bản chuyển đổi trạng thái và xử lý đồng thời trước khi hoàn tất task.
