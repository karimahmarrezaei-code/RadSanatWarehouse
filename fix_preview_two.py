# -*- coding: utf-8 -*-
"""دو ترمیم دقیق پیش‌نمایش - اجرا: python fix_preview_two.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) معافیت دیالوگ‌های دارای QTextBrowser از پیچ اسکرول
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# PREV-SKIP2' not in s:
    anchor = 'def _safe_fit(w):\n'
    if anchor in s:
        s = s.replace(anchor, anchor +
                      "    try:  # PREV-SKIP2\n"
                      "        from PyQt5.QtWidgets import QDialog as _QD, QTextBrowser as _QTB  # PREV-SKIP2\n"
                      "        if isinstance(w, _QD) and w.findChildren(_QTB):  # PREV-SKIP2\n"
                      "            return  # PREV-SKIP2\n"
                      "    except Exception:  # PREV-SKIP2\n"
                      "        pass  # PREV-SKIP2\n", 1)
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('1) معافیت QTextBrowser نصب شد ✔')
else:
    print('1) از قبل بود ✔')

# 2) اگر به دیالوگ مسیر فایل دادند، خودش بخواند
hp = os.path.join(ROOT, 'app', 'ui', 'html_preview_dialog.py')
h = open(hp, encoding='utf-8').read()
if '# PATH-FIX' not in h:
    anchor2 = "        self.html_content = simplify_html(html)\n"
    if anchor2 in h:
        h = h.replace(anchor2,
                      "        try:  # PATH-FIX\n"
                      "            if html and '<' not in html and os.path.exists(html):  # PATH-FIX\n"
                      "                with open(html, encoding='utf-8', errors='replace') as _f:  # PATH-FIX\n"
                      "                    html = _f.read()  # PATH-FIX\n"
                      "        except Exception:  # PATH-FIX\n"
                      "            pass  # PATH-FIX\n" + anchor2, 1)
        open(hp, 'w', encoding='utf-8').write(h)
        py_compile.compile(hp, doraise=True)
        print('2) خواندن مسیر فایل نصب شد ✔')
else:
    print('2) از قبل بود ✔')

# بیلد با محافظ داده
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