# -*- coding: utf-8 -*-
"""check_jalali.py - پیدا کردن نمایش تاریخ میلادی بدون تبدیل شمسی"""
from pathlib import Path

ROOT = Path(__file__).parent

DATE_FIELDS = [
    'transaction_date', 'finance_date', 'issue_date', 'receipt_date', 'due_date',
    'created_at', 'last_transaction_date', 'register_date', 'opening_date',
    'operation_date', 'entry_date', 'event_date', 'confirmed_at', 'printed_at',
    'last_login_at', 'updated_at', 'cancelled_at',
]
DISPLAY_HINTS = ['setItem', 'setText', 'addRow', 'values', 'vals', 'append',
                 'format', 'f"', "f'", 'QTableWidgetItem', 'setHtml', 'QLabel']

def main():
    grouped = {}
    for py in sorted((ROOT / 'app').rglob('*.py')):
        lines = py.read_text(encoding='utf-8', errors='ignore').splitlines()
        for i, line in enumerate(lines, 1):
            if not any(h in line for h in DISPLAY_HINTS):
                continue
            for f in DATE_FIELDS:
                if f in line:
                    ctx = '\n'.join(lines[max(0, i - 3): i + 1])
                    if 'jalali' not in ctx.lower():
                        grouped.setdefault(str(py.relative_to(ROOT)), []).append((i, line.strip()))
                    break

    total = sum(len(v) for v in grouped.values())
    print(f'== {total} مورد نمایش تاریخ بدون تبدیل شمسی ==\n')
    for file, items in grouped.items():
        print(f'--- {file} ({len(items)} مورد)')
        for ln, code in items:
            print(f'   خط {ln}: {code[:100]}')
        print()

if __name__ == '__main__':
    main()