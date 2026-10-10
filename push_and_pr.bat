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

start "" "https://github.com/thanhhuyens4c-cmd/viet-translate/compare/main...phuonganh/admin?expand=1&title=Th%%C3%%AAm+t%%C3%%ADnh+n%%C4%%83ng+upload+%%E1%%BA%%A3nh+trong+chat&body=%%23%%23+T%%C3%%ADnh+n%%C4%%83ng+m%%E1%%BB%%9Bi%%0A-+Th%%C3%%AAm+n%%C3%%BAt+upload+%%E1%%BA%%A3nh+trong+chat%%0A-+Preview+%%E1%%BA%%A3nh+tr%%C6%%B0%%E1%%BB%%9Bc+khi+g%%E1%%BB%%ADi%%0A-+H%%E1%%BB%%97+tr%%E1%%BB%%A3+drag+%%26+drop+v%%C3%%A0+paste+t%%E1%%BB%%AB+clipboard%%0A-+Lightbox+xem+%%E1%%BA%%A3nh+full-screen%%0A-+%%C3%%81p+d%%E1%%BB%%A5ng+cho+c%%E1%%BA%%A3+Direct+Chat+v%%C3%%A0+Contract+Chat"

echo.
echo ===========================================
echo   HOAN TAT!
echo   Trang Pull Request da mo tren trinh duyet.
echo   Hay kiem tra va nhan "Create pull request".
echo ===========================================
pause
