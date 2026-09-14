# -*- coding: utf-8 -*-
import sqlite3
from app.core.database import DatabaseManager
conn = sqlite3.connect(getattr(DatabaseManager(), 'db_path', None))
conn.row_factory = sqlite3.Row

bad = conn.execute("SELECT COUNT(*) c FROM inventory_transactions "
                   "WHERE reference_type='TRANSFER' AND transaction_type='IN' AND qty_out<>0").fetchone()['c']
print('ردیف خراب باقی‌مانده:', bad)

print('\nماندهٔ هر پالت به تفکیک انبار (از کاردکس):')
for r in conn.execute("""SELECT p.code, w.name,
        SUM(CASE WHEN t.transaction_type='IN' THEN t.qty_in ELSE -t.qty_out END) AS bal
    FROM inventory_transactions t
    JOIN pallets p ON p.id=t.pallet_id
    LEFT JOIN warehouses w ON w.id=t.warehouse_id
    GROUP BY p.code, w.name ORDER BY p.code, w.name"""):
    print(f"  {r['code']} | {r['name'] or '-'} | {int(r['bal']):,}")

print('\nموجودی انبار (از inventory_levels):')
for r in conn.execute("""SELECT p.code, w.name, il.quantity
    FROM inventory_levels il
    JOIN pallets p ON p.id=il.pallet_id
    LEFT JOIN warehouses w ON w.id=il.warehouse_id
    ORDER BY p.code, w.name"""):
    print(f"  {r['code']} | {r['name'] or '-'} | {int(r['quantity']):,}")
conn.close()