# -*- coding: utf-8 -*-
"""ساخت EXE یکپارچه - هر بار برای آپدیت: python build_exe.py"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
APP_NAME = 'warehouse_app'
ICON = os.path.join(ROOT, 'icon.png')
if not os.path.exists(ICON):
    ICON = os.path.join(ROOT, 'rad sanat novin.ico')
if not os.path.exists(ICON):
    print('⚠️ آیکون پیدا نشد؛ بدون آیکون ساخته می‌شود')
    ICON = None

# 1) پاکسازی خروجی قبلی
for d in ('build', 'dist'):
    p = os.path.join(ROOT, d)
    if os.path.exists(p):
        shutil.rmtree(p)
        print('✔ پاک شد:', d)

# 2) دستور PyInstaller
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--noconfirm', '--onedir', '--windowed',
    '--name', APP_NAME,
    '--hidden-import', 'app.core.jalali',
    '--hidden-import', 'app.core.database',
    '--hidden-import', 'app.core.letterhead',
    '--hidden-import', 'app.ui.theme_manager',
    '--hidden-import', 'app.ui.dashboard_charts',
    '--hidden-import', 'PyQt5.QtWebEngineWidgets',
    '--collect-submodules', 'PyQt5',
]
if ICON:
    cmd += ['--icon', ICON]
cmd.append('main.py')

print('\n🔨 شروع ساخت EXE...')
r = subprocess.run(cmd, cwd=ROOT)
if r.returncode != 0:
    print('❌ ساخت EXE ناموفق بود')
    sys.exit(1)

# 3) کپی پوشهٔ data و آیکون کنار EXE
dist_app = os.path.join(ROOT, 'dist', APP_NAME)
for src_name in ('data', 'icon.png', 'rad sanat novin.ico'):
    src = os.path.join(ROOT, src_name)
    if not os.path.exists(src):
        continue
    dst = os.path.join(dist_app, src_name)
    if os.path.exists(dst):
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        else:
            os.remove(dst)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    print('✔ کپی شد:', src_name)

# 4) راهنمای پایانی
print('\n' + '=' * 60)
print('✅ EXE با موفقیت ساخته شد!')
print('📁 مسیر:', dist_app)
print('📋 برای لپ‌تاپ:')
print('   1) کل پوشهٔ «warehouse_app» داخل dist را کپی کنید')
print('   2) روی لپ‌تاپ در هر مسیری پیست کنید (مثلاً C:\\Programs)')
print('   3) روی dist\\warehouse_app\\warehouse_app.exe راست‌کلیک')
print('      → Send to → Desktop (create shortcut)')
print('   4) پوشهٔ data کنار exe، دیتابیس شماست — مراقبش باشید!')
print('=' * 60)
input('Enter...')