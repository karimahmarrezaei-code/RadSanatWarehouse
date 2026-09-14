# -*- coding: utf-8 -*-
"""پاک‌سازی داده‌های تراکنشی برای شروع تست تازه
اجرا: py reset_test_data.py  (ابتدا برنامه را ببندید)"""
import os, sqlite3
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

dbs = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d.lower() not in ('.venv', 'venv', '__pycache__', '.git', 'backups')]
    for fn in filenames:
        if fn.lower().endswith(('.db', '.sqlite', '.sqlite3')):
            dbs.append(os.path.join(dirpath, fn))
DB = sorted(dbs, key=os.path.getmtime)[-1]
BACK = os.path.join(os.path.dirname(DB), 'backups')
os.makedirs(BACK, exist_ok=True)

# ---------- 1) بک‌آپ نهایی ----------
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
FINAL = os.path.join(BACK, 'warehouse_FINAL_before_reset_{}.db'.format(stamp))
con0 = sqlite3.connect(DB, timeout=30)
con0.execute('VACUUM INTO ?', (FINAL,))
con0.close()
print('OK - بک‌آپ نهایی ساخته شد:', os.path.basename(FINAL))

# ---------- 2) گزارش وضعیت فعلی + تأیید ----------
con = sqlite3.connect(DB, timeout=30)
print('وضعیت فعلی:')
for t in ('proforma_invoices', 'outbound_loads', 'warehouse_issues', 'warehouse_receipts',
          'inventory_transactions', 'financial_documents', 'payment_entries', 'bank_accounts'):
    try:
        print('  - {}: {} ردیف'.format(t, con.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0]))
    except Exception:
        pass
ans = input('برای پاک‌سازی کامل عبارت «پاک شود» را بنویسید: ').strip()
if ans != 'پاک شود':
    print('لغو شد؛ هیچ تغییری اعمال نشد.')
    con.close(); input('Enter...'); raise SystemExit(0)

# ---------- 3) پاک‌سازی تراکنش‌ها ----------
WIPE = [
    'proforma_invoice_items', 'proforma_invoices',
    'warehouse_issue_items', 'warehouse_issues',
    'warehouse_receipt_items', 'warehouse_receipts',
    'outbound_load_items', 'outbound_loads', 'inbound_loads',
    'inventory_transactions', 'inventory_levels', 'opening_inventory_items', 'pallet_transfers',
    'stock_movements', 'stock_document_lines', 'stock_documents', 'stock_takes', 'stock_adjustments',
    'invoice_items', 'return_items', 'shipment_orders',
    'box_sale_items', 'box_sales', 'box_production', 'box_inventory', 'box_expenses',
    'scrap_sale_photos', 'scrap_sale_items', 'scrap_sales',
    'payment_entries', 'treasury_transactions', 'cash_transactions',
    'journal_lines', 'journal_entries', 'financial_documents',
    'bank_reconciliations', 'checkbook_movements', 'checkbook_checks', 'bank_accounts', 'cash_accounts',
    'document_images', 'audit_logs',
    'sequences', 'sqlite_sequence',
]
for t in WIPE:
    try:
        n = con.execute('DELETE FROM %s' % t).rowcount
        print('پاک شد: {} ({} ردیف)'.format(t, n))
    except Exception as e:
        print('رد شد: {} ({})'.format(t, e))
con.commit(); con.close()

# ---------- 4) حذف بک‌آپ‌های قدیمی ----------
removed = 0
for f in os.listdir(BACK):
    if f.endswith('.db') and f != os.path.basename(FINAL):
        try:
            os.remove(os.path.join(BACK, f)); removed += 1
        except Exception:
            pass
print('OK - بک‌آپ‌های قدیمی حذف شد:', removed)
print('=' * 60)
print('تمام! شماره‌ها از 0001 شروع می‌شوند؛ بک‌آپ نهایی:', os.path.basename(FINAL))
input('Enter...')