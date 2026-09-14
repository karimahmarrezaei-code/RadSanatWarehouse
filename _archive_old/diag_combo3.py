# -*- coding: utf-8 -*-
"""مقایسه schema پالت‌ها: کد vs دیتابیس - اجرا: python diag_combo3.py"""
import os, re, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__))

print('=' * 30, '1) CREATE TABLE pallets در schema.sql', '=' * 30)
for rel in (os.path.join('data', 'schema.sql'), 'schema.sql'):
    p = os.path.join(ROOT, rel)
    if os.path.exists(p):
        t = open(p, encoding='utf-8', errors='replace').read()
        m = re.search(r'CREATE TABLE\s+(IF NOT EXISTS\s+)?pallets\s*\(.*?\);', t, re.I | re.S)
        print(rel, '->')
        print(m.group(0) if m else '(پیدا نشد)')

print('=' * 30, '2) ستون‌های واقعی در هر دو دیتابیس', '=' * 30)
for name, p in (('data/app.db', os.path.join(ROOT, 'data', 'app.db')),
                ('dist', os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db'))):
    if os.path.exists(p):
        con = sqlite3.connect(p)
        cols = [r[1] for r in con.execute('PRAGMA table_info(pallets)').fetchall()]
        print(name, '->', cols)
        con.close()

print('=' * 30, '3) کدِ ذخیرهٔ پالت (INSERT/UPDATE)', '=' * 30)
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith('.py'):
            fp = os.path.join(dp, fn)
            t = open(fp, encoding='utf-8', errors='replace').read()
            for kw in ('INSERT INTO pallets', 'UPDATE pallets'):
                i = t.find(kw)
                while i != -1:
                    print('---', os.path.relpath(fp, ROOT), kw)
                    print('\n'.join(t[max(0, i - 400):i + 600].split('\n')))
                    i = t.find(kw, i + 1)
input('Enter...')