# -*- coding: utf-8 -*-
"""Proforma Invoice Window - پیش فاکتور (نسخه تمیز و اصلاح‌شده)"""
import tempfile
import webbrowser
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
    QTableWidget, QTableWidgetItem, QDateEdit, QTextBrowser,
    QFileDialog, QHeaderView, QCheckBox
)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_display_from_iso, today_iso_date
from app.core.sequence_utils import next_sequence_no
from app.core.numbering_service import NumberingService
from app.ui.pallet_items_table import PalletItemsTable
from app.ui.html_preview_dialog import HtmlPreviewDialog
from app.core.stock_service import free_stock_map  # ONE-STOCK


class ProformaInvoiceWindow(QDialog):
    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, '_shown_once', False):
            self._shown_once = True
            self.resize(1200, 750)

    data_changed = pyqtSignal()

    def __init__(self, db, user_data):
        super().__init__()
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowSystemMenuHint |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )
        self.db = db
        self.user_data = user_data
        self.customers = []
        self.company_info = {}
        self.selected_proforma_id = None
        self.pallets = []
        self.setWindowTitle('مدیریت پیش‌فاکتور')
        self.resize(1400, 900)
        self.setLayoutDirection(Qt.RightToLeft)
        self._load_company_info()
        self._load_customers()
        self._load_pallets()
        self._build_ui()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(20)
        header = QFrame()
        header.setObjectName('Card')
        header_layout = QVBoxLayout(header)
        title = QLabel('مدیریت پیش‌فاکتورهای فروش')
        title.setObjectName('Title')
        subtitle = QLabel('ثبت، مشاهده و چاپ پیش‌فاکتورها')
        subtitle.setObjectName('Muted')
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)
        self.tabs = QTabWidget()
        
        def _wrap_in_scroll(widget):
            from PyQt5.QtWidgets import QScrollArea
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setWidget(widget)
            sa.setFrameShape(QScrollArea.NoFrame)
            return sa

        self.tabs.addTab(_wrap_in_scroll(self._build_new_tab()), 'ثبت پیش‌فاکتور جدید')
        self.tabs.addTab(_wrap_in_scroll(self._build_list_tab()), 'لیست پیش‌فاکتورها')
        root.addWidget(self.tabs)
        close_btn = QPushButton('بستن')
        close_btn.setObjectName('SecondaryButton')
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)

    def _build_new_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        wh_group = QGroupBox('انتخاب انبار مبدأ')
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
        self.warehouse_msg_lbl = QLabel('⚠️ ابتدا انبار را انتخاب کنید تا موجودی و میانگین قیمت لود شوند.')
        self.warehouse_msg_lbl.setObjectName('WarningLabel')
        whl.addWidget(self.warehouse_msg_lbl)
        layout.addWidget(wh_group)
        self._load_warehouses()
        info_group = QGroupBox('اطلاعات پیش‌فاکتور')
        info_layout = QGridLayout(info_group)
        info_layout.setHorizontalSpacing(16)
        info_layout.setVerticalSpacing(16)
        self.proforma_no_label = QLabel('-')
        self.proforma_no_label.setObjectName('Title')
        self.proforma_date_label = QLabel('-')
        self.proforma_date_label.setObjectName('Muted')
        self.proforma_date_label.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(250)
        self.customer_combo.currentIndexChanged.connect(self._on_customer_changed)
        self.validity_days_edit = QLineEdit('30')
        self.validity_days_edit.setPlaceholderText('تعداد روز اعتبار')
        self.description_edit = QTextEdit()
        self.description_edit.setMinimumHeight(60)
        self.description_edit.setPlaceholderText('توضیحات پیش‌فاکتور...')
        info_layout.addWidget(QLabel('شماره پیش‌فاکتور:'), 0, 0)
        info_layout.addWidget(self.proforma_no_label, 0, 1)
        info_layout.addWidget(QLabel('تاریخ:'), 0, 2)
        info_layout.addWidget(self.proforma_date_label, 0, 3)
        info_layout.addWidget(QLabel('مشتری:'), 1, 0)
        info_layout.addWidget(self.customer_combo, 1, 1, 1, 3)
        info_layout.addWidget(QLabel('اعتبار (روز):'), 2, 0)
        info_layout.addWidget(self.validity_days_edit, 2, 1)
        info_layout.addWidget(QLabel('توضیحات:'), 3, 0)
        info_layout.addWidget(self.description_edit, 3, 1, 1, 3)
        self.vat_exempt_check = QCheckBox('معاف از ارزش افزوده')
        info_layout.addWidget(self.vat_exempt_check, 4, 0, 1, 2)
        layout.addWidget(info_group)
        items_group = QGroupBox('ردیف‌های پیش‌فاکتور')
        items_layout = QVBoxLayout(items_group)
        items_layout.setSpacing(10)
        self.items_table = PalletItemsTable(db=self.db, show_price_avg=True)
        self._apply_reserved_stocks()
        items_layout.addWidget(self.items_table)
        self.items_table.setEnabled(False)
        layout.addWidget(items_group)

        action_buttons = QHBoxLayout()
        save_btn = QPushButton('ثبت پیش‌فاکتور')
        save_btn.setObjectName('PrimaryButton')
        save_btn.setMinimumHeight(45)
        save_btn.clicked.connect(self._save_proforma)
        preview_btn = QPushButton('پیش‌نمایش')
        preview_btn.setObjectName('SecondaryButton')
        preview_btn.setMinimumHeight(45)
        preview_btn.clicked.connect(self._preview_current_form)
        new_btn = QPushButton('فرم جدید')
        new_btn.setObjectName('SecondaryButton')
        new_btn.setMinimumHeight(45)
        new_btn.clicked.connect(self._clear_form)
        action_buttons.addWidget(new_btn)
        action_buttons.addWidget(preview_btn)
        action_buttons.addStretch()
        action_buttons.addWidget(save_btn)
        layout.addLayout(action_buttons)
        self._refresh_proforma_number()
        self.customer_combo.clear()
        self.customer_combo.addItem('انتخاب مشتری', None)
        for c in self.customers:
            name = "{} {}".format(c['first_name'], c['last_name']).strip()
            mobile = c.get('mobile', '')
            if mobile:
                self.customer_combo.addItem("{} | {}".format(name, mobile), c['id'])
            else:
                self.customer_combo.addItem(name, c['id'])
        return tab


    def _build_list_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        filter_group = QGroupBox('فیلتر')
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.addWidget(QLabel('از تاریخ:'))
        self.filter_date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDisplayFormat('yyyy-MM-dd')
        filter_layout.addWidget(self.filter_date_from)
        self.filter_from_jalali_lbl = QLabel('-')
        self.filter_from_jalali_lbl.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
        filter_layout.addWidget(self.filter_from_jalali_lbl)
        filter_layout.addWidget(QLabel('تا تاریخ:'))
        self.filter_date_to = QDateEdit(QDate.currentDate())
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDisplayFormat('yyyy-MM-dd')
        filter_layout.addWidget(self.filter_date_to)
        self.filter_to_jalali_lbl = QLabel('-')
        self.filter_to_jalali_lbl.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
        filter_layout.addWidget(self.filter_to_jalali_lbl)
        self.filter_date_from.dateChanged.connect(self._update_filter_jalali_labels)
        self.filter_date_to.dateChanged.connect(self._update_filter_jalali_labels)
        self._update_filter_jalali_labels()
        filter_customer = QComboBox()
        filter_customer.addItem('همه مشتریان', None)
        for c in self.customers:
            name = "{} {}".format(c['first_name'], c['last_name']).strip()
            filter_customer.addItem(name, c['id'])
        self.filter_customer_combo = filter_customer
        filter_layout.addWidget(QLabel('مشتری:'))
        filter_layout.addWidget(self.filter_customer_combo)
        refresh_btn = QPushButton('بروزرسانی')
        refresh_btn.setObjectName('PrimaryButton')
        refresh_btn.clicked.connect(self._refresh_list)
        filter_layout.addWidget(refresh_btn)
        filter_layout.addStretch()
        layout.addWidget(filter_group)
        self.proforma_list_table = QTableWidget(0, 9)
        self.proforma_list_table.setHorizontalHeaderLabels(['شناسه', 'شماره', 'تاریخ', 'مشتری', 'انبار', 'تعداد ردیف', 'جمع کل', 'اعتبار', 'وضعیت'])
        self.proforma_list_table.setColumnHidden(0, True)
        self.proforma_list_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.proforma_list_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.proforma_list_table.verticalHeader().setVisible(False)
        self.proforma_list_table.setAlternatingRowColors(True)
        self.proforma_list_table.itemSelectionChanged.connect(self._on_list_selection)
        layout.addWidget(self.proforma_list_table)
        list_buttons = QHBoxLayout()
        view_btn = QPushButton('مشاهده جزئیات')
        view_btn.setObjectName('PrimaryButton')
        view_btn.setMinimumHeight(40)
        view_btn.clicked.connect(self._view_selected_proforma)
        print_btn = QPushButton('چاپ')
        print_btn.setObjectName('SecondaryButton')
        print_btn.setMinimumHeight(40)
        print_btn.clicked.connect(self._print_selected_proforma)
        delete_btn = QPushButton('حذف')
        delete_btn.setObjectName('SecondaryButton')
        delete_btn.setMinimumHeight(40)
        delete_btn.clicked.connect(self._delete_selected_proforma)
        convert_btn = QPushButton('تبدیل به فاکتور')
        convert_btn.setObjectName('PrimaryButton')
        convert_btn.setMinimumWidth(160)
        convert_btn.setMinimumHeight(40)
        convert_btn.clicked.connect(self._convert_to_invoice)
        deleted_btn = QPushButton('پیش‌فاکتورهای حذف‌شده')
        deleted_btn.setObjectName('SecondaryButton')
        deleted_btn.clicked.connect(self._show_deleted_proformas)
        list_buttons.addWidget(view_btn)
        list_buttons.addWidget(print_btn)
        list_buttons.addWidget(convert_btn)
        list_buttons.addWidget(deleted_btn)
        list_buttons.addStretch()
        list_buttons.addWidget(delete_btn)
        layout.addLayout(list_buttons)
        self._refresh_list()
        return tab

    # ------------------------------------------------------------ Load
    def _load_company_info(self):
        from app.core.letterhead import get_filtered_company
        self.company_info = get_filtered_company(self.db)

    def _load_customers(self):
        self.customers = []
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                try:
                    rows = conn.execute("SELECT p.id, p.first_name, p.last_name, p.mobile FROM persons p JOIN person_roles pr ON pr.person_id = p.id AND pr.role_type = 'CUSTOMER' WHERE p.is_active = 1 ORDER BY p.first_name, p.last_name").fetchall()
                except Exception:
                    rows = conn.execute("SELECT id, first_name, last_name, mobile FROM persons WHERE is_active = 1 AND role_type = 'CUSTOMER' ORDER BY first_name, last_name").fetchall()
                self.customers = [{'id': r[0], 'first_name': r[1] or '', 'last_name': r[2] or '', 'mobile': r[3] or ''} for r in rows]
        except Exception:
            pass

    def _load_pallets(self):
        self.pallets = []
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("SELECT id,code,name FROM pallets WHERE is_active=1 ORDER BY code").fetchall()
                for r in rows:
                    self.pallets.append({'id': r[0], 'code': r[1] or '', 'name': r[2] or ''})
        except Exception:
            pass

    # ------------------------------------------------------------ Number
    def _on_customer_changed(self):
        self._refresh_proforma_number()

    def _refresh_proforma_number(self):
        today = today_iso_date()
        self.proforma_date_label.setText(jalali_date_display_from_iso(today))
        try:
            new_no = self._compute_next_proforma_no(self.customer_combo.currentData())
        except Exception:
            new_no = 'PR-0000-0000'
        self.proforma_no_label.setText(new_no)

    def _compute_next_proforma_no(self, customer_id) -> str:
        today = today_iso_date()
        try:
            from app.core.jalali import gregorian_to_jalali_str
            year = gregorian_to_jalali_str(today).split('/')[0]
        except Exception:
            year = today.split('-')[0]
        with self.db.connect() as conn:
            conn.row_factory = None
            row = conn.execute("SELECT proforma_no FROM proforma_invoices WHERE proforma_no LIKE ? ORDER BY id DESC LIMIT 1", (f'PR-{year}-%',)).fetchone()
            if row and row[0]:
                parts = row[0].split('-')
                try:
                    next_num = int(parts[-1]) + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1
            return f'PR-{year}-{next_num:04d}'

    # ------------------------------------------------------------ Save
    def _apply_reserved_stocks(self):
        """موجودی قابل‌استفادهٔ جدول = فیزیکی − رزروشده"""
        try:
            from app.core.stock_service import free_stock_map  # ONE-STOCK
            physical = free_stock_map(self.db)  # ONE-STOCK
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT pii.pallet_id, SUM(pii.quantity) "
                    "FROM proforma_invoice_items pii "
                    "JOIN proforma_invoices pi ON pi.id = pii.proforma_id "
                    "WHERE pi.status IN ('DRAFT','FINALIZED') "
                    "GROUP BY pii.pallet_id").fetchall()
            reserved = {r[0]: int(r[1] or 0) for r in rows}
            try:
                self._show_reserved_label(physical, reserved)
            except Exception:
                pass
            self.items_table.stocks = {
                pid: max(int(physical.get(pid, 0)) - int(reserved.get(pid, 0)), 0)
                for pid in physical
            }
        except Exception:
            pass

    def _pre_save_checks(self, items):
        """[VALID] ردیف تکراری + دوره مالی + موجودی آزاد(با رزرو)"""
        seen = set()
        for it in items:
            pid = it.get('pallet_id')
            if pid in seen:
                QMessageBox.warning(self, 'خطا', 'یک پالت در دو ردیف ثبت شده است؛ هر پالت فقط یک ردیف.')
                return False
            seen.add(pid)
        try:
            from app.repositories.fiscal_period_repository import FiscalPeriodRepository
            locked = FiscalPeriodRepository(self.db).locked_period(today_iso_date())
            if locked:
                QMessageBox.warning(self, 'دورهٔ مالی بسته',
                    'تاریخ سند داخل دورهٔ بستهٔ «{}» است. ابتدا بازگشایی کنید.'.format(locked.get('name', '-')))
                return False
        except Exception:
            pass
        try:
            from app.core.stock_service import free_stock_map  # ONE-STOCK
            physical = free_stock_map(self.db)  # ONE-STOCK
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT pii.pallet_id, SUM(pii.quantity) "
                    "FROM proforma_invoice_items pii "
                    "JOIN proforma_invoices pi ON pi.id = pii.proforma_id "
                    "WHERE pi.status IN ('DRAFT','FINALIZED') "
                    "GROUP BY pii.pallet_id").fetchall()
            reserved = {r[0]: int(r[1] or 0) for r in rows}
            requested = {}
            for it in items:
                pid = it.get('pallet_id')
                requested[pid] = requested.get(pid, 0) + int(it.get('quantity', 0) or 0)
            short = []
            for pid, q in requested.items():
                avail = int(physical.get(pid, 0)) - int(reserved.get(pid, 0))
                if q > avail:
                    code = next((p['code'] for p in self.pallets if p['id'] == pid), pid)
                    short.append('پالت {}: موجودی {:,} | رزروشده {:,} | آزاد {:,} | درخواست {:,}'.format(
                        code, int(physical.get(pid, 0)), int(reserved.get(pid, 0)), avail, q))
            if short:
                QMessageBox.warning(self, 'موجودی آزاد کافی نیست',
                    'جمع این پیش‌فاکتور و پیش‌فاکتورهای باز بیش از موجودی است:\n' + '\n'.join(short))
                return False
        except Exception:
            pass
        return True

    def _load_warehouses(self):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("SELECT id, code, name FROM warehouses WHERE is_active=1 ORDER BY code").fetchall()
            self.warehouses = [{'id': r[0], 'code': r[1] or '', 'name': r[2] or ''} for r in rows]
        except Exception:
            self.warehouses = []
        if hasattr(self, 'warehouse_combo'):
            self.warehouse_combo.blockSignals(True)
            self.warehouse_combo.clear()
            self.warehouse_combo.addItem('-- ابتدا انبار را انتخاب کنید --', None)
            for w in self.warehouses:
                self.warehouse_combo.addItem('{} | {}'.format(w.get('code', ''), w.get('name', '')), w.get('id'))
            self.warehouse_combo.blockSignals(False)

    def _stock_for_warehouse(self, pallet_id, warehouse_id):
        if not warehouse_id:
            return 0
        try:
            with self.db.connect() as conn:
                r = conn.execute("SELECT quantity FROM inventory_levels WHERE pallet_id=? AND warehouse_id=?", (pallet_id, warehouse_id)).fetchone()
                return int(r[0] or 0) if r else 0
        except Exception:
            return 0

    def _avg_price_for_warehouse(self, pallet_id, warehouse_id):
        """[AVG] میانگین: اول کاردکس (رسید)، بعد سند افتتاحیه، بعد قیمت پایه"""
        fb = int(getattr(self, 'avg_pallet_prices', {}).get(pallet_id, 0) or 0)
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                if warehouse_id:
                    r = conn.execute("SELECT COALESCE(SUM(qty_in*unit_price),0)/COALESCE(SUM(qty_in),0) FROM inventory_transactions WHERE pallet_id=? AND warehouse_id=? AND qty_in>0 AND unit_price>0 AND reference_type<>'TRANSFER'", (pallet_id, warehouse_id)).fetchone()
                    if r and r[0]:
                        return int(r[0])
                r2 = conn.execute("SELECT COALESCE(SUM(qty*unit_price),0)/COALESCE(SUM(qty),0) FROM opening_inventory_items WHERE pallet_id=? AND qty>0 AND unit_price>0", (pallet_id,)).fetchone()
                if r2 and r2[0]:
                    return int(r2[0])
                try:
                    r3 = conn.execute("SELECT price FROM pallets WHERE id=?", (pallet_id,)).fetchone()
                    if r3 and r3[0]:
                        return int(r3[0])
                except Exception:
                    pass
                return fb
        except Exception:
            return fb

    def _show_reserved_label(self, physical, reserved):
        try:
            from PyQt5.QtWidgets import QLabel
            if not hasattr(self, 'reserved_info_label'):
                self.reserved_info_label = QLabel('')
                self.reserved_info_label.setStyleSheet('color: #f59e0b; font-weight: bold; padding: 2px 6px;')
                try:
                    self.items_table.parentWidget().layout().addWidget(self.reserved_info_label)
                except Exception:
                    pass
            parts = []
            for pid, r in sorted(reserved.items()):
                if int(r or 0) > 0:
                    code = str(pid)
                    try:
                        code = next(x['code'] for x in self.items_table.pallets if x['id'] == pid)
                    except Exception:
                        pass
                    parts.append('{}: فیزیکی {} − رزرو {} = قابل‌فروش {}'.format(
                        code, int(physical.get(pid, 0)), int(r), max(int(physical.get(pid, 0)) - int(r), 0)))
            self.reserved_info_label.setText('رزرو باز → ' + ' | '.join(parts) if parts else '')
        except Exception:
            pass
    def _reserved_open_qty_map(self):
        """[RESERVE] مجموع رزروشده در پیش‌فاکتورهای باز و در اعتبار"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT pii.pallet_id, SUM(pii.quantity) "
                    "FROM proforma_invoice_items pii "
                    "JOIN proforma_invoices pi ON pi.id = pii.proforma_id "
                    "WHERE pi.status IN ('DRAFT','FINALIZED') "
                    "AND date(pi.proforma_date, '+' || COALESCE(pi.validity_days,30) || ' days') >= date('now') "
                    "GROUP BY pii.pallet_id"
                ).fetchall()
                d = {r[0]: int(r[1] or 0) for r in rows}
                rows2 = conn.execute(
                    "SELECT oli.pallet_id, "
                    "       SUM(oli.qty) - COALESCE((SELECT SUM(wii.qty) "
                    "           FROM warehouse_issue_items wii "
                    "           JOIN warehouse_issues wi ON wi.id = wii.issue_id "
                    "           WHERE wi.outbound_load_id = oli.outbound_load_id "
                    "             AND wii.pallet_id = oli.pallet_id "
                    "             AND wi.issue_status != 'CANCELLED'), 0) "
                    "FROM outbound_load_items oli "
                    "JOIN outbound_loads ol ON ol.id = oli.outbound_load_id "
                    "WHERE ol.is_active = 1 AND COALESCE(ol.remaining_qty,0) > 0 "
                    "GROUP BY oli.outbound_load_id, oli.pallet_id"
                ).fetchall()
                for pid, rem in rows2:
                    rem = int(rem or 0)
                    if rem > 0:
                        d[pid] = d.get(pid, 0) + rem
                return d
        except Exception:
            return {}

    def _on_warehouse_changed(self):
        wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
        if not wid:
            if hasattr(self, 'warehouse_msg_lbl'): self.warehouse_msg_lbl.show()
            if hasattr(self, 'items_table'): self.items_table.setEnabled(False)
            return
        if hasattr(self, 'warehouse_msg_lbl'): self.warehouse_msg_lbl.hide()
        if not hasattr(self, 'items_table'):
            return
        self.items_table.setEnabled(True)
        pallets = getattr(self.items_table, '_all_pallets', None) or getattr(self.items_table, 'pallets', []) or []
        self.items_table._all_pallets = pallets
        physical = free_stock_map(self.db)  # ONE-STOCK
        reserved = self._reserved_open_qty_map()
        stocks = {pid: max(int(physical.get(pid, 0)) - int(reserved.get(pid, 0)), 0) for pid in physical}
        prices = {p['id']: self._avg_price_for_warehouse(p['id'], wid) for p in pallets}
        if hasattr(self.items_table, 'stocks'): self.items_table.stocks = stocks
        for attr in ('prices', 'avg_prices', 'avg_pallet_prices'):
            if hasattr(self.items_table, attr): setattr(self.items_table, attr, prices)
        tbl = getattr(self.items_table, 'tbl', None)
        if tbl is not None:
            for row in range(tbl.rowCount()):
                combo = tbl.cellWidget(row, 1)
                spin = tbl.cellWidget(row, 2)
                if isinstance(combo, QComboBox):
                    cur = combo.currentData()
                    combo.blockSignals(True)
                    combo.clear()
                    combo.addItem('انتخاب پالت', None)
                    _vis = [p for p in pallets if stocks.get(p['id'], 0) > 0]
                    if cur and not any(p['id'] == cur for p in _vis):
                        _cp = next((p for p in pallets if p['id'] == cur), None)
                        if _cp:
                            _vis.append(_cp)
                    for p in _vis:
                        s = stocks.get(p['id'], 0); a = prices.get(p['id'], 0)
                        txt = '{} | {} (مانده انبار: {:,})'.format(p.get('code', ''), p.get('name', ''), s)
                        if a > 0: txt += ' | میانگین: {:,}'.format(a)
                        combo.addItem(txt, p['id'])
                    if cur:
                        idx = combo.findData(cur)
                        combo.setCurrentIndex(idx if idx >= 0 else 0)
                    combo.blockSignals(False)
                    pid = combo.currentData()
                    if spin is not None and hasattr(spin, 'setMaximum') and pid:
                        spin.setMaximum(max(stocks.get(pid, 0), 1))
                    self.items_table.pallets = [p for p in pallets if stocks.get(p['id'], 0) > 0]

    def _save_proforma(self):
        if getattr(self, '_saving', False):
            return
        self._saving = True
        try:
            customer_id = self.customer_combo.currentData()
            if not customer_id:
                QMessageBox.warning(self, 'خطا', 'لطفاً مشتری را انتخاب کنید.')
                return
            if hasattr(self, 'warehouse_combo') and not self.warehouse_combo.currentData():
                QMessageBox.warning(self, 'خطا', 'لطفاً ابتدا انبار مبدأ را انتخاب کنید.')
                return
            items = self.items_table.get_items()
            if not items:
                if self.items_table.tbl.rowCount() > 0:
                    QMessageBox.warning(self, 'خطا',
                        'ردیف ثبت‌نشده در جدول دارید!\n'
                        'لطفاً برای هر ردیف، پس از انتخاب پالت و تعداد، دکمهٔ «ثبت» همان ردیف را بزنید\n'
                        'یا ردیف مشکل‌دار را با دکمهٔ «حذف ردیف» حذف کنید.')
                else:
                    QMessageBox.warning(self, 'خطا', 'حداقل یک ردیف اضافه کنید.')
                return
            for item in items:
                if not item.get('pallet_id'):
                    QMessageBox.warning(self, 'خطا', 'لطفاً پالت را انتخاب کنید.')
                    return
                if item.get('quantity', 0) <= 0:
                    QMessageBox.warning(self, 'خطا', 'تعداد باید بیشتر از صفر باشد.')
                    return
            if not self._pre_save_checks(items):
                return
            proforma_no = self._compute_next_proforma_no(customer_id)
            proforma_date = today_iso_date()
            # [VALID-FISCAL] بررسی دورهٔ مالی بسته
            try:
                from app.repositories.fiscal_period_repository import FiscalPeriodRepository
                _locked = FiscalPeriodRepository(self.db).locked_period(proforma_date)
                if _locked:
                    QMessageBox.warning(
                        self, 'دورهٔ مالی بسته',
                        'تاریخ سند داخل دورهٔ بستهٔ «{}» است. ابتدا دوره را بازگشایی کنید.'.format(_locked.get('name', '-'))
                    )
                    return
            except Exception:
                pass
            # [VALID-DUP] جلوگیری از ردیف تکراری برای یک پالت
            _seen = set()
            for _it in items:
                _pid = _it.get('pallet_id')
                if _pid in _seen:
                    QMessageBox.warning(self, 'خطا', 'یک پالت در دو ردیف ثبت شده است؛ هر پالت فقط یک ردیف.')
                    return
                _seen.add(_pid)
            # [VALID-STOCK] کنترل ماندهٔ موجودی پالت‌ها
            try:
                with self.db.connect() as conn:
                    conn.row_factory = None
                    for _it in items:
                        _pid = _it.get('pallet_id')
                        _qty = int(_it.get('quantity', 0) or 0)
                        _r = conn.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory_levels WHERE pallet_id=?", (_pid,)).fetchone()
                        _stock = int(_r[0] or 0) if _r else 0
                        if _qty > _stock:
                            QMessageBox.warning(self, 'خطا', 'تعداد این پالت ({:,}) بیشتر از موجودی انبار ({:,}) است.'.format(_qty, _stock))
                            return
            except Exception:
                pass

            validity_days = int(self.validity_days_edit.text() or 30)
            description = self.description_edit.toPlainText()
            total_amount = sum(item.get('total_amount', 0) for item in items)
            vat_exempt = 1 if self.vat_exempt_check.isChecked() else 0
            vat_amount = 0 if vat_exempt else int(round(total_amount * 0.09))
            total_with_vat = total_amount + vat_amount
            try:
                with self.db.connect() as conn:
                    conn.execute("PRAGMA foreign_keys = OFF")
                    user_id = self.user_data.get('id')
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS proforma_invoices (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, proforma_no TEXT UNIQUE NOT NULL,
                            proforma_date TEXT NOT NULL, customer_id INTEGER, validity_days INTEGER DEFAULT 30,
                            total_amount INTEGER DEFAULT 0, description TEXT, status TEXT DEFAULT 'DRAFT',
                            created_by INTEGER, created_at TEXT,
                            vat_exempt INTEGER DEFAULT 0, vat_amount INTEGER DEFAULT 0, total_with_vat INTEGER DEFAULT 0
                        )
                    """)
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS proforma_invoice_items (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, proforma_id INTEGER NOT NULL, row_no INTEGER NOT NULL,
                            pallet_id INTEGER, quantity INTEGER DEFAULT 0, unit_price INTEGER DEFAULT 0,
                            total_amount INTEGER DEFAULT 0, note TEXT
                        )
                    """)
                    for col_name, col_type in [('vat_exempt', 'INTEGER DEFAULT 0'), ('vat_amount', 'INTEGER DEFAULT 0'), ('total_with_vat', 'INTEGER DEFAULT 0'), ('warehouse_id', 'INTEGER')]:
                        try:
                            conn.execute(f'ALTER TABLE proforma_invoices ADD COLUMN {col_name} {col_type}')
                        except Exception:
                            pass
                    conn.execute("""
                        INSERT INTO proforma_invoices
                        (proforma_no, proforma_date, customer_id, validity_days, total_amount, description, status, created_by, created_at, vat_exempt, vat_amount, total_with_vat)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (proforma_no, proforma_date, customer_id, validity_days, total_amount, description, 'DRAFT', user_id, now, vat_exempt, vat_amount, total_with_vat))
                    proforma_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    try:
                        _wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
                        if _wid:
                            conn.execute("UPDATE proforma_invoices SET warehouse_id=? WHERE id=?", (_wid, proforma_id))
                    except Exception:
                        pass
                    for item in items:
                        conn.execute("""
                            INSERT INTO proforma_invoice_items
                            (proforma_id, row_no, pallet_id, quantity, unit_price, total_amount, note)
                            VALUES (?,?,?,?,?,?,?)
                        """, (proforma_id, item.get('row_no', 1), item.get('pallet_id'), item.get('quantity', 0), item.get('unit_price', 0), item.get('total_amount', 0), item.get('note', '')))
                    conn.commit()
                reply = QMessageBox.question(self, 'تأیید ثبت', f'پیش‌فاکتور {proforma_no} با موفقیت ثبت شد.\n\nآیا می‌خواهید پیش‌فاکتور را مشاهده و چاپ کنید؟', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    self._print_proforma(proforma_id)
                self._clear_form()
                self._refresh_list()
                self.data_changed.emit()
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, 'خطا', f'خطا در ثبت پیش‌فاکتور:\n{e}')
        finally:
            self._saving = False

    # ------------------------------------------------------------ List
    def _update_filter_jalali_labels(self, *_args):
        try:
            self.filter_from_jalali_lbl.setText(jalali_date_display_from_iso(self.filter_date_from.date().toString('yyyy-MM-dd')))
            self.filter_to_jalali_lbl.setText(jalali_date_display_from_iso(self.filter_date_to.date().toString('yyyy-MM-dd')))
        except Exception:
            pass

    def _refresh_list(self):
        if not hasattr(self, 'proforma_list_table'):
            return
        date_from = self.filter_date_from.date().toString('yyyy-MM-dd')
        date_to = self.filter_date_to.date().toString('yyyy-MM-dd')
        customer_id = self.filter_customer_combo.currentData()
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                query = """
                    SELECT pi.id, pi.proforma_no, pi.proforma_date, pi.total_amount, pi.validity_days, pi.status,
                       p.first_name || ' ' || p.last_name,
                       (SELECT COUNT(*) FROM proforma_invoice_items WHERE proforma_id=pi.id),
                       (CASE WHEN w.id IS NULL THEN '-' ELSE COALESCE(w.code,'-') || ' | ' || COALESCE(w.name,'-') END)
                 FROM proforma_invoices pi
                 LEFT JOIN persons p ON p.id=pi.customer_id
                 LEFT JOIN warehouses w ON w.id = pi.warehouse_id
                 WHERE pi.proforma_date BETWEEN ? AND ?
                """
                params = [date_from, date_to]
                if customer_id:
                    query += " AND pi.customer_id=?"
                    params.append(customer_id)
                query += " ORDER BY COALESCE(w.code, '~~~~') ASC, pi.id DESC"
                rows = conn.execute(query, params).fetchall()
                self.proforma_list_table.setRowCount(len(rows))
                for idx, r in enumerate(rows):
                    status_labels = {'DRAFT': 'پیش‌نویس', 'FINALIZED': 'نهایی', 'CONVERTED': 'تبدیل شده', 'CANCELLED': 'باطل شده'}
                    vals = [
                        str(r[0]), r[1] or '-',
                        jalali_date_display_from_iso(r[2]) if r[2] else '-',
                        r[6] or '-',
                        r[8] or '-',
                        str(r[7] or 0),
                        '{:,}'.format(int(r[3] or 0)) + ' ریال',
                        str(r[4] or 30) + ' روز',
                        status_labels.get(r[5], r[5] or '-')
                    ]
                    for col, v in enumerate(vals):
                        item = QTableWidgetItem(str(v))
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        self.proforma_list_table.setItem(idx, col, item)
                self.proforma_list_table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در بارگذاری لیست:\n' + str(e))

    def _on_list_selection(self):
        pass

    # ------------------------------------------------------------ View
    def _pallet_remaining_info(self, pallet_id, warehouse_id, fallback_price):
        """[NEW] مانده فعلی پالت در انبار سند + ارزش ریالی آن"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                r = conn.execute("SELECT quantity FROM inventory_levels WHERE pallet_id=? AND warehouse_id=?", (pallet_id, warehouse_id)).fetchone()
                rem = int(r[0] or 0) if r else 0
                a = conn.execute("SELECT COALESCE(SUM(qty_in*unit_price),0)/COALESCE(SUM(qty_in),0) FROM inventory_transactions WHERE pallet_id=? AND warehouse_id=? AND qty_in>0 AND unit_price>0 AND reference_type<>'TRANSFER'", (pallet_id, warehouse_id)).fetchone()
                avg = int(a[0]) if (a and a[0]) else int(fallback_price or 0)
                return rem, avg
        except Exception:
            return 0, int(fallback_price or 0)

    def _view_selected_proforma(self):
        row = self.proforma_list_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'توجه', 'ابتدا یک پیش‌فاکتور از لیست انتخاب کنید.')
            return
        proforma_id = int(self.proforma_list_table.item(row, 0).text())
        self._view_proforma(proforma_id)

    def _view_proforma(self, proforma_id):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                pi = conn.execute("SELECT pi.id,pi.proforma_no,pi.proforma_date,pi.total_amount,pi.validity_days,pi.status,pi.description,p.first_name||' '||p.last_name,COALESCE(pi.vat_amount,0),COALESCE(pi.total_with_vat,0),COALESCE(pi.vat_exempt,0), COALESCE(w.code,'-'), COALESCE(w.name,'-'), pi.warehouse_id FROM proforma_invoices pi LEFT JOIN persons p ON p.id=pi.customer_id LEFT JOIN warehouses w ON w.id=pi.warehouse_id WHERE pi.id=?", (proforma_id,)).fetchone()
                if not pi:
                    QMessageBox.warning(self, 'خطا', 'پیش‌فاکتور یافت نشد.')
                    return
                items = conn.execute("SELECT pii.row_no,p.code,p.name,pii.quantity,pii.unit_price,pii.total_amount,pii.note,pii.pallet_id FROM proforma_invoice_items pii JOIN pallets p ON p.id=pii.pallet_id WHERE pii.proforma_id=? ORDER BY pii.row_no", (proforma_id,)).fetchall()
            dialog = QDialog(self)
            dialog.setWindowTitle('جزئیات: {}'.format(pi[1]))
            dialog.resize(900, 600)
            dialog.setLayoutDirection(Qt.RightToLeft)
            dlg_layout = QVBoxLayout(dialog)
            info_group = QGroupBox('اطلاعات')
            info_layout = QGridLayout(info_group)
            info_layout.addWidget(QLabel('شماره:'), 0, 0)
            info_layout.addWidget(QLabel(str(pi[1])), 0, 1)
            info_layout.addWidget(QLabel('تاریخ:'), 0, 2)
            info_layout.addWidget(QLabel(jalali_date_display_from_iso(pi[2]) if pi[2] else '-'), 0, 3)
            info_layout.addWidget(QLabel('مشتری:'), 1, 0)
            info_layout.addWidget(QLabel(str(pi[7] or '-')), 1, 1)
            info_layout.addWidget(QLabel('جمع کل:'), 1, 2)
            info_layout.addWidget(QLabel("{:,} ریال".format(int(pi[3] or 0))), 1, 3)
            info_layout.addWidget(QLabel('اعتبار:'), 2, 0)
            info_layout.addWidget(QLabel("{} روز".format(pi[4] or 30)), 2, 1)
            info_layout.addWidget(QLabel('ارزش افزوده:'), 2, 2)
            info_layout.addWidget(QLabel('معاف' if int(pi[10] or 0) else "{:,} ریال".format(int(pi[8] or 0))), 2, 3)
            info_layout.addWidget(QLabel('جمع نهایی:'), 3, 0)
            info_layout.addWidget(QLabel("{:,} ریال".format(int(pi[9] or 0))), 3, 1)
            info_layout.addWidget(QLabel('انبار:'), 4, 0)
            info_layout.addWidget(QLabel((pi[11] + ' | ' + pi[12]) if (pi[11] and pi[11] != '-') else '-'), 4, 1, 1, 3)
            dlg_layout.addWidget(info_group)
            items_table = QTableWidget(0, 7)
            items_table.setHorizontalHeaderLabels(['ردیف', 'کد پالت', 'نام پالت', 'تعداد', 'قیمت واحد', 'مبلغ کل', 'مانده انبار', 'ارزش مانده', 'توضیح'])
            items_table.verticalHeader().setVisible(False)
            items_table.setRowCount(len(items))
            for idx, it in enumerate(items):
                rem, avg = self._pallet_remaining_info(it[7], pi[13], it[4])
                vals = [str(it[0]), it[1] or '-', it[2] or '-', "{:,}".format(int(it[3] or 0)), "{:,}".format(int(it[4] or 0)), "{:,}".format(int(it[5] or 0)), "{:,}".format(rem), "{:,} ریال".format(rem * avg), it[6] or '-']
                for col, v in enumerate(vals):
                    cell = QTableWidgetItem(str(v))
                    cell.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    items_table.setItem(idx, col, cell)
            items_table.resizeColumnsToContents()
            dlg_layout.addWidget(items_table)
            close_btn = QPushButton('بستن')
            close_btn.clicked.connect(dialog.accept)
            dlg_layout.addWidget(close_btn)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در نمایش:\n{}'.format(e))

    # ------------------------------------------------------------ Words
    def _number_to_persian_words(self, number):
        if number == 0:
            return 'صفر'
        ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه', 'ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']
        tens = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
        hundreds = ['', 'یکصد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']

        def three_digits(n):
            result = ''
            h, t, o = n // 100, (n % 100) // 10, n % 10
            if h > 0:
                result += hundreds[h] + ' و '
            if t == 1:
                result += ones[10 + o]
            else:
                if t > 0:
                    result += tens[t]
                    if o > 0:
                        result += ' و ' + ones[o]
                elif o > 0:
                    result += ones[o]
            return result.strip(' و ')

        if number < 0:
            return 'منفی ' + self._number_to_persian_words(-number)
        parts = []
        if number >= 1000000000:
            parts.append(three_digits(number // 1000000000) + ' میلیارد')
            number %= 1000000000
        if number >= 1000000:
            parts.append(three_digits(number // 1000000) + ' میلیون')
            number %= 1000000
        if number >= 1000:
            parts.append(three_digits(number // 1000) + ' هزار')
            number %= 1000
        if number > 0:
            parts.append(three_digits(number))
        return ' و '.join(parts)

    # ------------------------------------------------------------ Print
    def _print_selected_proforma(self):
        row = self.proforma_list_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'توجه', 'ابتدا یک پیش‌فاکتور از لیست انتخاب کنید.')
            return
        proforma_id = int(self.proforma_list_table.item(row, 0).text())
        self._print_proforma(proforma_id)

    def _print_proforma(self, proforma_id):  # UNIFIED-PROFORMA
        from app.core.letterhead import get_filtered_company
        company = get_filtered_company(self.db)
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                pi = conn.execute(
                    "SELECT pi.id, pi.proforma_no, pi.proforma_date, pi.total_amount, "
                    "pi.validity_days, pi.status, pi.description, "
                    "p.first_name || ' ' || p.last_name, p.mobile, "
                    "COALESCE(pi.vat_amount,0), COALESCE(pi.total_with_vat,0), COALESCE(pi.vat_exempt,0), "
                    "COALESCE(w.code, '-'), COALESCE(w.name, '-') "
                    "FROM proforma_invoices pi "
                    "LEFT JOIN persons p ON p.id = pi.customer_id LEFT JOIN warehouses w ON w.id = pi.warehouse_id "
                    "WHERE pi.id = ?", (proforma_id,)
                ).fetchone()
                if not pi:
                    QMessageBox.warning(self, 'خطا', 'پیش‌فاکتور یافت نشد.')
                    return
                items = conn.execute(
                    "SELECT pii.row_no, p.code, p.name, pii.quantity, pii.unit_price, "
                    "pii.total_amount, pii.note "
                    "FROM proforma_invoice_items pii "
                    "JOIN pallets p ON p.id = pii.pallet_id "
                    "WHERE pii.proforma_id = ? ORDER BY pii.row_no", (proforma_id,)
                ).fetchall()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e))
            return

        def to_int(val, default=0):
            try: return int(float(str(val or default).replace(',','')))
            except: return default

        total_amount = to_int(pi[3])
        vat_amount = to_int(pi[9])
        total_with_vat = to_int(pi[10]) if to_int(pi[10]) else (total_amount + vat_amount)
        vat_exempt = bool(to_int(pi[11]))
        amount_words = self._number_to_persian_words(total_with_vat) + ' ریال'

        rows_html = ""
        for it in items:
            rows_html += ("<tr><td>{}</td><td>{}</td><td>{}</td>"
                          "<td>{:,}</td><td>{:,}</td><td>{:,}</td></tr>").format(
                it[0] or '', it[1] or '', it[2] or '',
                to_int(it[3]), to_int(it[4]), to_int(it[5]))

        ceo_line = "<p>مدیر عامل: {}</p>".format(company.get('ceo_name','')) if company.get('ceo_name') else ""
        nat_parts = []
        if company.get('national_id'): nat_parts.append("شناسه ملی: {}".format(company['national_id']))
        if company.get('economic_code'): nat_parts.append("کد اقتصادی: {}".format(company['economic_code']))
        national_line = "<p>{}</p>".format(" | ".join(nat_parts)) if nat_parts else ""
        ph_parts = []
        if company.get('phone'): ph_parts.append("تلفن: {}".format(company['phone']))
        if company.get('mobile'): ph_parts.append("موبایل: {}".format(company['mobile']))
        phone_line = "<p>{}</p>".format(" | ".join(ph_parts)) if ph_parts else ""
        addr_line = "<p>آدرس: {}</p>".format(company.get('address','')) if company.get('address') else ""
        customer_phone = "<p>تلفن: {}</p>".format(pi[8]) if pi[8] else ""
        notes_box = '<div class="notes-box"><strong>توضیحات:</strong> {}</div>'.format(pi[6]) if pi[6] else ""

        if vat_exempt:
            vat_rows = ('<tr bgcolor="#f1f5f9"><td colspan="4" align="left"><b>ارزش افزوده:</b></td>'
                        '<td colspan="2"><b>معاف از مالیات</b></td></tr>')
        else:
            vat_rows = ('<tr bgcolor="#f1f5f9"><td colspan="4" align="left"><b>ارزش افزوده ۹٪:</b></td>'
                        '<td colspan="2"><b>{:,} ریال</b></td></tr>'
                        '<tr bgcolor="#dcfce7"><td colspan="4" align="left"><b>جمع نهایی:</b></td>'
                        '<td colspan="2"><b>{:,} ریال</b></td></tr>'.format(vat_amount, total_with_vat))

        html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>پیش‌فاکتور {proforma_no}</title></head>
<body dir="rtl" style="font-family:Tahoma,Arial,sans-serif;color:#1e293b;">
<table width="100%" border="0" dir="rtl"><tr><td>
<table width="100%" cellspacing="0" cellpadding="4" border="0"><tr>
<td width="62%" valign="top">
<font size="6" color="#1e293b"><b>{company_name}</b></font><br>
<font size="2" color="#475569">{ceo_line}{national_line}{phone_line}{addr_line}</font>
</td>
<td width="38%" valign="top">
<table width="100%" cellspacing="0" cellpadding="6" border="1">
<tr><td bgcolor="#f5f3ff" align="center">
<font size="4" color="#9333ea"><b>پیش‌فاکتور فروش</b></font><br>
<font size="2" color="#334155">
<b>شماره:</b> {proforma_no}<br>
<b>تاریخ:</b> {proforma_date}<br>
<b>اعتبار:</b> {validity} روز
</font></td></tr></table>
</td></tr></table>
<hr color="#9333ea" size="2">
<table width="100%" cellspacing="0" cellpadding="8" border="1"><tr><td bgcolor="#fef3c7">
<font size="2"><b>خریدار:</b> {customer_name} {customer_phone}<br><b>انبار مبدأ:</b> {warehouse_code} | {warehouse_name}</font>
</td></tr></table>
<table width="100%" border="1" cellspacing="0" cellpadding="3">
<tr><th>ردیف</th><th>کد پالت</th><th>نام پالت</th><th>تعداد</th><th>قیمت واحد</th><th>مبلغ کل</th></tr>
{rows_html}
<tr bgcolor="#dbeafe"><td colspan="4" align="left"><b>جمع کل:</b></td><td colspan="2"><b>{total_amount:,} ریال</b></td></tr>
{vat_rows}
</table>
<table width="100%" cellspacing="0" cellpadding="8" border="0"><tr><td bgcolor="#f8fafc">
<font size="2">مبلغ به حروف: <b>{amount_words}</b></font>
</td></tr></table>
{notes_box}
<table width="100%" cellspacing="0" cellpadding="10" border="0"><tr>
<td align="center"><br><br>____________________<br><font size="2">مهر و امضای فروشنده</font></td>
<td align="center"><br><br>____________________<br><font size="2">مهر و امضای خریدار</font></td>
</tr></table>
<p align="center"><font size="1" color="#7c3aed">این سند به صورت سیستمی تولید شده است</font></p>
</td></tr></table>
</body></html>""".format(
            proforma_no=pi[1] or '-', company_name=company.get('company_name','نام شرکت'),
            ceo_line=ceo_line, national_line=national_line, phone_line=phone_line, addr_line=addr_line,
            proforma_date=jalali_date_display_from_iso(pi[2]) if pi[2] else '-',
            validity=to_int(pi[4], 30),
            customer_name=pi[7] or '-', customer_phone=customer_phone,
            warehouse_code=pi[12] or '-', warehouse_name=pi[13] or '-',  # PF-WAREHOUSE
            rows_html=rows_html, total_amount=total_amount, vat_rows=vat_rows,
            amount_words=amount_words, notes_box=notes_box)

        from app.ui.html_preview_dialog import HtmlPreviewDialog
        dialog = HtmlPreviewDialog(html, 'پیش‌فاکتور {}'.format(pi[1] or ''), self)
        dialog.exec_()

    # ------------------------------------------------------------ Preview
    def _preview_current_form(self):  # UNIFIED-PROFORMA
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً مشتری را انتخاب کنید.')
            return
        customer_name = self.customer_combo.currentText().split('|')[0].strip()
        _wid_idx = self.warehouse_combo.currentIndex() if hasattr(self, 'warehouse_combo') else 0
        _wid_txt = self.warehouse_combo.currentText() if hasattr(self, 'warehouse_combo') else ''
        if '|' in _wid_txt:
            _wc, _wn = _wid_txt.split('|', 1); _wc = _wc.strip(); _wn = _wn.strip()
        else:
            _wc, _wn = '-', '-'  # PF-WAREHOUSE
        proforma_no = self.proforma_no_label.text()
        proforma_date = self.proforma_date_label.text()
        validity_days = int(self.validity_days_edit.text() or 30)
        items = self.items_table.get_items()
        if not items:
            QMessageBox.warning(self, 'خطا', 'حداقل یک ردیف کالا اضافه کنید.')
            return
        total_amount = sum(item.get('total_amount', 0) for item in items)
        vat_exempt = self.vat_exempt_check.isChecked()
        vat_amount = 0 if vat_exempt else int(round(total_amount * 0.09))
        total_with_vat = total_amount + vat_amount
        amount_words = self._number_to_persian_words(total_with_vat) + ' ریال'

        rows_html = ''
        for idx, item in enumerate(items, 1):
            rows_html += '<tr><td>{}</td><td>{}</td><td>{}</td><td>{:,}</td><td>{:,}</td><td>{:,}</td></tr>'.format(
                idx, item.get('code', ''), item.get('name', ''),
                int(item.get('quantity', 0) or 0), int(item.get('unit_price', 0) or 0),
                int(item.get('total_amount', 0) or 0))

        from app.core.letterhead import get_filtered_company
        company = get_filtered_company(self.db)
        ceo_line = "<p>مدیر عامل: {}</p>".format(company.get('ceo_name','')) if company.get('ceo_name') else ""
        nat_parts = []
        if company.get('national_id'): nat_parts.append("شناسه ملی: {}".format(company['national_id']))
        if company.get('economic_code'): nat_parts.append("کد اقتصادی: {}".format(company['economic_code']))
        national_line = "<p>{}</p>".format(" | ".join(nat_parts)) if nat_parts else ""
        ph_parts = []
        if company.get('phone'): ph_parts.append("تلفن: {}".format(company['phone']))
        if company.get('mobile'): ph_parts.append("موبایل: {}".format(company['mobile']))
        phone_line = "<p>{}</p>".format(" | ".join(ph_parts)) if ph_parts else ""
        addr_line = "<p>آدرس: {}</p>".format(company.get('address','')) if company.get('address') else ""

        if vat_exempt:
            vat_rows = ('<tr bgcolor="#f1f5f9"><td colspan="4" align="left"><b>ارزش افزوده:</b></td>'
                        '<td colspan="2"><b>معاف از مالیات</b></td></tr>')
        else:
            vat_rows = ('<tr bgcolor="#f1f5f9"><td colspan="4" align="left"><b>ارزش افزوده ۹٪:</b></td>'
                        '<td colspan="2"><b>{:,} ریال</b></td></tr>'
                        '<tr bgcolor="#dcfce7"><td colspan="4" align="left"><b>جمع نهایی:</b></td>'
                        '<td colspan="2"><b>{:,} ریال</b></td></tr>'.format(vat_amount, total_with_vat))

        html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>پیش‌نمایش {proforma_no}</title></head>
