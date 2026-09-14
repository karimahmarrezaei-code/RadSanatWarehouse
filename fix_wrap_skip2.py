# -*- coding: utf-8 -*-
"""taskkill داخلی + معافیت پیچ - اجرا: python fix_wrap_skip2.py"""
import os, sys, subprocess, shutil, py_compile, time
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 0) بستن برنامه قبل از هر کاری
subprocess.run(['taskkill', '/f', '/im', 'RadSanatWarehouse.exe'],
               capture_output=True)
time.sleep(2)
print('0) برنامه بسته شد ✔')

mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# WRAP-SKIP' not in s:
    anchor = 'def _safe_fit(w):\n'
    if anchor in s:
        s = s.replace(anchor, anchor +
                      "    try:  # WRAP-SKIP\n"
                      "        from PyQt5.QtWebEngineWidgets import QWebEngineView as _QWV  # WRAP-SKIP\n"
                      "        if w.findChildren(_QWV):  # WRAP-SKIP\n"
                      "            return  # WRAP-SKIP\n"
                      "    except Exception:  # WRAP-SKIP\n"
                      "        pass  # WRAP-SKIP\n"
                      "    try:  # WRAP-SKIP\n"
                      "        from PyQt5.QtWidgets import QDialog as _QD2, QTextBrowser as _QTB2  # WRAP-SKIP\n"
                      "        if isinstance(w, _QD2) and w.findChildren(_QTB2):  # WRAP-SKIP\n"
                      "            return  # WRAP-SKIP\n"
                      "    except Exception:  # WRAP-SKIP\n"
                      "        pass  # WRAP-SKIP\n", 1)
        open(mp, 'w', encoding='utf-8').write(s)
        print('1) معافیت نصب شد ✔')
else:
    print('1) معافیت از قبل بود ✔')
py_compile.compile(mp, doraise=True)

# بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
print('2) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('❌ بیلد ناموفق'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
dst_app = os.path.join(DST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql', '.py')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn); rel2 = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel2)
            os.makedirs(os.path.dirname(tgt), exist_ok=True); shutil.copy2(src, tgt)
if os.path.exists(keep):
    os.makedirs(os.path.join(DST, '_internal', 'data'), exist_ok=True)
    shutil.copy2(keep, db)
    print('2) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('3) تمام ✔')
input('Enter...')