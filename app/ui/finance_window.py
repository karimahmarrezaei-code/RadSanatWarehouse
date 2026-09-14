# -*- coding: utf-8 -*-
"""
Finance Manager Window - نسخه تب‌بندی‌شده و زیبا
سه تب: لیست اسناد | جزئیات | ثبت تسویه

⚠️ نسخه اصلاح‌شده (بازبینی ۱۴۰۵/۰۵/۱۱):
  [C1]  رفع باگ بحرانی: _load_treasury_accounts از جدول treasury_accounts می‌خواند
        (قبلاً از cash_accounts می‌خواند که دیگر وجود ندارد → «حساب فعال نیست»)
  [REMAIN] ماندهٔ درست (کل − تسویه − چک PENDING) هم در لیست اسناد و هم در تب تسویه: remaining = total − settled − چک‌های PENDING
        (قبلاً فقط total − settled بود؛ اگر چک در انتظار داشتید، بیش از حد تسویه می‌شد)
  [CANCEL] سند ابطال‌شده → فرم تسویه غیرفعال + بنر قرمز «این سند ابطال شده است»
  [BANK]  افزودن «بانک طرف مقابل» که از bank_accounts شخص پر می‌شود و فیلدهای چک را خودکار پر می‌کند
  [JALALI] نمایش تاریخ شمسی سررسید در فرم تسویه
  [CHECKCOUNT] ستون «تعداد چک» در لیست اسناد
  [FIX]   تعمیر کامل تخریب‌های کپی-پیست (سینتکس): __init__، _build_ui، self.search_edit، < و ...
"""

from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QTabWidget, QWidget, QDateEdit, QHeaderView,
)

from app.ui.theme_colors import txt as _tc_txt
from app.core.database import DatabaseManager
from app.core.validators import ValidationError
from app.core.jalali import jalali_date_display_from_iso
from app.repositories.finance_repository import FinanceRepository
from app.ui.checks_window import ChecksManagementWindow
from app.ui.treasury_window import TreasuryManagementWindow


OPERATION_LABELS = {
    'INBOUND_RECEIPT': 'خرید / رسید ورودی',
    'INBOUND_FREIGHT': 'کرایه حمل ورودی',
    'OUTBOUND_ISSUE': 'فروش / حواله خروج',
    'OUTBOUND_FREIGHT': 'کرایه حمل خروجی',
}

DIRECTION_LABELS = {'RECEIVABLE': 'دریافتنی', 'PAYABLE': 'پرداختنی'}
STATUS_LABELS = {'OPEN': 'باز', 'PARTIAL': 'ناقص', 'SETTLED': 'تسویه', 'CANCELLED': 'لغو'}

STATUS_COLORS = {
    'OPEN': '#b91c1c',
    'PARTIAL': '#b45309',
    'SETTLED': '#047857',
    'CANCELLED': '#64748b',
}


# ── تابع تشخیص نوع سند از پیشوند شماره ────────────────────────────
def _operation_label_from_finance_no(finance_no: str, operation_type: str) -> str:
    if (finance_no or '').startswith('PAY-'):  # pay_account_added
        return 'پرداخت پرسنل'
    fn = (finance_no or '').strip()
    if fn.startswith('WP-'):
        return 'فروش ضایعات'
    if fn.startswith('BS-'):
        return 'برگشت از فروش'
    if fn.startswith('BR-'):
        return 'برگشت از خرید'
    if fn.startswith('RS-') or fn.startswith('SR-'):
        return 'برگشت از فروش'
    if fn.startswith('RB-') or fn.startswith('PR-'):
        return 'برگشت از خرید'
    return OPERATION_LABELS.get(operation_type, operation_type or '-')


