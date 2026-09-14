# -*- coding: utf-8 -*-
"""مقایسه RTL+مقیاس - اجرا: python diag_login6.py (رزولوشن 1366x768)"""
import os, sys, gc
os.environ['QT_SCALE_FACTOR'] = '0.74'
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
from app.core.database import DatabaseManager
from app.ui.login_window import LoginWindow

def run_cfg(tag, app_rtl, dlg_rtl, factor):
    os.environ['QT_SCALE_FACTOR'] = factor
    app = QApplication(sys.argv)
    if app_rtl:
        app.setLayoutDirection(Qt.RightToLeft)
    db = DatabaseManager(os.path.join('data', 'app.db'))
    w = LoginWindow(db)
    w.setMinimumSize(620, 500)
    if dlg_rtl:
        w.setLayoutDirection(Qt.RightToLeft)
    try:
        from app.styles.app_style import apply_style
        apply_style(app)
    except Exception:
        pass
    w.show()
    out = []
    def dump():
        out.append('=== %s | window %s' % (tag, w.geometry()))
        for c in w.findChildren(object):
            n = type(c).__name__
            if hasattr(c, 'geometry') and not n.endswith('Layout'):
                out.append('   %s %s %s' % (n, c.objectName(), c.geometry()))
        app.quit()
    QTimer.singleShot(700, dump)
    app.exec_()
    del app
    gc.collect()
    return out

res = []
res += run_cfg('A: app-RTL + scale (مثل exe فعلی)', True, False, '0.74')
res += run_cfg('B: dlg-RTL + scale (نامزد اصلاح)', False, True, '0.74')
res += run_cfg('C: dlg-RTL بدون scale (مبنای سالم)', False, True, '1.0')
print('\n'.join(res))
input('Enter...')