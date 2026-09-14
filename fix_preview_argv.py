# -*- coding: utf-8 -*-
"""خواندن همه‌فن‌حریف --preview - اجرا: python fix_preview_argv.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

mp = os.path.join(ROOT, 'main.py')
lines = open(mp, encoding='utf-8').read().split('\n')
s = None
for i, l in enumerate(lines):
    if "'--preview' in sys.argv" in l and l.lstrip().startswith('if'):
        s = i
        break
e = None
if s is not None:
    for j in range(s + 1, min(len(lines), s + 60)):
        if lines[j].strip().startswith('sys.exit('):
            e = j
            break
if s is None or e is None:
    print('❌ بلوک --preview پیدا نشد'); input(); raise SystemExit
print('1) بلوک قبلی خطوط', s + 1, 'تا', e + 1)
block = [
    "    if '--preview' in sys.argv:  # ARGV-FIX",
    "        _html = ''  # ARGV-FIX",
    "        _title = 'پیش‌نمایش سند'  # ARGV-FIX",
    "        _args = sys.argv[sys.argv.index('--preview') + 1:]  # ARGV-FIX",
    "        for _a in _args:  # ARGV-FIX",
    "            try:  # ARGV-FIX",
    "                if not _html and os.path.exists(_a) and _a.lower().endswith(('.html', '.htm', '.txt')):  # ARGV-FIX",
    "                    with open(_a, encoding='utf-8', errors='replace') as _f:  # ARGV-FIX",
    "                        _html = _f.read()  # ARGV-FIX",
    "                elif not _html and '<' in _a and '>' in _a:  # ARGV-FIX",
    "                    _html = _a  # ARGV-FIX",
    "                elif '<' not in _a and not _a.lower().endswith(('.html', '.htm', '.txt')) and len(_a) < 200:  # ARGV-FIX",
    "                    _title = _a  # ARGV-FIX",
    "            except Exception:  # ARGV-FIX",
    "                pass  # ARGV-FIX",
    "        if not _html:  # ARGV-FIX",
    "            for _a in _args:  # ARGV-FIX",
    "                try:  # ARGV-FIX",
    "                    if os.path.exists(_a):  # ARGV-FIX",
    "                        with open(_a, encoding='utf-8', errors='replace') as _f:  # ARGV-FIX",
    "                            _html = _f.read()  # ARGV-FIX",
    "                            break  # ARGV-FIX",
    "                except Exception:  # ARGV-FIX",
    "                    pass  # ARGV-FIX",
    "        _app = QApplication(sys.argv)  # ARGV-FIX",
    "        try:  # ARGV-FIX",
    "            from app.ui.theme_manager import apply_theme as _at  # ARGV-FIX",
    "            _at(_app)  # ARGV-FIX",
    "        except Exception:  # ARGV-FIX",
    "            pass  # ARGV-FIX",
    "        from app.ui.html_preview_dialog import HtmlPreviewDialog  # ARGV-FIX",
    "        _d = HtmlPreviewDialog(_html, _title)  # ARGV-FIX",
    "        _d.exec_()  # ARGV-FIX",
    "        sys.exit(0)  # ARGV-FIX",
]
lines[s:e + 1] = block
open(mp, 'w', encoding='utf-8').write('\n'.join(lines))
py_compile.compile(mp, doraise=True)
print('2) بلوک جدید نصب شد ✔')

# بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
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
            src = os.path.join(dp, fn); rel2 = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel2)
            os.makedirs(os.path.dirname(tgt), exist_ok=True); shutil.copy2(src, tgt)
if os.path.exists(keep):
    os.makedirs(os.path.join(DST, '_internal', 'data'), exist_ok=True)
    shutil.copy2(keep, db)
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')