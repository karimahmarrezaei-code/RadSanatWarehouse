# -*- coding: utf-8 -*-
"""
Reports Window - نسخه بازطراحی‌شده کامل
با Sidebar Navigation و طراحی مدرن
"""

from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QSize, QDate
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFileDialog, QFrame,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSplitter,
    QStackedWidget, QTableWidget,
    QTabWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QDateEdit,
)

from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_display_from_iso
from app.repositories.finance_repository import FinanceRepository
from app.repositories.report_repository import ReportRepository
from app.services.report_export_service import (
    export_aggregate_stock_to_excel,
    export_aggregate_stock_to_pdf,
    export_financial_summary_to_excel,
    export_financial_summary_to_pdf,
    export_kardex_to_excel,
    export_kardex_to_pdf,
    export_person_statement_to_excel,
    export_person_statement_to_pdf,
    export_stock_value_to_excel,
    export_stock_value_to_pdf,
)

# فرم‌های خارجی
from app.ui.return_report_window import ReturnReportWindow
from app.ui.pnl_report_window import PnlReportWindow
from app.ui.aging_report_window import AgingReportWindow
from app.ui.expense_category_window import ExpenseCategoryManagerWindow
from app.ui.expense_window import ExpenseWindow
from app.ui.expense_report_window import ExpenseReportWindow
from app.ui.dead_stock_window import DeadStockWindow


ROLE_LABELS = {
    'CUSTOMER': 'مشتری',
    'SUPPLIER': 'تأمین‌کننده',
    'DRIVER': 'راننده',
}

OPERATION_LABELS = {
    'INBOUND_RECEIPT': 'خرید / رسید ورودی',
    'INBOUND_FREIGHT': 'کرایه حمل ورودی',
    'OUTBOUND_ISSUE': 'فروش / حواله خروج',
    'OUTBOUND_FREIGHT': 'کرایه حمل خروجی',
}

DIRECTION_LABELS = {'RECEIVABLE': 'دریافتنی', 'PAYABLE': 'پرداختنی'}
STATUS_LABELS = {'OPEN': 'باز', 'PARTIAL': 'ناقص', 'SETTLED': 'تسویه', 'CANCELLED': 'لغو'}
# [SOFT-COLOR] soft status colors (approved palette)
SOFT_STATUS_COLORS = {
    'OPEN': '#b91c1c',
    'PARTIAL': '#b45309',
    'SETTLED': '#047857',
    'CANCELLED': '#64748b',
}


def _soft_status_color(status: str) -> str:
    return SOFT_STATUS_COLORS.get(status, '#e2e8f0')

ROW_TYPE_LABELS = {'FINANCE_DOC': 'سند مالی', 'PAYMENT': 'تسویه'}


# ================================================================
# 🎨 استایل‌های مرکزی
# ================================================================
GLOBAL_STYLE = """"""


def make_kpi_card(title: str, value: str = '0', kind: str = 'info') -> tuple:
    """کارت KPI زیبا - (card, value_label)"""
    card = QFrame()
    card.setObjectName('KpiCard')
    card.setProperty('kind', kind)
    card.setMinimumHeight(72)
    card.setMaximumHeight(85)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setSpacing(4)

    title_lbl = QLabel(title)
    title_lbl.setObjectName('KpiTitle')
    title_lbl.setAlignment(Qt.AlignRight)

    value_lbl = QLabel(value)
    value_lbl.setObjectName('KpiValue')
    value_lbl.setAlignment(Qt.AlignRight)

    layout.addWidget(title_lbl)
    layout.addWidget(value_lbl)
    return card, value_lbl


def styled_button(text: str, color: str = None) -> QPushButton:
    """دکمه با رنگ استاندارد"""
    btn = QPushButton(text)
    if color:
        btn.setProperty('color', color)
    return btn


