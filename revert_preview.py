# -*- coding: utf-8 -*-
"""بازگردانی کامل ماژول پیش‌نمایش از گیت - اجرا: python revert_preview.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) بازگردانی html_preview_dialog.py از گیت (نسخهٔ سالمِ اصلی)
for rel in ('app/ui/html_preview_dialog.py', 'app/ui/ui/html_preview_dialog.py',
            'app/ui/webengine_preview.py', 'app/ui/ui/webengine_preview.py'):
    p = os.path.join(ROOT, rel)
    g = subprocess.run(['git', 'show', f'HEAD:{rel.replace(os.sep, "/")}'],
                       capture_output=True)
    if g.returncode == 0 and g.stdout:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(g.stdout)
        try:
            py_compile.compile(p, doraise=True)
            print('1)', rel, 'بازگردانی از گیت ✔')
        except Exception as e:
            print('1)', rel, '⚠', e)
    elif os.path.exists(p) and 'ui/ui/' in rel:
        # پاک کردن نسخه سایه
        os.remove(p)
        print('1)', rel, 'پاک شد (سایه) ✔')

# 2) پاکسازی main.py از پچ‌های پرچم وب‌انجین
mp = os.path.join(ROOT, 'main.py')
s = open(mp, encoding='utf-8').read()
for marker in ('QTWEBENGINE_CHROMIUM_FLAGS', 'QWebEngineView as _QWV'):
    s = '\n'.join(l for l in s.split('\n') if marker not in l)
open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)
print('2) main.py پاک شد ✔')

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