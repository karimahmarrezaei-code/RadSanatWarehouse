# -*- coding: utf-8 -*-
"""نگهبان ردیف + پلهٔ آخر داشبورد - اجرا: python fix_row_dash5.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) ROW-GUARD در main.py
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# ROW-GUARD' not in s:
    anchor = '                _compact(self)  # COMPACT-UI\n'
    guard = (
        "                try:  # ROW-GUARD\n"
        "                    lt = getattr(self, 'lines_table', None)  # ROW-GUARD\n"
        "                    if lt is not None and lt.rowCount() == 0 and callable(getattr(self, 'add_line_row', None)):  # ROW-GUARD\n"
        "                        self.add_line_row()  # ROW-GUARD\n"
        "                except Exception as _re:  # ROW-GUARD\n"
        "                    try:  # ROW-GUARD\n"
        "                        import traceback as _tb3  # ROW-GUARD\n"
        "                        with open('ROW_ERROR.txt', 'a', encoding='utf-8') as _f3:  # ROW-GUARD\n"
        "                            _f3.write(_tb3.format_exc())  # ROW-GUARD\n"
        "                    except Exception:  # ROW-GUARD\n"
        "                        pass  # ROW-GUARD\n"
    )
    if anchor in s:
        s = s.replace(anchor, anchor + guard, 1)
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('1) ROW-GUARD نصب شد ✔')
else:
    print('1) از قبل بود ✔')

# 2) پلهٔ آخر داشبورد
mw = os.path.join(ROOT, 'app', 'ui', 'main_window.py')
t = open(mw, encoding='utf-8').read()
t = t.replace('setMinimumHeight(70)', 'setMinimumHeight(60)')
t = t.replace('setMaximumHeight(95)', 'setMaximumHeight(80)')
t = t.replace('setMinimumHeight(75); self.', 'setMinimumHeight(65); self.')
t = t.replace('.setMaximumHeight(90)', '.setMaximumHeight(78)')
open(mw, 'w', encoding='utf-8').write(t)
py_compile.compile(mw, doraise=True)
print('2) داشبورد پلهٔ آخر ✔')

# 3) بیلد با محافظ داده
db_dist = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
print('3) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('❌ بیلد ناموفق'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
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
if os.path.exists(keep):
    os.makedirs(os.path.join(DST, '_internal', 'data'), exist_ok=True)
    shutil.copy2(keep, db_dist)
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')