class ReportsWindow(QDialog):
    def __init__(self, db: DatabaseManager, user_data: Dict) -> None:
        super().__init__()
        self.setMinimumSize(900, 600)  # SCROLL-FIT
        self.db = db
        self.user_data = user_data
        self.finance_repository = FinanceRepository(db)
        self.report_repository = ReportRepository(db)
        self.warehouses: List[Dict] = []
        self.pallets: List[Dict] = []
        self.current_financial_report: Optional[Dict] = None
        self.current_stock_report: Optional[Dict] = None
        self.current_kardex_report: Optional[Dict] = None
        self.current_person_statement: Optional[Dict] = None
        self.current_aggregate_report: Optional[Dict] = None

        # نگهدارنده ارتباط سایدبار به استک
        self._sidebar_to_stack: Dict[int, int] = {}

        self.setWindowTitle('گزارشات مالی و انبار')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1400, 820)
        self.setMinimumSize(1200, 700)
        if False: pass

        self._build_ui()
        self._load_report_lookups()
        self.refresh_financial_report()
        self.refresh_person_summary()
        self.refresh_stock_value_report()
        self.refresh_kardex_report()
        self.refresh_aggregate_stock_report()
        self.refresh_journal_report()

    # ================================================================
    # UI اصلی
    # ================================================================
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # هدر
        header = QFrame()
        header.setObjectName('HeaderCard')
        header.setMaximumHeight(70)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)

        title = QLabel('📊  گزارشات مالی و انبار')
        title.setObjectName('HeaderTitle')
        subtitle = QLabel('گردش حساب، ارزش ریالی انبار، کاردکس، سود و زیان، هزینه‌ها و رانندگان')
        subtitle.setObjectName('HeaderSubtitle')
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        # بدنه (سایدبار + محتوا)
        body = QHBoxLayout()
        body.setSpacing(10)

        # سایدبار
        self.sidebar = QListWidget()
        self.sidebar.setObjectName('Sidebar')
        self.sidebar.setFixedWidth(230)

        # استک محتوا
        self.stack = QStackedWidget()

        # تعریف بخش‌ها
        sections = [
            ('── 💰 گزارشات مالی ──', None),
            ('📑  گزارش اسناد مالی', self._build_financial_report_tab),
            ('👥  گردش حساب اشخاص', self._build_person_statement_tab),
            ('📈  سود و زیان', self._build_pnl_report_tab),
            ('⏰  سن بدهی‌ها و مطالبات', self._build_aging_report_tab),
            ('📔  دفتر روزنامه', self._build_journal_tab),

            ('── 📦 گزارشات انبار ──', None),
            ('🏭  ارزش ریالی انبار', self._build_stock_value_tab),
            ('📋  کاردکس پالت و انبار', self._build_kardex_tab),
            ('🗂️  تجمیعی همه انبارها', self._build_aggregate_stock_tab),
            ('🔄  برگشت از خرید و فروش', self._build_return_report_tab),
            ('💤  اقلام راکد', self._build_dead_stock_tab),

            ('── 💸 هزینه‌ها ──', None),
            ('🏷️  دسته‌بندی هزینه', self._build_expense_category_tab),
            ('➕  ثبت هزینه', self._build_expense_entry_tab),
            ('📊  گزارش هزینه‌ها', self._build_expense_report_tab),

            ('── 🚚 عملیات حمل ──', None),
            ('🚛  گزارش رانندگان', self._build_driver_report_tab),
        ]

        first_selectable_row = None
        stack_index = 0

        for row_index, (text, builder) in enumerate(sections):
            item = QListWidgetItem(text)
            if builder is None:
                # عنوان دسته
                flags = item.flags()
                flags &= ~Qt.ItemIsSelectable
                flags &= ~Qt.ItemIsEnabled
                item.setFlags(flags)
                self.sidebar.addItem(item)
            else:
                self.sidebar.addItem(item)
                self.stack.addWidget(builder())
                self._sidebar_to_stack[row_index] = stack_index
                stack_index += 1
                if first_selectable_row is None:
                    first_selectable_row = row_index

        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)

        body.addWidget(self.sidebar)
        body.addWidget(self.stack, 1)
        root.addLayout(body)

        if first_selectable_row is not None:
            self.sidebar.setCurrentRow(first_selectable_row)

    def _on_sidebar_changed(self, row: int) -> None:
        if row in self._sidebar_to_stack:
            self.stack.setCurrentIndex(self._sidebar_to_stack[row])

    # ================================================================
    # 📑 تب گزارش اسناد مالی
    # ================================================================
    def _build_financial_report_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        # نوار فیلتر
        filter_bar = QFrame()
        filter_bar.setObjectName('FilterBar')
        fl = QHBoxLayout(filter_bar)
        fl.setContentsMargins(10, 8, 10, 8)

        self.fin_search_edit = QLineEdit()
        self.fin_search_edit.setPlaceholderText('🔍 جستجو در اسناد مالی...')
        self.fin_search_edit.setMinimumWidth(240)
        self.fin_search_edit.textChanged.connect(self.refresh_financial_report)

        self.fin_status_combo = QComboBox()
        self.fin_status_combo.addItem('همه وضعیت‌ها', 'ALL')
        self.fin_status_combo.addItem('باز', 'OPEN')
        self.fin_status_combo.addItem('ناقص', 'PARTIAL')
        self.fin_status_combo.addItem('تسویه', 'SETTLED')
        self.fin_status_combo.currentIndexChanged.connect(self.refresh_financial_report)

        self.fin_direction_combo = QComboBox()
        self.fin_direction_combo.addItem('همه جهت‌ها', 'ALL')
        self.fin_direction_combo.addItem('دریافتنی', 'RECEIVABLE')
        self.fin_direction_combo.addItem('پرداختنی', 'PAYABLE')
        self.fin_direction_combo.currentIndexChanged.connect(self.refresh_financial_report)

        refresh_btn = styled_button('🔄 بروزرسانی')
        refresh_btn.clicked.connect(self.refresh_financial_report)

        export_excel_btn = styled_button('📗 Excel', 'success')
        export_excel_btn.clicked.connect(self.export_financial_summary_excel)

        export_pdf_btn = styled_button('📕 PDF', 'danger')
        export_pdf_btn.clicked.connect(self.export_financial_summary_pdf)

        fl.addWidget(self.fin_search_edit, 1)
        fl.addWidget(QLabel('وضعیت:'))
        fl.addWidget(self.fin_status_combo)
        fl.addWidget(QLabel('جهت:'))
        fl.addWidget(self.fin_direction_combo)
        fl.addWidget(refresh_btn)
        fl.addWidget(export_excel_btn)
        fl.addWidget(export_pdf_btn)
        layout.addWidget(filter_bar)

        # کارت‌های KPI
        cards = QHBoxLayout()
        cards.setSpacing(8)
        c1, self.sum_total_docs = make_kpi_card('کل اسناد', '0', 'info')
        c2, self.sum_open_docs = make_kpi_card('اسناد باز', '0', 'warning')
        c3, self.sum_settled_docs = make_kpi_card('اسناد تسویه', '0', 'success')
        c4, self.sum_receivable = make_kpi_card('کل دریافتنی', '0', 'success')
        c5, self.sum_receivable_balance = make_kpi_card('مانده دریافتنی', '0', 'warning')
        c6, self.sum_payable = make_kpi_card('کل پرداختنی', '0', 'danger')
        c7, self.sum_payable_balance = make_kpi_card('مانده پرداختنی', '0', 'danger')
        for c in (c1, c2, c3, c4, c5, c6, c7):
            cards.addWidget(c)
        layout.addLayout(cards)

        # جدول
        self.fin_table = QTableWidget(0, 10)
        self.fin_table.setHorizontalHeaderLabels([
            'شناسه', 'شماره سند', 'تاریخ', 'نوع', 'جهت', 'طرف حساب',
            'مرجع عملیات', 'مبلغ کل', 'تسویه شده', 'وضعیت'
        ])
        self.fin_table.setColumnHidden(0, True)
        self.fin_table.verticalHeader().setVisible(False)
        self.fin_table.setAlternatingRowColors(True)
        self.fin_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fin_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.fin_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.fin_table)

        return tab

    # ================================================================
    # 👥 تب گردش حساب اشخاص
    # ================================================================
    def _build_person_statement_tab(self) -> QWidget:
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(10)

        # ---------- نوار جستجو (مشترک) ----------
        search_bar = QFrame()
        search_bar.setObjectName('FilterBar')
        sl = QHBoxLayout(search_bar)
        sl.setContentsMargins(10, 8, 10, 8)

        self.person_search_edit = QLineEdit()
        self.person_search_edit.setPlaceholderText('🔍 جستجو بر اساس نام، موبایل یا کد ملی...')
        self.person_search_edit.textChanged.connect(self.refresh_person_summary)

        # [RANGE] فیلتر بازه تاریخ برای گردش شخص
        self.person_date_from_edit = QDateEdit()
        self.person_date_from_edit.setCalendarPopup(True)
        self.person_date_from_edit.setDisplayFormat('yyyy-MM-dd')
        self.person_date_from_edit.setDate(QDate.currentDate().addDays(-30))
        self.person_date_to_edit = QDateEdit()
        self.person_date_to_edit.setCalendarPopup(True)
        self.person_date_to_edit.setDisplayFormat('yyyy-MM-dd')
        self.person_date_to_edit.setDate(QDate.currentDate())

        refresh_btn = styled_button('🔄 بروزرسانی')
        refresh_btn.clicked.connect(self.refresh_person_summary)

        sl.addWidget(QLabel('از:'))
        sl.addWidget(self.person_date_from_edit)
        self.person_from_jalali_lbl = QLabel('-')
        self.person_from_jalali_lbl.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
        sl.addWidget(self.person_from_jalali_lbl)
        sl.addWidget(QLabel('تا:'))
        sl.addWidget(self.person_date_to_edit)
        self.person_to_jalali_lbl = QLabel('-')
        self.person_to_jalali_lbl.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
        sl.addWidget(self.person_to_jalali_lbl)
        sl.addWidget(self.person_search_edit, 1)
        sl.addWidget(refresh_btn)
        main_layout.addWidget(search_bar)

        # ---------- تب‌ها ----------
        self.person_tabs = QTabWidget()

        # ---- تب ۱: اشخاص ----
        tab_persons = QWidget()
        persons_layout = QVBoxLayout(tab_persons)
        persons_layout.setContentsMargins(4, 4, 4, 4)
        persons_layout.setSpacing(8)

        self.person_table = QTableWidget(0, 6)
        self.person_table.setHorizontalHeaderLabels([
            'شناسه', 'شخص', 'نقش', 'مانده دریافتنی', 'مانده پرداختنی', 'تعداد چک'
        ])
        self.person_table.setColumnHidden(0, True)
        self.person_table.verticalHeader().setVisible(False)
        self.person_table.setAlternatingRowColors(True)
        self.person_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.person_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.person_table.itemSelectionChanged.connect(self._load_selected_person_statement)
        self.person_table.horizontalHeader().setStretchLastSection(True)
        persons_layout.addWidget(self.person_table)

        # ---- تب ۲: ریز گردش ----
        tab_statement = QWidget()
        st_layout = QVBoxLayout(tab_statement)
        st_layout.setContentsMargins(4, 4, 4, 4)
        st_layout.setSpacing(8)

        # خلاصه شخص انتخاب‌شده
        summary_frame = QFrame()
        summary_frame.setObjectName('FilterBar')
        sf = QHBoxLayout(summary_frame)
        sf.setContentsMargins(12, 10, 12, 10)
        sf.setSpacing(10)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        self.person_name_label = QLabel('👤  شخص انتخاب نشده')
        self.person_name_label.setObjectName('PersonName')
        self.person_mobile_label = QLabel('📱  -')
        self.person_mobile_label.setObjectName('PersonMobile')
        info_layout.addWidget(self.person_name_label)
        info_layout.addWidget(self.person_mobile_label)
        info_widget.setMinimumWidth(220)
        sf.addWidget(info_widget)

        c1, self.person_receivable_label = make_kpi_card('کل دریافتنی', '0', 'success')
        c2, self.person_payable_label = make_kpi_card('کل پرداختنی', '0', 'danger')
        c3, self.person_net_label = make_kpi_card('خالص مانده', '0', 'info')
        for c in (c1, c2, c3):
            c.setMinimumWidth(170)
            sf.addWidget(c)

        self.person_export_excel_btn = styled_button('📗 خروجی Excel', 'success')
        self.person_export_excel_btn.clicked.connect(self.export_person_statement_excel)
        self.person_export_pdf_btn = styled_button('📕 خروجی PDF', 'danger')
        self.person_export_pdf_btn.clicked.connect(self.export_person_statement_pdf)
        sf.addWidget(self.person_export_excel_btn)
        sf.addWidget(self.person_export_pdf_btn)

        st_layout.addWidget(summary_frame)

        # جدول ریز گردش (تمام‌عرض)
        self.statement_table = QTableWidget(0, 8)
        self.statement_table.setHorizontalHeaderLabels([
            'تاریخ', 'نوع ردیف', 'شماره سند', 'نوع عملیات',
            'شرح', 'بدهکار', 'بستانکار', 'مانده'
        ])
        self.statement_table.verticalHeader().setVisible(False)
        self.statement_table.setAlternatingRowColors(True)
        self.statement_table.horizontalHeader().setStretchLastSection(True)
        self.statement_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        st_layout.addWidget(self.statement_table, 1)

        self.person_tabs.addTab(tab_persons, '👥 اشخاص')
        self.person_tabs.addTab(tab_statement, '📄 ریز گردش')

        main_layout.addWidget(self.person_tabs, 1)

        # اتصال تغییر تاریخ به بارگذاری مجدد گردش
        self.person_date_from_edit.dateChanged.connect(self._reload_current_person_statement)
        self.person_date_from_edit.dateChanged.connect(self._update_person_jalali)
        self.person_date_to_edit.dateChanged.connect(self._reload_current_person_statement)
        self.person_date_to_edit.dateChanged.connect(self._update_person_jalali)
        self._update_person_jalali()

        return tab

    def _build_stock_value_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        # نوار فیلتر
        filter_bar = QFrame()
        filter_bar.setObjectName('FilterBar')
        fl = QHBoxLayout(filter_bar)
        fl.setContentsMargins(10, 8, 10, 8)

        self.warehouse_combo = QComboBox()
        self.warehouse_combo.setMinimumWidth(260)

        refresh_btn = styled_button('🔄 نمایش', 'primary')
        refresh_btn.clicked.connect(self.refresh_stock_value_report)

        self.stock_preview_button = styled_button('🌐 پیش‌نمایش Flask', 'indigo')
        self.stock_preview_button.clicked.connect(self.open_stock_value_preview)

        self.stock_excel_button = styled_button('📗 Excel', 'success')
        self.stock_excel_button.clicked.connect(self.export_stock_value_excel)

        self.stock_pdf_button = styled_button('📕 PDF', 'danger')
        self.stock_pdf_button.clicked.connect(self.export_stock_value_pdf)

        fl.addWidget(QLabel('انبار:'))
        fl.addWidget(self.warehouse_combo)
        fl.addWidget(refresh_btn)
        fl.addStretch()
        fl.addWidget(self.stock_preview_button)
        fl.addWidget(self.stock_excel_button)
        fl.addWidget(self.stock_pdf_button)
        layout.addWidget(filter_bar)

        # KPI Cards
        cards = QHBoxLayout()
        cards.setSpacing(8)

        # کارت نام انبار (متفاوت با بقیه)
        wh_card = QFrame()
        wh_card.setObjectName('KpiCard')
        wh_card.setProperty('kind', 'purple')
        wh_card.setMinimumHeight(72)
        wh_card.setMaximumHeight(85)
        wh_layout = QVBoxLayout(wh_card)
        wh_layout.setContentsMargins(12, 8, 12, 8)
        wh_title = QLabel('🏭  انبار')
        wh_title.setObjectName('KpiTitle')
        wh_title.setAlignment(Qt.AlignRight)
        self.stock_warehouse_name_label = QLabel('-')
        self.stock_warehouse_name_label.setObjectName('KpiValue')
        self.stock_warehouse_name_label.setAlignment(Qt.AlignRight)
        wh_layout.addWidget(wh_title)
        wh_layout.addWidget(self.stock_warehouse_name_label)
        cards.addWidget(wh_card, 2)

        c2, self.stock_total_qty_label = make_kpi_card('تعداد کل موجودی', '0', 'info')
        c3, self.stock_total_value_label = make_kpi_card('ارزش ریالی کل', '0', 'success')
        c4, self.stock_type_count_label = make_kpi_card('انواع پالت', '0', 'warning')
        for c in (c2, c3, c4):
            cards.addWidget(c, 1)
        layout.addLayout(cards)

        # جدول
        self.stock_table = QTableWidget(0, 12)
        self.stock_table.setHorizontalHeaderLabels([
            'ردیف', 'کد پالت', 'نام پالت', 'جنس', 'ابعاد',
            'جمع ورود', 'جمع خروج', 'موجودی',
            'ارزش ورود', 'ارزش خروج', 'ارزش فعلی', 'آخرین گردش'
        ])
        self.stock_table.verticalHeader().setVisible(False)
        self.stock_table.setAlternatingRowColors(True)
        self.stock_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.stock_table)

        return tab

    # ================================================================
    # 📋 تب کاردکس پالت و انبار
    # ================================================================
    def _build_kardex_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        # نوار فیلتر
        filter_bar = QFrame()
        filter_bar.setObjectName('FilterBar')
        fl = QHBoxLayout(filter_bar)
        fl.setContentsMargins(10, 8, 10, 8)

        self.kardex_warehouse_combo = QComboBox()
        self.kardex_warehouse_combo.setMinimumWidth(220)
        self.kardex_pallet_combo = QComboBox()
        self.kardex_pallet_combo.setMinimumWidth(220)

        refresh_btn = styled_button('🔄 نمایش', 'primary')
        refresh_btn.clicked.connect(self.refresh_kardex_report)

        preview_btn = styled_button('🌐 پیش‌نمایش Flask', 'indigo')
        preview_btn.clicked.connect(self.open_kardex_preview)

        excel_btn = styled_button('📗 Excel', 'success')
        excel_btn.clicked.connect(self.export_kardex_excel)

        pdf_btn = styled_button('📕 PDF', 'danger')
        pdf_btn.clicked.connect(self.export_kardex_pdf)

        fl.addWidget(QLabel('انبار:'))
        fl.addWidget(self.kardex_warehouse_combo)
        fl.addWidget(QLabel('پالت:'))
        fl.addWidget(self.kardex_pallet_combo)
        fl.addWidget(refresh_btn)
        fl.addStretch()
        fl.addWidget(preview_btn)
        fl.addWidget(excel_btn)
        fl.addWidget(pdf_btn)
        layout.addWidget(filter_bar)

        # KPI Cards
        cards = QHBoxLayout()
        cards.setSpacing(8)

        info_card = QFrame()
        info_card.setObjectName('KpiCard')
        info_card.setProperty('kind', 'purple')
        info_card.setMinimumHeight(72)
        info_card.setMaximumHeight(85)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_title = QLabel('🏭  انبار / پالت')
        info_title.setObjectName('KpiTitle')
        info_title.setAlignment(Qt.AlignRight)
        self.kardex_warehouse_label = QLabel('-')
        self.kardex_warehouse_label.setObjectName('KpiValue')
        self.kardex_warehouse_label.setStyleSheet('font-size: 12px;')
        self.kardex_warehouse_label.setAlignment(Qt.AlignRight)
        self.kardex_pallet_label = QLabel('همه پالت‌ها')
        self.kardex_pallet_label.setStyleSheet('color: #64748b; font-size: 10px;')
        self.kardex_pallet_label.setAlignment(Qt.AlignRight)
        info_layout.addWidget(info_title)
        info_layout.addWidget(self.kardex_warehouse_label)
        info_layout.addWidget(self.kardex_pallet_label)
        cards.addWidget(info_card, 2)

        c2, self.kardex_total_in_qty_label = make_kpi_card('جمع ورود', '0', 'success')
        c3, self.kardex_total_out_qty_label = make_kpi_card('جمع خروج', '0', 'danger')
        c4, self.kardex_current_qty_label = make_kpi_card('مانده تعدادی', '0', 'info')
        c5, self.kardex_current_value_label = make_kpi_card('مانده ریالی', '0', 'warning')
        for c in (c2, c3, c4, c5):
            cards.addWidget(c, 1)
        layout.addLayout(cards)

        # جدول
        self.kardex_table = QTableWidget(0, 14)
        self.kardex_table.setHorizontalHeaderLabels([
            'ردیف', 'تاریخ', 'نوع', 'مرجع اصلی', 'سند مرحله‌ای',
            'کد پالت', 'نام پالت', 'ورود', 'خروج', 'مانده',
            'قیمت واحد', 'مبلغ گردش', 'مانده ریالی', 'شرح'
        ])
        self.kardex_table.verticalHeader().setVisible(False)
        self.kardex_table.setAlternatingRowColors(True)
        self.kardex_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.kardex_table)

        return tab

    # ================================================================
    # 🗂️ تب تجمیعی همه انبارها
    # ================================================================
    def _build_aggregate_stock_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        # نوار فیلتر
        filter_bar = QFrame()
        filter_bar.setObjectName('FilterBar')
        fl = QHBoxLayout(filter_bar)
        fl.setContentsMargins(10, 8, 10, 8)

        title_lbl = QLabel('🗂️  گزارش تجمیعی همه انبارها')
        title_lbl.setStyleSheet(' font-size: 13px; font-weight: bold;')

        refresh_btn = styled_button('🔄 نمایش', 'primary')
        refresh_btn.clicked.connect(self.refresh_aggregate_stock_report)

        preview_btn = styled_button('🌐 پیش‌نمایش Flask', 'indigo')
        preview_btn.clicked.connect(self.open_aggregate_stock_preview)

        excel_btn = styled_button('📗 Excel', 'success')
        excel_btn.clicked.connect(self.export_aggregate_stock_excel)

        pdf_btn = styled_button('📕 PDF', 'danger')
        pdf_btn.clicked.connect(self.export_aggregate_stock_pdf)

        fl.addWidget(title_lbl)
        fl.addStretch()
        fl.addWidget(refresh_btn)
        fl.addWidget(preview_btn)
        fl.addWidget(excel_btn)
        fl.addWidget(pdf_btn)
        layout.addWidget(filter_bar)

        # KPI Cards
        cards = QHBoxLayout()
        cards.setSpacing(8)
        c1, self.aggregate_warehouse_count_label = make_kpi_card('تعداد انبارها', '0', 'purple')
        c2, self.aggregate_total_qty_label = make_kpi_card('کل موجودی', '0', 'info')
        c3, self.aggregate_total_value_label = make_kpi_card('ارزش ریالی کل', '0', 'success')
        c4, self.aggregate_pallet_type_count_label = make_kpi_card('انواع پالت', '0', 'warning')
        for c in (c1, c2, c3, c4):
            cards.addWidget(c)
        layout.addLayout(cards)

        # Splitter: انبارها و پالت‌ها
        splitter = QSplitter(Qt.Vertical)

        # جدول انبارها
        wh_group = QGroupBox('📊  خلاصه به تفکیک انبار')
        wh_layout = QVBoxLayout(wh_group)
        self.aggregate_warehouses_table = QTableWidget(0, 11)
        self.aggregate_warehouses_table.setHorizontalHeaderLabels([
            'ردیف', 'کد انبار', 'نام انبار', 'انواع پالت',
            'جمع ورود', 'جمع خروج', 'موجودی',
            'ارزش ورود', 'ارزش خروج', 'ارزش فعلی', 'آخرین گردش'
        ])
        self.aggregate_warehouses_table.verticalHeader().setVisible(False)
        self.aggregate_warehouses_table.setAlternatingRowColors(True)
        self.aggregate_warehouses_table.horizontalHeader().setStretchLastSection(True)
        wh_layout.addWidget(self.aggregate_warehouses_table)
        splitter.addWidget(wh_group)

        # جدول پالت‌ها
        pl_group = QGroupBox('📦  خلاصه پالت‌ها در همه انبارها')
        pl_layout = QVBoxLayout(pl_group)
        self.aggregate_pallets_table = QTableWidget(0, 10)
        self.aggregate_pallets_table.setHorizontalHeaderLabels([
            'ردیف', 'کد پالت', 'نام پالت', 'جنس', 'ابعاد',
            'جمع ورود', 'جمع خروج', 'موجودی', 'ارزش ریالی', 'آخرین گردش'
        ])
        self.aggregate_pallets_table.verticalHeader().setVisible(False)
        self.aggregate_pallets_table.setAlternatingRowColors(True)
        self.aggregate_pallets_table.horizontalHeader().setStretchLastSection(True)
        pl_layout.addWidget(self.aggregate_pallets_table)
        splitter.addWidget(pl_group)

        splitter.setSizes([300, 300])
        layout.addWidget(splitter, 1)

        return tab

    # ================================================================
    # تب‌های Launcher (پنجره‌های خارجی) - با یک تابع مشترک
    # ================================================================
    def _build_launcher_tab(self, icon: str, title: str, description: str,
                             button_text: str, button_color: str,
                             callback, features: list) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        # کارت اطلاعات
        info_card = QFrame()
        info_card.setObjectName('FilterBar')
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(10)

        title_lbl = QLabel(f'{icon}  {title}')
        title_lbl.setObjectName('SectionTitle')
        title_lbl.setAlignment(Qt.AlignCenter)

        desc_lbl = QLabel(description)
        desc_lbl.setObjectName('SectionDesc')
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setWordWrap(True)

        info_layout.addWidget(title_lbl)
        info_layout.addWidget(desc_lbl)
        layout.addWidget(info_card)

        # دکمه بزرگ
        open_btn = styled_button(f'{icon}  {button_text}', button_color)
        open_btn.setMinimumHeight(55)
        open_btn.setMaximumWidth(420)
        open_btn.setStyleSheet(
            open_btn.styleSheet() + 
            'QPushButton { font-size: 15px; font-weight: bold; padding: 12px 24px; }'
        )
        open_btn.clicked.connect(callback)
        layout.addWidget(open_btn, alignment=Qt.AlignCenter)

        # ویژگی‌ها
        features_group = QGroupBox('✨  امکانات این گزارش')
        features_layout = QVBoxLayout(features_group)
        features_layout.setSpacing(6)
        for feature in features:
            lbl = QLabel(f'  ✓  {feature}')
            lbl.setWordWrap(True)
            lbl.setStyleSheet(' padding: 3px; font-size: 12px;')
            features_layout.addWidget(lbl)
        layout.addWidget(features_group)
        layout.addStretch()

        return tab

    def _build_return_report_tab(self) -> QWidget:
        return self._build_launcher_tab(
            icon='🔄', title='گزارش برگشت از خرید و فروش',
            description='گزارش جامع اسناد برگشتی شامل کارت‌های آماری، لیست اسناد، ریز اقلام و نمودار روند.',
            button_text='باز کردن گزارش برگشت کالا',
            button_color='primary',
            callback=self._open_return_report,
            features=[
                'فیلتر بر اساس بازه زمانی (از تاریخ / تا تاریخ)',
                'فیلتر نوع برگشت (خرید / فروش / همه)',
                'فیلتر طرف حساب (مشتری / تأمین‌کننده)',
                'کارت‌های آماری (تعداد اسناد، مبلغ کل)',
                'نمایش ریز اقلام هر سند با کلیک روی آن',
                'نمودار روند مبلغ برگشتی بر اساس تاریخ',
                'خروجی HTML برای چاپ و آرشیو',
            ]
        )

    def _build_pnl_report_tab(self) -> QWidget:
        return self._build_launcher_tab(
            icon='📈', title='گزارش سود و زیان',
            description='محاسبه فروش خالص، بهای تمام‌شده، سود ناخالص و حاشیه سود.',
            button_text='باز کردن گزارش سود و زیان',
            button_color='success',
            callback=self._open_pnl_report,
            features=[
                'فیلتر بر اساس بازه زمانی',
                'کارت‌های فروش ناخالص، برگشت، فروش خالص',
                'کارت‌های خرید ناخالص، برگشت، خرید خالص',
                'محاسبه سود ناخالص و حاشیه سود',
                'جدول جزئیات تمامی اسناد',
                'نمودار مقایسه‌ای فروش و خرید',
                'خلاصه تحلیلی با وضعیت سودده/زیان‌ده',
            ]
        )

    def _build_aging_report_tab(self) -> QWidget:
        return self._build_launcher_tab(
            icon='⏰', title='گزارش سن بدهی‌ها و مطالبات',
            description='نمایش مانده باز هر شخص به تفکیک بازه زمانی (0-30، 31-60، 61-90، 91-180، 180+).',
            button_text='باز کردن گزارش سن بدهی‌ها',
            button_color='danger',
            callback=self._open_aging_report,
            features=[
                'فیلتر نوع گزارش (مطالبات / بدهی‌ها / جامع)',
                'انتخاب تاریخ سررسید برای محاسبه سن',
                '6 کارت آماری: جمع کل + 5 بازه سنی',
                'جدول اشخاص با مانده باز به تفکیک بازه',
                'ریز اسناد هر شخص',
                'نمودار توزیع مانده بر اساس سن',
                'تب هشدارها: شناسایی موارد بحرانی',
                'توصیه‌های مدیریتی برای هر بازه',
            ]
        )

    def _build_expense_category_tab(self) -> QWidget:
        return self._build_launcher_tab(
            icon='🏷️', title='مدیریت دسته‌بندی هزینه‌های عملیاتی',
            description='دسته‌بندی‌های مورد استفاده در فرم ثبت هزینه را مدیریت کنید.',
            button_text='باز کردن مدیریت دسته‌بندی',
            button_color='teal',
            callback=self._open_expense_category,
            features=[
                'اضافه کردن دسته‌بندی جدید با نام و رنگ',
                'ویرایش نام، توضیحات و رنگ دسته‌بندی',
                'حذف دسته‌بندی (فقط اگر استفاده نشده باشد)',
                'تغییر وضعیت فعال/غیرفعال',
            ]
        )

    def _build_expense_entry_tab(self) -> QWidget:
        return self._build_launcher_tab(
            icon='➕', title='ثبت هزینه‌های عملیاتی',
            description='هزینه‌های عملیاتی شرکت (حقوق، اجاره، حمل و...) را ثبت کنید.',
            button_text='ثبت هزینه جدید',
            button_color='warning',
            callback=self._open_expense_entry,
            features=[
                'انتخاب دسته‌بندی از لیست فعال',
                'ورود مبلغ کل و مبلغ پرداخت‌شده',
                'محاسبه خودکار مانده باز',
                'ثبت تاریخ، شماره فاکتور و توضیحات',
                'تعیین خودکار وضعیت (باز/ناقص/تسویه)',
            ]
        )

    def _build_expense_report_tab(self) -> QWidget:
        return self._build_launcher_tab(
            icon='📊', title='گزارش هزینه‌های عملیاتی',
            description='گزارش جامع هزینه‌ها با فیلترهای مختلف، نمودار توزیع، روند زمانی و خلاصه تحلیلی.',
            button_text='باز کردن گزارش هزینه‌ها',
            button_color='danger',
            callback=self._open_expense_report,
            features=[
                'فیلتر بر اساس بازه زمانی',
                'فیلتر بر اساس دسته‌بندی',
                'فیلتر بر اساس وضعیت',
                'کارت‌های آماری کامل',
                'جدول کامل هزینه‌ها',
                'نمودار توزیع بر اساس دسته‌بندی',
                'نمودار روند زمانی هزینه‌ها',
                'خلاصه تحلیلی با توصیه‌های مدیریتی',
            ]
        )

    def _build_dead_stock_tab(self) -> QWidget:
        return self._build_launcher_tab(
            icon='💤', title='گزارش اقلام راکد (Dead Stock)',
            description='نمایش پالت‌هایی که در بازه مشخصی هیچ حرکتی نداشته‌اند. شناسایی سرمایه خوابیده.',
            button_text='باز کردن گزارش اقلام راکد',
            button_color='purple',
            callback=self._open_dead_stock,
            features=[
                'فیلتر بر اساس انبار',
                'تنظیم آستانه راکد (30 تا 365 روز)',
                'انتخاب تاریخ برش برای محاسبه',
                '4 کارت آماری',
                'جدول اقلام راکد با رنگ‌بندی شدت',
                'نمودار توزیع بر اساس انبار',
                'توصیه‌های مدیریتی خودکار',
            ]
        )

    def _build_driver_report_tab(self) -> QWidget:
        return self._build_launcher_tab(
            icon='🚛', title='گزارش جامع رانندگان',
            description='نمایش تمام سفرهای راننده شامل کرایه حمل، مقدار بار و طرف حساب.',
            button_text='باز کردن گزارش رانندگان',
            button_color='purple',
            callback=self._open_driver_report,
            features=[
                'فیلتر بر اساس راننده',
                'فیلتر نوع عملیات (ورود / خروج / همه)',
                'فیلتر بازه تاریخ',
                'کارت‌های آماری کامل',
                'جدول کامل سفرها با جزئیات',
                'نمایش طرف حساب (تأمین‌کننده / مشتری)',
                'خروجی HTML و CSV',
            ]
        )

    # ================================================================
    # توابع باز کردن پنجره‌های خارجی
    # ================================================================
    def _safe_open(self, window_class, title: str) -> None:
        try:
            window = window_class(self.db, self.user_data)
            window.exec_()
        except Exception:
            import traceback
            QMessageBox.critical(self, 'خطا', f'باز کردن {title} با خطا مواجه شد:\n\n{traceback.format_exc()}')

    def _open_return_report(self) -> None:
        self._safe_open(ReturnReportWindow, 'گزارش برگشت کالا')

    def _open_pnl_report(self) -> None:
        self._safe_open(PnlReportWindow, 'گزارش سود و زیان')

    def _open_aging_report(self) -> None:
        self._safe_open(AgingReportWindow, 'گزارش سن بدهی‌ها')

    def _open_expense_category(self) -> None:
        self._safe_open(ExpenseCategoryManagerWindow, 'مدیریت دسته‌بندی هزینه')

    def _open_expense_entry(self) -> None:
        self._safe_open(ExpenseWindow, 'ثبت هزینه')

    def _open_expense_report(self) -> None:
        self._safe_open(ExpenseReportWindow, 'گزارش هزینه‌ها')

    def _open_dead_stock(self) -> None:
        self._safe_open(DeadStockWindow, 'گزارش اقلام راکد')

    def _open_driver_report(self) -> None:
        try:
            from app.ui.driver_report_window import DriverReportWindow
            window = DriverReportWindow(self.db, self.user_data)
            window.exec_()
        except Exception:
            import traceback
            QMessageBox.critical(self, 'خطا', f'باز کردن گزارش رانندگان با خطا مواجه شد:\n\n{traceback.format_exc()}')

    # ================================================================
    # بارگذاری Lookupها
    # ================================================================
    def _load_report_lookups(self) -> None:
        self.warehouses = self.report_repository.list_active_warehouses()
        self.pallets = self.report_repository.list_active_pallets()

        self.warehouse_combo.blockSignals(True)
        self.warehouse_combo.clear()
        self.warehouse_combo.addItem('همه انبارها', None)

        self.kardex_warehouse_combo.blockSignals(True)
        self.kardex_warehouse_combo.clear()
        self.kardex_warehouse_combo.addItem('انتخاب انبار', None)

        for item in self.warehouses:
            label = f"{item['code']} | {item['name']}"
            self.warehouse_combo.addItem(label, item['id'])
            self.kardex_warehouse_combo.addItem(label, item['id'])

        self.warehouse_combo.blockSignals(False)
        self.kardex_warehouse_combo.blockSignals(False)

        self.kardex_pallet_combo.clear()
        self.kardex_pallet_combo.addItem('همه پالت‌ها', None)
        for item in self.pallets:
            self.kardex_pallet_combo.addItem(f"{item['code']} | {item['name']}", item['id'])

        self.warehouse_combo.currentIndexChanged.connect(self.refresh_stock_value_report)
        self.kardex_warehouse_combo.currentIndexChanged.connect(self.refresh_kardex_report)
        self.kardex_pallet_combo.currentIndexChanged.connect(self.refresh_kardex_report)

        if self.warehouse_combo.count() > 1:
            self.warehouse_combo.setCurrentIndex(1)
        if self.kardex_warehouse_combo.count() > 1:
            self.kardex_warehouse_combo.setCurrentIndex(1)

    def _money(self, value: int) -> str:
        return f'{int(value):,} ریال'

    # ================================================================
    # منطق گزارش مالی
    # ================================================================
    def _summarize_financial_rows(self, rows: List[Dict]) -> Dict[str, int]:
        receivable_total = sum(int(row.get('total_amount') or 0) for row in rows if row.get('direction') == 'RECEIVABLE' and row.get('status') != 'CANCELLED')
        receivable_settled = sum(int(row.get('settled_amount') or 0) for row in rows if row.get('direction') == 'RECEIVABLE' and row.get('status') != 'CANCELLED')
        payable_total = sum(int(row.get('total_amount') or 0) for row in rows if row.get('direction') == 'PAYABLE' and row.get('status') != 'CANCELLED')
        payable_settled = sum(int(row.get('settled_amount') or 0) for row in rows if row.get('direction') == 'PAYABLE' and row.get('status') != 'CANCELLED')
        open_docs = sum(1 for row in rows if row.get('status') in {'OPEN', 'PARTIAL'})
        settled_docs = sum(1 for row in rows if row.get('status') == 'SETTLED')

        return {
            'receivable_total': receivable_total,
            'receivable_settled': receivable_settled,
            'receivable_balance': receivable_total - receivable_settled,
            'payable_total': payable_total,
            'payable_settled': payable_settled,
            'payable_balance': payable_total - payable_settled,
            'open_docs': open_docs,
            'settled_docs': settled_docs,
            'total_docs': len(rows),
        }

    def _require_financial_report(self) -> Optional[Dict]:
        if self.current_financial_report is None:
            self.refresh_financial_report()
        if self.current_financial_report is None:
            QMessageBox.warning(self, 'گزارش مالی', 'گزارش مالی برای خروجی در دسترس نیست.')
            return None
        return self.current_financial_report

    def refresh_financial_report(self) -> None:
        rows = self.finance_repository.list_financial_documents(
            search_text=self.fin_search_edit.text(),
            status_filter=self.fin_status_combo.currentData(),
            direction_filter=self.fin_direction_combo.currentData(),
        )

        summary = self._summarize_financial_rows(rows)
        self.current_financial_report = {
            'summary': summary,
            'items': [
                {
                    **row,
                    'reference_label': row.get('receipt_no') or row.get('issue_no') or row.get('inbound_reference_no') or row.get('outbound_reference_no') or '-',
                    'finance_date_label': (lambda fd: (lambda j: f"{j} | {fd}" if j != fd else fd)(jalali_date_display_from_iso(fd) if fd else '-'))(str(row.get('finance_date') or '')),
                    'operation_type_label': OPERATION_LABELS.get(row['operation_type'], row['operation_type']),
                    'direction_label': DIRECTION_LABELS.get(row['direction'], row['direction']),
                    'status_label': STATUS_LABELS.get(row['status'], row['status']),
                    'remaining_amount': int(row.get('total_amount') or 0) - int(row.get('settled_amount') or 0),
                }
                for row in rows
            ],
        }

        self.sum_total_docs.setText(str(summary['total_docs']))
        self.sum_open_docs.setText(str(summary['open_docs']))
        self.sum_settled_docs.setText(str(summary['settled_docs']))
        self.sum_receivable.setText(self._money(summary['receivable_total']))
        self.sum_receivable_balance.setText(self._money(summary['receivable_balance']))
        self.sum_payable.setText(self._money(summary['payable_total']))
        self.sum_payable_balance.setText(self._money(summary['payable_balance']))

        self.fin_table.setRowCount(len(rows))
        for row_index, row in enumerate(self.current_financial_report['items']):
            values = [
                str(row['id']), row['finance_no'], row.get('finance_date_label') or '-',
                row['operation_type_label'], row['direction_label'],
                row.get('counterparty_name') or '-', row['reference_label'],
                self._money(int(row.get('total_amount') or 0)),
                self._money(int(row.get('settled_amount') or 0)),
                row['status_label'],
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                # [SOFT-COLOR] status column (last) with soft color
                if col == 9:
                    item.setForeground(QColor(_soft_status_color(row.get('status'))))
                self.fin_table.setItem(row_index, col, item)
        self.fin_table.resizeColumnsToContents()

    def export_financial_summary_excel(self) -> None:
        report = self._require_financial_report()
        if report is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره Excel اسناد مالی', 'financial-summary.xlsx', 'Excel Files (*.xlsx)')
        if not file_path:
            return
        try:
            saved_path = export_financial_summary_to_excel(report, file_path)
            QMessageBox.information(self, 'خروجی Excel', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا در تولید Excel:\n{exc}')

    def export_financial_summary_pdf(self) -> None:
        report = self._require_financial_report()
        if report is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره PDF اسناد مالی', 'financial-summary.pdf', 'PDF Files (*.pdf)')
        if not file_path:
            return
        try:
            saved_path = export_financial_summary_to_pdf(report, file_path)
            QMessageBox.information(self, 'خروجی PDF', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا در تولید PDF:\n{exc}')

    # ================================================================
    # منطق گردش حساب اشخاص
    # ================================================================
    def _update_person_jalali(self):
        try:
            self.person_from_jalali_lbl.setText(jalali_date_display_from_iso(self.person_date_from_edit.date().toString('yyyy-MM-dd')))
            self.person_to_jalali_lbl.setText(jalali_date_display_from_iso(self.person_date_to_edit.date().toString('yyyy-MM-dd')))
        except Exception:
            pass

    def refresh_person_summary(self) -> None:
        rows = self.finance_repository.list_person_financial_summaries(self.person_search_edit.text())

        # [CHECKCOUNT] تعداد چک هر شخص
        check_count_map = {}
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                for cr in conn.execute(
                    "SELECT fd.counterparty_person_id AS pid, COUNT(*) AS c "
                    "FROM payment_entries pe "
                    "JOIN payment_methods pm ON pm.id = pe.payment_method_id "
                    "JOIN financial_documents fd ON fd.id = pe.financial_document_id "
                    "WHERE pm.code = 'CHECK' "
                    "GROUP BY fd.counterparty_person_id"
                ).fetchall():
                    check_count_map[int(cr[0])] = int(cr[1])
        except Exception:
            pass
        self.person_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            full_name = f"{row['first_name']} {row['last_name']}".strip()
            roles = '، '.join(ROLE_LABELS.get(role, role) for role in row.get('roles', [])) or '-'
            check_count = check_count_map.get(int(row['id']), 0)
            values = [
                str(row['id']), full_name, roles,
                self._money(int(row['receivable_balance'])),
                self._money(int(row['payable_balance'])),
                str(check_count),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.person_table.setItem(row_index, col, item)
        self.person_table.resizeColumnsToContents()
        if rows and self.person_table.currentRow() < 0:
            self.person_table.selectRow(0)
        if not rows:
            self._clear_person_statement()

    def _clear_person_statement(self) -> None:
        self.current_person_statement = None
        self.person_name_label.setText('👤  شخص انتخاب نشده')
        self.person_mobile_label.setText('📱  -')
        self.person_receivable_label.setText('0')
        self.person_payable_label.setText('0')
        self.person_net_label.setText('0')
        self.statement_table.setRowCount(0)

    def _load_selected_person_statement(self) -> None:
        row = self.person_table.currentRow()
        if row < 0:
            return
        item = self.person_table.item(row, 0)
        if not item:
            return
        statement = self.finance_repository.get_person_statement(int(item.text()))
        self.current_person_statement = statement
        person = statement['person']
        summary = statement['summary']
        self.person_name_label.setText(f"👤  {person['first_name']} {person['last_name']}")
        self.person_mobile_label.setText(f"📱  {person.get('mobile') or '-'}")
        self.person_receivable_label.setText(self._money(int(summary['receivable_total'])))
        self.person_payable_label.setText(self._money(int(summary['payable_total'])))
        self.person_net_label.setText(self._money(int(summary['net_balance'])))

        rows: List[Dict] = statement['rows']

        # [RANGE] فیلتر بازه تاریخ
        date_from = self.person_date_from_edit.date().toString('yyyy-MM-dd')
        date_to = self.person_date_to_edit.date().toString('yyyy-MM-dd')
        filtered_rows = []
        for data in rows:
            d = str(data.get('event_date') or '')
            if d and d < date_from:
                continue
            if d and d > date_to:
                continue
            filtered_rows.append(data)

        self.statement_table.setRowCount(len(filtered_rows))
        for row_index, data in enumerate(filtered_rows):
            running = int(data['running_balance'])
            running_text = f"{self._money(abs(running))} {'بدهکار' if running >= 0 else 'بستانکار'}"
            event_date = str(data.get('event_date') or '-')
            event_jalali = jalali_date_display_from_iso(event_date) if event_date and event_date != '-' else '-'
            date_cell = f"{event_jalali} | {event_date}" if event_jalali != event_date else event_date
            values = [
                date_cell, ROW_TYPE_LABELS.get(data['row_type'], data['row_type']),
                data['reference_no'], OPERATION_LABELS.get(data['operation_type'], data['operation_type']),
                data.get('description') or '-',
                self._money(int(data['debit_amount'])) if int(data['debit_amount']) else '-',
                self._money(int(data['credit_amount'])) if int(data['credit_amount']) else '-',
                running_text,
            ]
            for col, value in enumerate(values):
                item_cell = QTableWidgetItem(str(value))
                item_cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                # [SOFT-COLOR] direction: debit = very soft red, credit = very soft blue
                if col == 5 and value != '-':
                    item_cell.setForeground(QColor('#fca5a5'))
                elif col == 6 and value != '-':
                    item_cell.setForeground(QColor('#93c5fd'))
                self.statement_table.setItem(row_index, col, item_cell)
        self.statement_table.resizeColumnsToContents()




        # [TABS] رفتن به تب ریز گردش بعد از انتخاب شخص
        if hasattr(self, 'person_tabs'):
            self.person_tabs.setCurrentIndex(1)
    def _reload_current_person_statement(self) -> None:
        """بارگذاری مجدد گردش شخص جاری هنگام تغییر بازه تاریخ"""
        if self.person_table.currentRow() >= 0:
            self._load_selected_person_statement()

    def _require_selected_person_statement(self) -> Optional[Dict]:
        if self.current_person_statement is None:
            row = self.person_table.currentRow()
            if row < 0:
                QMessageBox.warning(self, 'گردش حساب اشخاص', 'ابتدا یک شخص را از جدول انتخاب کنید.')
                return None
            item = self.person_table.item(row, 0)
            if not item:
                return None
            self.current_person_statement = self.finance_repository.get_person_statement(int(item.text()))
        return self.current_person_statement

    def export_person_statement_excel(self) -> None:
        statement = self._require_selected_person_statement()
        if statement is None:
            return
        person = statement['person']
        filename = f"{person['first_name']}_{person['last_name']}_statement.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره Excel گردش حساب', filename, 'Excel Files (*.xlsx)')
        if not file_path:
            return
        try:
            saved_path = export_person_statement_to_excel(statement, file_path)
            QMessageBox.information(self, 'خروجی Excel', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا در تولید Excel:\n{exc}')

    def export_person_statement_pdf(self) -> None:
        statement = self._require_selected_person_statement()
        if statement is None:
            return
        person = statement['person']
        filename = f"{person['first_name']}_{person['last_name']}_statement.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره PDF گردش حساب', filename, 'PDF Files (*.pdf)')
        if not file_path:
            return
        try:
            saved_path = export_person_statement_to_pdf(statement, file_path)
            QMessageBox.information(self, 'خروجی PDF', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا در تولید PDF:\n{exc}')

    # ================================================================
    # منطق ارزش ریالی انبار
    # ================================================================


    def _fill_stock_table(self, rows) -> None:
        """پر کردن جدول ارزش انبار از لیست آیتم‌ها"""
        self.stock_table.setRowCount(len(rows))
        for row_index, item in enumerate(rows):
            dimensions = item.get('dimensions') or "{} × {} × {}".format(
                item.get('length_cm') or 0, item.get('width_cm') or 0, item.get('height_cm') or 0)
            values = [
                str(row_index + 1), item.get('pallet_code') or '-',
                item.get('pallet_name') or '-', item.get('material_type') or '-',
                dimensions,
                f"{int(item.get('total_in_qty') or 0):,}",
                f"{int(item.get('total_out_qty') or 0):,}",
                f"{int(item.get('current_qty') or 0):,}",
                self._money(int(item.get('total_in_value') or 0)),
                self._money(int(item.get('total_out_value') or 0)),
                self._money(int(item.get('current_value') or 0)),
                jalali_date_display_from_iso(str(item['last_transaction_date'])[:10]) if item.get('last_transaction_date') else '-',
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.stock_table.setItem(row_index, col, cell)
        self.stock_table.resizeColumnsToContents()

    def refresh_stock_value_report(self) -> None:
        warehouse_id = self.warehouse_combo.currentData()
        if not warehouse_id:
            # [ALL] همه انبارها - همه پالت‌ها (از جمله جعبه‌های تولیدی)
            try:
                agg = self.report_repository.get_all_warehouses_stock_value_report()
                items = agg.get('pallets', [])
                total_qty = int(agg.get('summary', {}).get('total_qty', 0) or 0)
                total_value = int(agg.get('summary', {}).get('total_value', 0) or 0)
                type_count = int(agg.get('summary', {}).get('pallet_type_count', 0) or 0)
                self.current_stock_report = {
                    'warehouse': {'id': None, 'code': 'ALL', 'name': 'همه انبارها'},
                    'items': items,
                    'summary': {'total_qty': total_qty, 'total_value': total_value,
                                'pallet_type_count': type_count},
                }
                self.stock_warehouse_name_label.setText('همه انبارها')
                self.stock_total_qty_label.setText(f"{total_qty:,} عدد")
                self.stock_total_value_label.setText(self._money(total_value))
                self.stock_type_count_label.setText(str(type_count))
                self._fill_stock_table(items)
                return
            except Exception:
                self.current_stock_report = None
                self.stock_table.setRowCount(0)
                return

        try:
            report = self.report_repository.get_warehouse_stock_value_report(int(warehouse_id))
        except Exception:
            self.current_stock_report = None
            self.stock_table.setRowCount(0)
            return

        self.current_stock_report = report
        self.stock_warehouse_name_label.setText(report['warehouse']['name'])
        self.stock_total_qty_label.setText(f"{int(report['summary']['total_qty']):,} عدد")
        self.stock_total_value_label.setText(self._money(int(report['summary']['total_value'])))
        self.stock_type_count_label.setText(str(report['summary']['pallet_type_count']))

        rows = report['items']
        self.stock_table.setRowCount(len(rows))
        for row_index, item in enumerate(rows):
            values = [
                str(row_index + 1), item['pallet_code'], item['pallet_name'], item['material_type'], item['dimensions'],
                f"{int(item['total_in_qty']):,}", f"{int(item['total_out_qty']):,}", f"{int(item['current_qty']):,}",
                self._money(int(item['total_in_value'])), self._money(int(item['total_out_value'])), self._money(int(item['current_value'])),
                jalali_date_display_from_iso(str(item['last_transaction_date'])[:10]) if item.get('last_transaction_date') else '-',
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.stock_table.setItem(row_index, col, cell)
        self.stock_table.resizeColumnsToContents()

    def _require_selected_stock_report(self) -> Optional[Dict]:
        if not self.warehouse_combo.currentData():
            QMessageBox.warning(self, 'گزارش انبار', 'ابتدا یک انبار را انتخاب کنید.')
            return None
        if self.current_stock_report is None:
            self.refresh_stock_value_report()
        if self.current_stock_report is None:
            QMessageBox.warning(self, 'گزارش انبار', 'تهیه گزارش ممکن نشد.')
            return None
        return self.current_stock_report

    def open_stock_value_preview(self) -> None:
        report = self._require_selected_stock_report()
        if report is None:
            return
        try:
            from app.reporting.report_server import open_stock_value_report
            url = open_stock_value_report(self.db.db_path, int(report['warehouse']['id']))
            QMessageBox.information(self, 'پیش‌نمایش', f'گزارش در مرورگر باز شد:\n{url}')
        except RuntimeError as exc:
            QMessageBox.warning(self, 'پیش‌نیاز Flask', str(exc))
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا:\n{exc}')

    def export_stock_value_excel(self) -> None:
        report = self._require_selected_stock_report()
        if report is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره Excel', f"{report['warehouse']['code']}-stock-value.xlsx", 'Excel Files (*.xlsx)')
        if not file_path:
            return
        try:
            saved_path = export_stock_value_to_excel(report, file_path)
            QMessageBox.information(self, 'خروجی Excel', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا در تولید Excel:\n{exc}')

    def export_stock_value_pdf(self) -> None:
        report = self._require_selected_stock_report()
        if report is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره PDF', f"{report['warehouse']['code']}-stock-value.pdf", 'PDF Files (*.pdf)')
        if not file_path:
            return
        try:
            saved_path = export_stock_value_to_pdf(report, file_path)
            QMessageBox.information(self, 'خروجی PDF', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا در تولید PDF:\n{exc}')

    # ================================================================
    # منطق کاردکس
    # ================================================================
    def refresh_kardex_report(self) -> None:
        warehouse_id = self.kardex_warehouse_combo.currentData()
        pallet_id = self.kardex_pallet_combo.currentData()

        if not warehouse_id:
            self.current_kardex_report = None
            self.kardex_warehouse_label.setText('-')
            self.kardex_pallet_label.setText('همه پالت‌ها')
            self.kardex_total_in_qty_label.setText('0')
            self.kardex_total_out_qty_label.setText('0')
            self.kardex_current_qty_label.setText('0')
            self.kardex_current_value_label.setText('0')
            self.kardex_table.setRowCount(0)
            return

        try:
            report = self.report_repository.get_inventory_kardex_report(
                int(warehouse_id), int(pallet_id) if pallet_id else None
            )
        except Exception:
            self.current_kardex_report = None
            self.kardex_table.setRowCount(0)
            return

        self.current_kardex_report = report
        self.kardex_warehouse_label.setText(report['warehouse']['name'])
        self.kardex_pallet_label.setText(report['pallet']['name'] if report.get('pallet') else 'همه پالت‌ها')
        self.kardex_total_in_qty_label.setText(f"{int(report['summary']['total_in_qty']):,}")
        self.kardex_total_out_qty_label.setText(f"{int(report['summary']['total_out_qty']):,}")
        self.kardex_current_qty_label.setText(f"{int(report['summary']['current_qty']):,}")
        self.kardex_current_value_label.setText(self._money(int(report['summary']['current_value'])))

        rows = report['items']
        self.kardex_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            description = item.get('description') or ''
            running_value = item.get('running_value') or 0
            running_qty = item.get('running_qty') or 0
            unit_price = item.get('unit_price') or 0
            qty_out = int(item.get('qty_out') or 0)
            qty_in = int(item.get('qty_in') or 0)
            pallet_name = item.get('pallet_name') or ''
            pallet_code = item.get('pallet_code') or ''
            reference_no = item.get('reference_no') or ''
            main_reference = item.get('main_reference_no') or ''
            if item.get('transaction_type') == 'OPENING':
                trans_type = 'افتتاحیه'
            elif item.get('transaction_type') == 'IN':
                trans_type = 'ورود'
            else:
                trans_type = 'خروج'
            trans_date = item.get('transaction_date') or ''
            row_no = item.get('row_no') or ''

            delta_value = int(item.get('total_price') or 0)
            if item.get('transaction_type') != 'IN':
                delta_value = -delta_value

            vals = (
                str(row_no), trans_date, trans_type, main_reference, reference_no,
                pallet_code, pallet_name, f"{qty_in:,}", f"{qty_out:,}", f"{running_qty:,}",
                f"{int(unit_price):,}", self._money(delta_value), self._money(running_value), description,
            )

            for col, cell in enumerate(vals):
                table_item = QTableWidgetItem(str(cell))
                table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                # رنگ‌بندی ظریف
                if item.get('transaction_type') == 'OPENING':
                    table_item.setBackground(QColor(30, 64, 90))    # آبی تیره
                    table_item.setForeground(QColor(147, 197, 253)) # آبی روشن
                elif item.get('transaction_type') == 'IN':
                    table_item.setBackground(QColor(30, 60, 45))    # سبز تیره
                    table_item.setForeground(QColor(134, 239, 172)) # سبز روشن
                else:
                    table_item.setBackground(QColor(60, 30, 30))    # قرمز تیره
                    table_item.setForeground(QColor(252, 165, 165)) # قرمز روشن
                self.kardex_table.setItem(row, col, table_item)

        self.kardex_table.resizeColumnsToContents()

    def _require_selected_kardex_report(self) -> Optional[Dict]:
        if not self.kardex_warehouse_combo.currentData():
            QMessageBox.warning(self, 'گزارش کاردکس', 'ابتدا یک انبار را انتخاب کنید.')
            return None
        if self.current_kardex_report is None:
            self.refresh_kardex_report()
        if self.current_kardex_report is None:
            QMessageBox.warning(self, 'گزارش کاردکس', 'تهیه کاردکس ممکن نشد.')
            return None
        return self.current_kardex_report

    def open_kardex_preview(self) -> None:
        report = self._require_selected_kardex_report()
        if report is None:
            return
        try:
            from app.reporting.report_server import open_kardex_report
            pallet_id = report['pallet']['id'] if report.get('pallet') else None
            url = open_kardex_report(self.db.db_path, int(report['warehouse']['id']), int(pallet_id) if pallet_id else None)
            QMessageBox.information(self, 'پیش‌نمایش', f'گزارش در مرورگر باز شد:\n{url}')
        except RuntimeError as exc:
            QMessageBox.warning(self, 'پیش‌نیاز Flask', str(exc))
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا:\n{exc}')

    def export_kardex_excel(self) -> None:
        report = self._require_selected_kardex_report()
        if report is None:
            return
        pallet_part = report['pallet']['code'] if report.get('pallet') else 'ALL'
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره Excel', f"{report['warehouse']['code']}-kardex-{pallet_part}.xlsx", 'Excel Files (*.xlsx)')
        if not file_path:
            return
        try:
            saved_path = export_kardex_to_excel(report, file_path)
            QMessageBox.information(self, 'خروجی Excel', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا:\n{exc}')

    def export_kardex_pdf(self) -> None:
        report = self._require_selected_kardex_report()
        if report is None:
            return
        pallet_part = report['pallet']['code'] if report.get('pallet') else 'ALL'
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره PDF', f"{report['warehouse']['code']}-kardex-{pallet_part}.pdf", 'PDF Files (*.pdf)')
        if not file_path:
            return
        try:
            saved_path = export_kardex_to_pdf(report, file_path)
            QMessageBox.information(self, 'خروجی PDF', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا:\n{exc}')

    # ================================================================
    # منطق گزارش تجمیعی
    # ================================================================
    def refresh_aggregate_stock_report(self) -> None:
        try:
            report = self.report_repository.get_all_warehouses_stock_value_report()
        except Exception:
            self.current_aggregate_report = None
            self.aggregate_warehouse_count_label.setText('0')
            self.aggregate_total_qty_label.setText('0')
            self.aggregate_total_value_label.setText('0')
            self.aggregate_pallet_type_count_label.setText('0')
            self.aggregate_warehouses_table.setRowCount(0)
            self.aggregate_pallets_table.setRowCount(0)
            return

        self.current_aggregate_report = report
        self.aggregate_warehouse_count_label.setText(str(report['summary']['warehouse_count']))
        self.aggregate_total_qty_label.setText(f"{int(report['summary']['total_qty']):,}")
        self.aggregate_total_value_label.setText(self._money(int(report['summary']['total_value'])))
        self.aggregate_pallet_type_count_label.setText(str(report['summary']['pallet_type_count']))

        self.aggregate_warehouses_table.setRowCount(len(report['warehouses']))
        for row_index, item in enumerate(report['warehouses']):
            values = [
                str(row_index + 1), item['code'], item['name'], str(int(item['pallet_type_count'] or 0)),
                f"{int(item['total_in_qty']):,}", f"{int(item['total_out_qty']):,}", f"{int(item['current_qty']):,}",
                self._money(int(item['total_in_value'])), self._money(int(item['total_out_value'])), self._money(int(item['current_value'])),
                jalali_date_display_from_iso(str(item['last_transaction_date'])[:10]) if item.get('last_transaction_date') else '-',
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.aggregate_warehouses_table.setItem(row_index, col, cell)
        self.aggregate_warehouses_table.resizeColumnsToContents()

        self.aggregate_pallets_table.setRowCount(len(report['pallets']))
        for row_index, item in enumerate(report['pallets']):
            values = [
                str(row_index + 1), item['pallet_code'], item['pallet_name'], item['material_type'], item['dimensions'],
                f"{int(item['total_in_qty']):,}", f"{int(item['total_out_qty']):,}", f"{int(item['current_qty']):,}",
                self._money(int(item['current_value'])), jalali_date_display_from_iso(str(item['last_transaction_date'])[:10]) if item.get('last_transaction_date') else '-',
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.aggregate_pallets_table.setItem(row_index, col, cell)
        self.aggregate_pallets_table.resizeColumnsToContents()

    # ================================================================
    # 📔 تب دفتر روزنامه
    # ================================================================
    def _build_journal_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        filter_bar = QFrame(); filter_bar.setObjectName('FilterBar')
        fl = QHBoxLayout(filter_bar); fl.setContentsMargins(10, 8, 10, 8)

        self.journal_from_edit = QDateEdit(); self.journal_from_edit.setCalendarPopup(True)
        self.journal_from_edit.setDisplayFormat('yyyy-MM-dd'); self.journal_from_edit.setDate(QDate.currentDate().addDays(-30))
        self.journal_to_edit = QDateEdit(); self.journal_to_edit.setCalendarPopup(True)
        self.journal_to_edit.setDisplayFormat('yyyy-MM-dd'); self.journal_to_edit.setDate(QDate.currentDate())
        self.journal_search_edit = QLineEdit(); self.journal_search_edit.setPlaceholderText('🔍 جستجو در دفتر روزنامه...')
        refresh_btn = styled_button('🔄 نمایش', 'primary'); refresh_btn.clicked.connect(self.refresh_journal_report)

        fl.addWidget(QLabel('از:')); fl.addWidget(self.journal_from_edit)
        fl.addWidget(QLabel('تا:')); fl.addWidget(self.journal_to_edit)
        fl.addWidget(self.journal_search_edit, 1)
        fl.addWidget(refresh_btn)
        layout.addWidget(filter_bar)

        cards = QHBoxLayout(); cards.setSpacing(8)
        c1, self.journal_count_label = make_kpi_card('تعداد اسناد', '0', 'info')
        c2, self.journal_debit_label = make_kpi_card('جمع بدهکار', '0', 'success')
        c3, self.journal_credit_label = make_kpi_card('جمع بستانکار', '0', 'danger')
        for c in (c1, c2, c3): cards.addWidget(c)
        layout.addLayout(cards)

        self.journal_table = QTableWidget(0, 8)
        self.journal_table.setHorizontalHeaderLabels([
            'شماره سند', 'تاریخ', 'مرجع', 'شرح سند', 'ردیف', 'حساب', 'بدهکار', 'بستانکار'
        ])
        self.journal_table.verticalHeader().setVisible(False)
        self.journal_table.setAlternatingRowColors(True)
        self.journal_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.journal_table)
        return tab

    def refresh_journal_report(self) -> None:
        try:
            report = self.report_repository.get_journal_report(
                self.journal_from_edit.date().toString('yyyy-MM-dd'),
                self.journal_to_edit.date().toString('yyyy-MM-dd'),
                self.journal_search_edit.text(),
            )
        except Exception:
            self.journal_table.setRowCount(0)
            return

        self.journal_count_label.setText(str(report['summary']['count']))
        self.journal_debit_label.setText(self._money(report['summary']['total_debit']))
        self.journal_credit_label.setText(self._money(report['summary']['total_credit']))

        rows = []
        for e in report['entries']:
            date_lbl = jalali_date_display_from_iso(e['entry_date']) if e['entry_date'] else '-'
            for L in e['lines']:
                rows.append((e['entry_no'], date_lbl, e['reference_type'] or '-', e['description'] or '-',
                             L['line_no'], f"{L['account_code']} | {L['account_name']}", L['debit'], L['credit']))

        self.journal_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r[0], r[1], r[2], r[3], str(r[4]), r[5],
                    self._money(r[6]) if r[6] else '-', self._money(r[7]) if r[7] else '-']
            for col, v in enumerate(vals):
                cell = QTableWidgetItem(str(v)); cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.journal_table.setItem(i, col, cell)
        self.journal_table.resizeColumnsToContents()


    def _require_aggregate_report(self) -> Optional[Dict]:
        if self.current_aggregate_report is None:
            self.refresh_aggregate_stock_report()
        if self.current_aggregate_report is None:
            QMessageBox.warning(self, 'گزارش تجمیعی', 'تهیه گزارش ممکن نشد.')
            return None
        return self.current_aggregate_report

    def open_aggregate_stock_preview(self) -> None:
        report = self._require_aggregate_report()
        if report is None:
            return
        try:
            from app.reporting.report_server import open_aggregate_stock_report
            url = open_aggregate_stock_report(self.db.db_path)
            QMessageBox.information(self, 'پیش‌نمایش', f'گزارش در مرورگر باز شد:\n{url}')
        except RuntimeError as exc:
            QMessageBox.warning(self, 'پیش‌نیاز Flask', str(exc))
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا:\n{exc}')

    def export_aggregate_stock_excel(self) -> None:
        report = self._require_aggregate_report()
        if report is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره Excel تجمیعی', 'all-warehouses-summary.xlsx', 'Excel Files (*.xlsx)')
        if not file_path:
            return
        try:
            saved_path = export_aggregate_stock_to_excel(report, file_path)
            QMessageBox.information(self, 'خروجی Excel', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا:\n{exc}')

    def export_aggregate_stock_pdf(self) -> None:
        report = self._require_aggregate_report()
        if report is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره PDF تجمیعی', 'all-warehouses-summary.pdf', 'PDF Files (*.pdf)')
        if not file_path:
            return
        try:
            saved_path = export_aggregate_stock_to_pdf(report, file_path)
            QMessageBox.information(self, 'خروجی PDF', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'خطا:\n{exc}')