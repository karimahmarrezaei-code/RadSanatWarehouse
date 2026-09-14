# -*- coding: utf-8 -*-
"""بازگردانی theme_manager + ثبت در spec + بیلد - اجرا: python fix_theme_restore.py"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) پیدا کردن theme_manager.py هر جای پروژه
cands = []
for dp, ds, fs in os.walk(ROOT):
    tail = dp.split(os.sep)[-1]
    if any(k in dp for k in ('.venv', '.git', '\\build', '\\dist')):
        continue
    if 'theme_manager.py' in fs:
        cands.append(os.path.join(dp, 'theme_manager.py'))
print('پیدا شد در:', cands)
root_file = os.path.join(ROOT, 'theme_manager.py')
if not os.path.exists(root_file):
    if cands:
        shutil.copy2(cands[0], root_file)
        print('1) بازگردانی شد به ریشه از:', cands[0])
    else:
        print('❌ هیچ نسخه‌ای پیدا نشد؛ از گیت برگردانید: git checkout HEAD~2 -- theme_manager.py')
        input(); raise SystemExit
else:
    print('1) فایل از قبل در ریشه بود ✔')

# 2) ثبت دائمی در spec تا هرگز از بیلد نیفتد
spec = os.path.join(ROOT, 'RadSanatWarehouse.spec')
s = open(spec, encoding='utf-8').read()
if "'theme_manager'" not in s:
    s = s.replace('hiddenimports=[', "hiddenimports=['theme_manager',", 1)
    open(spec, 'w', encoding='utf-8').write(s)
    print('2) theme_manager به hiddenimports spec اضافه شد')
else:
    print('2) از قبل در spec بود ✔')

# 3) بیلد + تزریق + bat
print('3) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق؛ اول: taskkill /f /im RadSanatWarehouse.exe'); input(); raise SystemExit
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
print('3) تمام ✔')
print('=== تست: رزولوشن 1366x768 → run.bat → لاگین + تب تسویهٔ پیش‌فاکتور/سند مالی ===')
input('Enter...')