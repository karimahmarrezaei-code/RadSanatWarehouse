# -*- coding: utf-8 -*-
"""بررسی دیتابیس و اضافه کردن پالت تستی - اجرا: python fix_check_db.py"""
import os, sqlite3, shutil
ROOT = os.path.dirname(os.path.abspath(__file__))

print('=' * 60)
print('بررسی دیتابیس‌های موجود')
print('=' * 60)

# 1) چک هر دو دیتابیس
paths = [
    ('data/app.db (منبع)', os.path.join(ROOT, 'data', 'app.db')),
    ('dist/_internal/data/app.db (بسته)', 
     os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')),
]

for name, p in paths:
    print(f'\n{name}:')
    if os.path.exists(p):
        print(f'  SIZE: {os.path.getsize(p)} bytes')
        con = sqlite3.connect(p)
        try:
            cnt = con.execute("SELECT count(*) FROM pallets").fetchone()[0]
            print(f'  pallets count: {cnt}')
            if cnt == 0:
                print('  ⚠ خالی است!')
            else:
                rows = con.execute("SELECT id, code, name FROM pallets LIMIT 5").fetchall()
                print(f'  sample: {rows}')
        except Exception as e:
            print(f'  error: {e}')
        finally:
            con.close()
    else:
        print('  NOT FOUND')

# 2) اگر data/app.db خالی بود، یک پالت تستی اضافه کن
db = os.path.join(ROOT, 'data', 'app.db')
if os.path.exists(db):
    con = sqlite3.connect(db)
    try:
        cnt = con.execute("SELECT count(*) FROM pallets").fetchone()[0]
        if cnt == 0:
            print('\n' + '=' * 60)
            print('اضافه کردن پالت تستی به data/app.db')
            print('=' * 60)
            con.execute("""
                INSERT INTO pallets (code, name, material_type, length_cm, width_cm, height_cm,
                                    warehouse_id, opening_stock, low_stock_threshold, is_active,
                                    created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))
            """, ('PLT-001', 'پالت چوبی استاندارد', 'چوب', 120, 100, 150, 1, 0, 10))
            con.commit()
            print('✔ پالت تستی اضافه شد: PLT-001')
        else:
            print(f'\n✔ data/app.db دارای {cnt} پالت است')
    finally:
        con.close()

print('\n' + '=' * 60)
print('حالا run.bat را اجرا کنید و فرم پیش‌فاکتور را باز کنید')
print('باید پالت PLT-001 در کامبو ظاهر شود')
print('=' * 60)
input('Enter...')