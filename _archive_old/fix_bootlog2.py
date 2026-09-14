# -*- coding: utf-8 -*-
"""لاگ هندسه لاگین در نسخه فریزن - اجرا: python fix_bootlog2.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# LOGIN-DBG' not in s:
    anchor = '    login_dlg.setMinimumSize(620, 500)  # LOGIN-FIX2'
    if anchor not in s:
        print('anchor not found'); input(); raise SystemExit
    block = anchor + '\n' + (
        "    from PyQt5.QtCore import QTimer  # LOGIN-DBG\n"
        "    def _dump_login():  # LOGIN-DBG\n"
        "        try:  # LOGIN-DBG\n"
        "            import sys as _s2, os as _o2  # LOGIN-DBG\n"
        "            _base = _o2.path.dirname(_s2.executable) if getattr(_s2, 'frozen', False) else _o2.getcwd()  # LOGIN-DBG\n"
        "            with open(_o2.path.join(_base, 'BOOT_LOG.txt'), 'w', encoding='utf-8') as _f2:  # LOGIN-DBG\n"
        "                _f2.write('env %s\\n' % _o2.environ.get('QT_SCALE_FACTOR'))  # LOGIN-DBG\n"
        "                _f2.write('window %s dpr %s\\n' % (login_dlg.geometry(), login_dlg.devicePixelRatioF()))  # LOGIN-DBG\n"
        "                for _c in login_dlg.findChildren(object):  # LOGIN-DBG\n"
        "                    _n = type(_c).__name__  # LOGIN-DBG\n"
        "                    if hasattr(_c, 'geometry') and not _n.endswith('Layout'):  # LOGIN-DBG\n"
        "                        _f2.write('%s %s %s\\n' % (_n, _c.objectName(), _c.geometry()))  # LOGIN-DBG\n"
        "        except Exception:  # LOGIN-DBG\n"
        "            pass  # LOGIN-DBG\n"
        "    QTimer.singleShot(700, _dump_login)  # LOGIN-DBG\n"
    )
    s = s.replace(anchor, block, 1)
    open(mp, 'w', encoding='utf-8').write(s); py_compile.compile(mp, doraise=True)
    print('1) لاگ کاشته شد')
print('2) بیلد...')
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
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\nset QT_OPENGL=software\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('2) تمام')
input('Enter...')
