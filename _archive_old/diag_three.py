# -*- coding: utf-8 -*-
"""سه نقطهٔ جراحی - اجرا: python diag_three.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))

def dump(rel, keys, before=2, after=25, max_hits=4):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print('MISSING', rel); return
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    print('=' * 25, rel, '=' * 25)
    hits = 0
    for i, l in enumerate(lines):
        if any(k in l for k in keys):
            for j in range(max(0, i - before), min(len(lines), i + after)):
                print(f'{j+1:5} {lines[j].rstrip()}')
            print('-' * 50)
            hits += 1
            if hits >= max_hits:
                break

print('##### الف) پیش‌نمایش/چاپ رسید #####')
dump('app/ui/receipt_manager_window.py',
     ['def _print', 'def _preview', 'preview_html', 'WebEnginePreview', 'def _build_html'])
print('##### ب) نگاشت ذخیرهٔ پالت #####')
dump('app/ui/pallets_window.py', ["'name':", 'name_edit', "'code':"])
print('##### ج) تولید شماره مرجع در تبدیل #####')
dump('app/ui/issue_manager_window.py',
     ['reference_no', 'REF-', 'def _convert', 'def _generate'])
input('Enter...')