# -*- coding: utf-8 -*-
"""دیدن تابع چاپ حواله - اجرا: python diag_print.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
targets = []
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith('.py'):
            p = os.path.join(dp, fn)
            try:
                t = open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            if 'تعداد کل بار' in t:
                targets.append(p)
for p in targets[:2]:
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    print('=' * 25, os.path.relpath(p, ROOT), '=' * 25)
    n = 0
    for i, l in enumerate(lines):
        if 'تعداد کل بار' in l or 'تحویل به انبار' in l:
            for j in range(max(0, i - 8), min(len(lines), i + 40)):
                print(f'{j+1:5} {lines[j].rstrip()}')
            print('-' * 50)
            n += 1
            if n >= 2:
                break
input('Enter...')