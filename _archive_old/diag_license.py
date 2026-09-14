# -*- coding: utf-8 -*-
"""نگاه به داخل سیستم لایسنس - اجرا: python diag_license.py"""
import os, glob
ROOT = os.path.dirname(os.path.abspath(__file__))

lm = os.path.join(ROOT, 'app', 'core', 'license_manager.py')
if os.path.exists(lm):
    print('=' * 60)
    print('FILE:', lm, os.path.getsize(lm), 'bytes')
    print(open(lm, encoding='utf-8', errors='replace').read())
else:
    print('license_manager.py پیدا نشد!')

pats = [
    os.path.join(ROOT, 'data', '*license*'),
    os.path.join(ROOT, 'data', '*.key'),
    os.path.join(ROOT, '*license*'),
    os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', '*license*'),
    os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', '*.key'),
]
for pat in pats:
    for p in glob.glob(pat):
        if os.path.isfile(p):
            print('=' * 60)
            print('KEY FILE:', p)
            try:
                print(open(p, encoding='utf-8', errors='replace').read()[:1500])
            except Exception as e:
                print('read error:', e)
input('Enter...')