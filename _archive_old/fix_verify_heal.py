# -*- coding: utf-8 -*-
"""بررسی + ترمیم + چاپ عدد فرمول - اجرا: python fix_verify_heal.py"""
import os, re, sys, shutil, py_compile, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

src = os.path.join(ROOT, 'app', 'ui', 'proforma_window.py')
dst = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'app', 'ui', 'proforma_window.py')

# 1) منبع: اگر ONE-STOCK نیست، با ریگکس شناور بگذار
s = open(src, encoding='utf-8').read()
if '# ONE-STOCK' not in s:
    s2, n = re.subn(r"(?m)^(\s*)physical\s*=\s*dict\(self\.items_table\.stocks\)\s*$",
                    lambda m: m.group(1) + "from app.core.stock_service import free_stock_map  # ONE-STOCK\n" + m.group(1) + "physical = free_stock_map(self.db)  # ONE-STOCK",
                    s, count=1)
    if n:
        open(src, 'w', encoding='utf-8').write(s2)
        py_compile.compile(src, doraise=True)
        print('1) منبع ترمیم شد ✔')
    else:
        print('1) ⚠ خط physical در منبع پیدا نشد')
else:
    print('1) منبع ONE-STOCK دارد ✔')

# 2) کپی اجباری به dist (بدون بیلد)
for rel in ('app/ui/proforma_window.py', 'app/ui/issue_manager_window.py',
            'app/ui/receipt_manager_window.py', 'app/core/stock_service.py', 'main.py'):
    a = os.path.join(ROOT, rel)
    b = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', rel)
    if os.path.exists(a):
        os.makedirs(os.path.dirname(b), exist_ok=True)
        shutil.copy2(a, b)
print('2) کپی به dist انجام شد ✔')
d = open(dst, encoding='utf-8', errors='replace').read()
print('   dist ONE-STOCK دارد:', '# ONE-STOCK' in d)

# 3) اجرای زندهٔ فرمول روی دیتابیس
dbp = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
con = sqlite3.connect(dbp)
phys = {r[0]: int(r[1] or 0) for r in con.execute("SELECT pallet_id, COALESCE(SUM(quantity),0) FROM inventory_levels GROUP BY pallet_id").fetchall()}
iss = {r[0]: int(r[1] or 0) for r in con.execute("SELECT wii.pallet_id, SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.issue_status!='CANCELLED' GROUP BY wii.pallet_id").fetchall()}
rsv = {r[0]: int(r[1] or 0) for r in con.execute("SELECT oli.pallet_id, SUM(oli.qty - COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=ol.id AND wi.issue_status!='CANCELLED' AND wii.pallet_id=oli.pallet_id),0)) FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id WHERE ol.load_status='OPEN' AND ol.is_active=1 GROUP BY oli.pallet_id").fetchall()}
print('3) physical :', phys)
print('   issued   :', iss)
print('   reserved :', rsv)
print('   FREE     :', {p: max(phys.get(p, 0) - iss.get(p, 0) - rsv.get(p, 0), 0) for p in phys})
con.close()
input('Enter...')