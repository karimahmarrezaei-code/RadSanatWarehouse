# -*- coding: utf-8 -*-
"""spec خودش data را بسته‌بندی می‌کند - اجرا: python fix_spec_data.py"""
import os, sys, subprocess, shutil
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

spec = os.path.join(ROOT, 'RadSanatWarehouse.spec')
s = open(spec, encoding='utf-8').read()
if '_DATA_FILES' not in s:
    header = ("import os as _os  # DATA-SELF\n"
              "_DATA_FILES = [(_os.path.join('data', f), 'data') for f in _os.listdir('data') "
              "if f.endswith(('.sql', '.json', '.key'))]  # DATA-SELF\n")
    i = s.find('datas=')
    if i == -1:
        print('❌ datas= پیدا نشد'); input(); raise SystemExit
    # درج header قبل از اولین بخش Analysis
    j = s.find('Analysis(')
    s = s[:j] + header + s[j:]
    s = s.replace('datas=', 'datas=_DATA_FILES + ', 1)
    open(spec, 'w', encoding='utf-8').write(s)
    print('1) spec خودکفا شد ✔')
else:
    print('1) از قبل بود ✔')

print('2) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق؛ اول: taskkill /f /im RadSanatWarehouse.exe'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
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
print('2) تمام ✔')
input('Enter...')