# -*- coding: utf-8 -*-
"""بایگانی اسکریپت‌های موقت ریشه - اجرا: python cleanup_root.py"""
import os, shutil, subprocess
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
ARCH = os.path.join(ROOT, '_archive_old')
os.makedirs(ARCH, exist_ok=True)

KEEP_FILES = {
    'main.py', 'post_build.py', 'RadSanatWarehouse.spec',
    'requirements.txt', 'README_FA.md', 'README_FIRST RUN.bat',
    'icon.png', 'rad_sanat_novin.ico', '.gitignore', 'run_template.bat',
}
KEEP_DIRS = {
    'app', 'data', 'dist', 'build', 'exports', 'uploads',
    'tools_laptop', 'share', '.venv', '.git', '_archive_old', '__pycache__',
}

# بات الگوی نهایی (برای بیلدهای آینده)
with open(os.path.join(ROOT, 'run_template.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')

moved = 0
for name in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, name)
    if os.path.isdir(p):
        if name not in KEEP_DIRS:
            print('DIR (بررسی دستی):', name)
        continue
    if name in KEEP_FILES:
        continue
    ext = os.path.splitext(name)[1].lower()
    is_temp = (
        ext in ('.py', '.txt', '.zip', '.sql', '.ps1', '.psl')
        or (ext == '.spec' and name != 'RadSanatWarehouse.spec')
        or name.startswith('main.backup-')
        or name.startswith('main.py.')
        or name in ('backup_before_build.bat',)
    )
    if is_temp:
        shutil.move(p, os.path.join(ARCH, name))
        moved += 1
print('منتقل شد به _archive_old:', moved)
subprocess.run(['git', 'add', '-A'])
r = subprocess.run(['git', 'commit', '-m', 'پاکسازی ریشه: بایگانی اسکریپت‌های موقت در _archive_old'],
                   capture_output=True, text=True)
print('commit:', r.returncode, (r.stdout.strip() or r.stderr.strip())[:200])
input('Enter...')