class FinanceManagerWindow(QDialog):

    data_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.repository = FinanceRepository(db)
        permissions = set(user_data.get('permissions', []) or [])
        self.can_manage = 'finance.manage' in permissions or user_data.get('role_code') == 'ADMIN'
        self.current_finance_id: Optional[int] = None
        self.current_finance_status: Optional[str] = None
        self.payment_methods = []
        self.treasury_accounts = []
        self._child_windows = []

        self.setWindowTitle('اسناد مالی متصل به ورود و خروج')
        self.resize(1600, 900)
        self._build_ui()
        self._update_due_date_jalali()
        self._load_payment_methods()
        self._load_treasury_accounts()
        self._apply_permissions()
        self.refresh_documents()
        self.showMaximized()

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
        title = QLabel('مالی متصل به ورود و خروج')
        title.setObjectName('Title')
        subtitle = QLabel('اسناد مالی به‌صورت خودکار از رسید انبار و حواله خروج ایجاد می‌شوند و از اینجا قابل مشاهده و تسویه هستند.')
        subtitle.setObjectName('Muted')
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        # نوار ابزار
        toolbar_card = QFrame()
        toolbar_card.setObjectName('Card')
        toolbar = QHBoxLayout(toolbar_card)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('جستجو بر اساس شماره سند، طرف حساب، شماره مرجع...')
        self.search_edit.textChanged.connect(self.refresh_documents)
        self.status_combo = QComboBox()
        self.status_combo.addItem('همه وضعیت‌ها', 'ALL')
        self.status_combo.addItem('باز', 'OPEN')
        self.status_combo.addItem('ناقص', 'PARTIAL')
        self.status_combo.addItem('تسویه', 'SETTLED')
        self.status_combo.addItem('لغو', 'CANCELLED')
        self.status_combo.currentIndexChanged.connect(self.refresh_documents)
        self.direction_combo = QComboBox()
        self.direction_combo.addItem('همه جهت‌ها', 'ALL')
        self.direction_combo.addItem('دریافتنی', 'RECEIVABLE')
        self.direction_combo.addItem('پرداختنی', 'PAYABLE')
        self.direction_combo.currentIndexChanged.connect(self.refresh_documents)

        refresh_btn = QPushButton('بروزرسانی')
        refresh_btn.setObjectName('SecondaryButton')
        refresh_btn.clicked.connect(self.refresh_documents)
        cancel_btn = QPushButton('ابطال سند')
        cancel_btn.setObjectName('SecondaryButton')
        cancel_btn.clicked.connect(self.cancel_selected_document)
        treasury_btn = QPushButton('مدیریت صندوق/بانک')
        treasury_btn.setObjectName('SecondaryButton')
        treasury_btn.clicked.connect(self.open_treasury_manager)
        checks_btn = QPushButton('مدیریت چک‌ها')
        checks_btn.setObjectName('SecondaryButton')
        checks_btn.clicked.connect(self.open_checks_manager)

        toolbar.addWidget(QLabel('جستجو:'))
        toolbar.addWidget(self.search_edit, 1)
        toolbar.addWidget(QLabel('وضعیت:'))
        toolbar.addWidget(self.status_combo)
        toolbar.addWidget(QLabel('جهت:'))
        toolbar.addWidget(self.direction_combo)
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(cancel_btn)
        toolbar.addWidget(treasury_btn)
        toolbar.addWidget(checks_btn)
        scrap_btn = QPushButton('🪵 فروش ضایعات')
        scrap_btn.setObjectName('SecondaryButton')
        scrap_btn.clicked.connect(self.open_scrap_window)
        toolbar.addWidget(scrap_btn)
        pending_btn = QPushButton('🏦 مانده با چک‌های در انتظار')
        pending_btn.setObjectName('SecondaryButton')
        pending_btn.clicked.connect(self._open_account_pending_dialog)
        toolbar.addWidget(pending_btn)
        revert_btn = QPushButton('↩️ برگشت تسویه‌ها')
        revert_btn.setObjectName('SecondaryButton')
        revert_btn.clicked.connect(self._revert_cleared_payments)
        revert_btn.setEnabled(self.can_manage)
        revert_btn.setToolTip('برگشت چک‌های وصول‌شدهٔ سند انتخاب‌شده به «در انتظار» (با کسر از صندوق)')
        toolbar.addWidget(revert_btn)
        root.addWidget(toolbar_card)

        # تب‌ها
        self.tabs = QTabWidget()
        self.tabs

        self.tabs.addTab(self._build_tab_documents(), '📋 لیست اسناد')
        self.tabs.addTab(self._build_tab_details(), '🔍 جزئیات سند')
        self.tabs.addTab(self._build_tab_payment(), '💰 ثبت تسویه')

        root.addWidget(self.tabs, 1)

    # ================================================================
    # تب ۱: لیست اسناد + کارت‌های آماری
    # ================================================================

    def _build_tab_documents(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_recv_open = self._stat_card('دریافتنی باز', '0 ریال', '#1d4ed8')
        self.card_recv_settled = self._stat_card('دریافتنی تسویه', '0 ریال', '#2563eb')
        self.card_pay_open = self._stat_card('پرداختنی باز', '0 ریال', '#b91c1c')
        self.card_pay_settled = self._stat_card('پرداختنی تسویه', '0 ریال', '#dc2626')
        self.card_total = self._stat_card('جمع کل اسناد', '0 مورد', '#6d28d9')

        cards_layout.addWidget(self.card_recv_open)
        cards_layout.addWidget(self.card_recv_settled)
        cards_layout.addWidget(self.card_pay_open)
        cards_layout.addWidget(self.card_pay_settled)
        cards_layout.addWidget(self.card_total)
        layout.addLayout(cards_layout)

        self.documents_table = QTableWidget(0, 12)
        self.documents_table.setHorizontalHeaderLabels([
            'ردیف', 'شناسه', 'شماره سند', 'تاریخ', 'نوع', 'جهت', 'طرف حساب',
            'مبلغ کل', 'تسویه شده', 'مانده', 'تعداد چک', 'وضعیت'
        ])
        self.documents_table.setColumnHidden(1, True)
        self.documents_table.verticalHeader().setVisible(False)
        self.documents_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.documents_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.documents_table.setAlternatingRowColors(True)
        self.documents_table.itemSelectionChanged.connect(self._on_document_selected)
        layout.addWidget(self.documents_table)

        return tab

    # ================================================================
    # تب ۲: جزئیات سند انتخاب‌شده
    # ================================================================

    def _build_tab_details(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        info_group = QGroupBox('اطلاعات سند')
        info_layout = QGridLayout(info_group)
        info_layout.setHorizontalSpacing(15)
        info_layout.setVerticalSpacing(10)

        self.fin_no_lbl = self._info_label('-')
        self.op_type_lbl = self._info_label('-')
        self.dir_lbl = self._info_label('-')
        self.counter_lbl = self._info_label('-')
        self.ref_lbl = self._info_label('-')
        self.status_lbl = self._info_label('-')
        self.total_lbl = self._info_label('0', '#93c5fd')
        self.settled_lbl = self._info_label('0', '#10b981')
        self.remaining_lbl = self._info_label('0', '#fca5a5')
        self.desc_view = QTextEdit()
        self.desc_view.setReadOnly(True)
        self.desc_view.setMinimumHeight(80)
        self.desc_view

        info_layout.addWidget(QLabel('شماره سند:'), 0, 0)
        info_layout.addWidget(self.fin_no_lbl, 0, 1)
        info_layout.addWidget(QLabel('نوع عملیات:'), 0, 2)
        info_layout.addWidget(self.op_type_lbl, 0, 3)
        info_layout.addWidget(QLabel('جهت:'), 1, 0)
        info_layout.addWidget(self.dir_lbl, 1, 1)
        info_layout.addWidget(QLabel('طرف حساب:'), 1, 2)
        info_layout.addWidget(self.counter_lbl, 1, 3)
        info_layout.addWidget(QLabel('سند مرجع:'), 2, 0)
        info_layout.addWidget(self.ref_lbl, 2, 1)
        info_layout.addWidget(QLabel('وضعیت:'), 2, 2)
        info_layout.addWidget(self.status_lbl, 2, 3)
        info_layout.addWidget(QLabel('مبلغ کل:'), 3, 0)
        info_layout.addWidget(self.total_lbl, 3, 1)
        info_layout.addWidget(QLabel('تسویه شده:'), 3, 2)
        info_layout.addWidget(self.settled_lbl, 3, 3)
        info_layout.addWidget(QLabel('مانده:'), 4, 0)
        info_layout.addWidget(self.remaining_lbl, 4, 1, 1, 3)
        info_layout.addWidget(QLabel('توضیحات:'), 5, 0)
        info_layout.addWidget(self.desc_view, 5, 1, 1, 3)

        layout.addWidget(info_group)

        payments_group = QGroupBox('تراکنش‌های مالی ثبت‌شده')
        payments_layout = QVBoxLayout(payments_group)
        self.payments_table = QTableWidget(0, 7)
        self.payments_table.setHorizontalHeaderLabels([
            'شناسه', 'تاریخ ثبت', 'روش', 'مبلغ', 'حساب', 'وضعیت', 'توضیح'
        ])
        self.payments_table.setColumnHidden(0, True)
        self.payments_table.verticalHeader().setVisible(False)
        self.payments_table.setAlternatingRowColors(True)
        self.payments_table.horizontalHeader().setStretchLastSection(True)
        payments_layout.addWidget(self.payments_table)
        layout.addWidget(payments_group)

        return tab

    # ================================================================
    # تب ۳: ثبت تسویه / پرداخت
    # ================================================================

    def _build_tab_payment(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        # [CANCEL] بنر هشدار برای سند ابطال‌شده
        self.cancelled_banner = QLabel('⚠️ این سند ابطال شده است و امکان تسویه ندارد.')
        self.cancelled_banner.setStyleSheet(
            "background-color: #fee2e2; color: #b91c1c; font-weight: bold; "
            "padding: 10px; border-radius: 6px; border: 2px solid #ef4444;"
        )
        self.cancelled_banner.setAlignment(Qt.AlignCenter)
        self.cancelled_banner.hide()
        layout.addWidget(self.cancelled_banner)

        summary_group = QGroupBox('سند در حال تسویه')
        summary_layout = QGridLayout(summary_group)
        self.pay_fin_no = self._info_label('-')
        self.pay_counter = self._info_label('-')
        self.pay_direction = self._info_label('-')
        self.pay_total = self._info_label('0')
        self.pay_settled = self._info_label('0')
        self.pay_remaining = self._info_label('0', '#f59e0b')

        summary_layout.addWidget(QLabel('شماره سند:'), 0, 0)
        summary_layout.addWidget(self.pay_fin_no, 0, 1)
        summary_layout.addWidget(QLabel('طرف حساب:'), 0, 2)
        summary_layout.addWidget(self.pay_counter, 0, 3)
        summary_layout.addWidget(QLabel('جهت:'), 1, 0)
        summary_layout.addWidget(self.pay_direction, 1, 1)
        summary_layout.addWidget(QLabel('مبلغ کل:'), 1, 2)
        summary_layout.addWidget(self.pay_total, 1, 3)
        summary_layout.addWidget(QLabel('تسویه شده:'), 2, 0)
        summary_layout.addWidget(self.pay_settled, 2, 1)
        summary_layout.addWidget(QLabel('مانده برای تسویه:'), 2, 2)
        self.pay_remaining.setStyleSheet('color: #fdba74; font-size: 14px; font-weight: bold; padding: 4px;')
        summary_layout.addWidget(self.pay_remaining, 2, 3)
        summary_layout.addWidget(QLabel('مغایرت با مبلغ واردشده:'), 3, 0)
        self.pay_diff_label = QLabel('-')
        self.pay_diff_label.setStyleSheet('color: #fdba74; font-size: 14px; font-weight: bold; padding: 4px;')
        summary_layout.addWidget(self.pay_diff_label, 3, 1, 1, 3)
        summary_layout.addWidget(QLabel('چک‌های در انتظار:'), 4, 0)
        self.pay_pending_label = QLabel('0 ریال')
        self.pay_pending_label.setStyleSheet('color: #fdba74; font-size: 14px; font-weight: bold; padding: 4px;')
        summary_layout.addWidget(self.pay_pending_label, 4, 1)
        layout.addWidget(summary_group)

        form_group = QGroupBox('فرم تسویه')
        form_layout = QGridLayout(form_group)
        form_layout.setHorizontalSpacing(15)
        form_layout.setVerticalSpacing(12)

        self.payment_method_combo = QComboBox()
        self.payment_method_combo.setMinimumWidth(180)
        self.treasury_account_combo = QComboBox()
        self.treasury_account_combo.setMinimumWidth(250)
        self.payment_amount_edit = QLineEdit()
        self.payment_amount_edit.setPlaceholderText('مبلغ به ریال')
        self.payment_amount_edit.textChanged.connect(self._format_payment_amount)
        self.payment_amount_edit.textChanged.connect(self._update_pay_diff)
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.due_date_edit.setDate(QDate.currentDate())
        # [JALALI] نمایش تاریخ شمسی سررسید
        self.due_date_jalali_lbl = QLabel('-')
        # [JALALI-STYLE] فونت درشت + نارنجی (مثل رنگ مانده) + وسط‌چین
        self.due_date_jalali_lbl.setStyleSheet(
            'color: #f59e0b; font-size: 20px; font-weight: bold; padding-top: 8px;'
        )
        self.due_date_jalali_lbl.setAlignment(Qt.AlignCenter)
        self.due_date_edit.dateChanged.connect(self._update_due_date_jalali)
        self.check_no_edit = QLineEdit()
        self.check_serial_edit = QLineEdit()
        self.check_bank_edit = QLineEdit()
        self.check_branch_edit = QLineEdit()
        self.payment_desc_edit = QLineEdit()
        self.payment_desc_edit.setPlaceholderText('توضیح (اختیاری)')

        # [BANK] بانک‌های طرف مقابل (از bank_accounts شخص)
        self.party_bank_combo = QComboBox()
        self.party_bank_combo.setMinimumWidth(200)
        self.party_bank_combo.currentIndexChanged.connect(self._on_party_bank_changed)

        self.register_btn = QPushButton('ثبت پرداخت / دریافت')
        self.register_btn.setObjectName('PrimaryButton')
        self.register_btn.setMinimumHeight(45)
        self.register_btn.clicked.connect(self.register_payment)

        form_layout.addWidget(QLabel('روش پرداخت:'), 0, 0)
        form_layout.addWidget(self.payment_method_combo, 0, 1)
        form_layout.addWidget(QLabel('صندوق / بانک:'), 0, 2)
        form_layout.addWidget(self.treasury_account_combo, 0, 3)
        form_layout.addWidget(QLabel('بانک طرف مقابل:'), 1, 0)
        form_layout.addWidget(self.party_bank_combo, 1, 1)
        form_layout.addWidget(QLabel('مبلغ:'), 1, 2)
        form_layout.addWidget(self.payment_amount_edit, 1, 3)
        form_layout.addWidget(QLabel('تاریخ سررسید:'), 2, 0)
        form_layout.addWidget(self.due_date_edit, 2, 1)
        form_layout.addWidget(QLabel('شمسی:'), 2, 2)
        form_layout.addWidget(self.due_date_jalali_lbl, 2, 3)
        form_layout.addWidget(QLabel('شماره چک:'), 3, 0)
        form_layout.addWidget(self.check_no_edit, 3, 1)
        form_layout.addWidget(QLabel('سریال چک:'), 3, 2)
        form_layout.addWidget(self.check_serial_edit, 3, 3)
        form_layout.addWidget(QLabel('بانک چک:'), 4, 0)
        form_layout.addWidget(self.check_bank_edit, 4, 1)
        form_layout.addWidget(QLabel('شعبه:'), 4, 2)
        form_layout.addWidget(self.check_branch_edit, 4, 3)
        form_layout.addWidget(QLabel('توضیح:'), 5, 0)
        form_layout.addWidget(self.payment_desc_edit, 5, 1, 1, 3)
        form_layout.addWidget(self.register_btn, 6, 0, 1, 4)

        form_layout.setColumnStretch(1, 1)
        form_layout.setColumnStretch(3, 1)

        layout.addWidget(form_group)
        layout.addStretch()

        return tab

    # ================================================================
    # توابع کمکی UI
    # ================================================================

    def _stat_card(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName('Card')
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)
        lbl = QLabel(title)
        lbl.setStyleSheet('color: ' + color + '; font-size: 12px; font-weight: bold;')
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        val_lbl = QLabel(value)
        val_lbl.setObjectName('value')
        val_lbl.setStyleSheet(' font-size: 18px; font-weight: bold;')
        val_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(val_lbl)
        return card

    def _info_label(self, text: str, color: str = '') -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet('color: ' + (color or _tc_txt()) + '; font-size: 14px; padding: 4px;')
        return lbl

    # ================================================================
    # بارگذاری داده‌ها
    # ================================================================

    def _load_payment_methods(self) -> None:
        self.payment_methods = self.repository.list_payment_methods()
        self.payment_method_combo.clear()
        self.payment_method_combo.addItem('انتخاب کنید', None)
        for item in self.payment_methods:
            self.payment_method_combo.addItem(item['name'], item['id'])

    def _load_treasury_accounts(self) -> None:
        """[C1] بارگذاری از treasury_accounts (نه cash_accounts)"""
        self.treasury_account_combo.clear()
        self.treasury_account_combo.addItem('انتخاب کنید', None)
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("""
                    SELECT id, code, name, account_type, bank_name, account_number, current_balance, is_active
                    FROM treasury_accounts
                    WHERE is_active = 1
                    ORDER BY account_type, name
                """).fetchall()
                for r in rows:
                    acc_id, code, name, acc_type, bank_name, acc_number, balance, is_active = r
                    type_label = 'صندوق' if acc_type == 'CASHBOX' else 'بانک'
                    bank_info = f" - {bank_name}" if bank_name and acc_type == 'BANK' else ""
                    balance_str = f"{int(balance or 0):,} ریال"
                    display = f"{name} [{type_label}{bank_info}] - مانده: {balance_str}"
                    self.treasury_account_combo.addItem(display, acc_id)
        except Exception:
            pass

    def _apply_permissions(self) -> None:
        if not self.can_manage:
            self.register_btn.setEnabled(False)

    # ================================================================
    # بارگذاری و نمایش اسناد
    # ================================================================

    def _revert_cleared_payments(self):
        """برگشت پرداخت‌های وصول‌شدهٔ سند انتخاب‌شده به «در انتظار» + معکوس‌سازی صندوق"""
        fid = self.current_finance_id
        if not fid:
            QMessageBox.information(self, 'برگشت تسویه', 'ابتدا یک سند مالی از لیست انتخاب کنید.')
            return
        try:
            with self.db.connect() as conn:
                pays = conn.execute(
                    "SELECT id, amount, status, treasury_account_id FROM payment_entries "
                    "WHERE financial_document_id = ? AND status = 'CLEARED'", (fid,)
                ).fetchall()
                if not pays:
                    QMessageBox.information(self, 'برگشت تسویه',
                        'این سند پرداخت وصول‌شده‌ای ندارد؛ ابطال آزاد است.')
                    return
                total = sum(int(x[1] or 0) for x in pays)
                ok = QMessageBox.question(
                    self, 'برگشت تسویه',
                    'این سند {} پرداخت وصول‌شده به مبلغ {:,} ریال دارد.\n'
                    'با برگشت به «در انتظار»، مبلغ از صندوق/بانک کسر می‌شود.\n'
                    'ادامه می‌دهید؟'.format(len(pays), total),
                    QMessageBox.Yes | QMessageBox.No)
                if ok != QMessageBox.Yes:
                    return
                for x in pays:
                    if x[3]:
                        conn.execute(
                            "UPDATE treasury_accounts SET current_balance = COALESCE(current_balance,0) - ? "
                            "WHERE id = ?", (int(x[1] or 0), int(x[3])))
                    conn.execute(
                        "UPDATE payment_entries SET status = 'PENDING', treasury_account_id = NULL "
                        "WHERE id = ?", (x[0],))
                conn.commit()
            self.refresh_documents()
            QMessageBox.information(self, 'برگشت تسویه',
                '✔ پرداخت‌های وصول‌شده به «در انتظار» برگشتند.\nحالا می‌توانید سند را ابطال کنید.')
        except Exception as e:
            QMessageBox.critical(self, 'خطا در برگشت تسویه', str(e))

    def refresh_documents(self) -> None:
        rows = self.repository.list_financial_documents(
            search_text=self.search_edit.text(),
            status_filter=self.status_combo.currentData(),
            direction_filter=self.direction_combo.currentData(),
        )

        self.documents_table.setRowCount(len(rows))

        # [REMAIN] جمع چک‌های در انتظار همه اسناد (برای ماندهٔ درست در لیست)
        pending_map = {}
        # [CHECKCOUNT] تعداد چک‌های هر سند (برای ستون «تعداد چک»)
        check_count_map = {}
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                for cr in conn.execute(
                    "SELECT pe.financial_document_id, COUNT(*) AS c FROM payment_entries pe "
                    "JOIN payment_methods pm ON pm.id = pe.payment_method_id "
                    "WHERE pm.code = 'CHECK' GROUP BY pe.financial_document_id"
                ).fetchall():
                    check_count_map[int(cr[0])] = int(cr[1])
        except Exception:
            pass
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                for pr in conn.execute(
                    "SELECT financial_document_id, SUM(amount) AS p FROM payment_entries "
                    "WHERE status = 'PENDING' GROUP BY financial_document_id"
                ).fetchall():
                    pending_map[int(pr[0])] = int(pr[1] or 0)
        except Exception:
            pass

        recv_open_total = 0
        recv_settled_total = 0
        pay_open_total = 0
        pay_settled_total = 0

        for row_index, row in enumerate(rows):
            total = int(row.get('total_amount') or 0)
            settled = int(row.get('settled_amount') or 0)
            pending = pending_map.get(int(row.get('id') or 0), 0)
            remaining = max(total - settled - pending, 0)
            direction = row.get('direction', '')
            status = row.get('status', '')
            finance_date = row.get('finance_date', '')
            date_jalali = jalali_date_display_from_iso(finance_date) if finance_date else '-'

            if direction == 'RECEIVABLE':
                if status in ('OPEN', 'PARTIAL'):
                    recv_open_total += remaining
                else:
                    recv_settled_total += total
            elif direction == 'PAYABLE':
                if status in ('OPEN', 'PARTIAL'):
                    pay_open_total += remaining
                else:
                    pay_settled_total += total

            check_count = check_count_map.get(int(row.get('id') or 0), 0)
            op_label = _operation_label_from_finance_no(row['finance_no'], row['operation_type'])
            cp_val = row.get('counterparty_name') or ''  # pay_cp
            if not cp_val and (row.get('finance_no') or '').startswith('PAY-'):
                try:
                    with self.db.connect() as _cc:
                        _cc.row_factory = None
                        _r = _cc.execute("SELECT description FROM financial_documents WHERE id=?", (int(row["id"]),)).fetchone()
                        cp_val = (_r[0] or '').replace('پرداخت پرسنل: ', '').strip() if _r else ''
                except Exception:
                    cp_val = ''
            cp_val = cp_val or '-'
            values = [
                str(row_index + 1),
                str(row['id']),
                row['finance_no'],
                date_jalali,
                op_label,
                DIRECTION_LABELS.get(direction, direction),
                cp_val,
                f"{total:,} ریال",
                f"{settled:,} ریال",
                f"{remaining:,} ریال",
                str(check_count),  # [CHECKCOUNT] تعداد چک
                STATUS_LABELS.get(status, status),
            ]

            row_color = STATUS_COLORS.get(status, '#e2e8f0')
            is_return = op_label.startswith('برگشت')

            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 11:
                    item.setForeground(QColor(row_color))
                elif col == 4 and is_return:
                    item.setForeground(QColor('#b45309'))
                    item.setBackground(QColor('#fef3c7'))
                self.documents_table.setItem(row_index, col, item)

        self.documents_table.resizeColumnsToContents()

        self.card_recv_open.findChild(QLabel, 'value').setText(f"{recv_open_total:,} ریال")
        self.card_recv_settled.findChild(QLabel, 'value').setText(f"{recv_settled_total:,} ریال")
        self.card_pay_open.findChild(QLabel, 'value').setText(f"{pay_open_total:,} ریال")
        self.card_pay_settled.findChild(QLabel, 'value').setText(f"{pay_settled_total:,} ریال")
        self.card_total.findChild(QLabel, 'value').setText(f"{len(rows)} مورد")

        if rows and self.documents_table.currentRow() < 0:
            self.documents_table.selectRow(0)

    def _on_document_selected(self) -> None:
        row = self.documents_table.currentRow()
        if row < 0:
            return
        item = self.documents_table.item(row, 1)
        if not item:
            return
        try:
            finance_id = int(item.text())
        except ValueError:
            return
        self.current_finance_id = finance_id
        self._load_details(finance_id)
        self._update_payment_tab(finance_id)

    def _load_details(self, finance_id: int) -> None:
        finance = self.repository.get_financial_document(finance_id)
        if not finance:
            return

        total = int(finance.get('total_amount') or 0)
        settled = int(finance.get('settled_amount') or 0)
        remaining = max(total - settled, 0)
        ref_text = (finance.get('receipt_no') or finance.get('issue_no') or
                    finance.get('inbound_reference_no') or finance.get('outbound_reference_no') or '-')

        self.fin_no_lbl.setText(finance.get('finance_no') or '-')
        self.op_type_lbl.setText(_operation_label_from_finance_no(finance.get('finance_no'), finance.get('operation_type')))
        self.dir_lbl.setText(DIRECTION_LABELS.get(finance.get('direction'), finance.get('direction', '-')))
        self.counter_lbl.setText(finance.get('counterparty_name') or '-')
        self.ref_lbl.setText(ref_text)
        for _lb in (self.fin_no_lbl, self.op_type_lbl, self.dir_lbl, self.counter_lbl, self.ref_lbl):
            _lb.setStyleSheet(' font-weight:bold; font-size:13px;')
        status = finance.get('status', '-')
        self.status_lbl.setText(STATUS_LABELS.get(status, status))
        self.status_lbl.setStyleSheet(f'color: {STATUS_COLORS.get(status, "#e2e8f0")}; font-size: 14px; font-weight: bold; padding: 4px;')
        self.total_lbl.setText(f"{total:,} ریال")
        self.settled_lbl.setText(f"{settled:,} ریال")
        self.remaining_lbl.setText(f"{remaining:,} ریال")
        self.desc_view.setPlainText(finance.get('description') or '')

        payments = finance.get('payments') or []
        self.payments_table.setRowCount(len(payments))
        for i, p in enumerate(payments):
            values = [
                str(p['id']),
                p.get('created_at', '-')[:10] if p.get('created_at') else '-',
                p.get('payment_method_name') or '-',
                f"{int(p.get('amount') or 0):,} ریال",
                p.get('treasury_account_name') or '-',
                p.get('status') or '-',
                p.get('description') or '-',
            ]
            for j, v in enumerate(values):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.payments_table.setItem(i, j, item)
        self.payments_table.resizeColumnsToContents()

    def _update_payment_tab(self, finance_id: int) -> None:
        finance = self.repository.get_financial_document(finance_id)
        if not finance:
            return

        total = int(finance.get('total_amount') or 0)
        settled = int(finance.get('settled_amount') or 0)
        status = finance.get('status') or 'OPEN'

        # [REMAIN] مانده = کل − تسویه − چک‌های در انتظار
        pending = 0
        try:
            with self.db.connect() as conn:
                row = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM payment_entries "
                    "WHERE financial_document_id = ? AND status = 'PENDING'",
                    (finance_id,)
                ).fetchone()
                pending = int(row[0] or 0)
        except Exception:
            pass
        remaining = max(total - settled - pending, 0)

        self.current_finance_status = status
        self.pay_fin_no.setText(finance.get('finance_no') or '-')
        self.pay_counter.setText(finance.get('counterparty_name') or '-')
        self.pay_direction.setText(DIRECTION_LABELS.get(finance.get('direction'), '-'))
        for _pb in (self.pay_fin_no, self.pay_counter, self.pay_direction, self.pay_total, self.pay_settled):
            _pb.setStyleSheet(' font-weight:bold; font-size:13px;')
        self.pay_total.setText(f"{total:,} ریال")
        self.pay_settled.setText(f"{settled:,} ریال")
        self.pay_remaining.setText(f"{remaining:,} ریال")
        if hasattr(self, 'pay_pending_label'):
            self.pay_pending_label.setText(f"{pending:,} ریال")
        # پر کردن خودکار مبلغ با ماندهٔ قابل تسویه (برای تسویهٔ نقدیِ باقی‌مانده)
        if remaining > 0:
            self.payment_amount_edit.setText(f"{remaining:,}")
        else:
            self.payment_amount_edit.clear()
        self._update_pay_diff()

        # [CANCEL] غیرفعال کردن فرم برای سند ابطال‌شده
        is_cancelled = (status == 'CANCELLED')
        self.cancelled_banner.setVisible(is_cancelled)
        for w in (self.payment_method_combo, self.treasury_account_combo,
                  self.party_bank_combo, self.payment_amount_edit,
                  self.due_date_edit, self.check_no_edit, self.check_serial_edit,
                  self.check_bank_edit, self.check_branch_edit, self.payment_desc_edit,
                  self.register_btn):
            w.setEnabled((not is_cancelled) and self.can_manage)

        # [BANK] بارگذاری بانک‌های طرف مقابل
        self._load_party_banks(finance.get('counterparty_person_id'))

    # ================================================================
    # [BANK] بانک‌های طرف مقابل
    # ================================================================

    def _load_party_banks(self, person_id) -> None:
        """[BANK-FIX2] خواندن بانک‌های شخص از bank_accounts (جایی که واقعاً ذخیره می‌شوند)
        و اگر رکوردی نبود، از persons.bank_name به‌عنوان پشتیبان"""
        self.party_bank_combo.clear()
        self.party_bank_combo.addItem('بانک طرف مقابل (اختیاری)', None)
        if not person_id:
            return
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT id, bank_name, account_number, iban, card_number "
                    "FROM bank_accounts WHERE person_id = ? ORDER BY is_default DESC, id",
                    (person_id,)
                ).fetchall()
                for r in rows:
                    bank_name = r[1] or 'بانک'
                    acc_no = r[2] or ''
                    label = f"{bank_name} {(' - ' + acc_no) if acc_no else ''}".strip()
                    self.party_bank_combo.addItem(label, {
                        'bank_name': r[1] or '',
                        'account_number': r[2] or '',
                        'iban': r[3] or '',
                        'card_number': r[4] or '',
                    })
                # اگر هیچ رکوردی در bank_accounts نبود، از persons بخوان
                if self.party_bank_combo.count() <= 1:
                    row = conn.execute(
                        "SELECT bank_name, account_number, iban FROM persons WHERE id = ?",
                        (person_id,)
                    ).fetchone()
                    if row and (row[0] or row[1]):
                        bank_name = row[0] or 'بانک'
                        acc_no = row[1] or ''
                        label = f"{bank_name} {(' - ' + acc_no) if acc_no else ''}".strip()
                        self.party_bank_combo.addItem(label, {
                            'bank_name': row[0] or '',
                            'account_number': row[1] or '',
                            'iban': row[2] or '',
                            'card_number': '',
                        })
        except Exception:
            pass

    def _on_party_bank_changed(self) -> None:
        data = self.party_bank_combo.currentData()
        if not data or not isinstance(data, dict):
            return
        # پر کردن فیلدهای چک از بانک طرف مقابل
        if data.get('bank_name'):
            self.check_bank_edit.setText(data['bank_name'])
        # شماره کارت/حساب در توضیح یا سریال چک نمی‌آید؛ فقط بانک و شعبه مهم است
        # (در صورت نیاز می‌توان شماره حساب را هم اضافه کرد)

    # ================================================================
    # ثبت پرداخت
    # ================================================================

    def _update_due_date_jalali(self) -> None:
        """[JALALI] نمایش معادل شمسی تاریخ سررسید"""
        try:
            iso = self.due_date_edit.date().toString('yyyy-MM-dd')
            self.due_date_jalali_lbl.setText(jalali_date_display_from_iso(iso))
        except Exception:
            self.due_date_jalali_lbl.setText('-')

    def _format_payment_amount(self) -> None:
        digits = ''.join(ch for ch in self.payment_amount_edit.text() if ch.isdigit())
        self.payment_amount_edit.blockSignals(True)
        self.payment_amount_edit.setText(f'{int(digits):,}' if digits else '')
        self.payment_amount_edit.blockSignals(False)

    def _int_from_text(self, value: str) -> int:
        digits = ''.join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else 0


    def _update_pay_diff(self) -> None:
        """مغایرت زنده بین مبلغ واردشده و ماندهٔ قابل تسویه"""
        if not hasattr(self, 'pay_diff_label'):
            return
        remaining = self._int_from_text(self.pay_remaining.text())
        entered = self._int_from_text(self.payment_amount_edit.text())
        if entered <= 0:
            self.pay_diff_label.setText('-')
            self.pay_diff_label.setStyleSheet('color: #fdba74; font-size: 14px; font-weight: bold; padding: 4px;')
            return
        diff = remaining - entered
        if diff >= 0:
            self.pay_diff_label.setText(f'{diff:,} ریال پس از این پرداخت باقی می‌ماند')
            self.pay_diff_label.setStyleSheet('color: #fdba74; font-size: 14px; font-weight: bold; padding: 4px;')
        else:
            self.pay_diff_label.setText(f'⚠️ {abs(diff):,} ریال بیش از ماندهٔ قابل تسویه!')
            self.pay_diff_label.setStyleSheet('color: #b91c1c; font-size: 14px; font-weight: bold; padding: 4px;')

    def register_payment(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه ثبت عملیات مالی را ندارید.')
            return
        if self.current_finance_id is None:
            QMessageBox.information(self, 'عملیات مالی', 'ابتدا یک سند مالی از تب «لیست اسناد» انتخاب کنید.')
            return
        if self.current_finance_status == 'CANCELLED':
            QMessageBox.warning(self, 'عملیات مالی', 'این سند ابطال شده است و امکان تسویه ندارد.')
            return
        amount = self._int_from_text(self.payment_amount_edit.text())
        remaining = self._int_from_text(self.pay_remaining.text())
        if amount <= 0:
            QMessageBox.warning(self, 'ثبت مالی', 'لطفاً مبلغ پرداخت را وارد کنید.')
            return
        if amount > remaining:
            QMessageBox.warning(
                self, 'ثبت مالی',
                f'مبلغ واردشده ({{amount:,}} ریال) بیشتر از ماندهٔ قابل تسویه ({{remaining:,}} ریال) است.\n'
                'ماندهٔ قابل تسویه، چک‌های در انتظار را هم کسر کرده است.')
            return
        try:
            finance = self.repository.register_payment(
                finance_id=self.current_finance_id,
                payment_method_id=int(self.payment_method_combo.currentData() or 0),
                amount=self._int_from_text(self.payment_amount_edit.text()),
                user_id=self.user_data.get('id'),
                due_date=self.due_date_edit.date().toString('yyyy-MM-dd') if self.due_date_edit.date().isValid() else None,
                check_no=self.check_no_edit.text().strip() or None,
                check_serial=self.check_serial_edit.text().strip() or None,
                check_bank_name=self.check_bank_edit.text().strip() or None,
                check_branch_name=self.check_branch_edit.text().strip() or None,
                description=self.payment_desc_edit.text().strip() or None,
                treasury_account_id=int(self.treasury_account_combo.currentData() or 0) or None,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, 'ثبت مالی', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'ثبت تراکنش با خطا مواجه شد:\n{exc}')
            return

        QMessageBox.information(self, 'ثبت موفق',
            f"تراکنش مالی برای سند «{finance.get('finance_no')}» ثبت شد.")

        self.payment_method_combo.setCurrentIndex(0)
        self.treasury_account_combo.setCurrentIndex(0)
        self.party_bank_combo.setCurrentIndex(0)
        self.payment_amount_edit.clear()
        self.check_no_edit.clear()
        self.check_serial_edit.clear()
        self.check_bank_edit.clear()
        self.check_branch_edit.clear()
        self.payment_desc_edit.clear()

        self._load_treasury_accounts()
        self.refresh_documents()
        self.data_changed.emit()

    # ================================================================
    # ابطال سند
    # ================================================================

    def cancel_selected_document(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه ابطال سند مالی را ندارید.')
            return
        if self.current_finance_id is None:
            QMessageBox.information(self, 'ابطال سند', 'ابتدا یک سند مالی انتخاب کنید.')
            return
        answer = QMessageBox.question(
            self, 'تأیید ابطال',
            'آیا از ابطال این سند مطمئن هستید؟',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            finance = self.repository.cancel_financial_document(
                self.current_finance_id, user_id=self.user_data.get('id'))
        except ValidationError as exc:
            QMessageBox.warning(self, 'ابطال', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'ابطال با خطا مواجه شد:\n{exc}')
            return
        QMessageBox.information(self, 'ابطال موفق',
            f"سند «{finance.get('finance_no')}» ابطال شد.")
        self.refresh_documents()
        self.data_changed.emit()

    # ================================================================
    # پنجره‌های جانبی
    # ================================================================


    def _open_account_pending_dialog(self) -> None:
        """ماندهٔ هر حساب با در نظر گرفتن چک‌های در انتظار وصول/پرداخت"""
        dlg = QDialog(self)
        dlg.setWindowTitle('ماندهٔ حساب‌ها با چک‌های در انتظار')
        dlg.resize(1000, 550)
        dlg.setLayoutDirection(Qt.RightToLeft)
        lay = QVBoxLayout(dlg)
        note = QLabel('ماندهٔ قابل استفاده = مانده فعلی − چک پرداختنی در انتظار + چک دریافتنی در انتظار')
        note.setStyleSheet('color:#f59e0b;font-weight:bold;padding:6px;')
        lay.addWidget(note)
        tbl = QTableWidget(0, 6)
        tbl.setHorizontalHeaderLabels(['حساب', 'مانده فعلی', 'چک پرداختنی در انتظار', 'چک دریافتنی در انتظار', 'مانده قابل استفاده'])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute("""
                SELECT ta.id, ta.name, ta.current_balance,
                  (SELECT COALESCE(SUM(pe.amount),0) FROM payment_entries pe
                   JOIN financial_documents fd ON fd.id=pe.financial_document_id
                   WHERE pe.treasury_account_id=ta.id AND pe.status='PENDING' AND fd.direction='PAYABLE') AS p_out,
                  (SELECT COALESCE(SUM(pe.amount),0) FROM payment_entries pe
                   JOIN financial_documents fd ON fd.id=pe.financial_document_id
                   WHERE pe.treasury_account_id=ta.id AND pe.status='PENDING' AND fd.direction='RECEIVABLE') AS p_in,
              (SELECT MIN(pe.due_date) FROM payment_entries pe
               JOIN financial_documents fd ON fd.id=pe.financial_document_id
               WHERE pe.treasury_account_id=ta.id AND pe.status='PENDING' AND fd.direction='RECEIVABLE') AS next_due
                FROM treasury_accounts ta WHERE ta.is_active=1 ORDER BY ta.name
            """).fetchall()
        tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            cur = int(r[2] or 0); p_out = int(r[3] or 0); p_in = int(r[4] or 0)
            avail = cur - p_out + p_in
            from app.core.jalali import jalali_date_display_from_iso
            nd = r[5]
            nd_txt = jalali_date_display_from_iso(nd) if nd else "-"
            vals = [r[1], f"{cur:,} ریال", f"{p_out:,} ریال", f"{p_in:,} ریال", f"{avail:,} ریال", nd_txt]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c == 4:
                    it.setForeground(QColor('#047857' if avail >= 0 else '#b91c1c'))
                tbl.setItem(i, c, it)
        tbl.resizeColumnsToContents()
        lay.addWidget(tbl)
        close_btn = QPushButton('بستن'); close_btn.setObjectName('SecondaryButton'); close_btn.clicked.connect(dlg.accept)
        lay.addWidget(close_btn)
        dlg.exec_()

    def open_treasury_manager(self) -> None:
        window = TreasuryManagementWindow(self.db, self.user_data)
        window.data_changed.connect(self._load_treasury_accounts)
        window.data_changed.connect(self.refresh_documents)
        window.show()
        self._child_windows.append(window)

    def open_scrap_window(self) -> None:
        from app.ui.scrap_window import ScrapWindow
        w = ScrapWindow(self.db, self.user_data)
        w.show(); self._child_windows.append(w)

    def open_checks_manager(self) -> None:
        window = ChecksManagementWindow(self.db, self.user_data)
        window.data_changed.connect(self._load_treasury_accounts)
        window.data_changed.connect(self.refresh_documents)
        window.show()
        self._child_windows.append(window)
