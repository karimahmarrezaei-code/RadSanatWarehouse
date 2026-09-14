# -*- coding: utf-8 -*-
"""پیش‌نمایش زیبای CSS3 - فقط در فرایند جدا اجرا می‌شود [BEAUTY-PREVIEW]"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QFileDialog, QMessageBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog


class HtmlPreviewDialog(QDialog):
    def __init__(self, html: str, title: str = '', parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1200, 850)
        self.setLayoutDirection(Qt.RightToLeft)
        self.html_content = html
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        toolbar = QHBoxLayout()
        self.print_btn = QPushButton('🖨 پرینت')
        self.print_btn.setObjectName('PrimaryButton')
        self.print_btn.setMinimumWidth(130); self.print_btn.setMinimumHeight(40)
        self.print_btn.clicked.connect(self._print_document)
        self.pdf_btn = QPushButton('💾 ذخیره PDF')
        self.pdf_btn.setObjectName('SecondaryButton')
        self.pdf_btn.setMinimumWidth(130); self.pdf_btn.setMinimumHeight(40)
        self.pdf_btn.clicked.connect(self._save_pdf)
        self.close_btn = QPushButton('بستن')
        self.close_btn.setObjectName('SecondaryButton')
        self.close_btn.setMinimumWidth(130); self.close_btn.setMinimumHeight(40)
        self.close_btn.clicked.connect(self.accept)
        toolbar.addWidget(self.close_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.pdf_btn)
        toolbar.addWidget(self.print_btn)
        layout.addLayout(toolbar)
        self.browser = QWebEngineView()
        self.browser.setHtml(self.html_content)
        layout.addWidget(self.browser)

    def _print_document(self):
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec_() != QPrintDialog.Accepted:
            return
        self.browser.page().print(printer, lambda ok: None)

    def _save_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره PDF', 'preview.pdf', 'PDF Files (*.pdf)')
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'
        self.browser.page().printToPdf(path)
        QMessageBox.information(self, 'PDF', 'فایل PDF ذخیره شد:\n' + path)
