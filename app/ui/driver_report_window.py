import sqlite3
"""
گزارش رانندگان - نسخه نهایی
منبع داده: warehouse_receipts و warehouse_issues
بدون استفاده از financial_documents
"""
import os
import tempfile
import webbrowser
from datetime import datetime
from typing import Dict, List

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QDialog, QFileDialog,
    QFrame, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from app.core.jalali import jalali_date_display_from_iso


class DriverReportWindow(QDialog):
    """گزارش جامع رانندگان با استفاده از warehouse_receipts و warehouse_issues"""

    def __init__(self, db, user_data: Dict) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.drivers: List[Dict] = []
        self.report_rows: List[Dict] = []

        self.setWindowTitle('گزارش رانندگان')
        self.resize(1600, 850)
        self._build_ui()
        self._load_drivers()
        self._update_from_jalali()
        self._update_to_jalali()
        self._refresh_report()

    # ================================================================
    # به‌روزرسانی لیبل‌های شمسی
    # ================================================================
    def _update_from_jalali(self):
        iso = self.date_from.date().toString('yyyy-MM-dd')
        self.from_jalali_lbl.setText(jalali_date_display_from_iso(iso))

    def _update_to_jalali(self):
        iso = self.date_to.date().toString('yyyy-MM-dd')
        self.to_jalali_lbl.setText(jalali_date_display_from_iso(iso))

    # ================================================================
    # ساخت UI
    # ================================================================
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # هدر
        header = QFrame()
        header.setObjectName('Card')
        header_layout = QVBoxLayout(header)
        title = QLabel('گزارش جامع رانندگان')
        title.setObjectName('Title')
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel('نمایش سفرهای راننده بر اساس رسید انبار و حواله انبار')
        subtitle.setObjectName('Muted')
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        # فیلترها
        filter_card = QFrame()
        filter_card.setObjectName('Card')
        filter_layout = QHBoxLayout(filter_card)

        filter_layout.addWidget(QLabel('راننده:'))
        self.driver_combo = QComboBox()
        self.driver_combo.setMinimumWidth(220)
        filter_layout.addWidget(self.driver_combo)

        filter_layout.addWidget(QLabel('نوع:'))
        self.type_combo = QComboBox()
        self.type_combo.addItem('همه', 'ALL')
        self.type_combo.addItem('ورود بار', 'INBOUND')
        self.type_combo.addItem('خروج بار', 'OUTBOUND')
        filter_layout.addWidget(self.type_combo)

        filter_layout.addWidget(QLabel('از تاریخ:'))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat('yyyy-MM-dd')
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setMinimumWidth(130)
        filter_layout.addWidget(self.date_from)
        self.from_jalali_lbl = QLabel('-')
        self.from_jalali_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;padding:0 8px;')
        filter_layout.addWidget(self.from_jalali_lbl)

        filter_layout.addWidget(QLabel('تا تاریخ:'))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat('yyyy-MM-dd')
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setMinimumWidth(130)
        filter_layout.addWidget(self.date_to)
        self.to_jalali_lbl = QLabel('-')
        self.to_jalali_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;padding:0 8px;')
        filter_layout.addWidget(self.to_jalali_lbl)

        refresh_btn = QPushButton('بروزرسانی')
        refresh_btn.setObjectName('PrimaryButton')
        refresh_btn.clicked.connect(self._refresh_report)
        filter_layout.addWidget(refresh_btn)
        filter_layout.addStretch()
        root.addWidget(filter_card)
        
        # اتصال سیگنال‌ها برای به‌روزرسانی لیبل‌های شمسی
        self.date_from.dateChanged.connect(self._update_from_jalali)
        self.date_to.dateChanged.connect(self._update_to_jalali)

        # کارت‌های آماری
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(10)
        self.card_trips = self._card('تعداد سفر', '0', '#2563eb')
        self.card_freight = self._card('جمع کرایه', '0 ریال', '#059669')
        self.card_inbound = self._card('ورودی', '0', '#10b981')
        self.card_outbound = self._card('خروجی', '0', '#ef4444')
        summary_layout.addWidget(self.card_trips)
        summary_layout.addWidget(self.card_freight)
        summary_layout.addWidget(self.card_inbound)
        summary_layout.addWidget(self.card_outbound)
        root.addLayout(summary_layout)

        # جدول گزارش - 9 ستون
        self.report_table = QTableWidget(0, 11)
        self.report_table.setHorizontalHeaderLabels([
            'ردیف', 'نوع', 'شماره سند', 'مرحله', 'نام راننده', 'شماره وسیله',
            'وضعیت', 'تاریخ', 'مبلغ کرایه', 'مقدار بار', 'طرف حساب'
        ])
        hv = self.report_table.horizontalHeader()
        for i in range(10):
            hv.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hv.setSectionResizeMode(10, QHeaderView.Stretch)
        self.report_table.verticalHeader().setVisible(False)
        self.report_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.report_table.setAlternatingRowColors(True)
        root.addWidget(self.report_table)

        # دکمه‌ها
        btn_layout = QHBoxLayout()
        html_btn = QPushButton('خروجی HTML')
        html_btn.setObjectName('SecondaryButton')
        html_btn.setMinimumHeight(45)
        html_btn.clicked.connect(self._export_html)
        csv_btn = QPushButton('خروجی Excel')
        csv_btn.setObjectName('SecondaryButton')
        csv_btn.setMinimumHeight(45)
        csv_btn.clicked.connect(self._export_csv)
        close_btn = QPushButton('بستن')
        close_btn.setObjectName('SecondaryButton')
        close_btn.setMinimumHeight(45)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(html_btn)
        btn_layout.addWidget(csv_btn)
        btn_layout.addWidget(close_btn)
        root.addLayout(btn_layout)

    def _card(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet('')
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)
        lbl = QLabel(title)
        lbl.setStyleSheet(f'color: {color}; font-size: 12px; font-weight: bold;')
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        val_lbl = QLabel(value)
        val_lbl.setObjectName('value')
        val_lbl.setStyleSheet(' font-size: 18px; font-weight: bold;')
        val_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(val_lbl)
        return card

    # ================================================================
    # بارگذاری رانندگان
    # ================================================================
    def _load_drivers(self) -> None:
        """بارگذاری رانندگان از جدول persons با role='DRIVER'
        اگر کسی نداشت، همه اشخاص فعال"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT id, first_name, last_name
                    FROM persons
                    WHERE is_active = 1 AND id IN (SELECT person_id FROM person_roles WHERE role_type = 'DRIVER')
                    ORDER BY last_name, first_name
                """).fetchall()
                if not rows:
                    rows = conn.execute("""
                        SELECT id, first_name, last_name
                        FROM persons
                        WHERE is_active = 1
                        ORDER BY last_name, first_name
                    """).fetchall()
                self.drivers = [{'id': r[0], 'fn': r[1] or '', 'ln': r[2] or ''} for r in rows]
        except Exception:
            self.drivers = []

        self.driver_combo.blockSignals(True)
        self.driver_combo.clear()
        self.driver_combo.addItem('همه رانندگان', None)
        for d in self.drivers:
            name = f"{d['fn']} {d['ln']}".strip()
            self.driver_combo.addItem(name, d['id'])
        self.driver_combo.blockSignals(False)
        if self.drivers:
            self.driver_combo.setCurrentIndex(0)

    # ================================================================
    # بارگذاری گزارش
    # ================================================================
    def _refresh_report(self) -> None:
        driver_id = self.driver_combo.currentData()
        op_type = self.type_combo.currentData()
        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')

        all_rows = []

        try:
            with self.db.connect() as conn:
                conn.row_factory = sqlite3.Row

                # 1. کرایه‌های ورودی از warehouse_receipts
                if not op_type or op_type == 'ALL' or op_type == 'INBOUND':
                    q = """
                        SELECT
                            wr.id,
                            wr.receipt_no AS finance_no,
                            wr.receipt_date AS finance_date,
                            wr.freight_amount,
                            wr.vehicle_plate,
                            (SELECT COALESCE(SUM(wri.qty),0) FROM warehouse_receipt_items wri WHERE wri.receipt_id = wr.id) as bar_qty,
                            wr.stage_no,
                            wr.supplier_id,
                            sp.first_name,
                            sp.last_name,
                            wr.driver_id,
                            dr.first_name,
                            dr.last_name,
                            COALESCE(wr.receipt_status, 'CONFIRMED') AS doc_status
                        FROM warehouse_receipts wr
                        LEFT JOIN persons sp ON sp.id = wr.supplier_id
                        LEFT JOIN persons dr ON dr.id = wr.driver_id
                        WHERE wr.receipt_date BETWEEN ? AND ?
                    """
                    params = [date_from, date_to]
                    if driver_id:
                        q += " AND wr.driver_id = ?"
                        params.append(driver_id)
                    q += " ORDER BY wr.receipt_date DESC, wr.id DESC"
                    for r in conn.execute(q, params).fetchall():
                        all_rows.append(('INBOUND', r))

                # 2. کرایه‌های خروجی از warehouse_issues
                if not op_type or op_type == 'ALL' or op_type == 'OUTBOUND':
                    q = """
                        SELECT
                            wi.id,
                            wi.issue_no AS finance_no,
                            wi.issue_date AS finance_date,
                            wi.freight_amount AS total_amount,
                            wi.vehicle_plate,
                            (SELECT COALESCE(SUM(wii.qty),0) FROM warehouse_issue_items wii WHERE wii.issue_id = wi.id) as bar_qty,
                            wi.stage_no,
                            wi.customer_id,
                            cp.first_name,
                            cp.last_name,
                            wi.driver_id,
                            dr.first_name,
                            dr.last_name,
                            COALESCE(wi.issue_status, 'CONFIRMED') AS doc_status
                        FROM warehouse_issues wi
                        LEFT JOIN persons cp ON cp.id = wi.customer_id
                        LEFT JOIN persons dr ON dr.id = wi.driver_id
                        WHERE wi.issue_date BETWEEN ? AND ?
                    """
                    params = [date_from, date_to]
                    if driver_id:
                        q += " AND wi.driver_id = ?"
                        params.append(driver_id)
                    q += " ORDER BY wi.issue_date DESC, wi.id DESC"
                    for r in conn.execute(q, params).fetchall():
                        all_rows.append(('OUTBOUND', r))

        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در بارگذاری:\n\n{e}')
            return

        # مرتب‌سازی
        all_rows.sort(key=lambda x: x[1][2] or '', reverse=True)

        # مرتب‌سازی بر اساس شماره سند + مرحله
        def sort_key(item):
            direction, r = item
            doc_no = r[1] or ''
            stage = r[6] or 0
            # stage=0 یعنی بدون مرحله (پیش‌فرض)
            return (doc_no, stage)
        all_rows.sort(key=sort_key)

        # ساخت report_rows
        self.report_rows = []
        for direction, r in all_rows:
            op_label = 'ورود' if direction == 'INBOUND' else 'خروج'

            # طرف حساب: تأمین‌کننده برای ورودی، مشتری برای خروجی
            party_fn = r[8] or ''
            party_ln = r[9] or ''
            party_name = f"{party_fn} {party_ln}".strip() or '-'

            # راننده
            driver_fn = r[11] or ''
            driver_ln = r[12] or ''
            driver_name = f"{driver_fn} {driver_ln}".strip() or '-'

            # مرحله
            stage_no = r['stage_no'] or 0

            doc_status = r['doc_status'] if 'doc_status' in r.keys() else 'CONFIRMED'
            self.report_rows.append({
                'id': r[0],
                'finance_no': r[1],
                'finance_date': r[2],
                'finance_date_jalali': jalali_date_display_from_iso(r[2]) if r[2] else '-',
                'total_amount': r[3] or 0,
                'vehicle_no': r['vehicle_plate'] or '-',
                'bar_qty': r['bar_qty'] or 0,
                'stage_no': stage_no,
                'party_name': party_name,
                'driver_name': driver_name,
                'operation_label': op_label,
                'doc_status': doc_status,
                'is_void': doc_status == 'CANCELLED',
            })

        self._populate_table()
        self._update_summary()

    # ================================================================
    # پر کردن جدول
    # ================================================================
    def _populate_table(self) -> None:
        self.report_table.blockSignals(True)
        self.report_table.setRowCount(len(self.report_rows))

        bg = QColor('#dbeafe')
        txt = QColor('#0f172a')
        green = QColor('#10b981')
        red = QColor('#ef4444')
        blue = QColor('#1d4ed8')
        yellow = QColor('#b45309')
        pink = QColor('#f472b6')
        purple = QColor('#a78bfa')

        gray_bg = QColor('#f1f5f9')
        gray_txt = QColor('#94a3b8')
        for idx, row in enumerate(self.report_rows):
            is_void = row.get('is_void', False)
            row_bg = gray_bg if is_void else bg
            row_txt = gray_txt if is_void else txt

            def make_item(text, fg=None, center=True, use_bg=None):
                item = QTableWidgetItem(str(text))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                align = Qt.AlignCenter | Qt.AlignVCenter if center else Qt.AlignRight | Qt.AlignVCenter
                item.setTextAlignment(align)
                item.setForeground(fg if fg is not None else row_txt)
                item.setBackground(use_bg if use_bg is not None else row_bg)
                return item

            # 0: ردیف
            self.report_table.setItem(idx, 0, make_item(idx + 1))
            # 1: نوع
            fg = green if row['operation_label'] == 'ورود' else red
            self.report_table.setItem(idx, 1, make_item(row['operation_label'], fg))
            # 2: شماره سند
            self.report_table.setItem(idx, 2, make_item(row['finance_no'], blue))
            # 3: مرحله
            stage = row.get('stage_no', 0) or 0
            self.report_table.setItem(idx, 3, make_item(stage if stage else '-'))
            # 4: نام راننده (جدید)
            self.report_table.setItem(idx, 4, make_item(row['driver_name'], None, center=False))
            # 5: شماره وسیله
            fg4 = pink if row['vehicle_no'] != '-' else None
            self.report_table.setItem(idx, 5, make_item(row['vehicle_no'], fg4))
            # 6: وضعیت (جدید)
            status_lbl = 'باطل' if is_void else 'فعال'
            fg6s = red if is_void else green
            self.report_table.setItem(idx, 6, make_item(status_lbl, fg6s))
            # 7: تاریخ شمسی
            self.report_table.setItem(idx, 7, make_item(row['finance_date_jalali'], yellow if not is_void else gray_txt))
            # 8: مبلغ کرایه
            freight = row['total_amount']
            fg8 = yellow if freight and not is_void else None
            self.report_table.setItem(idx, 8, make_item(f"{int(freight):,} ریال" if freight else '-'))
            # 9: مقدار بار
            bar = row['bar_qty']
            fg9 = green if bar and not is_void else None
            self.report_table.setItem(idx, 9, make_item(f"{int(bar):,}" if bar else '-'))
            # 10: طرف حساب
            self.report_table.setItem(idx, 10, make_item(row['party_name'], None, center=False))

        self.report_table.blockSignals(False)
        self.report_table.resizeColumnsToContents()

    # ================================================================
    # بروزرسانی کارت‌ها
    # ================================================================
    def _update_summary(self) -> None:
        active_rows = [r for r in self.report_rows if not r.get('is_void')]
        total = len(active_rows)
        freight = sum(int(r['total_amount']) for r in active_rows)
        inbound = sum(1 for r in active_rows if r['operation_label'] == 'ورود')
        outbound = sum(1 for r in active_rows if r['operation_label'] == 'خروج')

        self.card_trips.findChild(QLabel, 'value').setText(f'{total:,}')
        self.card_freight.findChild(QLabel, 'value').setText(f'{freight:,} ریال')
        self.card_inbound.findChild(QLabel, 'value').setText(f'{inbound:,}')
        self.card_outbound.findChild(QLabel, 'value').setText(f'{outbound:,}')

    # ================================================================
    # خروجی HTML
    # ================================================================
    def _export_html(self) -> None:
        if not self.report_rows:
            QMessageBox.information(self, 'خروجی', 'داده‌ای برای خروجی وجود ندارد.')
            return

        driver_name = self.driver_combo.currentText()
        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        total = len(self.report_rows)
        freight = sum(int(r['total_amount']) for r in self.report_rows)
        inbound = sum(1 for r in self.report_rows if r['operation_label'] == 'ورود')
        outbound = sum(1 for r in self.report_rows if r['operation_label'] == 'خروج')

        rows_html = ""
        for idx, row in enumerate(self.report_rows):
            cls = 'inbound' if row['operation_label'] == 'ورود' else 'outbound'
            bar = row['bar_qty']
            bar_text = f"{int(bar):,}" if bar else '-'
            vehicle = row['vehicle_no'] or '-'
            stage = row.get('stage_no', 0) or 0
            stage_text = str(stage) if stage else '-'
            freight_amt = int(row['total_amount'])
            status_lbl = 'باطل' if row.get('is_void') else 'فعال'
            status_style = 'color:#dc2626;font-weight:bold;' if row.get('is_void') else 'color:#059669;font-weight:bold;'
            rows_html += f"""<tr class="{cls}">
                <td>{idx+1}</td><td>{row['operation_label']}</td><td>{row['finance_no']}</td>
                <td>{stage_text}</td><td>{row['driver_name']}</td><td>{vehicle}</td>
                <td style="{status_style}">{status_lbl}</td><td>{row['finance_date_jalali']}</td>
                <td>{freight_amt:,} ریال</td><td>{bar_text}</td><td>{row['party_name']}</td></tr>
"""

        html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head><meta charset="UTF-8"><title>گزارش رانندگان</title>
