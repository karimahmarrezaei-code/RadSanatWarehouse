# -*- coding: utf-8 -*-
"""کوچک‌کردن فونت‌های درون‌ویجتی در حالت فشرده - اجرا: python fix_compact2.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

if '# COMPACT2' not in s:
    anchor = '            for lay in self.findChildren(_QL2):  # COMPACT-UI\n'
    block = (
        "            import re as _re2  # COMPACT2\n"
        "            for w in self.findChildren(_QW):  # COMPACT2\n"
        "                try:  # COMPACT2\n"
        "                    ss = w.styleSheet()  # COMPACT2\n"
        "                    if ss and 'font-size' in ss:  # COMPACT2\n"
        "                        new = _re2.sub(r'font-size:\\s*(\\d+)px', lambda m: f'font-size: {max(10, int(int(m.group(1)) * 0.8))}px', ss)  # COMPACT2\n"
        "                        if new != ss:  # COMPACT2\n"
        "                            w.setStyleSheet(new)  # COMPACT2\n"
        "                except Exception:  # COMPACT2\n"
        "                    pass  # COMPACT2\n"
    )
    if anchor in s:
        s = s.replace(anchor, block + anchor, 1)
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('1) COMPACT2 اضافه شد ✔')
    else:
        print('1) ⚠ anchor پیدا نشد')
else:
    print('1) از قبل بود ✔')

print('2) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('❌ بیلد ناموفق؛ اول: taskkill /f /im RadSanatWarehouse.exe'); input(); raise SystemExit
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