# -*- coding: utf-8 -*-
"""ریست داده‌های عملیاتی با حفظ اطلاعات پایه - اجرا: python reset_transactions.py"""
import os, shutil, sqlite3, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
db = os.path.join(ROOT, 'data', 'app.db')
bak = db + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy2(db, bak)
print('✔ پشتیبان کامل:', os.path.basename(bak))

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
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        cur.execute(f"DELETE FROM {t}")
        print('   پاک شد: {} ({} ردیف)'.format(t, n))

# بازسازی موجودی از افتتاحیه (اطلاعات پایه)
if 'opening_inventory_items' in names and 'inventory_levels' in names:
    cur.execute("DELETE FROM inventory_levels")
    cur.execute("""
        INSERT INTO inventory_levels (pallet_id, warehouse_id, quantity, updated_at)
        SELECT pallet_id, warehouse_id, COALESCE(SUM(qty),0), datetime('now')
        FROM opening_inventory_items GROUP BY pallet_id, warehouse_id
    """)
    print('✔ موجودی از افتتاحیه بازسازی شد:',
          cur.execute("SELECT COUNT(*) FROM inventory_levels").fetchone()[0], 'پالت')
conn.commit()
conn.close()
print('\n✅ ریست کامل شد. اطلاعات پایه (اشخاص، پالت‌ها، انبارها، رانندگان، صندوق/بانک) دست‌نخورده‌اند.')
input('Enter...')