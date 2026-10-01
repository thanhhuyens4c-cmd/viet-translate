@echo off
setlocal
title Dang nhap GitHub va Push code

set PATH=C:\Users\nguye\AppData\Local\Programs\Git\cmd;C:\Users\nguye\AppData\Local\Programs\Git\bin;C:\Users\nguye\AppData\Local\Programs\Git\mingw64\bin;%PATH%

echo =======================================================
echo   DANG NHAP GITHUB VA DAY CODE LEN REPO
echo =======================================================
echo.
echo [1/2] Dang mo trinh duyet de dang nhap GitHub...
echo Vui long bam "Authorize" tren trinh duyet khi duoc yeu cau.
echo.

"C:\Users\nguye\AppData\Local\Programs\Git\mingw64\bin\git-credential-manager.exe" github login --browser

echo.
echo [2/2] Dang day code len nhanh phuonganh/admin...
echo.

git push -u origin phuonganh/admin

if %ERRORLEVEL% neq 0 (
    echo.
    echo [THONG BAO] Push truc tiep khong thanh cong.
    echo Neu ban khong co quyen ghi (write permission) vao repo goc,
    echo ban can Fork repo ve tai khoan cua minh truoc.
    echo.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo   DAY CODE THANH CONG! Dang mo Pull Request...
echo =======================================================
echo.

start "" "https://github.com/thanhhuyens4c-cmd/viet-translate/compare/main...phuonganh/admin?expand=1&title=Them+tinh+nang+upload+anh+trong+chat&body=Them+tinh+nang+upload+anh+trong+chat+giua+phien+dich+vien+va+khach+thue"

echo Hoan tat! Ban co the dong cua so nay.
pause
