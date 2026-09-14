# -*- coding: utf-8 -*-
"""تأیید عدد نهایی FN-000001 - اجرا: python verify_fn000001.py"""
import os, sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
conn = sqlite3.connect(os.path.join(ROOT, 'data', 'app.db'))
conn.row_factory = sqlite3.Row

print('=== اسناد مالی مشتری (پس از تطبیق) ===')
rows = conn.execute("SELECT finance_no, total_amount, settled_amount, status "
                    "FROM financial_documents "
                    "WHERE finance_no IN ('FN-000001','FN-000003','FN-000005','FN-000007') "
                    "ORDER BY finance_no").fetchall()
for r in rows:
    print('{:<12} | کل: {:>15,} | تسویه: {:>15,} | وضعیت: {}'.format(
        r['finance_no'], int(r['total_amount'] or 0), int(r['settled_amount'] or 0), r['status']))

print()
print('=== چک‌های مشتری آذر چوب ===')
chk = conn.execute("SELECT amount, status FROM payment_entries WHERE financial_document_id = "
                   "(SELECT id FROM financial_documents WHERE finance_no='FN-000001') "
                   "AND payment_method_id = (SELECT id FROM payment_methods WHERE code='CHECK')").fetchall()
paid = sum(int(c['amount'] or 0) for c in chk)
print('مجموع چک‌های پرداخت‌شده:', f"{paid:,}")

print()
print('=== سند کرایه راننده ===')
fr = conn.execute("SELECT finance_no, total_amount, counterparty_person_id, p.name "
                  "FROM financial_documents fd LEFT JOIN persons p ON p.id=fd.counterparty_person_id "
                  "WHERE fd.operation_type='OUTBOUND_FREIGHT' ORDER BY finance_no").fetchall()
for r in fr:
    print('{:<12} | کرایه: {:>12,} | راننده: {}'.format(
        r['finance_no'], int(r['total_amount'] or 0), r['name'] or '-'))
conn.close()
input('Enter...')