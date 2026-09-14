# -*- coding: utf-8 -*-
"""گزارش کامل تم - اجرا: python diag_theme.py"""
import os, sys, glob
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

p = os.path.join(ROOT, 'app', 'styles', 'app_style.py')
print('=' * 30, 'app_style.py', '=' * 30)
print(open(p, encoding='utf-8', errors='replace').read())

print('=' * 30, 'فایل‌های app/styles', '=' * 30)
for q in glob.glob(os.path.join(ROOT, 'app', 'styles', '*')):
    print('STYLE FILE:', os.path.basename(q), os.path.getsize(q), 'bytes')

print('=' * 30, 'توابع موجود در theme_manager فعلی', '=' * 30)
sys.path.insert(0, ROOT)
try:
    import theme_manager as tm
    print('ROOT:', [n for n in dir(tm) if not n.startswith('_')])
except Exception as e:
    print('ROOT import error:', e)
try:
    import app.styles.theme_manager as tm2
    print('app.styles:', [n for n in dir(tm2) if not n.startswith('_')])
except Exception as e:
    print('app.styles import error:', e)

print('=' * 30, 'جستجوی تعریف load_theme / apply_theme در کل پروژه', '=' * 30)
found = 0
for dp, ds, fs in os.walk(ROOT):
    if any(k in dp for k in ('.venv', '.git', '\\build', '\\dist')):
        continue
    for fn in fs:
        if fn.endswith('.py'):
            fp = os.path.join(dp, fn)
            try:
                t = open(fp, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            hits = [k for k in ('def load_theme', 'def apply_theme') if k in t]
            if hits:
                print('DEF FOUND:', os.path.relpath(fp, ROOT), hits)
                found += 1
if not found:
    print('(هیچ‌جا تعریف نشده!)')
input('Enter...')