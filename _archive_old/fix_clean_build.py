# -*- coding: utf-8 -*-
"""بیلد تمیز بدون کش - اجرا: python fix_clean_build.py"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 0) اطمینان از حضور theme_manager در ریشه
tm = os.path.join(ROOT, 'theme_manager.py')
print('0) theme_manager در ریشه:', os.path.exists(tm))
if not os.path.exists(tm):
    print('❌ اول آن را از _archive_old کپی کنید'); input(); raise SystemExit

# 1) حذف کش بیلد
cache = os.path.join(ROOT, 'build', 'RadSanatWarehouse')
if os.path.isdir(cache):
    shutil.rmtree(cache, ignore_errors=True)
    print('1) کش build حذف شد')

# 2) بیلد تمیز (این‌بار باید ~2 دقیقه طول بکشد = کامل)
print('2) بیلد تمیز...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec',
                    '--noconfirm', '--clean'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق'); input(); raise SystemExit

# 3) تزریق + bat
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
idata = os.path.join(DST, '_internal', 'data'); os.makedirs(idata, exist_ok=True)
for fn in os.listdir(os.path.join(ROOT, 'data')):
    if fn.endswith(('.sql', '.json', '.key')):
        shutil.copy2(os.path.join(ROOT, 'data', fn), os.path.join(idata, fn))
db = os.path.join(idata, 'app.db')
if os.path.exists(db): os.remove(db)
dst_app = os.path.join(DST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn); rel = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True); shutil.copy2(src, tgt)
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.png')) and ('icon' in fn.lower() or 'rad_sanat' in fn.lower()):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, fn))
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, '_internal', fn))
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
sc = ('@echo off\r\nset "d=%~dp0"\r\npowershell -NoProfile -Command "'
      "$w=New-Object -ComObject WScript.Shell;"
      "$s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\RadSanatWarehouse.lnk');"
      "$s.TargetPath='%d%run.bat';$s.WorkingDirectory='%d%';"
      "$s.IconLocation='%d%RadSanatWarehouse.exe,0';"
      '$s.Save()"'
      '\r\necho Shortcut created\r\npause\r\n')
with open(os.path.join(DST, 'make_shortcut.bat'), 'w') as f:
    f.write(sc)
print('3) تزریق و bat تمام ✔')
print('=== تست: 1366x768 → run.bat → لاگین + تب تسویه ===')
input('Enter...')