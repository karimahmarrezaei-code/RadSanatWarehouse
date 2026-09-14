# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox, QTextEdit)
from app.core import license_manager as LM

class LicenseActivationDialog(QDialog):
    def __init__(self, parent=None, expired=False):
        super().__init__(parent)
        self.action = 'exit'
        self.setWindowTitle('فعال‌سازی لایسنس — راد صنعت نوین')
        self.resize(480, 280); self.setLayoutDirection(Qt.RightToLeft)
        root = QVBoxLayout(self)
        if expired:
            root.addWidget(QLabel('⛔ لایسنس این نصب به پایان رسیده است.\nبرای تمدید/خرید با راد صنعت نوین تماس بگیرید.'))
        else:
            root.addWidget(QLabel('این نصب فاقد لایسنس معتبر است.'))
        root.addWidget(QLabel('کد لایسنس را وارد کنید:'))
        self.code_edit = QTextEdit(); self.code_edit.setMaximumHeight(90)
        root.addWidget(self.code_edit)
        bar = QHBoxLayout()
        act = QPushButton('🔑 فعال‌سازی'); act.clicked.connect(self._activate); bar.addWidget(act)
        if LM.check() is None:
            demo = QPushButton('🎁 شروع دمو ۷روزه'); demo.clicked.connect(self._demo); bar.addWidget(demo)
        ext = QPushButton('خروج'); ext.clicked.connect(self._exit); bar.addWidget(ext)
        bar.addStretch(); root.addLayout(bar)
        root.addWidget(QLabel('نرم‌افزار متعلق به راد صنعت نوین است.'))

    def _activate(self):
        code = self.code_edit.toPlainText().strip()
        p = LM.parse_code(code)
        if not p:
            QMessageBox.warning(self, 'خطا', 'کد لایسنس نامعتبر است.'); return
        if p.get('m') and p['m'] != LM.machine_fingerprint():
            QMessageBox.warning(self, 'خطا', 'این لایسنس برای دستگاه دیگری صادر شده است.'); return
        LM.save_license(code)
        self.action = 'activated'; self.accept()

    def _demo(self):
        self.action = 'demo'; self.accept()

    def _exit(self):
        self.action = 'exit'; self.accept()
