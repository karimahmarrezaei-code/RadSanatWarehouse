# -*- coding: utf-8 -*-
"""
نیرومند: باز کردن قفل ابطال سند (مستقیم از دیتابیس)
اجرا: python force_pending.py
"""
import os
import sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(ROOT, 'data', 'app.db')

if not os.path.exists(db_path):
    print("❌ فایل دیتابیس پیدا نشد.")
    input()
    exit()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

print("=== 🔓 ابزار رفع قفل ابطال سند ===")
fn = input("شماره سند مالی را وارد کنید (مثلاً FN-000005): ").strip().upper()

doc = conn.execute("SELECT id, finance_no, total_amount FROM financial_documents WHERE finance_no = ?", (fn,)).fetchone()
if not doc:
    print(f"❌ سند {fn} در دیتابیس یافت نشد.")
    input()
    exit()

print(f"\n📄 سند: {doc['finance_no']} | مبلغ: {int(doc['total_amount'] or 0):,} ریال")

pays = conn.execute("""
    SELECT pe.id, pe.amount, pe.status, pe.treasury_account_id, ta.name as acc_name
    FROM payment_entries pe
    LEFT JOIN treasury_accounts ta ON ta.id = pe.treasury_account_id
    WHERE pe.financial_document_id = ?
""", (doc['id'],)).fetchall()

if not pays:
    print("ℹ️ این سند هیچ پرداختی ندارد. آماده ابطال است.")
    input()
    exit()

print("\nلیست پرداخت‌های این سند:")
for p in pays:
    print(f"  - مبلغ: {int(p['amount'] or 0):,} ریال | وضعیت: {p['status']} | حساب: {p['acc_name'] or '-'}")

cleared = [p for p in pays if p['status'] == 'CLEARED']
if not cleared:
    print("\n✅ هیچ پرداخت وصول‌شده‌ای (CLEARED) وجود ندارد. قفل ابطال از قبل باز است!")
    input()
    exit()

print(f"\n⚠️ {len(cleared)} پرداخت وصول‌شده یافت شد. در حال آزادسازی و معکوس‌سازی صندوق...")
for p in cleared:
    # 1. برگشت پول از صندوق/بانک
    if p['treasury_account_id']:
        conn.execute("""
            UPDATE treasury_accounts 
            SET current_balance = COALESCE(current_balance, 0) - ? 
            WHERE id = ?
        """, (int(p['amount']), p['treasury_account_id']))
        print(f"  ↩️ {int(p['amount']):,} ریال از حساب «{p['acc_name']}» کسر و به حالت معلق برگشت.")
    
    # 2. تغییر وضعیت به PENDING
    conn.execute("""
        UPDATE payment_entries 
        SET status = 'PENDING', treasury_account_id = NULL 
        WHERE id = ?
    """, (p['id'],))

conn.commit()
conn.close()

print("\n" + "="*50)
print("✅ عملیات با موفقیت انجام شد!")
print("حالا به برنامه برگردید و سند/حواله را ابطال کنید. قفل باز است.")
print("="*50)
input("Enter...")