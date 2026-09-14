# -*- coding: utf-8 -*-
"""همه انتساب‌های physical به منبع واحد - اجرا: python fix_physical_all.py"""
import os, re, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

for rel in ('app/ui/proforma_window.py', 'app/ui/ui/proforma_window.py'):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    lines = [l for l in open(p, encoding='utf-8').read().split('\n') if '# DBG' not in l]
    n = 0
    for i, l in enumerate(lines):
        st = l.lstrip()
        if st.startswith('physical =') and '# ONE-STOCK' not in l:
            ind = len(l) - len(l.lstrip())
            print('   جایگزین شد:', rel, 'خط', i + 1, '->', st[:60])
            lines[i] = ' ' * ind + 'physical = free_stock_map(self.db)  # ONE-STOCK'
            n += 1
    # تضمین import داخل تابع
    if 'from app.core.stock_service import free_stock_map' not in '\n'.join(lines):
        for i, l in enumerate(lines):
            if l.strip().startswith('def _apply_reserved_stocks'):
                ind = len(l) - len(l.lstrip()) + 4
                lines[i + 1:i + 1] = [' ' * ind + 'from app.core.stock_service import free_stock_map  # ONE-STOCK']
                n += 1
                break
    if n:
        open(p, 'w', encoding='utf-8').write('\n'.join(lines))
        py_compile.compile(p, doraise=True)
    print('1)', rel, 'انتساب‌های جایگزین‌شده:', n)

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