# -*- coding: utf-8 -*-
"""حفظ کامل API قدیمی پیش‌نمایش - اجرا: python fix_preview_api.py"""
import os, re, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

g = subprocess.run(['git', 'show', 'HEAD:app/ui/html_preview_dialog.py'], capture_output=True)
orig = g.stdout.decode('utf-8', errors='replace') if g.returncode == 0 else ''
defs = re.findall(r'(?m)^def (\w+)\s*\(', orig)
classes = re.findall(r'(?m)^class (\w+)\s*\(', orig)
print('1) API اصلی:', 'classes=', classes, 'defs=', defs)
NAME = classes[0] if classes else 'HtmlPreviewDialog'

TPL = '''# -*- coding: utf-8 -*-
"""پیش‌نمایش سند - QTextBrowser (سبک، پایدار، بدون وب‌انجین)"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPrinter, QTextDocument
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTextBrowser, QFileDialog, QPrintDialog, QWidget)


class {NAME}(QDialog):
    def __init__(self, *args, **kwargs):
        parent = kwargs.pop('parent', None)
        super().__init__(parent)
        html = kwargs.pop('html', '') or ''
        title = kwargs.pop('title', '') or ''
        for a in args:
            if isinstance(a, QWidget):
                parent = a
            elif isinstance(a, str) and '<' in a and '>' in a:
                html = a
            elif isinstance(a, str):
                title = title or a
        self.setWindowTitle(title or 'پیش‌نمایش سند')
        self.resize(1000, 720)
        self.setLayoutDirection(Qt.RightToLeft)
        self._html = html
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
        self.view.setStyleSheet('QTextBrowser {{ background:#ffffff; }}')
        lay.addWidget(self.view)
        if self._html:
            self.view.setHtml(self._html)
        self.btn_print.clicked.connect(self._print)
        self.btn_pdf.clicked.connect(self._pdf)
        self.btn_share.clicked.connect(self._share)
        self.btn_close.clicked.connect(self.close)

    def set_html(self, h):
        self._html = h or ''
        self.view.setHtml(self._html)

    def setHtml(self, h):
        self.set_html(h)

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


WebEnginePreviewDialog = {NAME}
HtmlPreviewDialog = {NAME}
'''

COMPAT = '''

def {FN}(*args, **kwargs):
    try:
        html = ''
        title = ''
        parent = None
        for a in args:
            if isinstance(a, str) and '<' in a and '>' in a:
                html = a
            elif isinstance(a, str):
                title = title or a
            else:
                parent = a
        return {NAME}(html, title, parent).exec_()
    except Exception:
        return None
'''

content = TPL.replace('{NAME}', NAME)
for fn in defs:
    content += COMPAT.replace('{FN}', fn).replace('{NAME}', NAME)

for rel in ('app/ui/html_preview_dialog.py', 'app/ui/ui/html_preview_dialog.py'):
    p = os.path.join(ROOT, rel)
    if os.path.isdir(os.path.dirname(p)):
        open(p, 'w', encoding='utf-8').write(content)
        py_compile.compile(p, doraise=True)
        print('2)', rel, '✔')

# بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
print('3) بیلد...')
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
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')