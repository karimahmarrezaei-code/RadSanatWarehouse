# -*- coding: utf-8 -*-
"""لاگ خودکار هندسه لاگین از exe فریزن - اجرا: python fix_bootlog3.py (رزولوشن 1366x768 بماند)"""
import os, sys, subprocess, shutil, time, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

# حذف بلوک قدیمی LOGIN-DBG اگر هست
if '# LOGIN-DBG' in s and '# LOGIN-DBG3' not in s:
    s = '\n'.join(l for l in s.split('\n') if not l.rstrip().endswith('# LOGIN-DBG'))
    print('0) بلوک قدیمی حذف شد')

if '# LOGIN-DBG3' not in s:
    anchor = '    login_dlg.setMinimumSize(620, 500)  # LOGIN-FIX2'
    if anchor not in s:
        print('❌ anchor پیدا نشد'); input(); raise SystemExit
    block = anchor + '\n' + (
        "    import os as _o3, sys as _s3  # LOGIN-DBG3\n"
        "    def _dbg3(tag):  # LOGIN-DBG3\n"
        "        try:  # LOGIN-DBG3\n"
        "            _base = _o3.path.dirname(_s3.executable) if getattr(_s3, 'frozen', False) else _o3.getcwd()  # LOGIN-DBG3\n"
        "            with open(_o3.path.join(_base, 'BOOT_LOG.txt'), 'a', encoding='utf-8') as _f3:  # LOGIN-DBG3\n"
        "                _f3.write(tag + ' env=' + str(_o3.environ.get('QT_SCALE_FACTOR')) + ' window=' + str(login_dlg.geometry()) + ' dpr=' + str(login_dlg.devicePixelRatioF()) + '\\n')  # LOGIN-DBG3\n"
        "                for _c in login_dlg.findChildren(object):  # LOGIN-DBG3\n"
        "                    _n = type(_c).__name__  # LOGIN-DBG3\n"
        "                    if hasattr(_c, 'geometry') and not _n.endswith('Layout'):  # LOGIN-DBG3\n"
        "                        _f3.write('   ' + _n + ' ' + _c.objectName() + ' ' + str(_c.geometry()) + '\\n')  # LOGIN-DBG3\n"
        "        except Exception:  # LOGIN-DBG3\n"
        "            pass  # LOGIN-DBG3\n"
        "    try:  # LOGIN-DBG3\n"
        "        _b0 = _o3.path.dirname(_s3.executable) if getattr(_s3, 'frozen', False) else _o3.getcwd()  # LOGIN-DBG3\n"
        "        _o3.remove(_o3.path.join(_b0, 'BOOT_LOG.txt'))  # LOGIN-DBG3\n"
        "    except Exception:  # LOGIN-DBG3\n"
        "        pass  # LOGIN-DBG3\n"
        "    from PyQt5.QtCore import QTimer as _QT3  # LOGIN-DBG3\n"
        "    _QT3.singleShot(1200, lambda: _dbg3('AFTER-SHOW'))  # LOGIN-DBG3\n"
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

# 3) اجرای خودکار exe و خواندن لاگ
exe = os.path.join(DST, 'RadSanatWarehouse.exe')
print('3) exe:', time.ctime(os.path.getmtime(exe)))
p = subprocess.Popen([exe], cwd=DST)
time.sleep(6)
try:
    p.kill()
except Exception:
    pass
lg = os.path.join(DST, 'BOOT_LOG.txt')
print('=== BOOT_LOG.txt ===')
print(open(lg, encoding='utf-8', errors='replace').read() if os.path.exists(lg) else '(ساخته نشد!)')
input('Enter...')
