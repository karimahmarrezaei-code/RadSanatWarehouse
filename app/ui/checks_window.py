# -*- coding: utf-8 -*-
"""
Checks Management Window - نسخه تب‌بندی‌شده (۳ تب)

تب‌ها:
  📋 لیست چک‌ها   → جدول کامل + فیلترها + کارت‌های آماری
  🔍 جزئیات چک   → اطلاعات کامل چک انتخاب‌شده (با تاریخ شمسی)
  ⚙️ تغییر وضعیت → وصول/برگشت/لغو + انتخاب بانک مقصد

⚠️ نسخه اصلاح‌شده (بازبینی ۱۴۰۵/۰۵/۱۱):
  [TABS] سه‌تب‌بندی مثل «لیست اسناد» برای وضوح
  [JALALI] نمایش تاریخ شمسی سررسید (میلادی + شمسی) در لیست و جزئیات
  [FIX] تعمیر کامل تخریب‌های کپی-پیست (سینتکس): __init__، _build_ui، self.search_edit، < و ...
"""

from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.database import DatabaseManager
from app.core.validators import ValidationError
from app.core.jalali import jalali_date_display_from_iso
from app.repositories.finance_repository import FinanceRepository


CHECK_STATUS_LABELS = {
    'PENDING': 'در انتظار',
    'CLEARED': 'وصول شد',
    'BOUNCED': 'برگشتی',
    'CANCELLED': 'لغو',
}
DIRECTION_LABELS = {'RECEIVABLE': 'دریافتنی', 'PAYABLE': 'پرداختنی'}

STATUS_COLORS = {
    'PENDING': '#b45309',    # نارنجی
    'CLEARED': '#047857',    # سبز
    'BOUNCED': '#b91c1c',    # قرمز
    'CANCELLED': '#64748b',  # خاکستری
}


