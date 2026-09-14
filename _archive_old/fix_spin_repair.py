# -*- coding: utf-8 -*-
"""تعمیر اسپین‌های پالت - اجرا: python fix_spin_repair.py"""
import os, re, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
p = os.path.join(ROOT, 'app', 'ui', 'pallets_window.py')
s = open(p, encoding='utf-8').read()

# 1) حذف setRange تکراری و درست‌کردن نامِ بدون self
pat = re.compile(r'self\.(\w+) = QSpinBox\(\); \1\.setRange\((\d+), (\d+)\); self\.\1\.setRange\(\d+, \d+\)')
s, n1 = pat.subn(lambda m: f'self.{m.group(1)} = QSpinBox(); self.{m.group(1)}.setRange({m.group(2)}, {m.group(3)})', s)

# 2) ایمنی: هر setRange با نامِ برهنه از این اسپین‌ها → self. بگیرد
pat2 = re.compile(r'(?<![\w.])(length_spin|width_spin|height_spin|opening_stock_spin|low_stock_spin)\.setRange')
s, n2 = pat2.subn(lambda m: f'self.{m.group(1)}.setRange', s)

open(p, 'w', encoding='utf-8').write(s)
py_compile.compile(p, doraise=True)
print('تعمیر شد:', n1, n2)

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
print('=== تست: 1366x768 → run.bat → پالت با ابعاد 120x100x150 ===')
input('Enter...')