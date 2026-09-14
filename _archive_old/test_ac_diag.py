# -*- coding: utf-8 -*-
"""
test_ac_diag.py - تشخیص کامل auto-complete و کلید F2
=====================================================

این اسکریپت:
  ۱) نسخه PyQt5 و Qt را چاپ می‌کند
  ۲) همه کلیدهای فشرده‌شده را در کنسول لاگ می‌کند (می‌بینیم F2 به برنامه می‌رسد یا نه)
  ۳) auto-complete را روی یک پنجره تست نصب می‌کند (با خطای کامل اگر خطا دهد)
  ۴) بعد از ۱.۵ ثانیه خودکار یک «F2 مصنوعی» به فیلد می‌فرستد تا ببینیم مدیر باز می‌شود یا نه
  ۵) یک دکمه «باز کردن مدیر (مستقیم)» هم دارد — بدون نیاز به F2

اجرا (از پوشه F:\\warehouse_app):
    py -X utf8 .\\test_ac_diag.py

خروجی کنسول را کامل برای من بفرستید (همه خط‌ها).
"""
import sys
import os
import traceback


def main():
    print('=== AC DIAG ===')
    print('cwd:', os.getcwd())
    print('')

    # ---------- ۱) نسخه PyQt5 ----------
    try:
        import PyQt5
        from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
        print('PyQt5:', PYQT_VERSION_STR, '| Qt:', QT_VERSION_STR)
    except Exception as e:
        print('PyQt5 import error:', e)
        input('Enter...')
        return

    from PyQt5.QtCore import Qt, QEvent, QTimer, QObject
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QLineEdit, QTextEdit,
        QVBoxLayout, QPushButton, QLabel, QMessageBox,
    )

    app = QApplication(sys.argv)

    # ---------- ۲) لاگ همه کلیدها در سطح برنامه ----------
    class KeyLog(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.KeyPress:
                print('KEYPRESS | obj={} | key={} | text={!r}'.format(
                    obj.__class__.__name__, event.key(), event.text()))
            return False

    keylog = KeyLog()
    app.installEventFilter(keylog)
    print('keylog installed on app')
    print('')

    # ---------- ۳) پنجره تست ----------
    win = QWidget()
    win.setWindowTitle('AC DIAG - تست')
    win.resize(520, 360)
    lay = QVBoxLayout(win)

    e1 = QLineEdit()
    e1.setPlaceholderText('فیلد خطی (روی این کلیک کن)')
    t1 = QTextEdit()
    t1.setPlaceholderText('فیلد چندخطی')
    t1.setFixedHeight(80)
    btn = QPushButton('باز کردن مدیر (مستقیم - بدون F2)')
    label = QLabel('...')
    label.setStyleSheet('color:#0f766e; font-weight:bold;')
    lay.addWidget(QLabel('دو فیلد زیر را امتحان کن:'))
    lay.addWidget(e1)
    lay.addWidget(t1)
    lay.addWidget(btn)
    lay.addWidget(label)

    # ---------- ۴) نصب auto-complete ----------
    store = None
    flts = []
    try:
        sys.path.insert(0, os.getcwd())
        from app.core.auto_complete import install_autocomplete
        print('import install_autocomplete: OK')
        store = install_autocomplete(win)
        print('install returned store:', store)
        flts = getattr(win, '_ac_filters', [])
        print('_ac_filters count:', len(flts))
        label.setText('نصب شد. تعداد فیلترها: {}'.format(len(flts)))
    except Exception:
        print('INSTALL ERROR:')
        traceback.print_exc()
        QMessageBox.critical(win, 'خطای نصب', traceback.format_exc())
        label.setText('خطای نصب! کنسول را ببین و بفرست')
    print('')

    # ---------- ۵) دکمه مستقیم ----------
    def open_first():
        print('--- open_first pressed ---')
        flts_now = getattr(win, '_ac_filters', [])
        print('filters:', len(flts_now))
        for f in flts_now:
            if hasattr(f, 'open_manager'):
                print('opening manager, field =', getattr(f, 'field', '?'))
                f.open_manager()
                return
        print('NO FILTER with open_manager!')
        QMessageBox.information(win, 'تست', 'فیلتری پیدا نشد')

    btn.clicked.connect(open_first)

    # ---------- ۶) تایمر: بعد از ۱.۵ ثانیه F2 مصنوعی بفرست ----------
    def fake_f2():
        focus = QApplication.focusWidget()
        print('--- fake F2 ---')
        print('focus now:', focus.__class__.__name__ if focus else 'None')
        if focus is None or not isinstance(focus, (QLineEdit, QTextEdit)):
            e1.setFocus()
            focus = e1
            print('focus set to e1')
        try:
            from PyQt5.QtTest import QTest
            QTest.keyClick(focus, Qt.Key_F2)
            print('QTest.keyClick(F2) sent to', focus.__class__.__name__)
        except Exception as e:
            print('QTest error:', e)

    QTimer.singleShot(1500, fake_f2)

    # ---------- ۷) گزارش بعد از ۵ ثانیه ----------
    def report():
        print('--- report after 5s ---')
        fw = QApplication.focusWidget()
        print('focus =', fw.__class__.__name__ if fw else 'None')
        aw = QApplication.activeWindow()
        print('activeWindow =', aw.__class__.__name__ if aw else 'None')
        print('window visible =', win.isVisible())
        print('auto-complete.json exists:',
              os.path.exists(os.path.join('data', 'autocomplete.json')))

    QTimer.singleShot(5000, report)

    e1.setFocus()
    win.show()
    print('window shown. focus on e1')
    print('')
    print('>>> حالا این پنجره را ببین. بعد از ۱.۵ ثانیه خودکار F2 فرستاده می‌شود.')
    print('>>> خروجی کنسول را کامل برای من بفرست.')
    print('')

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
