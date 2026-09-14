# -*- coding: utf-8 -*-
"""تم درست + SAFE-FIT v4 (پوشش exec_) - اجرا: python fix_final4.py"""
import os, shutil, subprocess, sys, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) پیدا کردن نسخهٔ درست theme_manager (دارای load_theme)
good = None
cands = []
for dp, ds, fs in os.walk(ROOT):
    if any(k in dp for k in ('.venv', '.git', '\\build', '\\dist')):
        continue
    if 'theme_manager.py' in fs:
        p = os.path.join(dp, 'theme_manager.py')
        try:
            txt = open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        if 'def load_theme' in txt:
            cands.append(p)
for p in cands:
    if 'app' + os.sep + 'ui' in p:
        good = p
if good is None and cands:
    good = cands[0]
if good is None:
    r = subprocess.run(['git', 'log', '--all', '--oneline', '--', 'theme_manager.py'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n')[:10]:
        if not line.strip():
            continue
        c = line.split()[0]
        out = subprocess.run(['git', 'show', c + ':theme_manager.py'],
                             capture_output=True, text=True)
        if 'def load_theme' in out.stdout:
            open(os.path.join(ROOT, 'theme_manager.py'), 'w', encoding='utf-8').write(out.stdout)
            good = os.path.join(ROOT, 'theme_manager.py')
            break
print('1) نسخه درست پیدا شد در:', good)
if good is None:
    print('❌ هیچ نسخه‌ای با load_theme پیدا نشد'); input(); raise SystemExit
shutil.copy2(good, os.path.join(ROOT, 'theme_manager.py'))
shutil.copy2(good, os.path.join(ROOT, 'app', 'styles', 'theme_manager.py'))
print('   کپی شد به ریشه و app/styles')

# 2) SAFE-FIT v4: پوشش exec_ هم
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# SAFE-FIT-V4' not in s:
    anchor = '    _QW.show = _safe_show\n'
    add = (
        "    from PyQt5.QtWidgets import QDialog as _QD  # SAFE-FIT-V4\n"
        "    _orig_exec = _QD.exec_  # SAFE-FIT-V4\n"
        "    def _safe_exec(self):  # SAFE-FIT-V4\n"
        "        try:  # SAFE-FIT-V4\n"
        "            _safe_show(self)  # SAFE-FIT-V4\n"
        "        except Exception:  # SAFE-FIT-V4\n"
        "            pass  # SAFE-FIT-V4\n"
        "        return _orig_exec(self)  # SAFE-FIT-V4\n"
        "    _QD.exec_ = _safe_exec  # SAFE-FIT-V4\n"
    )
    if anchor in s:
        s = s.replace(anchor, anchor + add, 1)
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('2) SAFE-FIT v4 اضافه شد ✔')
else:
    print('2) از قبل بود ✔')

# 3) بیلد + تزریق
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
# کپی مستقیم تم درست داخل بسته (بدون وابستگی به کش)
for rel in ('theme_manager.py', os.path.join('app', 'styles', 'theme_manager.py')):
    tgt = os.path.join(DST, '_internal', rel)
    if os.path.isdir(os.path.dirname(tgt)):
        shutil.copy2(good, tgt)
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
print('3) تمام ✔')
print('=== تست 1366x768: تم تیره؟ پیش‌فاکتور و اسناد مالی اسکرول؟ ===')
input('Enter...')