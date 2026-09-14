# -*- coding: utf-8 -*-
"""پاکسازی + wipe دیتابیس + بیلد - اجرا: python cleanup_and_build.py"""
import os, glob, sqlite3, shutil, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# 1) حذف اسکریپت‌های موقت
rm = 0
for pat in ('fix_*.py', 'print_*.py', 'find_*.py', 'make_docs.py'):
    for p in glob.glob(os.path.join(ROOT, pat)):
        try: os.remove(p); rm += 1
        except Exception: pass
print('حذف موقت‌ها:', rm)

# 2) __pycache__
for dirpath, dirs, files in os.walk(ROOT):
    if '.venv' in dirpath or '.git' in dirpath: continue
    for d in list(dirs):
        if d == '__pycache__':
            shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True); dirs.remove(d)

# 3) WIPE کامل دیتابیس (همهٔ جدول‌ها + شماره‌های مرجع/sequences)
dbs = []
for dirpath, dirs, files in os.walk(ROOT):
    if '.venv' in dirpath or '.git' in dirpath: continue
    for fn in files:
        if fn.endswith('.db'):
            dbs.append(os.path.join(dirpath, fn))
print('دیتابیس‌های پیدا شده:', dbs)
if dbs:
    ok = input('برای پاک‌کردن کامل همهٔ اطلاعات (حتی اطلاعات پایه و شماره مرجع) عبارت WIPE را بنویسید: ')
    if ok.strip() == 'WIPE':
        for db in dbs:
            conn = sqlite3.connect(db)
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            conn.execute('PRAGMA foreign_keys=OFF')
            for t in tables:
                conn.execute('DELETE FROM {}'.format(t))
            try: conn.execute('DELETE FROM sqlite_sequence')
            except Exception: pass
            conn.commit(); conn.close()
            print('✔ پاک شد:', db, '| جدول‌ها:', len(tables))
    else:
        print('· wipe انجام نشد')

# 4) بیلد
specs = glob.glob(os.path.join(ROOT, '*.spec'))
if specs:
    cmd = ['python', '-m', 'PyInstaller', specs[0], '--noconfirm']
else:
    cmd = ['python', '-m', 'PyInstaller', 'main.py', '--noconfirm', '--windowed', '--name', 'WarehouseApp']
print('بیلد:', ' '.join(cmd))
r = subprocess.run(cmd, cwd=ROOT)
print('کد خروجی بیلد:', r.returncode)
input('Enter...')