# -*- coding: utf-8 -*-
"""
Receipt Manager Window - نسخه نهایی و پایدار
ویژگی‌ها:
- ثبت رسید انبار با پشتیبانی مرحله‌ای
- ابطال رسید با پیش‌نمایش موجودی
- فرم جداگانه بایگانی سندهای ابطال‌شده
"""

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QDialog, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_display_from_iso, today_iso_date
from app.core.validators import ValidationError
from app.repositories.receipt_repository import ReceiptRepository


class HtmlPreviewDialog(QDialog):
    def __init__(self, title: str, html: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 760)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                color: #000000;
            }
        """)
        browser.setHtml(html)
        layout.addWidget(browser)


class ReceiptManagerWindow(QDialog):
    data_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.repository = ReceiptRepository(db)
        permissions = set(user_data.get('permissions', []) or [])
        self.can_manage = 'receipts.manage' in permissions or user_data.get('role_code') == 'ADMIN'

        self.suppliers: List[Dict[str, Any]] = []
        self.drivers: List[Dict[str, Any]] = []
        self.pallets: List[Dict[str, Any]] = []
        self.warehouses: List[Dict[str, Any]] = []
        self.open_references: List[Dict[str, Any]] = []
        self.avg_pallet_prices: Dict[int, float] = {}  # pallet_id -> avg_price
        self.pallet_stock: Dict[int, int] = {}  # pallet_id -> موجودی کل در همه انبارها

        self.setWindowTitle('رسید انبار')
        self.resize(1200, 850)
        self._build_ui()
        self._load_lookups()
        self._apply_permissions()
        self._refresh_reference_numbers()
        self.refresh_recent_receipts()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName('Card')
        header_layout = QVBoxLayout(header)
        title = QLabel('مدیریت رسید انبار')
        title.setObjectName('Title')
        subtitle = QLabel('شماره‌گذاری خودکار رسید به فرمت WH-تاریخ-0001 و پشتیبانی از ثبت مرحله‌ای بار')
        subtitle.setObjectName('Muted')
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        # ایجاد تب‌ها
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #334155;
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: #1e293b;
                color: #e2e8f0;
                padding: 8px 24px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-left: 2px;
                border: 1px solid #334155;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #0f172a;
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #64748b;
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background-color: #334155;
            }
        """)

        # ==================== تب ۱: اطلاعات رسید ====================
        tab_info = QWidget()
        tab_info_layout = QVBoxLayout(tab_info)
        tab_info_layout.setSpacing(14)

        reference_group = QGroupBox('اطلاعات مرجع و شماره رسید')
        reference_layout = QGridLayout(reference_group)
        reference_layout.setHorizontalSpacing(12)
        reference_layout.setVerticalSpacing(12)

        self.date_info_label = QLabel('-')
        self.date_info_label.setObjectName('Muted')
        self.operation_date_edit = QDateEdit(QDate.currentDate())
        self.operation_date_edit.setCalendarPopup(True)
        self.operation_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.operation_date_edit.dateChanged.connect(self._refresh_reference_numbers)

        self.reference_selector_combo = QComboBox()
        self.reference_selector_combo.currentIndexChanged.connect(self._reference_selection_changed)

        self.reference_no_label = QLabel('-')
        self.reference_no_label.setObjectName('Title')
        self.document_no_label = QLabel('-')
        self.document_no_label.setObjectName('Title')
        self.stage_no_label = QLabel('-')
        self.stage_no_label.setObjectName('Muted')
        self.remaining_qty_label = QLabel('-')
        self.remaining_qty_label.setObjectName('Muted')

        reference_layout.addWidget(QLabel('تاریخ عملیات'), 0, 0)
        reference_layout.addWidget(self.operation_date_edit, 0, 1)
        reference_layout.addWidget(QLabel('تاریخ شمسی'), 0, 2)
        reference_layout.addWidget(self.date_info_label, 0, 3)
        reference_layout.addWidget(QLabel('مرجع بار باز'), 1, 0)
        reference_layout.addWidget(self.reference_selector_combo, 1, 1)
        reference_layout.addWidget(QLabel('شماره مرجع بار'), 1, 2)
        reference_layout.addWidget(self.reference_no_label, 1, 3)
        reference_layout.addWidget(QLabel('شماره رسید مرحله'), 2, 0)
        reference_layout.addWidget(self.document_no_label, 2, 1)
        reference_layout.addWidget(QLabel('مرحله'), 2, 2)
        reference_layout.addWidget(self.stage_no_label, 2, 3)
        reference_layout.addWidget(QLabel('مانده تقریبی بار'), 3, 0)
        reference_layout.addWidget(self.remaining_qty_label, 3, 1, 1, 3)
        tab_info_layout.addWidget(reference_group)

        info_group = QGroupBox('اطلاعات اصلی رسید')
        info_layout = QGridLayout(info_group)
        info_layout.setHorizontalSpacing(12)
        info_layout.setVerticalSpacing(12)

        self.waybill_edit = QLineEdit()
        self.supplier_combo = QComboBox()
        self.driver_combo = QComboBox()
        self.driver_combo.currentIndexChanged.connect(self._driver_changed)
        self.vehicle_label = QLabel('-')
        self.vehicle_label.setObjectName('Muted')

        self.total_declared_edit = QLineEdit()
        self.stage_declared_edit = QLineEdit()
        self.stage_received_edit = QLineEdit()
        self.freight_edit = QLineEdit()
        self.source_location_edit = QLineEdit()
        self.destination_location_edit = QLineEdit()
        self.warehouse_keeper_edit = QLineEdit()
        self.receiver_name_edit = QLineEdit()
        self.discrepancy_label = QLabel('0')
        self.discrepancy_label.setObjectName('Alert')

        self.total_declared_edit.textChanged.connect(self._on_quantity_changed)
        self.stage_declared_edit.textChanged.connect(self._on_quantity_changed)
        self.stage_received_edit.textChanged.connect(self._on_quantity_changed)
        self.freight_edit.textChanged.connect(lambda: self._format_line_edit_number(self.freight_edit))

        info_layout.addWidget(QLabel('شماره حواله / بارنامه'), 0, 0)
        info_layout.addWidget(self.waybill_edit, 0, 1)
        info_layout.addWidget(QLabel('تأمین‌کننده'), 0, 2)
        info_layout.addWidget(self.supplier_combo, 0, 3)

        info_layout.addWidget(QLabel('راننده'), 1, 0)
        info_layout.addWidget(self.driver_combo, 1, 1)
        info_layout.addWidget(QLabel('خودرو / پلاک'), 1, 2)
        info_layout.addWidget(self.vehicle_label, 1, 3)

        info_layout.addWidget(QLabel('تعداد کل بار'), 2, 0)
        info_layout.addWidget(self.total_declared_edit, 2, 1)
        info_layout.addWidget(QLabel('تعداد بار این مرحله'), 2, 2)
        info_layout.addWidget(self.stage_declared_edit, 2, 3)

        info_layout.addWidget(QLabel('تعداد تحویل به انبار'), 3, 0)
        info_layout.addWidget(self.stage_received_edit, 3, 1)
        info_layout.addWidget(QLabel('مغایرت'), 3, 2)
        info_layout.addWidget(self.discrepancy_label, 3, 3)

        info_layout.addWidget(QLabel('مبلغ پس‌کرایه (ریال)'), 4, 0)
        info_layout.addWidget(self.freight_edit, 4, 1)
        info_layout.addWidget(QLabel('مبدأ'), 4, 2)
        info_layout.addWidget(self.source_location_edit, 4, 3)

        info_layout.addWidget(QLabel('محل تخلیه / مقصد'), 5, 0)
        info_layout.addWidget(self.destination_location_edit, 5, 1)
        info_layout.addWidget(QLabel('مسئول انبار'), 5, 2)
        info_layout.addWidget(self.warehouse_keeper_edit, 5, 3)

        info_layout.addWidget(QLabel('تحویل‌گیرنده'), 6, 0)
        info_layout.addWidget(self.receiver_name_edit, 6, 1)
        tab_info_layout.addWidget(info_group)

        notes_group = QGroupBox('توضیحات و وضعیت')
        notes_layout = QVBoxLayout(notes_group)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(90)
        self.notes_edit.setPlaceholderText('توضیحات، وضعیت بار، عیوب کلی و ...')
        notes_layout.addWidget(self.notes_edit)
        tab_info_layout.addWidget(notes_group)
        tab_info_layout.addStretch()

        # ==================== تب ۲: افزودن پالت ====================
        tab_pallet = QWidget()
        tab_pallet_layout = QVBoxLayout(tab_pallet)
        tab_pallet_layout.setSpacing(14)

        # برچسب قیمت میانگین (مثل فرم حواله)
        avg_price_bar = QHBoxLayout()
        avg_price_bar.setContentsMargins(4, 4, 4, 4)
        self.avg_price_lbl = QLabel('قیمت میانگین: ')
        self.avg_price_lbl.setStyleSheet(
            "background-color: #fbbf24; color: #1e293b; padding: 6px 14px; "
            "font-weight: bold; font-size: 14px; border-radius: 4px;"
        )
        self.avg_price_value = QLabel('0 ریال')
        self.avg_price_value.setStyleSheet(
            "background-color: #22c55e; color: #ffffff; padding: 6px 14px; "
            "font-weight: bold; font-size: 14px; border-radius: 4px;"
        )
        avg_price_bar.addWidget(self.avg_price_lbl)
        avg_price_bar.addWidget(self.avg_price_value)
        avg_price_bar.addStretch()
        tab_pallet_layout.addLayout(avg_price_bar)

        lines_group = QGroupBox('ردیف‌های پالت')
        lines_layout = QVBoxLayout(lines_group)
        line_actions = QHBoxLayout()
        self.add_line_button = QPushButton('افزودن ردیف')
        self.add_line_button.setObjectName('SecondaryButton')
        self.add_line_button.clicked.connect(self.add_line_row)
        self.remove_line_button = QPushButton('حذف ردیف انتخابی')
        self.remove_line_button.setObjectName('SecondaryButton')
        self.remove_line_button.clicked.connect(self.remove_selected_line)
        self.lines_total_label = QLabel('جمع ریالی ردیف‌ها: 0 ریال')
        self.lines_total_label.setObjectName('Muted')
        line_actions.addWidget(self.add_line_button)
        line_actions.addWidget(self.remove_line_button)
        line_actions.addStretch()
        line_actions.addWidget(self.lines_total_label)
        lines_layout.addLayout(line_actions)

        self.lines_table = QTableWidget(0, 7)
        self.lines_table.setHorizontalHeaderLabels([
            'ردیف', 'پالت', 'تعداد', 'قیمت هر پالت', 'مبلغ کل', 'انبار', 'عیوب / توضیح'
        ])
        self.lines_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.lines_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lines_table.verticalHeader().setVisible(False)
        self.lines_table.horizontalHeader().setStretchLastSection(True)
        lines_layout.addWidget(self.lines_table)
        tab_pallet_layout.addWidget(lines_group)

        # ==================== تب ۳: لیست رسیدها ====================
        tab_list = QWidget()
        tab_list_layout = QVBoxLayout(tab_list)
        tab_list_layout.setSpacing(14)

        right_group = QGroupBox('رسیدهای ثبت‌شده')
        right_layout = QVBoxLayout(right_group)
        right_toolbar = QHBoxLayout()
        refresh_receipts_btn = QPushButton('بروزرسانی لیست')
        refresh_receipts_btn.setObjectName('SecondaryButton')
        refresh_receipts_btn.clicked.connect(self.refresh_recent_receipts)
        edit_btn = QPushButton('ویرایش حواله انتخابی')
        edit_btn.setObjectName('SecondaryButton')
        edit_btn.clicked.connect(self._edit_selected_receipt)
        preview_saved_btn = QPushButton('پیش‌نمایش سند انتخابی')
        preview_saved_btn.setObjectName('SecondaryButton')
        preview_saved_btn.clicked.connect(self.preview_selected_saved_receipt)
        rollback_btn = QPushButton('rollback سند انتخابی')
        rollback_btn.setObjectName('SecondaryButton')
        rollback_btn.clicked.connect(self.rollback_selected_receipt)

        # دکمه بایگانی ابطال‌ها
        archive_btn = QPushButton('بایگانی ابطال‌ها')
        archive_btn.setObjectName('SecondaryButton')
        archive_btn.clicked.connect(self.open_cancelled_archive)

        right_toolbar.addWidget(refresh_receipts_btn)
        right_toolbar.addWidget(edit_btn)
        right_toolbar.addWidget(preview_saved_btn)
        right_toolbar.addWidget(rollback_btn)
        right_toolbar.addWidget(archive_btn)
        right_toolbar.addStretch()
        right_layout.addLayout(right_toolbar)

        self.receipts_table = QTableWidget(0, 7)
        self.receipts_table.setHorizontalHeaderLabels([
            'شناسه', 'مرجع بار', 'تأمین‌کننده', 'راننده',
            'تعداد کل حواله', 'تعداد تحویل', 'مانده حواله'
        ])
        self.receipts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.receipts_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.receipts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.receipts_table.verticalHeader().setVisible(False)
        self.receipts_table.setColumnHidden(0, True)
        self.receipts_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.receipts_table)
        tab_list_layout.addWidget(right_group)

        # ==================== تب ۴: حواله‌های تکمیل‌شده ====================
        tab_completed = QWidget()
        tab_completed_layout = QVBoxLayout(tab_completed)
        tab_completed_layout.setSpacing(14)

        completed_group = QGroupBox('حواله‌های تکمیل‌شده (مانده = 0)')
        completed_layout = QVBoxLayout(completed_group)
        completed_toolbar = QHBoxLayout()
        refresh_completed_btn = QPushButton('بروزرسانی لیست')
        refresh_completed_btn.setObjectName('SecondaryButton')
        refresh_completed_btn.clicked.connect(self.refresh_completed_receipts)
        print_completed_btn = QPushButton('پرینت حواله انتخابی')
        print_completed_btn.setObjectName('SecondaryButton')
        print_completed_btn.clicked.connect(self.print_selected_completed_receipt)
        completed_toolbar.addWidget(refresh_completed_btn)
        completed_toolbar.addWidget(print_completed_btn)
        completed_toolbar.addStretch()
        completed_layout.addLayout(completed_toolbar)

        self.completed_table = QTableWidget(0, 8)
        self.completed_table.setHorizontalHeaderLabels([
            'شناسه', 'مرجع بار', 'تأمین‌کننده', 'راننده',
            'تعداد کل حواله', 'تعداد تحویل', 'مانده', 'مبلغ کل'
        ])
        self.completed_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.completed_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.completed_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.completed_table.verticalHeader().setVisible(False)
        self.completed_table.setColumnHidden(0, True)
        self.completed_table.horizontalHeader().setStretchLastSection(True)
        completed_layout.addWidget(self.completed_table)
        tab_completed_layout.addWidget(completed_group)

        # اضافه کردن تب‌ها
        self.tabs.addTab(tab_info, 'اطلاعات رسید')
        self.tabs.addTab(tab_pallet, 'افزودن پالت')
        self.tabs.addTab(tab_list, 'لیست رسیدها')
        self.tabs.addTab(tab_completed, 'حواله‌های تکمیل‌شده')

        root.addWidget(self.tabs)

        # ==================== دکمه‌های عملیاتی پایین فرم ====================
        action_buttons = QHBoxLayout()
        self.new_button = QPushButton('رسید جدید')
        self.new_button.setObjectName('SecondaryButton')
        self.new_button.clicked.connect(self.clear_form)

        self.preview_button = QPushButton('پیش‌نمایش رسید')
        self.preview_button.setObjectName('SecondaryButton')
        self.preview_button.clicked.connect(self.preview_current_receipt)

        self.show_list_button = QPushButton('مشاهده لیست رسیدها')
        self.show_list_button.setObjectName('SecondaryButton')
        self.show_list_button.clicked.connect(lambda: self.tabs.setCurrentIndex(2))  # تب لیست رسیدها (index 2)

        self.save_button = QPushButton('ثبت و تایید رسید')
        self.save_button.clicked.connect(self.save_receipt)

        action_buttons.addWidget(self.new_button)
        action_buttons.addWidget(self.preview_button)
        action_buttons.addWidget(self.show_list_button)
        action_buttons.addStretch()
        action_buttons.addWidget(self.save_button)

        root.addLayout(action_buttons)

    def _apply_permissions(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'دسترسی ثبت رسید برای شما فعال نیست. فرم در حالت فقط‌نمایش باز شده است.')
            for widget in [
                self.reference_selector_combo, self.operation_date_edit, self.waybill_edit,
                self.supplier_combo, self.driver_combo, self.total_declared_edit,
                self.stage_declared_edit, self.stage_received_edit, self.freight_edit,
                self.source_location_edit, self.destination_location_edit,
                self.warehouse_keeper_edit, self.receiver_name_edit,
                self.add_line_button, self.remove_line_button, self.notes_edit,
                self.new_button, self.preview_button, self.save_button,
            ]:
                widget.setEnabled(False)

    def _load_lookups(self) -> None:
        self.suppliers = self.repository.list_suppliers()
        self.drivers = self.repository.list_drivers()
        self.pallets = self.repository.list_pallets()
        self.warehouses = self.repository.list_warehouses()
        self.open_references = self.repository.list_open_inbound_references()

        self.supplier_combo.clear()
        self.supplier_combo.addItem('انتخاب کنید', None)
        for row in self.suppliers:
            name = f"{row['first_name']} {row['last_name']}".strip()
            self.supplier_combo.addItem(name, row['id'])

        self.driver_combo.clear()
        self.driver_combo.addItem('انتخاب کنید', None)
        for row in self.drivers:
            name = f"{row['first_name']} {row['last_name']}".strip()
            label = f"{name} | {row.get('vehicle_plate') or '-'}"
            self.driver_combo.addItem(label, row['id'])

        self.reference_selector_combo.blockSignals(True)
        self.reference_selector_combo.clear()
        self.reference_selector_combo.addItem('مرجع جدید خودکار', None)
        for row in self.open_references:
            remaining = int(row['remaining_qty'])
            label = f"{row['reference_no']} | مانده: {remaining:,}"
            self.reference_selector_combo.addItem(label, row['id'])
        self.reference_selector_combo.blockSignals(False)

        self._load_pallet_prices()

        if self.lines_table.rowCount() == 0:
            self.add_line_row()
        self._refresh_reference_numbers()

    def _current_iso_date(self) -> str:
        return self.operation_date_edit.date().toString('yyyy-MM-dd')

    def _refresh_reference_numbers(self) -> None:
        iso_date = self._current_iso_date()
        self.date_info_label.setText(jalali_date_display_from_iso(iso_date))

        selected_reference_id = self.reference_selector_combo.currentData()
        if selected_reference_id:
            reference = next((row for row in self.open_references if row['id'] == selected_reference_id), None)
            if not reference:
                return
            reference_no = reference['reference_no']
            stage_no = self.repository.next_stage_no(selected_reference_id)
            document_no = self.repository.build_document_no(reference_no, stage_no)
            remaining = int(reference['remaining_qty'])
            self.reference_no_label.setText(reference_no)
            self.document_no_label.setText(document_no)
            self.stage_no_label.setText(str(stage_no))
            self.remaining_qty_label.setText(f'{remaining:,} عدد')
            self.total_declared_edit.setText(self._fmt_int(int(reference['total_load_qty'])))
            self.total_declared_edit.setEnabled(False and self.can_manage)
        else:
            reference_no = self.repository.next_reference_no(iso_date)
            document_no = self.repository.build_document_no(reference_no, 1)
            self.reference_no_label.setText(reference_no)
            self.document_no_label.setText(document_no)
            self.stage_no_label.setText('1')
            self.remaining_qty_label.setText('مرجع جدید')
            self.total_declared_edit.setEnabled(self.can_manage)

    def _reference_selection_changed(self) -> None:
        selected_reference_id = self.reference_selector_combo.currentData()
        print(f'_reference_selection_changed: selected_reference_id={selected_reference_id}')
        if selected_reference_id:
            reference = next((row for row in self.open_references if row['id'] == selected_reference_id), None)
            print(f'_reference_selection_changed: reference={reference}')
            if reference:
                self._select_combo_by_data(self.supplier_combo, reference.get('supplier_id'))
                self._select_combo_by_data(self.driver_combo, reference.get('driver_id'))
                self.waybill_edit.setText(reference.get('waybill_no') or '')
                self.source_location_edit.setText(reference.get('source_location') or '')
                self.destination_location_edit.setText(reference.get('destination_location') or '')
                remaining = int(reference['remaining_qty'])
                self.stage_declared_edit.setText(self._fmt_int(max(remaining, 0)))
                self.stage_received_edit.setText(self._fmt_int(max(remaining, 0)))
                self._load_receipt_items(selected_reference_id)
            else:
                print(f'_reference_selection_changed: reference not found in open_references!')
                # ممکنه حواله تکمیل شده باشه - باید مستقیم لود کنیم
                self._load_receipt_items(selected_reference_id)
        else:
            self.total_declared_edit.clear()
            self.stage_declared_edit.clear()
            self.stage_received_edit.clear()
            self.waybill_edit.clear()
            self.source_location_edit.clear()
            self.destination_location_edit.clear()
        self._refresh_reference_numbers()
        self._driver_changed()
        self._on_quantity_changed()

    def _load_pallet_prices(self) -> None:
        """خواندن قیمت میانگین هر پالت و موجودی فعلی آن‌ها"""
        self.avg_pallet_prices = {}
        self.pallet_stock = {}
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                # قیمت میانگین از تراکنش‌های ورودی
                rows = conn.execute(
                    "SELECT pallet_id, "
                    "       CASE WHEN SUM(qty) > 0 THEN "
                    "           SUM(COALESCE(total_amount, unit_price * qty)) / SUM(qty) "
                    "       ELSE 0 END AS avg_price "
                    "FROM inventory_transactions "
                    "WHERE transaction_type = 'IN' AND COALESCE(is_void, 0) = 0 "
                    "GROUP BY pallet_id"
                ).fetchall()
                print(f'_load_pallet_prices: got {len(rows)} rows')
                for r in rows:
                    self.avg_pallet_prices[r[0]] = float(r[1] or 0)
                print(f'avg_pallet_prices: {self.avg_pallet_prices}')
                # موجودی فعلی هر پالت
                rows2 = conn.execute(
                    "SELECT pallet_id, "
                    "       SUM(CASE WHEN transaction_type='IN' THEN qty ELSE -qty END) AS stock "
                    "FROM inventory_transactions "
                    "WHERE COALESCE(is_void, 0) = 0 "
                    "GROUP BY pallet_id"
                ).fetchall()
                for r in rows2:
                    self.pallet_stock[r[0]] = max(int(r[1] or 0), 0)
        except Exception as e:
            print(f'Load pallet prices error: {e}')
            import traceback
            traceback.print_exc()

    def _on_receipt_pallet_changed(self, row: int) -> None:
        """وقتی پالت در یک ردیف تغییر می‌کند: نمایش قیمت میانگین"""
        pallet_combo = self.lines_table.cellWidget(row, 1)
        if not isinstance(pallet_combo, QComboBox):
            return
        pallet_id = pallet_combo.currentData()
        price_edit = self.lines_table.cellWidget(row, 3)

        print(f'_on_receipt_pallet_changed: row={row}, pallet_id={pallet_id}, avg_prices={self.avg_pallet_prices}')

        if pallet_id:
            avg_price = self.avg_pallet_prices.get(pallet_id, 0)
            print(f'avg_price for pallet {pallet_id}: {avg_price}')
            self.avg_price_value.setText(f"{int(avg_price):,} ریال")

            # اگر قیمت خالی است، قیمت میانگین پیشنهاد بده
            if isinstance(price_edit, QLineEdit) and not price_edit.text():
                price_edit.blockSignals(True)
                price_edit.setText(f"{int(avg_price):,}")
                price_edit.blockSignals(False)
        else:
            self.avg_price_value.setText('0 ریال')

        self.recalculate_lines()

    def _load_receipt_items(self, inbound_load_id):
        """بارگذاری آیتم‌های پالت از مراحل قبلی این حواله مادر"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                items = conn.execute(
                    "SELECT wri.pallet_id, p.code, p.name, wri.qty, wri.unit_price, "
                    "       wri.total_price, wri.warehouse_id, wri.defect_description "
                    "FROM warehouse_receipt_items wri "
                    "JOIN pallets p ON p.id = wri.pallet_id "
                    "JOIN warehouse_receipts wr ON wr.id = wri.receipt_id "
                    "WHERE wr.inbound_load_id = ? "
                    "AND COALESCE(wr.receipt_status, 'CONFIRMED') <> 'CANCELLED' "
                    "ORDER BY wr.stage_no, wri.row_no",
                    (inbound_load_id,)
                ).fetchall()
                print(f'_load_receipt_items: got {len(items)} items for inbound_load_id={inbound_load_id}')
                if not items:
                    return
                self.lines_table.setRowCount(0)
                for idx, item in enumerate(items):
                    row = self.lines_table.rowCount()
                    self.lines_table.insertRow(row)
                    no_item = QTableWidgetItem(str(idx + 1))
                    no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
                    no_item.setTextAlignment(Qt.AlignCenter)
                    self.lines_table.setItem(row, 0, no_item)
                    pallet_combo = QComboBox()
                    pallet_combo.addItem('انتخاب پالت', None)
                    for p in self.pallets:
                        pallet_combo.addItem(f"{p['code']} | {p['name']}", p['id'])
                        if p['id'] == item[0]:
                            pallet_combo.setCurrentIndex(pallet_combo.count() - 1)
                    r = row
                    pallet_combo.currentIndexChanged.connect(lambda _, row=r: self._on_receipt_pallet_changed(row))
                    self.lines_table.setCellWidget(row, 1, pallet_combo)
                    qty_spin = QSpinBox()
                    qty_spin.setRange(0, 100000000)
                    qty_spin.setValue(int(item[3] or 0))
                    qty_spin.valueChanged.connect(self.recalculate_lines)
                    self.lines_table.setCellWidget(row, 2, qty_spin)
                    price_edit = QLineEdit(self._fmt_int(int(item[4] or 0)))
                    price_edit.textChanged.connect(lambda: self._handle_price_edit_change(price_edit))
                    self.lines_table.setCellWidget(row, 3, price_edit)
                    total_item = QTableWidgetItem(self._fmt_int(int(item[5] or 0)))
                    total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
                    total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.lines_table.setItem(row, 4, total_item)
                    wh_combo = QComboBox()
                    wh_combo.addItem('انتخاب انبار', None)
                    for w in self.warehouses:
                        wh_combo.addItem(f"{w['code']} | {w['name']}", w['id'])
                        if w['id'] == item[6]:
                            wh_combo.setCurrentIndex(wh_combo.count() - 1)
                    wh_combo.currentIndexChanged.connect(self.recalculate_lines)
                    self.lines_table.setCellWidget(row, 5, wh_combo)
                    defect_edit = QLineEdit(item[7] or '')
                    self.lines_table.setCellWidget(row, 6, defect_edit)
                    # نمایش قیمت میانگین برای این ردیف
                    self._on_receipt_pallet_changed(row)
                self.recalculate_lines()
        except Exception as e:
            print('Load receipt items error:', str(e))

    def _on_receipt_double_click(self, index) -> None:
        """دابل‌کلیک روی حواله در لیست → لود در فرم ویرایش"""
        row = index.row()
        if row < 0:
            return
        item = self.receipts_table.item(row, 0)
        if not item:
            return
        inbound_load_id = int(item.text())
        self._load_receipt_for_edit(inbound_load_id)

    def _edit_selected_receipt(self) -> None:
        """دکمه ویرایش حواله انتخابی"""
        row = self.receipts_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'ویرایش', 'ابتدا یک حواله از جدول انتخاب کنید.')
            return
        item = self.receipts_table.item(row, 0)
        if not item:
            return
        inbound_load_id = int(item.text())
        self._load_receipt_for_edit(inbound_load_id)

    def _load_receipt_for_edit(self, inbound_load_id: int) -> None:
        """لود حواله مادر در فرم برای ویرایش/مشاهده"""
        print(f'_load_receipt_for_edit: inbound_load_id={inbound_load_id}')
        
        # پیدا کردن این inbound_load_id در reference_selector_combo
        found = False
        for i in range(self.reference_selector_combo.count()):
            if self.reference_selector_combo.itemData(i) == inbound_load_id:
                self.reference_selector_combo.setCurrentIndex(i)
                found = True
                break
        
        if not found:
            # اگر در لیست بازها نیست، یعنی تکمیل شده - باید مستقیم لود کنیم
            QMessageBox.information(self, 'مشاهده', 
                'این حواله تکمیل شده است.\n'
                'برای مشاهده پالت‌های ثبت‌شده، از تب "حواله‌های تکمیل‌شده" استفاده کنید.')
            # رفتن به تب تکمیل‌شده‌ها
            self.tabs.setCurrentIndex(3)
            return
        
        # رفتن به تب اطلاعات رسید
        self.tabs.setCurrentIndex(0)

    def _driver_changed(self) -> None:
        driver_id = self.driver_combo.currentData()
        row = next((item for item in self.drivers if item['id'] == driver_id), None)
        if not row:
            self.vehicle_label.setText('-')
            return
        self.vehicle_label.setText(f"{row.get('vehicle_type') or '-'} | {row.get('vehicle_plate') or '-'}")

    def add_line_row(self) -> None:
        row = self.lines_table.rowCount()
        self.lines_table.insertRow(row)
        self.lines_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))

        pallet_combo = QComboBox()
        pallet_combo.addItem('انتخاب پالت', None)
        # برای رسید انبار: همه پالت‌ها نمایش داده شوند (چون بار جدید وارد می‌کنیم)
        for item in self.pallets:
            stock = self.pallet_stock.get(item['id'], 0)
            pallet_combo.addItem(f"{item['code']} | {item['name']}", item['id'])
        r = row  # capture for lambda
        pallet_combo.currentIndexChanged.connect(lambda _, row=r: self._on_receipt_pallet_changed(row))

        qty_spin = QSpinBox()
        qty_spin.setRange(0, 100000000)
        qty_spin.valueChanged.connect(self.recalculate_lines)

        unit_price_edit = QLineEdit()
        unit_price_edit.textChanged.connect(lambda: self._handle_price_edit_change(unit_price_edit))

        line_total_item = QTableWidgetItem('0')
        line_total_item.setFlags(line_total_item.flags() & ~Qt.ItemIsEditable)
        line_total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        warehouse_combo = QComboBox()
        warehouse_combo.addItem('انتخاب انبار', None)
        for item in self.warehouses:
            warehouse_combo.addItem(f"{item['code']} | {item['name']}", item['id'])
        warehouse_combo.currentIndexChanged.connect(self.recalculate_lines)

        defect_edit = QLineEdit()
        defect_edit.setPlaceholderText('عیب یا توضیح ردیف')

        self.lines_table.setCellWidget(row, 1, pallet_combo)
        self.lines_table.setCellWidget(row, 2, qty_spin)
        self.lines_table.setCellWidget(row, 3, unit_price_edit)
        self.lines_table.setItem(row, 4, line_total_item)
        self.lines_table.setCellWidget(row, 5, warehouse_combo)
        self.lines_table.setCellWidget(row, 6, defect_edit)
        self.lines_table.resizeColumnsToContents()
        self.recalculate_lines()

    def remove_selected_line(self) -> None:
        row = self.lines_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'ردیف‌ها', 'ابتدا یک ردیف را انتخاب کنید.')
            return
        self.lines_table.removeRow(row)
        for index in range(self.lines_table.rowCount()):
            item = self.lines_table.item(index, 0)
            if item:
                item.setText(str(index + 1))
        if self.lines_table.rowCount() == 0:
            self.add_line_row()
        self.recalculate_lines()

    def _handle_price_edit_change(self, edit: QLineEdit) -> None:
        self._format_line_edit_number(edit)
        self.recalculate_lines()

    def _format_line_edit_number(self, edit: QLineEdit) -> None:
        digits = ''.join(ch for ch in edit.text() if ch.isdigit())
        edit.blockSignals(True)
        edit.setText(self._fmt_int(int(digits)) if digits else '')
        edit.blockSignals(False)

    def _on_quantity_changed(self) -> None:
        for edit in [self.total_declared_edit, self.stage_declared_edit, self.stage_received_edit]:
            self._format_line_edit_number(edit)
        total = self._int_from_text(self.stage_declared_edit.text())
        received = self._int_from_text(self.stage_received_edit.text())
        self.discrepancy_label.setText(self._fmt_int(max(total - received, 0)))

    def _fmt_int(self, value: int) -> str:
        return f'{int(value):,}'

    def _int_from_text(self, value: str) -> int:
        digits = ''.join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else 0

    def recalculate_lines(self) -> None:
        grand_total = 0
        grand_qty = 0
        for row in range(self.lines_table.rowCount()):
            qty_widget = self.lines_table.cellWidget(row, 2)
            price_widget = self.lines_table.cellWidget(row, 3)
            qty = qty_widget.value() if isinstance(qty_widget, QSpinBox) else 0
            unit_price = self._int_from_text(price_widget.text()) if isinstance(price_widget, QLineEdit) else 0
            line_total = qty * unit_price
            grand_total += line_total
            grand_qty += qty
            item = self.lines_table.item(row, 4)
            if item:
                item.setText(self._fmt_int(line_total))
        self.lines_total_label.setText(f'جمع ریالی ردیف‌ها: {self._fmt_int(grand_total)} ریال')
        if not self.stage_received_edit.hasFocus() and grand_qty > 0:
            self.stage_received_edit.setText(self._fmt_int(grand_qty))
        self._on_quantity_changed()

    def _collect_lines(self) -> List[Dict[str, Any]]:
        lines: List[Dict[str, Any]] = []
        for row in range(self.lines_table.rowCount()):
            pallet_widget = self.lines_table.cellWidget(row, 1)
            qty_widget = self.lines_table.cellWidget(row, 2)
            price_widget = self.lines_table.cellWidget(row, 3)
            warehouse_widget = self.lines_table.cellWidget(row, 5)
            defect_widget = self.lines_table.cellWidget(row, 6)
            lines.append({
                'pallet_id': pallet_widget.currentData() if isinstance(pallet_widget, QComboBox) else None,
                'quantity': qty_widget.value() if isinstance(qty_widget, QSpinBox) else 0,
                'unit_price': price_widget.text() if isinstance(price_widget, QLineEdit) else '0',
                'warehouse_id': warehouse_widget.currentData() if isinstance(warehouse_widget, QComboBox) else None,
                'defect_notes': defect_widget.text() if isinstance(defect_widget, QLineEdit) else '',
            })
        return lines

    def _collect_payload(self) -> Dict[str, Any]:
        return {
            'inbound_load_id': self.reference_selector_combo.currentData(),
            'operation_date': self._current_iso_date(),
            'supplier_person_id': self.supplier_combo.currentData(),
            'driver_person_id': self.driver_combo.currentData(),
            'total_declared_qty': self.total_declared_edit.text(),
            'stage_declared_qty': self.stage_declared_edit.text(),
            'stage_received_qty': self.stage_received_edit.text(),
            'freight_amount': self.freight_edit.text(),
            'waybill_no': self.waybill_edit.text(),
            'source_location': self.source_location_edit.text(),
            'destination_location': self.destination_location_edit.text(),
            'warehouse_keeper_name': self.warehouse_keeper_edit.text(),
            'receiver_name': self.receiver_name_edit.text(),
            'notes': self.notes_edit.toPlainText(),
            'lines': self._collect_lines(),
        }

    def _select_combo_by_data(self, combo: QComboBox, value: Any) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(0)

    def _build_preview_context_from_form(self) -> Dict[str, Any]:
        payload = self._collect_payload()
        from app.core.validators import validate_receipt_payload
        data = validate_receipt_payload(payload)
        supplier_text = self.supplier_combo.currentText() or '-'
        driver_text = self.driver_combo.currentText().split('|')[0].strip() or '-'
        vehicle_text = self.vehicle_label.text() or '-'
        vehicle_parts = [part.strip() for part in vehicle_text.split('|', 1)]
        vehicle_type = vehicle_parts[0] if vehicle_parts else '-'
        vehicle_plate = vehicle_parts[1] if len(vehicle_parts) > 1 else '-'
        lines = []
        for idx, line in enumerate(data['lines'], start=1):
            pallet_widget = self.lines_table.cellWidget(idx - 1, 1)
            warehouse_widget = self.lines_table.cellWidget(idx - 1, 5)
            lines.append({
                'row_no': idx,
                'pallet_code': (pallet_widget.currentText().split('|')[0].strip() if isinstance(pallet_widget, QComboBox) else '-'),
                'pallet_name': (pallet_widget.currentText().split('|', 1)[1].strip() if isinstance(pallet_widget, QComboBox) and '|' in pallet_widget.currentText() else pallet_widget.currentText() if isinstance(pallet_widget, QComboBox) else '-'),
                'quantity': line['quantity'],
                'unit_price': line['unit_price'],
                'total_amount': line['line_total_amount'],
                'warehouse_name': (warehouse_widget.currentText().split('|', 1)[1].strip() if isinstance(warehouse_widget, QComboBox) and '|' in warehouse_widget.currentText() else warehouse_widget.currentText() if isinstance(warehouse_widget, QComboBox) else '-'),
                'defect_description': line['defect_notes'] or '-',
            })
        total_amount = sum(item['total_amount'] for item in lines)
        return {
            'reference_no': self.reference_no_label.text(),
            'receipt_no': self.document_no_label.text(),
            'stage_no': int(self.stage_no_label.text() or '1'),
            'operation_date_iso': data['operation_date'],
            'operation_date_jalali': jalali_date_display_from_iso(data['operation_date']),
            'waybill_no': data['waybill_no'] or '-',
            'supplier_name': supplier_text,
            'driver_name': driver_text,
            'vehicle_type': vehicle_type,
            'vehicle_plate': vehicle_plate,
            'source_location': data['source_location'] or '-',
            'destination_location': data['destination_location'] or '-',
            'total_declared_qty': data['total_declared_qty'],
            'stage_load_qty': data['stage_declared_qty'],
            'delivered_qty': data['stage_received_qty'],
            'discrepancy_qty': data['stage_declared_qty'] - data['stage_received_qty'],
            'freight_amount': data['freight_amount'],
            'lines_total_amount': total_amount,
            'warehouse_keeper_name': data['warehouse_keeper_name'] or '-',
            'receiver_name': data['receiver_name'] or '-',
            'notes': data['notes'] or '-',
            'lines': lines,
        }

    def preview_current_receipt(self) -> None:
        """پیش‌نمایش حواله مادر از تب اطلاعات رسید"""
        selected_reference_id = self.reference_selector_combo.currentData()
        if not selected_reference_id:
            # اگر مرجع انتخاب نشده، از لیست بگیر
            QMessageBox.information(self, 'پیش‌نمایش رسید',
                'ابتدا یک مرجع بار از تب "لیست رسیدها" انتخاب کنید و سپس دکمه پیش‌نمایش را بزنید.\n'
                'یا در تب "اطلاعات رسید" یک مرجع بار باز انتخاب کنید.')
            return

        try:
            details = self.repository.get_completed_receipt_details(selected_reference_id)
            if not details:
                QMessageBox.warning(self, 'پیش‌نمایش', 'حواله یافت نشد.')
                return
            html = self.repository.render_completed_receipt_html(details)
            HtmlPreviewDialog(f'پیش‌نمایش حواله: {details.get("reference_no", "-")}', html, self).exec_()
        except Exception as exc:
            QMessageBox.critical(self, 'خطا در پیش‌نمایش', f'خطا: {exc}')

    def save_receipt(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه ثبت رسید را ندارید.')
            return
        try:
            saved = self.repository.create_inbound_receipt(self._collect_payload(), user_id=self.user_data.get('id'))
        except ValidationError as exc:
            QMessageBox.warning(self, 'ثبت رسید', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'ثبت رسید با خطا مواجه شد:\n{exc}')
            return

        QMessageBox.information(
            self, 'رسید ثبت شد',
            f"رسید با موفقیت ثبت و تایید شد.\nشماره مرجع: {saved.get('reference_no')}\nشماره رسید: {saved.get('receipt_no')}",
        )
        self._load_lookups()
        self.refresh_recent_receipts()
        self.clear_form()
        self.data_changed.emit()
        if saved.get('print_html'):
            HtmlPreviewDialog('پیش‌نمایش رسید ثبت‌شده', saved['print_html'], self).exec_()

    def refresh_recent_receipts(self) -> None:
        rows = self.repository.list_recent_receipts()
        self.receipts_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            total_load = row.get('total_load_qty', 0) or 0
            delivered = row.get('delivered_qty', 0) or 0
            remaining = row.get('remaining_qty', 0) or 0
            values = [
                str(row['id']),
                row['reference_no'],
                row.get('supplier_name') or '-',
                row.get('driver_name') or '-',
                self._fmt_int(int(total_load)),
                self._fmt_int(int(delivered)),
                self._fmt_int(int(remaining)),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.receipts_table.setItem(row_index, column_index, item)
            # دابل‌کلیک برای ویرایش
            self.receipts_table.item(row_index, 1).setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable
            )
        self.receipts_table.resizeColumnsToContents()
        self.receipts_table.doubleClicked.connect(self._on_receipt_double_click)

    def preview_selected_saved_receipt(self) -> None:
        """پیش‌نمایش حواله مادر با همه مراحل"""
        row = self.receipts_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'پیش‌نمایش', 'ابتدا یک حواله را از جدول انتخاب کنید.')
            return
        item = self.receipts_table.item(row, 0)
        if not item:
            return
        try:
            inbound_load_id = int(item.text())
            details = self.repository.get_completed_receipt_details(inbound_load_id)
            if not details:
                QMessageBox.warning(self, 'پیش‌نمایش', 'حواله یافت نشد.')
                return
            html = self.repository.render_completed_receipt_html(details)
            HtmlPreviewDialog(f'پیش‌نمایش حواله: {details.get("reference_no", "-")}', html, self).exec_()
        except Exception as exc:
            QMessageBox.critical(self, 'خطا در پیش‌نمایش', f'خطا: {exc}')

    def rollback_selected_receipt(self) -> None:
        """ابطال کل حواله مادر با همه مراحل"""
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه ابطال حواله را ندارید.')
            return
        row = self.receipts_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'ابطال حواله', 'ابتدا یک حواله را از جدول انتخاب کنید.')
            return
        item = self.receipts_table.item(row, 0)
        if not item:
            return

        inbound_load_id = int(item.text())

        try:
            details = self.repository.get_completed_receipt_details(inbound_load_id)
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'دریافت اطلاعات حواله با خطا مواجه شد:\n{exc}')
            return

        if not details:
            QMessageBox.warning(self, 'خطا', 'حواله یافت نشد.')
            return

        # بررسی اینکه آیا حداقل یک مرحله فعال وجود دارد
        active_stages = [s for s in details.get('stages', []) if s.get('receipt_status') != 'CANCELLED']
        if not active_stages:
            QMessageBox.warning(self, 'خطا', 'این حواله قبلاً ابطال شده است.')
            return

        # خواندن موجودی فعلی و محاسبه موجودی پس از ابطال
        rollback_items = []
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                lines = conn.execute(
                    """
                    SELECT wri.row_no, wri.pallet_id, wri.qty, wri.unit_price,
                           wri.total_price, wri.warehouse_id,
                           p.code as pallet_code, p.name as pallet_name,
                           w.name as warehouse_name,
                           COALESCE((SELECT SUM(CASE WHEN t.transaction_type='IN' THEN t.qty ELSE -t.qty END)
                                    FROM inventory_transactions t
                                    WHERE t.pallet_id = wri.pallet_id
                                    AND t.warehouse_id = wri.warehouse_id
                                    AND COALESCE(t.is_void, 0) = 0), 0) as current_qty
                    FROM warehouse_receipt_items wri
                    JOIN warehouse_receipts wr ON wr.id = wri.receipt_id
                    JOIN pallets p ON p.id = wri.pallet_id
                    LEFT JOIN warehouses w ON w.id = wri.warehouse_id
                    WHERE wr.inbound_load_id = ?
                    AND COALESCE(wr.receipt_status, 'CONFIRMED') <> 'CANCELLED'
                    ORDER BY wr.stage_no, wri.row_no
                    """,
                    (inbound_load_id,),
                ).fetchall()

                for line in lines:
                    current_qty = int(line[9] or 0)
                    rollback_qty = int(line[2])
                    after_qty = current_qty - rollback_qty
                    if after_qty < 0:
                        raise ValidationError(
                            f'موجودی پالت «{line[7]}» در انبار «{line[8] or '-'}» کافی نیست.\n'
                            f'موجودی فعلی: {current_qty:,} | نیاز ابطال: {rollback_qty:,}'
                        )
                    rollback_items.append({
                        'row_no': line[0],
                        'pallet_code': line[6],
                        'pallet_name': line[7],
                        'warehouse_name': line[8] or '-',
                        'rollback_qty': rollback_qty,
                        'current_qty': current_qty,
                        'after_qty': after_qty,
                    })
        except ValidationError as exc:
            QMessageBox.warning(self, 'ابطال ممکن نیست', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا در بررسی موجودی:\n{exc}')
            return

        # نمایش پیش‌نمایش در پنجره
        dialog = QDialog(self)
        dialog.setWindowTitle(f'پیش‌نمایش ابطال حواله {details.get("reference_no", "-")}')
        dialog.resize(900, 600)
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #e2e8f0; font-size: 13px; }
            QGroupBox { color: #e2e8f0; font-weight: bold;
                        border: 1px solid #334155; border-radius: 6px;
                        margin-top: 10px; padding-top: 10px; }
            QTableWidget { background-color: #1e293b; color: #e2e8f0;
                           gridline-color: #334155; }
            QHeaderView::section { background-color: #334155; color: #e2e8f0;
                                   padding: 6px; border: 1px solid #475569; }
        """)
        layout = QVBoxLayout(dialog)

        info_group = QGroupBox('اطلاعات حواله در حال ابطال')
        info_layout = QGridLayout(info_group)
        info_layout.addWidget(QLabel('مرجع بار:'), 0, 0)
        info_layout.addWidget(QLabel(details.get('reference_no') or '-'), 0, 1)
        info_layout.addWidget(QLabel('تأمین‌کننده:'), 1, 0)
        info_layout.addWidget(QLabel(details.get('supplier_name') or '-'), 1, 1)
        info_layout.addWidget(QLabel('راننده:'), 2, 0)
        info_layout.addWidget(QLabel(details.get('driver_name') or '-'), 2, 1)
        info_layout.addWidget(QLabel('تعداد کل:'), 0, 2)
        info_layout.addWidget(QLabel(f"{int(details.get('total_load_qty') or 0):,}"), 0, 3)
        info_layout.addWidget(QLabel('تعداد تحویل:'), 1, 2)
        total_delivered = sum(item.get('quantity', 0) for item in details.get('items', []))
        info_layout.addWidget(QLabel(f"{total_delivered:,}"), 1, 3)
        info_layout.addWidget(QLabel('تعداد مراحل:'), 2, 2)
        info_layout.addWidget(QLabel(str(len(active_stages))), 2, 3)
        layout.addWidget(info_group)

        impact_group = QGroupBox('تأثیر ابطال بر موجودی پالت‌ها')
        impact_layout = QVBoxLayout(impact_group)
        impact_table = QTableWidget(0, 7)
        impact_table.setHorizontalHeaderLabels([
            'ردیف', 'کد پالت', 'نام پالت', 'انبار',
            'موجودی فعلی', 'کاهش', 'موجودی پس از ابطال'
        ])
        impact_table.verticalHeader().setVisible(False)
        impact_table.setRowCount(len(rollback_items))

        for idx, it in enumerate(rollback_items):
            vals = [
                str(it['row_no']),
                it['pallet_code'],
                it['pallet_name'],
                it['warehouse_name'],
                f"{it['current_qty']:,}",
                f"-{it['rollback_qty']:,}",
                f"{it['after_qty']:,}",
            ]
            for col, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                cell.setBackground(QColor('#1e293b'))
                if col == 5:
                    cell.setForeground(QColor('#ef4444'))
                elif col == 6:
                    if it['after_qty'] == 0:
                        cell.setForeground(QColor('#f59e0b'))
                    else:
                        cell.setForeground(QColor('#10b981'))
                impact_table.setItem(idx, col, cell)

        impact_table.resizeColumnsToContents()
        impact_layout.addWidget(impact_table)
        layout.addWidget(impact_group)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton('انصراف')
        cancel_btn.setObjectName('SecondaryButton')
        cancel_btn.clicked.connect(dialog.reject)
        confirm_btn = QPushButton('تأیید و ابطال')
        confirm_btn.setStyleSheet("""
            QPushButton { background-color: #dc2626; color: white;
                         font-weight: bold; padding: 8px 20px; border-radius: 4px; }
            QPushButton:hover { background-color: #b91c1c; }
        """)
        confirm_btn.clicked.connect(dialog.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

        if dialog.exec_() != QDialog.Accepted:
            return

        try:
            result = self.repository.rollback_inbound_load(
                inbound_load_id,
                user_id=self.user_data.get('id'),
            )
        except ValidationError as exc:
            QMessageBox.warning(self, 'ابطال حواله', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'ابطال حواله با خطا مواجه شد:\n{exc}')
            return

        # گزارش کامل ابطال
        report_dialog = QDialog(self)
        report_dialog.setWindowTitle('گزارش ابطال حواله')
        report_dialog.resize(700, 450)
        report_dialog.setLayoutDirection(Qt.RightToLeft)
        report_dialog.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #e2e8f0; }
        """)
        r_layout = QVBoxLayout(report_dialog)

        success_lbl = QLabel('✔ عملیات ابطال با موفقیت انجام شد')
        success_lbl.setStyleSheet('color: #10b981; font-size: 18px; font-weight: bold;')
        success_lbl.setAlignment(Qt.AlignCenter)
        r_layout.addWidget(success_lbl)

        r_layout.addWidget(QLabel(f"مرجع بار: {details.get('reference_no', '-')}"))
        r_layout.addWidget(QLabel(f"تعداد کل ابطال: {total_delivered:,} پالت"))
        r_layout.addWidget(QLabel(f"تعداد مراحل ابطال‌شده: {len(active_stages)}"))

        summary_text = 'پالت‌های تحت تأثیر:\n'
        for it in rollback_items:
            summary_text += (
                f"  • {it['pallet_code']} ({it['pallet_name']}) در {it['warehouse_name']}: "
                f"{it['current_qty']:,} → {it['after_qty']:,} ({it['rollback_qty']:,}-)\n"
            )

        summary_lbl = QLabel(summary_text)
        summary_lbl.setWordWrap(True)
        summary_lbl.setStyleSheet(
            'color: #e2e8f0; font-size: 12px; background-color: #1e293b; '
            'padding: 10px; border-radius: 4px; border: 1px solid #334155;'
        )
        r_layout.addWidget(summary_lbl)

        note_lbl = QLabel('⚠ سندهای مالی مرتبط نیز ابطال شدند.')
        note_lbl.setStyleSheet('color: #f59e0b; font-size: 12px;')
        r_layout.addWidget(note_lbl)

        close_btn = QPushButton('بستن')
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(report_dialog.accept)
        r_layout.addWidget(close_btn)

        report_dialog.exec_()

        self._load_lookups()
        self.refresh_recent_receipts()
        self.data_changed.emit()

    def open_cancelled_archive(self) -> None:
        """باز کردن فرم بایگانی سندهای ابطال‌شده"""
        try:
            from app.ui.cancelled_receipts_window import CancelledReceiptsWindow
            window = CancelledReceiptsWindow(self.db, self.user_data, self)
            window.exec_()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در باز کردن بایگانی:\n{e}')

    def refresh_completed_receipts(self) -> None:
        """بارگذاری حواله‌های تکمیل‌شده"""
        rows = self.repository.list_completed_receipts()
        self.completed_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row['id']),
                row['reference_no'],
                row.get('supplier_name') or '-',
                row.get('driver_name') or '-',
                self._fmt_int(int(row.get('total_load_qty') or 0)),
                self._fmt_int(int(row.get('total_received') or 0)),
                self._fmt_int(int(row.get('remaining_qty') or 0)),
                self._fmt_int(int(row.get('total_amount') or 0)) + ' ریال',
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.completed_table.setItem(row_index, column_index, item)
        self.completed_table.resizeColumnsToContents()

    def print_selected_completed_receipt(self) -> None:
        """پرینت حواله تکمیل‌شده انتخابی"""
        row = self.completed_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'پرینت', 'ابتدا یک حواله از جدول انتخاب کنید.')
            return
        item = self.completed_table.item(row, 0)
        if not item:
            return
        try:
            inbound_load_id = int(item.text())
            details = self.repository.get_completed_receipt_details(inbound_load_id)
            if not details:
                QMessageBox.warning(self, 'خطا', 'حواله یافت نشد.')
                return
            html = self.repository.render_completed_receipt_html(details)
            HtmlPreviewDialog(f'پرینت حواله: {details.get("reference_no", "-")}', html, self).exec_()
        except Exception as exc:
            QMessageBox.critical(self, 'خطا در پرینت', f'خطا: {exc}')

    def clear_form(self) -> None:
        self.operation_date_edit.setDate(QDate.fromString(today_iso_date(), 'yyyy-MM-dd'))
        self.reference_selector_combo.setCurrentIndex(0)
        self.waybill_edit.clear()
        self.supplier_combo.setCurrentIndex(0)
        self.driver_combo.setCurrentIndex(0)
        self.total_declared_edit.clear()
        self.stage_declared_edit.clear()
        self.stage_received_edit.clear()
        self.freight_edit.clear()
        self.source_location_edit.clear()
        self.destination_location_edit.clear()
        self.warehouse_keeper_edit.clear()
        self.receiver_name_edit.clear()
        self.notes_edit.clear()
        self.vehicle_label.setText('-')
        self.lines_table.setRowCount(0)
        self.avg_price_value.setText('0 ریال')
        self.add_line_row()
        self._load_lookups()
        self._refresh_reference_numbers()
        self._on_quantity_changed()