class ChecksManagementWindow(QDialog):

    data_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.repository = FinanceRepository(db)
        permissions = set(user_data.get('permissions', []) or [])
        self.can_manage = 'finance.manage' in permissions or user_data.get('role_code') == 'ADMIN'
        self.current_payment_id: Optional[int] = None
        self.treasury_accounts = []
        self.setWindowTitle('مدیریت چک‌ها و سررسیدها')
        self.resize(1450, 860)
        self._build_ui()
        self._load_treasury_accounts()
        self._apply_permissions()
        self.refresh_checks()

    # ================================================================
    # ساخت UI (سه تب)
    # ================================================================

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # هدر
        header = QFrame()
        header.setObjectName('Card')
        header_layout = QVBoxLayout(header)
        title = QLabel('مدیریت چک‌ها و سررسیدها')
        title.setObjectName('Title')
        subtitle = QLabel('پیگیری چک‌های در انتظار، سررسیدها، وصول و برگشتی')
        subtitle.setObjectName('Muted')
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        # نوار فیلتر (مشترک)
        filters_card = QFrame()
        filters_card.setObjectName('Card')
        filters_layout = QHBoxLayout(filters_card)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('جستجو بر اساس شماره سند، طرف حساب، شماره چک، بانک یا مرجع بار...')
        self.search_edit.textChanged.connect(self.refresh_checks)
        self.status_combo = QComboBox()
        self.status_combo.addItem('همه وضعیت‌ها', 'ALL')
        self.status_combo.addItem('در انتظار', 'PENDING')
        self.status_combo.addItem('وصول شد', 'CLEARED')
        self.status_combo.addItem('برگشتی', 'BOUNCED')
        self.status_combo.addItem('لغو', 'CANCELLED')
        self.status_combo.currentIndexChanged.connect(self.refresh_checks)
        self.due_scope_combo = QComboBox()
        self.due_scope_combo.addItem('همه سررسیدها', 'ALL')
        self.due_scope_combo.addItem('معوق', 'OVERDUE')
        self.due_scope_combo.addItem('سررسید امروز', 'TODAY')
        self.due_scope_combo.addItem('آتی', 'UPCOMING')
        self.due_scope_combo.addItem('بدون سررسید', 'NO_DUE_DATE')
        self.due_scope_combo.currentIndexChanged.connect(self.refresh_checks)
        refresh_btn = QPushButton('بروزرسانی')
        refresh_btn.setObjectName('SecondaryButton')
        refresh_btn.clicked.connect(self.refresh_checks)
        filters_layout.addWidget(QLabel('جستجو:'))
        filters_layout.addWidget(self.search_edit, 1)
        filters_layout.addWidget(QLabel('وضعیت:'))
        filters_layout.addWidget(self.status_combo)
        filters_layout.addWidget(QLabel('سررسید:'))
        filters_layout.addWidget(self.due_scope_combo)
        filters_layout.addWidget(refresh_btn)
        root.addWidget(filters_card)

        # تب‌ها
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_tab_list(), '📋 لیست چک‌ها')
        self.tabs.addTab(self._build_tab_details(), '🔍 جزئیات چک')
        self.tabs.addTab(self._build_tab_action(), '⚙️ تغییر وضعیت')
        root.addWidget(self.tabs, 1)

    # ----------------------------------------------------------------
    # تب ۱: لیست چک‌ها + کارت‌های آماری
    # ----------------------------------------------------------------

    def _build_tab_list(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # کارت‌های آماری
        summary_group = QGroupBox('خلاصه چک‌ها')
        summary_layout = QGridLayout(summary_group)
        summary_layout.setHorizontalSpacing(18)
        summary_layout.setVerticalSpacing(8)

        self.total_checks_label = QLabel('0')
        self.total_checks_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #8b5cf6;')
        self.pending_count_label = QLabel('0')
        self.pending_count_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #f59e0b;')
        self.pending_amount_label = QLabel('0')
        self.pending_amount_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #f59e0b;')
        self.overdue_count_label = QLabel('0')
        self.overdue_count_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #dc2626;')
        self.overdue_amount_label = QLabel('0')
        self.overdue_amount_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #dc2626;')
        self.due_today_amount_label = QLabel('0')
        self.due_today_amount_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #f59e0b;')
        self.cleared_count_label = QLabel('0')
        self.cleared_count_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #10b981;')
        self.bounced_count_label = QLabel('0')
        self.bounced_count_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #dc2626;')

        summary_layout.addWidget(QLabel('تعداد کل چک‌ها'), 0, 0)
        summary_layout.addWidget(self.total_checks_label, 0, 1)
        summary_layout.addWidget(QLabel('چک‌های در انتظار'), 0, 2)
        summary_layout.addWidget(self.pending_count_label, 0, 3)
        summary_layout.addWidget(QLabel('مبلغ در انتظار'), 1, 0)
        summary_layout.addWidget(self.pending_amount_label, 1, 1)
        summary_layout.addWidget(QLabel('تعداد معوق'), 1, 2)
        summary_layout.addWidget(self.overdue_count_label, 1, 3)
        summary_layout.addWidget(QLabel('مبلغ معوق'), 2, 0)
        summary_layout.addWidget(self.overdue_amount_label, 2, 1)
        summary_layout.addWidget(QLabel('مبلغ سررسید امروز'), 2, 2)
        summary_layout.addWidget(self.due_today_amount_label, 2, 3)
        summary_layout.addWidget(QLabel('چک‌های وصول‌شده'), 3, 0)
        summary_layout.addWidget(self.cleared_count_label, 3, 1)
        summary_layout.addWidget(QLabel('چک‌های برگشتی'), 3, 2)
        summary_layout.addWidget(self.bounced_count_label, 3, 3)
        layout.addWidget(summary_group)

        # جدول چک‌ها
        self.checks_table = QTableWidget(0, 11)
        self.checks_table.setHorizontalHeaderLabels([
            'شناسه', 'شماره سند', 'طرف حساب', 'جهت', 'مبلغ',
            'سررسید (میلادی)', 'سررسید (شمسی)', 'شماره چک', 'بانک', 'وضعیت', 'مرجع'
        ])
        self.checks_table.setColumnHidden(0, True)
        self.checks_table.verticalHeader().setVisible(False)
        self.checks_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.checks_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.checks_table.itemSelectionChanged.connect(self._load_selected_check)
        self.checks_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.checks_table)

        return tab

    # ----------------------------------------------------------------
    # تب ۲: جزئیات چک
    # ----------------------------------------------------------------

    def _build_tab_details(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        details_group = QGroupBox('جزئیات کامل چک')
        details_layout = QGridLayout(details_group)
        details_layout.setHorizontalSpacing(15)
        details_layout.setVerticalSpacing(12)

        self.finance_no_label = QLabel('-')
        self.counterparty_label = QLabel('-')
        self.direction_label = QLabel('-')
        self.amount_label = QLabel('0')
        self.due_date_label = QLabel('-')
        self.due_date_jalali_label = QLabel('-')
        self.check_no_label = QLabel('-')
        self.check_serial_label = QLabel('-')
        self.bank_label = QLabel('-')
        self.branch_label = QLabel('-')
        self.status_label = QLabel('-')
        self.reference_label = QLabel('-')
        self.description_view = QTextEdit()
        self.description_view.setReadOnly(True)
        self.description_view.setMinimumHeight(90)

        # استایل تاریخ شمسی (درشت + نارنجی)
        self.due_date_jalali_label.setStyleSheet(
            'color: #f59e0b; font-size: 20px; font-weight: bold;'
        )

        details_layout.addWidget(QLabel('شماره سند مالی'), 0, 0)
        details_layout.addWidget(self.finance_no_label, 0, 1)
        details_layout.addWidget(QLabel('طرف حساب'), 0, 2)
        details_layout.addWidget(self.counterparty_label, 0, 3)
        details_layout.addWidget(QLabel('جهت'), 1, 0)
        details_layout.addWidget(self.direction_label, 1, 1)
        details_layout.addWidget(QLabel('مبلغ'), 1, 2)
        details_layout.addWidget(self.amount_label, 1, 3)
        details_layout.addWidget(QLabel('تاریخ سررسید (میلادی)'), 2, 0)
        details_layout.addWidget(self.due_date_label, 2, 1)
        details_layout.addWidget(QLabel('تاریخ سررسید (شمسی)'), 2, 2)
        details_layout.addWidget(self.due_date_jalali_label, 2, 3)
        details_layout.addWidget(QLabel('وضعیت'), 3, 0)
        details_layout.addWidget(self.status_label, 3, 1)
        details_layout.addWidget(QLabel('شماره چک'), 3, 2)
        details_layout.addWidget(self.check_no_label, 3, 3)
        details_layout.addWidget(QLabel('سریال چک'), 4, 0)
        details_layout.addWidget(self.check_serial_label, 4, 1)
        details_layout.addWidget(QLabel('بانک'), 4, 2)
        details_layout.addWidget(self.bank_label, 4, 3)
        details_layout.addWidget(QLabel('شعبه'), 5, 0)
        details_layout.addWidget(self.branch_label, 5, 1)
        details_layout.addWidget(QLabel('مرجع عملیات'), 5, 2)
        details_layout.addWidget(self.reference_label, 5, 3)
        details_layout.addWidget(QLabel('توضیحات'), 6, 0)
        details_layout.addWidget(self.description_view, 6, 1, 1, 3)
        layout.addWidget(details_group)
        layout.addStretch()

        return tab

    # ----------------------------------------------------------------
    # تب ۳: تغییر وضعیت
    # ----------------------------------------------------------------

    def _build_tab_action(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        info_group = QGroupBox('چک انتخاب‌شده')
        info_layout = QGridLayout(info_group)
        self.action_check_label = QLabel('-')
        self.action_amount_label = QLabel('-')
        self.action_status_label = QLabel('-')
        info_layout.addWidget(QLabel('چک:'), 0, 0)
        info_layout.addWidget(self.action_check_label, 0, 1)
        info_layout.addWidget(QLabel('مبلغ:'), 0, 2)
        info_layout.addWidget(self.action_amount_label, 0, 3)
        info_layout.addWidget(QLabel('وضعیت:'), 1, 0)
        info_layout.addWidget(self.action_status_label, 1, 1)
        layout.addWidget(info_group)

        action_group = QGroupBox('تغییر وضعیت چک')
        action_layout = QVBoxLayout(action_group)
        action_layout.setSpacing(12)

        self.treasury_account_combo = QComboBox()
        self.status_note_edit = QLineEdit()
        self.status_note_edit.setPlaceholderText('مثلاً وصول شد / برگشت خورد / لغو شد')

        btns = QHBoxLayout()
        self.clear_btn = QPushButton('✅ وصول شد')
        self.clear_btn
        self.bounce_btn = QPushButton('❌ برگشتی')
        self.bounce_btn
        self.cancel_btn = QPushButton('🚫 لغو')
        self.cancel_btn
        self.clear_btn.clicked.connect(lambda: self._change_status('CLEARED'))
        self.bounce_btn.clicked.connect(lambda: self._change_status('BOUNCED'))
        self.cancel_btn.clicked.connect(lambda: self._change_status('CANCELLED'))
        self.pending_btn = QPushButton('↩️ بازگشت به در انتظار')
        self.pending_btn.clicked.connect(lambda: self._change_status('PENDING'))
        btns.addWidget(self.clear_btn)
        btns.addWidget(self.bounce_btn)
        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.pending_btn)

        action_layout.addWidget(QLabel('بانک مقصد / صندوق تسویه'))
        action_layout.addWidget(self.treasury_account_combo)
        action_layout.addWidget(self.status_note_edit)
        action_layout.addLayout(btns)
        layout.addWidget(action_group)
        layout.addStretch()

        return tab

    # ================================================================
    # توابع کمکی
    # ================================================================

    def _apply_permissions(self) -> None:
        if not self.can_manage:
            for widget in [self.clear_btn, self.bounce_btn, self.cancel_btn, self.pending_btn,
                           self.status_note_edit, self.treasury_account_combo]:
                widget.setEnabled(False)

    def _load_treasury_accounts(self) -> None:
        self.treasury_accounts = self.repository.list_active_treasury_accounts()
        self.treasury_account_combo.clear()
        self.treasury_account_combo.addItem('انتخاب کنید', None)
        for item in self.treasury_accounts:
            label = f"{item['code']} | {item['name']} | مانده: {self._money(int(item.get('current_balance') or 0))}"
            self.treasury_account_combo.addItem(label, item['id'])

    def _money(self, value: int) -> str:
        return f'{int(value):,} ریال'

    # ================================================================
    # بارگذاری لیست
    # ================================================================

    def refresh_checks(self) -> None:
        summary = self.repository.fetch_check_overview()
        self.total_checks_label.setText(str(summary['total_checks']))
        self.pending_count_label.setText(str(summary['pending_count']))
        self.pending_amount_label.setText(self._money(summary['pending_amount']))
        self.overdue_count_label.setText(str(summary['overdue_count']))
        self.overdue_amount_label.setText(self._money(summary['overdue_amount']))
        self.due_today_amount_label.setText(self._money(summary['due_today_amount']))
        self.cleared_count_label.setText(str(summary['cleared_count']))
        self.bounced_count_label.setText(str(summary['bounced_count']))

        rows = self.repository.list_check_entries(
            search_text=self.search_edit.text(),
            status_filter=self.status_combo.currentData(),
            due_scope=self.due_scope_combo.currentData(),
        )
        self.checks_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            reference_text = (row.get('receipt_no') or row.get('issue_no')
                              or row.get('inbound_reference_no') or row.get('outbound_reference_no') or '-')
            due_date = row.get('due_date') or '-'
            due_jalali = jalali_date_display_from_iso(due_date) if due_date and due_date != '-' else '-'
            status = row.get('status') or '-'
            values = [
                str(row['id']),
                row.get('finance_no') or '-',
                row.get('counterparty_name') or '-',
                DIRECTION_LABELS.get(row.get('direction'), row.get('direction', '-')),
                self._money(int(row.get('amount') or 0)),
                due_date,
                due_jalali,  # [JALALI] تاریخ شمسی
                row.get('check_no') or '-',
                row.get('check_bank_name') or '-',
                CHECK_STATUS_LABELS.get(status, status),
                reference_text,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 9:  # وضعیت
                    item.setForeground(self._status_color(status))
                self.checks_table.setItem(row_index, col, item)
        self.checks_table.resizeColumnsToContents()
        if rows and self.checks_table.currentRow() < 0:
            self.checks_table.selectRow(0)
        if not rows:
            self._clear_details()

    def _status_color(self, status: str):
        from PyQt5.QtGui import QColor
        color = STATUS_COLORS.get(status, '#e2e8f0')
        return QColor(color)

    # ================================================================
    # جزئیات
    # ================================================================

    def _clear_details(self) -> None:
        self.current_payment_id = None
        for label in [
            self.finance_no_label, self.counterparty_label, self.direction_label,
            self.amount_label, self.due_date_label, self.due_date_jalali_label,
            self.check_no_label, self.check_serial_label, self.bank_label,
            self.branch_label, self.status_label, self.reference_label,
            self.action_check_label, self.action_amount_label, self.action_status_label,
        ]:
            label.setText('-')
        self.description_view.clear()

    def _load_selected_check(self) -> None:
        row = self.checks_table.currentRow()
        if row < 0:
            return
        item = self.checks_table.item(row, 0)
        if not item:
            return
        payment = self.repository.get_check_entry(int(item.text()))
        if not payment:
            return
        self.current_payment_id = payment['id']
        ref_text = (payment.get('receipt_no') or payment.get('issue_no')
                    or payment.get('inbound_reference_no') or payment.get('outbound_reference_no') or '-')
        status = payment.get('status') or '-'
        due_date = payment.get('due_date') or '-'
        due_jalali = jalali_date_display_from_iso(due_date) if due_date and due_date != '-' else '-'

        self.finance_no_label.setText(payment.get('finance_no') or '-')
        self.counterparty_label.setText(payment.get('counterparty_name') or '-')
        self.direction_label.setText(DIRECTION_LABELS.get(payment.get('direction'), payment.get('direction', '-')))
        self.amount_label.setText(self._money(int(payment.get('amount') or 0)))
        self.due_date_label.setText(due_date)
        self.due_date_jalali_label.setText(due_jalali)  # [JALALI]
        self.check_no_label.setText(payment.get('check_no') or '-')
        self.check_serial_label.setText(payment.get('check_serial') or '-')
        self.bank_label.setText(payment.get('check_bank_name') or '-')
        self.branch_label.setText(payment.get('check_branch_name') or '-')
        self.status_label.setText(CHECK_STATUS_LABELS.get(status, status))
        self.reference_label.setText(ref_text)
        self.description_view.setPlainText(payment.get('description') or '')

        # تب تغییر وضعیت
        self.action_check_label.setText(f"{payment.get('check_no') or payment.get('check_serial') or '-'}")
        self.action_amount_label.setText(self._money(int(payment.get('amount') or 0)))
        self.action_status_label.setText(CHECK_STATUS_LABELS.get(status, status))

        for index in range(self.treasury_account_combo.count()):
            if self.treasury_account_combo.itemData(index) == payment.get('treasury_account_id'):
                self.treasury_account_combo.setCurrentIndex(index)
                break

    # ================================================================
    # تغییر وضعیت
    # ================================================================

    def _change_status(self, new_status: str) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه تغییر وضعیت چک را ندارید.')
            return
        if self.current_payment_id is None:
            QMessageBox.information(self, 'چک‌ها', 'ابتدا یک چک را از جدول انتخاب کنید.')
            return
        try:
            result = self.repository.update_check_status(
                payment_entry_id=self.current_payment_id,
                new_status=new_status,
                user_id=self.user_data.get('id'),
                note=self.status_note_edit.text().strip() or None,
                treasury_account_id=int(self.treasury_account_combo.currentData() or 0) or None,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, 'تغییر وضعیت چک', str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'خطا', f'تغییر وضعیت چک با خطا مواجه شد:\n{exc}')
            return
        QMessageBox.information(
            self, 'تغییر وضعیت چک',
            f"وضعیت چک به «{CHECK_STATUS_LABELS.get(result.get('status'), result.get('status'))}» تغییر کرد."
        )
        self.status_note_edit.clear()
        self.treasury_account_combo.setCurrentIndex(0)
        self._load_treasury_accounts()
        self.refresh_checks()
        self.data_changed.emit()
