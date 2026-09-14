# -*- coding: utf-8 -*-
"""تست زندهٔ لاگین در رزولوشن کوچک - اول رزولوشن را 1366x768 کنید - اجرا: python diag_login3.py"""
import os, sys, glob, ctypes

h = ctypes.windll.user32.GetSystemMetrics(1)
f = round(max(0.72, min(1.0, (h - 40) / 980.0)), 2) if h and h < 900 else 1.0
os.environ['QT_SCALE_FACTOR'] = str(f)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from app.core.database import DatabaseManager
from app.ui.login_window import LoginWindow

print('screen height:', h, '| factor:', f)
app = QApplication(sys.argv)
db = DatabaseManager(os.path.join('data', 'app.db'))
w = LoginWindow(db)
w.show()

def dump():
    print('window:', w.geometry(), '| sizeHint:', w.sizeHint(), '| min:', w.minimumSize(), '| dpr:', w.devicePixelRatioF())
    for c in w.findChildren(object):
        if hasattr(c, 'geometry'):
            print('  ', type(c).__name__, c.objectName(), c.geometry(), 'vis:', c.isVisible())
    print('--- QSS lines about Card/Title/min/max ---')
    n = 0
    for q in glob.glob(os.path.join('app', '**', '*.qss'), recursive=True):
        for i, l in enumerate(open(q, encoding='utf-8', errors='replace').read().split('\n')):
            if any(k in l for k in ('Card', 'Title', 'min-width', 'min-height', 'max-width', 'max-height')):
                print('QSS', os.path.relpath(q), i + 1, l.strip())
                n += 1
                if n > 25:
                    return app.quit()
    app.quit()

QTimer.singleShot(1200, dump)
sys.exit(app.exec_())