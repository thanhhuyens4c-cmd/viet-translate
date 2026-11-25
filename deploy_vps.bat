@echo off
chcp 65001 >nul
echo ========================================================
echo   KÍCH HOẠT VPS CẬP NHẬT CODE MỚI NHẤT TỪ GITHUB
echo ========================================================
echo Đang gửi yêu cầu triển khai đến VPS 103.161.118.158...

curl.exe -s -X POST http://103.161.118.158/webhook -H "Content-Type: application/json" -d "{\"ref\":\"refs/heads/main\"}"

echo.
echo ========================================================
echo Đã kích hoạt lệnh deploy trên VPS thành công!
echo Website đang được nạp lại tự động mà không bị gián đoạn.
echo Kiểm tra website tại: http://103.161.118.158/
echo ========================================================
pause
