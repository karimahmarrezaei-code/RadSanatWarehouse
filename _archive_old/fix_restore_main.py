# -*- coding: utf-8 -*-
"""بازیابی main.py سالم از گیت + WIN-BTN - اجرا: python fix_restore_main.py"""
import os, subprocess, sys, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py')
cur = open(mp, encoding='utf-8', errors='replace').read()
print('0) main فعلی آلوده به app.views؟', 'app.views' in cur)

r = subprocess.run(['git', 'show', 'HEAD:main.py'], capture_output=True, text=True)
if r.returncode != 0 or 'SAFE-FIT' not in r.stdout:
    print('❌ نسخهٔ گیت مناسب نیست:', (r.stderr or '')[:200]); input(); raise SystemExit
s = r.stdout

if '# WIN-BTN' not in s:
    anchor = '    def _safe_show(self):\n'
    helper = (
        "    def _safe_flags(self):  # WIN-BTN\n"
        "        try:  # WIN-BTN\n"
        "            from PyQt5.QtCore import Qt as _QtC2  # WIN-BTN\n"
        "            f = self.windowFlags()  # WIN-BTN\n"
        "            f |= _QtC2.Window | _QtC2.WindowMaximizeButtonHint | _QtC2.WindowMinimizeButtonHint  # WIN-BTN\n"
        "            f &= ~_QtC2.WindowContextHelpButtonHint  # WIN-BTN\n"
        "            if f != self.windowFlags():  # WIN-BTN\n"
        "                self.setWindowFlags(f)  # WIN-BTN\n"
        "            if self.minimumSize() == self.maximumSize():  # WIN-BTN\n"
        "                self.setMaximumSize(16777215, 16777215)  # WIN-BTN\n"
        "        except Exception:  # WIN-BTN\n"
        "            pass  # WIN-BTN\n"
    )
    s = s.replace(anchor, helper + anchor, 1)
    s = s.replace('                self._safe_done = True\n',
                  '                self._safe_done = True\n                _safe_flags(self)  # WIN-BTN\n', 1)
    print('1) WIN-BTN دوباره اضافه شد')

open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)
print('2) main.py سالم بازیابی شد ✔')

print('3) بیلد...')
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
    for tgt in (os.path.join(DST, 'theme_manager.py'),
                os.path.join(DST, '_internal', 'theme_manager.py'),
                os.path.join(DST, '_internal', 'app', 'styles', 'theme_manager.py')):
        if os.path.isdir(os.path.dirname(tgt)):
            shutil.copy2(good, tgt)
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('3) تمام ✔')
print('=== تست: 1366x768 → run.bat ===')
input('Enter...')