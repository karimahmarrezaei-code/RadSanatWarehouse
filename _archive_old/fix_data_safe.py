# -*- coding: utf-8 -*-
"""دیتا امن + فونت کامبو + تشخیص نگاشت پالت - اجرا: python fix_data_safe.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 0) چاپ کدهای نگاشت پالت (برای پچ نهایی ترتیب)
for rel, keys in (('app/ui/issue_manager_window.py', ('self.pallets =',)),
                  ('app/ui/pallets_window.py', ("'code':", 'code_edit', 'dimensions'))):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    print('=' * 25, rel, '=' * 25)
    n = 0
    for i, l in enumerate(lines):
        if any(k in l for k in keys):
            for j in range(max(0, i - 2), min(len(lines), i + 8)):
                print(f'{j+1:5} {lines[j].rstrip()}')
            print('-' * 40)
            n += 1
            if n > 8:
                break

# 1) فونت کوچک‌تر کامبوهای داخل جدول
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# FONT-COMBO' not in s:
    anchor = '        apply_style(app)\n'
    add = ("        try:  # FONT-COMBO\n"
           "            app.setStyleSheet(app.styleSheet() + ' QTableWidget QComboBox { font-size: 12px; } ')  # FONT-COMBO\n"
           "        except Exception:  # FONT-COMBO\n"
           "            pass  # FONT-COMBO\n")
    if anchor in s:
        s = s.replace(anchor, anchor + add, 1)
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('1) FONT-COMBO اضافه شد ✔')
else:
    print('1) از قبل بود ✔')

# 2) بیلد + تزریق — بدون حذف app.db (دیتا امن)
print('2) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق؛ اول: taskkill /f /im RadSanatWarehouse.exe'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
idata = os.path.join(DST, '_internal', 'data'); os.makedirs(idata, exist_ok=True)
for fn in os.listdir(os.path.join(ROOT, 'data')):
    if fn.endswith(('.sql', '.json', '.key')):
        shutil.copy2(os.path.join(ROOT, 'data', fn), os.path.join(idata, fn))
dst_app = os.path.join(DST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql', '.py')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn); rel = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True); shutil.copy2(src, tgt)
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.png')) and ('icon' in fn.lower() or 'rad_sanat' in fn.lower()):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, fn))
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, '_internal', fn))
good = os.path.join(ROOT, 'theme_manager.py')
if os.path.exists(good):
    for tgt in (os.path.join(DST, 'theme_manager.py'),
                os.path.join(DST, '_internal', 'theme_manager.py'),
                os.path.join(DST, '_internal', 'app', 'styles', 'theme_manager.py')):
        if os.path.isdir(os.path.dirname(tgt)):
            shutil.copy2(good, tgt)
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('2) تمام ✔ (app.db حذف نشد)')
input('Enter...')