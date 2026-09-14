# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QFormLayout,
    QMessageBox, QWidget)
from app.repositories.bank_reconciliation_repository import BankReconciliationRepository


class BankReconciliationWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.user_data = user_data or {}
        self.repo = BankReconciliationRepository(db)
        self.setWindowTitle('مغایرت‌گیری بانکی')
        self.resize(1100, 700); self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui(); self._load_banks(); self._update_jalali()

    def _build_ui(self):
        root = QVBoxLayout(self)
        top = QGroupBox('انتخاب حساب و صورت‌حساب')
        f = QFormLayout(top)
        self.bank_combo = QComboBox(); self.bank_combo.currentIndexChanged.connect(self._load_account)
        self.statement_date = QDateEdit(QDate.currentDate()); self.statement_date.setDisplayFormat('yyyy-MM-dd')
        self.statement_date.setMinimumHeight(34); self.statement_date.setStyleSheet('font-size:14px;')
        self.stmt_jalali_lbl = QLabel('-'); self.stmt_jalali_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        self._jalali_pairs = [(self.statement_date, self.stmt_jalali_lbl)]
        self.statement_date.dateChanged.connect(self._update_jalali)
        self.statement_balance = QLineEdit(); self.statement_balance.setPlaceholderText('موجودی طبق صورت‌حساب بانک (ریال)')
        self.statement_balance.textChanged.connect(self._calc)
        self.book_lbl = QLabel('0'); self.diff_lbl = QLabel('0')
        self.diff_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        f.addRow('حساب بانکی:', self.bank_combo)
        f.addRow('موجودی طبق دفتر:', self.book_lbl)
        f.addRow('تاریخ صورت‌حساب:', self.statement_date)
        f.addRow('', self.stmt_jalali_lbl)
        f.addRow('موجودی طبق بانک:', self.statement_balance)
        f.addRow('اختلاف (بانک − دفتر):', self.diff_lbl)
        save_btn = QPushButton('💾 ثبت مغایرت'); save_btn.clicked.connect(self._save)
        f.addRow(save_btn)
        root.addWidget(top)

        g = QGroupBox('گردش‌های حساب (برای یافتن علت مغایرت)')
        v = QVBoxLayout(g)
        self.tx_table = QTableWidget(0, 5)
        self.tx_table.setHorizontalHeaderLabels(['تاریخ', 'نوع', 'مبلغ', 'مانده بعد از', 'شرح'])
        self.tx_table.verticalHeader().setVisible(False)
        self.tx_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(self.tx_table)
        root.addWidget(g, 1)

        h = QGroupBox('سابقهٔ مغایرت‌های این حساب')
        hv = QVBoxLayout(h)
        self.hist_table = QTableWidget(0, 4)
        self.hist_table.setHorizontalHeaderLabels(['تاریخ صورت‌حساب', 'دفتر', 'بانک', 'اختلاف'])
        self.hist_table.verticalHeader().setVisible(False)
        self.hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        hv.addWidget(self.hist_table)
        root.addWidget(h)


    def _update_jalali(self):
        from app.core.jalali import jalali_date_display_from_iso
        for ed, lb in getattr(self, '_jalali_pairs', []):
            lb.setText(jalali_date_display_from_iso(ed.date().toString('yyyy-MM-dd')))

    def _load_banks(self):
        self.banks = self.repo.list_banks()
        self.bank_combo.clear()
        for b in self.banks:
            self.bank_combo.addItem(f"{b['code']} | {b['name']}", b['id'])

    def _load_account(self):
        bid = self.bank_combo.currentData()
        if not bid: return
        b = next(x for x in self.banks if x['id'] == bid)
        self.book_bal = int(b['current_balance'] or 0)
        self.book_lbl.setText(f"{self.book_bal:,} ریال")
        rows = self.repo.transactions(bid)
        self.tx_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r['transaction_date'], r['transaction_type'], f"{r['amount']:,}",
                    f"{r['balance_after']:,}", r['description'] or '-']
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tx_table.setItem(i, c, it)
        hist = self.repo.history(bid)
        self.hist_table.setRowCount(len(hist))
        for i, r in enumerate(hist):
            vals = [r['statement_date'], f"{r['book_balance']:,}", f"{r['statement_balance']:,}", f"{r['difference']:,}"]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.hist_table.setItem(i, c, it)
        self._calc()

    def _calc(self):
        digits = ''.join(ch for ch in self.statement_balance.text() if ch.isdigit())
        stmt = int(digits) if digits else 0
        diff = stmt - getattr(self, 'book_bal', 0)
        self.diff_lbl.setText(f"{diff:,} ریال" + (' ✔ بدون مغایرت' if diff == 0 else ''))

    def _save(self):
        bid = self.bank_combo.currentData()
        if not bid: return
        digits = ''.join(ch for ch in self.statement_balance.text() if ch.isdigit())
        stmt = int(digits) if digits else 0
        self.repo.save(bid, self.statement_date.date().toString('yyyy-MM-dd'),
                       getattr(self, 'book_bal', 0), stmt, '', self.user_data.get('id', 1))
        QMessageBox.information(self, 'مغایرت', 'مغایرت بانکی ثبت و به سابقه اضافه شد.')
        self._load_account()