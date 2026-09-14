# -*- coding: utf-8 -*-
"""theme_manager داخل بسته + تور اطمینان استایل - اجرا: python fix_theme_final.py"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) اطمینان از حضور theme_manager در ریشه
root_tm = os.path.join(ROOT, 'theme_manager.py')
if not os.path.exists(root_tm):
    cands = []
    for dp, ds, fs in os.walk(ROOT):
        if any(k in dp for k in ('.venv', '.git', '\\build', '\\dist')):
            continue
        if 'theme_manager.py' in fs:
            cands.append(os.path.join(dp, 'theme_manager.py'))
    if not cands:
        print('❌ هیچ theme_manager.py پیدا نشد'); input(); raise SystemExit
    shutil.copy2(cands[0], root_tm)
    print('1) بازگردانی به ریشه از:', cands[0])
else:
    print('1) در ریشه هست ✔')

# 2) کپی داخل بسته تا برای همیشه باندل شود (مسیری که app_style جستجو می‌کند)
dst_tm = os.path.join(ROOT, 'app', 'styles', 'theme_manager.py')
shutil.copy2(root_tm, dst_tm)
print('2) کپی شد به app/styles/theme_manager.py ✔')

# 3) تور اطمینان در main: استایل هرگز شروع برنامه را نکشد
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# STYLE-SAFE' not in s:
    old = '    apply_style(app)\n'
    new = ('    try:  # STYLE-SAFE\n'
           '        apply_style(app)\n'
           '    except Exception as _st_exc:  # STYLE-SAFE\n'
           "        print('[style] skip:', _st_exc)  # STYLE-SAFE\n")
    if old in s:
        s = s.replace(old, new, 1)
        open(mp, 'w', encoding='utf-8').write(s)
        print('3) تور اطمینان اضافه شد ✔')
    else:
        print('3) ⚠ خط apply_style پیدا نشد')
else:
    print('3) از قبل بود ✔')

# 4) بیلد تمیز + تزریق + bat
print('4) بیلد تمیز (~2 دقیقه)...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec',
                    '--noconfirm', '--clean'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق'); input(); raise SystemExit
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
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
sc = ('@echo off\r\nset "d=%~dp0"\r\npowershell -NoProfile -Command "'
      "$w=New-Object -ComObject WScript.Shell;"
      "$s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\RadSanatWarehouse.lnk');"
      "$s.TargetPath='%d%run.bat';$s.WorkingDirectory='%d%';"
      "$s.IconLocation='%d%RadSanatWarehouse.exe,0';"
      '$s.Save()"'
      '\r\necho Shortcut created\r\npause\r\n')
with open(os.path.join(DST, 'make_shortcut.bat'), 'w') as f:
    f.write(sc)
print('4) تمام ✔')
print('=== تست: 1366x768 → run.bat → لاگین + تم تیره + تب تسویه ===')
input('Enter...')