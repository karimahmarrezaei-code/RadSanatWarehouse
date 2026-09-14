# -*- coding: utf-8 -*-
import os
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QFileDialog, QMessageBox, QTextBrowser, QApplication)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtGui import QFont, QTextDocument

# تلاش برای استفاده از موتور پیشرفته WebEngine
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False

class HtmlPreviewDialog(QDialog):
    def __init__(self, html: str, title: str = '', parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1050, 900)
        self.setLayoutDirection(Qt.RightToLeft)
        self.html_content = html
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()

        # دکمه بستن در سمت چپ
        btn_close = QPushButton("بستن")
        btn_close.setStyleSheet("padding: 8px;")
        btn_close.clicked.connect(self.accept)
        toolbar.addWidget(btn_close)
        toolbar.addStretch() # برای اینکه دکمه‌های بعدی به سمت راست بروند

        # دکمه‌ها در سمت راست
        btn_print = QPushButton("🖨 چاپ")
        btn_print.setStyleSheet("background-color: #2563eb; color: white; padding: 8px;")
        btn_print.clicked.connect(self._print_document)
        
        btn_pdf = QPushButton("💾 ذخیره PDF")
        btn_pdf.setStyleSheet("background-color: #475569; color: white; padding: 8px;")
        btn_pdf.clicked.connect(self._save_pdf)

        toolbar.addWidget(btn_print)
        toolbar.addWidget(btn_pdf)
        layout.addLayout(toolbar)

        # انتخاب موتور نمایش
        if WEB_ENGINE_AVAILABLE:
            self.viewer = QWebEngineView()
            self.viewer.setHtml(self.html_content)
        else:
            self.viewer = QTextBrowser()
            self.viewer.setFont(QFont('Tahoma', 10))
            # پاکسازی HTML برای موتور ضعیف QTextBrowser (حذف استایل‌های پیچیده)
            safe_html = self.html_content.replace('display: flex', '').replace('grid', 'table')
            self.viewer.setHtml(safe_html)

        layout.addWidget(self.viewer)

    def _print_document(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            if WEB_ENGINE_AVAILABLE:
                self.viewer.page().print(printer, lambda ok: None)
            else:
                doc = QTextDocument()
                doc.setHtml(self.html_content)
                doc.setPageSize(printer.pageRect(QPrinter.Point).size())
                doc.print_(printer)

    def _save_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره PDF", "", "PDF Files (*.pdf)")
        if not path: return
        if not path.lower().endswith('.pdf'): path += '.pdf'
        
        if WEB_ENGINE_AVAILABLE:
            self.viewer.page().printToPdf(path)
            QMessageBox.information(self, "موفقیت", "فایل با موفقیت ذخیره شد.")
        else:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            doc = QTextDocument()
            doc.setHtml(self.html_content)
            doc.setPageSize(printer.pageRect(QPrinter.Point).size())
            doc.print_(printer)
            QMessageBox.information(self, "موفقیت", "فایل با موفقیت ذخیره شد.")
