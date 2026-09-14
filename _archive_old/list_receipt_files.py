# -*- coding: utf-8 -*-
"""list_receipt_files.py - لیست همه فایل‌های receipt_manager_window با تاریخ"""
import os
from datetime import datetime

def main():
    print('=== همه فایل‌های receipt_manager_window ===')
    found = []
    for base, dirs, files in os.walk('.'):
        if 'venv' in base or '__pycache__' in base:
            continue
        for fn in files:
            if 'receipt_manager_window' in fn:
                p = os.path.join(base, fn)
                mt = datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M')
                sz = os.path.getsize(p)
                found.append((mt, sz, p))
    found.sort(reverse=True)
    for mt, sz, p in found:
        print('  {} | {:>8,} bytes | {}'.format(mt, sz, p))
    print()
    print('قدیمی‌ترین = قبل از همه پچ‌ها (سالم‌ترین)')

if __name__ == '__main__':
    main()
