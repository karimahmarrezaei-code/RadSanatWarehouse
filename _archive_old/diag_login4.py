# -*- coding: utf-8 -*-
"""مقایسهٔ لاگین با و بدون استایل - اجرا: python diag_login4.py"""
import os, sys
os.environ['QT_SCALE_FACTOR'] = '0.74'
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from app.core.database import DatabaseManager
from app.ui.login_window import LoginWindow

app = QApplication(sys.argv)
db = DatabaseManager(os.path.join('data', 'app.db'))
w = LoginWindow(db)
w.show()

def kids(tag):
    print('---', tag, '| window:', w.geometry())
    for c in w.findChildren(object):
        nm = type(c).__name__
        if hasattr(c, 'geometry') and not nm.endswith('Layout'):
            print('  ', nm, c.objectName(), c.geometry())

def dump():
    kids('BEDUNE STYLE')
    try:
        from app.styles.app_style import apply_style
        apply_style(app)
        app.processEvents()
        kids('BA STYLE')
    except Exception as e:
        print('style error:', e)
    app.quit()

QTimer.singleShot(800, dump)
sys.exit(app.exec_())