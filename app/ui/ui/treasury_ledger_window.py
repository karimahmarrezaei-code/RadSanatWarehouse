# -*- coding: utf-8 -*-
"""گزارش گردش صندوق/بانک - حسابرسی و مغایرت با پرینت بانک"""
import os, tempfile, webbrowser
from datetime import datetime
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                             QDateEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView, QMessageBox)
from app.core.jalali import jalali_date_display_from_iso


class TreasuryLedgerWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle('گردش صندوق / بانک (حسابرسی)')
        self.resize(1250, 700)
        self.rows = []
        self._build_ui()
        self._load_accounts()

    def _build_ui(self):
        root = QVBoxLayout(self)
        f = QHBoxLayout()
        f.addWidget(QLabel('حساب:'))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(280)
        f.addWidget(self.account_combo)
        f.addWidget(QLabel('از تاریخ:'))
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-3))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat('yyyy-MM-dd')
        f.addWidget(self.date_from)
        f.addWidget(QLabel('تا تاریخ:'))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat('yyyy-MM-dd')
        f.addWidget(self.date_to)
        rb = QPushButton('بروزرسانی')
        rb.setObjectName('PrimaryButton')
        rb.clicked.connect(self.refresh)
        f.addWidget(rb)
        hb = QPushButton('خروجی HTML / چاپ')
        hb.setObjectName('SecondaryButton')
        hb.clicked.connect(self.export_html)
        f.addWidget(hb)
        f.addStretch()
        root.addLayout(f)
        self.sum_lbl = QLabel('')
        self.sum_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;padding:4px;')
        root.addWidget(self.sum_lbl)
        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels(['تاریخ', 'نوع', 'مبلغ (ریال)', 'مانده بعد از سند', 'شماره سند مبدأ', 'شرح', 'ردیف'])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        hv = self.tbl.horizontalHeader()
        hv.setSectionResizeMode(5, QHeaderView.Stretch)
        root.addWidget(self.tbl)

    def _load_accounts(self):
        try:
            with self.db.connect() as conn:
                rows = conn.execute("SELECT id, code, name, account_type, current_balance "
                                    "FROM treasury_accounts WHERE is_active=1 "
                                    "ORDER BY account_type, code").fetchall()
            self.account_combo.clear()
            for r in rows:
                self.account_combo.addItem('%s | %s (%s)' % (r[1], r[2], r[3] or '-'), r[0])
        except Exception:
            pass
        self.refresh()

    def _doc_no(self, conn, st, sid):
        try:
            if st == 'EXPENSE':
                r = conn.execute("SELECT expense_no FROM expenses WHERE id=?", (sid,)).fetchone()
            elif st in ('PAYMENT', 'PAYMENT_ENTRY', 'FINANCE'):
                r = conn.execute("SELECT fd.finance_no FROM payment_entries pe "
                                 "JOIN financial_documents fd ON fd.id=pe.financial_document_id "
                                 "WHERE pe.id=?", (sid,)).fetchone()
            else:
                r = None
            return r[0] if r and r[0] else (st or '-')
        except Exception:
            return st or '-'

    def refresh(self):
        acc_id = self.account_combo.currentData()
        if not acc_id:
            return
        d1 = self.date_from.date().toString('yyyy-MM-dd')
        d2 = self.date_to.date().toString('yyyy-MM-dd')
        self.rows = []
        try:
            with self.db.connect() as conn:
                txs = conn.execute("SELECT transaction_date, transaction_type, amount, balance_after, "
                                   "description, source_type, source_id FROM treasury_transactions "
                                   "WHERE treasury_account_id=? AND transaction_date BETWEEN ? AND ? "
                                   "ORDER BY transaction_date, id", (acc_id, d1, d2)).fetchall()
                for t in txs:
                    self.rows.append((t[0], t[1], t[2], t[3], self._doc_no(conn, t[5], t[6]), t[4] or ''))
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e))
            return
        tin = sum(int(r[2] or 0) for r in self.rows if r[1] == 'IN')
        tout = sum(int(r[2] or 0) for r in self.rows if r[1] != 'IN')
        self.sum_lbl.setText('جمع دریافت: {:,} ریال | جمع پرداخت: {:,} ریال | خالص: {:,} ریال'.format(tin, tout, tin - tout))
        self.tbl.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            vals = [jalali_date_display_from_iso(r[0]) if r[0] else '-',
                    'دریافت' if r[1] == 'IN' else 'پرداخت',
                    '{:,}'.format(int(r[2] or 0)),
                    '{:,}'.format(int(r[3] or 0)),
                    r[4], r[5], str(i + 1)]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.tbl.setItem(i, c, it)
        self.tbl.resizeColumnsToContents()

    def export_html(self):
        if not self.rows:
            QMessageBox.information(self, 'خروجی', 'داده‌ای نیست.')
            return
        acc_txt = self.account_combo.currentText()
        tr = ''
        for i, r in enumerate(self.rows):
            tr += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                jalali_date_display_from_iso(r[0]) if r[0] else '-', 'دریافت' if r[1] == 'IN' else 'پرداخت',
                '{:,}'.format(int(r[2] or 0)), '{:,}'.format(int(r[3] or 0)), r[4], r[5])
        html = ('<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8">'
                '<title>گردش حساب</title><style>body{font-family:Tahoma;background:#f5f5f5;margin:20px}'
                '.c{background:white;padding:25px;border-radius:8px}table{width:100%;border-collapse:collapse}'
                'th{background:#46505f;color:white;padding:10px}td{padding:8px;border-bottom:1px solid #e2e8f0;text-align:center}'
                'h1{text-align:center}</style></head><body><div class="c"><h1>گردش حساب: %s</h1>'
                '<p>%s تا %s</p><table><thead><tr><th>تاریخ</th><th>نوع</th><th>مبلغ</th>'
                '<th>مانده بعد</th><th>سند مبدأ</th><th>شرح</th></tr></thead><tbody>%s</tbody></table>'
                '<p style="text-align:center;color:#64748b">%s</p></div></body></html>' % (
                    acc_txt, self.date_from.date().toString('yyyy-MM-dd'),
                    self.date_to.date().toString('yyyy-MM-dd'), tr,
                    datetime.now().strftime('%Y-%m-%d %H:%M')))
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره HTML', 'treasury_ledger.html', 'HTML (*.html)')
        if path:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(html)
            webbrowser.open('file:///' + path)
