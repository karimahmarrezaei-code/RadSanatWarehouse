# -*- coding: utf-8 -*-
"""منبع واحد موجودی: app/core/stock_service.py - اجرا: python fix_one_stock.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) ماژول جدید
os.makedirs(os.path.join(ROOT, 'app', 'core'), exist_ok=True)
sp = os.path.join(ROOT, 'app', 'core', 'stock_service.py')
open(sp, 'w', encoding='utf-8').write('''# -*- coding: utf-8 -*-
"""منبع واحد موجودی آزاد پالت - ONE-STOCK"""


def free_stock_map(db):
    try:
        with db.connect() as cn:
            cn.row_factory = None
            phys = {r[0]: int(r[1] or 0) for r in cn.execute(
                "SELECT pallet_id, COALESCE(SUM(quantity),0) FROM inventory_levels GROUP BY pallet_id").fetchall()}
            iss = {r[0]: int(r[1] or 0) for r in cn.execute(
                "SELECT wii.pallet_id, SUM(wii.qty) FROM warehouse_issue_items wii "
                "JOIN warehouse_issues wi ON wi.id=wii.issue_id "
                "WHERE wi.issue_status!='CANCELLED' GROUP BY wii.pallet_id").fetchall()}
            rsv = {r[0]: int(r[1] or 0) for r in cn.execute(
                "SELECT oli.pallet_id, SUM(oli.qty - COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii "
                "JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=ol.id "
                "AND wi.issue_status!='CANCELLED' AND wii.pallet_id=oli.pallet_id),0)) "
                "FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id "
                "WHERE ol.load_status='OPEN' AND ol.is_active=1 GROUP BY oli.pallet_id").fetchall()}
        return {pid: max(phys.get(pid, 0) - iss.get(pid, 0) - rsv.get(pid, 0), 0) for pid in phys}
    except Exception:
        return {}


def free_stock(db, pallet_id):
    return int(free_stock_map(db).get(pallet_id, 0) or 0)
''')
py_compile.compile(sp, doraise=True)
print('1) stock_service.py ساخته شد ✔')

# 2) پیش‌فاکتور: physical از منبع واحد
p = os.path.join(ROOT, 'app/ui/proforma_window.py')
lines = open(p, encoding='utf-8').read().split('\n')
i = j = None
for k, l in enumerate(lines):
    if 'from app.core.pallet_service import PalletService' in l:
        i = k
    if i is not None and 'physical = ps.' in l:
        j = k
        break
if i is not None and j is not None:
    ind = len(lines[i]) - len(lines[i].lstrip())
    lines[i:j + 1] = [' ' * ind + 'from app.core.stock_service import free_stock_map  # ONE-STOCK',
                      ' ' * ind + 'physical = free_stock_map(self.db)  # ONE-STOCK']
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    py_compile.compile(p, doraise=True)
    print('2) پیش‌فاکتور به منبع واحد وصل شد ✔')
else:
    print('2) ⚠ نقطه پیش‌فاکتور پیدا نشد')

# 3) ورود/خروج: بدنهٔ _stock_for_warehouse از منبع واحد
for rel in ('app/ui/issue_manager_window.py', 'app/ui/receipt_manager_window.py'):
    q = os.path.join(ROOT, rel)
    ls = open(q, encoding='utf-8').read().split('\n')
    a = b = None
    for k, l in enumerate(ls):
        if 'base = int(r[0] or 0) if r else 0  # STOCK-FORMULA' in l:
            a = k
        if a is not None and 'return base  # STOCK-FORMULA' in l:
            b = k
            break
    if a is not None and b is not None:
        ind = len(ls[a]) - len(ls[a].lstrip())
        ls[a:b + 1] = [' ' * ind + 'return int(free_stock(self.db, pallet_id) or 0)  # ONE-STOCK']
        # import بالای فایل
        last_imp = 0
        for k, l in enumerate(ls[:50]):
            if l.startswith('import ') or l.startswith('from '):
                last_imp = k
        ls[last_imp + 1:last_imp + 1] = ['from app.core.stock_service import free_stock  # ONE-STOCK']
        open(q, 'w', encoding='utf-8').write('\n'.join(ls))
        py_compile.compile(q, doraise=True)
        print('3)', rel, '✔')
    else:
        print('3)', rel, '⚠')

# 4) main: دیکشنری‌ها از منبع واحد
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
i = s.find('                    try:  # STOCK-FULL')
j = s.find('                        pass  # STOCK-FULL')
if i != -1 and j != -1:
    j += len('                        pass  # STOCK-FULL\n')
    block = ("                    try:  # ONE-STOCK\n"
             "                        from app.core.stock_service import free_stock_map as _fsm  # ONE-STOCK\n"
             "                        _m7 = _fsm(self.db)  # ONE-STOCK\n"
             "                        for _d6 in (getattr(self, 'pallet_stock', None), getattr(ps, 'pallet_stock', None)):  # ONE-STOCK\n"
             "                            if isinstance(_d6, dict):  # ONE-STOCK\n"
             "                                _d6.clear(); _d6.update(_m7)  # ONE-STOCK\n"
             "                    except Exception:  # ONE-STOCK\n"
             "                        pass  # ONE-STOCK\n")
    s = s[:i] + block + s[j:]
    open(mp, 'w', encoding='utf-8').write(s)
    py_compile.compile(mp, doraise=True)
    print('4) main به منبع واحد وصل شد ✔')
else:
    print('4) ⚠ بلوک STOCK-FULL پیدا نشد')

# 5) بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
print('5) بیلد...')
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
    print('5) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('6) تمام ✔')
input('Enter...')