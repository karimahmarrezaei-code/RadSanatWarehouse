# -*- coding: utf-8 -*-
"""یافتن سازندهٔ واقعی چاپ - اجرا: python diag_print2.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))

p = os.path.join(ROOT, 'app', 'repositories', 'issue_repository.py')
lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
tgt = None
for i, l in enumerate(lines):
    if 'total_load_qty=int(context.get(' in l:
        tgt = i
        break
print('=== خط kwargs:', tgt + 1 if tgt is not None else None, '===')
if tgt is not None:
    di = None
    for i in range(tgt, -1, -1):
        if lines[i].lstrip().startswith('def '):
            di = i
            break
    print('--- تابع سازنده:', lines[di].strip()[:100], '(خط', di + 1, ') ---')
    for j in range(di, min(len(lines), di + 30)):
        print(f'{j+1:5} {lines[j].rstrip()}')
    print('--- 12 خط قبل از kwargs ---')
    for j in range(max(0, tgt - 12), tgt + 3):
        print(f'{j+1:5} {lines[j].rstrip()}')

print()
for rel in ('app/ui/issue_manager_window.py',):
    q = os.path.join(ROOT, rel)
    ls = open(q, encoding='utf-8', errors='replace').read().split('\n')
    print('===', rel, ': delivered_qty / context ===')
    n = 0
    for i, l in enumerate(ls):
        if 'delivered_qty' in l or "'total_load_qty'" in l:
            for j in range(max(0, i - 3), min(len(ls), i + 4)):
                print(f'{j+1:5} {ls[j].rstrip()}')
            print('-' * 40)
            n += 1
            if n >= 4:
                break
input('Enter...')