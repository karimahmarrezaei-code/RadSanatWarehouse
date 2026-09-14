# -*- coding: utf-8 -*-
"""مانده زنده + آیکون لاگین + بیلد آخر - اجرا: python fix_last_breath.py"""
import os, sys, subprocess, shutil, py_compile, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 0) شفاف‌سازی دیتابیس
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
if os.path.exists(db):
    con = sqlite3.connect(db)
    for r in con.execute("SELECT id, reference_no, issued_qty_total, remaining_qty, load_status, is_active FROM outbound_loads").fetchall():
        print('   ', r)
    con.close()

# 1) مانده زنده در برچسب مرجع (هر جا که remaining از ref خوانده می‌شود)
for rel in ('app/ui/issue_manager_window.py', 'app/ui/combo_refresh_patch.py'):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    lines = open(p, encoding='utf-8').read().split('\n')
    n = 0
    for i, l in enumerate(lines):
        if '# LIVE-REM' in l:
            continue
        if 'remaining' in l and '= ref.get(' in l and 'outbound' not in l:
            ind = len(l) - len(l.lstrip())
            sp = ' ' * ind
            block = [
                sp + "try:  # LIVE-REM",
                sp + "    with self.db.connect() as _cn9:  # LIVE-REM",
                sp + "        _cn9.row_factory = None  # LIVE-REM",
                sp + "        _pl = _cn9.execute(\"SELECT COALESCE(SUM(qty),0) FROM outbound_load_items WHERE outbound_load_id=?\", (ref.get('id'),)).fetchone()[0]  # LIVE-REM",
                sp + "        _is9 = _cn9.execute(\"SELECT COALESCE(SUM(wii.qty),0) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=? AND wi.issue_status!='CANCELLED'\", (ref.get('id'),)).fetchone()[0]  # LIVE-REM",
                sp + "        remaining = int(_pl or 0) - int(_is9 or 0)  # LIVE-REM",
                sp + "except Exception:  # LIVE-REM",
                sp + "    remaining = int(ref.get('remaining_qty', 0) or 0)  # LIVE-REM",
            ]
            lines[i:i + 1] = block
            n += 1
    if n:
        open(p, 'w', encoding='utf-8').write('\n'.join(lines))
        py_compile.compile(p, doraise=True)
    print('1)', rel, 'مانده زنده:', n)

# 2) آیکون لاگین و پنجره اصلی
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
old_ico = ("    _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rad_sanat_novin.ico')\n"
           "    if os.path.exists(_ico):\n"
           "        app.setWindowIcon(QIcon(_ico))\n")
new_ico = ("    _ico = ''\n"
           "    try:\n"
           "        import glob as _gb\n"
           "        _b0 = os.path.dirname(os.path.abspath(__file__))\n"
           "        _c0 = _gb.glob(os.path.join(_b0, '*.ico')) + _gb.glob(os.path.join(_b0, '_internal', '*.ico'))\n"
           "        if _c0:\n"
           "            _ico = _c0[0]\n"
           "    except Exception:\n"
           "        pass\n"
           "    if _ico and os.path.exists(_ico):\n"
           "        app.setWindowIcon(QIcon(_ico))\n")
if old_ico in s:
    s = s.replace(old_ico, new_ico, 1)
    print('2) جستجوی آیکون ✔')
if 'login_dlg.setWindowIcon' not in s:
    old_l = '    login_dlg = LoginWindow(db)\n'
    if old_l in s:
        s = s.replace(old_l, old_l + '    try:\n        if _ico:\n            login_dlg.setWindowIcon(QIcon(_ico))\n    except Exception:\n        pass\n', 1)
        print('2) آیکون لاگین ✔')
if 'window.setWindowIcon' not in s:
    old_w = '    window = MainWindow(db, user_data)\n'
    if old_w in s:
        s = s.replace(old_w, old_w + '    try:\n        if _ico:\n            window.setWindowIcon(QIcon(_ico))\n    except Exception:\n        pass\n', 1)
        print('2) آیکون پنجره اصلی ✔')
open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)

# 3) بیلد با محافظ داده
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
    shutil.copy2(keep, db)
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')