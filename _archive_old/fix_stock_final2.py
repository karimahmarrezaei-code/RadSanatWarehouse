# -*- coding: utf-8 -*-
"""پچ خط‌محور فرمول موجودی - اجرا: python fix_stock_final2.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) فرمول داخل تابع منبع (هر دو فرم)
for rel in ('app/ui/issue_manager_window.py', 'app/ui/receipt_manager_window.py'):
    p = os.path.join(ROOT, rel)
    s = open(p, encoding='utf-8').read()
    if '# STOCK-FORMULA' in s:
        print('1)', rel, 'از قبل بود ✔'); continue
    lines = s.split('\n')
    done = False
    for i, l in enumerate(lines):
        if 'return int(r[0] or 0) if r else 0' in l and any('inventory_levels' in lines[k] for k in range(max(0, i - 5), i)):
            ind = len(l) - len(l.lstrip())
            sp = ' ' * ind
            block = [
                sp + "base = int(r[0] or 0) if r else 0  # STOCK-FORMULA",
                sp + "try:  # STOCK-FORMULA",
                sp + "    r2 = conn.execute(\"SELECT SUM(oli.qty) FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id WHERE oli.pallet_id=? AND ol.load_status='OPEN' AND ol.is_active=1\", (pallet_id,)).fetchone()  # STOCK-FORMULA",
                sp + "    base -= int(r2[0] or 0) if r2 and r2[0] else 0  # STOCK-FORMULA",
                sp + "except Exception:  # STOCK-FORMULA",
                sp + "    pass  # STOCK-FORMULA",
                sp + "return base  # STOCK-FORMULA",
            ]
            lines[i:i + 1] = block
            done = True
            break
    if done:
        open(p, 'w', encoding='utf-8').write('\n'.join(lines))
        py_compile.compile(p, doraise=True)
        print('1)', rel, '✔')
    else:
        print('1)', rel, '⚠ خط پیدا نشد')

# 2) رسید: مانده از تابع منبع
p = os.path.join(ROOT, 'app/ui/receipt_manager_window.py')
lines = open(p, encoding='utf-8').read().split('\n')
done = False
for i, l in enumerate(lines):
    if "_s = int(getattr(self, 'pallet_stock'" in l:
        ind = len(l) - len(l.lstrip())
        lines[i] = ' ' * ind + "_s = int(self._stock_for_warehouse(p['id'], (self.warehouse_combo.currentData() if getattr(self, 'warehouse_combo', None) is not None else None)))  # STOCK-FORMULA"
        done = True
        break
if done:
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    py_compile.compile(p, doraise=True)
    print('2) رسید از منبع می‌خواند ✔')
else:
    print('2) ⚠ خط _s پیدا نشد')

# 3) بیلد با محافظ داده
db_dist = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
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
if os.path.exists(keep):
    os.makedirs(os.path.join(DST, '_internal', 'data'), exist_ok=True)
    shutil.copy2(keep, db_dist)
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')