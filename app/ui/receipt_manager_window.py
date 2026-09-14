# -*- coding: utf-8 -*-
"""
Receipt Manager Window - نسخه نهایی و یکپارچه (هم‌ساختار با Issue Manager)
ویژگی‌ها:
- انتقال دکمه‌های عملیاتی به نوار ابزار بالای فرم (Top Bar)
- ثبت رسید انبار با پشتیبانی مرحله‌ای
- ابطال رسید با پیش‌نمایش موجودی
- تکمیل خودکار عبارات (F2 / Ctrl+Space)
- دیتاگرید یکدست + کامبو پالت با موجودی/میانگین
"""
import tempfile
import webbrowser
from typing import Any, Dict, List, Optional, Set
from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtGui import QGuiApplication, QColor
from PyQt5.QtWidgets import (
    QCheckBox, QAbstractItemView, QComboBox, QDateEdit, QDialog, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget, QScrollArea, QApplication,
)
from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_display_from_iso, today_iso_date
from app.core.validators import ValidationError
from app.core.pallet_service import PalletService
from app.repositories.receipt_repository import ReceiptRepository
from app.core.stock_service import free_stock  # ONE-STOCK

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
        self.avg_pallet_prices: Dict[int, float] = {}
        self.pallet_stock: Dict[int, int] = {}
        self.allowed_pallet_ids: Optional[Set[int]] = None
        
        self.setWindowTitle('رسید انبار')
        self.resize(1200, 850)
        self._build_ui()
        #  پیام راهنمای ورود
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, lambda: QMessageBox.information(self, "راهنما", "برای مشاهده لیست، ابتدا انبار مقصد را انتخاب کنید."))
        self._load_lookups()
        self._apply_permissions()
        self._refresh_reference_numbers()
        self.refresh_receipts_final()

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.refresh_completed_receipts()
        except Exception:
            pass
        self.setWindowState(Qt.WindowMaximized)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # --- هدر فرم ---
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

        # --- انتخاب انبار مقصد ---
        wh_group = QGroupBox('انتخاب انبار مقصد')
        whl = QVBoxLayout(wh_group)
        wtop = QHBoxLayout()
        wtop.addWidget(QLabel('انبار:'))
        self.warehouse_combo = QComboBox()
        self.warehouse_combo.setMinimumWidth(300)
        self.warehouse_combo.addItem('-- ابتدا انبار را انتخاب کنید --', None)
        self.warehouse_combo.currentIndexChanged.connect(self._on_warehouse_changed)
        wtop.addWidget(self.warehouse_combo, 1)
        wtop.addStretch()
        whl.addLayout(wtop)
        
        self.warehouse_msg_lbl = QLabel('⚠️ ابتدا انبار را انتخاب کنید تا پالت‌ها و میانگین قیمت لود شوند.')
        self.warehouse_msg_lbl.setObjectName('WarningLabel')
        whl.addWidget(self.warehouse_msg_lbl)
        root.addWidget(wh_group)

        # --- نوار ابزار بالا (فقط دکمه‌های عملیاتی اصلی) ---
        top_bar = QHBoxLayout()
        self.save_button = QPushButton('✅ ثبت و تایید رسید')
        self.save_button.setObjectName('SuccessButton')
        self.new_button = QPushButton('رسید جدید')
        self.new_button.setObjectName('SecondaryButton')
        
        for _b in (self.save_button, self.new_button):
            _b.setMinimumWidth(130)
            
        top_bar.addStretch()
        top_bar.addWidget(self.new_button)
        top_bar.addWidget(self.save_button)
        
        self.save_button.clicked.connect(self.save_receipt)
        self.new_button.clicked.connect(self.clear_form)
        
        root.addLayout(top_bar)

        # --- تب‌های اصلی ---
        self.tabs = QTabWidget()
        
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
        self.date_info_label.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
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
        
        avg_price_bar = QHBoxLayout()
        avg_price_bar.setContentsMargins(4, 4, 4, 4)
        self.avg_price_lbl = QLabel('قیمت میانگین: ')
        self.avg_price_lbl.setObjectName('AvgPriceLabel')
        self.avg_price_value = QLabel('0 ریال')
        self.avg_price_value.setObjectName('AvgPriceValue')
        avg_price_bar.addWidget(self.avg_price_lbl)
        avg_price_bar.addWidget(self.avg_price_value)
        avg_price_bar.addStretch()
        
        self.receipt_pct_lbl = QLabel('درصد:')
        self.receipt_pct_lbl.setObjectName('IssuePctLabel')
        self.receipt_pct_edit = QLineEdit('40')
        self.receipt_pct_edit.setFixedWidth(70)
        self.receipt_pct_edit.textChanged.connect(self._receipt_recalc_percent)
        self.receipt_calc_val = QLabel('-')
        self.receipt_calc_val.setObjectName('IssueCalcValue')
        avg_price_bar.addWidget(self.receipt_pct_lbl)
        avg_price_bar.addWidget(self.receipt_pct_edit)
        avg_price_bar.addWidget(self.receipt_calc_val)
        self.receipt_mode_lbl = QLabel('حالت خرید: قیمت ردیف با میانگین پر می‌شود')
        self.receipt_mode_lbl.setObjectName('WarningLabel')
        avg_price_bar.addWidget(self.receipt_mode_lbl)
        avg_price_bar.addStretch()
        
        for _lb in (self.avg_price_lbl, self.avg_price_value, self.receipt_pct_lbl, self.receipt_calc_val):
            _lb.setFixedHeight(38)
        self.receipt_pct_edit.setFixedHeight(34)
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
        
        self.lines_table = QTableWidget(0, 6)
        self.lines_table.setHorizontalHeaderLabels(['ردیف', 'پالت', 'تعداد', 'قیمت هر پالت', 'مبلغ کل', 'عیوب / توضیح'])
        self.lines_table.horizontalHeader().setFixedHeight(32)
        self.lines_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.lines_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lines_table.verticalHeader().setVisible(False)
        lines_layout.addWidget(self.lines_table, 1)
        self._setup_lines_table_layout()
        lines_group.setMaximumHeight(430)
        tab_pallet_layout.addWidget(lines_group)
        
        totals_group = QGroupBox('قیمت نهایی (ارزش افزوده و مخارج)')
        totals_layout = QGridLayout(totals_group)
        totals_layout.setHorizontalSpacing(12)
        totals_layout.setVerticalSpacing(10)
        
        self.vat_checkbox = QCheckBox('ارزش افزوده ۹٪')
        self.vat_checkbox.toggled.connect(self._recalc_final_total)
        totals_layout.addWidget(self.vat_checkbox, 0, 0)
        self.vat_amount_label = QLabel('۰ ریال')
        self.vat_amount_label.setObjectName('VatAmountLabel')
        totals_layout.addWidget(self.vat_amount_label, 0, 1)
        
        self.extra_checkbox = QCheckBox('مخارج اضافی')
        self.extra_checkbox.toggled.connect(self._on_extra_toggled)
        totals_layout.addWidget(self.extra_checkbox, 1, 0)
        self.extra_costs_edit = QLineEdit()
        self.extra_costs_edit.setPlaceholderText('۰')
        self.extra_costs_edit.setFixedWidth(200)
        self.extra_costs_edit.setEnabled(False)
        self.extra_costs_edit.setAlignment(Qt.AlignCenter)
        self.extra_costs_edit.setObjectName('ExtraCostsEdit')
        self.extra_costs_edit.textChanged.connect(self._format_extra_costs_edit)
        totals_layout.addWidget(self.extra_costs_edit, 1, 1)
        
        self.final_total_label = QLabel('قیمت نهایی: ۰ ریال')
        self.final_total_label.setObjectName('FinalTotalLabel')
        totals_layout.addWidget(self.final_total_label, 2, 0, 1, 2)
        tab_pallet_layout.addWidget(totals_group)
        
        # ==================== تب ۳: لیست رسیدها ====================
        tab_list = QWidget()
        tab_list_layout = QVBoxLayout(tab_list)
        tab_list_layout.setSpacing(14)
        
        right_group = QGroupBox('رسیدهای ثبت‌شده')
        right_layout = QVBoxLayout(right_group)
        
        # ✅ نوار ابزار پایین (اینجا دکمه‌ها قرار می‌گیرند)
        right_toolbar = QHBoxLayout()
        
        refresh_receipts_btn = QPushButton('بروزرسانی لیست')
        refresh_receipts_btn.setObjectName('SecondaryButton')
        refresh_receipts_btn.clicked.connect(self.refresh_receipts_final)
        
        # ✅ دکمه جزئیات رسید (جایگزین پیش‌نمایش)
        details_btn = QPushButton('📄 جزئیات رسید')
        details_btn.setObjectName('PrimaryButton')
        details_btn.clicked.connect(self.preview_selected_saved_receipt)
        
        rollback_btn = QPushButton('rollback سند انتخابی')
        rollback_btn.setObjectName('SecondaryButton')
        rollback_btn.clicked.connect(self.rollback_selected_receipt)
        
        archive_btn = QPushButton('بایگانی ابطال‌ها')
        archive_btn.setObjectName('SecondaryButton')
        archive_btn.clicked.connect(self.open_cancelled_archive)
        
        right_toolbar.addWidget(refresh_receipts_btn)
        self.preview_doc_btn = QPushButton('پیش‌نمایش سند انتخابی')  # BTN-FINAL
        self.preview_doc_btn.clicked.connect(self.preview_selected_saved_receipt)
        right_toolbar.addWidget(self.preview_doc_btn)
        self.remaining_rcpt_btn = QPushButton('رسیدهای مانده')  # BTN-FINAL
        self.remaining_rcpt_btn.clicked.connect(self._show_remaining_receipts)
        right_toolbar.addWidget(self.remaining_rcpt_btn)
        right_toolbar.addWidget(details_btn) # اضافه کردن دکمه جدید
        right_toolbar.addWidget(rollback_btn)
        right_toolbar.addWidget(archive_btn)
        for _tb in (refresh_receipts_btn, details_btn, rollback_btn, archive_btn):
            _tb.setMinimumWidth(150)
        right_toolbar.addStretch()
        right_layout.addLayout(right_toolbar)
        
        self.receipts_table = QTableWidget(0, 9)
        self.receipts_table.setHorizontalHeaderLabels(['شناسه', 'مرجع بار', 'تأمین‌کننده', 'راننده', 'تعداد کل حواله', 'تعداد تحویل', 'مانده حواله', 'تاریخ', 'انبار'])
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
        self.completed_table.setHorizontalHeaderLabels(['شناسه', 'مرجع بار', 'تأمین‌کننده', 'راننده', 'تعداد کل حواله', 'تعداد تحویل', 'مانده', 'مبلغ کل'])
        self.completed_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.completed_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.completed_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.completed_table.verticalHeader().setVisible(False)
        self.completed_table.setColumnHidden(0, True)
        self.completed_table.horizontalHeader().setStretchLastSection(True)
        completed_layout.addWidget(self.completed_table)
        tab_completed_layout.addWidget(completed_group)
        
        self.tabs.addTab(tab_info, 'اطلاعات رسید')
        self.tabs.addTab(tab_pallet, 'افزودن پالت')
        self.tabs.addTab(tab_list, 'لیست رسیدها')
        self.tabs.addTab(tab_completed, 'حواله‌های تکمیل‌شده')
        root.addWidget(self.tabs, 1)
        
        self._setup_autocomplete()

    def _setup_autocomplete(self) -> None:
        try:
            from app.core.auto_complete import AutoCompleteStore, attach_autocomplete, install_window_shortcuts
        except Exception as exc:
            print('[auto-complete] import error:', exc)
            return
        try:
            self._ac_store = AutoCompleteStore()
            self._ac_filters = {}
            fields = [
                (self.waybill_edit, 'waybill_no'),
                (self.source_location_edit, 'source_location'),
                (self.destination_location_edit, 'destination_location'),
                (self.warehouse_keeper_edit, 'warehouse_keeper'),
                (self.receiver_name_edit, 'receiver_name'),
                (self.notes_edit, 'notes'),
            ]
            for widget, key in fields:
                self._ac_filters[widget] = attach_autocomplete(self._ac_store, widget, key)
            install_window_shortcuts(self, self._ac_filters)
        except Exception as exc:
            print('[auto-complete] setup error:', exc)

    def _ac_save_all(self) -> None:
        for flt in getattr(self, '_ac_filters', {}).values():
            try:
                flt.save_now()
            except Exception:
                pass

    def _setup_lines_table_layout(self) -> None:
        from PyQt5.QtWidgets import QHeaderView
        tbl = self.lines_table
        header = tbl.horizontalHeader()
        header.setMinimumSectionSize(40)
        header.setStretchLastSection(False)
        widths = {0: 45, 1: 260, 2: 85, 3: 130, 4: 130}
        for col, w in widths.items():
            header.setSectionResizeMode(col, QHeaderView.Interactive)
            tbl.setColumnWidth(col, w)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        tbl.verticalHeader().setDefaultSectionSize(34)
        tbl.setWordWrap(False)

    def _build_receipt_details_html(self, details) -> str:
        """ساخت HTML جزئیات رسید برای چاپ و پیش‌نمایش"""
        from app.core.letterhead import get_filtered_company
        company = get_filtered_company(self.db)
        
        rows_html = ''
        total_qty = 0
        total_amount = 0
        
        items = details.get('items', [])
        for item in items:
            qty = item.get('quantity', 0)
            price = item.get('unit_price', 0)
            amount = item.get('total_amount', 0)
            rows_html += f"""<tr>
                <td>{item.get('row_no', '')}</td>
                <td>{item.get('pallet_code', '')}</td>
                <td>{item.get('pallet_name', '')}</td>
                <td>{qty:,}</td>
                <td>{price:,}</td>
                <td>{amount:,}</td>
                <td>{item.get('warehouse_name', '')}</td>
            </tr>"""
            total_qty += qty
            total_amount += amount
        
        # دریافت مقادیر با مقدار پیش‌فرض
        receipt_no = details.get('receipt_no', '-')
        receipt_date = details.get('receipt_date', '-')
        reference_no = details.get('reference_no', '-')
        supplier_name = details.get('supplier_name', '-')
        driver_name = details.get('driver_name', '-')
        receipt_status = details.get('receipt_status', 'CONFIRMED')
        
        html = f"""<!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>جزئیات رسید ورودی: {reference_no}</title>
        <style>
            body {{ font-family: Tahoma, Arial, sans-serif; padding: 20px; direction: rtl; background: #fff; }}
            .header {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-bottom: 2px solid #2563eb; }}
            .header h2 {{ margin: 0; color: #46505f; }}
            .info-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }}
            .info-item {{ padding: 10px; background: #fff; border: 1px solid #dee2e6; border-radius: 4px; }}
            .info-label {{ font-weight: bold; color: #46505f; display: block; margin-bottom: 5px; font-size: 12px; }}
            .info-value {{ color: #1e293b; font-size: 14px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background: #46505f; color: white; padding: 10px; text-align: center; border: 1px solid #5b6675; font-size: 13px; }}
            td {{ padding: 8px; text-align: center; border: 1px solid #e2e8f0; font-size: 12px; }}
            tr:nth-child(even) {{ background-color: #f8fafc; }}
            .footer {{ background: #f1f5f9; padding: 15px; border-radius: 8px; margin-top: 20px; border-top: 2px solid #2563eb; display: flex; justify-content: space-between; }}
            .total {{ font-size: 16px; font-weight: bold; color: #059669; }}
            .print-btn {{ position: fixed; top: 20px; left: 20px; padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }}
            @media print {{ .print-btn {{ display: none; }} }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>اطلاعات رسید ورودی</h2>
            <p style="margin: 5px 0 0 0; color: #6b7686;">{company.get('company_name', 'نام شرکت')}</p>
        </div>
        
        <div class="info-grid">
            <div class="info-item">
                <span class="info-label">شماره حواله:</span>
                <span class="info-value">{receipt_no}</span>
            </div>
            <div class="info-item">
                <span class="info-label">مرجع بار:</span>
                <span class="info-value">{reference_no}</span>
            </div>
            <div class="info-item">
                <span class="info-label">تاریخ:</span>
                <span class="info-value">{receipt_date}</span>
            </div>
            <div class="info-item">
                <span class="info-label">تأمین‌کننده:</span>
                <span class="info-value">{supplier_name}</span>
            </div>
            <div class="info-item">
                <span class="info-label">راننده:</span>
                <span class="info-value">{driver_name}</span>
            </div>
            <div class="info-item">
                <span class="info-label">وضعیت:</span>
                <span class="info-value">{receipt_status}</span>
            </div>
        </div>
        
        <h3 style="color: #46505f; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">ردیف‌های پالت</h3>
        <table>
            <thead>
                <tr>
                    <th>ردیف</th>
                    <th>کد پالت</th>
                    <th>نام پالت</th>
                    <th>تعداد</th>
                    <th>قیمت واحد</th>
                    <th>مبلغ کل</th>
                    <th>انبار</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        
        <div class="footer">
            <div class="total">تعداد کل: {total_qty:,} پالت</div>
            <div class="total">مبلغ کل: {total_amount:,} ریال</div>
        </div>
        
        <p style="text-align: center; color: #64748b; font-size: 11px; margin-top: 30px;">این سند به صورت سیستمی تولید شده است</p>
    </body>
    </html>"""
        return html 

    def _open_html_in_browser(self, html: str) -> None:  # DLG-FINAL
        """پیش‌نمایش HTML با ترجیح WebEngine و بازگشت به دیالوگ ساده."""
        parent = self
        candidates = (
            ('app.ui.webengine_preview', 'HtmlPreviewDialog'),
            ('webengine_preview', 'HtmlPreviewDialog'),
            ('app.ui.html_preview_dialog', 'HtmlPreviewDialog'),
            ('html_preview_dialog', 'HtmlPreviewDialog'),
        )
        for mod_name, cls_name in candidates:
            try:
                module = __import__(mod_name, fromlist=[cls_name])
            except Exception:
                continue
            cls = getattr(module, cls_name, None)
            if cls is None:
                continue
            try:
                dlg = cls(html, '', parent)
                try:
                    dlg.setAttribute(Qt.WA_DeleteOnClose, True)  # PATCH-DELETEONCLOSE
                except Exception:
                    pass
                dlg.exec_()
            except Exception:
                continue
            return
        # هیچ پیش‌نمایشی در دسترس نبود
        try:
            import webbrowser
            import tempfile
            fd, path = tempfile.mkstemp(suffix='.html')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(html or '')
            webbrowser.open('file://' + path)
        except Exception:
            pass


    def _old_open_html_disabled(self, html: str) -> None:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            temp_file = f.name
        webbrowser.open('file:///' + temp_file)

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

    # --- ادامه متدهای کلاس (بدون تغییر در منطق، صرفاً برای تکمیل فایل) ---
    def _load_lookups(self) -> None:
        self.suppliers = self.repository.list_suppliers()
        self.drivers = self.repository.list_drivers()
        self.pallets = self.repository.list_pallets()
        self.warehouses = self.repository.list_warehouses()
        if hasattr(self, 'warehouse_combo'):
            self.warehouse_combo.blockSignals(True)
            self.warehouse_combo.clear()
            self.warehouse_combo.addItem('-- ابتدا انبار را انتخاب کنید --', None)
            for w in self.warehouses:
                self.warehouse_combo.addItem(f"{w['code']} | {w['name']}", w['id'])
            self.warehouse_combo.blockSignals(False)
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
        self._refresh_reference_combo()
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
            if not reference: return
            reference_no = reference['reference_no']
            stage_no = self.repository.peek_stage_no(selected_reference_id)
            document_no = self.repository.peek_document_no(reference_no, stage_no, personnel_id=self.supplier_combo.currentData())
            remaining = int(reference['remaining_qty'])
            self.reference_no_label.setText(reference_no)
            self.document_no_label.setText(document_no)
            self.stage_no_label.setText(str(stage_no))
            self.remaining_qty_label.setText(f'{remaining:,} عدد')
            self.total_declared_edit.setText(self._fmt_int(int(reference['total_load_qty'])))
            self.total_declared_edit.setEnabled(False and self.can_manage)
        else:
            reference_no = self.repository.peek_reference_no(iso_date)
            document_no = self.repository.peek_document_no(reference_no, 1, personnel_id=self.supplier_combo.currentData())
            self.reference_no_label.setText(reference_no)
            self.document_no_label.setText(document_no)
            self.stage_no_label.setText('1')
            self.remaining_qty_label.setText('مرجع جدید')
            self.total_declared_edit.setEnabled(self.can_manage)

    def _load_reference_pallet_ids(self, inbound_load_id) -> List[int]:
        ids: List[int] = []
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("SELECT pallet_id FROM inbound_load_items WHERE inbound_load_id=? ORDER BY row_no", (inbound_load_id,)).fetchall()
                ids = [r[0] for r in rows]
        except Exception as e:
            print('inbound_load_items query error:', str(e))
        if not ids:
            try:
                with self.db.connect() as conn:
                    conn.row_factory = None
                    rows = conn.execute("SELECT DISTINCT wri.pallet_id FROM warehouse_receipt_items wri JOIN warehouse_receipts wr ON wr.id = wri.receipt_id WHERE wr.inbound_load_id=?", (inbound_load_id,)).fetchall()
                    ids = [r[0] for r in rows]
            except Exception:
                pass
        return ids

    def _pallet_options(self, extra_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if self.allowed_pallet_ids is None:
            return self.pallets
        options = [p for p in self.pallets if p['id'] in self.allowed_pallet_ids]
        if extra_id and not any(p['id'] == extra_id for p in options):
            extra = next((p for p in self.pallets if p['id'] == extra_id), None)
            if extra: options.append(extra)
        return options if options else self.pallets

    def _reference_selection_changed(self) -> None:
        selected_reference_id = self.reference_selector_combo.currentData()
        if selected_reference_id:
            ids = self._load_reference_pallet_ids(selected_reference_id)
            self.allowed_pallet_ids = set(ids) if ids else None
            reference = next((row for row in self.open_references if row['id'] == selected_reference_id), None)
            
            if reference:
                # ✅ ست کردن خودکار مشتری
                customer_id = reference.get('customer_id')
                if customer_id:
                    self._select_combo_by_data(self.customer_combo, customer_id)
                
                # ادامه تنظیمات دیگر
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
                self._load_receipt_items(selected_reference_id)
        else:
            self.allowed_pallet_ids = None
            self.total_declared_edit.clear()
            self.stage_declared_edit.clear()
            self.stage_received_edit.clear()
            self.waybill_edit.clear()
            self.source_location_edit.clear()
            self.destination_location_edit.clear()
        
        self._refresh_pallet_combos()
        self._refresh_reference_numbers()
        self._driver_changed()
        self._on_quantity_changed()

    def _on_warehouse_changed(self) -> None:
        wid = self.warehouse_combo.currentData()
        if not wid:
            self.warehouse_msg_lbl.setText('⚠️ ابتدا انبار مقصد را انتخاب کنید.')
            self.warehouse_msg_lbl.show()
            return
        if self.lines_table.rowCount() > 0:
            if QMessageBox.question(self, 'تغییر انبار', 'با تغییر انبار، همه ردیف‌های فعلی پاک می‌شوند.\nادامه می‌دهید؟', QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                self.warehouse_combo.blockSignals(True)
                self.warehouse_combo.setCurrentIndex(0)
                self.warehouse_combo.blockSignals(False)
                return
            self.lines_table.setRowCount(0)
        self.warehouse_msg_lbl.hide()
        self.warehouse_combo.setEnabled(False)
        self.reference_selector_combo.setCurrentIndex(0)
        self._refresh_reference_combo()
        if self.lines_table.rowCount() == 0:
            self.add_line_row()
        self._refresh_pallet_combos()

    def _refresh_reference_combo(self):
        wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
        wh_map = {}
        try:
            with self.db.connect() as conn:
                for r in conn.execute("""SELECT wr.inbound_load_id, wri.warehouse_id FROM warehouse_receipts wr JOIN warehouse_receipt_items wri ON wri.receipt_id=wr.id WHERE COALESCE(wr.receipt_status,'CONFIRMED')<>'CANCELLED'"""):
                    wh_map.setdefault(r[0], set()).add(r[1])
        except Exception:
            pass
        self.reference_selector_combo.blockSignals(True)
        cur = self.reference_selector_combo.currentData()
        self.reference_selector_combo.clear()
        self.reference_selector_combo.addItem('مرجع جدید خودکار', None)
        for row in self.open_references:
            rws = wh_map.get(row['id'])
            if wid and rws and wid not in rws: continue
            remaining = int(row['remaining_qty'])
            self.reference_selector_combo.addItem(f"{row['reference_no']} | مانده: {remaining:,}", row['id'])
        if cur:
            idx = self.reference_selector_combo.findData(cur)
            if idx >= 0: self.reference_selector_combo.setCurrentIndex(idx)
        self.reference_selector_combo.blockSignals(False)

    def _load_pallet_prices(self) -> None:
        self.pallet_service = getattr(self, 'pallet_service', None) or PalletService(self.db)
        self.pallet_service.reload()
        self.avg_pallet_prices = self.pallet_service.prices_map()
        self.pallet_stock = self.pallet_service.stock_map()
        if hasattr(self, 'lines_table'):
            self._refresh_pallet_combos()

    def _avg_price_for_warehouse(self, pallet_id: int, warehouse_id: Optional[int]) -> int:
        if not warehouse_id: return int(self.avg_pallet_prices.get(pallet_id, 0) or 0)
        try:
            with self.db.connect() as conn:
                r = conn.execute("""SELECT COALESCE(SUM(qty_in*unit_price),0)/COALESCE(SUM(qty_in),0) FROM inventory_transactions WHERE pallet_id=? AND warehouse_id=? AND qty_in>0 AND unit_price>0 AND reference_type<>'TRANSFER'""", (pallet_id, warehouse_id)).fetchone()
                return int(r[0] or 0)
        except Exception:
            return int(self.avg_pallet_prices.get(pallet_id, 0) or 0)

    def _stock_for_warehouse(self, pallet_id: int, warehouse_id: Optional[int]) -> int:
        if not warehouse_id: return self.pallet_stock.get(pallet_id, 0)
        try:
            with self.db.connect() as conn:
                r = conn.execute("SELECT quantity FROM inventory_levels WHERE pallet_id=? AND warehouse_id=?", (pallet_id, warehouse_id)).fetchone()
                return int(free_stock(self.db, pallet_id) or 0)  # ONE-STOCK
        except Exception:
            return 0

    def _receipt_recalc_percent(self):
        try:
            pct_text = self.receipt_pct_edit.text().strip()
            if not pct_text:
                self.receipt_calc_val.setText('-')
                return
            digits = ''.join(ch for ch in pct_text if ch.isdigit())
            if not digits:
                self.receipt_calc_val.setText('-')
                return
            pct = float(digits)
            avg_text = self.avg_price_value.text().replace(' ریال', '').replace(',', '').strip()
            try: avg = int(float(avg_text))
            except Exception: avg = 0
            if avg <= 0:
                self.receipt_calc_val.setText('-')
                return
            calc = int(avg * (1 + pct / 100.0))
            self.receipt_calc_val.setText('{:,} ریال (+{}%)'.format(calc, int(pct)))
        except Exception:
            self.receipt_calc_val.setText('-')

    def _pallet_options_for_warehouse(self):
        wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
        result = []
        for p in self._pallet_options():
            s = self._stock_for_warehouse(p['id'], wid) if wid else self.pallet_stock.get(p['id'], 0)
            a = self._avg_price_for_warehouse(p['id'], wid) or int(self.avg_pallet_prices.get(p['id'], 0) or 0)
            result.append((p, s, a))
        return result

    def _refresh_pallet_combos(self) -> None:
        for row in range(self.lines_table.rowCount()):
            combo = self.lines_table.cellWidget(row, 1)
            if not isinstance(combo, QComboBox): continue
            current_id = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem('انتخاب پالت', None)
            for p, s, a in self._pallet_options_for_warehouse():
                txt = "{} | {} (مانده انبار: {:,})".format(p['code'], p['name'], s)
                if a > 0: txt += " | میانگین: {:,}".format(a)
                combo.addItem(txt, p['id'])
            if current_id:
                idx = combo.findData(current_id)
                combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

    def _on_receipt_pallet_changed(self, row: int) -> None:
        pallet_combo = self.lines_table.cellWidget(row, 1)
        if not isinstance(pallet_combo, QComboBox): return
        pallet_id = pallet_combo.currentData()
        # DUP-CHECK: جلوگیری از انتخاب پالت تکراری
        if pallet_id:
            for _r in range(self.lines_table.rowCount()):
                if _r == row: continue
                _other = self.lines_table.cellWidget(_r, 1)
                if isinstance(_other, QComboBox) and _other.currentData() == pallet_id:
                    QMessageBox.warning(self, 'خطا', 'این پالت قبلاً در ردیف دیگری انتخاب شده است.')
                    pallet_combo.blockSignals(True)
                    pallet_combo.setCurrentIndex(0)
                    pallet_combo.blockSignals(False)
                    return
        price_edit = self.lines_table.cellWidget(row, 3)
        if pallet_id:
            wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
            avg_price = self._avg_price_for_warehouse(pallet_id, wid) or int(self.avg_pallet_prices.get(pallet_id, 0) or 0)
            self.avg_price_value.setText(f"{avg_price:,} ریال")
            if hasattr(self, 'receipt_calc_val'): self._receipt_recalc_percent()
            if isinstance(price_edit, QLineEdit):
                price_edit.blockSignals(True)
                price_edit.setText(f"{int(avg_price):,}")
                price_edit.blockSignals(False)
        else:
            self.avg_price_value.setText('0 ریال')
        if hasattr(self, 'vat_checkbox'):
            self.vat_checkbox.setChecked(False)
            self.extra_checkbox.setChecked(False)
            self.extra_costs_edit.clear()
            self.extra_costs_edit.setEnabled(False)
            self.vat_amount_label.setText('۰ ریال')
            self.final_total_label.setText('قیمت نهایی: ۰ ریال')
        self.recalculate_lines()

    def _load_receipt_items(self, inbound_load_id):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                items = conn.execute(
                    "SELECT wri.pallet_id, p.code, p.name, wri.qty, wri.unit_price, wri.total_price, wri.warehouse_id, wri.defect_description "
                    "FROM warehouse_receipt_items wri JOIN pallets p ON p.id = wri.pallet_id JOIN warehouse_receipts wr ON wr.id = wri.receipt_id "
                    "WHERE wr.inbound_load_id = ? AND COALESCE(wr.receipt_status, 'CONFIRMED') <> 'CANCELLED' ORDER BY wr.stage_no, wri.row_no",
                    (inbound_load_id,)
                ).fetchall()
                if not items: return
                self.lines_table.setRowCount(0)
                for idx, item in enumerate(items):
                    row = self.lines_table.rowCount()
                    self.lines_table.insertRow(row)
                    no_item = QTableWidgetItem(str(idx + 1))
                    no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
                    no_item.setTextAlignment(Qt.AlignCenter)
                    self.lines_table.setItem(row, 0, no_item)
                    pallet_combo = QComboBox()
                    try: self.lines_table.setColumnWidth(1, 430)
                    except Exception: pass
                    pallet_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
                    pallet_combo.setMinimumContentsLength(6)
                    pallet_combo.addItem('انتخاب پالت', None)
                    for p in self._pallet_options(extra_id=item[0]):
                        pallet_combo.addItem(f"{p['code']} | {p['name']}", p['id'])
                        if p['id'] == item[0]: pallet_combo.setCurrentIndex(pallet_combo.count() - 1)
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
                        if w['id'] == item[6]: wh_combo.setCurrentIndex(wh_combo.count() - 1)
                    wh_combo.currentIndexChanged.connect(self.recalculate_lines)
                    defect_edit = QLineEdit(item[7] or '')
                    self.lines_table.setCellWidget(row, 5, defect_edit)  # LOAD-FIX
                    self._on_receipt_pallet_changed(row)
                self._refresh_pallet_combos()
                self.recalculate_lines()
        except Exception as e:
            print('Load receipt items error:', str(e))

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
        no_item = QTableWidgetItem(str(row + 1))
        no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
        no_item.setTextAlignment(Qt.AlignCenter)
        self.lines_table.setItem(row, 0, no_item)
        pallet_combo = QComboBox()
        try: self.lines_table.setColumnWidth(1, 430)
        except Exception: pass
        pallet_combo.addItem('انتخاب پالت', None)
        for item, s, a in self._pallet_options_for_warehouse():
            txt = "{} | {} (مانده انبار: {:,})".format(item['code'], item['name'], s)
            if a > 0: txt += " | میانگین: {:,}".format(a)
            pallet_combo.addItem(txt, item['id'])
        _handler = lambda _idx, r=row: self._on_receipt_pallet_changed(r)
        pallet_combo.currentIndexChanged.connect(_handler)
        pallet_combo.activated.connect(_handler)
        qty_spin = QSpinBox()
        qty_spin.setRange(0, 1000000000)
        qty_spin.valueChanged.connect(self.recalculate_lines)
        unit_price_edit = QLineEdit()
        unit_price_edit.textChanged.connect(lambda: self._handle_price_edit_change(unit_price_edit))
        line_total_item = QTableWidgetItem('0')
        line_total_item.setFlags(line_total_item.flags() & ~Qt.ItemIsEditable)
        line_total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        defect_edit = QLineEdit()
        defect_edit.setPlaceholderText('عیب یا توضیح ردیف')
        self.lines_table.setCellWidget(row, 1, pallet_combo)
        self.lines_table.setCellWidget(row, 2, qty_spin)
        self.lines_table.setCellWidget(row, 3, unit_price_edit)
        self.lines_table.setItem(row, 4, line_total_item)
        self.lines_table.setCellWidget(row, 5, defect_edit)
        self.recalculate_lines()

    def remove_selected_line(self) -> None:
        row = self.lines_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'ردیف‌ها', 'ابتدا یک ردیف را انتخاب کنید.')
            return
        self.lines_table.removeRow(row)
        for index in range(self.lines_table.rowCount()):
            item = self.lines_table.item(index, 0)
            if item: item.setText(str(index + 1))
        if self.lines_table.rowCount() == 0: self.add_line_row()
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

    def _lines_subtotal(self) -> int:
        total = 0
        for row in range(self.lines_table.rowCount()):
            qty_widget = self.lines_table.cellWidget(row, 2)
            price_widget = self.lines_table.cellWidget(row, 3)
            qty = qty_widget.value() if isinstance(qty_widget, QSpinBox) else 0
            unit_price = self._int_from_text(price_widget.text()) if isinstance(price_widget, QLineEdit) else 0
            total += qty * unit_price
        return total

    def _current_vat_amount(self) -> int:
        if not self.vat_checkbox.isChecked(): return 0
        return int(self._lines_subtotal() * 9 / 100)

    def _current_extra_costs(self) -> int:
        if not self.extra_checkbox.isChecked(): return 0
        return self._int_from_text(self.extra_costs_edit.text())

    def _recalc_final_total(self):
        subtotal = self._lines_subtotal()
        vat = self._current_vat_amount()
        extra = self._current_extra_costs()
        self.vat_amount_label.setText('{} ریال'.format(self._fmt_int(vat)))
        final = subtotal + vat + extra
        self.final_total_label.setText('قیمت نهایی: {} ریال'.format(self._fmt_int(final)))

    def _on_extra_toggled(self):
        self.extra_costs_edit.setEnabled(self.extra_checkbox.isChecked())
        if self.extra_checkbox.isChecked(): self.extra_costs_edit.setFocus()
        self._recalc_final_total()

    def _format_extra_costs_edit(self):
        edit = self.extra_costs_edit
        digits = ''.join(ch for ch in edit.text() if ch.isdigit())
        edit.blockSignals(True)
        edit.setText(self._fmt_int(int(digits)) if digits else '')
        edit.blockSignals(False)
        self._recalc_final_total()

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
            if item: item.setText(self._fmt_int(line_total))
        self.lines_total_label.setText(f'جمع ریالی ردیف‌ها: {self._fmt_int(grand_total)} ریال')
        if not self.stage_received_edit.hasFocus() and grand_qty > 0:
            self.stage_received_edit.setText(self._fmt_int(grand_qty))
        self._on_quantity_changed()
        if hasattr(self, 'vat_checkbox'): self._recalc_final_total()

    def _collect_lines(self) -> List[Dict[str, Any]]:
        lines: List[Dict[str, Any]] = []
        wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
        for row in range(self.lines_table.rowCount()):
            pallet_widget = self.lines_table.cellWidget(row, 1)
            qty_widget = self.lines_table.cellWidget(row, 2)
            price_widget = self.lines_table.cellWidget(row, 3)
            defect_widget = self.lines_table.cellWidget(row, 5)
            lines.append({
                'pallet_id': pallet_widget.currentData() if isinstance(pallet_widget, QComboBox) else None,
                'quantity': qty_widget.value() if isinstance(qty_widget, QSpinBox) else 0,
                'unit_price': price_widget.text() if isinstance(price_widget, QLineEdit) else '0',
                'warehouse_id': wid,
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
            'vat_enabled': self.vat_checkbox.isChecked() if hasattr(self, 'vat_checkbox') else False,
            'vat_amount': self._current_vat_amount() if hasattr(self, 'vat_checkbox') else 0,
            'extra_costs': self._current_extra_costs() if hasattr(self, 'vat_checkbox') else 0,
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
                'total_amount': line.get('line_total_amount', 0),
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
            'vat_amount': self._current_vat_amount() if hasattr(self, 'vat_checkbox') else 0,
            'extra_costs': self._current_extra_costs() if hasattr(self, 'vat_checkbox') else 0,
            'final_total': (total_amount + (self._current_vat_amount() if hasattr(self, 'vat_checkbox') else 0) + (self._current_extra_costs() if hasattr(self, 'vat_checkbox') else 0)),
            'warehouse_keeper_name': data['warehouse_keeper_name'] or '-',
            'receiver_name': data['receiver_name'] or '-',
            'notes': data['notes'] or '-',
            'lines': lines,
        }

    def _inject_letterhead(self, html: str) -> str:
        return html

    def _stored_print_html(self, inbound_load_id) -> Optional[str]:
        try:
            with self.db.connect() as conn:
                row = conn.execute("SELECT print_html FROM warehouse_receipts WHERE inbound_load_id=? ORDER BY stage_no DESC LIMIT 1", (inbound_load_id,)).fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def _show_remaining_receipts(self) -> None:  # BTN-FINAL
        try:
            with self.db.connect() as conn:
                rows = conn.execute(
                    "SELECT il.reference_no, il.total_load_qty, il.remaining_qty, "
                    "COALESCE(p.first_name||' '||p.last_name,'') FROM inbound_loads il "
                    "LEFT JOIN persons p ON p.id=il.supplier_id "
                    "WHERE il.remaining_qty>0 ORDER BY il.id DESC").fetchall()
        except Exception as e:
            QMessageBox.warning(self, 'خطا', str(e))
            return
        if not rows:
            QMessageBox.information(self, 'رسیدهای مانده', 'مورد مانده‌ای وجود ندارد')
            return
        txt = '\n'.join('%s | کل: %s | مانده: %s | %s' % (r[0], r[1], r[2], r[3]) for r in rows)
        QMessageBox.information(self, 'رسیدهای مانده', txt)

    def _ctx_from_details(self, details):  # PREVIEW-GOOD
        from app.core.jalali import jalali_date_display_from_iso as _j
        stages = details.get('stages', []) or []
        last = stages[-1] if stages else {}
        items = details.get('items', []) or []
        lines = []
        for idx, it in enumerate(items, 1):
            lines.append({'row_no': idx, 'pallet_code': it.get('pallet_code', ''), 'pallet_name': it.get('pallet_name', ''),
                          'quantity': it.get('quantity', 0), 'unit_price': it.get('unit_price', 0),
                          'total_amount': it.get('total_amount', 0), 'warehouse_name': it.get('warehouse_name', ''),
                          'defect_description': it.get('defect_description', '')})
        _d = last.get('receipt_date', '') or ''
        return {
            'reference_no': details.get('reference_no', ''), 'receipt_no': last.get('receipt_no', ''),
            'stage_no': last.get('stage_no', 1) or 1, 'operation_date': _d,
            'operation_date_jalali': _j(_d) if _d else '',
            'waybill_no': details.get('waybill_no', ''), 'supplier_name': details.get('supplier_name', ''),
            'driver_name': details.get('driver_name', ''), 'vehicle_type': details.get('vehicle_type', ''),
            'vehicle_plate': details.get('vehicle_plate', ''), 'source_location': details.get('source_location', ''),
            'destination_location': details.get('destination_location', ''),
            'stage_load_qty': details.get('total_qty', 0) or last.get('stage_load_qty', 0),
            'delivered_qty': last.get('delivered_qty', 0) or last.get('quantity', 0),
            'discrepancy_qty': last.get('discrepancy_qty', 0), 'freight_amount': last.get('freight_amount', 0),
            'lines': lines, 'lines_total_amount': sum(int(it.get('total_amount', 0) or 0) for it in items),
            'vat_amount': details.get('vat_amount', 0), 'extra_costs': last.get('extra_costs', 0),
            'notes': details.get('notes', ''),
        }

    def preview_selected_saved_receipt(self) -> None:  # NATIVE-DETAILS
        if not self.warehouse_combo.currentData():
            QMessageBox.warning(self, 'هشدار', 'ابتدا انبار مقصد را انتخاب کنید.')
            return
        row = self.receipts_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'جزئیات', 'ابتدا یک رسید را از جدول انتخاب کنید.')
            return
        item = self.receipts_table.item(row, 0)
        if not item:
            return
        inbound_load_id = int(item.text())
        try:
            details = self.repository.get_completed_receipt_details(inbound_load_id)
            if not details:
                QMessageBox.warning(self, 'خطا', 'اطلاعات رسید یافت نشد.')
                return
            with self.db.connect() as conn:
                conn.row_factory = None
                r = conn.execute(
                    "SELECT wr.receipt_no, wr.receipt_date, wr.receipt_status "
                    "FROM warehouse_receipts wr WHERE wr.inbound_load_id=? "
                    "ORDER BY wr.stage_no DESC LIMIT 1", (inbound_load_id,)).fetchone()
            receipt_no = r[0] if r else '-'
            receipt_date = jalali_date_display_from_iso(r[1]) if (r and r[1]) else '-'
            receipt_status = r[2] if r else 'CONFIRMED'
            items = details.get('items', [])
            total_amount = sum(int(it.get('total_amount', 0) or 0) for it in items)
            total_qty = sum(int(it.get('quantity', 0) or 0) for it in items)

            dialog = QDialog(self)
            dialog.setWindowTitle('جزئیات: {}'.format(details.get('reference_no', '-')))
            dialog.resize(950, 620)
            dialog.setLayoutDirection(Qt.RightToLeft)
            dlg_layout = QVBoxLayout(dialog)
            info_group = QGroupBox('اطلاعات')
            info_layout = QGridLayout(info_group)
            info_layout.addWidget(QLabel('شماره رسید:'), 0, 0)
            info_layout.addWidget(QLabel(str(receipt_no)), 0, 1)
            info_layout.addWidget(QLabel('تاریخ:'), 0, 2)
            info_layout.addWidget(QLabel(str(receipt_date)), 0, 3)
            info_layout.addWidget(QLabel('مرجع بار:'), 1, 0)
            info_layout.addWidget(QLabel(str(details.get('reference_no', '-'))), 1, 1)
            info_layout.addWidget(QLabel('تأمین‌کننده:'), 1, 2)
            info_layout.addWidget(QLabel(str(details.get('supplier_name', '-'))), 1, 3)
            info_layout.addWidget(QLabel('راننده:'), 2, 0)
            info_layout.addWidget(QLabel(str(details.get('driver_name', '-'))), 2, 1)
            info_layout.addWidget(QLabel('وضعیت:'), 2, 2)
            info_layout.addWidget(QLabel(str(receipt_status)), 2, 3)
            info_layout.addWidget(QLabel('تعداد کل:'), 3, 0)
            info_layout.addWidget(QLabel('{:,}'.format(total_qty)), 3, 1)
            info_layout.addWidget(QLabel('مبلغ کل:'), 3, 2)
            info_layout.addWidget(QLabel('{:,} ریال'.format(total_amount)), 3, 3)
            dlg_layout.addWidget(info_group)
            items_table = QTableWidget(0, 7)
            items_table.setHorizontalHeaderLabels(['ردیف', 'کد پالت', 'نام پالت', 'تعداد', 'قیمت واحد', 'مبلغ کل', 'انبار'])
            items_table.verticalHeader().setVisible(False)
            items_table.setRowCount(len(items))
            for idx, it in enumerate(items):
                vals = [str(it.get('row_no', idx + 1)), it.get('pallet_code', '-'), it.get('pallet_name', '-'),
                        '{:,}'.format(int(it.get('quantity', 0) or 0)),
                        '{:,}'.format(int(it.get('unit_price', 0) or 0)),
                        '{:,}'.format(int(it.get('total_amount', 0) or 0)),
                        it.get('warehouse_name', '-')]
                for col, v in enumerate(vals):
                    cell = QTableWidgetItem(str(v))
                    cell.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    items_table.setItem(idx, col, cell)
            items_table.resizeColumnsToContents()
            dlg_layout.addWidget(items_table)
            # جدول مراحل (زیرشاخه‌ها)  # STAGES-TABLE
            stages = details.get('stages', []) or []
            if stages:
                st_group = QGroupBox('مراحل / رسیدهای این بار')
                st_layout = QVBoxLayout(st_group)
                st_table = QTableWidget(0, 5)
                st_table.setHorizontalHeaderLabels(['مرحله', 'شماره رسید', 'تاریخ', 'تعداد تحویل', 'وضعیت'])
                st_table.verticalHeader().setVisible(False)
                st_table.setRowCount(len(stages))
                for si, st in enumerate(stages):
                    sv = [str(st.get('stage_no', si + 1)), str(st.get('receipt_no', '-')),
                          jalali_date_display_from_iso(st.get('receipt_date')) if st.get('receipt_date') else '-',
                          '{:,}'.format(int(st.get('delivered_qty', st.get('quantity', st.get('total_qty', 0))) or 0)),
                          str(st.get('receipt_status', 'CONFIRMED'))]
                    for col, v in enumerate(sv):
                        cell = QTableWidgetItem(str(v))
                        cell.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                        st_table.setItem(si, col, cell)
                st_table.resizeColumnsToContents()
                st_layout.addWidget(st_table)
                dlg_layout.addWidget(st_group)
            close_btn = QPushButton('بستن')
            close_btn.clicked.connect(dialog.accept)
            dlg_layout.addWidget(close_btn)
            html = self.repository.render_receipt_html(self._ctx_from_details(details))
            self._open_html_in_browser(self._inject_letterhead(html))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا در جزئیات', str(exc))

    def print_selected_completed_receipt(self) -> None:
        row = self.completed_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'پرینت', 'ابتدا یک حواله از جدول انتخاب کنید.')
            return
        item = self.completed_table.item(row, 0)
        if not item: return
        inbound_load_id = int(item.text())
        html = self._stored_print_html(inbound_load_id)
        if not html:
            details = self.repository.get_completed_receipt_details(inbound_load_id)
            html = self.repository.render_receipt_html(self._ctx_from_details(details)) if details else None
        if html:
            self._open_html_in_browser(self._inject_letterhead(html))

    def save_receipt(self) -> None:
        self._ac_save_all()
        # DUP-CHECK: چک تکراری پالت قبل از ذخیره
        _lines_for_check = self._collect_lines()
        _seen_pids = set()
        for _ln in _lines_for_check:
            _pid = _ln.get('pallet_id')
            if _pid in _seen_pids:
                QMessageBox.warning(self, 'خطا', 'یک پالت در دو ردیف ثبت شده است؛ هر پالت فقط یک ردیف.')
                return
            if _pid:
                _seen_pids.add(_pid)
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه ثبت رسید را ندارید.')
            return
        if hasattr(self, 'warehouse_combo') and not self.warehouse_combo.currentData():
            QMessageBox.warning(self, 'خطا', 'ابتدا انبار مقصد را انتخاب کنید.')
            return
        try:
            saved = self.repository.create_inbound_receipt(self._collect_payload(), user_id=self.user_data.get('id'))
        except ValidationError as exc:
            QMessageBox.warning(self, 'ثبت رسید', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'ثبت رسید با خطا مواجه شد:\n{exc}')
            return
        QMessageBox.information(self, 'رسید ثبت شد', f"رسید با موفقیت ثبت و تایید شد.\nشماره مرجع: {saved.get('reference_no')}\nشماره رسید: {saved.get('receipt_no')}")
        try:
            from app.core.doc_upload_helper import open_upload_after_save
            open_upload_after_save(self, 'RECEIPT', saved, self.db, self.user_data)
        except Exception as _img_exc:
            print('[doc-images] upload error:', _img_exc)
        self._load_lookups()
        self.refresh_receipts_final()
        self.clear_form()
        self.data_changed.emit()
        try:
            html = saved.get('print_html')
            if not html and saved.get('id'):
                with self.db.connect() as conn:
                    r = conn.execute("SELECT print_html FROM warehouse_receipts WHERE id=?", (saved['id'],)).fetchone()
                html = r[0] if r else None
            if html:
                self._open_html_in_browser(self._inject_letterhead(html))
        except Exception:
            pass

    def preview_current_receipt(self) -> None:
        selected_reference_id = self.reference_selector_combo.currentData()
        
        # ✅ چک انتخاب تأمین‌کننده برای پیش‌نمایش (اختیاری برای پیش‌نمایش، اجباری برای ثبت)
        if not self.supplier_combo.currentData():
            reply = QMessageBox.question(
                self, 'تأمین‌کننده', 
                'تأمین‌کننده انتخاب نشده است.\nآیا می‌خواهید با تأمین‌کننده "نامشخص" پیش‌نمایش بگیرید؟',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            # موقتاً مقدار پیش‌فرض برای پیش‌نمایش
            temp_supplier_id = None
        else:
            temp_supplier_id = self.supplier_combo.currentData()
        
        if not selected_reference_id:
            try:
                # ساخت payload بدون validate سخت‌گیرانه برای پیش‌نمایش
                payload = self._collect_payload()
                # اصلاح موقت supplier_id برای پیش‌نمایش
                if not payload.get('supplier_person_id'):
                    payload['supplier_person_id'] = None
                    
                ctx = {
                    'reference_no': self.reference_no_label.text(),
                    'receipt_no': self.document_no_label.text(),
                    'stage_no': int(self.stage_no_label.text() or '1'),
                    'operation_date_iso': self._current_iso_date(),
                    'operation_date_jalali': jalali_date_display_from_iso(self._current_iso_date()),
                    'waybill_no': payload.get('waybill_no') or '-',
                    'supplier_name': self.supplier_combo.currentText() or 'نامشخص',
                    'driver_name': self.driver_combo.currentText().split('|')[0].strip() or '-',
                    'vehicle_type': self.vehicle_label.text().split('|')[0].strip() if '|' in self.vehicle_label.text() else self.vehicle_label.text(),
                    'vehicle_plate': self.vehicle_label.text().split('|')[1].strip() if '|' in self.vehicle_label.text() else '-',
                    'source_location': payload.get('source_location') or '-',
                    'destination_location': payload.get('destination_location') or '-',
                    'total_declared_qty': self._int_from_text(payload.get('total_declared_qty', '0')),
                    'stage_load_qty': self._int_from_text(payload.get('stage_declared_qty', '0')),
                    'delivered_qty': self._int_from_text(payload.get('stage_received_qty', '0')),
                    'discrepancy_qty': max(self._int_from_text(payload.get('stage_declared_qty', '0')) - self._int_from_text(payload.get('stage_received_qty', '0')), 0),
                    'freight_amount': self._int_from_text(payload.get('freight_amount', '0')),
                    'lines_total_amount': self._lines_subtotal(),
                    'vat_amount': self._current_vat_amount() if hasattr(self, 'vat_checkbox') else 0,
                    'extra_costs': self._current_extra_costs() if hasattr(self, 'vat_checkbox') else 0,
                    'final_total': self._lines_subtotal() + self._current_vat_amount() + self._current_extra_costs(),
                    'warehouse_keeper_name': payload.get('warehouse_keeper_name') or '-',
                    'receiver_name': payload.get('receiver_name') or '-',
                    'notes': payload.get('notes') or '-',
                    'lines': []
                }
                
                # ساخت ردیف‌های جدول برای پیش‌نمایش
                for idx in range(self.lines_table.rowCount()):
                    pallet_widget = self.lines_table.cellWidget(idx, 1)
                    qty_widget = self.lines_table.cellWidget(idx, 2)
                    price_widget = self.lines_table.cellWidget(idx, 3)
                    defect_widget = self.lines_table.cellWidget(idx, 5)
                    
                    pallet_text = pallet_widget.currentText() if isinstance(pallet_widget, QComboBox) else '-'
                    ctx['lines'].append({
                        'row_no': idx + 1,
                        'pallet_code': pallet_text.split('|')[0].strip() if '|' in pallet_text else pallet_text,
                        'pallet_name': pallet_text.split('|', 1)[1].strip() if '|' in pallet_text else pallet_text,
                        'quantity': qty_widget.value() if isinstance(qty_widget, QSpinBox) else 0,
                        'unit_price': self._int_from_text(price_widget.text()) if isinstance(price_widget, QLineEdit) else 0,
                        'total_amount': (qty_widget.value() if isinstance(qty_widget, QSpinBox) else 0) * (self._int_from_text(price_widget.text()) if isinstance(price_widget, QLineEdit) else 0),
                        'warehouse_name': '-',
                        'defect_description': defect_widget.text() if isinstance(defect_widget, QLineEdit) else ''
                    })
                    
            except Exception as exc:
                QMessageBox.warning(self, 'پیش‌نمایش', f'برای پیش‌نمایش، اطلاعات را کامل کنید:\n{exc}')
                return
                
            # ساخت HTML ساده برای پیش‌نمایش
            rows_html = ''.join(
                f"<tr><td>{l['row_no']}</td><td>{l['pallet_code']}</td><td>{l['pallet_name']}</td>"
                f"<td>{l['quantity']:,}</td><td>{l['unit_price']:,}</td><td>{l['total_amount']:,}</td></tr>" 
                for l in ctx['lines']
            )
            
            html = f"""<html dir='rtl'><head><meta charset='utf-8'><style>
                body{{font-family:Tahoma,sans-serif;padding:20px;background:#fff}}
                table{{width:100%;border-collapse:collapse;margin-top:15px}}
                th{{background:#46505f;color:#fff;padding:10px 8px;text-align:center;font-size:13px}}
                td{{border:1px solid #e2e8f0;padding:8px;text-align:center;font-size:12px}}
                .header{{border-bottom:2px solid #2563eb;padding-bottom:15px;margin-bottom:20px}}
                .total{{background:#dbeafe;font-weight:bold;font-size:14px}}
            </style></head><body>
            <div class="header">
                <h2>پیش‌نمایش رسید (پیش‌نویس)</h2>
                <p><b>مرجع:</b> {ctx['reference_no']} | <b>رسید:</b> {ctx['receipt_no']} | <b>تاریخ:</b> {ctx['operation_date_jalali']}</p>
                <p><b>تأمین‌کننده:</b> {ctx['supplier_name']} | <b>راننده:</b> {ctx['driver_name']} | <b>خودرو:</b> {ctx['vehicle_plate']}</p>
            </div>
            <table>
                <thead><tr><th>ردیف</th><th>کد پالت</th><th>نام پالت</th><th>تعداد</th><th>قیمت واحد</th><th>مبلغ کل</th></tr></thead>
                <tbody>{rows_html}
                <tr class="total"><td colspan="5" style="text-align:left;padding:10px;">جمع کل:</td><td style="padding:10px;">{ctx['lines_total_amount']:,} ریال</td></tr>
                </tbody>
            </table>
            <p style="margin-top:15px;font-weight:bold">قیمت نهایی: {ctx['final_total']:,} ریال</p>
            </body></html>"""
            
            self._open_html_in_browser(html)
            return
            
        # اگر مرجع انتخاب شده باشد، از دیتابیس خوانده شود
        try:
            details = self.repository.get_completed_receipt_details(selected_reference_id)
            if not details:
                QMessageBox.warning(self, 'پیش‌نمایش', 'حواله یافت نشد.')
                return
            self._open_html_in_browser(self.repository.render_completed_receipt_html(details))
        except Exception as exc:
            QMessageBox.critical(self, 'خطا در پیش‌نمایش', f'خطا: {exc}')

    def refresh_receipts_final(self) -> None:  # RECEIPT-TREE-UI
        from app.core.jalali import jalali_date_display_from_iso as _j
        rows = self.repository.list_receipt_tree()
        tbl = self.receipts_table
        tbl.setColumnCount(11)
        tbl.setHorizontalHeaderLabels(
            ['شناسه', 'شماره رسید', 'مرجع مادر', 'انبار', 'تاریخ', 'تأمین‌کننده', 'راننده',
             'کل بار', 'تحویل', 'مانده', 'وضعیت'])
        tbl.setColumnHidden(0, True)
        tbl.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tbl.setRowCount(0)
        current_load = None
        for r in rows:
            if r['load_id'] != current_load:
                current_load = r['load_id']
                remaining = max(r['mother_total'] - r['mother_drawn'], 0)
                m_values = ['', '▶ ' + (r['mother_no'] or '-'), r['mother_no'] or '-', '-', '-', '-', '-',
                            '{:,}'.format(r['mother_total']), '{:,}'.format(r['mother_drawn']),
                            '{:,}'.format(remaining), 'بار مادر']
                pr = tbl.rowCount()
                tbl.insertRow(pr)
                for c, v in enumerate(m_values):
                    it = QTableWidgetItem(str(v))
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    f = it.font(); f.setBold(True); it.setFont(f)
                    it.setForeground(QColor('#ef4444'))
                    tbl.setItem(pr, c, it)
            if not r['receipt_id']:
                continue
            status = r['receipt_status'] or 'CONFIRMED'
            status_text = 'باطل' if status == 'CANCELLED' else 'تایید شده'
            c_values = [str(r['load_id']), r['receipt_no'] or '-', r['mother_no'] or '-',
                        r['warehouses'] or '-', _j(r['receipt_date']) if r['receipt_date'] else '-',
                        r['supplier'] or '-', r['driver'] or '-', '',
                        '{:,}'.format(r['receipt_qty']), '', status_text]
            cr = tbl.rowCount()
            tbl.insertRow(cr)
            for c, v in enumerate(c_values):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                tbl.setItem(cr, c, it)
        tbl.resizeColumnsToContents()

    def refresh_recent_receipts(self) -> None:
        rows = self.repository.list_recent_receipts()
        wh_map = {}
        try:
            with self.db.connect() as conn:
                for r in conn.execute("""SELECT wr.inbound_load_id, GROUP_CONCAT(DISTINCT w.name) AS wn FROM warehouse_receipts wr JOIN warehouse_receipt_items wri ON wri.receipt_id=wr.id LEFT JOIN warehouses w ON w.id=wri.warehouse_id GROUP BY wr.inbound_load_id"""):
                    wh_map[r[0]] = r[1] or '-'
        except Exception:
            pass
        date_map = {}
        try:
            with self.db.connect() as conn:
                for rr in conn.execute("SELECT id, register_date FROM inbound_loads"):
                    date_map[rr[0]] = rr[1]
        except Exception:
            pass
        self.receipts_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            total_load = row.get('total_load_qty', 0) or 0
            delivered = row.get('delivered_qty', 0) or 0
            remaining = row.get('remaining_qty', 0) or 0
            values = [
                str(row['id']), row['reference_no'], row.get('supplier_name') or '-', row.get('driver_name') or '-',
                self._fmt_int(int(total_load)), self._fmt_int(int(delivered)), self._fmt_int(int(remaining)),
                jalali_date_display_from_iso(date_map[row['id']]) if date_map.get(row['id']) else '-',
                wh_map.get(row['id'], '-'),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.receipts_table.setItem(row_index, column_index, item)
        self.receipts_table.resizeColumnsToContents()

    def rollback_selected_receipt(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه ابطال حواله را ندارید.')
            return
        row = self.receipts_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'ابطال حواله', 'ابتدا یک حواله را از جدول انتخاب کنید.')
            return
        item = self.receipts_table.item(row, 0)
        if not item: return
        inbound_load_id = int(item.text())
        try:
            details = self.repository.get_completed_receipt_details(inbound_load_id)
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'دریافت اطلاعات حواله با خطا مواجه شد:\n{exc}')
            return
        if not details:
            QMessageBox.warning(self, 'خطا', 'حواله یافت نشد.')
            return
        active_stages = [s for s in details.get('stages', []) if s.get('receipt_status') != 'CANCELLED']
        if not active_stages:
            QMessageBox.warning(self, 'خطا', 'این حواله قبلاً ابطال شده است.')
            return
        rollback_items = []
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                lines = conn.execute(
                    """SELECT wri.row_no, wri.pallet_id, wri.qty, wri.unit_price, wri.total_price, wri.warehouse_id,
                           p.code as pallet_code, p.name as pallet_name, w.name as warehouse_name,
                           COALESCE((SELECT SUM(q) FROM (SELECT o.qty AS q FROM opening_inventory_items o WHERE o.pallet_id = wri.pallet_id
                           UNION ALL SELECT CASE WHEN t.transaction_type='IN' THEN t.qty_in ELSE -t.qty_out END FROM inventory_transactions t
                           WHERE t.pallet_id = wri.pallet_id AND t.warehouse_id = wri.warehouse_id AND COALESCE(t.is_void, 0) = 0)), 0) as current_qty
                    FROM warehouse_receipt_items wri JOIN warehouse_receipts wr ON wr.id = wri.receipt_id
                    JOIN pallets p ON p.id = wri.pallet_id LEFT JOIN warehouses w ON w.id = wri.warehouse_id
                    WHERE wr.inbound_load_id = ? AND COALESCE(wr.receipt_status, 'CONFIRMED') <> 'CANCELLED' ORDER BY wr.stage_no, wri.row_no""",
                    (inbound_load_id,)
                ).fetchall()
                for line in lines:
                    current_qty = int(line[9] or 0)
                    rollback_qty = int(line[2])
                    after_qty = current_qty - rollback_qty
                    if after_qty < 0:
                        raise ValidationError(f'موجودی پالت «{line[7]}» در انبار «{line[8] or "-"}» کافی نیست.\nموجودی فعلی: {current_qty:,} | نیاز ابطال: {rollback_qty:,}')
                    rollback_items.append({
                        'row_no': line[0], 'pallet_code': line[6], 'pallet_name': line[7],
                        'warehouse_name': line[8] or '-', 'rollback_qty': rollback_qty,
                        'current_qty': current_qty, 'after_qty': after_qty,
                    })
        except ValidationError as exc:
            QMessageBox.warning(self, 'ابطال ممکن نیست', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا در بررسی موجودی:\n{exc}')
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f'پیش‌نمایش ابطال حواله {details.get("reference_no", "-")}')
        dialog.resize(900, 600)
        dialog.setLayoutDirection(Qt.RightToLeft)
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
        impact_table.setHorizontalHeaderLabels(['ردیف', 'کد پالت', 'نام پالت', 'انبار', 'موجودی فعلی', 'کاهش', 'موجودی پس از ابطال'])
        impact_table.verticalHeader().setVisible(False)
        impact_table.setRowCount(len(rollback_items))
        for idx, it in enumerate(rollback_items):
            vals = [str(it['row_no']), it['pallet_code'], it['pallet_name'], it['warehouse_name'], f"{it['current_qty']:,}", f"-{it['rollback_qty']:,}", f"{it['after_qty']:,}"]
            for col, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                cell.setBackground(QColor('#dbeafe'))
                if col == 5:
                    cell.setForeground(QColor('#ef4444'))
                elif col == 6:
                    cell.setForeground(QColor('#f59e0b') if it['after_qty'] == 0 else QColor('#10b981'))
                impact_table.setItem(idx, col, cell)
        impact_table.resizeColumnsToContents()
        impact_layout.addWidget(impact_table)
        layout.addWidget(impact_group)
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton('انصراف')
        cancel_btn.setObjectName('SecondaryButton')
        cancel_btn.clicked.connect(dialog.reject)
        confirm_btn = QPushButton('تأیید و ابطال')
        confirm_btn.setObjectName('DangerButton')
        confirm_btn.clicked.connect(dialog.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            result = self.repository.rollback_inbound_load(inbound_load_id, user_id=self.user_data.get('id'))
        except ValidationError as exc:
            QMessageBox.warning(self, 'ابطال حواله', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'ابطال حواله با خطا مواجه شد:\n{exc}')
            return
        report_dialog = QDialog(self)
        report_dialog.setWindowTitle('گزارش ابطال حواله')
        report_dialog.resize(700, 450)
        report_dialog.setLayoutDirection(Qt.RightToLeft)
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
            summary_text += f"  • {it['pallet_code']} ({it['pallet_name']}) در {it['warehouse_name']}: {it['current_qty']:,} → {it['after_qty']:,} ({it['rollback_qty']:,}-)\n"
        summary_lbl = QLabel(summary_text)
        summary_lbl.setWordWrap(True)
        summary_lbl.setStyleSheet('')
        r_layout.addWidget(summary_lbl)
        note_lbl = QLabel('⚠ اسناد مالی مرتبط نیز ابطال شدند.')
        note_lbl.setStyleSheet('color: #f59e0b; font-size: 12px;')
        r_layout.addWidget(note_lbl)
        close_btn = QPushButton('بستن')
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(report_dialog.accept)
        r_layout.addWidget(close_btn)
        report_dialog.exec_()
        self._load_lookups()
        self.refresh_receipts_final()
        self.data_changed.emit()

    def open_cancelled_archive(self) -> None:
        try:
            from app.ui.cancelled_receipts_window import CancelledReceiptsWindow
            window = CancelledReceiptsWindow(self.db, self.user_data, self)
            window.exec_()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در باز کردن بایگانی:\n{e}')

    def refresh_completed_receipts(self) -> None:
        rows = self.repository.list_completed_receipts()
        self.completed_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row['id']), row['reference_no'], row.get('supplier_name') or '-', row.get('driver_name') or '-',
                self._fmt_int(int(row.get('total_load_qty') or 0)), self._fmt_int(int(row.get('total_received') or 0)),
                self._fmt_int(int(row.get('remaining_qty') or 0)), self._fmt_int(int(row.get('total_amount') or 0)) + ' ریال',
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.completed_table.setItem(row_index, column_index, item)
        self.completed_table.resizeColumnsToContents()

    def clear_form(self) -> None:
        self.allowed_pallet_ids = None
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
        if hasattr(self, 'receipt_pct_edit'):
            self.receipt_pct_edit.setText('0')
        if hasattr(self, 'receipt_calc_val'):
            self.receipt_calc_val.setText('-')
        if hasattr(self, 'warehouse_combo'):
            self.warehouse_combo.setEnabled(True)
            self.warehouse_combo.setCurrentIndex(0)
            self.warehouse_msg_lbl.show()
        self.add_line_row()
        self._load_lookups()
        self._refresh_reference_numbers()
        self._on_quantity_changed()