# -*- coding: utf-8 -*-
"""
full_repair_receipt.py - ترمیم کامل فرم رسید

اگر فرم رسید با پچ‌های قبلی خراب شده، این اسکریپت:
  ۱) فایل receipt_repository.py و receipt_manager_window.py را از
     قدیمی‌ترین پشتیبان سالم بازیابی می‌کند
  ۲) پچ‌های درست را دوباره اعمال می‌کند:
     - patch_vat_fixes (final_total + avg price + toggle)
     - patch_receipt_print_final (قالب زیبای پرینت)
     - patch_receipt_final_fix (get_company_info + فرمت قیمت + avg)
  ۳) سینتکس را بررسی می‌کند

اجرا (از F:\\warehouse_app — برنامه بسته باشد):
    py -X utf8 .\\full_repair_receipt.py
"""
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

SKIP = {'venv', '.venv', '__pycache__', 'node_modules', '.git',
        'test_docimg', 'test_issue_percent', 'migration', 'backup_before_update'}


def log(*a):
    print(' '.join(str(x) for x in a))


def find_files(names):
    found = []
    for base, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for fn in names:
            if fn in files:
                p = os.path.join(base, fn)
                if p not in found:
                    found.append(p)
    return found


def find_backups(path):
    """پیدا کردن همه پشتیبان‌های یک فایل (به ترتیب قدیمی به جدید)"""
    d = os.path.dirname(path) or '.'
    base = os.path.basename(path)
    baks = []
    for fn in os.listdir(d):
        if fn.startswith(base + '.') and fn.endswith('.bak'):
            baks.append(os.path.join(d, fn))
    # مرتب بر اساس زمان ایجاد (قدیمی‌ترین اول)
    baks.sort(key=lambda p: os.path.getmtime(p))
    return baks


def restore_oldest_backup(path):
    """بازیابی از قدیمی‌ترین پشتیبان (قبل از همه پچ‌ها)"""
    baks = find_backups(path)
    if not baks:
        return False, 'پشتیبان پیدا نشد'
    oldest = baks[0]
    shutil.copy2(oldest, path)
    return True, oldest


def compile_ok(path):
    try:
        import py_compile
        py_compile.compile(path, doraise=True)
        return True, ''
    except Exception as e:
        return False, str(e)


def main():
    log('=== ترمیم کامل فرم رسید ===')
    log('برنامه باید بسته باشد!')
    log()

    # پیدا کردن فایل‌ها
    repos = find_files(['receipt_repository.py'])
    uis = find_files(['receipt_manager_window.py'])

    repo = repos[0] if repos else None
    ui = uis[0] if uis else None

    if not repo:
        log('❌ receipt_repository.py پیدا نشد')
        sys.exit(1)
    if not ui:
        log('⚠️ receipt_manager_window.py پیدا نشد')

    # ۱) بازیابی از پشتیبان (فقط اگر فایل خراب است)
    for path, name in [(repo, 'repository'), (ui, 'UI')]:
        if not path:
            continue
        ok, err = compile_ok(path)
        if not ok:
            restored, bak = restore_oldest_backup(path)
            if restored:
                log('{}: فایل خراب بود → از پشتیبان قدیمی بازیابی شد: {}'.format(name, bak))
                ok2, err2 = compile_ok(path)
                log('   سینتکس بعد از بازیابی:', '✅ سالم' if ok2 else '❌ ' + err2[:80])
            else:
                log('{}: فایل خراب است و پشتیبان نیست: {}'.format(name, err))
        else:
            log('{}: فایل سالم است ✅'.format(name))
    log()

    # ۲) اجرای پچ‌ها به ترتیب
    patches = [
        'patch_vat_fixes.py',
        'patch_receipt_print_final.py',
        'patch_receipt_final_fix.py',
    ]
    here = os.path.dirname(os.path.abspath(__file__))
    for p in patches:
        pth = os.path.join(here, p)
        if os.path.exists(pth):
            log('▶ اجرای:', p)
            r = subprocess.run([sys.executable, '-X', 'utf8', pth], capture_output=True, text=True, encoding='utf-8')
            out = r.stdout + r.stderr
            # نمایش خطوط مهم
            for ln in out.splitlines():
                if any(k in ln for k in ('✅', '❌', '⚠️', 'سینتکس', 'اضافه شد', 'بازنویسی', 'error', 'Error')):
                    log('   ', ln[:100])
            log()
        else:
            log('⚠️ پچ پیدا نشد:', p)

    # ۳) بررسی نهایی
    log('=== بررسی نهایی ===')
    for path, name in [(repo, 'repository'), (ui, 'UI')]:
        if not path:
            continue
        ok, err = compile_ok(path)
        log('{}: {}'.format(name, '✅ سالم' if ok else '❌ ' + err[:100]))
    log()
    log('تمام. برنامه را باز کنید: py -X utf8 .\\main.py')
    log('فرم رسید را تست کنید: قیمت میانگین، تایپ قیمت، ثبت رسید، پرینت.')


if __name__ == '__main__':
    main()
