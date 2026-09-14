# -*- coding: utf-8 -*-
"""تزریق schema + استایل‌ها به داخل dist - اجرا: python fix_dist_complete.py"""
import os, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')

# 1) schema و json ها → _internal\data
idata = os.path.join(DIST, '_internal', 'data')
os.makedirs(idata, exist_ok=True)
n1 = 0
for fn in os.listdir(os.path.join(ROOT, 'data')):
    if fn.endswith(('.sql', '.json')):
        shutil.copy2(os.path.join(ROOT, 'data', fn), os.path.join(idata, fn))
        n1 += 1
db = os.path.join(idata, 'app.db')
if os.path.exists(db):
    os.remove(db)
print('✔ schema/json در _internal\\data :', n1)

# 2) استایل‌ها و داده‌ها → _internal\app
dst_app = os.path.join(DIST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql')
n2 = 0
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn)
            rel = os.path.relpath(src, os.path.join(ROOT, 'app'))
            tgt = os.path.join(dst_app, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            shutil.copy2(src, tgt)
            n2 += 1
print('✔ استایل/داده در _internal\\app :', n2)

# 3) آیکن و فایل‌های ریشه
n3 = 0
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.qss')):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DIST, fn))
        n3 += 1
print('✔ فایل ریشه :', n3)

# 4) run.bat
with open(os.path.join(DIST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('✔ run.bat')

print('\n=== شبیه‌سازی در همین PC ===')
print('اجرا کنید: dist\\RadSanatWarehouse\\run.bat')
input('Enter...')