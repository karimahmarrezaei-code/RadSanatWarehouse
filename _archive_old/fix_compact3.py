# -*- coding: utf-8 -*-
"""فشرده‌سازی مرحلهٔ دوم - اجرا: python fix_compact3.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

if '# COMPACT3' not in s:
    # 1) تقویت COMPACT_QSS: فونت 11 + سقف ارتفاع‌ها + پدینگ کارت
    a = s.find('COMPACT_QSS = """')
    b = s.find('"""  # COMPACT-QSS')
    if a != -1 and b != -1:
        block = s[a:b]
        block = block.replace('12px', '11px')
        block += ('QFrame#Card { padding: 6px; }  # COMPACT3\n'
                  'QTabBar::tab { max-height: 24px; }  # COMPACT3\n'
                  'QPushButton { max-height: 28px; }  # COMPACT3\n'
                  'QLineEdit, QComboBox, QSpinBox, QDateEdit { max-height: 26px; }  # COMPACT3\n')
        s = s[:a] + block + s[b:]
    # 2) ضریب‌های محکم‌تر در _compact
    s = s.replace('* 0.78)', '* 0.68)')          # ارتفاع‌های ثابت
    s = s.replace('* 0.6)', '* 0.45)')           # حاشیه‌های چیدمان
    s = s.replace('spacing() * 0.6)', 'spacing() * 0.5)')
    s = s.replace('* 0.8))}px', '* 0.75))}px')   # فونت‌های درون‌ویجتی
    open(mp, 'w', encoding='utf-8').write(s)
    py_compile.compile(mp, doraise=True)
    print('1) COMPACT3 اعمال شد ✔')
else:
    print('1) از قبل بود ✔')

print('2) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('❌ بیلد ناموفق؛ اول: taskkill /f /im RadSanatWarehouse.exe'); input(); raise SystemExit
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
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('2) تمام ✔')
input('Enter...')
