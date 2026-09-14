# -*- coding: utf-8 -*-
"""تشخیص دقیق مشکل کامبو - اجرا: python diag_combo.py"""
import os, sys, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

print('=' * 30, '1) combo_refresh_patch.py', '=' * 30)
p = os.path.join(ROOT, 'app', 'ui', 'combo_refresh_patch.py')
if os.path.exists(p):
    print('SIZE:', os.path.getsize(p), 'bytes')
    print(open(p, encoding='utf-8', errors='replace').read())
else:
    print('NOT FOUND!')

print('=' * 30, '2) وضعیت پالت‌ها در دیتابیس', '=' * 30)
db = os.path.join(ROOT, 'data', 'app.db')
if os.path.exists(db):
    con = sqlite3.connect(db)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print('tables:', [t for t in tables if 'pallet' in t.lower() or 'plate' in t.lower()])
        for t in tables:
            if 'pallet' in t.lower() or 'plate' in t.lower():
                cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})").fetchall()]
                print(f'  {t} columns:', cols)
                rows = con.execute(f"SELECT * FROM {t} LIMIT 10").fetchall()
                print(f'  rows (max 10):', rows)
                try:
                    cnt = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                    print(f'  TOTAL COUNT:', cnt)
                except: pass
    finally:
        con.close()
else:
    print('app.db not found')

print('=' * 30, '3) جستجوی load_pallets در فرم‌های اصلی', '=' * 30)
targets = ['app/ui/receipt_window.py', 'app/ui/proforma_window.py',
           'app/ui/issue_window.py', 'app/ui/proforma_form.py']
for rel in targets:
    fp = os.path.join(ROOT, rel)
    if not os.path.exists(fp):
        continue
    lines = open(fp, encoding='utf-8', errors='replace').read().split('\n')
    print(f'--- {rel} ({len(lines)} lines) ---')
    for i, l in enumerate(lines):
        if any(k in l for k in ('pallet_combo', 'pallet_cb', 'load_pallet',
                                 'pallet_combo.addItem', 'clear()', 'combo.clear')):
            print(f'{i+1:5} {l.rstrip()}')

input('Enter...')