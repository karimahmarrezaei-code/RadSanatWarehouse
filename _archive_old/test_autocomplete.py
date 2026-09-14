# -*- coding: utf-8 -*-
"""
test_autocomplete.py - تست مستقل auto-complete (بدون دخالت فرم‌های واقعی)
==========================================================================

یک پنجره ساده با دو فیلد (یک خطی + چندخطی) و یک دکمه «باز کردن مدیر» می‌سازد
تا مطمئن شویم خود سیستم auto-complete کار می‌کند یا نه.

اجرا (از پوشه F:\\warehouse_app):
    py -X utf8 .\\test_autocomplete.py

اگر پنجره باز شد و دکمه کار کرد → ماژول سالم است، مشکل از اتصال به فرم واقعی است
اگر خطا داد → خطا را در پنجره می‌بینید؛ آن را برای من بفرستید.
"""
import os
import sys
import traceback


def main():
    try:
        from PyQt5.QtWidgets import (
            QApplication, QWidget, QLineEdit, QTextEdit, QPushButton,
            QVBoxLayout, QLabel, QMessageBox,
        )
    except Exception as e:
        print('ERROR: PyQt5 نصب نیست:', e)
        input('Enter...')
        return

    app = QApplication(sys.argv)

    win = QWidget()
    win.setWindowTitle('تست Auto-Complete')
    win.resize(480, 320)
    lay = QVBoxLayout(win)

    title = QLabel('این پنجره تست است — دو فیلد زیر را پر کن، ثبت کن، دوباره تایپ کن')
    title.setStyleSheet('font-weight: bold; color: #1e293b;')
    lay.addWidget(title)

    # فیلد خطی
    e1 = QLineEdit()
    e1.setPlaceholderText('فیلد خطی (مثلاً نام گیرنده)')
    lay.addWidget(e1)

    # فیلد چندخطی
    t1 = QTextEdit()
    t1.setPlaceholderText('فیلد چندخطی (مثلاً توضیحات)')
    t1.setFixedHeight(80)
    lay.addWidget(t1)

    info = QLabel('حالت: در حال نصب...')
    info.setStyleSheet('color: #0f766e;')
    lay.addWidget(info)

    btn = QPushButton('باز کردن مدیر پیشنهادها (تست)')
    lay.addWidget(btn)

    try:
        sys.path.insert(0, os.getcwd())
        from app.core.auto_complete import install_autocomplete, ManageDialog
        store = install_autocomplete(win)
        info.setText(
            'نصب انجام شد. حالا:\n'
            '  ۱) در فیلدها متن تایپ کن و دکمه «ثبت/ذخیره» مجازی ندارد —\n'
            '     فقط فیلد را ترک کن تا ذخیره شود\n'
            '  ۲) F2 یا Ctrl+Space یا دکمه زیر → مدیر پیشنهادها\n'
            'فایل ذخیره: data/autocomplete.json'
        )
        btn.clicked.connect(lambda: _open_first_manager(win))
    except Exception as e:
        info.setText('نصب با خطا مواجه شد!')
        QMessageBox.critical(win, 'خطای نصب', traceback.format_exc())
        print(traceback.format_exc())

    win.show()
    sys.exit(app.exec_())


def _open_first_manager(win):
    try:
        # پیدا کردن اولین فیلتر نصب‌شده
        flt = None
        if hasattr(win, '_ac_filters'):
            for f in win._ac_filters:
                if hasattr(f, 'open_manager'):
                    flt = f
                    break
        if flt is None:
            from app.core.auto_complete import ManageDialog, AutoCompleteStore
            dlg = ManageDialog(AutoCompleteStore(), 'test_field', win)
            dlg.exec_()
            return
        flt.open_manager()
    except Exception as e:
        QMessageBox.critical(win, 'خطا', traceback.format_exc())


if __name__ == '__main__':
    main()
