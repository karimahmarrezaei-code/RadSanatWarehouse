# -*- coding: utf-8 -*-
"""دیدن تابع محاسبه موجودی - اجرا: python diag_stock.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))

def dump(rel, key, after=28, hits=2):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print('MISSING', rel); return
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    print('=' * 25, rel, '=' * 25)
    n = 0
    for i, l in enumerate(lines):
        if key in l:
            for j in range(i, min(len(lines), i + after)):
                print(f'{j+1:5} {lines[j].rstrip()}')
            print('-' * 50)
            n += 1
            if n >= hits:
                break

dump('app/ui/issue_manager_window.py', 'def _stock_for_warehouse')
dump('app/ui/receipt_manager_window.py', 'def _stock_for_warehouse')
dump('app/services/pallet_service.py', 'def reload')
dump('app/services/pallet_service.py', 'stock')
input('Enter...')