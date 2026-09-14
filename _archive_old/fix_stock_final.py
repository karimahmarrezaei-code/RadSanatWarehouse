# -*- coding: utf-8 -*-
"""فرمول موجودی داخل تابع منبع - اجرا: python fix_stock_final.py"""
import os, re, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

NEW = (r'\1'
       r'\2base = int(r[0] or 0) if r else 0  # STOCK-FORMULA\n'
       r'\2try:  # STOCK-FORMULA\n'
       r'\2    r2 = conn.execute("SELECT SUM(oli.qty) FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id WHERE oli.pallet_id=? AND ol.load_status=\'OPEN\' AND ol.is_active=1", (pallet_id,)).fetchone()  # STOCK-FORMULA\n'
       r'\2    base -= int(r2[0] or 0) if r2 and r2[0] else 0  # STOCK-FORMULA\n'
       r'\2except Exception:  # STOCK-FORMULA\n'
       r'\2    pass  # STOCK-FORMULA\n'
       r'\2return base  # STOCK-FORMULA')

for rel in ('app/ui/issue_manager_window.py', 'app/ui/receipt_manager_window.py'):
    p = os.path.join(ROOT, rel)
    s = open(p, encoding='utf-8').read()
    if '# STOCK-FORMULA' not in s:
        pat = re.compile(r'(inventory_levels WHERE pallet_id=\? AND warehouse_id=\?"[^\n]*\n[^\n]*fetchone\(\)\n)([ \t]*)return int\(r\[0\] or 0\) if r else 0')
        s2, n = pat.subn(NEW, s, count=1)
        if n:
            open(p, 'w', encoding='utf-8').write(s2)
            py_compile.compile(p, doraise=True)
            print('1)', rel, '✔')
        else:
            print('1)', rel, '⚠ الگو پیدا نشد')
    else:
        print('1)', rel, 'از قبل بود ✔')

# 2) رسید: مانده را از همان تابع منبع بخوان
p = os.path.join(ROOT, 'app/ui/receipt_manager_window.py')
s = open(p, encoding='utf-8').read()
old_s = "_s = int(getattr(self, 'pallet_stock', {}).get(p['id'], 0) or 0)"
new_s = "_s = int(self._stock_for_warehouse(p['id'], (self.warehouse_combo.currentData() if getattr(self, 'warehouse_combo', None) is not None else None)))"
if old_s in s:
    s = s.replace(old_s, new_s)
    open(p, 'w', encoding='utf-8').write(s)
    py_compile.compile(p, doraise=True)
    print('2) رسید از منبع می‌خواند ✔')

# 3) حذف کسرهای تکراری از main (منبع حالا خودش می‌کاهد)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
i = s.find('        if callable(getattr(w, \'_stock_for_warehouse\', None)):  # SW-WRAP\n')
if i != -1:
    j = s.find('            w._stock_for_warehouse = sw  # SW-WRAP\n')
    if j != -1:
        j += len('            w._stock_for_warehouse = sw  # SW-WRAP\n')
        s = s[:i] + s[j:]
        print('3) SW-WRAP حذف شد ✔')
old_track = ("                    try:  # STOCK-TRACK\n"
             "                        rsv = _reserved_map(self.db)  # STOCK-TRACK\n"
             "                        stk = getattr(self, 'pallet_stock', None)  # STOCK-TRACK\n"
             "                        if isinstance(stk, dict):  # STOCK-TRACK\n"
             "                            for kk in list(stk.keys()):  # STOCK-TRACK\n"
             "                                stk[kk] = (stk[kk] or 0) - rsv.get(kk, 0)  # STOCK-TRACK\n"
             "                        pst = getattr(ps, 'pallet_stock', None)  # STOCK-TRACK\n"
             "                        if isinstance(pst, dict):  # STOCK-TRACK\n"
             "                            for kk in list(pst.keys()):  # STOCK-TRACK\n"
             "                                pst[kk] = (pst[kk] or 0) - rsv.get(kk, 0)  # STOCK-TRACK\n"
             "                    except Exception:  # STOCK-TRACK\n"
             "                        pass  # STOCK-TRACK\n")
if old_track in s:
    s = s.replace(old_track, '')
    print('3) STOCK-TRACK حذف شد ✔')
open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)

# 4) بیلد با محافظ داده
db_dist = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
print('4) بیلد...')
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
    print('4) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('5) تمام ✔')
input('Enter...')