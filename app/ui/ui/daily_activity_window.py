# -*- coding: utf-8 -*-
"""
Daily Activity Report - گزارش فعالیت روزانه (اصلاح شده)
- شامل افتتاحیه موجودی
- رنگ‌بندی مناسب
"""

import tempfile
import webbrowser
from datetime import datetime
from typing import Any, Dict, List

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QDateEdit, QDialog, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_display_from_iso


class DailyActivityWindow(QDialog):
    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data

        self.setWindowTitle('گزارش فعالیت روزانه')
        self.resize(1400, 900)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        # نمایش تاریخ شمسی اولیه
        self._on_date_changed()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # هدر
        header = QFrame()
        header.setObjectName('Card')
        header_layout = QVBoxLayout(header)
        title = QLabel('گزارش فعالیت روزانه')
        title.setObjectName('Title')
        subtitle = QLabel('نمایش تمام اسناد و فعالیت‌های ثبت‌شده در یک روز خاص')
        subtitle.setObjectName('Muted')
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        # فیلتر تاریخ
        filter_card = QFrame()
        filter_card.setObjectName('Card')
        filter_layout = QVBoxLayout(filter_card)
        
        # ردیف اول: برچسب + تاریخ میلادی + دکمه
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel('تاریخ:'))
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat('yyyy-MM-dd')
        self.date_edit.dateChanged.connect(self._on_date_changed)
        filter_row.addWidget(self.date_edit)

        # لیبل تاریخ شمسی
        self.jalali_date_label = QLabel('')
        self.jalali_date_label.setStyleSheet('font-size:13px;font-weight:bold;color:#2563eb;')
        filter_row.addWidget(self.jalali_date_label)

        refresh_btn = QPushButton('بروزرسانی')
        refresh_btn.setObjectName('PrimaryButton')
        refresh_btn.clicked.connect(self._refresh_report)
        filter_row.addWidget(refresh_btn)
        filter_row.addStretch()
        filter_layout.addLayout(filter_row)
        
        root.addWidget(filter_card)

        # کارت‌های آماری با رنگ‌های متفاوت
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        self.card_receipts = self._stat_card('رسیدهای ثبت‌شده', '0', '#ea580c')
        self.card_issues = self._stat_card('حواله‌های ثبت‌شده', '0', '#9333ea')
        self.card_finance = self._stat_card('اسناد مالی', '0', '#0891b2')
        self.card_expenses = self._stat_card('هزینه‌ها', '0', '#dc2626')
        self.card_opening = self._stat_card('افتتاحیه موجودی', '0', '#f59e0b')
        stats_layout.addWidget(self.card_receipts)
        stats_layout.addWidget(self.card_issues)
        stats_layout.addWidget(self.card_finance)
        stats_layout.addWidget(self.card_expenses)
        stats_layout.addWidget(self.card_opening)
        root.addLayout(stats_layout)

        # تب‌ها با رنگ‌بندی متفاوت
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet('')

        # تب 1: رسیدها
        receipts_tab = QWidget()
        receipts_layout = QVBoxLayout(receipts_tab)
        self.receipts_table = QTableWidget(0, 7)
        self.receipts_table.setHorizontalHeaderLabels([
            'شناسه', 'شماره رسید', 'مرحله', 'تأمین‌کننده', 'راننده', 'تعداد', 'تاریخ'
        ])
        self.receipts_table.setColumnHidden(0, True)
        self.receipts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.receipts_table.verticalHeader().setVisible(False)
        receipts_layout.addWidget(self.receipts_table)
        self.tabs.addTab(receipts_tab, 'رسیدهای انبار')

        # تب 2: حواله‌ها
        issues_tab = QWidget()
        issues_layout = QVBoxLayout(issues_tab)
        self.issues_table = QTableWidget(0, 7)
        self.issues_table.setHorizontalHeaderLabels([
            'شناسه', 'شماره حواله', 'مرحله', 'مشتری', 'راننده', 'تعداد', 'تاریخ'
        ])
        self.issues_table.setColumnHidden(0, True)
        self.issues_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.issues_table.verticalHeader().setVisible(False)
        issues_layout.addWidget(self.issues_table)
        self.tabs.addTab(issues_tab, 'حواله‌های خروج')

        # تب 3: اسناد مالی
        finance_tab = QWidget()
        finance_layout = QVBoxLayout(finance_tab)
        self.finance_table = QTableWidget(0, 7)
        self.finance_table.setHorizontalHeaderLabels([
            'شناسه', 'شماره سند', 'نوع', 'جهت', 'طرف حساب', 'مبلغ', 'تاریخ'
        ])
        self.finance_table.setColumnHidden(0, True)
        self.finance_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.finance_table.verticalHeader().setVisible(False)
        finance_layout.addWidget(self.finance_table)
        self.tabs.addTab(finance_tab, 'اسناد مالی')

        # تب 4: هزینه‌ها
        expenses_tab = QWidget()
        expenses_layout = QVBoxLayout(expenses_tab)
        self.expenses_table = QTableWidget(0, 6)
        self.expenses_table.setHorizontalHeaderLabels([
            'شناسه', 'شماره هزینه', 'دسته‌بندی', 'مبلغ کل', 'پرداخت‌شده', 'تاریخ'
        ])
        self.expenses_table.setColumnHidden(0, True)
        self.expenses_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.expenses_table.verticalHeader().setVisible(False)
        expenses_layout.addWidget(self.expenses_table)
        self.tabs.addTab(expenses_tab, 'هزینه‌ها')

        # تب 5: افتتاحیه موجودی
        opening_tab = QWidget()
        opening_layout = QVBoxLayout(opening_tab)
        self.opening_table = QTableWidget(0, 8)
        self.opening_table.setHorizontalHeaderLabels([
            'شناسه', 'شماره سند', 'تاریخ', 'تاریخ شمسی', 'انبار', 'تعداد انواع', 'مقدار کل', 'ارزش کل'
        ])
        self.opening_table.setColumnHidden(0, True)
        self.opening_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.opening_table.verticalHeader().setVisible(False)
        opening_layout.addWidget(self.opening_table)
        self.tabs.addTab(opening_tab, 'افتتاحیه موجودی')

        root.addWidget(self.tabs)

        # دکمه خروجی
        export_btn = QPushButton('خروجی HTML')
        export_btn.setObjectName('SecondaryButton')
        export_btn.setMinimumHeight(40)
        export_btn.clicked.connect(self._export_html)
        root.addWidget(export_btn)

    def _stat_card(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet('')
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)
        lbl = QLabel(title)
        lbl.setStyleSheet(f'color: {color}; font-size: 13px; font-weight: bold;')
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        val = QLabel(value)
        val.setObjectName('value')
        val.setStyleSheet(' font-size: 18px; font-weight: bold;')
        val.setAlignment(Qt.AlignCenter)
        layout.addWidget(val)
        return card

    def _on_date_changed(self) -> None:
        """به‌روزرسانی لیبل تاریخ شمسی هنگام تغییر تاریخ میلادی"""
        selected_date = self.date_edit.date().toString('yyyy-MM-dd')
        jalali_date = jalali_date_display_from_iso(selected_date)
        self.jalali_date_label.setText(jalali_date)
        # به‌روزرسانی خودکار گزارش
        self._refresh_report()

    def _refresh_report(self) -> None:
        selected_date = self.date_edit.date().toString('yyyy-MM-dd')

        try:
            with self.db.connect() as conn:
                conn.row_factory = None

                # رسیدها
                receipts = conn.execute("""
                    SELECT wr.id, wr.receipt_no, wr.stage_no, wr.receipt_date,
                           wr.delivered_qty,
                           sup.first_name || ' ' || sup.last_name,
                           drv.first_name || ' ' || drv.last_name
                    FROM warehouse_receipts wr
                    LEFT JOIN persons sup ON sup.id = wr.supplier_id
                    LEFT JOIN persons drv ON drv.id = wr.driver_id
                    WHERE wr.receipt_date = ?
                    ORDER BY wr.id DESC
                """, (selected_date,)).fetchall()

                # حواله‌ها
                issues = conn.execute("""
                    SELECT wi.id, wi.issue_no, wi.stage_no, wi.issue_date,
                           wi.delivered_qty,
                           cust.first_name || ' ' || cust.last_name,
                           drv.first_name || ' ' || drv.last_name
                    FROM warehouse_issues wi
                    LEFT JOIN persons cust ON cust.id = wi.customer_id
                    LEFT JOIN persons drv ON drv.id = wi.driver_id
                    WHERE wi.issue_date = ?
                    ORDER BY wi.id DESC
                """, (selected_date,)).fetchall()

                # اسناد مالی
                finance = conn.execute("""
                    SELECT fd.id, fd.finance_no, fd.operation_type, fd.direction,
                           fd.finance_date, fd.total_amount,
                           p.first_name || ' ' || p.last_name
                    FROM financial_documents fd
                    LEFT JOIN persons p ON p.id = fd.counterparty_person_id
                    WHERE fd.finance_date = ? AND fd.status <> 'CANCELLED'
                    ORDER BY fd.id DESC
                """, (selected_date,)).fetchall()

                # هزینه‌ها
                expenses = conn.execute("""
                    SELECT e.id, e.expense_no, e.expense_date, e.amount,
                           e.paid_amount, c.name
                    FROM expenses e
                    LEFT JOIN expense_categories c ON c.id = e.category_id
                    WHERE e.expense_date = ?
                    ORDER BY e.id DESC
                """, (selected_date,)).fetchall()

                # افتتاحیه موجودی
                try:
                    opening = conn.execute("""
                        SELECT od.id, od.opening_no, od.jalali_date_text,
                               w.name as warehouse_name,
                               od.total_types_count, od.total_qty, od.total_amount,
                               od.document_status
                        FROM opening_inventory_documents od
                        JOIN warehouses w ON w.id = od.warehouse_id
                        WHERE SUBSTR(od.opening_date, 1, 10) = ?
                        ORDER BY od.id DESC
                    """, (selected_date,)).fetchall()
                except Exception:
                    opening = []

        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در بارگذاری گزارش:\n{e}')
            return

        # به‌روزرسانی کارت‌ها
        self.card_receipts.findChild(QLabel, 'value').setText(f"{len(receipts):,}")
        self.card_issues.findChild(QLabel, 'value').setText(f"{len(issues):,}")
        self.card_finance.findChild(QLabel, 'value').setText(f"{len(finance):,}")
        self.card_expenses.findChild(QLabel, 'value').setText(f"{len(expenses):,}")
        self.card_opening.findChild(QLabel, 'value').setText(f"{len(opening):,}")

        # پر کردن جدول رسیدها
        self.receipts_table.setRowCount(len(receipts))
        for idx, r in enumerate(receipts):
            vals = [
                str(r[0]), r[1], str(r[2]),
                r[5] or '-', r[6] or '-',
                f"{int(r[4] or 0):,}",
                jalali_date_display_from_iso(r[3]) if r[3] else '-',
            ]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.receipts_table.setItem(idx, col, item)
        self.receipts_table.resizeColumnsToContents()

        # پر کردن جدول حواله‌ها
        self.issues_table.setRowCount(len(issues))
        for idx, r in enumerate(issues):
            vals = [
                str(r[0]), r[1], str(r[2]),
                r[5] or '-', r[6] or '-',
                f"{int(r[4] or 0):,}",
                jalali_date_display_from_iso(r[3]) if r[3] else '-',
            ]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.issues_table.setItem(idx, col, item)
        self.issues_table.resizeColumnsToContents()

        # پر کردن جدول اسناد مالی
        self.finance_table.setRowCount(len(finance))
        for idx, r in enumerate(finance):
            dir_label = 'دریافتنی' if r[3] == 'RECEIVABLE' else 'پرداختنی'
            type_labels = {
                'INBOUND_RECEIPT': 'خرید',
                'INBOUND_FREIGHT': 'کرایه ورودی',
                'OUTBOUND_ISSUE': 'فروش',
                'OUTBOUND_FREIGHT': 'کرایه خروجی',
                'BOX_SALE': 'فروش جعبه',
            }
            vals = [
                str(r[0]), r[1],
                type_labels.get(r[2], r[2]),
                dir_label,
                r[6] or '-',
                f"{int(r[5] or 0):,} ریال",
                jalali_date_display_from_iso(r[4]) if r[4] else '-',
            ]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.finance_table.setItem(idx, col, item)
        self.finance_table.resizeColumnsToContents()

        # پر کردن جدول هزینه‌ها
        self.expenses_table.setRowCount(len(expenses))
        for idx, r in enumerate(expenses):
            vals = [
                str(r[0]), r[1],
                r[5] or '-',
                f"{int(r[3] or 0):,} ریال",
                f"{int(r[4] or 0):,} ریال",
                jalali_date_display_from_iso(r[2]) if r[2] else '-',
            ]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.expenses_table.setItem(idx, col, item)
        self.expenses_table.resizeColumnsToContents()

        # پر کردن جدول افتتاحیه
        self.opening_table.setRowCount(len(opening))
        for idx, r in enumerate(opening):
            vals = [
                str(r[0]),
                r[1] or '-',
                jalali_date_display_from_iso(r[2]) if r[2] else '-',
                r[2] or '-',
                r[3] or '-',
                f"{int(r[4] or 0):,}",
                f"{int(r[5] or 0):,}",
                f"{int(r[6] or 0):,} ریال",
            ]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.opening_table.setItem(idx, col, item)
        self.opening_table.resizeColumnsToContents()

    def _export_html(self) -> None:
        selected_date = self.date_edit.date().toString('yyyy-MM-dd')
        jalali_date = jalali_date_display_from_iso(selected_date)

        html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>گزارش فعالیت روزانه - {jalali_date}</title>
    <style>
        body {{ font-family: Tahoma; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; }}
        h1 {{ text-align: center; border-bottom: 3px solid #2563eb; padding-bottom: 15px; }}
        .stats {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin: 20px 0; }}
        .stat {{ background: #f1f5f9; padding: 15px; border-radius: 6px; text-align: center; }}
        .stat .label {{ font-size: 12px; color: #64748b; }}
        .stat .value {{ font-size: 24px; font-weight: bold;  }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #46505f; color: white; padding: 10px; }}
        td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; text-align: center; }}
        h2 {{  border-right: 4px solid #2563eb; padding-right: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>گزارش فعالیت روزانه</h1>
        <p style="text-align: center; font-size: 18px;">تاریخ: <strong>{jalali_date}</strong> ({selected_date})</p>

        <div class="stats">
            <div class="stat"><div class="label">رسیدها</div><div class="value">{self.receipts_table.rowCount()}</div></div>
            <div class="stat"><div class="label">حواله‌ها</div><div class="value">{self.issues_table.rowCount()}</div></div>
            <div class="stat"><div class="label">اسناد مالی</div><div class="value">{self.finance_table.rowCount()}</div></div>
            <div class="stat"><div class="label">هزینه‌ها</div><div class="value">{self.expenses_table.rowCount()}</div></div>
            <div class="stat"><div class="label">افتتاحیه</div><div class="value">{self.opening_table.rowCount()}</div></div>
        </div>

        <h2>رسیدهای انبار</h2>
        <table>
            <tr><th>شماره</th><th>مرحله</th><th>تأمین‌کننده</th><th>راننده</th><th>تعداد</th></tr>
"""

        for row in range(self.receipts_table.rowCount()):
            no = self.receipts_table.item(row, 1).text()
            stage = self.receipts_table.item(row, 2).text()
            supplier = self.receipts_table.item(row, 3).text()
            driver = self.receipts_table.item(row, 4).text()
            qty = self.receipts_table.item(row, 5).text()
            html += f"            <tr><td>{no}</td><td>{stage}</td><td>{supplier}</td><td>{driver}</td><td>{qty}</td></tr>\n"

        html += """        </table>

        <h2>حواله‌های خروج</h2>
        <table>
            <tr><th>شماره</th><th>مرحله</th><th>مشتری</th><th>راننده</th><th>تعداد</th></tr>
"""

        for row in range(self.issues_table.rowCount()):
            no = self.issues_table.item(row, 1).text()
            stage = self.issues_table.item(row, 2).text()
            customer = self.issues_table.item(row, 3).text()
            driver = self.issues_table.item(row, 4).text()
            qty = self.issues_table.item(row, 5).text()
            html += f"            <tr><td>{no}</td><td>{stage}</td><td>{customer}</td><td>{driver}</td><td>{qty}</td></tr>\n"

        html += """        </table>

        <h2>اسناد مالی</h2>
        <table>
            <tr><th>شماره</th><th>نوع</th><th>جهت</th><th>طرف حساب</th><th>مبلغ</th></tr>
"""

        for row in range(self.finance_table.rowCount()):
            no = self.finance_table.item(row, 1).text()
            op_type = self.finance_table.item(row, 2).text()
            direction = self.finance_table.item(row, 3).text()
            person = self.finance_table.item(row, 4).text()
            amount = self.finance_table.item(row, 5).text()
            html += f"            <tr><td>{no}</td><td>{op_type}</td><td>{direction}</td><td>{person}</td><td>{amount}</td></tr>\n"

        html += """        </table>

        <h2>هزینه‌ها</h2>
        <table>
            <tr><th>شماره</th><th>دسته‌بندی</th><th>مبلغ کل</th><th>پرداخت‌شده</th></tr>
"""

        for row in range(self.expenses_table.rowCount()):
            no = self.expenses_table.item(row, 1).text()
            category = self.expenses_table.item(row, 2).text()
            amount = self.expenses_table.item(row, 3).text()
            paid = self.expenses_table.item(row, 4).text()
            html += f"            <tr><td>{no}</td><td>{category}</td><td>{amount}</td><td>{paid}</td></tr>\n"

        html += """        </table>

        <h2>افتتاحیه موجودی</h2>
        <table>
            <tr><th>شماره سند</th><th>تاریخ</th><th>انبار</th><th>انواع</th><th>تعداد کل</th><th>ارزش کل</th></tr>
"""

        for row in range(self.opening_table.rowCount()):
            no = self.opening_table.item(row, 1).text()
            date = self.opening_table.item(row, 2).text()
            warehouse = self.opening_table.item(row, 4).text()
            types = self.opening_table.item(row, 5).text()
            qty = self.opening_table.item(row, 6).text()
            amount = self.opening_table.item(row, 7).text()
            html += f"            <tr><td>{no}</td><td>{date}</td><td>{warehouse}</td><td>{types}</td><td>{qty}</td><td>{amount}</td></tr>\n"

        html += f"""        </table>

        <p style="text-align: center; color: #64748b; margin-top: 30px;">
            گزارش تولید شده در {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            temp_file = f.name

        webbrowser.open(f'file:///{temp_file}')
        QMessageBox.information(self, 'خروجی', f'گزارش در مرورگر باز شد.\nفایل: {temp_file}')
