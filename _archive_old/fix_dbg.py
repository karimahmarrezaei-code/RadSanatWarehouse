# -*- coding: utf-8 -*-
"""کاشت شاهد زمان اجرا - اجرا: python fix_dbg.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

DBG_ENTER = [
    "        try:  # DBG",
    "            import sys as _s9, os as _o9  # DBG",
    "            _dbg = _o9.path.join(_o9.path.dirname(_s9.executable), 'STOCK_DEBUG.txt')  # DBG",
    "            with open(_dbg, 'a', encoding='utf-8') as _f9:  # DBG",
    "                _f9.write('ENTER\\n')  # DBG",
    "        except Exception:  # DBG",
    "            pass  # DBG",
]

def write_block(var):
    return [
        "        try:  # DBG",
        f"            with open(_dbg, 'a', encoding='utf-8') as _f9:  # DBG",
        f"                _f9.write('{var}=' + repr({var}) + '\\n')  # DBG",
        "        except Exception:  # DBG",
        "            pass  # DBG",
    ]

for rel in ('app/ui/proforma_window.py', 'app/ui/ui/proforma_window.py'):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    lines = open(p, encoding='utf-8').read().split('\n')
    if any('# DBG' in l for l in lines):
        print('1)', rel, 'از قبل داشت ✔'); continue
    n = 0
    for i, l in enumerate(lines):
        if l.strip().startswith('def _apply_reserved_stocks'):
            lines[i + 1:i + 1] = DBG_ENTER
            n += 1
            break
    for i, l in enumerate(lines):
        if 'physical = free_stock_map(self.db)  # ONE-STOCK' in l:
            lines[i + 1:i + 1] = write_block('physical')
            n += 1
            break
    for i, l in enumerate(lines):
        if 'stocks = {pid: max(int(physical.get(pid, 0))' in l:
            lines[i + 1:i + 1] = write_block('stocks')
            n += 1
            break
    for i, l in enumerate(lines):
        if 'مانده انبار: {:,}' in l:
            lines[i + 1:i + 1] = write_block('txt')
            n += 1
            break
    if n:
        open(p, 'w', encoding='utf-8').write('\n'.join(lines))
        py_compile.compile(p, doraise=True)
    print('1)', rel, 'شاهد:', n)

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