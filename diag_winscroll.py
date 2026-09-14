# -*- coding: utf-8 -*-
"""دیدن بلوک‌های WIN-SCROLL - اجرا: python diag_winscroll.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
targets = ['main.py']
for fn in os.listdir(os.path.join(ROOT, 'app', 'ui')):
    if fn.endswith('.py'):
        targets.append(os.path.join('app', 'ui', fn))
for rel in targets:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    hits = [i for i, l in enumerate(lines) if 'WIN-SCROLL' in l]
    if not hits:
        continue
    print('=' * 20, rel, f'({len(hits)} نشان)', '=' * 20)
    shown = 0
    for i in hits:
        if shown >= 3:
            break
        for j in range(max(0, i - 12), min(len(lines), i + 18)):
            print(f'{j+1:5} {lines[j].rstrip()}')
        print('-' * 50)
        shown += 1
input('Enter...')