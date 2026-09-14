# -*- coding: utf-8 -*-
"""حذف سه مظنون رندر - اجرا: python fix_final.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

# 1) پاک کردن بلوک لاگ قبلی
if '# LOGIN-DBG3' in s:
    s = '\n'.join(l for l in s.split('\n') if not l.rstrip().endswith('# LOGIN-DBG3'))
    print('1) لاگ قبلی حذف شد')

# 2) حذف HighDpi attributes (مظنون رندر با ضریب اعشاری)
for blk in ('try:\n    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)\nexcept AttributeError:\n    pass\n',
            'try:\n    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)\nexcept AttributeError:\n    pass\n'):
    if blk in s:
        s = s.replace(blk, '')
        print('2) یک بلوک HighDpi حذف شد')

# 3) جابه‌جایی RTL: از سراسریِ قبل از لاگین → به دیالوگ و بعد از لاگین
old_rtl = '    app.setLayoutDirection(Qt.RightToLeft)\n'
if old_rtl in s:
    s = s.replace(old_rtl, '', 1)
    a = '    login_dlg = LoginWindow(db)\n'
    if a in s:
        s = s.replace(a, a + '    login_dlg.setLayoutDirection(Qt.RightToLeft)  # RTL-DLG\n', 1)
    b = '    if login_dlg.exec_() != QDialog.Accepted:\n        sys.exit(0)\n'
    if b in s:
        s = s.replace(b, b + '    app.setLayoutDirection(Qt.RightToLeft)  # RTL-AFTER-LOGIN\n', 1)
    print('3) RTL جابه‌جا شد (دیالوگ جدا، بقیه بعد از لاگین)')

open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)

# 4) بیلد + تزریق + bat بدون QT_OPENGL
print('4) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
idata = os.path.join(DST, '_internal', 'data'); os.makedirs(idata, exist_ok=True)
for fn in os.listdir(os.path.join(ROOT, 'data')):
    if fn.endswith(('.sql', '.json')):
        shutil.copy2(os.path.join(ROOT, 'data', fn), os.path.join(idata, fn))
db = os.path.join(idata, 'app.db')
if os.path.exists(db): os.remove(db)
dst_app = os.path.join(DST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn); rel = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True); shutil.copy2(src, tgt)
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.png')) and ('icon' in fn.lower() or 'rad_sanat' in fn.lower()):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, fn))
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, '_internal', fn))
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام (bat بدون QT_OPENGL)')
print('=== رزولوشن 1366x768 → run.bat → اسکرین‌شات لاگین و یک فرم ===')
input('Enter...')