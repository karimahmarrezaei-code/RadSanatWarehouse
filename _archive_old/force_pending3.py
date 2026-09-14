# -*- coding: utf-8 -*-
"""آزادسازی قفل ابطال با فهرست شماره‌دار - اجرا: python force_pending3.py"""
import os, sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
conn = sqlite3.connect(os.path.join(ROOT, 'data', 'app.db'))
conn.row_factory = sqlite3.Row

def fa2en(s):
    for a, b in zip('۰۱۲۳۴۵۶۷۸۹', '0123456789'):
        s = s.replace(a, b)
    return s.replace('‌', '').strip()

rows = conn.execute("""
    SELECT fd.finance_no, pe.id AS pid, pe.amount, pe.treasury_account_id, ta.name AS acc
    FROM payment_entries pe
    JOIN financial_documents fd ON fd.id = pe.financial_document_id
    LEFT JOIN treasury_accounts ta ON ta.id = pe.treasury_account_id
    WHERE pe.status = 'CLEARED' ORDER BY fd.id
""").fetchall()

if not rows:
    print('✅ هیچ پرداخت وصول‌شده‌ای نیست؛ همهٔ اسناد آمادهٔ ابطال‌اند.')
else:
    print('🔒 پرداخت‌های وصول‌شده (قفلِ ابطال):')
    for i, r in enumerate(rows, 1):
        print('  [{}] {} | {:,} ریال | حساب: {}'.format(
            i, r['finance_no'], int(r['amount'] or 0), r['acc'] or '-'))
    sel = fa2en(input('\nشمارهٔ ردیف (یا 0 = همه): '))
    try:
        targets = rows if sel == '0' else [rows[int(sel) - 1]]
    except Exception:
        print('❌ ورودی نامعتبر')
        input('Enter...')
        raise SystemExit
    for r in targets:
        if r['treasury_account_id']:
            conn.execute("UPDATE treasury_accounts SET current_balance = COALESCE(current_balance,0) - ? "
                         "WHERE id = ?", (int(r['amount'] or 0), int(r['treasury_account_id'])))
        conn.execute("UPDATE payment_entries SET status='PENDING', treasury_account_id=NULL "
                     "WHERE id = ?", (r['pid'],))
        print('✔ {} آزاد شد → {:,} ریال به «در انتظار» برگشت'.format(
            r['finance_no'], int(r['amount'] or 0)))
    conn.commit()
conn.close()
print('\n✅ حالا برنامه را ببندید، باز کنید و سند را ابطال کنید ✔')
input('Enter...')