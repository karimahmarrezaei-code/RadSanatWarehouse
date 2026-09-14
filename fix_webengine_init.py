# -*- coding: utf-8 -*-
"""مقداردهی صحیح وب‌انجین قبل از QApplication - اجرا: python fix_webengine_init.py"""
import os, sys, subprocess, shutil, py_compile, time
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

subprocess.run(['taskkill', '/f', '/im', 'RadSanatWarehouse.exe'], capture_output=True)
time.sleep(2)
print('0) برنامه بسته شد ✔')

mp = os.path.join(ROOT, 'main.py')
lines = open(mp, encoding='utf-8').read().split('\n')
if '# WEBENGINE-INIT-FIX' not in '\n'.join(lines):
    idx = None
    for i, l in enumerate(lines[:60]):
        if l.startswith('import ') or l.startswith('from '):
            idx = i
            break
    if idx is None:
        idx = 0
    block = [
        "# WEBENGINE-INIT-FIX: وب‌انجین باید قبل از QApplication مقداردهی شود",
        "try:  # WEBENGINE-INIT-FIX",
        "    from PyQt5.QtCore import Qt as _Qt_AA  # WEBENGINE-INIT-FIX",
        "    from PyQt5.QtWidgets import QApplication as _QApp_AA  # WEBENGINE-INIT-FIX",
        "    _QApp_AA.setAttribute(_Qt_AA.AA_ShareOpenGLContexts, True)  # WEBENGINE-INIT-FIX",
        "    import PyQt5.QtWebEngineWidgets  # noqa  # WEBENGINE-INIT-FIX",
        "except Exception:  # WEBENGINE-INIT-FIX",
        "    pass  # WEBENGINE-INIT-FIX",
    ]
    lines[idx:idx] = block
    open(mp, 'w', encoding='utf-8').write('\n'.join(lines))
    py_compile.compile(mp, doraise=True)
    print('1) بلوک مقداردهی در بالای main نصب شد ✔')
else:
    print('1) از قبل بود ✔')

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