# -*- coding: utf-8 -*-
"""
consumable_report_window.py - گزارش خرید اقلام مصرفی (از تاریخ تا تاریخ) v2

نمایش:
  - ردیف، قلم مصرفی، تعداد (از ستون quantity)، تاریخ درج (شمسی)، مبلغ کل
  - جمع کل خریداری‌شده

استفاده:
    from app.ui.consumable_report_window import ConsumableReportWindow
    ConsumableReportWindow(db, user_data, parent).exec_()
"""
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QMessageBox, QDateEdit, QHeaderView,
    QAbstractItemView, QGroupBox,
)

from app.core.jalali import jalali_date_display_from_iso


class ConsumableReportWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('📊 گزارش خرید اقلام مصرفی')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(850, 600)
        self._build_ui()
        self._run()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)

        filter_group = QGroupBox('بازه تاریخ')
        fh = QHBoxLayout(filter_group)
        fh.addWidget(QLabel('از:'))
        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat('yyyy-MM-dd')
        fh.addWidget(self.date_from)
        fh.addWidget(QLabel('تا:'))
        self.date_to = QDateEdit(QDate.currentDate().addDays(365))
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat('yyyy-MM-dd')
        fh.addWidget(self.date_to)
        apply_btn = QPushButton('محاسبه')
        apply_btn.setObjectName('PrimaryButton')
        apply_btn.clicked.connect(self._run)
        fh.addWidget(apply_btn)
        fh.addStretch()
        root.addWidget(filter_group)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'ردیف', 'کد قلم', 'قلم مصرفی', 'تعداد', 'تاریخ درج (شمسی)', 'مبلغ کل (ریال)'
        ])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        total_row = QHBoxLayout()
        total_row.addStretch()
        self.total_lbl = QLabel('جمع کل: 0 ریال')
        self.total_lbl.setStyleSheet('font-size: 16px; font-weight: bold; color: #2563eb;')
        total_row.addWidget(self.total_lbl)
        root.addLayout(total_row)

        btns = QHBoxLayout()
        close_btn = QPushButton('بستن')
        close_btn.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(close_btn)
        root.addLayout(btns)

    def _run(self):
        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        if date_from > date_to:
            QMessageBox.warning(self, 'خطا', 'تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.')
            return

        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                # خواندن expenses مصرفی با تعداد و کد قلم
                rows = conn.execute(
                    'SELECT e.id, e.expense_no, e.expense_date, e.description, e.amount, '
                    'COALESCE(e.quantity, 1), COALESCE(ci.code, \'\'), '
                    'COALESCE(ci.name, e.description) '
                    'FROM expenses e '
                    'LEFT JOIN consumable_items ci ON ci.id = e.consumable_item_id '
                    'WHERE e.expense_date BETWEEN ? AND ? '
                    "AND (e.category_id = 7 OR e.description LIKE 'مصرف مصرفی%') "
                    'ORDER BY e.expense_date, e.id',
                    (date_from, date_to),
                ).fetchall()
        except Exception as e:
            # اگر ستون quantity/consumable_item_id نبود
            try:
                with self.db.connect() as conn:
                    conn.row_factory = None
                    rows = conn.execute(
                        'SELECT id, expense_no, expense_date, description, amount, 1, \'\', description '
                        'FROM expenses '
                        'WHERE expense_date BETWEEN ? AND ? '
                        "AND (category_id = 7 OR description LIKE 'مصرف مصرفی%') "
                        'ORDER BY expense_date, id',
                        (date_from, date_to),
                    ).fetchall()
            except Exception as e2:
                QMessageBox.critical(self, 'خطا', 'خطا در بارگذاری:\n{}'.format(e2))
                return

        self.table.setRowCount(len(rows))
        grand_total = 0
        for i, r in enumerate(rows):
            amount = int(r[4] or 0)
            qty = int(r[5] or 1)
            grand_total += amount
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(r[6] or '-'))
            self.table.setItem(i, 2, QTableWidgetItem(r[7] or '-'))
            qty_item = QTableWidgetItem(str(qty))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, qty_item)
            jdate = jalali_date_display_from_iso(r[2]) if r[2] else '-'
            self.table.setItem(i, 4, QTableWidgetItem('{} | {}'.format(jdate, r[2])))
            amt_item = QTableWidgetItem('{:,}'.format(amount))
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 5, amt_item)

        self.total_lbl.setText('جمع کل: {:,} ریال'.format(grand_total))
