# -*- coding: utf-8 -*-
"""ترمیم spec و بیلد خودکفا - اجرا: python fix_spec_repair.py"""
import os, re, sys, subprocess, shutil
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) بازگردانی spec سالم از گیت
subprocess.run(['git', 'checkout', '--', 'RadSanatWarehouse.spec'])
spec = os.path.join(ROOT, 'RadSanatWarehouse.spec')
s = open(spec, encoding='utf-8').read()
print('1) spec از گیت برگشت ✔')

# 2) درج امن: قبل از کلِ خطِ  x = Analysis(
if '_DATA_FILES' not in s:
    header = ("import os as _os  # DATA-SELF\n"
              "_DATA_FILES = [(_os.path.join('data', f), 'data') for f in _os.listdir('data') "
              "if f.endswith(('.sql', '.json', '.key'))]  # DATA-SELF\n")
    m = re.search(r'(?m)^[A-Za-z_]\w*\s*=\s*Analysis\(', s)
    if not m:
        print('❌ خط Analysis پیدا نشد'); input(); raise SystemExit
    s = s[:m.start()] + header + s[m.start():]
    s = s.replace('datas=', 'datas=_DATA_FILES + ', 1)
    open(spec, 'w', encoding='utf-8').write(s)
    # نمایش محل درج برای اطمینان
    lines = s.split('\n')
    for i, l in enumerate(lines):
        if '_DATA_FILES' in l or 'Analysis(' in l:
            print(f'{i+1:4} {l[:90]}')
    print('2) درج امن انجام شد ✔')
else:
    print('2) از قبل بود ✔')

# 3) بیلد + تزریق
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
print('3) تمام ✔')
input('Enter...')