# -*- coding: utf-8 -*-
"""HtmlPreviewDialog - دکمه‌های بالا و پایین [DLG-V5]"""
import re
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QFileDialog, QMessageBox, QTextBrowser)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
import os, tempfile, subprocess
from PyQt5.QtCore import QUrl
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QTextDocument, QFont


def simplify_html(html):
    h = html or ''
    h = re.sub(r'<script.*?>.*?</script>', '', h, flags=re.S | re.I)
    h = re.sub(r'<style.*?>.*?</style>', '', h, flags=re.S | re.I)
    h = re.sub(r'<button.*?</button>', '', h, flags=re.S | re.I)
    h = re.sub(r'\sstyle\s*=\s*"[^"]*"', '', h, flags=re.I)
    h = re.sub(r"\sstyle\s*=\s*'[^']*'", '', h, flags=re.I)
    h = re.sub(r'\sclass\s*=\s*"[^"]*"', '', h, flags=re.I)
    h = re.sub(r'<table(?![^>]*\bborder\b)([^>]*)>', r'<table border="1" cellspacing="0" cellpadding="5" width="100%"\1>', h, flags=re.I)
    h = re.sub(r'<th([^>]*)>(.*?)</th>', r'<th\1 bgcolor="#1e293b"><font color="#ffffff">\2</font></th>', h, flags=re.S | re.I)
    return '<font face="Tahoma" color="#000000" size="2">' + h + '</font>'  # WRAPPER-SIZE



class HtmlPreviewDialog(QDialog):
    def __init__(self, html: str, title: str = '', parent=None):
        super().__init__(parent)
        self._preview_no_wrap = True   # جلوگیری از مونکی‌پچ compact
        self._no_compact = True        # جلوگیری از کوچک‌سازی ابعاد
        #self.setWindowTitle(title or 'پیش‌نمایش سند')
        # ... بقیه کدها
        self.setWindowTitle(title)
        self.resize(1050, 900)
        self.setLayoutDirection(Qt.RightToLeft)
        self.html_content = simplify_html(html)
        self._build_ui()

    def _toolbar(self):
        bar = QHBoxLayout()
        b1 = QPushButton('🖨 چاپ')
        b1.setMinimumWidth(130); b1.setMinimumHeight(40)
        b1.setStyleSheet('background:#2563eb;color:#fff;font-weight:bold;')
        b1.clicked.connect(self._print_document)
        b2 = QPushButton('💾 PDF')
        b2.setMinimumWidth(130); b2.setMinimumHeight(40)
        b2.setStyleSheet('background:#475569;color:#fff;font-weight:bold;')
        b2.clicked.connect(self._save_pdf)
        b3 = QPushButton('بستن')
        b3.setMinimumWidth(130); b3.setMinimumHeight(40)
        b3.clicked.connect(self.accept)
        bar.addWidget(b1); bar.addWidget(b2); b4 = QPushButton("اشتراک"); b4.setMinimumWidth(130); b4.setMinimumHeight(40); b4.setStyleSheet("background:#0ea5e9;color:#fff;font-weight:bold;"); b4.clicked.connect(self._share_pdf); bar.addWidget(b4);  # SHARE-BTN-UI
        bar.addStretch(); bar.addWidget(b3)
        return bar

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(self._toolbar())
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setFont(QFont('Tahoma', 10))  # FONT-FIT
        self.browser.setStyleSheet('QTextBrowser{background:#ffffff;color:#000000;}')
        self.browser.setHtml(self.html_content)
        layout.addWidget(self.browser, 1)

    def _share_pdf(self):  # SHARE-BTN
        import datetime
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        out_dir = os.path.join(base, 'exports', 'share')  # SHARE-DIR
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, 'share_{}.pdf'.format(
            datetime.datetime.now().strftime('%Y%m%d_%H%M%S')))
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        doc = self._make_doc()
        doc.setPageSize(printer.pageRect(QPrinter.Point).size())
        doc.print_(printer)
        md = QMimeData()
        md.setUrls([QUrl.fromLocalFile(path)])
        QApplication.clipboard().setMimeData(md)
        ret = QMessageBox.question(
            self, 'اشتراک',
            'فایل PDF ساخته و در کلیپ‌بورد کپی شد.\n'
            'در بله / ایتا / تلگرام کافی است Ctrl+V بزنید.\n\n'
            'پوشهٔ فایل باز شود؟',
            QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])

    def _make_doc(self):
        doc = QTextDocument()
        doc.setHtml(self.html_content)
        doc.setDefaultFont(QFont('Tahoma', 9))  # FONT-FIT
        return doc

    def _print_document(self):  # LAYOUT-V2
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
        doc = self._make_doc()  # LAYOUT-V2
        doc.setPageSize(printer.pageRect(QPrinter.Point).size())
        doc.print_(printer)
        QMessageBox.information(self, 'PDF', 'فایل PDF ذخیره شد:\n' + path)
