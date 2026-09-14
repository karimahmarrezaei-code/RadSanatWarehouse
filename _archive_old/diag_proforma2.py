# -*- coding: utf-8 -*-
"""تابع _load_pallets کامل + همه خطوط stocks/مانده - اجرا: python diag_proforma2.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(ROOT, 'app/ui/proforma_window.py')
lines = open(p, encoding='utf-8', errors='replace').read().split('\n')

s = None
for i, l in enumerate(lines):
    if l.strip().startswith('def _load_pallets'):
        s = i
        break
if s is None:
    print('❌ تابع پیدا نشد')
else:
    ind = len(lines[s]) - len(lines[s].lstrip())
    e = len(lines)
    for j in range(s + 1, len(lines)):
        if lines[j].strip() and (len(lines[j]) - len(lines[j].lstrip())) == ind and lines[j].lstrip().startswith('def '):
            e = j
            break
    print(f'=== _load_pallets کامل: خطوط {s+1} تا {e} ===')
    for k in range(s, e):
        print(f'{k+1:5} {lines[k].rstrip()}')

print()
print('=== هر خط با stocks / مانده / pallet_stock ===')
for i, l in enumerate(lines):
    if 'stocks' in l or 'مانده' in l or 'pallet_stock' in l:
        print(f'{i+1:5} {l.rstrip()}')
input('Enter...')