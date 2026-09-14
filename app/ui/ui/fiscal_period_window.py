# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDateEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QFormLayout, QMessageBox)
from PyQt5.QtGui import QColor
from app.repositories.fiscal_period_repository import FiscalPeriodRepository
from app.repositories.general_ledger_repository import GeneralLedgerRepository


class FiscalPeriodWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.user_data = user_data or {}
        self.repo = FiscalPeriodRepository(db)
        self.setWindowTitle('مدیریت دوره‌های مالی')
        self.resize(950, 650); self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui(); self.refresh(); self._update_jalali()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self.check_lbl = QLabel(''); root.addWidget(self.check_lbl)

        g = QGroupBox('دورهٔ جدید')
        f = QFormLayout(g)
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText('مثلاً: مرداد ۱۴۰۵')
        self.start_date = QDateEdit(QDate.currentDate().addMonths(-1)); self.start_date.setDisplayFormat('yyyy-MM-dd')
        self.start_date.setMinimumHeight(34); self.start_date.setStyleSheet('font-size:14px;')
        self.end_date = QDateEdit(QDate.currentDate()); self.end_date.setDisplayFormat('yyyy-MM-dd')
        self.end_date.setMinimumHeight(34); self.end_date.setStyleSheet('font-size:14px;')
        self.start_jalali_lbl = QLabel('-'); self.start_jalali_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        self.end_jalali_lbl = QLabel('-'); self.end_jalali_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        self._jalali_pairs = [(self.start_date, self.start_jalali_lbl), (self.end_date, self.end_jalali_lbl)]
        self.start_date.dateChanged.connect(self._update_jalali)
        self.end_date.dateChanged.connect(self._update_jalali)
        f.addRow('نام دوره:', self.name_edit)
        f.addRow('از تاریخ:', self.start_date)
        f.addRow('', self.start_jalali_lbl)
        f.addRow('تا تاریخ:', self.end_date)
        f.addRow('', self.end_jalali_lbl)
        create_btn = QPushButton('➕ ایجاد دوره باز'); create_btn.clicked.connect(self._create)
        f.addRow(create_btn)
        root.addWidget(g)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['نام دوره', 'از', 'تا', 'وضعیت', 'بسته‌شده در'])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        bar = QHBoxLayout()
        close_btn = QPushButton('🔒 بستن دوره'); close_btn.clicked.connect(self._close)
        reopen_btn = QPushButton('🔓 بازگشایی (فقط مدیر)'); reopen_btn.clicked.connect(self._reopen)
        bar.addWidget(close_btn); bar.addWidget(reopen_btn); bar.addStretch()
        root.addLayout(bar)


    def _update_jalali(self):
        from app.core.jalali import jalali_date_display_from_iso
        for ed, lb in getattr(self, '_jalali_pairs', []):
            lb.setText(jalali_date_display_from_iso(ed.date().toString('yyyy-MM-dd')))

    def refresh(self):
        # چک‌لیست توازن
        accs = GeneralLedgerRepository(self.db).list_accounts()
        td = sum(a['total_debit'] for a in accs); tc = sum(a['total_credit'] for a in accs)
        ok = '✔' if td == tc else '✘'
        self.check_lbl.setText(f'پیش‌نیاز بستن: توازن تراز آزمایشی {ok} (بدهکار {td:,} = بستانکار {tc:,})')
        self.check_lbl.setStyleSheet('color:#10b981;' if td == tc else 'color:#dc2626;')

        rows = self.repo.list_periods()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r['name'], r['start_date'], r['end_date'],
                    '🔒 بسته' if r['status'] == 'CLOSED' else '🔓 باز', r['closed_at'] or '-']
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if r['status'] == 'CLOSED': it.setForeground(QColor('#dc2626'))
                self.table.setItem(i, c, it)

    def _selected_id(self):
        r = self.table.currentRow()
        if r < 0: return None
        return self.repo.list_periods()[r]['id'] if r < len(self.repo.list_periods()) else None

    def _create(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, 'دوره', 'نام دوره را وارد کنید.'); return
        self.repo.create(self.name_edit.text().strip(),
                         self.start_date.date().toString('yyyy-MM-dd'),
                         self.end_date.date().toString('yyyy-MM-dd'),
                         self.user_data.get('id', 1))
        QMessageBox.information(self, 'دوره', 'دورهٔ باز ایجاد شد.')
        self.refresh()

    def _close(self):
        pid = self._selected_id()
        if not pid: return
        if QMessageBox.question(self, 'بستن دوره', 'پس از بستن، هیچ سندی در این بازه قابل ثبت/ویرایش نیست. ادامه می‌دهید؟',
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        self.repo.close(pid, self.user_data.get('id', 1)); self.refresh()

    def _reopen(self):
        if self.user_data.get('role_code') != 'ADMIN':
            QMessageBox.warning(self, 'دسترسی', 'بازگشایی دوره فقط برای مدیر مجاز است.'); return
        pid = self._selected_id()
        if not pid: return
        self.repo.reopen(pid, self.user_data.get('id', 1)); self.refresh()