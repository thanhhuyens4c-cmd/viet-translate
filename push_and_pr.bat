@echo off
echo ==============================================
echo   Push code module Thu nhap len GitHub & Tao PR
echo ==============================================
git status
git add app.py services/payout_methods.py templates/base.html templates/income_*.html scratch/*.py
git commit -m "feat(income): hoan thien module thu nhap cho phien dich vien (5 muc con)"
git push origin phuonganh/admin
echo.
echo Dang mo trinh duyet de tao Pull Request vao main...
start "" "https://github.com/thanhhuyens4c-cmd/viet-translate/compare/main...phuonganh/admin?expand=1"
echo Da hoan tat!
pause
