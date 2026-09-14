# -*- coding: utf-8 -*-
"""
TreasuryManagementWindow - اصلاح‌شده

⚠️ نسخه اصلاح‌شده (بازبینی ۱۴۰۵/۰۵/۱۱):
  [FIX] تعمیر کامل تخریب‌های کپی-پیست (سینتکس): __init__، _build_ui، self.search_edit، < و ...
  [UX]  جلوگیری از پاک شدن فرم هنگام جستجو/فیلتر (اگر کاربر در حال ویرایش است،
        auto-select ردیف اول دیگر فرم را با حساب دیگری بازنویسی نمی‌کند)
  [UX]  بعد از ثبت/ویرایش، همان ردیف در جدول انتخاب می‌شود (قبلاً به ردیف اول می‌پرید)
  [C4]  هماهنگ با TreasuryRepository اصلاح‌شده: حساب دارای گردش فقط غیرفعال می‌شود
"""

from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from app.core.database import DatabaseManager
from app.core.validators import ValidationError
from app.repositories.treasury_repository import TreasuryRepository


TYPE_LABELS = {'CASHBOX': 'صندوق', 'BANK': 'بانک'}


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
        self.resize(1500, 860)
        self._build_ui()
        self.clear_form()
        self._apply_permissions()
        self.refresh_accounts()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName('Card')
        hl = QVBoxLayout(header)
        title = QLabel('مدیریت صندوق / بانک تفصیلی')
        title.setObjectName('Title')
        subtitle = QLabel('تعریف صندوق‌ها و حساب‌های بانکی شرکت و مشاهده مانده و گردش آنها')
        subtitle.setObjectName('Muted')
        hl.addWidget(title)
        hl.addWidget(subtitle)
        root.addWidget(header)

        toolbar = QFrame()
        toolbar.setObjectName('Card')
        tl = QHBoxLayout(toolbar)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('جستجو بر اساس کد، نام، بانک، شماره حساب یا شبا...')
        self.search_edit.textChanged.connect(self.refresh_accounts)
        self.active_filter_combo = QComboBox()
        self.active_filter_combo.addItem('همه وضعیت‌ها', 'ALL')
        self.active_filter_combo.addItem('فقط فعال', 'ACTIVE')
        self.active_filter_combo.addItem('فقط غیرفعال', 'INACTIVE')
        self.active_filter_combo.currentIndexChanged.connect(self.refresh_accounts)
        refresh_btn = QPushButton('بروزرسانی')
        refresh_btn.setObjectName('SecondaryButton')
        refresh_btn.clicked.connect(self.refresh_accounts)
        tl.addWidget(QLabel('جستجو:'))
        tl.addWidget(self.search_edit, 1)
        tl.addWidget(QLabel('وضعیت:'))
        tl.addWidget(self.active_filter_combo)
        tl.addWidget(refresh_btn)
        root.addWidget(toolbar)

        content = QHBoxLayout()
        content.setSpacing(14)

        form_group = QGroupBox('فرم صندوق / بانک')
        fl = QVBoxLayout(form_group)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItem('صندوق', 'CASHBOX')
        self.type_combo.addItem('بانک', 'BANK')
        self.type_combo.currentIndexChanged.connect(self._toggle_bank_fields)
        self.bank_name_edit = QLineEdit()
        self.account_number_edit = QLineEdit()
        self.iban_edit = QLineEdit()
        self.card_number_edit = QLineEdit()
        self.branch_name_edit = QLineEdit()
        self.branch_code_edit = QLineEdit()
        self.opening_balance_edit = QLineEdit()
        self.opening_balance_edit.textChanged.connect(self._format_opening_balance)
        self.current_balance_label = QLabel('0 ریال')
        self.current_balance_label.setObjectName('Alert')
        self.is_active_checkbox = QCheckBox('فعال')
        self.is_active_checkbox.setChecked(True)
        self.description_edit = QTextEdit()
        self.description_edit.setMinimumHeight(90)

        grid.addWidget(QLabel('کد'), 0, 0)
        grid.addWidget(self.code_edit, 0, 1)
        grid.addWidget(QLabel('نام'), 0, 2)
        grid.addWidget(self.name_edit, 0, 3)
        grid.addWidget(QLabel('نوع'), 1, 0)
        grid.addWidget(self.type_combo, 1, 1)
        grid.addWidget(QLabel('مانده فعلی'), 1, 2)
        grid.addWidget(self.current_balance_label, 1, 3)
        grid.addWidget(QLabel('نام بانک'), 2, 0)
        grid.addWidget(self.bank_name_edit, 2, 1)
        grid.addWidget(QLabel('شماره حساب'), 2, 2)
        grid.addWidget(self.account_number_edit, 2, 3)
        grid.addWidget(QLabel('شماره شبا'), 3, 0)
        grid.addWidget(self.iban_edit, 3, 1)
        grid.addWidget(QLabel('شماره کارت'), 3, 2)
        grid.addWidget(self.card_number_edit, 3, 3)
        grid.addWidget(QLabel('نام شعبه'), 4, 0)
        grid.addWidget(self.branch_name_edit, 4, 1)
        grid.addWidget(QLabel('کد شعبه'), 4, 2)
        grid.addWidget(self.branch_code_edit, 4, 3)
        grid.addWidget(QLabel('موجودی اولیه'), 5, 0)
        grid.addWidget(self.opening_balance_edit, 5, 1)
        grid.addWidget(self.is_active_checkbox, 5, 2, 1, 2)
        fl.addLayout(grid)
        fl.addWidget(QLabel('توضیحات'))
        fl.addWidget(self.description_edit)
        self.meta_label = QLabel('وضعیت رکورد: جدید')
        self.meta_label.setObjectName('Muted')
        fl.addWidget(self.meta_label)

        btns = QHBoxLayout()
        self.new_button = QPushButton('فرم جدید')
        self.new_button.setObjectName('SecondaryButton')
        self.new_button.clicked.connect(self.clear_form)
        self.save_button = QPushButton('ذخیره')
        self.save_button.clicked.connect(self.save_account)
        self.delete_button = QPushButton('حذف / غیرفعال‌سازی')
        self.delete_button.setObjectName('SecondaryButton')
        self.delete_button.clicked.connect(self.delete_account)
        btns.addWidget(self.new_button)
        btns.addStretch()
        btns.addWidget(self.delete_button)
        btns.addWidget(self.save_button)
        fl.addLayout(btns)

        right = QVBoxLayout()
        list_group = QGroupBox('لیست صندوق‌ها و بانک‌ها')
        ll = QVBoxLayout(list_group)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(['شناسه', 'کد', 'نام', 'نوع', 'بانک', 'مانده فعلی', 'وضعیت'])
        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._load_selected_account)
        self.table.horizontalHeader().setStretchLastSection(True)
        ll.addWidget(self.table)
        right.addWidget(list_group)

        tx_group = QGroupBox('آخرین گردش‌های صندوق / بانک')
        txl = QVBoxLayout(tx_group)
        self.tx_table = QTableWidget(0, 6)
        self.tx_table.setHorizontalHeaderLabels(['تاریخ', 'نوع', 'منبع', 'مبلغ', 'مانده پس از ثبت', 'شرح'])
        self.tx_table.verticalHeader().setVisible(False)
        self.tx_table.horizontalHeader().setStretchLastSection(True)
        txl.addWidget(self.tx_table)
        right.addWidget(tx_group)

        content.addWidget(form_group, 5)
        content.addLayout(right, 6)
        root.addLayout(content)

    def _apply_permissions(self) -> None:
        if not self.can_manage:
            for widget in [
                self.code_edit, self.name_edit, self.type_combo, self.bank_name_edit, self.account_number_edit,
                self.iban_edit, self.card_number_edit, self.branch_name_edit, self.branch_code_edit,
                self.opening_balance_edit, self.is_active_checkbox, self.description_edit,
                self.new_button, self.save_button, self.delete_button,
            ]:
                widget.setEnabled(False)

    def _format_opening_balance(self) -> None:
        digits = ''.join(ch for ch in self.opening_balance_edit.text() if ch.isdigit())
        self.opening_balance_edit.blockSignals(True)
        self.opening_balance_edit.setText(f'{int(digits):,}' if digits else '')
        self.opening_balance_edit.blockSignals(False)

    def _int_from_text(self, value: str) -> int:
        digits = ''.join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else 0

    def _toggle_bank_fields(self) -> None:
        is_bank = self.type_combo.currentData() == 'BANK'
        for widget in [self.bank_name_edit, self.account_number_edit, self.iban_edit,
                       self.card_number_edit, self.branch_name_edit, self.branch_code_edit]:
            widget.setEnabled(is_bank and self.can_manage)
        if not is_bank:
            self.bank_name_edit.clear()
            self.account_number_edit.clear()
            self.iban_edit.clear()
            self.card_number_edit.clear()
            self.branch_name_edit.clear()
            self.branch_code_edit.clear()

    def _collect_payload(self) -> Dict[str, Any]:
        return {
            'code': self.code_edit.text(),
            'name': self.name_edit.text(),
            'account_type': self.type_combo.currentData(),
            'bank_name': self.bank_name_edit.text(),
            'account_number': self.account_number_edit.text(),
            'iban': self.iban_edit.text(),
            'card_number': self.card_number_edit.text(),
            'branch_name': self.branch_name_edit.text(),
            'branch_code': self.branch_code_edit.text(),
            'opening_balance': self._int_from_text(self.opening_balance_edit.text()),
            'is_active': self.is_active_checkbox.isChecked(),
            'description': self.description_edit.toPlainText(),
        }

    # [UX] آیا فرم محتوای دست‌نخورده دارد؟ (برای جلوگیری از بازنویسی هنگام جستجو)
    def _form_has_content(self) -> bool:
        return bool(
            self.code_edit.text().strip()
            or self.name_edit.text().strip()
            or self.opening_balance_edit.text().strip()
            or self.description_edit.toPlainText().strip()
            or self.bank_name_edit.text().strip()
            or self.account_number_edit.text().strip()
        )

    def clear_form(self) -> None:
        self.current_account_id = None
        self.code_edit.clear()
        self.name_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.bank_name_edit.clear()
        self.account_number_edit.clear()
        self.iban_edit.clear()
        self.card_number_edit.clear()
        self.branch_name_edit.clear()
        self.branch_code_edit.clear()
        self.opening_balance_edit.clear()
        self.current_balance_label.setText('0 ریال')
        self.is_active_checkbox.setChecked(True)
        self.description_edit.clear()
        self.meta_label.setText('وضعیت رکورد: جدید')
        self.tx_table.setRowCount(0)
        self.table.clearSelection()
        self._toggle_bank_fields()

    def refresh_accounts(self) -> None:
        rows = self.repository.list_accounts(self.search_edit.text(), self.active_filter_combo.currentData())
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row['id']), row['code'], row['name'],
                TYPE_LABELS.get(row['account_type'], row['account_type']),
                row.get('bank_name') or '-',
                f"{int(row.get('current_balance') or 0):,} ریال",
                'فعال' if row.get('is_active') else 'غیرفعال',
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_index, col, item)
        self.table.resizeColumnsToContents()
        # [UX] فقط وقتی فرم خالی است ردیف اول خودکار انتخاب شود
        if rows and self.table.currentRow() < 0 and not self._form_has_content():
            self.table.selectRow(0)
        if not rows:
            self.clear_form()

    # [UX] انتخاب ردیف مشخص در جدول (بعد از ثبت/ویرایش)
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
        self.meta_label.setText(
            f"شناسه: {account['id']} | ایجاد: {account.get('created_at') or '-'} | "
            f"بروزرسانی: {account.get('updated_at') or '-'}"
        )
        self._toggle_bank_fields()

        transactions = account.get('transactions') or []
        self.tx_table.setRowCount(len(transactions))
        for row_index, tx in enumerate(transactions):
            values = [
                tx.get('transaction_date') or '-',
                'ورود' if tx.get('transaction_type') == 'IN' else 'خروج',
                tx.get('source_type') or '-',
                f"{int(tx.get('amount') or 0):,} ریال",
                f"{int(tx.get('balance_after') or 0):,} ریال",
                tx.get('description') or '-',
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tx_table.setItem(row_index, col, cell)
        self.tx_table.resizeColumnsToContents()

    def save_account(self) -> None:
        if not self.can_manage:
            return
        try:
            if self.current_account_id is None:
                saved = self.repository.create_account(self._collect_payload(), user_id=self.user_data.get('id'))
                msg = f"حساب «{saved.get('name')}» ثبت شد."
                # [UX] بعد از ثبت جدید، فرم روی همان حساب بماند
                self.current_account_id = saved.get('id')
            else:
                saved = self.repository.update_account(self.current_account_id, self._collect_payload(),
                                                       user_id=self.user_data.get('id'))
                msg = f"حساب «{saved.get('name')}» بروزرسانی شد."
        except ValidationError as exc:
            QMessageBox.warning(self, 'صندوق / بانک', str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'خطا', f'ذخیره حساب با خطا مواجه شد:\n{exc}')
            return
        QMessageBox.information(self, 'ذخیره موفق', msg)
        self.refresh_accounts()
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
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
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
                f"حساب «{result.get('name')}» دارای گردش مالی است و به‌صورت امن غیرفعال شد.",
            )
        self.refresh_accounts()
        self.data_changed.emit()
