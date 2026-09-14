# -*- coding: utf-8 -*-
"""پاکسازی امن + ثبت گیت از وضعیت سالم - اجرا: py git_commit_cleanup.py"""
import os, shutil, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
EXCLUDE = {'.venv', 'venv', '__pycache__', '.git', 'node_modules', 'backups'}

def run(cmd):
    try:
        r = subprocess.run(cmd, cwd=ROOT, shell=True, capture_output=True, text=True)
        return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()
    except Exception as e:
        return 1, '', str(e)

removed = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDE]
    for fn in filenames:
        if '.bak' in fn.lower():
            p = os.path.join(dirpath, fn)
            try:
                os.remove(p); removed += 1
                print('حذف پشتیبان:', os.path.relpath(p, ROOT))
            except Exception as e:
                print('خطا:', os.path.relpath(p, ROOT), e)

for fn in os.listdir(ROOT):
    p = os.path.join(ROOT, fn)
    if not os.path.isfile(p) or fn.lower() == 'git_commit_cleanup.py':
        continue
    if fn.lower().startswith(('fix_', 'create_', 'find_', 'diag_')) and fn.lower().endswith('.py'):
        try:
            os.remove(p); removed += 1
            print('حذف اسکریپت:', fn)
        except Exception as e:
            print('خطا:', fn, e)

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDE]
    for d in list(dirnames):
        if d.lower() == '__pycache__':
            shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
print('تعداد فایل حذف‌شده:', removed)

with open(os.path.join(ROOT, '.gitignore'), 'w', encoding='utf-8') as f:
    f.write('.venv/\nvenv/\n__pycache__/\n*.pyc\n*.bak*\ndata/\nbackups/\n')
print('OK - .gitignore')

code, out, err = run('git rev-parse --is-inside-work-tree')
if code != 0:
    print('مخزن گیت نیست؛ git init...')
    run('git init')
code, out, err = run('git config user.email')
if not out:
    run('git config user.email "dev@warehouse.local"')
    run('git config user.name "Warehouse App"')

try:
    os.remove(os.path.abspath(__file__))
    print('OK - اسکریپت پاکسازی حذف شد')
except Exception:
    pass

run('git add -A')
code, out, err = run('git commit -m "یکپارچه‌سازی شماره‌گذاری (پیش‌نمایش=ذخیره)، انبارمحوری کامل حواله/مرجع، زنجیره تعهد موجودی و پاکسازی"')
print(out or err)
code, out, err = run('git log --oneline -3')
print(out)
input('Enter...')