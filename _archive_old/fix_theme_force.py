# -*- coding: utf-8 -*-
"""بارگذاری مستقیم تم از فایل خوب - اجرا: python fix_theme_force.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) اطمینان از خوب‌بودن نسخهٔ ریشه
root_tm = os.path.join(ROOT, 'theme_manager.py')
txt = open(root_tm, encoding='utf-8', errors='replace').read()
if 'def load_theme' not in txt or 'def apply_theme' not in txt:
    print('❌ نسخهٔ ریشه هنوز ناقص است'); input(); raise SystemExit
shutil.copy2(root_tm, os.path.join(ROOT, 'app', 'styles', 'theme_manager.py'))
print('1) نسخه خوب در ریشه و app/styles ✔')

# 2) درج THEME-FORCE در main
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# THEME-FORCE' not in s:
    anchor = '    try:  # STYLE-SAFE\n        apply_style(app)\n'
    force = (
        "    try:  # STYLE-SAFE\n"
        "        import importlib.util as _ilu  # THEME-FORCE\n"
        "        _b = os.path.dirname(os.path.abspath(__file__))  # THEME-FORCE\n"
        "        _cand = [os.path.join(_b, 'app', 'styles', 'theme_manager.py'), os.path.join(_b, 'theme_manager.py')]  # THEME-FORCE\n"
        "        if getattr(sys, 'frozen', False):  # THEME-FORCE\n"
        "            _e = os.path.dirname(sys.executable)  # THEME-FORCE\n"
        "            _cand += [os.path.join(_e, 'theme_manager.py'), os.path.join(_e, '_internal', 'app', 'styles', 'theme_manager.py')]  # THEME-FORCE\n"
        "        for _p in _cand:  # THEME-FORCE\n"
        "            if not os.path.exists(_p):  # THEME-FORCE\n"
        "                continue  # THEME-FORCE\n"
        "            try:  # THEME-FORCE\n"
        "                _spec = _ilu.spec_from_file_location('theme_manager_force', _p)  # THEME-FORCE\n"
        "                _mod = _ilu.module_from_spec(_spec)  # THEME-FORCE\n"
        "                _spec.loader.exec_module(_mod)  # THEME-FORCE\n"
        "                if hasattr(_mod, 'apply_theme') and hasattr(_mod, 'load_theme'):  # THEME-FORCE\n"
        "                    sys.modules['theme_manager'] = _mod  # THEME-FORCE\n"
        "                    sys.modules['app.styles.theme_manager'] = _mod  # THEME-FORCE\n"
        "                    break  # THEME-FORCE\n"
        "            except Exception:  # THEME-FORCE\n"
        "                continue  # THEME-FORCE\n"
        "        apply_style(app)\n"
    )
    if anchor in s:
        s = s.replace(anchor, force, 1)
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('2) THEME-FORCE درج شد ✔')
    else:
        print('2) ⚠ anchor پیدا نشد')
else:
    print('2) از قبل بود ✔')

# 3) بیلد + تزریق + کپی فایل خوب در همهٔ جای‌های ممکن
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
# فایل خوب تم، صریحاً در هر چهار نقطه
for tgt in (os.path.join(DST, 'theme_manager.py'),
            os.path.join(DST, '_internal', 'theme_manager.py'),
            os.path.join(DST, '_internal', 'app', 'styles', 'theme_manager.py')):
    if os.path.isdir(os.path.dirname(tgt)):
        shutil.copy2(root_tm, tgt)
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('3) تمام ✔')
print('=== تست 1366x768: تم باید تیره باشد ===')
input('Enter...')