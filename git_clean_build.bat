@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo.
echo == 1) پاک‌سازی داربست‌ها ==
del /q print_*.py 2>nul
del /q fix_*.py 2>nul
del /q diag_*.py 2>nul
del /q *.bak* 2>nul
del /s /q app\*.bak* 2>nul
echo پاک‌سازی انجام شد

echo.
echo == 2) ثبت در گیت ==
git add -A
git commit -m "پرداخت پرسنل با حساب و سند مالی + اصلاح نقدینگی + ابزارهای کامل لپ‌تاپ"

echo.
echo == 3) بیلد نهایی ==
python build_exe.py

echo.
echo == تمام! خروجی: dist\warehouse_app ==
pause