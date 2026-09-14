# -*- coding: utf-8 -*-
"""بازنویسی کامل check_due_reminder.py - اجرا: py fix_check_reminder_final.py"""
import os, shutil, py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
CR = os.path.join(ROOT, 'app', 'ui', 'check_due_reminder.py')

NEW = '''# -*- coding: utf-8 -*-
"""CheckDueReminderDialog - پیام سررسید یکپارچه: چک‌ها + مصارف مصرفی باز"""

from datetime import date
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from app.core.database import DatabaseManager


class CheckDueReminderDialog(QDialog):
    def __init__(self, db: DatabaseManager, user_data: Optional[Dict] = None, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('📅 سررسید چک‌ها و مصارف')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(760, 640)

        layout = QVBoxLayout(self)
        title = QLabel('⚠️ موارد زیر به سررسید رسیده‌اند و نیاز به اقدام دارند:')
        title.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
        layout.addWidget(title)

        lbl_checks = QLabel('📌 چک‌های سررسیدشده (پرداخت‌نشده):')
        lbl_checks.setStyleSheet('font-weight:bold;color:#2563eb;')
        layout.addWidget(lbl_checks)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['تاریخ سررسید', 'شماره چک', 'مبلغ (ریال)', 'ذی‌نفع', 'شماره سند'])
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        lbl_cons = QLabel('📌 مصارف مصرفی بازِ سررسیدشده (نیاز به تسویه):')
        lbl_cons.setStyleSheet('font-weight:bold;color:#7c3aed;')
        layout.addWidget(lbl_cons)
        self.cons_table = QTableWidget(0, 4)
        self.cons_table.setHorizontalHeaderLabels(['تاریخ سررسید', 'شماره هزینه', 'مبلغ (ریال)', 'شرح'])
        self.cons_table.verticalHeader().setVisible(False)
        layout.addWidget(self.cons_table)

        close_btn = QPushButton('بستن')
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self._load()

    def has_due_checks(self) -> bool:
        """True اگر چک سررسیدشده یا مصرف باز سررسیدشده وجود داشته باشد (نمایش یکپارچه)"""
        return self.has_due_checks_only() or self.has_due_consumables()

    def has_due_checks_only(self) -> bool:
        today = date.today().isoformat()
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute(
                    "SELECT COUNT(*) FROM payment_entries pe "
                    "JOIN payment_methods pm ON pm.id = pe.payment_method_id "
                    "WHERE pm.code = 'CHECK' AND pe.status = 'PENDING' AND pe.due_date <= ?",
                    (today,),
                ).fetchone()
                return bool(row and row[0] > 0)
        except Exception:
            return False

    def has_due_consumables(self) -> bool:
        today = date.today().isoformat()
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute(
                    "SELECT COUNT(*) FROM expenses "
                    "WHERE status = 'OPEN' AND expense_date <= ? "
                    "AND (category_id = 7 OR description LIKE 'مصرف مصرفی%')",
                    (today,),
                ).fetchone()
                return bool(row and row[0] > 0)
        except Exception:
            return False

    def _load(self) -> None:
        today = date.today().isoformat()
        # --- چک‌ها ---
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT pe.due_date, pe.check_no, pe.amount, "
                    " COALESCE(p.first_name || ' ' || p.last_name, '-'), fd.finance_no "
                    "FROM payment_entries pe "
                    "JOIN payment_methods pm ON pm.id = pe.payment_method_id "
                    "JOIN financial_documents fd ON fd.id = pe.financial_document_id "
                    "LEFT JOIN persons p ON p.id = fd.counterparty_person_id "
                    "WHERE pm.code = 'CHECK' AND pe.status = 'PENDING' AND pe.due_date <= ? "
                    "ORDER BY pe.due_date",
                    (today,),
                ).fetchall()
        except Exception:
            rows = []
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for col, v in enumerate([r[0] or '-', r[1] or '-', f"{int(r[2] or 0):,}", r[3], r[4]]):
                cell = QTableWidgetItem(str(v))
                cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, col, cell)
        self.table.resizeColumnsToContents()
        # --- مصارف باز سررسیدشده ---
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                cons = conn.execute(
                    "SELECT expense_date, expense_no, amount, description FROM expenses "
                    "WHERE status = 'OPEN' AND expense_date <= ? "
                    "AND (category_id = 7 OR description LIKE 'مصرف مصرفی%') "
                    "ORDER BY expense_date",
                    (today,),
                ).fetchall()
        except Exception:
            cons = []
        self.cons_table.setRowCount(len(cons))
        for i, r in enumerate(cons):
            desc = (r[3] or '-')
            if len(desc) > 60:
                desc = desc[:60] + '...'
            for col, v in enumerate([r[0] or '-', r[1] or '-', f"{int(r[2] or 0):,}", desc]):
                cell = QTableWidgetItem(str(v))
                cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.cons_table.setItem(i, col, cell)
        self.cons_table.resizeColumnsToContents()
'''

if os.path.exists(CR):
    shutil.copy2(CR, CR + '.bak29')
    open(CR, 'w', encoding='utf-8').write(NEW)
    print('OK - check_due_reminder.py کامل بازنویسی شد')
    try:
        py_compile.compile(CR, doraise=True)
        print('OK سینتکس: check_due_reminder')
    except Exception as e:
        print('❌ خطا:', e)
else:
    print('❌ فایل پیدا نشد')
input('Enter...')