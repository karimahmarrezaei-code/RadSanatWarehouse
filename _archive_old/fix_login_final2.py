# -*- coding: utf-8 -*-
"""حذف ترفند تقسیم و کف منطقی ساده برای لاگین - اجرا: python fix_login_final2.py"""
import os, sys, subprocess, shutil, py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py')
s = open(mp, encoding='utf-8').read()

start = s.find('    try:\n        _f = float(')
if start >= 0:
    e = s.find('        login_dlg.setMinimumSize(520, 470)')
    e = s.find('\n', e) + 1
    s = s[:start] + '    login_dlg.setMinimumSize(620, 500)  # LOGIN-FIX2\n' + s[e:]
    open(mp, 'w', encoding='utf-8').write(s)
    py_compile.compile(mp, doraise=True)
    print('1) LOGIN-FIX2 جایگزین شد (کف 620x500 منطقی، بدون تقسیم)')
else:
    print('1) ⚠ بلوک قبلی پیدا نشد')

print('2) بیلد...')
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
print('2) تمام')
print('=== رزولوشن 1366x768 بماند → run.bat ===')
input('Enter...')