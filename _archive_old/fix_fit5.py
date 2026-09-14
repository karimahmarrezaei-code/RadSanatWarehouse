# -*- coding: utf-8 -*-
"""اسکرول‌بار حرفه‌ای - اجرا: python fix_fit5.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

if '# SAFE-FIT-V5' not in s:
    anchor = '    _orig_show = _QW.show\n'
    helper = (
        "    def _mk_sa(wgt):  # SAFE-FIT-V5\n"
        "        from PyQt5.QtCore import Qt as _QtC  # SAFE-FIT-V5\n"
        "        sa = _QS()  # SAFE-FIT-V5\n"
        "        sa.setWidgetResizable(True)  # SAFE-FIT-V5\n"
        "        sa.setWidget(wgt)  # SAFE-FIT-V5\n"
        "        sa.setVerticalScrollBarPolicy(_QtC.ScrollBarAlwaysOn)  # SAFE-FIT-V5\n"
        "        sa.setHorizontalScrollBarPolicy(_QtC.ScrollBarAsNeeded)  # SAFE-FIT-V5\n"
        "        sa.setStyleSheet('QScrollBar:vertical{width:16px;background:#2a2f3a;}'  # SAFE-FIT-V5\n"
        "                         'QScrollBar::handle:vertical{min-height:48px;background:#7f8896;border-radius:8px;margin:3px;}'  # SAFE-FIT-V5\n"
        "                         'QScrollBar::handle:vertical:hover{background:#a8b0bc;}'  # SAFE-FIT-V5\n"
        "                         'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}')  # SAFE-FIT-V5\n"
        "        return sa  # SAFE-FIT-V5\n"
    )
    if anchor in s:
        s = s.replace(anchor, anchor + helper, 1)
        s = s.replace('                    sa = _QS(); sa.setWidgetResizable(True); sa.setWidget(cw)\n',
                      '                    sa = _mk_sa(cw)  # SAFE-FIT-V5\n', 1)
        s = s.replace('                    sa = _QS(); sa.setWidgetResizable(True); sa.setWidget(inner)\n',
                      '                    sa = _mk_sa(inner)  # SAFE-FIT-V5\n', 1)
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('1) SAFE-FIT v5 (اسکرول‌بار حرفه‌ای) اعمال شد')
else:
    print('1) از قبل بود ✔')

print('2) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق؛ اول: taskkill /f /im RadSanatWarehouse.exe'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
idata = os.path.join(DST, '_internal', 'data'); os.makedirs(idata, exist_ok=True)
for fn in os.listdir(os.path.join(ROOT, 'data')):
    if fn.endswith(('.sql', '.json', '.key')):
        shutil.copy2(os.path.join(ROOT, 'data', fn), os.path.join(idata, fn))
db = os.path.join(idata, 'app.db')
if os.path.exists(db): os.remove(db)
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
    for rel in ('theme_manager.py', os.path.join('app', 'styles', 'theme_manager.py')):
        tgt = os.path.join(DST, '_internal', rel)
        if os.path.isdir(os.path.dirname(tgt)):
            shutil.copy2(good, tgt)
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('2) تمام ✔')
print('=== تست 1366x768: دستگیرهٔ اسکرول بزرگ و روان؟ تم؟ ===')
input('Enter...')