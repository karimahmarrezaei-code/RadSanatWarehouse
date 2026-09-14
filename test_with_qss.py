# -*- coding: utf-8 -*-
import sys, os, re
sys.path.insert(0, os.getcwd())
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)

# 1) چاپ هر قانون استایل که به مرورگرها دست می‌زند
print('=== قوانین مشکوک استایل ===')
files = ['main.py', 'app/ui/theme_manager.py']
for dp, ds, fs in os.walk('app'):
    for fn in fs:
        if fn.endswith(('.qss', '.css')):
            files.append(os.path.join(dp, fn))
for f in files:
    if not os.path.exists(f):
        continue
    for i, l in enumerate(open(f, encoding='utf-8', errors='replace').read().split('\n')):
        if re.search(r'QTextBrowser|QWebEngine|max-height|WIN-SCROLL', l):
            print(f'{f}:{i+1}: {l.strip()[:100]}')

# 2) اعمال تم دقیقاً مثل برنامه
try:
    from app.ui.theme_manager import apply_theme
    apply_theme(app)
    print('=== تم اعمال شد ===')
except Exception as e:
    print('تم خطا:', e)

# 3) دیالوگ با تم
from app.ui.html_preview_dialog import HtmlPreviewDialog as D
html = ('<html><body dir="rtl"><h2>تست با تم</h2>'
        '<table border="1" cellspacing="0" cellpadding="5" width="100%">'
        '<tr><th>کد</th><th>نام</th></tr>'
        '<tr><td>CH-0001</td><td>پالت چوبی سرامیکی</td></tr>'
        '<tr><td>CH-0002</td><td>پالت چوبی مازون</td></tr></table></body></html>')
d = D(html, 'تست با تم')
d.exec_()