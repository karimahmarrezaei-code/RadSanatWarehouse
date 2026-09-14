# -*- coding: utf-8 -*-
"""لاگین با اندازه فیزیکی ثابت در هر رزولوشن - اجرا: python fix_login_final.py"""
import os, sys, subprocess, shutil, py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# 1) هر دو نسخهٔ login_window: حداقلِ عرض درست شود
for rel in (os.path.join('app', 'ui', 'login_window.py'),
            os.path.join('app', 'ui', 'ui', 'login_window.py')):
    p = os.path.join(ROOT, rel)
    if os.path.exists(p):
        t = open(p, encoding='utf-8').read()
        if 'setMinimumWidth(430)' in t:
            t = t.replace('self.setMinimumWidth(430)', 'self.setMinimumWidth(520)')
            open(p, 'w', encoding='utf-8').write(t)
            py_compile.compile(p, doraise=True)
            print('1) درست شد:', rel)

# 2) main.py: جبران ضریب برای لاگین (اندازه فیزیکی ثابت)
mp = os.path.join(ROOT, 'main.py')
s = open(mp, encoding='utf-8').read()
old = '    login_dlg.setMinimumSize(620, 470)  # LOGIN-MIN'
new = (
    "    try:\n"
    "        _f = float(os.environ.get('QT_SCALE_FACTOR') or 1.0)\n"
    "    except Exception:\n"
    "        _f = 1.0\n"
    "    if _f and _f != 1.0:  # LOGIN-FIX: اندازه فیزیکی ثابت در هر صفحه\n"
    "        login_dlg.setMinimumSize(int(520 / _f), int(470 / _f))\n"
    "        login_dlg.resize(int(560 / _f), int(500 / _f))\n"
    "    else:\n"
    "        login_dlg.setMinimumSize(520, 470)\n"
)
if old in s:
    s = s.replace(old, new, 1)
    open(mp, 'w', encoding='utf-8').write(s)
    py_compile.compile(mp, doraise=True)
    print('2) LOGIN-FIX اضافه شد')
else:
    print('2) ⚠ خط LOGIN-MIN پیدا نشد؛ دستی بررسی کنید')

# 3) بیلد + تزریق + bat ها
print('3) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق'); input('Enter...'); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
idata = os.path.join(DST, '_internal', 'data')
os.makedirs(idata, exist_ok=True)
for fn in os.listdir(os.path.join(ROOT, 'data')):
    if fn.endswith(('.sql', '.json')):
        shutil.copy2(os.path.join(ROOT, 'data', fn), os.path.join(idata, fn))
db = os.path.join(idata, 'app.db')
if os.path.exists(db):
    os.remove(db)
dst_app = os.path.join(DST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn)
            rel2 = os.path.relpath(src, os.path.join(ROOT, 'app'))
            tgt = os.path.join(dst_app, rel2)
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            shutil.copy2(src, tgt)
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.png')) and ('icon' in fn.lower() or 'rad_sanat' in fn.lower()):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, fn))
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, '_internal', fn))
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\nset QT_OPENGL=software\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
sc = ('@echo off\r\nset "d=%~dp0"\r\npowershell -NoProfile -Command "'
      "$w=New-Object -ComObject WScript.Shell;"
      "$s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\RadSanatWarehouse.lnk');"
      "$s.TargetPath='%d%run.bat';$s.WorkingDirectory='%d%';"
      "$s.IconLocation='%d%RadSanatWarehouse.exe,0';"
      '$s.Save()"'
      '\r\necho Shortcut created\r\npause\r\n')
with open(os.path.join(DST, 'make_shortcut.bat'), 'w') as f:
    f.write(sc)
scl = os.path.join(DST, 'scale.txt')
if os.path.exists(scl):
    os.remove(scl)
print('3) تمام (scale.txt هم حذف شد تا خودکار باشد)')
print('=== حالا رزولوشن را 1366x768 کنید و run.bat بزنید ===')
input('Enter...')