# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QTabWidget, QWidget, QHeaderView, QAbstractItemView, QDateEdit)
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QColor
from app.repositories.general_ledger_repository import GeneralLedgerRepository, TYPE_FA

DEBIT_TYPES = ('ASSET', 'EXPENSE')  # مانده = بدهکار - بستانکار


class GeneralLedgerWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.user_data = user_data or {}
        self.repo = GeneralLedgerRepository(db)
        self.setWindowTitle('دفتر کل و دفتر معین')
        self.resize(1200, 750); self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui(); self.refresh(); self._update_jalali_labels()

    def _build_ui(self):
        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel('نوع حساب:'))
        self.type_combo = QComboBox()
        self.type_combo.addItem('همه', None)
        for k, v in TYPE_FA.items(): self.type_combo.addItem(v, k)
        self.type_combo.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.type_combo)
        bar.addWidget(QLabel('از:'))
        self.date_from = QDateEdit(QDate.currentDate().addYears(-1)); self.date_from.setDisplayFormat('yyyy-MM-dd')
        self.date_from.setMinimumWidth(120)
        self.date_from.setStyleSheet('font-size:12px;')
        self.date_from.setCalendarPopup(True)
        self.date_from.setMinimumHeight(38); self.date_from.setStyleSheet('font-size:15px;')
        self.date_from.dateChanged.connect(self._update_jalali_labels)
        bar.addWidget(self.date_from)
        self.jalali_from_lbl = QLabel('-'); self.jalali_from_lbl.setStyleSheet('color:#f59e0b;font-size:14px;font-weight:bold;')
        bar.addWidget(self.jalali_from_lbl)
        bar.addWidget(QLabel('تا:'))
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setDisplayFormat('yyyy-MM-dd')
        self.date_to.setMinimumWidth(120)
        self.date_to.setStyleSheet('font-size:12px;')
        self.date_to.setCalendarPopup(True)
        self.date_to.setMinimumHeight(38); self.date_to.setStyleSheet('font-size:15px;')
        self.date_to.dateChanged.connect(self._update_jalali_labels)
        bar.addWidget(self.date_to)
        self.jalali_to_lbl = QLabel('-'); self.jalali_to_lbl.setStyleSheet('color:#f59e0b;font-size:14px;font-weight:bold;')
        bar.addWidget(self.jalali_to_lbl)
        refresh_btn = QPushButton('بروزرسانی'); refresh_btn.clicked.connect(self.refresh)
        bar.addWidget(refresh_btn); bar.addStretch()
        root.addLayout(bar)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_trial(), '📊 دفتر کل / تراز آزمایشی')
        self.tabs.addTab(self._tab_detail(), '📒 دفتر معین (جزئیات)')
        self.tabs.addTab(self._tab_journal(), '📰 دفتر روزنامه')
        root.addWidget(self.tabs, 1)

    def _tab_trial(self):
        w = QWidget(); l = QVBoxLayout(w)
        self.hint_lbl = QLabel(''); l.addWidget(self.hint_lbl)
        self.trial_table = QTableWidget(0, 6)
        self.trial_table.setHorizontalHeaderLabels(['کد', 'نام حساب', 'نوع', 'جمع بدهکار', 'جمع بستانکار', 'مانده'])
        self.trial_table.verticalHeader().setVisible(False)
        self.trial_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.trial_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.trial_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.trial_table.setColumnWidth(0, 95)
        self.trial_table.itemSelectionChanged.connect(self._load_detail)
        l.addWidget(self.trial_table)
        self.total_lbl = QLabel(''); l.addWidget(self.total_lbl)
        return w

    def _tab_detail(self):
        w = QWidget(); l = QVBoxLayout(w)
        self.detail_lbl = QLabel('یک حساب از جدول دفتر کل انتخاب کنید'); l.addWidget(self.detail_lbl)
        self.detail_table = QTableWidget(0, 6)
        self.detail_table.setHorizontalHeaderLabels(['تاریخ', 'سند', 'شرح', 'بدهکار', 'بستانکار', 'مانده'])
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.detail_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.detail_table.setColumnWidth(0, 95)
        l.addWidget(self.detail_table)
        return w


    def _update_jalali_labels(self):
        from app.core.jalali import jalali_date_display_from_iso
        self.jalali_from_lbl.setText(jalali_date_display_from_iso(self.date_from.date().toString('yyyy-MM-dd')))
        self.jalali_to_lbl.setText(jalali_date_display_from_iso(self.date_to.date().toString('yyyy-MM-dd')))


    def _tab_journal(self):
        w = QWidget(); l = QVBoxLayout(w)
        self.journal_table = QTableWidget(0, 6)
        self.journal_table.setHorizontalHeaderLabels(['تاریخ', 'سند', 'شرح سند', 'حساب', 'بدهکار', 'بستانکار'])
        self.journal_table.verticalHeader().setVisible(False)
        self.journal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.journal_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.journal_table.setColumnWidth(0, 95)
        l.addWidget(self.journal_table)
        return w

    def _load_journal(self):
        q = """SELECT je.entry_no, je.entry_date, je.description AS entry_desc,
                      la.code || ' | ' || la.name AS account,
                      jl.debit_amount, jl.credit_amount
               FROM journal_lines jl
               JOIN journal_entries je ON je.id = jl.journal_entry_id
               JOIN ledger_accounts la ON la.id = jl.account_id
               WHERE je.entry_date BETWEEN ? AND ?
               ORDER BY je.entry_date, je.id, jl.line_no"""
        with self.db.connect() as c:
            rows = c.execute(q, (self.date_from.date().toString('yyyy-MM-dd'),
                                 self.date_to.date().toString('yyyy-MM-dd'))).fetchall()
        self.journal_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r['entry_date'], r['entry_no'], r['entry_desc'] or '-', r['account'],
                    f"{r['debit_amount']:,}" if r['debit_amount'] else '', f"{r['credit_amount']:,}" if r['credit_amount'] else '']
            for cidx, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.journal_table.setItem(i, cidx, it)

    def refresh(self):
        rows = self.repo.list_accounts(self.type_combo.currentData())
        self.trial_table.setRowCount(len(rows))
        td = tc = 0
        for i, r in enumerate(rows):
            bal = (r['total_debit'] - r['total_credit']) if r['account_type'] in DEBIT_TYPES \
                  else (r['total_credit'] - r['total_debit'])
            td += r['total_debit']; tc += r['total_credit']
            vals = [r['code'], r['name'], TYPE_FA.get(r['account_type'], r['account_type']),
                    f"{r['total_debit']:,}", f"{r['total_credit']:,}", f"{bal:,}"]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trial_table.setItem(i, c, it)
        ok = '✔' if td == tc else '✘'
        self._load_journal()
        self.total_lbl.setText(f'جمع بدهکار: {td:,} | جمع بستانکار: {tc:,} | توازن: {ok}')
        if not self.repo.has_entries():
            self.hint_lbl.setText('⚠️ هنوز سند حسابداری (journal) ثبت نشده؛ پس از ثبت اسناد مالی، این دفتر پر می‌شود.')
            self.hint_lbl.setStyleSheet('color:#f59e0b;')
        else:
            self.hint_lbl.setText('')

    def _load_detail(self):
        r = self.trial_table.currentRow()
        if r < 0: return
        code = self.trial_table.item(r, 0).text()
        acc = next((a for a in self.repo.list_accounts() if a['code'] == code), None)
        if not acc: return
        self.detail_lbl.setText(f'دفتر معین: {acc["name"]} ({acc["code"]})')
        lines = self.repo.account_lines(acc['id'],
            self.date_from.date().toString('yyyy-MM-dd'), self.date_to.date().toString('yyyy-MM-dd'))
        self.detail_table.setRowCount(len(lines))
        bal = 0
        for i, ln in enumerate(lines):
            d, c = ln['debit_amount'] or 0, ln['credit_amount'] or 0
            bal += (d - c) if acc['account_type'] in DEBIT_TYPES else (c - d)
            vals = [ln['entry_date'], ln['entry_no'],
                    (ln['description'] or ln['entry_desc'] or '-') + (f" | {ln['person_name']}" if ln['person_name'] else ''),
                    f"{d:,}", f"{c:,}", f"{bal:,}"]
            for cidx, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.detail_table.setItem(i, cidx, it)
