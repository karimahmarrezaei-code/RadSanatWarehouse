# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView)
from PyQt5.QtGui import QColor
from app.repositories.general_ledger_repository import GeneralLedgerRepository

DEBIT_TYPES = ('ASSET', 'EXPENSE')


class BalanceSheetWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.repo = GeneralLedgerRepository(db)
        self.setWindowTitle('ترازنامه')
        self.resize(1000, 700); self.setLayoutDirection(Qt.RightToLeft)
        root = QVBoxLayout(self)
        self.title_lbl = QLabel('ترازنامه'); self.title_lbl.setObjectName('Title')
        root.addWidget(self.title_lbl)
        self.check_lbl = QLabel(''); root.addWidget(self.check_lbl)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['حساب', 'نوع', 'مانده'])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table)
        self._fill()

    def _bal(self, r):
        return (r['total_debit'] - r['total_credit']) if r['account_type'] in DEBIT_TYPES \
               else (r['total_credit'] - r['total_debit'])

    def _fill(self):
        accs = self.repo.list_accounts()
        assets = [r for r in accs if r['account_type'] == 'ASSET']
        liabs = [r for r in accs if r['account_type'] == 'LIABILITY']
        equities = [r for r in accs if r['account_type'] == 'EQUITY']
        income = sum(self._bal(r) for r in accs if r['account_type'] == 'INCOME')
        expense = sum(self._bal(r) for r in accs if r['account_type'] == 'EXPENSE')
        net = income - expense

        rows = []
        rows.append(('── دارایی‌ها ──', '', ''))
        ta = 0
        for r in assets:
            b = self._bal(r); ta += b; rows.append((r['name'], 'دارایی', b))
        rows.append(('جمع دارایی‌ها', '', ta))
        rows.append(('', '', ''))
        rows.append(('── بدهی‌ها ──', '', ''))
        tl = 0
        for r in liabs:
            b = self._bal(r); tl += b; rows.append((r['name'], 'بدهی', b))
        rows.append(('جمع بدهی‌ها', '', tl))
        rows.append(('', '', ''))
        rows.append(('── سرمایه ──', '', ''))
        te = 0
        for r in equities:
            b = self._bal(r); te += b; rows.append((r['name'], 'سرمایه', b))
        rows.append(('سود (زیان) انباشتهٔ دوره', 'سرمایه', net))
        rows.append(('جمع بدهی + سرمایه', '', tl + te + net))

        self.table.setRowCount(len(rows))
        for i, (name, typ, bal) in enumerate(rows):
            btxt = f"{bal:,}" if isinstance(bal, int) else bal
            for c, v in enumerate([name, typ, btxt]):
                it = QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if name.startswith('جمع') or name.startswith('──'):
                    it.setBackground(QColor('#dbeafe'))
                self.table.setItem(i, c, it)
        ok = '✔' if ta == tl + te + net else '✘'
        self.check_lbl.setText(f'دارایی: {ta:,} = بدهی+سرمایه: {tl + te + net:,} | توازن: {ok}')
        self.check_lbl.setStyleSheet('color:#10b981;font-weight:bold;')