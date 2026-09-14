# -*- coding: utf-8 -*-
"""
پیش‌نمایش HTML مدرن با پشتیبانی از WebEngine و fallback هوشمند به QTextBrowser
"""
import os
import sys

os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX', '1')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-web-security --allow-file-access-from-files')

from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QTextBrowser, QApplication
)

_WEBENGINE_AVAILABLE = True
try:
    from PyQt5.QtWebEngineWidgets import (
        QWebEngineView, QWebEngineProfile,
        QWebEngineSettings, QWebEnginePage
    )
except ImportError:
    _WEBENGINE_AVAILABLE = False

from PyQt5.QtPrintSupport import QPrinter, QPrintDialog


class HtmlPreviewDialog(QDialog):
    LOAD_TIMEOUT_MS = 6000

    def __init__(self, html: str, title: str = '', parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or 'پیش‌نمایش سند')
        self.resize(1150, 800)
        self.setLayoutDirection(Qt.RightToLeft)

        self.html_content = html or ''
        self._base_url = QUrl('file:///')
        self._fallback_used = False
        self._loaded_ok = False

        self._build_ui()

    def _resolve_content(self):
        """در صورتی که ورودی آدرس فایل باشد محتوا و پوشه مرجع را لود می‌کند."""
        h = self.html_content
        if bool(h) and '<' not in h and os.path.isfile(h):
            try:
                folder = os.path.dirname(os.path.abspath(h))
                self._base_url = QUrl.fromLocalFile(folder + os.sep)
                with open(h, encoding='utf-8', errors='replace') as f:
                    h = f.read()
            except Exception:
                pass
        self.html_content = h
        return h

    def _setup_webengine(self):
        self.profile = QWebEngineProfile(self)
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, False)
        settings.setAttribute(QWebEngineSettings.ShowScrollBars, True)

        self.page = QWebEnginePage(self.profile, self)
        self.browser = QWebEngineView(self)
        self.browser.setPage(self.page)

        self._resolve_content()
        self.browser.setHtml(self.html_content, self._base_url)

        self.browser.loadFinished.connect(self._on_load_finished)

        # تایمر اضطراری در صورتی که لود موتور بی‌پاسخ بماند
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_timeout)
        self._timeout_timer.start(self.LOAD_TIMEOUT_MS)

    def _on_load_finished(self, ok):
        if hasattr(self, '_timeout_timer'):
            self._timeout_timer.stop()
        if ok:
            self._loaded_ok = True
        else:
            self._fallback_to_text_browser()

    def _on_timeout(self):
        if not self._loaded_ok:
            self._fallback_to_text_browser()

    def _fallback_to_text_browser(self):
        if self._fallback_used:
            return
        self._fallback_used = True

        try:
            self.browser.setParent(None)
            self.browser.deleteLater()
        except Exception:
            pass

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(False)
        self.browser.setHtml(self.html_content)
        self.layout().addWidget(self.browser, 1)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # دکمه‌های ابزار بالا
        toolbar = QHBoxLayout()

        self.close_btn = QPushButton('بستن')
        self.close_btn.setMinimumHeight(38)
        self.close_btn.setMinimumWidth(100)
        self.close_btn.clicked.connect(self.accept)
        toolbar.addWidget(self.close_btn)

        toolbar.addStretch()

        self.save_html_btn = QPushButton('📄 ذخیره HTML')
        self.save_html_btn.setMinimumHeight(38)
        self.save_html_btn.setMinimumWidth(120)
        self.save_html_btn.clicked.connect(self._save_html)
        toolbar.addWidget(self.save_html_btn)

        self.pdf_btn = QPushButton('💾 ذخیره PDF')
        self.pdf_btn.setMinimumHeight(38)
        self.pdf_btn.setMinimumWidth(120)
        self.pdf_btn.clicked.connect(self._save_pdf)
        toolbar.addWidget(self.pdf_btn)

        self.print_btn = QPushButton('🖨 چاپ')
        self.print_btn.setMinimumHeight(38)
        self.print_btn.setMinimumWidth(120)
        self.print_btn.clicked.connect(self._print_document)
        toolbar.addWidget(self.print_btn)

        layout.addLayout(toolbar)

        if _WEBENGINE_AVAILABLE:
            try:
                self._setup_webengine()
                layout.addWidget(self.browser, 1)
            except Exception:
                self._fallback_to_text_browser()
        else:
            self._fallback_to_text_browser()

    def _print_document(self):
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec_() != QPrintDialog.Accepted:
            return

        if _WEBENGINE_AVAILABLE and isinstance(self.browser, QWebEngineView):
            self.browser.page().print(printer, lambda ok: self._notify_print_status(ok))
        else:
            from PyQt5.QtGui import QTextDocument
            doc = QTextDocument()
            doc.setHtml(self.html_content)
            doc.setPageSize(printer.pageRect(QPrinter.Point).size())
            doc.print_(printer)

    def _notify_print_status(self, ok):
        if not ok:
            QMessageBox.warning(self, 'خطا در چاپ', 'فرایند چاپ انجام نشد.')

    def _save_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره خروجی PDF', 'document.pdf', 'PDF Files (*.pdf)')
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'

        if _WEBENGINE_AVAILABLE and isinstance(self.browser, QWebEngineView):
            def _pdf_callback(p_path, success):
                if success:
                    QMessageBox.information(self, 'موفقیت', f'فایل PDF با موفقیت ذخیره شد:\n{p_path}')
                else:
                    QMessageBox.warning(self, 'خطا', 'ایجاد فایل PDF ناموفق بود.')

            self.browser.page().pdfPrintingFinished.connect(
                lambda p, ok: _pdf_callback(path, ok)
            )
            self.browser.page().printToPdf(path)
        else:
            from PyQt5.QtGui import QTextDocument
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            doc = QTextDocument()
            doc.setHtml(self.html_content)
            doc.setPageSize(printer.pageRect(QPrinter.Point).size())
            doc.print_(printer)
            QMessageBox.information(self, 'موفقیت', f'فایل PDF با موفقیت ذخیره شد:\n{path}')

    def _save_html(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره HTML', 'document.html', 'HTML Files (*.html)')
        if not path:
            return
        if not path.lower().endswith('.html'):
            path += '.html'
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.html_content)
            QMessageBox.information(self, 'موفقیت', f'فایل HTML ذخیره شد:\n{path}')
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ذخیره‌سازی: {e}')
