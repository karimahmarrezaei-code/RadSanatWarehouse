# -*- coding: utf-8 -*-
"""رفع سایه app/ui/ui - اجرا: python fix_dup.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) سند: کدام ماژول import می‌شود
mw = os.path.join(ROOT, 'app', 'ui', 'main_window.py')
for i, l in enumerate(open(mw, encoding='utf-8', errors='replace').read().split('\n')):
    if 'proforma' in l and ('import' in l or 'from' in l):
        print(f'   main_window {i+1}: {l.strip()[:100]}')
    if ('receipt_manager' in l or 'issue_manager' in l) and ('import' in l or 'from' in l):
        print(f'   main_window {i+1}: {l.strip()[:100]}')

# 2) کپی روی نسخه سایه
pairs = [
    ('app/ui/proforma_window.py', 'app/ui/ui/proforma_window.py'),
    ('app/ui/issue_manager_window.py', 'app/ui/ui/issue_manager_window.py'),
    ('app/ui/receipt_manager_window.py', 'app/ui/ui/receipt_manager_window.py'),
]
for a, b in pairs:
    sa = os.path.join(ROOT, a); sb = os.path.join(ROOT, b)
    if os.path.exists(sa) and os.path.isdir(os.path.dirname(sb)):
        shutil.copy2(sa, sb)
        py_compile.compile(sb, doraise=True)
        print('2) کپی سایه:', b, '✔')

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
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.png')) and ('icon' in fn.lower() or 'rad_sanat' in fn.lower()):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, fn))
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, '_internal', fn))
good = os.path.join(ROOT, 'theme_manager.py')
if os.path.exists(good):
    for tgt in (os.path.join(DST, 'theme_manager.py'),
                os.path.join(DST, '_internal', 'theme_manager.py'),
                os.path.join(DST, '_internal', 'app', 'styles', 'theme_manager.py')):
        if os.path.isdir(os.path.dirname(tgt)):
            shutil.copy2(good, tgt)
if os.path.exists(keep):
    os.makedirs(os.path.join(DST, '_internal', 'data'), exist_ok=True)
    shutil.copy2(keep, db)
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')