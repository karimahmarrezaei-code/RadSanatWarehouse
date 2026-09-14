# save as: test_service.py
import sys
sys.path.insert(0, '.')

from app.core.database import DatabaseManager
from app.core.pallet_service import PalletService

db = DatabaseManager('data/app.db')
svc = PalletService(db)

print('=== STEP 1: reload ===')
svc.reload()

print('=== STEP 2: all_pallets ===')
pallets = svc.all_pallets()
print('count:', len(pallets))
for p in pallets[:3]:
    print(' ', p)

print('=== STEP 3: stock_map ===')
stocks = svc.stock_map()
print('count:', len(stocks))
print('data:', stocks)

print('=== STEP 4: prices_map ===')
prices = svc.prices_map()
print('count:', len(prices))
print('data:', prices)

print('=== STEP 5: inventory_levels ===')
with db.connect() as conn:
    conn.row_factory = None
    rows = conn.execute(
        "SELECT pallet_id, warehouse_id, quantity FROM inventory_levels LIMIT 10"
    ).fetchall()
    print('inventory_levels rows:', len(rows))
    for r in rows:
        print(' ', dict(zip(['pallet_id','warehouse_id','quantity'], r)))

print('=== STEP 6: opening_inventory_items ===')
with db.connect() as conn:
    conn.row_factory = None
    rows = conn.execute(
        "SELECT pallet_id, qty, unit_price, total_price "
        "FROM opening_inventory_items LIMIT 10"
    ).fetchall()
    print('opening_inventory_items rows:', len(rows))
    for r in rows:
        print(' ', dict(zip(
            ['pallet_id','qty','unit_price','total_price'], r
        )))

print('=== STEP 7: inventory_transactions (OPENING) ===')
with db.connect() as conn:
    conn.row_factory = None
    rows = conn.execute("""
        SELECT pallet_id, warehouse_id, transaction_type,
               qty_in, qty_out, total_price
        FROM inventory_transactions
        WHERE transaction_type = 'OPENING'
        LIMIT 10
    """).fetchall()
    print('OPENING transactions:', len(rows))
    for r in rows:
        print(' ', r)