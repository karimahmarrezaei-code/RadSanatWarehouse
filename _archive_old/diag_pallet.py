# -*- coding: utf-8 -*-
"""بررسی دقیق کامبو و فرم پالت - اجرا: python diag_pallet.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))

print('=== فایل‌های دارای pallet_combo ===')
files = []
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app', 'ui')):
    for fn in fs:
        if fn.endswith('.py'):
            p = os.path.join(dp, fn)
            if 'pallet_combo' in open(p, encoding='utf-8', errors='replace').read():
                files.append(p)
                print(' -', os.path.relpath(p, ROOT))

for p in files[:4]:
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    print('=' * 25, os.path.relpath(p, ROOT), '=' * 25)
    n = 0
    for i, l in enumerate(lines):
        if 'pallet_combo' in l:
            for j in range(max(0, i - 3), min(len(lines), i + 4)):
                mark = '>>' if j == i else '  '
                print(f'{mark}{j+1:5} {lines[j].rstrip()}')
            print('-' * 40)
            n += 1
            if n > 20:
                break

print('=' * 25, 'فرم پالت: ورودی‌ها و جدول', '=' * 25)
p = os.path.join(ROOT, 'app', 'ui', 'pallets_window.py')
if os.path.exists(p):
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    n = 0
    for i, l in enumerate(lines):
        if any(k in l for k in ('QSpinBox', 'setMaximum', 'setMinimum',
                                'HorizontalHeader', 'columnCount', 'length_cm', 'width_cm', 'height_cm')):
            print(f'{i+1:5} {l.rstrip()}')
            n += 1
            if n > 40:
                break
input('Enter...')