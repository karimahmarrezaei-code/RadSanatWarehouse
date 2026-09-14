# -*- coding: utf-8 -*-
"""حذف COMPACT4 + داشبورد جمع‌تر + نگهدار app.db - اجرا: python fix_revert4_dash.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) حذف COMPACT4 از main.py
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
for bad in ("                    elif 60 < w.minimumHeight() < 400:  # COMPACT4\n"
            "                        w.setMinimumHeight(int(w.minimumHeight() * 0.75))  # COMPACT4\n"
            "                        if w.maximumHeight() < 10000:  # COMPACT4\n"
            "                            w.setMaximumHeight(int(w.maximumHeight() * 0.75))  # COMPACT4\n",
            "                        new = _re2.sub(r'min-height:\\s*(\\d+)px', lambda m: f'min-height: {max(30, int(int(m.group(1)) * 0.75))}px', new)  # COMPACT4\n"):
    s = s.replace(bad, '')
open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)
print('1) COMPACT4 حذف شد ✔')

# 2) داشبورد جمع‌تر در منبع
mw = os.path.join(ROOT, 'app', 'ui', 'main_window.py')
t = open(mw, encoding='utf-8').read()
t = t.replace('setMinimumHeight(84)', 'setMinimumHeight(70)')
t = t.replace('setMaximumHeight(120)', 'setMaximumHeight(95)')
t = t.replace('setMinimumHeight(90); self.', 'setMinimumHeight(75); self.')
t = t.replace('.setMaximumHeight(110)', '.setMaximumHeight(90)')
open(mw, 'w', encoding='utf-8').write(t)
py_compile.compile(mw, doraise=True)
print('2) داشبورد جمع‌تر شد ✔')

# 3) نگهدار app.db قبل از بیلد
db_dist = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
    print('3) کپی امن app.db گرفته شد ✔')

print('4) بیلد...')
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
# بازگرداندن app.db
if os.path.exists(keep):
    os.makedirs(os.path.join(DST, '_internal', 'data'), exist_ok=True)
    shutil.copy2(keep, db_dist)
    print('4) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('5) تمام ✔')
input('Enter...')