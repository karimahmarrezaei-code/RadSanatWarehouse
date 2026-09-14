# -*- coding: utf-8 -*-
"""یافتن سه نقطهٔ گم‌شده - اجرا: python diag_four.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))

def find(term):
    out = []
    for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
        for fn in fs:
            if fn.endswith('.py'):
                p = os.path.join(dp, fn)
                try:
                    t = open(p, encoding='utf-8', errors='replace').read()
                except Exception:
                    continue
                if term in t:
                    out.append(p)
    return out

def dump(p, term, after=30, max_hits=2):
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    print('=' * 25, os.path.relpath(p, ROOT), '=' * 25)
    hits = 0
    for i, l in enumerate(lines):
        if term in l:
            for j in range(max(0, i - 3), min(len(lines), i + after)):
                print(f'{j+1:5} {lines[j].rstrip()}')
            print('-' * 50)
            hits += 1
            if hits >= max_hits:
                break

print('##### الف) سازندهٔ پیش‌نمایش سند ثبت‌شده #####')
for p in find('سند ثبت‌شده')[:2]:
    dump(p, 'سند ثبت‌شده')

print('##### ب) فرمتِ نمایشِ موجودی آزاد در کامبو #####')
for p in find('موجودی آزاد')[:2]:
    dump(p, 'موجودی آزاد', after=12)

print('##### ج) درج و تولید شماره مرجع #####')
for p in find('INSERT INTO outbound_loads')[:2]:
    dump(p, 'INSERT INTO outbound_loads', after=25)
input('Enter...')