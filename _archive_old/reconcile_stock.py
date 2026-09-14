# -*- coding: utf-8 -*-
import sqlite3
from app.core.database import DatabaseManager
conn = sqlite3.connect(getattr(DatabaseManager(), 'db_path', None))
conn.row_factory = sqlite3.Row
now = "datetime('now')"

# ماندهٔ واقعی هر پالت/انبار از روی کاردکس
bals = {}
for r in conn.execute("""SELECT pallet_id, warehouse_id,
        SUM(CASE WHEN transaction_type='IN' THEN qty_in ELSE -qty_out END) AS bal
    FROM inventory_transactions GROUP BY pallet_id, warehouse_id"""):
    bals[(r['pallet_id'], r['warehouse_id'])] = int(r['bal'] or 0)

fixed = 0
for (pid, wid), bal in bals.items():
    if bal < 0:
        # اصلاحیه: ورودِ معادلِ منفی تا مانده صفر شود
        conn.execute(f"""INSERT INTO inventory_transactions
            (transaction_date,transaction_type,reference_type,reference_id,pallet_id,warehouse_id,
             qty_in,qty_out,unit_price,total_price,description,created_at)
            VALUES (date('now'),'IN','ADJUST',NULL,?,?,?,0,0,0,'اصلاحیه موجودی (حذف منفی)',{now})""",
            (pid, wid, -bal))
        bals[(pid, wid)] = 0
        fixed += 1

# همسان‌سازی inventory_levels با کاردکس
for (pid, wid), bal in bals.items():
    ex = conn.execute("SELECT id FROM inventory_levels WHERE pallet_id=? AND warehouse_id=?", (pid, wid)).fetchone()
    if ex:
        conn.execute("UPDATE inventory_levels SET quantity=?, updated_at=? WHERE id=?", (bal, now, ex['id']))
    elif bal > 0:
        conn.execute(f"INSERT INTO inventory_levels (pallet_id,warehouse_id,quantity,updated_at) VALUES (?,?,?,{now})", (pid, wid, bal))
conn.execute("DELETE FROM inventory_levels WHERE quantity<=0")
conn.commit()
print('اصلاحیه‌های ثبت‌شده:', fixed)
print('✅ موجودی‌ها با کاردکس هم‌سان شد؛ دیگر منفی نداریم.')
conn.close()