<body dir="rtl" style="font-family:Tahoma,Arial,sans-serif;color:#1e293b;">
<table width="100%" border="0" dir="rtl"><tr><td>
<table width="100%" cellspacing="0" cellpadding="4" border="0"><tr>
<td width="62%" valign="top">
<font size="6" color="#1e293b"><b>{company_name}</b></font><br>
<font size="2" color="#475569">{ceo_line}{national_line}{phone_line}{addr_line}</font>
</td>
<td width="38%" valign="top">
<table width="100%" cellspacing="0" cellpadding="6" border="1">
<tr><td bgcolor="#f5f3ff" align="center">
<font size="4" color="#9333ea"><b>پیش‌نمایش پیش‌فاکتور</b></font><br>
<font size="2" color="#334155">
<b>شماره:</b> {proforma_no}<br>
<b>تاریخ:</b> {proforma_date}<br>
<b>اعتبار:</b> {validity} روز
</font></td></tr></table>
</td></tr></table>
<hr color="#9333ea" size="2">
<table width="100%" cellspacing="0" cellpadding="8" border="1"><tr><td bgcolor="#fef3c7">
<font size="2"><b>خریدار:</b> {customer_name}<br><b>انبار مبدأ:</b> {warehouse_code} | {warehouse_name}</font>
</td></tr></table>
<table width="100%" border="1" cellspacing="0" cellpadding="3">
<tr><th>ردیف</th><th>کد پالت</th><th>نام پالت</th><th>تعداد</th><th>قیمت واحد</th><th>مبلغ کل</th></tr>
{rows_html}
<tr bgcolor="#dbeafe"><td colspan="4" align="left"><b>جمع کل:</b></td><td colspan="2"><b>{total_amount:,} ریال</b></td></tr>
{vat_rows}
</table>
<table width="100%" cellspacing="0" cellpadding="8" border="0"><tr><td bgcolor="#f8fafc">
<font size="2">مبلغ به حروف: <b>{amount_words}</b></font>
</td></tr></table>
<table width="100%" cellspacing="0" cellpadding="10" border="0"><tr>
<td align="center"><br><br>____________________<br><font size="2">مهر و امضای فروشنده</font></td>
<td align="center"><br><br>____________________<br><font size="2">مهر و امضای خریدار</font></td>
</tr></table>
</td></tr></table>
</body></html>""".format(
            proforma_no=proforma_no, company_name=company.get('company_name','نام شرکت'),
            ceo_line=ceo_line, national_line=national_line, phone_line=phone_line, addr_line=addr_line,
            proforma_date=proforma_date, validity=validity_days,
            customer_name=customer_name, warehouse_code=_wc, warehouse_name=_wn,  # PF-WAREHOUSE
            rows_html=rows_html,
            total_amount=total_amount, vat_rows=vat_rows, amount_words=amount_words)

        from app.ui.html_preview_dialog import HtmlPreviewDialog
        dialog = HtmlPreviewDialog(html, 'پیش‌نمایش {}'.format(proforma_no), self)
        dialog.exec_()

    # ------------------------------------------------------------ Delete
    def _delete_selected_proforma(self):
        row = self.proforma_list_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'توجه', 'ابتدا یک پیش‌فاکتور از لیست انتخاب کنید.')
            return
        proforma_id = int(self.proforma_list_table.item(row, 0).text())
        proforma_no = self.proforma_list_table.item(row, 1).text()
        reply = QMessageBox.question(self, 'تایید حذف', 'آیا از حذف پیش‌فاکتور {} اطمینان دارید؟'.format(proforma_no), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            with self.db.connect() as conn:
                conn.execute("UPDATE proforma_invoices SET status = 'CANCELLED' WHERE id = ?", (proforma_id,))
                conn.execute("UPDATE outbound_loads SET load_status = 'CANCELLED', is_active = 0 WHERE id = (SELECT outbound_load_id FROM proforma_invoices WHERE id = ?)", (proforma_id,))
                conn.commit()
            QMessageBox.information(self, 'موفق', 'پیش‌فاکتور حذف شد.')
            self._refresh_list()
            self.data_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در حذف:\n{}'.format(e))

    # ------------------------------------------------------------ Convert
    def _convert_to_invoice(self):
        row = self.proforma_list_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'توجه', 'ابتدا یک پیش‌فاکتور از لیست انتخاب کنید.')
            return
        proforma_id = int(self.proforma_list_table.item(row, 0).text())
        proforma_no = self.proforma_list_table.item(row, 1).text()
        reply = QMessageBox.question(self, 'تأیید', 'آیا از تبدیل پیش‌فاکتور {} به مرجع خروج اطمینان دارید؟'.format(proforma_no), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                conn.execute("CREATE TABLE IF NOT EXISTS outbound_load_items (id INTEGER PRIMARY KEY AUTOINCREMENT, outbound_load_id INTEGER NOT NULL, row_no INTEGER NOT NULL, pallet_id INTEGER NOT NULL, qty INTEGER NOT NULL DEFAULT 0, unit_price INTEGER NOT NULL DEFAULT 0, total_price INTEGER NOT NULL DEFAULT 0, notes TEXT)")
                pi = conn.execute("SELECT id,proforma_no,proforma_date,total_amount,customer_id,status,description FROM proforma_invoices WHERE id=?", (proforma_id,)).fetchone()
                if not pi:
                    QMessageBox.warning(self, 'خطا', 'پیش‌فاکتور یافت نشد.')
                    return
                if pi[5] == 'CONVERTED':
                    QMessageBox.warning(self, 'خطا', 'این پیش‌فاکتور قبلاً تبدیل شده.')
                    return
                items = conn.execute("SELECT pii.row_no, pii.pallet_id, pii.quantity, pii.unit_price, pii.total_amount FROM proforma_invoice_items pii WHERE pii.proforma_id=? ORDER BY pii.row_no", (proforma_id,)).fetchall()
                if not items:
                    QMessageBox.warning(self, 'خطا', 'پیش‌فاکتور فاقد آیتم است.')
                    return
                customer_id = pi[4]
                total_qty = sum(int(it[2] or 0) for it in items)
                if total_qty <= 0:
                    QMessageBox.warning(self, 'خطا', 'جمع تعداد اقلام پیش‌فاکتور صفر است.')
                    return
                driver_id = None
                dr = conn.execute("SELECT p.id FROM persons p JOIN person_roles pr ON pr.person_id = p.id AND pr.role_type = 'DRIVER' WHERE p.is_active = 1 LIMIT 1").fetchone()
                if dr:
                    driver_id = dr[0]
                if driver_id is None:
                    QMessageBox.critical(self, 'خطا', 'هیچ راننده‌ای تعریف نشده است.')
                    return
                gregorian_date = today_iso_date()
                _jy = jalali_date_display_from_iso(datetime.now().strftime('%Y-%m-%d'))[:4]
                ref_no = f"EX-{_jy}-" + str(proforma_id).zfill(4)

                conn.execute("INSERT INTO outbound_loads (reference_no, customer_id, driver_id, total_load_qty, issued_qty_total, remaining_qty, load_status, register_date, is_active) VALUES (?,?,?,?,?,?,?,?,?)", (ref_no, customer_id, driver_id, total_qty, 0, total_qty, 'OPEN', gregorian_date, 1))
                outbound_load_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute("UPDATE proforma_invoices SET outbound_load_id = ? WHERE id = ?", (outbound_load_id, proforma_id))
                for it in items:
                    qty = int(it[2] or 0)
                    unit_price = int(it[3] or 0)
                    conn.execute("INSERT INTO outbound_load_items (outbound_load_id, row_no, pallet_id, qty, unit_price, total_price, notes) VALUES (?,?,?,?,?,?,?)", (outbound_load_id, int(it[0] or 0), it[1], qty, unit_price, qty * unit_price, ''))
                conn.execute("UPDATE proforma_invoices SET status='CONVERTED' WHERE id=?", (proforma_id,))
                conn.commit()
                QMessageBox.information(self, 'موفق', 'پیش‌فاکتور {} به مرجع خروج تبدیل شد.\nشماره مرجع: {}\n\nاکنون از «حواله خروج» این مرجع را انتخاب و ثبت کنید؛\nسند مالی و کاردکس فقط هنگام ثبت حواله صادر می‌شود.'.format(proforma_no, ref_no))
                self._refresh_list()
                self.data_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در تبدیل:\n' + str(e))

    # ------------------------------------------------------------ Helpers
    def _show_deleted_proformas(self):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("SELECT pi.id, pi.proforma_no, pi.proforma_date, pi.total_amount, p.first_name || ' ' || p.last_name, pi.status FROM proforma_invoices pi LEFT JOIN persons p ON p.id=pi.customer_id WHERE pi.status = 'CANCELLED' ORDER BY pi.id DESC").fetchall()
            if not rows:
                QMessageBox.information(self, 'پیش‌فاکتورهای حذف‌شده', 'هیچ پیش‌فاکتور حذف‌شده‌ای وجود ندارد.')
                return
            dialog = QDialog(self)
            dialog.setWindowTitle('پیش‌فاکتورهای حذف‌شده')
            dialog.resize(800, 500)
            dialog.setLayoutDirection(Qt.RightToLeft)
            layout = QVBoxLayout(dialog)
            table = QTableWidget(0, 5)
            table.setHorizontalHeaderLabels(['شماره', 'تاریخ', 'مشتری', 'مبلغ', 'وضعیت'])
            table.verticalHeader().setVisible(False)
            table.setRowCount(len(rows))
            for idx, r in enumerate(rows):
                table.setItem(idx, 0, QTableWidgetItem(r[1] or '-'))
                table.setItem(idx, 1, QTableWidgetItem(jalali_date_display_from_iso(r[2]) if r[2] else '-'))
                table.setItem(idx, 2, QTableWidgetItem(r[4] or '-'))
                table.setItem(idx, 3, QTableWidgetItem(f"{int(r[3] or 0):,} ریال"))
                table.setItem(idx, 4, QTableWidgetItem(r[5] or '-'))
            table.resizeColumnsToContents()
            layout.addWidget(table)
            close_btn = QPushButton('بستن')
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در نمایش:\n{e}')

    def _clear_form(self):
        self.customer_combo.setCurrentIndex(0)
        self.validity_days_edit.setText('30')
        self.description_edit.clear()
        if hasattr(self, 'vat_exempt_check'):
            self.vat_exempt_check.setChecked(False)
        if hasattr(self, 'items_table'):
            self.items_table.clear()
        self._refresh_proforma_number()


