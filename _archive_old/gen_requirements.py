# -*- coding: utf-8 -*-
"""ساخت requirements.txt با نسخه‌های دقیق - اجرا: python gen_requirements.py"""
import importlib.metadata as md

pkgs = ['PyQt5', 'PyQtWebEngine', 'reportlab', 'Pillow', 'numpy', 'openpyxl', 'matplotlib']
lines = []
for p in pkgs:
    try:
        v = md.version(p)
        lines.append('{}=={}'.format(p, v))
        print('✔', p, v)
    except Exception:
        print('⚠ نصب نیست (رد شد):', p)

with open('requirements.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('\n✔ requirements.txt ساخته شد:')
print(open('requirements.txt', encoding='utf-8').read())
input('Enter...')