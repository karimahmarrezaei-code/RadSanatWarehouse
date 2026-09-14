# -*- coding: utf-8 -*-
"""تسویه اسناد برگشت + چاپ کد کارت‌های داشبورد - اجرا: python fix_settle_returns.py"""
import os, sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
conn = sqlite3.connect(os.path.join(ROOT, 'data', 'app.db'))

print('=== اسناد برگشت قبل از اصلاح:')
for r in conn.execute("SELECT finance_no, total_amount, settled_amount, status FROM financial_documents WHERE finance_no LIKE 'B%'"):
    print('   ', r)

conn.execute("""
    UPDATE financial_documents
    SET status = 'SETTLED', settled_amount = COALESCE(total_amount, 0)
    WHERE finance_no LIKE 'B%' AND status != 'SETTLED'
""")
conn.commit()
print('✔ اسناد برگشت تسویه شدند — عدد منفی حذف می‌شود')

print('=== اسناد برگشت بعد از اصلاح:')
for r in conn.execute("SELECT finance_no, total_amount, settled_amount, status FROM financial_documents WHERE finance_no LIKE 'B%'"):
    print('   ', r)
conn.close()

# چاپ کد کارت‌های داشبورد برای بزرگ‌سازی باکس‌ها
p = os.path.join(ROOT, 'app', 'ui', 'main_window.py')
lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
print('\n=== کارت‌های داشبورد:')
for i, l in enumerate(lines):
    if any(k in l for k in ('دریافتنی باز', 'پرداختنی باز', 'card_', 'باز:', 'تسویه:')):
        for j in range(max(0, i - 2), min(len(lines), i + 10)):
            print('{:5d}|{}'.format(j + 1, lines[j]))
        print('   ---')
input('Enter...')