# -*- coding: utf-8 -*-
"""جمع‌وجورسازی کارت‌های داشبورد - اجرا: python fix_dash_compact.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'app', 'ui', 'main_window.py')
s = open(mp, encoding='utf-8').read()
n = 0

reps = [
    ('border-radius:8px; padding:12px; min-height:110px; }}',
     'border-radius:8px; padding:6px; min-height:64px; }} QLabel#CardValue {{ font-size:26px; font-weight:bold; }}'),
    ('setMinimumHeight(150)', 'setMinimumHeight(84)'),
    ('setMaximumHeight(200)', 'setMaximumHeight(120)'),
    ('layout.setSpacing(6); layout.setContentsMargins(10, 8, 10, 8)',
     'layout.setSpacing(2); layout.setContentsMargins(8, 4, 8, 4)'),
    ('v = QLabel(value)', 'v = QLabel(value); v.setObjectName("CardValue")'),
    ('cards_layout.setSpacing(16)', 'cards_layout.setSpacing(10)'),
    ('setMaximumHeight(180)', 'setMaximumHeight(150)'),
]
for old, new in reps:
    if old in s:
        s = s.replace(old, new)
        n += 1
print('اعمال شد:', n, 'از', len(reps))
open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)

print('بیلد...')
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
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql', '.py')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn); rel = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel)
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
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('تمام ✔')
print('=== تست 1366x768: داشبورد جمع‌وجور ===')
input('Enter...')