<style>
body {{ font-family: Tahoma; margin: 20px; background: #f5f5f5; }}
.container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
h1 {{ text-align: center; border-bottom: 3px solid #2563eb; padding-bottom: 15px; }}
.filter {{ display: flex; gap: 30px; margin-bottom: 20px; padding: 15px; background: #f1f5f9; border-radius: 6px; }}
.summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
.card {{ padding: 15px; border-radius: 6px; text-align: center; }}
.card .label {{ font-size: 14px; color: #64748b; }}
.card .value {{ font-size: 22px; font-weight: bold; }}
.card.trips {{ background: #dbeafe; border: 2px solid #2563eb; }}
.card.freight {{ background: #dcfce7; border: 2px solid #059669; }}
.card.in {{ background: #d1fae5; border: 2px solid #10b981; }}
.card.out {{ background: #fee2e2; border: 2px solid #ef4444; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ background: #46505f; color: white; padding: 12px; }}
td {{ padding: 10px; text-align: center; border-bottom: 1px solid #e2e8f0; }}
tr:nth-child(even) {{ background: #f8fafc; }}
.inbound {{ background: #dcfce7; }}
.outbound {{ background: #fee2e2; }}
</style></head>
<body><div class="container">
<h1>گزارش رانندگان</h1>
<div class="filter">
    <div><b>راننده:</b> {driver_name}</div>
    <div><b>از:</b> {date_from}</div><div><b>تا:</b> {date_to}</div>
</div>
<div class="summary">
    <div class="card trips"><div class="label">تعداد سفر</div><div class="value">{total:,}</div></div>
    <div class="card freight"><div class="label">جمع کرایه</div><div class="value">{freight:,} ریال</div></div>
    <div class="card in"><div class="label">ورودی</div><div class="value">{inbound:,}</div></div>
    <div class="card out"><div class="label">خروجی</div><div class="value">{outbound:,}</div></div>
</div>
<table><thead><tr>
    <th>ردیف</th><th>نوع</th><th>شماره سند</th><th>مرحله</th><th>نام راننده</th><th>شماره وسیله</th>
    <th>وضعیت</th><th>تاریخ</th><th>مبلغ کرایه</th><th>مقدار بار</th><th>طرف حساب</th>
</tr></thead><tbody>{rows_html}</tbody></table>
<p style="text-align:center;color:#64748b;font-size:12px;margin-top:30px;">
    تاریخ تولید: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div></body></html>"""

        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره HTML', 'driver_report.html', 'HTML (*.html)')
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)
            webbrowser.open(f'file:///{file_path}')
            QMessageBox.information(self, 'موفق', f'گزارش ذخیره شد:\n{file_path}')

    # ================================================================
    # خروجی CSV
    # ================================================================
    def _export_csv(self) -> None:
        if not self.report_rows:
            QMessageBox.information(self, 'خروجی', 'داده‌ای برای خروجی وجود ندارد.')
            return
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره CSV', 'driver_report.csv', 'CSV (*.csv)')
        if not file_path:
            return
        with open(file_path, 'w', encoding='utf-8-sig') as f:
            f.write('ردیف,نوع,شماره سند,مرحله,نام راننده,شماره وسیله,وضعیت,تاریخ شمسی,مبلغ کرایه,مقدار بار,طرف حساب\n')
            for idx, row in enumerate(self.report_rows):
                stage = row.get('stage_no', 0) or 0
                status_lbl = 'باطل' if row.get('is_void') else 'فعال'
            f.write(f"{idx+1},{row['operation_label']},{row['finance_no']},"
                    f"{stage},{row['driver_name']},{row['vehicle_no']},{status_lbl},"
                    f"{row['finance_date_jalali']},{row['total_amount']},{row['bar_qty']},{row['party_name']}\n")
        QMessageBox.information(self, 'موفق', f'گزارش ذخیره شد:\n{file_path}')
