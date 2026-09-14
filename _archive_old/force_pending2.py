# -*- coding: utf-8 -*-
"""آزادسازی قفل ابطال - نسخه پُرسروصدا - اجرا: python force_pending2.py"""
import os, sqlite3, traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(ROOT, 'data', 'app.db')

print('=' * 60)
print('🔓 ابزار آزادسازی قفل ابطال سند')
print('=' * 60)
print(f'📂 مسیر دیتابیس: {db_path}')
print(f'✓ فایل موجود است: {os.path.exists(db_path)}')

if not os.path.exists(db_path):
    print('❌ دیتابیس یافت نشد!')
    input('Enter...')
    exit()

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    fn = input('\nشماره سند مالی (مثلاً FN-000005): ').strip().upper()
    print(f'\n🔍 جستجوی سند: {fn}')
    
    doc = conn.execute(
        "SELECT id, finance_no, total_amount, status FROM financial_documents WHERE finance_no = ?", 
        (fn,)
    ).fetchone()
    
    if not doc:
        print(f'❌ سند {fn} در دیتابیس یافت نشد!')
        print('\n📋 ۱۰ سند مالی اخیر:')
        recent = conn.execute("SELECT finance_no, total_amount, status FROM financial_documents ORDER BY id DESC LIMIT 10").fetchall()
        for r in recent:
            print(f"   {r['finance_no']} | {int(r['total_amount'] or 0):,} ریال | {r['status']}")
        input('\nEnter...')
        exit()
    
    print(f'\n✅ سند یافت شد:')
    print(f'   شماره: {doc["finance_no"]}')
    print(f'   مبلغ: {int(doc["total_amount"] or 0):,} ریال')
    print(f'   وضعیت: {doc["status"]}')
    
    pays = conn.execute("""
        SELECT pe.id, pe.amount, pe.status, pe.treasury_account_id, 
               COALESCE(ta.name, '-') as acc_name
        FROM payment_entries pe
        LEFT JOIN treasury_accounts ta ON ta.id = pe.treasury_account_id
        WHERE pe.financial_document_id = ?
    """, (doc['id'],)).fetchall()
    
    print(f'\n💰 پرداخت‌های این سند ({len(pays)} مورد):')
    if not pays:
        print('   (هیچ پرداختی ثبت نشده)')
    else:
        for p in pays:
            print(f"   • ID={p['id']} | {int(p['amount'] or 0):,} ریال | وضعیت: {p['status']} | حساب: {p['acc_name']}")
    
    cleared = [p for p in pays if p['status'] == 'CLEARED']
    print(f'\n🔒 پرداخت‌های وصول‌شده (CLEARED): {len(cleared)} مورد')
    
    if not cleared:
        print('\n✅ هیچ پرداخت وصول‌شده‌ای وجود ندارد!')
        print('   سند آمادهٔ ابطال است.')
        input('\nEnter...')
        exit()
    
    print(f'\n⚙️ در حال آزادسازی {len(cleared)} پرداخت...')
    for p in cleared:
        # 1. معکوس‌سازی صندوق
        if p['treasury_account_id']:
            conn.execute("""
                UPDATE treasury_accounts 
                SET current_balance = COALESCE(current_balance, 0) - ? 
                WHERE id = ?
            """, (int(p['amount']), p['treasury_account_id']))
            print(f'   ↩️ {int(p["amount"]):,} ریال از حساب «{p["acc_name"]}» کسر شد')
        
        # 2. تغییر وضعیت به PENDING
        conn.execute("""
            UPDATE payment_entries 
            SET status = 'PENDING', treasury_account_id = NULL 
            WHERE id = ?
        """, (p['id'],))
        print(f'   ✓ پرداخت ID={p["id"]} به وضعیت «در انتظار» برگشت')
    
    conn.commit()
    conn.close()
    
    print('\n' + '=' * 60)
    print('✅ عملیات با موفقیت انجام شد!')
    print('حالا به برنامه برگردید و سند را ابطال کنید.')
    print('=' * 60)

except Exception as e:
    print(f'\n❌ خطا رخ داد:')
    print(traceback.format_exc())

input('\nEnter...')