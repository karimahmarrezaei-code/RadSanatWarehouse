# -*- coding: utf-8 -*-
"""
backup_and_cleanup.py - بکاپ کلی + پاکسازی فایل‌های زاید
=========================================================

دو کار انجام می‌دهد:

گام ۱) بکاپ کلی:
  از کل پروژه (به‌جز پوشه‌های سنگین venv / __pycache__) یک فایل ZIP می‌سازد:
      backup_full_YYYYMMDD_HHMMSS.zip
  این فایل شامل دیتابیس و همه فایل‌های اصلی است — مرجع امن برای بازگشت.

گام ۲) پاکسازی فایل‌های زاید:
  همه فایل‌هایی که در این روزهای عیب‌یابی ساخته شدند حذف می‌شوند:
    - بکاپ‌های پراکنده  (*.bak)
    - اسکریپت‌های پچ     (fix_*.py, patch_*.py, rescue_*.py)
    - اسکریپت‌های تشخیصی (diag_*.py, check_*.py, scan_*.py, show_*.py, find_*.py)
    - اسکریپت‌های ارسال  (send_*.py, files_for_agent*.txt)
    - سایر ابزارهای موقت (install_*.py, connect_*.py, rebuild_*.py, cleanup_*.py,
                          reset_*.py, activate_*.py, add_*.py, backfill_*.py,
                          dedupe_*.py, delete_*.py, clear_*.py, build_*.py, check_*.bat)
    - پوشه __pycache__

  ⚠️ فایل‌های اصلی برنامه (main.py, app/...) دست نمی‌خورند.

اجرا (از پوشه F:\\warehouse_app — برنامه بسته باشد):
    py -X utf8 .\\backup_and_cleanup.py
"""
import os
import zipfile
from datetime import datetime

SKIP_DIRS = {'venv', '.venv', '__pycache__', 'node_modules', '.git',
             'migration', 'test_docimg', 'test_issue_percent'}

# الگوهای فایل زاید (در ریشه پروژه یا هر زیرپوشه)
CLEAN_PREFIXES = (
    'fix_', 'patch_', 'rescue_', 'diag_', 'scan_', 'show_', 'find_',
    'check_', 'send_', 'install_', 'connect_', 'rebuild_', 'cleanup_',
    'reset_', 'activate_', 'backfill_', 'dedupe_', 'delete_', 'clear_',
    'build_receipt_', 'add_', 'remove_',
)
CLEAN_EXACT = {
    'FIX_LOCK.bat', 'cleanup_junk.bat', 'cleanup_junk.ps1', 'cleanup_junk_MOVE.bat',
    'files_for_agent.txt', 'files_for_agent2.txt', 'files_backup.txt',
    'diag_result.txt', 'diag_ui_report.txt', 'diag_save_blocks.txt',
}
CLEAN_EXTENSIONS = {'.bak'}


def log(*a):
    print(' '.join(str(x) for x in a))


def hr():
    print('-' * 66)


def collect_all_files(root='.'):
    """همه فایل‌ها به‌جز پوشه‌های سنگین"""
    files = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in names:
            files.append(os.path.join(base, n))
    return files


def make_backup(files, stamp):
    """ساخت ZIP کلی"""
    zip_name = 'backup_full_{}.zip'.format(stamp)
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        count = 0
        for f in files:
            try:
                zf.write(f)
                count += 1
            except Exception:
                pass
    return zip_name, count


def is_junk(rel):
    """آیا این فایل زاید است؟"""
    base = os.path.basename(rel)
    low = base.lower()
    if base in CLEAN_EXACT:
        return True
    if low.endswith('.bak'):
        return True
    for p in CLEAN_PREFIXES:
        if low.startswith(p):
            return True
    return False


def main():
    log('=== بکاپ کلی + پاکسازی فایل‌های زاید ===')
    log('⚠️  برنامه باید بسته باشد!')
    hr()

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # گام ۱: بکاپ کلی
    log('گام ۱: ساخت بکاپ کلی...')
    files = collect_all_files()
    zip_name, count = make_backup(files, stamp)
    log('   بکاپ ساخته شد: {}  ({} فایل)'.format(zip_name, count))

    # گام ۲: پاکسازی
    log()
    log('گام ۲: پاکسازی فایل‌های زاید...')
    removed = []
    for f in files:
        rel = f.replace('\\', '/')
        if rel.startswith('backup_full_') and rel.endswith('.zip'):
            continue  # بکاپی که الان ساختیم را پاک نکن
        if is_junk(rel):
            try:
                os.remove(f)
                removed.append(rel)
            except Exception:
                pass

    # پاک کردن __pycache__ در هر عمقی (با walk جداگانه که آن را فیلتر نمی‌کند)
    removed_pyc = 0
    for base, dirs, names in os.walk('.', topdown=False):
        for d in list(dirs):
            if d == '__pycache__':
                pc = os.path.join(base, d)
                try:
                    for n in os.listdir(pc):
                        p = os.path.join(pc, n)
                        if os.path.isfile(p):
                            os.remove(p)
                            removed_pyc += 1
                    os.rmdir(pc)
                except Exception:
                    pass

    if removed:
        for r in removed:
            log('   ✂ ' + r)
        log('   جمعاً {} فایل زاید حذف شد.'.format(len(removed)))
    else:
        log('   فایل زایدی پیدا نشد.')
    if removed_pyc:
        log('   {} فایل کش (__pycache__) حذف شد.'.format(removed_pyc))

    hr()
    log('تمام! بکاپ کلی در: ' + zip_name)
    log('حالا می‌توانی این اسکریپت (backup_and_cleanup.py) را هم خودت پاک کنی.')
    log('و برنامه را اجرا کن:  py -X utf8 .\\main.py')


if __name__ == '__main__':
    main()
