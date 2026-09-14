# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.getcwd())
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
from app.ui.html_preview_dialog import HtmlPreviewDialog
html = ('<html><body dir="rtl"><h2>تست پیش‌نمایش</h2>'
        '<table border="1" cellspacing="0" cellpadding="5" width="100%">'
        '<tr><th>ردیف</th><th>کد پالت</th><th>نام</th></tr>'
        '<tr><td>1</td><td>CH-0001</td><td>پالت چوبی سرامیکی 9-110-110</td></tr>'
        '<tr><td>2</td><td>CH-0002</td><td>پالت چوبی مازون 15-120-120</td></tr>'
        '</table></body></html>')
d = HtmlPreviewDialog(html, 'تست پیش‌نمایش')
d.exec_()