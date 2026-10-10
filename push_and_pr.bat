@echo off
setlocal

REM Them Git vao PATH
set PATH=%PATH%;C:\Users\nguye\AppData\Local\Programs\Git\cmd

echo ===========================================
echo   BUOC 1: DAY CODE LEN GITHUB
echo ===========================================
echo.

git push -u origin phuonganh/admin

if %ERRORLEVEL% neq 0 (
    echo.
    echo [LOI] Push that bai! Hay kiem tra lai xac thuc GitHub.
    pause
    exit /b 1
)

echo.
echo ===========================================
echo   BUOC 2: TAO PULL REQUEST
echo ===========================================
echo.
echo Dang mo trang tao Pull Request tren GitHub...
echo.

start "" "https://github.com/thanhhuyens4c-cmd/viet-translate/compare/main...phuonganh/admin?expand=1&title=Hoan+thien+trang+Tong+quan+(Dashboard)+cho+phien+dich+vien&body=%%23%%23+Noi+dung+thay+doi%%0A-+Hoan+thien+toan+bo+7+thanh+phan+tren+Dashboard+Interpreter+(/interpreter/dashboard):%%0A--+1.+Thong+tin+ho+so+va+xac+minh%%0A--+2.+Thong+ke+cong+viec%%0A--+3.+Thong+ke+thu+nhap%%0A--+4.+Ca+lam+sap+toi%%0A--+5.+Viec+lam+de+xuat%%0A--+6.+Viec+can+xu+ly%%0A--+7.+Thong+bao+gan+day%%0A-+Cap+nhat+menu+Sidebar+dieu+huong+va+dong+bo+trang+thai"

echo.
echo ===========================================
echo   HOAN TAT!
echo   Trang Pull Request da mo tren trinh duyet.
echo   Hay kiem tra va nhan "Create pull request".
echo ===========================================
pause
