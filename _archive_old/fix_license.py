# -*- coding: utf-8 -*-
"""تمدید لایسنس تا ۱۴۰۵/۱۲/۲۹ (معادل 2027-03-20) - اجرا: python fix_license.py"""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
sys.path.insert(0, ROOT)
from app.core import license_manager as lm

st = lm.check()
print('قبل از تمدید:', st)

old = lm.load_license()
pl = lm.parse_code(old) if old else None
company = (pl or {}).get('c', 'RadSanatNovin')

START = '2026-01-01'   # شروع اعتبار
END   = '2027-03-20'   # = ۱۴۰۵/۱۲/۲۹ (آخر اسفند ۱۴۰۵)

code = lm.make_code(company, START, END, machine='', ltype='full')
print('payload جدید:', lm.parse_code(code))

targets = [os.path.join('data', 'license.key'),
           os.path.join('dist', 'RadSanatWarehouse', '_internal', 'data', 'license.key')]
for t in targets:
    os.makedirs(os.path.dirname(t), exist_ok=True)
    with open(t, 'w', encoding='utf-8') as f:
        f.write(code)
    print('نوشته شد:', t)

print('بعد از تمدید:', lm.check())
input('Enter...')