# BÁO CÁO CHUYỂN ĐỔI DỮ LIỆU PHƯƠNG THỨC NHẬN TIỀN (PAYOUT METHODS MIGRATION)

## 1. Bối cảnh & Lý do Chuyển đổi
Trước đây, module `services/payout_methods.py` quản lý thông tin tài khoản ngân hàng thụ hưởng của phiên dịch viên thông qua một file JSON cục bộ (`instance/interpreter_payout_methods.json`) và khóa tiến trình `threading.Lock()`:
- `threading.Lock()` chỉ có hiệu lực bên trong một single process. Khi chạy Gunicorn multi-workers trên VPS production, các worker ghi file đồng thời có nguy cơ làm corrupt tệp JSON hoặc mất đồng bộ trạng thái (race conditions).
- File JSON cục bộ không được hưởng lợi từ cơ chế sao lưu định kỳ của hệ quản trị cơ sở dữ liệu (`pg_dump`).
- Không có ràng buộc toàn vẹn dữ liệu (Foreign Key) trỏ tới bảng `user.id`.

**Mục tiêu giải pháp:**
- Thiết kế hai bảng quan hệ chuẩn trong PostgreSQL: `payout_methods` và `payout_histories`.
- Ràng buộc khóa ngoại: `user_id` liên kết với `user.id` kèm `ON DELETE CASCADE`.
- Đảm bảo giao dịch ACID: Khi thêm, sửa, đổi mặc định hoặc xóa phương thức, các thao tác được commit an toàn trong transaction.
- Bảo mật thông tin tài chính: Số tài khoản luôn được che (`masked_account_number`) khi trả ra UI; không ghi số tài khoản vào log hệ thống.
- Viết script migration `migrations/migrate_payout_to_db.py` có tính idempotent (chạy nhiều lần không gây trùng lặp).

---

## 2. Thiết kế Schema Database (PostgreSQL)

### Bảng `payout_methods`
```sql
CREATE TABLE IF NOT EXISTS payout_methods (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    bank_code VARCHAR(20) NOT NULL,
    bank_short_name VARCHAR(50) NOT NULL,
    bank_name VARCHAR(200) NOT NULL,
    account_number VARCHAR(50) NOT NULL,
    masked_account_number VARCHAR(50) NOT NULL,
    account_holder_name VARCHAR(100) NOT NULL,
    branch VARCHAR(120) DEFAULT '',
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    status_label VARCHAR(100) NOT NULL DEFAULT 'Khai báo hợp lệ · Đang hoạt động',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE INDEX IF NOT EXISTS ix_payout_methods_user_id ON payout_methods(user_id);
```

### Bảng `payout_histories`
```sql
CREATE TABLE IF NOT EXISTS payout_histories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    method_id VARCHAR(36),
    action VARCHAR(50) NOT NULL,
    bank VARCHAR(50),
    masked_account VARCHAR(50),
    summary VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE INDEX IF NOT EXISTS ix_payout_histories_user_id ON payout_histories(user_id);
```

---

## 3. Bản đồ Chuyển đổi (Mapping Schema JSON -> PostgreSQL)

| Thuộc tính trong JSON cũ | Cột trong bảng `payout_methods` | Kiểu dữ liệu | Ghi chú chuyển đổi |
| :--- | :--- | :--- | :--- |
| `id` | `id` | `VARCHAR(36)` | Giữ nguyên mã chuỗi `pm_xxxxxxxxxxxx` |
| `[user_id]` (key cha) | `user_id` | `INTEGER` | Ép kiểu `int(user_id)` và kiểm tra `User.query.get(user_id)` |
| `bank_code` | `bank_code` | `VARCHAR(20)` | Viết in hoa chuẩn ISO / mã NHVN |
| `bank_short_name` | `bank_short_name` | `VARCHAR(50)` | Tên viết tắt ngân hàng |
| `bank_name` | `bank_name` | `VARCHAR(200)` | Tên pháp nhân đầy đủ |
| `account_number` | `account_number` | `VARCHAR(50)` | Giữ nguyên chuỗi số tài khoản |
| `masked_account_number` | `masked_account_number` | `VARCHAR(50)` | Che chuỗi: `•••• •••• •••• xxxx` |
| `account_holder_name` | `account_holder_name` | `VARCHAR(100)` | Chuẩn hóa in hoa không dấu cách thừa |
| `branch` | `branch` | `VARCHAR(120)` | Chi nhánh phát hành thẻ |
| `is_default` | `is_default` | `BOOLEAN` | Cờ tài khoản mặc định |
| `status` | `status` | `VARCHAR(20)` | Trạng thái (active) |
| `status_label` | `status_label` | `VARCHAR(100)` | Nhãn hiển thị giao diện |
| `created_at` | `created_at` | `TIMESTAMP` | Parse từ ISO format hoặc datetime hiện tại |
| `updated_at` | `updated_at` | `TIMESTAMP` | Parse từ ISO format hoặc datetime hiện tại |

---

## 4. Quy trình Thực thi Migration & Kiểm tra Idempotent

Script thực thi: `python migrations/migrate_payout_to_db.py`
1. **Kiểm tra bảng:** Tự động tạo bảng nếu chưa có.
2. **Kiểm tra tệp JSON:** Nếu tệp `instance/interpreter_payout_methods.json` không tồn tại (trường hợp DB mới hoặc VPS mới), hệ thống bỏ qua bước import và báo sẵn sàng.
3. **Idempotency:** Kiểm tra `PayoutMethod.query.get(method_id)`. Nếu bản ghi đã tồn tại, tự động bỏ qua để tránh trùng lặp.
4. **Bảo toàn tệp gốc:** Tệp JSON được giữ nguyên làm bản backup offline; tuyệt đối không tự động xóa sau khi chuyển đổi.

---

## 5. Phương án Phục hồi & Rollback (Nếu cần)

1. Nếu cần rollback về lưu trữ tệp:
   - Dữ liệu tệp `interpreter_payout_methods.json` gốc vẫn còn nguyên vẹn.
   - Code `services/payout_methods.py` được thiết kế có fallback mode (`_read_data`, `_write_data`), có thể chuyển đổi linh hoạt.
2. Nếu cần sao lưu dữ liệu ngân hàng mới tạo từ PostgreSQL ra JSON:
   - Có thể truy vấn `PayoutMethod.query.all()` và serialize ngược lại format dictionary của JSON bất kỳ lúc nào.
