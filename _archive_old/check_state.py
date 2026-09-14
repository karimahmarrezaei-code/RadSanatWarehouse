# -*- coding: utf-8 -*-
"""بررسی وضعیت قالب رسید - اجرا: python check_state.py"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(ROOT, 'app', 'repositories', 'receipt_repository.py'), encoding='utf-8').read()
i = s.find('def render_receipt_html')
print('قالب رسید:', 'NEW (کپی حواله)' if 'رسید ورودی انبار' in s[i:i+4000] else 'OLD (کهنه)')
d = open(os.path.join(ROOT, 'app', 'ui', 'html_preview_dialog.py'), encoding='utf-8').read()
print('دیالوگ:', 'تک‌موتوره' if 'QTextBrowser' in d else 'نامشخص')
input('Enter...')