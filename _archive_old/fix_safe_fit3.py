# -*- coding: utf-8 -*-
"""SAFE-FIT v3 + ثبت خطای استایل - اجرا: python fix_safe_fit3.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

# 1) SAFE-FIT v3: اسکرول بر اساس حداقلِ واقعی چیدمان (نه فقط sizeHint)
old_cond = "            if self.sizeHint().height() > scr.height():\n"
new_cond = (
    "            _need = 0\n"
    "            try:\n"
    "                _lay = self.layout()\n"
    "                if _lay is not None:\n"
    "                    _need = _lay.totalMinimumSize().height()\n"
    "                if isinstance(self, _QM) and self.centralWidget() is not None and self.centralWidget().layout() is not None:\n"
    "                    _need = max(_need, self.centralWidget().layout().totalMinimumSize().height())\n"
    "            except Exception:\n"
    "                _need = 0\n"
    "            if max(self.sizeHint().height(), _need) > scr.height():  # SAFE-FIT-V3\n"
)
if '# SAFE-FIT-V3' not in s and old_cond in s:
    s = s.replace(old_cond, new_cond, 1)
    print('1) SAFE-FIT v3 اعمال شد')

# 2) ثبت خطای استایل در STYLE_ERROR.txt
old_st = "        print('[style] skip:', _st_exc)  # STYLE-SAFE\n"
new_st = (
    "        print('[style] skip:', _st_exc)  # STYLE-SAFE\n"
    "        try:  # STYLE-SAFE\n"
    "            import traceback as _tb2  # STYLE-SAFE\n"
    "            _p2 = _os2.path.join(_os2.path.dirname(_sys2.executable) if getattr(_sys2, 'frozen', False) else '.', 'STYLE_ERROR.txt')  # STYLE-SAFE\n"
    "            open(_p2, 'w', encoding='utf-8').write(_tb2.format_exc())  # STYLE-SAFE\n"
    "        except Exception:  # STYLE-SAFE\n"
    "            pass  # STYLE-SAFE\n"
)
if old_st in s and 'STYLE_ERROR.txt' not in s:
    s = s.replace(old_st, new_st, 1)
    print('2) ثبت خطای استایل اضافه شد')

open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)

# 3) بیلد + تزریق + bat
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
print('=== تست: 1366x768 → run.bat → پیش‌فاکتور (اسکرول؟) + تم ===')
input('Enter...')