# patch_preview_dialog.py
import os
import shutil

target_path = os.path.join("app", "ui", "html_preview_dialog.py")

if not os.path.exists(target_path):
    print(f"❌ فایل مورد نظر یافت نشد: {target_path}")
    exit(1)

# ایجاد نسخه پشتیبان
backup_path = target_path + ".bak"
shutil.copyfile(target_path, backup_path)
print(f"💾 بکاپ در {backup_path} ذخیره شد.")

new_code = '''# -*- coding: utf-8 -*-
"""
HtmlPreviewDialog - پنجره بهینه‌شده پیش‌نمایش فاکتور و اسناد
"""
import os
import tempfile
import subprocess
from PyQt5.QtCore import Qt, QUrl, QMimeData
from PyQt5.QtGui import QFont, QTextDocument
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QTextBrowser, QApplication
)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

class HtmlPreviewDialog(QDialog):
    def __init__(self, html_content_or_path, title='پیش‌نمایش', parent=None):
        super(HtmlPreviewDialog, self).__init__(parent)
        self.setWindowTitle(title)
        
        # افزودن دکمه‌های ماکسیمایز و مینیمایز
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)
        self.setLayoutDirection(Qt.RightToLeft)
        
        # تنظیم اندازه متناسب با صفحه نمایش
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            w = min(1050, int(geo.width() * 0.88))
            h = min(880, int(geo.height() * 0.88))
            self.resize(w, h)
        else:
            self.resize(980, 750)

        # پردازش ورودی (فایل یا متن html)
        if isinstance(html_content_or_path, str) and os.path.isfile(html_content_or_path):
            try:
                with open(html_content_or_path, 'r', encoding='utf-8') as f:
                    self.html_content = f.read()
            except Exception:
                self.html_content = html_content_or_path
        else:
            self.html_content = str(html_content_or_path)

        self._build_ui()

    def _toolbar(self):
        bar = QHBoxLayout()
        bar.setSpacing(10)

        btn_print = QPushButton('🖨️ چاپ')
        btn_print.setFixedHeight(38)
        btn_print.setStyleSheet('QPushButton{background:#2563eb;color:#fff;font-weight:bold;padding:0 15px;border-radius:5px;}')
        btn_print.clicked.connect(self._print_document)
        bar.addWidget(btn_print)

        btn_pdf = QPushButton('💾 ذخیره PDF')
        btn_pdf.setFixedHeight(38)
        btn_pdf.setStyleSheet('QPushButton{background:#475569;color:#fff;font-weight:bold;padding:0 15px;border-radius:5px;}')
        btn_pdf.clicked.connect(self._save_pdf)
        bar.addWidget(btn_pdf)

        btn_share = QPushButton('📤 اشتراک‌گذاری (PDF)')
        btn_share.setFixedHeight(38)
        btn_share.setStyleSheet('QPushButton{background:#0ea5e9;color:#fff;font-weight:bold;padding:0 15px;border-radius:5px;}')
        btn_share.clicked.connect(self._share_pdf)
        bar.addWidget(btn_share)

        bar.addStretch()

        btn_close = QPushButton('بستن')
        btn_close.setFixedHeight(38)
        btn_close.setStyleSheet('QPushButton{background:#e2e8f0;color:#1e293b;padding:0 20px;border-radius:5px;}')
        btn_close.clicked.connect(self.accept)
        bar.addWidget(btn_close)

        return bar

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        layout.addLayout(self._toolbar())

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setFont(QFont('Tahoma', 10))
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        self.browser.setHtml(self.html_content)
        layout.addWidget(self.browser, 1)

    def _make_doc(self):
        doc = QTextDocument()
        doc.setDefaultFont(QFont('Tahoma', 9))
        doc.setHtml(self.html_content)
        return doc

    def _print_document(self):
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec_() == QDialog.Accepted:
            doc = self._make_doc()
            doc.print_(printer)

    def _save_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره PDF', 'invoice.pdf', 'PDF Files (*.pdf)')
        if not path:
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        doc = self._make_doc()
        doc.print_(printer)
        QMessageBox.information(self, 'موفق', 'فایل PDF با موفقیت ذخیره شد.')

    def _share_pdf(self):
        export_dir = os.path.join(os.getcwd(), 'exports', 'share')
        os.makedirs(export_dir, exist_ok=True)
        pdf_path = os.path.join(export_dir, f'share_{os.getpid()}.pdf')

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(pdf_path)
        doc = self._make_doc()
        doc.print_(printer)

        cb = QApplication.clipboard()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(pdf_path)])
        cb.setMimeData(mime)

        res = QMessageBox.question(
            self, 'اشتراک‌گذاری',
            'فایل PDF کپی شد (می‌توانید در پیام‌رسان Paste کنید).\\nآیا پوشه فایل باز شود؟',
            QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            subprocess.Popen(f'explorer /select,"{pdf_path}"')
'''

with open(target_path, 'w', encoding='utf-8') as f:
    f.write(new_code)

print("✅ فایل app/ui/html_preview_dialog.py با موفقیت به‌روزرسانی شد.")
