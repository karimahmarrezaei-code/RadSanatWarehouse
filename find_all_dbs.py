# -*- coding: utf-8 -*-
"""پیدا کردن همه app.db ها - اجرا: python find_all_dbs.py"""
import os, sqlite3, time
ROOT = os.path.dirname(os.path.abspath(__file__))
print('=== همهٔ app.db های زیر پروژه ===')
for dp, ds, fs in os.walk(ROOT):
    if any(k in dp for k in ('.venv', '.git')):
        continue
    if 'app.db' in fs:
        p = os.path.join(dp, 'app.db')
        try:
            con = sqlite3.connect(p)
            cnt = con.execute("SELECT count(*) FROM pallets").fetchone()[0]
            codes = [r[0] for r in con.execute("SELECT code FROM pallets LIMIT 5").fetchall()]
            try:
                wh = con.execute("SELECT count(*) FROM warehouses").fetchone()[0]
            except Exception:
                wh = '?'
            con.close()
        except Exception as e:
            cnt, codes, wh = f'err', [], '?'
        print(f'{os.path.relpath(p, ROOT)} | pallets={cnt} | warehouses={wh} | codes={codes} | mtime={time.ctime(os.path.getmtime(p))}')
input('Enter...')