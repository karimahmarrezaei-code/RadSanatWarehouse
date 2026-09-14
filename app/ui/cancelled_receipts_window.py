# -*- coding: utf-8 -*-
"""
فرم نمایش سندهای ابطال‌شده رسید انبار
این فرم به صورت مستقل باز می‌شود و به فرم اصلی آسیب نمی‌زند.
"""

from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QDialog, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from app.core.jalali import jalali_date_display_from_iso
from app.core.database import DatabaseManager
from app.repositories.receipt_repository import ReceiptRepository


class CancelledReceiptsWindow(QDialog):
    """پنجره نمایش سندهای ابطال‌شده"""

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.repository = ReceiptRepository(db)

        self.setWindowTitle('بایگانی سندهای ابطال‌شده رسید')
        self.resize(1200, 700)
        self.setLayoutDirection(Qt.RightToLeft)

        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # هدر
        header = QGroupBox('سندهای ابطال‌شده رسید انبار')
        header.setStyleSheet("""
            QGroupBox { color: #ef4444; font-weight: bold; font-size: 16px;
                        border: 1px solid #ef4444; border-radius: 6px;
                        margin-top: 10px; padding-top: 15px; }
        """)
        header_layout = QVBoxLayout(header)

        info_lbl = QLabel('این بخش سندهای رسیدی که ابطال شده‌اند را نمایش می‌دهد.')
        info_lbl.setStyleSheet('font-size: 13px; font-weight: normal;')
        header_layout.addWidget(info_lbl)
        root.addWidget(header)

        # نوار ابزار
        toolbar = QGroupBox()
        toolbar_layout = QHBoxLayout(toolbar)

        refresh_btn = QPushButton('🔄 بروزرسانی')
        refresh_btn.setObjectName('PrimaryButton')
        refresh_btn.clicked.connect(self.refresh_data)

        view_btn = QPushButton('🔍 مشاهده جزئیات')
        view_btn.setObjectName('SecondaryButton')
        view_btn.clicked.connect(self.view_details)

        toolbar_layout.addWidget(refresh_btn)
        toolbar_layout.addWidget(view_btn)
        toolbar_layout.addStretch()
        root.addWidget(toolbar)

        # جدول
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            'شناسه', 'شماره رسید', 'مرجع بار', 'تأمین‌کننده',
            'راننده', 'تعداد', 'تاریخ', 'دلیل ابطال'
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnHidden(0, True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        # آمار
        self.stats_label = QLabel('تعداد سندهای ابطال‌شده: 0')
        self.stats_label.setStyleSheet('color: #f59e0b; font-size: 13px; font-weight: bold;')
        root.addWidget(self.stats_label)

        # دکمه بستن
        close_btn = QPushButton('بستن')
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)

    def refresh_data(self) -> None:
        """بارگذاری لیست سندهای ابطال‌شده"""
        try:
            query = '''
                SELECT wr.id, wr.receipt_no, il.reference_no, wr.receipt_date,
                       wr.delivered_qty, wr.description,
                       sup.first_name || ' ' || sup.last_name AS supplier_name,
                       drv.first_name || ' ' || drv.last_name AS driver_name
                FROM warehouse_receipts wr
                JOIN inbound_loads il ON il.id = wr.inbound_load_id
                LEFT JOIN persons sup ON sup.id = wr.supplier_id
                LEFT JOIN persons drv ON drv.id = wr.driver_id
                WHERE wr.receipt_status = 'CANCELLED'
                ORDER BY wr.id DESC
            '''
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(query).fetchall()

            self.table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                # row is tuple: (id, receipt_no, reference_no, receipt_date, delivered_qty, description, supplier_name, driver_name)
                date_jalali = jalali_date_display_from_iso(row[3]) if row[3] else '-'
                values = [
                    str(row[0]),
                    row[1] or '-',
                    row[2] or '-',
                    row[6] or '-',
                    row[7] or '-',
                    f"{int(row[4] or 0):,}",
                    date_jalali,
                    row[5] or '-',
                ]
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if column_index == 7:  # دلیل ابطال
                        item.setForeground(QColor('#ef4444'))
                    self.table.setItem(row_index, column_index, item)

            self.table.resizeColumnsToContents()
            self.stats_label.setText(f'تعداد سندهای ابطال‌شده: {len(rows)} مورد')

        except Exception as e:
            QMessageBox.critical(self, 'خطا در بارگذاری', f'خطا: {e}')

    def view_details(self) -> None:
        """نمایش جزئیات سند ابطال‌شده"""
        try:
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, 'جزئیات', 'ابتدا یک سند از جدول انتخاب کنید.')
                return

            item = self.table.item(row, 0)
            if not item:
                return

            receipt_id = int(item.text())
            receipt = self.repository.get_receipt(receipt_id)

            if not receipt:
                QMessageBox.warning(self, 'خطا', 'سند یافت نشد.')
                return

            # نمایش در پنجره جزئیات
            dialog = QDialog(self)
            dialog.setWindowTitle(f'جزئیات: {receipt.get("receipt_no", "-")}')
            dialog.resize(800, 600)
            dialog.setLayoutDirection(Qt.RightToLeft)

            layout = QVBoxLayout(dialog)

            # اطلاعات کلی
            info_group = QGroupBox('اطلاعات سند')
            info_layout = QGridLayout(info_group)
            info_layout.addWidget(QLabel('شماره رسید:'), 0, 0)
            info_layout.addWidget(QLabel(receipt.get('receipt_no') or '-'), 0, 1)
            info_layout.addWidget(QLabel('مرجع بار:'), 0, 2)
            info_layout.addWidget(QLabel(receipt.get('reference_no') or '-'), 0, 3)
            info_layout.addWidget(QLabel('مرحله:'), 1, 0)
            info_layout.addWidget(QLabel(str(receipt.get('stage_no') or '-')), 1, 1)
            info_layout.addWidget(QLabel(jalali_date_display_from_iso(str(receipt.get('receipt_date'))[:10])
              if receipt.get('receipt_date') else '-'), 1, 3)
            info_layout.addWidget(QLabel('تأمین‌کننده:'), 2, 0)
            info_layout.addWidget(QLabel(receipt.get('supplier_name') or '-'), 2, 1)
            info_layout.addWidget(QLabel('راننده:'), 2, 2)
            info_layout.addWidget(QLabel(receipt.get('driver_name') or '-'), 2, 3)
            info_layout.addWidget(QLabel('تعداد تحویل:'), 3, 0)
            info_layout.addWidget(QLabel(f"{int(receipt.get('delivered_qty') or 0):,}"), 3, 1)
            info_layout.addWidget(QLabel('وضعیت:'), 3, 2)
            status_lbl = QLabel('ابطال‌شده')
            status_lbl.setStyleSheet('color: #ef4444; font-weight: bold;')
            info_layout.addWidget(status_lbl, 3, 3)
            layout.addWidget(info_group)

            # دلیل ابطال
            if receipt.get('description'):
                reason_group = QGroupBox('دلیل ابطال')
                reason_layout = QVBoxLayout(reason_group)
                reason_lbl = QLabel(receipt.get('description', ''))
                reason_lbl.setWordWrap(True)
                reason_lbl.setStyleSheet(
                    'color: #f59e0b; padding: 10px; background-color: #46505f; border-radius: 4px;'
                )
                reason_layout.addWidget(reason_lbl)
                layout.addWidget(reason_group)

            # ردیف‌های پالت
            if receipt.get('lines'):
                lines_group = QGroupBox('ردیف‌های پالت')
                lines_layout = QVBoxLayout(lines_group)
                lines_table = QTableWidget(0, 6)
                lines_table.setHorizontalHeaderLabels([
                    'ردیف', 'کد پالت', 'نام پالت', 'تعداد', 'قیمت واحد', 'مبلغ کل'
                ])
                lines_table.verticalHeader().setVisible(False)
                lines_table.setRowCount(len(receipt['lines']))

                for idx, line in enumerate(receipt['lines']):
                    vals = [
                        str(line.get('row_no', idx + 1)),
                        line.get('pallet_code', '-'),
                        line.get('pallet_name', '-'),
                        f"{int(line.get('qty', 0)):,}",
                        f"{int(line.get('unit_price', 0)):,} ریال",
                        f"{int(line.get('total_price', 0)):,} ریال",
                    ]
                    for col, v in enumerate(vals):
                        cell = QTableWidgetItem(v)
                        cell.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                        cell.setBackground(QColor('#dbeafe'))
                        lines_table.setItem(idx, col, cell)

                lines_layout.addWidget(lines_table)
                layout.addWidget(lines_group)

            close_btn = QPushButton('بستن')
            close_btn.setObjectName('SecondaryButton')
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در نمایش جزئیات: {e}')
