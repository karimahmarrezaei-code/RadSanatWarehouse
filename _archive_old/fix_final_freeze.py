# -*- coding: utf-8 -*-
"""عرض کامبو در همه فرم‌ها + بیلد نهایی - اجرا: python fix_final_freeze.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# COL-WIDTH2' not in s:
    anchor = "                except Exception as _re:  # ROW-GUARD\n"
    i = s.find(anchor)
    if i != -1:
        j = s.find('pass  # ROW-GUARD\n', i)
        j = s.find('\n', j) + 1
        block = (
            "                try:  # COL-WIDTH2\n"
            "                    from PyQt5.QtWidgets import QTableWidget as _QTBL2, QHeaderView as _QHV2, QComboBox as _QCB2  # COL-WIDTH2\n"
            "                    for _tb in self.findChildren(_QTBL2):  # COL-WIDTH2\n"
            "                        try:  # COL-WIDTH2\n"
            "                            if isinstance(_tb.cellWidget(0, 1), _QCB2) or _tb is getattr(self, 'lines_table', None) or _tb is getattr(self, 'items_table', None):  # COL-WIDTH2\n"
            "                                _tb.horizontalHeader().setSectionResizeMode(1, _QHV2.Fixed)  # COL-WIDTH2\n"
            "                                _tb.setColumnWidth(1, 430)  # COL-WIDTH2\n"
            "                        except Exception:  # COL-WIDTH2\n"
            "                            pass  # COL-WIDTH2\n"
            "                except Exception:  # COL-WIDTH2\n"
            "                    pass  # COL-WIDTH2\n"
        )
        s = s[:j] + block + s[j:]
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('1) COL-WIDTH2 نصب شد ✔')
else:
    print('1) از قبل بود ✔')

db_dist = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
print('2) بیلد...')
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
    print('2) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('3) بیلد نهایی تمام ✔')
input('Enter...')
