# -*- coding: utf-8 -*-
"""تعمیر خط تعریف کلاس PalletItemsTable - اجرا: py fix_pallet_class_line.py"""
import os, re, shutil, py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
PT = os.path.join(ROOT, 'app', 'ui', 'pallet_items_table.py')

src = open(PT, encoding='utf-8').read()
shutil.copy2(PT, PT + '.bak36')

src2, n = re.subn(r'class PalletItemsTable\(QWidget[^)]*\):',
                  'class PalletItemsTable(QWidget):', src, count=1)
if n:
    open(PT, 'w', encoding='utf-8').write(src2)
    print('OK - خط تعریف کلاس تعمیر شد')
else:
    print('SKIP - خط خراب پیدا نشد')

try:
    py_compile.compile(PT, doraise=True)
    print('OK سینتکس: pallet_items_table')
except Exception as e:
    print('❌ خطا:', e)
input('Enter...')