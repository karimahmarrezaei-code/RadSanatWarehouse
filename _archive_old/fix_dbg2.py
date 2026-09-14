# -*- coding: utf-8 -*-
"""شاهد با تورفتگی پویا - اجرا: python fix_dbg2.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

def blk(ind, body):
    sp = ' ' * ind
    sp2 = ' ' * (ind + 4)
    sp3 = ' ' * (ind + 8)
    return [sp + 'try:  # DBG',
            sp2 + body[0],
            sp3 + body[1],
            sp + 'except Exception:  # DBG',
            sp2 + 'pass  # DBG']

for rel in ('app/ui/proforma_window.py', 'app/ui/ui/proforma_window.py'):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    lines = [l for l in open(p, encoding='utf-8').read().split('\n') if '# DBG' not in l]
    n = 0
    for i, l in enumerate(lines):
        if l.strip().startswith('def _apply_reserved_stocks'):
            ind = len(l) - len(l.lstrip()) + 4
            lines[i + 1:i + 1] = blk(ind, ["import sys as _s9, os as _o9  # DBG",
                                           "open(_o9.path.join(_o9.path.dirname(_s9.executable), 'STOCK_DEBUG.txt'), 'a', encoding='utf-8').write('ENTER\\n').close()  # DBG"])
            n += 1
            break
    for i, l in enumerate(lines):
        if 'physical = free_stock_map(self.db)  # ONE-STOCK' in l:
            ind = len(l) - len(l.lstrip())
            lines[i + 1:i + 1] = blk(ind, ["import os as _o9, sys as _s9  # DBG",
                                           "open(_o9.path.join(_o9.path.dirname(_s9.executable), 'STOCK_DEBUG.txt'), 'a', encoding='utf-8').write('physical=' + repr(physical) + '\\n').close()  # DBG"])
            n += 1
            break
    for i, l in enumerate(lines):
        if 'stocks = {pid: max(int(physical.get(pid, 0))' in l:
            ind = len(l) - len(l.lstrip())
            lines[i + 1:i + 1] = blk(ind, ["import os as _o9, sys as _s9  # DBG",
                                           "open(_o9.path.join(_o9.path.dirname(_s9.executable), 'STOCK_DEBUG.txt'), 'a', encoding='utf-8').write('stocks=' + repr(stocks) + '\\n').close()  # DBG"])
            n += 1
            break
    for i, l in enumerate(lines):
        if 'مانده انبار: {:,}' in l:
            ind = len(l) - len(l.lstrip())
            lines[i + 1:i + 1] = blk(ind, ["import os as _o9, sys as _s9  # DBG",
                                           "open(_o9.path.join(_o9.path.dirname(_s9.executable), 'STOCK_DEBUG.txt'), 'a', encoding='utf-8').write('txt=' + repr(txt) + '\\n').close()  # DBG"])
            n += 1
            break
    if n:
        open(p, 'w', encoding='utf-8').write('\n'.join(lines))
        py_compile.compile(p, doraise=True)
    print('1)', rel, 'شاهد:', n)

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