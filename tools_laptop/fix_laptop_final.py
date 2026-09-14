# -*- coding: utf-8 -*-
import os

def find_db():
    base = os.path.dirname(os.path.abspath(__file__))
    for b in (base, os.path.dirname(base)):
        for p in (os.path.join(b, '_internal', 'data', 'app.db'),
                  os.path.join(b, 'data', 'app.db')):
            if os.path.exists(p):
                return p
    return None

"""اصلاح یکپارچگی نهایی - لپ‌تاپ"""
import sqlite3

dbp = find_db()
print('دیتابیس:', dbp)
c = sqlite3.connect(dbp)
r = c.execute("UPDATE financial_documents SET settled_amount = total_amount "
              "WHERE settled_amount > total_amount AND total_amount > 0")
print('تسویهٔ سقف‌شده:', r.rowcount)
r = c.execute("UPDATE financial_documents SET status='SETTLED' "
              "WHERE total_amount > 0 AND settled_amount >= total_amount")
print('وضعیت SETTLED:', r.rowcount)
r = c.execute("UPDATE financial_documents SET status='OPEN' WHERE settled_amount = 0")
print('وضعیت OPEN:', r.rowcount)
try:
    c.execute("ALTER TABLE payroll_transactions ADD COLUMN treasury_account_id INTEGER")
    print('ستون حساب پرسنل: اضافه شد')
except Exception:
    print('ستون حساب پرسنل: موجود بود')
c.commit()
c.close()
print('✔ تمام')
input('Enter...')
