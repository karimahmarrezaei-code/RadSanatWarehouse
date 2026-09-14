# -*- coding: utf-8 -*-
"""کسر رزرو در منبعِ موجودی + چاپ وضعیت داده - اجرا: python fix_stock_source.py"""
import os, sys, subprocess, shutil, py_compile, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 0) شفاف‌سازی داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
if os.path.exists(db):
    con = sqlite3.connect(db)
    print('=== پالت‌ها ===')
    for r in con.execute("SELECT id, code, name FROM pallets").fetchall():
        print('   ', r)
    print('=== بارگیری‌های باز ===')
    try:
        for r in con.execute("SELECT id, reference_no, load_status, remaining_qty FROM outbound_loads").fetchall():
            print('   ', r)
        for r in con.execute("SELECT pallet_id, SUM(qty) FROM outbound_load_items GROUP BY pallet_id").fetchall():
            print('    اقلام بارگیری:', r)
    except Exception as e:
        print('   ', e)
    con.close()

# 1) حذف کسرِ تکراری از _pallet_options
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
old_t = "                            out.append((d, (it[1] or 0) - rsv.get(d.get('id'), 0)) + tuple(it[2:]))\n"
if old_t in s:
    s = s.replace(old_t, "                            out.append((d, it[1]) + tuple(it[2:]))\n", 1)
    print('1) کسر تکراری حذف شد ✔')

# 2) کسر رزرو داخل منبعِ _stock_for_warehouse
if '# SW-WRAP' not in s:
    anchor = '        w._pallet_options = po\n'
    block = (
        "        if callable(getattr(w, '_stock_for_warehouse', None)):  # SW-WRAP\n"
        "            o3 = w._stock_for_warehouse  # SW-WRAP\n"
        "            def sw(pid, wh=None, _o=o3, _w=w):  # SW-WRAP\n"
        "                v = _o(pid, wh)  # SW-WRAP\n"
        "                try:  # SW-WRAP\n"
        "                    v = (v or 0) - _reserved_map(_w.db).get(pid, 0)  # SW-WRAP\n"
        "                except Exception:  # SW-WRAP\n"
        "                    pass  # SW-WRAP\n"
        "                return v  # SW-WRAP\n"
        "            w._stock_for_warehouse = sw  # SW-WRAP\n"
    )
    if anchor in s:
        s = s.replace(anchor, anchor + block, 1)
        print('2) SW-WRAP نصب شد ✔')
open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)

# 3) بیلد با محافظ داده
db_dist = db
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