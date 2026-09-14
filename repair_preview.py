# -*- coding: utf-8 -*-
"""
repair_preview.py
اسکریپت جایگزینی و اصلاح تمیز پنجره پیش‌نمایش فاکتور (HtmlPreviewDialog)
"""

import os

NEW_CODE = '''# -*- coding: utf-8 -*-
"""HtmlPreviewDialog - پنجره پیش‌نمایش فاکتور و اسناد [DLG-V6-FIXED]"""

import os
import re
import tempfile
import subprocess
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextBrowser, QFileDialog, QMessageBox, QSizePolicy, QApplication
)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog


def simplify_html(html: str) -> str:
    """آماده‌سازی HTML جهت نمایش استاندارد در QTextBrowser"""
    if not html:
        return ""
    # تبدیل و تطبیق اندازه‌ها برای خوانایی بهتر در QTextBrowser
    clean = re.sub(r'font-size:\s*\d+px;', 'font-size: 13px;', html, flags=re.I)
    return clean


class HtmlPreviewDialog(QDialog):
    def __init__(self, html: str, title: str = "پیش‌نمایش سند", parent=None):
        super().__init__(parent)
        self.raw_html = html or ""
        self.doc_title = title or "سند"

        # فعال‌سازی دکمه‌های کنترل پنجره (کوچک، بزرگ و بستن)
        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )

        self.setWindowTitle(self.doc_title)
        self.setLayoutDirection(Qt.RightToLeft)

        # تنظیم ابعاد پیش‌فرض متناسب و حداقل ابعاد ایمن
        self.resize(950, 680)
        self.setMinimumSize(700, 500)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # نوار ابزار بالا
        main_layout.addLayout(self._create_toolbar())

        # نمایشگر سند
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.browser.setHtml(simplify_html(self.raw_html))
        
        # افزودن با ضریب ۱ برای پر کردن کل فضای خالی
        main_layout.addWidget(self.browser, stretch=1)

    def _create_toolbar(self):
        bar = QHBoxLayout()
        bar.setSpacing(10)

        btn_print = QPushButton("چاپ")
        btn_pdf = QPushButton("ذخیره PDF")
        btn_close = QPushButton("بستن")

        btn_print.setMinimumHeight(36)
        btn_print.setMinimumWidth(110)
        btn_pdf.setMinimumHeight(36)
        btn_pdf.setMinimumWidth(110)
        btn_close.setMinimumHeight(36)
        btn_close.setMinimumWidth(90)

        # استایل دکمه‌ها
        btn_print.setStyleSheet("background-color: #2b5797; color: white; font-weight: bold; border-radius: 4px; padding: 4px 12px;")
        btn_pdf.setStyleSheet("background-color: #008272; color: white; font-weight: bold; border-radius: 4px; padding: 4px 12px;")
        btn_close.setStyleSheet("background-color: #555555; color: white; font-weight: bold; border-radius: 4px; padding: 4px 12px;")

        btn_print.clicked.connect(self._print_document)
        btn_pdf.clicked.connect(self._save_pdf)
        btn_close.clicked.connect(self.accept)

        bar.addWidget(btn_print)
        bar.addWidget(btn_pdf)
        bar.addStretch(1)
        bar.addWidget(btn_close)
        return bar

    def _print_document(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            self.browser.print_(printer)

    def _save_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره فاکتور به صورت PDF", f"{self.doc_title}.pdf", "PDF Files (*.pdf)"
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            self.browser.print_(printer)
            QMessageBox.information(self, "موفق", "فایل PDF با موفقیت ذخیره شد.")
'''

def main():
    target_path = os.path.join("app", "ui", "html_preview_dialog.py")
    
    if not os.path.exists(os.path.dirname(target_path)):
        print(f"خطا: مسیر پوشه {os.path.dirname(target_path)} یافت نشد.")
        print("لطفاً اطمینان حاصل کنید این اسکریپت در ریشه اصلی پروژه اجرا می‌شود.")
        return

    # تهیه نسخه پشتیبان
    if os.path.exists(target_path):
        backup_path = target_path + ".bak"
        with open(target_path, "r", encoding="utf-8") as f:
            old_data = f.read()
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(old_data)
        print(f"یک نسخه پشتیبان در {backup_path} ذخیره شد.")

    # بازنویسی تمیز
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(NEW_CODE)
        
    print(f"فایل {target_path} با موفقیت تعمیر و بهینه‌سازی شد.")

if __name__ == "__main__":
    main()
