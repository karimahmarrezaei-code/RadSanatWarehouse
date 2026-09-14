# -*- coding: utf-8 -*-
import sqlite3
from app.core.database import DatabaseManager
conn = sqlite3.connect(getattr(DatabaseManager(), 'db_path', None))
conn.row_factory = sqlite3.Row

# افتتاحیه به تفکیک انبار
opening = {}
for r in conn.execute("""SELECT oid.warehouse_id, oii.pallet_id, SUM(oii.qty) q
    FROM opening_inventory_items oii
    JOIN opening_inventory_documents oid ON oii.opening_document_id = oid.id
    GROUP BY oid.warehouse_id, oii.pallet_id"""):
    opening[(r['pallet_id'], r['warehouse_id'])] = int(r['q'] or 0)

# خالص حرکت‌ها به تفکیک انبار
net = {}
for r in conn.execute("""SELECT pallet_id, warehouse_id,
        SUM(CASE WHEN transaction_type='IN' THEN qty_in ELSE -qty_out END) q
    FROM inventory_transactions WHERE COALESCE(is_void,0)=0
    GROUP BY pallet_id, warehouse_id"""):
    net[(r['pallet_id'], r['warehouse_id'])] = int(r['q'] or 0)

keys = set(opening) | set(net)
for (pid, wid) in keys:
    qty = opening.get((pid, wid), 0) + net.get((pid, wid), 0)
    ex = conn.execute("SELECT id FROM inventory_levels WHERE pallet_id=? AND warehouse_id=?", (pid, wid)).fetchone()
    if ex:
        conn.execute("UPDATE inventory_levels SET quantity=? WHERE id=?", (qty, ex['id']))
    elif qty > 0:
        conn.execute("INSERT INTO inventory_levels (pallet_id,warehouse_id,quantity,updated_at) VALUES (?,?,?,datetime('now'))", (pid, wid, qty))
conn.execute("DELETE FROM inventory_levels WHERE quantity<=0")
conn.commit()

print('✅ موجودی = افتتاحیه + حرکت‌ها؛ حالا کاردکس، ارزش ریالی و موجودی انبار هم‌خوان‌اند.')
for r in conn.execute("""SELECT p.code, w.name, il.quantity FROM inventory_levels il
    JOIN pallets p ON p.id=il.pallet_id LEFT JOIN warehouses w ON w.id=il.warehouse_id
    ORDER BY p.code, w.name"""):
    print(f"  {r['code']} | {r['name']} | {int(r['quantity']):,}")
conn.close()