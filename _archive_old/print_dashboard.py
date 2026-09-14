# -*- coding: utf-8 -*-
"""یافتن کد کارت‌های داشبورد - اجرا: python print_dashboard.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
keys = ('Height', 'height', 'font-size', 'setMinimum', 'setFixed',
        'Card', 'Spacing', 'spacing', 'Margins', 'margins', 'setFont', 'PointSize')
targets = []
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith('.py'):
            p = os.path.join(dp, fn)
            try:
                t = open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            if ('داشبورد مدیریتی' in t) or ('رسیدهای باز' in t and 'پالت‌های فعال' in t):
                targets.append(p)
print('TARGET FILES:', [os.path.relpath(t, ROOT) for t in targets])
for p in targets:
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    print('=' * 70)
    print('FILE:', os.path.relpath(p, ROOT), '| lines:', len(lines))
    n = 0
    for i, l in enumerate(lines):
        if any(k in l for k in keys):
            print('{:5} {}'.format(i + 1, l.rstrip()))
            n += 1
            if n > 70:
                print('... (بقیه بریده شد)')
                break
input('Enter...')