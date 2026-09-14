# -*- coding: utf-8 -*-
"""
force_fix_avg.py - جایگزینی مستقیم کوئری خراب قیمت میانگین

مشکل: کوئری opening_inventory_items در _load_pallet_prices ناقص است
(SUM(total_price) حذف شده) → خطا → avg_pallet_prices فقط ۲ تا.

راه‌حل: کل متد _load_pallet_prices را با نسخه درست جایگزین می‌کند
(بدون وابستگی به الگوی خاص — هر شکلی باشد پیدا و عوض می‌کند).

اجرا (از F:\\warehouse_app — برنامه بسته باشد):
    py -X utf8 .\\force_fix_avg.py
"""
import os
import re
import shutil
import sys
from datetime import datetime

SKIP = {'venv', '.venv', '__pycache__', 'node_modules', '.git',
        'test_docimg', 'test_issue_percent', 'migration', 'backup_before_update'}


def log(*a):
    print(' '.join(str(x) for x in a))


def hr():
    print('-' * 66)


def find_file(name):
    for base, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in SKIP]
        if name in files:
            return os.path.join(base, name)
    return None


def backup(path):
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = '{}.forceavg_{}.bak'.format(path, stamp)
    shutil.copy2(path, bak)
    return bak


def compile_ok(path):
    try:
        import py_compile
        py_compile.compile(path, doraise=True)
        return True, ''
    except Exception as e:
        return False, str(e)


NEW_METHOD = '''    def _load_pallet_prices(self) -> None:
        """موجودی از inventory_levels + قیمت میانگین از opening/transactions"""
        self.avg_pallet_prices = {}
        self.pallet_stock = {}
        try:
            with self.db.connect() as conn:
                conn.row_factory = None

                # ۱) موجودی از inventory_levels
                rows = conn.execute(
                    "SELECT pallet_id, SUM(quantity) AS stock "
                    "FROM inventory_levels "
                    "GROUP BY pallet_id"
                ).fetchall()
                for r in rows:
                    self.pallet_stock[r[0]] = max(int(r[1] or 0), 0)

                # ۲) قیمت میانگین از opening_inventory_items
                rows = conn.execute(
                    "SELECT pallet_id, "
                    "CASE WHEN SUM(qty) > 0 THEN SUM(total_price) * 1.0 / SUM(qty) ELSE 0 END AS avg_price "
                    "FROM opening_inventory_items "
                    "WHERE qty > 0 "
                    "GROUP BY pallet_id"
                ).fetchall()
                for r in rows:
                    self.avg_pallet_prices[r[0]] = float(r[1] or 0)

                # ۳) قیمت میانگین از inventory_transactions
                rows = conn.execute(
                    "SELECT pallet_id, "
                    "CASE WHEN SUM(qty_in) > 0 THEN SUM(total_price) * 1.0 / SUM(qty_in) ELSE 0 END AS avg_price "
                    "FROM inventory_transactions "
                    "WHERE transaction_type = 'IN' AND qty_in > 0 "
                    "GROUP BY pallet_id"
                ).fetchall()
                for r in rows:
                    self.avg_pallet_prices[r[0]] = float(r[1] or 0)

                print('DEBUG: {} pallet prices loaded'.format(len(self.avg_pallet_prices)))
        except Exception as e:
            print('Load pallet prices error:', str(e))
            self.avg_pallet_prices = {}
            self.pallet_stock = {}

'''


def main():
    log('=== جایگزینی مستقیم کوئری قیمت میانگین ===')
    log('برنامه باید بسته باشد!')
    log()

    ui = find_file('receipt_manager_window.py')
    if not ui:
        log('❌ receipt_manager_window.py پیدا نشد')
        sys.exit(1)

    log('فایل:', ui)
    with open(ui, encoding='utf-8') as f:
        content = f.read()

    # پیدا کردن متد _load_pallet_prices (هر شکلی) و جایگزینی
    m = re.search(r'^[ \t]*def _load_pallet_prices\(self[^\n]*\n.*?(?=\n[ \t]*def |\nclass |\Z)', content, re.M | re.S)
    if not m:
        # حالت دیگر: با return type
        m = re.search(r'^[ \t]*def _load_pallet_prices\(self[^\n]*\)[^\n]*\n.*?(?=\n[ \t]*def |\nclass |\Z)', content, re.M | re.S)

    if not m:
        log('❌ _load_pallet_prices پیدا نشد')
        sys.exit(1)

    # بررسی: اگر از قبل درست است، رد شو
    seg = m.group(0)
    if 'SUM(total_price) * 1.0 / SUM(qty)' in seg and 'SUM(total_price) * 1.0 / SUM(qty_in)' in seg:
        log('   _load_pallet_prices از قبل درست است ✅')
        return

    content = content[:m.start()] + NEW_METHOD + content[m.end():]

    log('   پشتیبان:', backup(ui))
    with open(ui, 'w', encoding='utf-8') as f:
        f.write(content)
    ok, err = compile_ok(ui)
    log('   سینتکس:', '✅ سالم' if ok else '❌ ' + err[:120])

    hr()
    log('تمام! حالا DEBUG باید «5 pallet prices loaded» را نشان دهد.')


if __name__ == '__main__':
    main()
