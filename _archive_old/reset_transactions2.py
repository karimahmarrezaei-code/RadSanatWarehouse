# -*- coding: utf-8 -*-
"""ریست داده‌های عملیاتی - نسخه ۲ (ستون‌تطبیقی) - اجرا: python reset_transactions2.py"""
import os, shutil, sqlite3, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
db = os.path.join(ROOT, 'data', 'app.db')
bak = db + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy2(db, bak)
print('✔ پشتیبان:', os.path.basename(bak))

conn = sqlite3.connect(db)
cur = conn.cursor()
names = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

TRANSACTIONAL = [
    'payment_entries', 'treasury_transactions', 'financial_documents',
    'journal_entries', 'journals', 'return_items',
    'warehouse_issue_items', 'warehouse_issues',
    'warehouse_receipt_items', 'warehouse_receipts',
    'outbound_loads', 'inbound_loads',
    'inventory_transactions', 'inventory_levels',
    'scrap_sales', 'box_sale_docs',
]
for t in TRANSACTIONAL:
    if t in names:
        cur.execute("DELETE FROM {}".format(t))
        print('   پاک شد:', t)
conn.commit()
print('✔ داده‌های عملیاتی پاک و **کامیت** شد')

# بازسازی موجودی از افتتاحیه (با ستون‌های تطبیقی)
try:
    oi_cols = {r[1] for r in cur.execute("PRAGMA table_info(opening_inventory_items)")}
    print('>>> ستون‌های افتتاحیه:', sorted(oi_cols))
    qty_col = 'qty' if 'qty' in oi_cols else ('quantity' if 'quantity' in oi_cols else None)
    if 'opening_inventory_items' in names and 'inventory_levels' in names and qty_col:
        cur.execute("DELETE FROM inventory_levels")
        if 'warehouse_id' in oi_cols:
            cur.execute(
                "INSERT INTO inventory_levels (pallet_id, warehouse_id, quantity, updated_at) "
                "SELECT pallet_id, warehouse_id, COALESCE(SUM({}),0), datetime('now') "
                "FROM opening_inventory_items GROUP BY pallet_id, warehouse_id".format(qty_col))
        else:
            wh = cur.execute("SELECT id FROM warehouses WHERE is_active = 1 ORDER BY id LIMIT 1").fetchone()
            wh_id = wh[0] if wh else 1
            cur.execute(
                "INSERT INTO inventory_levels (pallet_id, warehouse_id, quantity, updated_at) "
                "SELECT pallet_id, ?, COALESCE(SUM({}),0), datetime('now') "
                "FROM opening_inventory_items GROUP BY pallet_id".format(qty_col), (wh_id,))
        conn.commit()
        print('✔ موجودی بازسازی شد:',
              cur.execute("SELECT COUNT(*) FROM inventory_levels").fetchone()[0], 'ردیف')
    else:
        print('⚠️ افتتاحیه/ستون تعداد یافت نشد؛ موجودی با اولین تراکنش ساخته می‌شود')
except Exception as e:
    print('⚠️ بازسازی موجودی رد شد:', str(e)[:150])
conn.close()
print('\n✅ ریست کامل شد. اطلاعات پایه دست‌نخورده‌اند.')
input('Enter...')