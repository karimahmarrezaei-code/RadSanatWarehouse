# -*- coding: utf-8 -*-
"""کوئری واقعی کامبوی پالت + شمارش جدول‌ها - اجرا: python diag_combo2.py"""
import os, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__))

print('=' * 30, 'توابع _load_pallets در همهٔ فرم‌ها', '=' * 30)
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app', 'ui')):
    for fn in fs:
        if fn.endswith('.py'):
            p = os.path.join(dp, fn)
            t = open(p, encoding='utf-8', errors='replace').read()
            i = t.find('def _load_pallets')
            while i != -1:
                print('=' * 20, os.path.relpath(p, ROOT))
                print('\n'.join(t[i:i + 1500].split('\n')[:30]))
                i = t.find('def _load_pallets', i + 1)

print('=' * 30, 'شمارش جدول‌های مرتبط در data/app.db', '=' * 30)
con = sqlite3.connect(os.path.join(ROOT, 'data', 'app.db'))
tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
for t in tabs:
    if any(k in t.lower() for k in ('pallet', 'stock', 'warehouse')):
        try:
            print(f'{t}: {con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]}')
        except Exception:
            pass
con.close()
input('Enter...')