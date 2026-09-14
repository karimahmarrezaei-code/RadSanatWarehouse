# -*- coding: utf-8 -*-
import sys, os
os.environ.pop('QTWEBENGINE_CHROMIUM_FLAGS', None)
os.environ.pop('QTWEBENGINE_DISABLE_SANDBOX', None)
sys.path.insert(0, os.getcwd())
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
from app.ui.webengine_preview import WebEnginePreviewDialog as D
html = ('<html><body dir="rtl"><h2>تست وب</h2>'
        '<table border="1" cellspacing="0" cellpadding="5" width="100%">'
        '<tr><th>کد پالت</th><th>نام</th></tr>'
        '<tr><td>CH-0001</td><td>پالت چوبی سرامیکی</td></tr></table></body></html>')
d = D(html, 'تست وب')
d.exec_()