# -*- coding: utf-8 -*-
"""بازبینی ساختاری مسیر موجودی پیش‌فاکتور - اجرا: python diag_proforma.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(ROOT, 'app/ui/proforma_window.py')
lines = open(p, encoding='utf-8', errors='replace').read().split('\n')

print('=== الف) برچسب مانده انبار ===')
n = 0
for i, l in enumerate(lines):
    if 'مانده انبار' in l or 'موجودی آزاد' in l:
        for j in range(max(0, i - 10), min(len(lines), i + 6)):
            print(f'{j+1:5} {lines[j].rstrip()}')
        print('-' * 50)
        n += 1
        if n >= 2:
            break

print('=== ب) هر جا pallet_stock / pallets پر می‌شود ===')
n = 0
for i, l in enumerate(lines):
    if 'pallet_stock' in l or 'self.pallets =' in l or 'pallet_service' in l:
        for j in range(max(0, i - 4), min(len(lines), i + 8)):
            print(f'{j+1:5} {lines[j].rstrip()}')
        print('-' * 50)
        n += 1
        if n >= 5:
            break

print('=== ج) تابع _load_pallets کامل ===')
s = None
for i, l in enumerate(lines):
    if l.strip().startswith('def _load_pallets'):
        s = i
        break
if s is not None:
    ind = len(lines[s]) - len(lines[s].lstrip())
    e = len(lines)
    for j in range(s + 1, len(lines)):
        if lines[j].strip() and (len(lines[j]) - len(lines[j].lstrip())) == ind and lines[j].lstrip().startswith('def '):
            e = j
            break
    for k in range(s, e):
        print(f'{k+1:5} {lines[k].rstrip()}')
else:
    print('   پیدا نشد')
input('Enter...')