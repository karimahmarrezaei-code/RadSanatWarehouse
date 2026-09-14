# -*- coding: utf-8 -*-
"""
TreasuryManagementWindow - بازطراحی کامل
  ✔ تب‌بندی: فرم | لیست | گردش حسابرسی
  ✔ قفل موجودی اولیه پس از اولین ذخیره (سند افتتاحیه دستکاری نمی‌شود)
  ✔ تولید خودکار کد (CA-001 / TR-001) بر اساس نوع
  ✔ گردش حسابرسی با شماره سند مبدأ (برای مغایرت با پرینت بانک)
"""

from typing import Any, Dict, Optional
import tempfile, webbrowser
from datetime import datetime

from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDialog, QFileDialog,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
    QWidget, QTabWidget, QHeaderView,
)
from app.core.jalali import jalali_date_display_from_iso
from app.core.database import DatabaseManager
from app.core.validators import ValidationError
from app.repositories.treasury_repository import TreasuryRepository


TYPE_LABELS = {'CASHBOX': 'صندوق', 'BANK': 'بانک'}
CODE_PREFIX = {'CASHBOX': 'CA', 'BANK': 'TR'}


class TreasuryManagementWindow(QDialog):
    data_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.repository = TreasuryRepository(db)
        self.current_account_id: Optional[int] = None
        permissions = set(user_data.get('permissions', []) or [])
        self.can_manage = 'finance.manage' in permissions or user_data.get('role_code') == 'ADMIN'
        self.setWindowTitle('مدیریت صندوق / بانک تفصیلی')
        self.resize(1400, 820)
        self._build_ui()
        self.clear_form()
        self._apply_permissions()
        self.refresh_accounts()
        self.refresh_ledger_tab()

    # ==================== ساخت UI ====================
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # هدر
        header = QFrame()
        header.setObjectName('Card')
        hl = QVBoxLayout(header)
        title = QLabel('مدیریت صندوق / بانک تفصیلی')
        title.setObjectName('Title')
        subtitle = QLabel('تعریف، ویرایش و حسابرسی گردش صندوق و حساب‌های بانکی شرکت')
        subtitle.setObjectName('Muted')
        hl.addWidget(title); hl.addWidget(subtitle)
        today_lbl = QLabel('امروز: ' + jalali_date_display_from_iso(QDate.currentDate().toString('yyyy-MM-dd')))
        today_lbl.setStyleSheet('color:#f59e0b;font-size:18px;font-weight:bold;')
        today_lbl.setAlignment(Qt.AlignCenter)
        hl.addWidget(today_lbl)
        root.addWidget(header)

        # تب‌ها
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { padding: 8px 18px; min-width: 120px; }")

        self.tab_form = QWidget()
        self.tab_list = QWidget()
        self.tab_ledger = QWidget()
        self.tabs.addTab(self.tab_form, '📝 فرم')
        self.tabs.addTab(self.tab_list, '📋 لیست حساب‌ها')
        self.tabs.addTab(self.tab_ledger, '📊 گردش حسابرسی')

        self._build_form_tab()
        self._build_list_tab()
        self._build_ledger_tab()

        root.addWidget(self.tabs)

    def _build_form_tab(self):
        lay = QVBoxLayout(self.tab_form)
        lay.setContentsMargins(10, 10, 10, 10)
        form_group = QGroupBox('تعریف / ویرایش حساب')
        fl = QVBoxLayout(form_group)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14); grid.setVerticalSpacing(10)

        self.code_edit = QLineEdit(); self.code_edit.setPlaceholderText('تولید خودکار (CA/TR)')
        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItem('صندوق', 'CASHBOX')
        self.type_combo.addItem('بانک', 'BANK')
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.bank_name_edit = QLineEdit()
        self.account_number_edit = QLineEdit()
        self.iban_edit = QLineEdit()
        self.card_number_edit = QLineEdit()
        self.branch_name_edit = QLineEdit()
        self.branch_code_edit = QLineEdit()
        self.opening_balance_edit = QLineEdit()
        self.opening_balance_edit.setPlaceholderText('فقط در اولین ثبت قابل تنظیم است')
        self.opening_balance_edit.textChanged.connect(self._format_opening_balance)
        self.current_balance_label = QLabel('0 ریال')
        self.current_balance_label.setStyleSheet('color:#2563eb;font-weight:bold;font-size:14px;')
        self.is_active_checkbox = QCheckBox('فعال')
        self.is_active_checkbox.setChecked(True)
        self.description_edit = QTextEdit()
        self.description_edit.setMinimumHeight(80)
        self.description_edit.setMaximumHeight(120)

        grid.addWidget(QLabel('کد:'), 0, 0)
        grid.addWidget(self.code_edit, 0, 1)
        grid.addWidget(QLabel('نام حساب:'), 0, 2)
        grid.addWidget(self.name_edit, 0, 3)
        grid.addWidget(QLabel('نوع:'), 1, 0)
        grid.addWidget(self.type_combo, 1, 1)
        grid.addWidget(QLabel('مانده فعلی:'), 1, 2)
        grid.addWidget(self.current_balance_label, 1, 3)
        grid.addWidget(QLabel('نام بانک:'), 2, 0)
        grid.addWidget(self.bank_name_edit, 2, 1)
        grid.addWidget(QLabel('شماره حساب:'), 2, 2)
        grid.addWidget(self.account_number_edit, 2, 3)
        grid.addWidget(QLabel('شماره شبا:'), 3, 0)
        grid.addWidget(self.iban_edit, 3, 1)
        grid.addWidget(QLabel('شماره کارت:'), 3, 2)
        grid.addWidget(self.card_number_edit, 3, 3)
        grid.addWidget(QLabel('نام شعبه:'), 4, 0)
        grid.addWidget(self.branch_name_edit, 4, 1)
        grid.addWidget(QLabel('کد شعبه:'), 4, 2)
        grid.addWidget(self.branch_code_edit, 4, 3)
        grid.addWidget(QLabel('موجودی اولیه (ریال):'), 5, 0)
        grid.addWidget(self.opening_balance_edit, 5, 1)
        grid.addWidget(self.is_active_checkbox, 5, 2, 1, 2)
        self.unlock_opening_cb = QCheckBox('🔓 ویرایش موجودی اولیه (فقط با تأیید)')
        self.unlock_opening_cb.setStyleSheet('color:#f59e0b;')
        self.unlock_opening_cb.stateChanged.connect(self._toggle_opening_lock)
        grid.addWidget(self.unlock_opening_cb, 6, 0, 1, 4)

        fl.addLayout(grid)
        fl.addWidget(QLabel('توضیحات:'))
        fl.addWidget(self.description_edit)
        self.meta_label = QLabel('وضعیت رکورد: جدید | 💡 برای ویرایش، در تب «لیست حساب‌ها» روی حساب کلیک کنید')
        self.meta_label.setObjectName('Muted')
        fl.addWidget(self.meta_label)

        btns = QHBoxLayout()
        self.new_button = QPushButton('✨ فرم جدید')
        self.new_button.setObjectName('SecondaryButton')
        self.new_button.clicked.connect(self.clear_form)
        self.save_button = QPushButton('💾 ذخیره')
        self.save_button.setObjectName('PrimaryButton')
        self.save_button.clicked.connect(self.save_account)
        self.delete_button = QPushButton('🗑 حذف / غیرفعال‌سازی')
        self.delete_button.setObjectName('SecondaryButton')
        self.delete_button.clicked.connect(self.delete_account)
        btns.addWidget(self.new_button)
        btns.addStretch()
        btns.addWidget(self.delete_button)
        btns.addWidget(self.save_button)
        fl.addLayout(btns)
        lay.addWidget(form_group)

    def _build_list_tab(self):
        lay = QVBoxLayout(self.tab_list)
        lay.setContentsMargins(10, 10, 10, 10)

        # Toolbar
        toolbar = QFrame()
        toolbar.setObjectName('Card')
        tl = QHBoxLayout(toolbar)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('جستجو بر اساس کد، نام، بانک یا شماره حساب...')
        self.search_edit.textChanged.connect(self.refresh_accounts)
        self.active_filter_combo = QComboBox()
        self.active_filter_combo.addItem('همه وضعیت‌ها', 'ALL')
        self.active_filter_combo.addItem('فقط فعال', 'ACTIVE')
        self.active_filter_combo.addItem('فقط غیرفعال', 'INACTIVE')
        self.active_filter_combo.currentIndexChanged.connect(self.refresh_accounts)
        refresh_btn = QPushButton('🔄 بروزرسانی')
        refresh_btn.setObjectName('SecondaryButton')
        refresh_btn.clicked.connect(self.refresh_accounts)
        tl.addWidget(QLabel('جستجو:'))
        tl.addWidget(self.search_edit, 1)
        tl.addWidget(QLabel('وضعیت:'))
        tl.addWidget(self.active_filter_combo)
        tl.addWidget(refresh_btn)
        lay.addWidget(toolbar)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(['شناسه', 'کد', 'نام', 'نوع', 'بانک', 'مانده فعلی', 'وضعیت'])
        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._load_selected_account)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(lambda: self.tabs.setCurrentIndex(0))
        lay.addWidget(self.table)

    def _build_ledger_tab(self):
        lay = QVBoxLayout(self.tab_ledger)
        lay.setContentsMargins(10, 10, 10, 10)

        # فیلترها
        flt = QHBoxLayout()
        flt.addWidget(QLabel('حساب:'))
        self.ledger_acc_combo = QComboBox()
        self.ledger_acc_combo.setMinimumWidth(320)
        self.ledger_acc_combo.currentIndexChanged.connect(self.refresh_ledger_tab)
        flt.addWidget(self.ledger_acc_combo)
        flt.addWidget(QLabel('از تاریخ:'))
        self.ledger_from = QDateEdit(QDate.currentDate().addMonths(-3))
        self.ledger_from.setCalendarPopup(True)
        self.ledger_from.setDisplayFormat('yyyy-MM-dd')
        self.ledger_from.dateChanged.connect(self.refresh_ledger_tab)
        flt.addWidget(self.ledger_from)
        self.ledger_from_jalali = QLabel('-')
        self.ledger_from_jalali.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
        flt.addWidget(self.ledger_from_jalali)
        self.ledger_from.dateChanged.connect(self._update_ledger_jalali)
        flt.addWidget(QLabel('تا تاریخ:'))
        self.ledger_to = QDateEdit(QDate.currentDate())
        self.ledger_to.setCalendarPopup(True)
        self.ledger_to.setDisplayFormat('yyyy-MM-dd')
        self.ledger_to.dateChanged.connect(self.refresh_ledger_tab)
        flt.addWidget(self.ledger_to)
        self.ledger_to_jalali = QLabel('-')
        self.ledger_to_jalali.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
        flt.addWidget(self.ledger_to_jalali)
        self.ledger_to.dateChanged.connect(self._update_ledger_jalali)
        led_refresh = QPushButton('🔄 بروزرسانی')
        led_refresh.setObjectName('SecondaryButton')
        led_refresh.clicked.connect(self.refresh_ledger_tab)
        flt.addWidget(led_refresh)
        lay.addLayout(flt)

        # جمع‌ها
        self.ledger_sum = QLabel('')
        self.ledger_sum.setStyleSheet('color:#f59e0b;font-weight:bold;padding:6px;font-size:13px;')
        lay.addWidget(self.ledger_sum)

        # جدول گردش
        self.ledger_table = QTableWidget(0, 12)
        self.ledger_table.setHorizontalHeaderLabels(
            ['تاریخ شمسی', 'حساب', 'نوع', 'روش', 'شماره سند', 'طرف حساب', 'شماره چک',
             'مبلغ (ریال)', 'معادل فارسی', 'مانده بعد', 'کنترل', 'شرح'])
        self.ledger_table.verticalHeader().setVisible(False)
        self.ledger_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ledger_table.setAlternatingRowColors(True)
        hv = self.ledger_table.horizontalHeader()
        hv.setSectionResizeMode(11, QHeaderView.Stretch)
        lay.addWidget(self.ledger_table)

        # دکمه‌های خروجی
        btn_row = QHBoxLayout()
        html_btn = QPushButton('🖨 چاپ / PDF')
        html_btn.setObjectName('PrimaryButton')
        html_btn.clicked.connect(self._export_ledger_html)
        xls_btn = QPushButton('📊 خروجی اکسل')
        xls_btn.setObjectName('SecondaryButton')
        xls_btn.clicked.connect(self._export_ledger_excel)
        close_btn = QPushButton('بستن')
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(html_btn)
        btn_row.addWidget(xls_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)
        self._update_ledger_jalali()

    # ==================== مجوزها ====================
    def _apply_permissions(self) -> None:
        if not self.can_manage:
            for w in [self.code_edit, self.name_edit, self.type_combo, self.bank_name_edit,
                      self.account_number_edit, self.iban_edit, self.card_number_edit,
                      self.branch_name_edit, self.branch_code_edit, self.opening_balance_edit,
                      self.is_active_checkbox, self.description_edit,
                      self.new_button, self.save_button, self.delete_button]:
                w.setEnabled(False)

    # ==================== فرمت و تولید کد ====================
    def _format_opening_balance(self) -> None:
        digits = ''.join(ch for ch in self.opening_balance_edit.text() if ch.isdigit())
        self.opening_balance_edit.blockSignals(True)
        self.opening_balance_edit.setText(f'{int(digits):,}' if digits else '')
        self.opening_balance_edit.blockSignals(False)

    def _int_from_text(self, value: str) -> int:
        digits = ''.join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else 0

    def _on_type_changed(self):
        self._toggle_bank_fields()
        if self.current_account_id is None:
            self._auto_generate_code()

    def _auto_generate_code(self):
        """تولید خودکار کد بر اساس نوع (CA-001 / TR-001) - فقط برای رکوردهای جدید"""
        if self.current_account_id is not None:
            return
        prefix = CODE_PREFIX.get(self.type_combo.currentData(), 'CA')
        try:
            with self.db.connect() as conn:
                row = conn.execute(
                    "SELECT code FROM treasury_accounts WHERE code LIKE ? ORDER BY id DESC LIMIT 1",
                    (f"{prefix}-%",)).fetchone()
                if row and row[0]:
                    try:
                        last_no = int(row[0].split('-', 1)[1])
                        new_no = last_no + 1
                    except (IndexError, ValueError):
                        new_no = 1
                else:
                    new_no = 1
                self.code_edit.setText(f"{prefix}-{new_no:03d}")
        except Exception:
            pass

    def _toggle_bank_fields(self) -> None:
        is_bank = self.type_combo.currentData() == 'BANK'
        for w in [self.bank_name_edit, self.account_number_edit, self.iban_edit,
                  self.card_number_edit, self.branch_name_edit, self.branch_code_edit]:
            w.setEnabled(is_bank and self.can_manage)
        if not is_bank:
            for w in [self.bank_name_edit, self.account_number_edit, self.iban_edit,
                      self.card_number_edit, self.branch_name_edit, self.branch_code_edit]:
                w.clear()

    def _collect_payload(self) -> Dict[str, Any]:
        return {
            'code': self.code_edit.text().strip(),
            'name': self.name_edit.text().strip(),
            'account_type': self.type_combo.currentData(),
            'bank_name': self.bank_name_edit.text().strip() or None,
            'account_number': self.account_number_edit.text().strip() or None,
            'iban': self.iban_edit.text().strip() or None,
            'card_number': self.card_number_edit.text().strip() or None,
            'branch_name': self.branch_name_edit.text().strip() or None,
            'branch_code': self.branch_code_edit.text().strip() or None,
            'opening_balance': self._int_from_text(self.opening_balance_edit.text()),
            'is_active': self.is_active_checkbox.isChecked(),
            'description': self.description_edit.toPlainText().strip() or None,
        }

    # ==================== فرم ====================
    def clear_form(self) -> None:
        self.current_account_id = None
        self.code_edit.clear()
        self.name_edit.clear()
        self.type_combo.setCurrentIndex(0)
        for w in [self.bank_name_edit, self.account_number_edit, self.iban_edit,
                  self.card_number_edit, self.branch_name_edit, self.branch_code_edit,
                  self.opening_balance_edit, self.description_edit]:
            w.clear()
        self.current_balance_label.setText('0 ریال')
        self.is_active_checkbox.setChecked(True)
        self.meta_label.setText('وضعیت رکورد: جدید')
        self._toggle_bank_fields()
        # قفل موجودی اولیه برداشته شود (رکورد جدید)
        self.opening_balance_edit.setReadOnly(False)
        self.opening_balance_edit.setStyleSheet('')
        self.unlock_opening_cb.blockSignals(True)
        self.unlock_opening_cb.setChecked(False)
        self.unlock_opening_cb.blockSignals(False)
        # کد خودکار
        self._auto_generate_code()
        self.table.clearSelection()

    def _toggle_opening_lock(self, state) -> None:
        if self.current_account_id is None:
            return
        unlocked = bool(state)
        self.opening_balance_edit.setReadOnly(not unlocked)
        self.opening_balance_edit.setStyleSheet('' if unlocked else 'background-color:#f1f5f9;color:#64748b;')

    def _auto_fix_balances(self):
        try:
            with self.db.connect() as _c:
                _c.execute("UPDATE treasury_accounts SET current_balance = CASE "
                           "WHEN EXISTS (SELECT 1 FROM treasury_transactions tt WHERE tt.treasury_account_id = treasury_accounts.id) "
                           "THEN COALESCE((SELECT SUM(CASE WHEN transaction_type='IN' THEN amount ELSE -amount END) "
                           "FROM treasury_transactions tt WHERE tt.treasury_account_id = treasury_accounts.id), 0) "
                           "ELSE COALESCE(opening_balance,0) END")
                _c.commit()
        except Exception:
            pass

    def refresh_accounts(self) -> None:
        self._auto_fix_balances()
        rows = self.repository.list_accounts(self.search_edit.text(), self.active_filter_combo.currentData())
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [
                str(row['id']), row['code'], row['name'],
                TYPE_LABELS.get(row['account_type'], row['account_type']),
                row.get('bank_name') or '-',
                f"{int(row.get('current_balance') or 0):,} ریال",
                'فعال' if row.get('is_active') else 'غیرفعال',
            ]
            for col, value in enumerate(values):
                it = QTableWidgetItem(str(value))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, col, it)
        self.table.resizeColumnsToContents()
        # بروزرسانی کمبو تب حسابرسی
        self._populate_ledger_combo()

    def _select_account_row(self, account_id: int) -> None:
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item and str(item.text()) == str(account_id):
                self.table.selectRow(r)
                return

    def _load_selected_account(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        account = self.repository.get_account(int(item.text()))
        if not account:
            return
        self.current_account_id = account['id']
        self.code_edit.setText(account.get('code') or '')
        self.name_edit.setText(account.get('name') or '')
        self.type_combo.setCurrentIndex(0 if account.get('account_type') == 'CASHBOX' else 1)
        self.bank_name_edit.setText(account.get('bank_name') or '')
        self.account_number_edit.setText(account.get('account_number') or '')
        self.iban_edit.setText(account.get('iban') or '')
        self.card_number_edit.setText(account.get('card_number') or '')
        self.branch_name_edit.setText(account.get('branch_name') or '')
        self.branch_code_edit.setText(account.get('branch_code') or '')
        self.opening_balance_edit.setText(f"{int(account.get('opening_balance') or 0):,}")
        self.current_balance_label.setText(f"{int(account.get('current_balance') or 0):,} ریال")
        self.is_active_checkbox.setChecked(bool(account.get('is_active')))
        self.description_edit.setPlainText(account.get('description') or '')
        created_j = jalali_date_display_from_iso(str(account.get('created_at'))[:10]) if account.get('created_at') else '-'
        updated_j = jalali_date_display_from_iso(str(account.get('updated_at'))[:10]) if account.get('updated_at') else '-'
        self.meta_label.setText(f"شناسه: {account['id']} | ایجاد: {created_j} | بروزرسانی: {updated_j}")
        self._toggle_bank_fields()
        # [قفل امن] موجودی اولیه خاکستری است؛ در صورت نیاز با چک‌باکس باز شود
        self.opening_balance_edit.setReadOnly(True)
        self.opening_balance_edit.setStyleSheet('background-color:#f1f5f9;color:#64748b;')
        self.unlock_opening_cb.blockSignals(True)
        self.unlock_opening_cb.setChecked(False)
        self.unlock_opening_cb.blockSignals(False)
        # سوئیچ به تب فرم
        self.tabs.setCurrentIndex(0)

    # ==================== تب حسابرسی ====================
    def _populate_ledger_combo(self):
        try:
            with self.db.connect() as conn:
                rows = conn.execute(
                    "SELECT id, code, name, account_type FROM treasury_accounts "
                    "WHERE is_active=1 ORDER BY account_type, code").fetchall()
            self.ledger_acc_combo.blockSignals(True)
            self.ledger_acc_combo.clear()
            self.ledger_acc_combo.addItem('📒 همه حساب‌ها', None)
            for r in rows:
                self.ledger_acc_combo.addItem(
                    f"{r[1]} | {r[2]} ({TYPE_LABELS.get(r[3], r[3])})", r[0])
            self.ledger_acc_combo.blockSignals(False)
        except Exception:
            pass

    def _doc_no(self, conn, st, sid):
        try:
            if st == 'EXPENSE':
                r = conn.execute("SELECT expense_no FROM expenses WHERE id=?", (sid,)).fetchone()
            elif st in ('PAYMENT', 'PAYMENT_ENTRY', 'FINANCE'):
                r = conn.execute(
                    "SELECT fd.finance_no FROM payment_entries pe "
                    "JOIN financial_documents fd ON fd.id=pe.financial_document_id "
                    "WHERE pe.id=?", (sid,)).fetchone()
            elif st in ('INBOUND_RECEIPT',):
                r = conn.execute("SELECT receipt_no FROM warehouse_receipts WHERE id=?", (sid,)).fetchone()
            elif st in ('OUTBOUND_ISSUE',):
                r = conn.execute("SELECT issue_no FROM warehouse_issues WHERE id=?", (sid,)).fetchone()
            else:
                r = None
            return r[0] if r and r[0] else (st or '-')
        except Exception:
            return st or '-'

    def _update_ledger_jalali(self):
        try:
            self.ledger_from_jalali.setText(jalali_date_display_from_iso(self.ledger_from.date().toString('yyyy-MM-dd')))
            self.ledger_to_jalali.setText(jalali_date_display_from_iso(self.ledger_to.date().toString('yyyy-MM-dd')))
        except Exception:
            pass

    def _fa_words(self, n):
        try:
            n = int(n)
        except Exception:
            return '-'
        if n == 0:
            return 'صفر ریال'
        ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه', 'ده', 'یازده',
                'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']
        tens = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
        hunds = ['', 'یکصد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']
        scales = ['', 'هزار', 'میلیون', 'میلیارد', 'بیلیون']

        def three(x):
            parts = []
            h, r = divmod(x, 100)
            if h:
                parts.append(hunds[h])
            if r:
                if r < 20:
                    parts.append(ones[r])
                else:
                    t, o = divmod(r, 10)
                    parts.append(tens[t])
                    if o:
                        parts.append(ones[o])
            return ' و '.join(parts)

        chunks, i = [], 0
        while n and i < len(scales):
            n, rem = divmod(n, 1000)
            if rem:
                chunks.append(three(rem) + (' ' + scales[i] if scales[i] else ''))
            i += 1
        return ' و '.join(reversed(chunks)) + ' ریال'

    def _incomplete_flag(self, r):
        m = (r.get('method') or '')
        if 'چک' in m and not (r.get('check_no') or ''):
            return True
        if not (r.get('desc') or '') and not (r.get('person') or ''):
            return True
        if int(r.get('amount') or 0) <= 0:
            return True
        return False

    def refresh_ledger_tab(self):
        acc_id = self.ledger_acc_combo.currentData()
        d1 = self.ledger_from.date().toString('yyyy-MM-dd')
        d2 = self.ledger_to.date().toString('yyyy-MM-dd')
        self._ledger_rows = []
        try:
            with self.db.connect() as conn:
                txs = conn.execute(
                    "SELECT tt.transaction_date, tt.transaction_type, tt.amount, tt.balance_after, "
                    "tt.description, tt.source_type, tt.source_id, "
                    "(ta.code || ' | ' || ta.name) AS acc_name, "
                    "pm.name, fd.finance_no, (p.first_name || ' ' || p.last_name), pe.check_no "
                    "FROM treasury_transactions tt "
                    "JOIN treasury_accounts ta ON ta.id = tt.treasury_account_id "
                    "LEFT JOIN payment_entries pe ON tt.source_type IN ('PAYMENT_ENTRY','PAYMENT') AND pe.id = tt.source_id "
                    "LEFT JOIN payment_methods pm ON pm.id = pe.payment_method_id "
                    "LEFT JOIN financial_documents fd ON fd.id = pe.financial_document_id "
                    "LEFT JOIN persons p ON p.id = fd.counterparty_person_id "
                    + ("WHERE " + ("tt.treasury_account_id=? AND " if acc_id else "") +
                     "tt.transaction_date BETWEEN ? AND ? "
                     "ORDER BY tt.transaction_date, tt.id"),
                    ((acc_id, d1, d2) if acc_id else (d1, d2))).fetchall()
                for t in txs:
                    self._ledger_rows.append({
                        'date': t[0], 'type': t[1], 'amount': t[2], 'after': t[3],
                        'desc': t[4], 'src': t[5], 'doc': self._doc_no(conn, t[5], t[6]),
                        'acc': t[7], 'method': t[8], 'finance_no': t[9], 'person': (t[10] or '').strip(),
                        'check_no': t[11]})
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e))
            return
        tin = sum(int(r['amount'] or 0) for r in self._ledger_rows if r['type'] == 'IN')
        tout = sum(int(r['amount'] or 0) for r in self._ledger_rows if r['type'] != 'IN')
        checks = [r for r in self._ledger_rows if (r['check_no'] or '') or ('چک' in (r['method'] or ''))]
        bad = [r for r in self._ledger_rows if self._incomplete_flag(r)]
        self.ledger_sum.setText(
            f'📥 دریافت: {tin:,} ریال   |   📤 پرداخت: {tout:,} ریال   |   🧮 خالص: {tin - tout:,} ریال   |   '
            f'📄 تعداد چک: {len(checks)}   |   ⚠️ موارد ناقص: {len(bad)}')
        self.ledger_table.setRowCount(len(self._ledger_rows))
        for i, r in enumerate(self._ledger_rows):
            flag = self._incomplete_flag(r)
            vals = [
                jalali_date_display_from_iso(r['date'][:10]) if r['date'] else '-',
                r['acc'] or '-',
                '📥 دریافت' if r['type'] == 'IN' else '📤 پرداخت',
                r['method'] or ('هزینه' if r['src'] == 'EXPENSE' else '-'),
                r['doc'],
                r['person'] or '-',
                r['check_no'] or '-',
                f"{int(r['amount'] or 0):,}",
                self._fa_words(int(r['amount'] or 0)),
                f"{int(r['after'] or 0):,}",
                '⚠️ ناقص' if flag else '✔ کامل',
                r['desc'] or '-',
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c == 2:
                    it.setForeground(Qt.darkGreen if r['type'] == 'IN' else Qt.darkRed)
                if c == 10:
                    it.setForeground(Qt.red if flag else Qt.darkGreen)
                self.ledger_table.setItem(i, c, it)
        self.ledger_table.resizeColumnsToContents()

    def _export_ledger_html(self):
        rows = getattr(self, '_ledger_rows', [])
        if not rows:
            QMessageBox.information(self, 'خروجی', 'داده‌ای نیست.')
            return
        acc_txt = self.ledger_acc_combo.currentText()
        body = ''
        for r in rows:
            body += (f"<tr><td>{jalali_date_display_from_iso(r['date'][:10]) if r['date'] else '-'}</td>"
                     f"<td>{'دریافت' if r['type']=='IN' else 'پرداخت'}</td><td>{r['method'] or '-'}</td>"
                     f"<td>{r['doc']}</td><td>{r['person'] or '-'}</td><td>{r['check_no'] or '-'}</td>"
                     f"<td>{int(r['amount'] or 0):,}</td><td>{int(r['after'] or 0):,}</td><td>{r['desc'] or '-'}</td></tr>")
        html = f"""<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8">
<title>گردش حساب</title><style>
body{{font-family:Tahoma;padding:20px;background:#f5f5f5;}}
.c{{background:white;padding:25px;border-radius:8px;}}
h1{{text-align:center;border-bottom:3px solid #2563eb;padding-bottom:10px;}}
table{{width:100%;border-collapse:collapse;}}
th{{background:#46505f;color:white;padding:10px;}}
td{{padding:8px;border-bottom:1px solid #e2e8f0;text-align:center;}}
.print-btn{{position:fixed;top:20px;left:20px;padding:12px 24px;background:#9333ea;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:bold;}}
</style></head><body>
<button class="print-btn" onclick="window.print()">🖨 چاپ / ذخیره PDF</button>
<div class="c">
<h1>گردش حساب: {acc_txt}</h1>
<p style="text-align:center">{self.ledger_from.date().toString('yyyy-MM-dd')} تا {self.ledger_to.date().toString('yyyy-MM-dd')}</p>
<p style="text-align:center;color:#f59e0b;font-weight:bold">{self.ledger_sum.text()}</p>
<table><thead><tr><th>تاریخ</th><th>نوع</th><th>روش</th><th>سند</th><th>طرف حساب</th><th>چک</th><th>مبلغ</th><th>مانده بعد</th><th>شرح</th></tr></thead>
<tbody>{body}</tbody></table>
</div></body></html>"""
        from PyQt5.QtWidgets import QFileDialog
        import webbrowser
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره HTML', 'گردش_حساب.html', 'HTML (*.html)')
        if path:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(html)
            webbrowser.open('file:///' + path)

    def _export_ledger_excel(self):
        rows = getattr(self, '_ledger_rows', [])
        if not rows:
            QMessageBox.information(self, 'خروجی', 'داده‌ای نیست.')
            return
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره CSV', 'گردش_حساب.csv', 'CSV (*.csv)')
        if not path:
            return
        if not path.lower().endswith('.csv'):
            path += '.csv'
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            f.write('تاریخ,نوع,روش,سند,طرف حساب,شماره چک,مبلغ,مانده بعد,شرح\n')
            for r in rows:
                desc = (r['desc'] or '-').replace(',', '،')
                f.write(f"{jalali_date_display_from_iso(r['date'][:10]) if r['date'] else '-'},"
                        f"{'دریافت' if r['type']=='IN' else 'پرداخت'},{r['method'] or '-'},"
                        f"{r['doc']},{(r['person'] or '-').replace(',', '،')},{r['check_no'] or '-'},"
                        f"{int(r['amount'] or 0)},{int(r['after'] or 0)},{desc}\n")
        QMessageBox.information(self, 'اکسل', f'خروجی ذخیره شد:\n{path}')

    # ==================== ذخیره ====================
    def save_account(self) -> None:
        if not self.can_manage:
            return
        payload = self._collect_payload()
        if not payload['name']:
            QMessageBox.warning(self, 'صندوق / بانک', 'نام حساب الزامی است.')
            return
        if not payload['code']:
            QMessageBox.warning(self, 'صندوق / بانک', 'کد حساب الزامی است.')
            return
        try:
            if self.current_account_id is None:
                saved = self.repository.create_account(payload, user_id=self.user_data.get('id'))
                msg = f"حساب «{saved.get('name')}» ثبت شد."
                self.current_account_id = saved.get('id')
            else:
                saved = self.repository.update_account(self.current_account_id, payload,
                                                       user_id=self.user_data.get('id'))
                msg = f"حساب «{saved.get('name')}» بروزرسانی شد."
        except ValidationError as exc:
            QMessageBox.warning(self, 'صندوق / بانک', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'ذخیره حساب:\n{exc}')
            return
        # همگام‌سازی مانده فعلی
        try:
            with self.db.connect() as _c:
                _c.execute(
                    "UPDATE treasury_accounts SET current_balance = "
                    "COALESCE(opening_balance,0) + COALESCE((SELECT SUM(CASE WHEN transaction_type='IN' THEN amount ELSE -amount END) "
                    "FROM treasury_transactions tt WHERE tt.treasury_account_id = treasury_accounts.id), 0) "
                    "WHERE id = ?", (saved.get('id'),))
                _c.commit()
        except Exception:
            pass
        QMessageBox.information(self, 'ذخیره موفق', msg)
        self.refresh_accounts()
        self.refresh_ledger_tab()
        self._select_account_row(saved.get('id'))
        self.data_changed.emit()

    def delete_account(self) -> None:
        if not self.can_manage:
            return
        if self.current_account_id is None:
            QMessageBox.information(self, 'صندوق / بانک', 'ابتدا یک حساب را از جدول انتخاب کنید.')
            return
        answer = QMessageBox.question(
            self, 'تأیید حذف', 'آیا از حذف / غیرفعال‌سازی این حساب مطمئن هستید؟',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            action, result = self.repository.delete_account(self.current_account_id, user_id=self.user_data.get('id'))
        except ValidationError as exc:
            QMessageBox.warning(self, 'صندوق / بانک', str(exc))
            return
        if action == 'deleted':
            QMessageBox.information(self, 'حذف', f"حساب «{result.get('name')}» حذف شد.")
        else:
            QMessageBox.information(
                self, 'غیرفعال شد',
                f"حساب «{result.get('name')}» دارای گردش مالی است و به‌صورت امن غیرفعال شد.")
        self.refresh_accounts()
        self.data_changed.emit()
