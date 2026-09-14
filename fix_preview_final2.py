# -*- coding: utf-8 -*-
"""دو ترمیم نهایی پیش‌نمایش - اجرا: python fix_preview_final2.py"""
import os, sys, subprocess, shutil, py_compile, time
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

subprocess.run(['taskkill', '/f', '/im', 'RadSanatWarehouse.exe'], capture_output=True)
time.sleep(2)
print('0) برنامه بسته شد ✔')

# 1) معافیت دیالوگ‌ها در _safe_show
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# SHOW-SKIP' not in s:
    anchor = 'def _safe_show('
    i = s.find(anchor)
    if i != -1:
        j = s.find('\n', i) + 1
        s = s[:j] + ("    try:  # SHOW-SKIP\n"
                     "        from PyQt5.QtWidgets import QDialog as _QD3  # SHOW-SKIP\n"
                     "        if isinstance(w, _QD3):  # SHOW-SKIP\n"
                     "            w.show()  # SHOW-SKIP\n"
                     "            return  # SHOW-SKIP\n"
                     "    except Exception:  # SHOW-SKIP\n"
                     "        pass  # SHOW-SKIP\n") + s[j:]
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('1) معافیت _safe_show نصب شد ✔')
    else:
        print('1) ⚠ _safe_show پیدا نشد')
else:
    print('1) از قبل بود ✔')

# 2) ساده‌سازی ملایم: بدون تراشیدن استایل‌ها
hp = os.path.join(ROOT, 'app', 'ui', 'html_preview_dialog.py')
h = open(hp, encoding='utf-8').read()
if '# LIGHT-FIX' not in h:
    old = "        self.html_content = simplify_html(html)\n"
    if old in h:
        h = h.replace(old,
                      "        try:  # LIGHT-FIX\n"
                      "            if html and '<' not in html and os.path.exists(html):  # LIGHT-FIX\n"
                      "                with open(html, encoding='utf-8', errors='replace') as _f:  # LIGHT-FIX\n"
                      "                    html = _f.read()  # LIGHT-FIX\n"
                      "        except Exception:  # LIGHT-FIX\n"
                      "            pass  # LIGHT-FIX\n"
                      "        import re as _re  # LIGHT-FIX\n"
                      "        _h = html or ''  # LIGHT-FIX\n"
                      "        _h = _re.sub(r'<table(?![^>]*\\bborder\\b)([^>]*)>', r'<table border=\"1\" cellspacing=\"0\" cellpadding=\"5\" width=\"100%\"\\1>', _h, flags=_re.I)  # LIGHT-FIX\n"
                      "        self.html_content = _h  # LIGHT-FIX\n", 1)
        open(hp, 'w', encoding='utf-8').write(h)
        py_compile.compile(hp, doraise=True)
        print('2) ساده‌سازی ملایم نصب شد ✔')
    else:
        print('2) ⚠ خط هدف پیدا نشد')
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