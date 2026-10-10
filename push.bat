@echo off
setlocal
echo ===========================================
echo       DANG DAY CODE LEN GITHUB
echo ===========================================

set /p msg="Nhap ghi chu cho lan sua nay (Enter de dung mac dinh 'Update code'): "
if "%msg%"=="" set msg=Update code

echo.
echo 1. Dang gom cac file thay doi...
git add .

echo 2. Dang luu commit: "%msg%"...
git commit -m "%msg%"

echo 3. Dang day len nhanh phuonganh/admin tren GitHub...
git push -u origin phuonganh/admin

echo.
echo ===========================================
echo       HOAN TAT!
echo ===========================================
pause
