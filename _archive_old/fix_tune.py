# -*- coding: utf-8 -*-
"""تنظیم نهایی مقیاس بر اساس ارتفاع - اجرا: python fix_tune.py"""
import os, sys, subprocess, shutil, py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py')
s = open(mp, encoding='utf-8').read()

# 1) جایگزینی بلوک AUTO-RES با نسخهٔ v2
i = s.find('# AUTO-RES:')
if i >= 0:
    j = s.find('_AUTO_FACTOR = _auto_scale()')
    j = s.find('\n', j) + 1
    block = (
        "# AUTO-RES v2: مقیاس خودکار بر اساس ارتفاع + scale.txt اختیاری - AUTO-RES\n"
        "import os as _os2, sys as _sys2\n"
        "def _auto_scale():\n"
        "    try:\n"
        "        _base = _os2.path.dirname(_sys2.executable) if getattr(_sys2, 'frozen', False) "
        "else _os2.path.dirname(_os2.path.abspath(__file__))\n"
        "        _p = _os2.path.join(_base, 'scale.txt')\n"
        "        if _os2.path.exists(_p):\n"
        "            _v = open(_p, encoding='utf-8').read().strip()\n"
        "            if _v:\n"
        "                return float(_v)\n"
        "        import ctypes\n"
        "        _h = ctypes.windll.user32.GetSystemMetrics(1)\n"
        "        if _h and _h < 900:\n"
        "            return round(max(0.72, min(1.0, (_h - 40) / 980.0)), 2)\n"
        "        return 1.0\n"
        "    except Exception:\n"
        "        return 1.0\n"
        "_AUTO_FACTOR = _auto_scale()\n"
        "if _AUTO_FACTOR != 1.0:\n"
        "    _os2.environ['QT_SCALE_FACTOR'] = str(_AUTO_FACTOR)\n"
    )
    s = s[:i] + block + s[j:]
    print('1) AUTO-RES v2 جایگزین شد')
else:
    print('1) بلوک AUTO-RES پیدا نشد!')

# 2) لاگین بزرگ‌تر
s = s.replace('setMinimumSize(560, 440)', 'setMinimumSize(620, 470)')
print('2) کف لاگین 620x470 شد')

open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)

# 3) بیلد + تزریق + run.bat + make_shortcut
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
            rel = os.path.relpath(src, os.path.join(ROOT, 'app'))
            tgt = os.path.join(dst_app, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            shutil.copy2(src, tgt)
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.png')) and ('icon' in fn.lower() or 'rad_sanat' in fn.lower()):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, fn))
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, '_internal', fn))
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\nset QT_OPENGL=software\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
sc = (
    '@echo off\r\n'
    'set "d=%~dp0"\r\n'
    'powershell -NoProfile -Command "'
    "$w=New-Object -ComObject WScript.Shell;"
    "$s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\RadSanatWarehouse.lnk');"
    "$s.TargetPath='%d%run.bat';"
    "$s.WorkingDirectory='%d%';"
    "$s.IconLocation='%d%RadSanatWarehouse.exe,0';"
    '$s.Save()"'
    '\r\necho Shortcut created\r\npause\r\n'
)
with open(os.path.join(DST, 'make_shortcut.bat'), 'w') as f:
    f.write(sc)
print('3) بیلد + تزریق + run.bat + make_shortcut تمام')
print('=== تست: رزولوشن 1366x768 → run.bat ===')
input('Enter...')