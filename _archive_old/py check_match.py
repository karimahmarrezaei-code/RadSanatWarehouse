# -*- coding: utf-8 -*-
import os, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__))
MGR = os.path.join(ROOT, 'app', 'ui', 'issue_manager_window.py')
src = open(MGR, encoding='utf-8').read()
n = src.count("'مانده حواله'")
src = src.replace("'مانده حواله'", "'مرجوعی این مرحله'")
open(MGR, 'w', encoding='utf-8').write(src)
print('OK - تعداد جایگزینی:', n)
try:
    py_compile.compile(MGR, doraise=True)
    print('OK سینتکس')
except Exception as e:
    print('❌', e)
input('Enter...')