# -*- coding: utf-8 -*-
"""پیدا کردن کد واقعی لاگین و خط‌های اندازهٔ آن - اجرا: python diag_login2.py"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
cands = [
    os.path.join(ROOT, 'app', 'ui', 'login_window.py'),
    os.path.join(ROOT, 'app', 'ui', 'ui', 'login_window.py'),
    os.path.join(ROOT, 'ui_patch_work', 'ui', 'login_window.py'),
    os.path.join(ROOT, 'ui', 'login_window.py'),
]
keys = ('resize', 'Fixed', 'Geometry', 'geometry', 'screen', 'Screen',
        'move(', 'Pixmap', 'pixmap', 'setWindowFlag', 'exec')
for p in cands:
    if not os.path.exists(p):
        continue
    print('=' * 70)
    print('FILE:', os.path.relpath(p, ROOT), '-', os.path.getsize(p), 'bytes')
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    print('TOTAL LINES:', len(lines))
    print('--- 15 خط اول فایل (برای دیدن پوسته یا واقعی بودن) ---')
    for i, l in enumerate(lines[:15]):
        print('{:5} {}'.format(i + 1, l.rstrip()))
    print('--- خط‌های مربوط به اندازه/صفحه/اجرا ---')
    n = 0
    for i, l in enumerate(lines):
        if any(k in l for k in keys):
            print('{:5} {}'.format(i + 1, l.rstrip()))
            n += 1
    print('MATCHES:', n)
input('Enter...')