# -*- coding: utf-8 -*-
"""پیش‌نمایش پایدار با QTextBrowser - اجرا: python fix_preview_textbrowser.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

CONTENT = '''# -*- coding: utf-8 -*-
"""پیش‌نمایش سند - QTextBrowser (سبک و پایدار، بدون وب‌انجین)"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPrinter, QTextDocument
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTextBrowser, QFileDialog, QPrintDialog)


class WebEnginePreviewDialog(QDialog):
    def __init__(self, html='', title='', parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or 'پیش‌نمایش سند')
        self.resize(1000, 720)
        self.setLayoutDirection(Qt.RightToLeft)
        self._html = html or ''
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.btn_print = QPushButton('چاپ')
        self.btn_pdf = QPushButton('ذخیره PDF')
        self.btn_share = QPushButton('اشتراک')
        self.btn_close = QPushButton('بستن')
        for b in (self.btn_print, self.btn_pdf, self.btn_share, self.btn_close):
            top.addWidget(b)
        top.addStretch(1)
        lay.addLayout(top)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(False)
        self.view.setStyleSheet('QTextBrowser { background:#ffffff; }')
        lay.addWidget(self.view)
        self.view.setHtml(self._html)
        self.btn_print.clicked.connect(self._print)
        self.btn_pdf.clicked.connect(self._pdf)
        self.btn_share.clicked.connect(self._share)
        self.btn_close.clicked.connect(self.close)

    def _doc(self):
        doc = QTextDocument()
        doc.setHtml(self._html)
        return doc

    def _print(self):
        pr = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(pr, self)
        if dlg.exec_() == QPrintDialog.Accepted:
            self._doc().print_(pr)

    def _pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره PDF', 'document.pdf', 'PDF (*.pdf)')
        if path:
            pr = QPrinter(QPrinter.HighResolution)
            pr.setOutputFormat(QPrinter.PdfFormat)
            pr.setOutputFileName(path)
            self._doc().print_(pr)

    def _share(self):
        path, _ = QFileDialog.getSaveFileName(self, 'اشتراک HTML', 'document.html', 'HTML (*.html)')
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self._html)
'''

for rel in ('app/ui/webengine_preview.py', 'app/ui/ui/webengine_preview.py'):
    p = os.path.join(ROOT, rel)
    if os.path.isdir(os.path.dirname(p)):
        open(p, 'w', encoding='utf-8').write(CONTENT)
        py_compile.compile(p, doraise=True)
        print('1)', rel, '✔')

# بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
print('2) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('❌ بیلد ناموفق'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
dst_app = os.path.join(DST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql', '.py')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn); rel2 = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel2)
            os.makedirs(os.path.dirname(tgt), exist_ok=True); shutil.copy2(src, tgt)
if os.path.exists(keep):
    os.makedirs(os.path.join(DST, '_internal', 'data'), exist_ok=True)
    shutil.copy2(keep, db)
    print('2) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('3) تمام ✔')
input('Enter...')