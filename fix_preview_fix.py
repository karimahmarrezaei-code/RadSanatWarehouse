# -*- coding: utf-8 -*-
"""پیش‌نمایش بدون پیچ + پرچم‌های وب‌انجین - اجرا: python fix_preview_fix.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

# 1) پرچم‌های کرومیوم قبل از هر چیزی
if 'QTWEBENGINE_CHROMIUM_FLAGS' not in s:
    anchor = 'from PyQt5.QtCore import Qt\n'
    if anchor in s:
        s = s.replace(anchor, anchor +
                      "os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--no-sandbox --disable-gpu --single-process --disable-software-rasterizer')  # PREV-FIX\n"
                      "os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX', '1')  # PREV-FIX\n", 1)
        print('1) پرچم‌ها ست شد ✔')

# 2) رد کردن پنجره‌های وب‌انجین از پیچ اسکرول
if '# PREV-FIX' not in s.split('QTWEBENGINE_CHROMIUM_FLAGS')[-1] or 'QWebEngineView as _QWV' not in s:
    anchor2 = 'def _safe_fit(w):\n'
    if anchor2 in s and 'QWebEngineView as _QWV' not in s:
        s = s.replace(anchor2, anchor2 +
                      "    try:  # PREV-FIX\n"
                      "        from PyQt5.QtWebEngineWidgets import QWebEngineView as _QWV  # PREV-FIX\n"
                      "        if w.findChildren(_QWV):  # PREV-FIX\n"
                      "            return  # PREV-FIX\n"
                      "    except Exception:  # PREV-FIX\n"
                      "        pass  # PREV-FIX\n", 1)
        print('2) وب‌انجین از پیچ معاف شد ✔')
open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)

# 3) بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
print('3) بیلد...')
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
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')