# -*- coding: utf-8 -*-
"""کسر خروج‌ها در همه خواندن‌های موجودی - اجرا: python fix_stock_full.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) فرم‌ها: کسر خروج‌های ثبت‌شده قبل از return
R3 = [
    "try:  # STOCK-ISSUED",
    "    r3 = conn.execute(\"SELECT COALESCE(SUM(wii.qty),0) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wii.pallet_id=? AND wi.issue_status!='CANCELLED'\", (pallet_id,)).fetchone()  # STOCK-ISSUED",
    "    base -= int(r3[0] or 0)  # STOCK-ISSUED",
    "except Exception:  # STOCK-ISSUED",
    "    pass  # STOCK-ISSUED",
]
for rel in ('app/ui/issue_manager_window.py', 'app/ui/receipt_manager_window.py'):
    p = os.path.join(ROOT, rel)
    lines = open(p, encoding='utf-8').read().split('\n')
    n = 0
    for i, l in enumerate(lines):
        if 'return base  # STOCK-FORMULA' in l and '# STOCK-ISSUED' not in lines[i - 1]:
            ind = len(l) - len(l.lstrip())
            ins = [' ' * ind + x for x in R3]
            lines[i:i] = ins
            n += 1
            break
    if n:
        open(p, 'w', encoding='utf-8').write('\n'.join(lines))
        py_compile.compile(p, doraise=True)
    print('1)', rel, ':', n)

# 2) main: دیکشنری‌های سرویس هم همان فرمول
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# STOCK-FULL' not in s:
    anchor = '                    ps.reload()\n'
    block = (
        "                    try:  # STOCK-FULL\n"
        "                        with self.db.connect() as _cn6:  # STOCK-FULL\n"
        "                            _cn6.row_factory = None  # STOCK-FULL\n"
        "                            iss = {r0[0]: int(r0[1] or 0) for r0 in _cn6.execute(\"SELECT wii.pallet_id, SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.issue_status!='CANCELLED' GROUP BY wii.pallet_id\").fetchall()}  # STOCK-FULL\n"
        "                            rsv = {r1[0]: int(r1[1] or 0) for r1 in _cn6.execute(\"SELECT oli.pallet_id, SUM(oli.qty - COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=ol.id AND wi.issue_status!='CANCELLED' AND wii.pallet_id=oli.pallet_id),0)) FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id WHERE ol.load_status='OPEN' AND ol.is_active=1 GROUP BY oli.pallet_id\").fetchall()}  # STOCK-FULL\n"
        "                        for _d6 in (getattr(self, 'pallet_stock', None), getattr(ps, 'pallet_stock', None)):  # STOCK-FULL\n"
        "                            if isinstance(_d6, dict):  # STOCK-FULL\n"
        "                                for _k6 in list(_d6.keys()):  # STOCK-FULL\n"
        "                                    _d6[_k6] = (_d6[_k6] or 0) - iss.get(_k6, 0) - rsv.get(_k6, 0)  # STOCK-FULL\n"
        "                    except Exception:  # STOCK-FULL\n"
        "                        pass  # STOCK-FULL\n"
    )
    if anchor in s:
        s = s.replace(anchor, anchor + block, 1)
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('2) STOCK-FULL نصب شد ✔')
else:
    print('2) از قبل بود ✔')

# 3) بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
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
            src = os.path.join(dp, fn); rel2 = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel2)
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
    shutil.copy2(keep, db)
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')