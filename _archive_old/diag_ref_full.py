# -*- coding: utf-8 -*-
"""بازبینی کامل منطق مرجع‌ها - اجرا: python diag_ref_full.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))

def dump_func(rel, start_key, max_lines=90):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print('MISSING', rel); return
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    print('=' * 25, rel, '::', start_key, '=' * 25)
    start = None
    for i, l in enumerate(lines):
        if l.strip().startswith(start_key):
            start = i
            break
    if start is None:
        print('NOT FOUND')
        return
    ind = len(lines[start]) - len(lines[start].lstrip())
    end = min(len(lines), start + max_lines)
    for j in range(start + 1, end):
        lj = lines[j]
        if lj.strip() and (len(lj) - len(lj.lstrip())) == ind and lj.lstrip().startswith('def '):
            end = j
            break
    for k in range(start, end):
        print(f'{k+1:5} {lines[k].rstrip()}')

dump_func('app/ui/issue_manager_window.py', 'def _refresh_reference_combo')
dump_func('app/ui/issue_manager_window.py', 'def _load_lookups')

p = os.path.join(ROOT, 'app/ui', 'combo_refresh_patch.py')
print('=' * 25, 'combo_refresh_patch.py (کامل)', '=' * 25)
if os.path.exists(p):
    print(open(p, encoding='utf-8', errors='replace').read())
else:
    print('MISSING')
input('Enter...')