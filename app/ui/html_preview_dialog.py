
# -*- coding: utf-8 -*-
"""دیالوگ پیش‌نمایش HTML ساده و پایدار برای پرینت و خروجی PDF"""
import os
import re
from datetime import datetime
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QTextDocument, QFont, QDesktopServices
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTextBrowser, QFileDialog, QMessageBox, QApplication)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog


def simplify_html(html: str) -> str:
    """ساده‌سازی CSS های پیچیده که توسط QTextBrowser پشتیبانی نمی‌شوند"""
    html = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<button.*?</button>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'style="[^"]*"', '', html, flags=re.IGNORECASE)
    html = re.sub(r'class="[^"]*"', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<table([^>]*)>', r'<table border="1" cellpadding="6" cellspacing="0"\1>', html)
    return (
        '<html><head><meta charset="utf-8"/></head>'
        '<body style="font-family: Tahoma; font-size: 11pt; direction: rtl; margin: 15px;">'
        + html +
        '</body></html>'
    )


class HtmlPreviewDialog(QDialog):
    def __init__(self, html: str, title: str = '', parent=None):
        super().__init__(parent)
        # گارد برای معافیت از مانکی‌پچ‌های ریسایز و اسکرول در main.py
        self._preview_no_wrap = True
        self._no_compact = True
        self.setProperty("_preview_no_wrap", True)
        self.setProperty("_no_compact", True)

        self.setWindowTitle(title)
        self.resize(1100, 800)
        self.setLayoutDirection(Qt.RightToLeft)

        # خواندن محتوای فایل در صورتی که مسیر پاس داده شده باشد
        content = html
        if os.path.exists(html) and os.path.isfile(html):
            try:
                with open(html, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except Exception:
                content = html

        # اصلاح استایل جداول برای نمایش استاندارد در QTextBrowser
        content = re.sub(r'<table\b', '<table border="1" cellspacing="0" cellpadding="4"', content, flags=re.IGNORECASE)
        self.html_content = content

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        btn_print = QPushButton('چاپ')
        btn_print.clicked.connect(self._print_document)
        toolbar.addWidget(btn_print)

        btn_pdf = QPushButton('ذخیره PDF')
        btn_pdf.clicked.connect(self._save_pdf)
        toolbar.addWidget(btn_pdf)

        btn_share = QPushButton('اشتراک‌گذاری (PDF)')
        btn_share.clicked.connect(self._share_pdf)
        toolbar.addWidget(btn_share)

        toolbar.addStretch()

        btn_close = QPushButton('بستن')
        btn_close.clicked.connect(self.accept)
        toolbar.addWidget(btn_close)

        layout.addLayout(toolbar)

        self.browser = QTextBrowser()
        self.browser.setReadOnly(True)
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(self.html_content)
        layout.addWidget(self.browser)

    def _share_pdf(self):
        share_dir = os.path.join(os.getcwd(), 'exports', 'share')
        os.makedirs(share_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = os.path.join(share_dir, f'share_{ts}.pdf')

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(pdf_path)
        doc = self._make_doc()
        doc.setPageSize(printer.pageRect(QPrinter.Point).size())
        doc.print_(printer)

        QApplication.clipboard().setText(QUrl.fromLocalFile(pdf_path).toString())
        try:
            import subprocess
            subprocess.Popen(['explorer', '/select,', os.path.normpath(pdf_path)])
        except Exception:
            pass
        QMessageBox.information(self, 'اشتراک‌گذاری', f'فایل PDF ساخته شد و لینک آن کپی شد:\n{pdf_path}')

    def _make_doc(self):
        doc = QTextDocument()
        doc.setDefaultFont(QFont('Tahoma', 9))
        doc.setHtml(self.html_content)
        return doc

    def _print_document(self):
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec_() != QPrintDialog.Accepted:
            return
        doc = self._make_doc()
        doc.setPageSize(printer.pageRect(QPrinter.Point).size())
        doc.print_(printer)

    def _save_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره PDF', 'preview.pdf', 'PDF Files (*.pdf)')
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        doc = self._make_doc()
        doc.setPageSize(printer.pageRect(QPrinter.Point).size())
        doc.print_(printer)
        QMessageBox.information(self, 'PDF', 'فایل PDF ذخیره شد:\n' + path)
