# -*- coding: utf-8 -*-
"""cleanup.py - بازنشانی کامل داده‌های تراکنشی (اطلاعات پایه و افتتاحیه دست‌نخورده)"""
import sqlite3
from app.core.config import DB_PATH

def main():
    print('DB file:', DB_PATH)
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    cur = conn.cursor()

    def count(q):
        return cur.execute(q).fetchone()[0]

    print('BEFORE:',
          count('SELECT COUNT(*) FROM warehouse_receipts'),
          count('SELECT COUNT(*) FROM warehouse_issues'),
          count('SELECT COUNT(*) FROM financial_documents'),
          count('SELECT COUNT(*) FROM proforma_invoices'))

    cur.execute("PRAGMA foreign_keys = OFF")
    stmts = [
        # ── اسناد مالی و پرداخت‌ها ─────────────────────────
        "DELETE FROM payment_entries",
        "DELETE FROM journal_lines",
        "DELETE FROM journal_entries",
        "DELETE FROM treasury_transactions",
        "DELETE FROM financial_documents",

        # ── پیش‌فاکتورها (شماره‌ها از 0001) ─────────────────
        "DELETE FROM proforma_invoice_items",
        "DELETE FROM proforma_invoices",

        # ── اسناد انبار و مرجع‌ها ──────────────────────────
        "DELETE FROM warehouse_receipt_items",
        "DELETE FROM warehouse_receipts",
        "DELETE FROM warehouse_issue_items",
        "DELETE FROM warehouse_issues",
        "DELETE FROM outbound_load_items",   # اقلام مرجع خروج (تبدیل پیش‌فاکتور)
        "DELETE FROM inbound_loads",
        "DELETE FROM outbound_loads",

        # ── جدول‌های قدیمی ─────────────────────────────────
        "DELETE FROM stock_movements",
        "DELETE FROM stock_document_lines",
        "DELETE FROM stock_documents",
        "DELETE FROM shipment_orders",

        # ── کاردکس: فقط رسید/حواله، افتتاحیه بماند ─────────
               # قبل:
        #"DELETE FROM inventory_transactions WHERE reference_type IN ('RECEIPT','ISSUE')",
        # بعد:
        "DELETE FROM inventory_transactions WHERE reference_type IN ('RECEIPT','ISSUE','TRANSFER')",


        # ── موجودی لحظه‌ای: بازسازی از افتتاحیه ────────────
        "DELETE FROM inventory_levels",

        # ── صفر کردن مانده صندوق/بانک ─────────────────────
        "UPDATE treasury_accounts SET opening_balance = 0, current_balance = 0, updated_at = datetime('now')",

        # ── صفر کردن همهٔ شماره‌گذاری‌ها (RC/IS/PR/WH/EX) ──
        "UPDATE sequences SET current_value = 0, updated_at = datetime('now')",

                # ── جابجایی‌ها ─────────────────────────────────────
        "DELETE FROM pallet_transfer_items",
        "DELETE FROM pallet_transfers",
    ]
    for s in stmts:
        cur.execute(s)
        print('affected', cur.rowcount, '<-', s)

    # بازسازی موجودی از افتتاحیه
    cur.execute("""
        INSERT INTO inventory_levels (pallet_id, warehouse_id, quantity, updated_at)
        SELECT oii.pallet_id, oid.warehouse_id, SUM(oii.qty), datetime('now')
        FROM opening_inventory_items oii
        JOIN opening_inventory_documents oid ON oid.id = oii.opening_document_id
        GROUP BY oii.pallet_id, oid.warehouse_id
    """)
    print('inventory_levels rebuilt:', cur.rowcount)

    conn.commit()

    print('AFTER:',
          count('SELECT COUNT(*) FROM warehouse_receipts'),
          count('SELECT COUNT(*) FROM warehouse_issues'),
          count('SELECT COUNT(*) FROM financial_documents'),
          count('SELECT COUNT(*) FROM proforma_invoices'))
    print('treasury balances:', count('SELECT COALESCE(SUM(current_balance),0) FROM treasury_accounts'))
    print('sequences max:', count('SELECT COALESCE(MAX(current_value),0) FROM sequences'))
    conn.close()
    print('DONE')

if __name__ == '__main__':
    main()