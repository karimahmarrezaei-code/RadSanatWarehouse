"""
فرم مدیریت نقدینگی (واریز، برداشت، انتقال بین حساب‌ها) - نسخه اصلاح‌شده
"""
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QComboBox, QFormLayout,
    QMessageBox, QFrame, QDateEdit, QDoubleSpinBox,
    QTextEdit, QTabWidget, QWidget
)
from PyQt5.QtGui import QFont
import sqlite3


class CashTransferWindow(QDialog):
    """فرم مدیریت نقدینگی"""
    
    transfer_completed = pyqtSignal()
    
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.user_id = user_data.get('id', 1)
        self.setWindowTitle('مدیریت نقدینگی (واریز/برداشت/انتقال)')
        self.resize(750, 650)
        self.setLayoutDirection(Qt.RightToLeft)
        
        self.accounts = []
        self._load_accounts()
        self._build_ui()
    
    def _load_accounts(self):
        """بارگذاری حساب‌های نقدی فعال"""
        try:
            with self.db.connect() as conn:
                self.accounts = conn.execute('''
                    SELECT id, name, type, balance, bank_name
                    FROM cash_accounts 
                    WHERE is_active = 1
                    ORDER BY type, name
                ''').fetchall()
        except Exception as e:
            self.accounts = []
    
    def _get_account_balance(self, account_id):
        """دریافت موجودی حساب"""
        for acc in self.accounts:
            if acc['id'] == account_id:
                return acc['balance']
        return 0
    
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # هدر
        header = QFrame()
        header.setObjectName('Card')
        h_layout = QVBoxLayout(header)
        title = QLabel('مدیریت نقدینگی')
        title.setObjectName('Title')
        subtitle = QLabel('واریز به صندوق، برداشت از صندوق، انتقال بین حساب‌ها')
        subtitle.setObjectName('Muted')
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        root.addWidget(header)

        # تب‌ها
        self.tabs = QTabWidget()
        
        # تب ۱: واریز به صندوق
        deposit_tab = self._build_deposit_tab()
        self.tabs.addTab(deposit_tab, '💵 واریز به صندوق')
        
        # تب ۲: برداشت از صندوق
        withdraw_tab = self._build_withdraw_tab()
        self.tabs.addTab(withdraw_tab, '💸 برداشت از صندوق')
        
        # تب ۳: انتقال بین حساب‌ها
        transfer_tab = self._build_transfer_tab()
        self.tabs.addTab(transfer_tab, '🔄 انتقال بین حساب‌ها')
        
        root.addWidget(self.tabs)
        
        # دکمه بستن
        close_btn = QPushButton('بستن')
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)
    
    def _build_deposit_tab(self):
        """تب واریز به صندوق (از بانک به صندوق)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        form_group = QGroupBox('اطلاعات واریز')
        form_layout = QFormLayout(form_group)
        
        # تاریخ
        self.deposit_date = QDateEdit(QDate.currentDate())
        self.deposit_date.setCalendarPopup(True)
        self.deposit_date.setDisplayFormat('yyyy-MM-dd')
        form_layout.addRow('تاریخ:', self.deposit_date)
        
        # حساب مبدأ (بانک)
        self.deposit_from = QComboBox()
        self.deposit_from.addItem('-- انتخاب حساب مبدأ (بانک) --', None)
        bank_accounts = [acc for acc in self.accounts if acc['type'] == 'BANK']
        for acc in bank_accounts:
            balance_str = f"{acc['balance']:,.0f} ریال"
            self.deposit_from.addItem(
                f"{acc['name']} (موجودی: {balance_str})",
                acc['id']
            )
        form_layout.addRow('از حساب (بانک):', self.deposit_from)
        
        # حساب مقصد (صندوق)
        self.deposit_to = QComboBox()
        self.deposit_to.addItem('-- انتخاب صندوق مقصد --', None)
        cash_accounts = [acc for acc in self.accounts if acc['type'] == 'CASH']
        for acc in cash_accounts:
            balance_str = f"{acc['balance']:,.0f} ریال"
            self.deposit_to.addItem(
                f"{acc['name']} (موجودی: {balance_str})",
                acc['id']
            )
        form_layout.addRow('به صندوق:', self.deposit_to)
        
        # مبلغ
        self.deposit_amount = QDoubleSpinBox()
        self.deposit_amount.setRange(0, 999999999999)
        self.deposit_amount.setDecimals(0)
        self.deposit_amount.setSuffix(' ریال')
        self.deposit_amount.setGroupSeparatorShown(True)
        form_layout.addRow('مبلغ:', self.deposit_amount)
        
        # توضیحات
        self.deposit_desc = QTextEdit()
        self.deposit_desc.setMaximumHeight(60)
        self.deposit_desc.setPlaceholderText('توضیحات (اختیاری)')
        form_layout.addRow('توضیحات:', self.deposit_desc)
        
        layout.addWidget(form_group)
        
        # دکمه ثبت
        deposit_btn = QPushButton('ثبت واریز')
        deposit_btn.setObjectName('SuccessButton')
        deposit_btn.setMinimumHeight(45)
        deposit_btn.setFont(QFont('Tahoma', 12, QFont.Bold))
        deposit_btn.clicked.connect(self._execute_deposit)
        layout.addWidget(deposit_btn)
        
        layout.addStretch()
        return tab
    
    def _build_withdraw_tab(self):
        """تب برداشت از صندوق (از صندوق به بانک)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        form_group = QGroupBox('اطلاعات برداشت')
        form_layout = QFormLayout(form_group)
        
        # تاریخ
        self.withdraw_date = QDateEdit(QDate.currentDate())
        self.withdraw_date.setCalendarPopup(True)
        self.withdraw_date.setDisplayFormat('yyyy-MM-dd')
        form_layout.addRow('تاریخ:', self.withdraw_date)
        
        # حساب مبدأ (صندوق)
        self.withdraw_from = QComboBox()
        self.withdraw_from.addItem('-- انتخاب صندوق مبدأ --', None)
        cash_accounts = [acc for acc in self.accounts if acc['type'] == 'CASH']
        for acc in cash_accounts:
            balance_str = f"{acc['balance']:,.0f} ریال"
            self.withdraw_from.addItem(
                f"{acc['name']} (موجودی: {balance_str})",
                acc['id']
            )
        form_layout.addRow('از صندوق:', self.withdraw_from)
        
        # حساب مقصد (بانک)
        self.withdraw_to = QComboBox()
        self.withdraw_to.addItem('-- انتخاب حساب مقصد (بانک) --', None)
        bank_accounts = [acc for acc in self.accounts if acc['type'] == 'BANK']
        for acc in bank_accounts:
            balance_str = f"{acc['balance']:,.0f} ریال"
            self.withdraw_to.addItem(
                f"{acc['name']} (موجودی: {balance_str})",
                acc['id']
            )
        form_layout.addRow('به حساب (بانک):', self.withdraw_to)
        
        # مبلغ
        self.withdraw_amount = QDoubleSpinBox()
        self.withdraw_amount.setRange(0, 999999999999)
        self.withdraw_amount.setDecimals(0)
        self.withdraw_amount.setSuffix(' ریال')
        self.withdraw_amount.setGroupSeparatorShown(True)
        form_layout.addRow('مبلغ:', self.withdraw_amount)
        
        # توضیحات
        self.withdraw_desc = QTextEdit()
        self.withdraw_desc.setMaximumHeight(60)
        self.withdraw_desc.setPlaceholderText('توضیحات (اختیاری)')
        form_layout.addRow('توضیحات:', self.withdraw_desc)
        
        layout.addWidget(form_group)
        
        # دکمه ثبت
        withdraw_btn = QPushButton('ثبت برداشت')
        withdraw_btn.setObjectName('SuccessButton')
        withdraw_btn.setMinimumHeight(45)
        withdraw_btn.setFont(QFont('Tahoma', 12, QFont.Bold))
        withdraw_btn.clicked.connect(self._execute_withdraw)
        layout.addWidget(withdraw_btn)
        
        layout.addStretch()
        return tab
    
    def _build_transfer_tab(self):
        """تب انتقال بین حساب‌ها (دلخواه)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        form_group = QGroupBox('اطلاعات انتقال')
        form_layout = QFormLayout(form_group)
        
        # تاریخ
        self.transfer_date = QDateEdit(QDate.currentDate())
        self.transfer_date.setCalendarPopup(True)
        self.transfer_date.setDisplayFormat('yyyy-MM-dd')
        form_layout.addRow('تاریخ:', self.transfer_date)
        
        # حساب مبدأ
        self.transfer_from = QComboBox()
        self.transfer_from.addItem('-- انتخاب حساب مبدأ --', None)
        for acc in self.accounts:
            balance_str = f"{acc['balance']:,.0f} ریال"
            self.transfer_from.addItem(
                f"{acc['name']} ({acc['type']}) - موجودی: {balance_str}",
                acc['id']
            )
        form_layout.addRow('از حساب:', self.transfer_from)
        
        # حساب مقصد
        self.transfer_to = QComboBox()
        self.transfer_to.addItem('-- انتخاب حساب مقصد --', None)
        for acc in self.accounts:
            balance_str = f"{acc['balance']:,.0f} ریال"
            self.transfer_to.addItem(
                f"{acc['name']} ({acc['type']}) - موجودی: {balance_str}",
                acc['id']
            )
        form_layout.addRow('به حساب:', self.transfer_to)
        
        # مبلغ
        self.transfer_amount = QDoubleSpinBox()
        self.transfer_amount.setRange(0, 999999999999)
        self.transfer_amount.setDecimals(0)
        self.transfer_amount.setSuffix(' ریال')
        self.transfer_amount.setGroupSeparatorShown(True)
        form_layout.addRow('مبلغ:', self.transfer_amount)
        
        # توضیحات
        self.transfer_desc = QTextEdit()
        self.transfer_desc.setMaximumHeight(60)
        self.transfer_desc.setPlaceholderText('توضیحات (اختیاری)')
        form_layout.addRow('توضیحات:', self.transfer_desc)
        
        layout.addWidget(form_group)
        
        # دکمه ثبت
        transfer_btn = QPushButton('ثبت انتقال')
        transfer_btn.setObjectName('SuccessButton')
        transfer_btn.setMinimumHeight(45)
        transfer_btn.setFont(QFont('Tahoma', 12, QFont.Bold))
        transfer_btn.clicked.connect(self._execute_transfer)
        layout.addWidget(transfer_btn)
        
        layout.addStretch()
        return tab
    
    def _execute_deposit(self):
        """اجرای واریز به صندوق"""
        from_id = self.deposit_from.currentData()
        to_id = self.deposit_to.currentData()
        amount = self.deposit_amount.value()
        
        if not from_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً حساب مبدأ (بانک) را انتخاب کنید.')
            return
        
        if not to_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً صندوق مقصد را انتخاب کنید.')
            return
        
        if amount <= 0:
            QMessageBox.warning(self, 'خطا', 'مبلغ باید بیشتر از صفر باشد.')
            return
        
        # بررسی موجودی بانک
        from_balance = self._get_account_balance(from_id)
        if from_balance < amount:
            QMessageBox.warning(self, 'خطا', 
                f'موجودی حساب مبدأ کافی نیست!\n'
                f'موجودی: {from_balance:,.0f} ریال\n'
                f'مبلغ واریز: {amount:,.0f} ریال')
            return
        
        reply = QMessageBox.question(
            self, 'تأیید واریز',
            f'آیا از واریز {amount:,.0f} ریال از حساب مبدأ به صندوق مقصد اطمینان دارید؟',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            with self.db.connect() as conn:
                date_str = self.deposit_date.date().toString('yyyy-MM-dd')
                description = self.deposit_desc.toPlainText() or 'واریز به صندوق'
                
                # ثبت تراکنش خروجی از بانک
                conn.execute('''
                    INSERT INTO cash_transactions 
                    (transaction_date, transaction_type, amount, from_account_id,
                     to_account_id, reference_type, description)
                    VALUES (?, 'TRANSFER_OUT', ?, ?, ?, 'TRANSFER', ?)
                ''', (date_str, amount, from_id, to_id, description))
                
                # ثبت تراکنش ورودی به صندوق
                conn.execute('''
                    INSERT INTO cash_transactions 
                    (transaction_date, transaction_type, amount, from_account_id,
                     to_account_id, reference_type, description)
                    VALUES (?, 'TRANSFER_IN', ?, ?, ?, 'TRANSFER', ?)
                ''', (date_str, amount, from_id, to_id, description))
                
                # به‌روزرسانی موجودی بانک (کاهش)
                conn.execute('''
                    UPDATE cash_accounts 
                    SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (amount, from_id))
                
                # به‌روزرسانی موجودی صندوق (افزایش)
                conn.execute('''
                    UPDATE cash_accounts 
                    SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (amount, to_id))
                
                conn.commit()
                
                # بارگذاری مجدد حساب‌ها
                self._load_accounts()
                
                QMessageBox.information(self, 'موفق',
                    f'واریز {amount:,.0f} ریال با موفقیت انجام شد.\n\n'
                    f'از: {self.deposit_from.currentText().split(" (")[0]}\n'
                    f'به: {self.deposit_to.currentText().split(" (")[0]}')
                
                self.transfer_completed.emit()
                
                # پاک کردن فرم
                self.deposit_amount.setValue(0)
                self.deposit_desc.clear()
                
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ثبت واریز:\n{e}')
    
    def _execute_withdraw(self):
        """اجرای برداشت از صندوق"""
        from_id = self.withdraw_from.currentData()
        to_id = self.withdraw_to.currentData()
        amount = self.withdraw_amount.value()
        
        if not from_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً صندوق مبدأ را انتخاب کنید.')
            return
        
        if not to_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً حساب مقصد (بانک) را انتخاب کنید.')
            return
        
        if amount <= 0:
            QMessageBox.warning(self, 'خطا', 'مبلغ باید بیشتر از صفر باشد.')
            return
        
        # بررسی موجودی صندوق
        from_balance = self._get_account_balance(from_id)
        if from_balance < amount:
            QMessageBox.warning(self, 'خطا', 
                f'موجودی صندوق مبدأ کافی نیست!\n'
                f'موجودی: {from_balance:,.0f} ریال\n'
                f'مبلغ برداشت: {amount:,.0f} ریال')
            return
        
        reply = QMessageBox.question(
            self, 'تأیید برداشت',
            f'آیا از برداشت {amount:,.0f} ریال از صندوق به حساب مقصد اطمینان دارید؟',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            with self.db.connect() as conn:
                date_str = self.withdraw_date.date().toString('yyyy-MM-dd')
                description = self.withdraw_desc.toPlainText() or 'برداشت از صندوق'
                
                # ثبت تراکنش خروجی از صندوق
                conn.execute('''
                    INSERT INTO cash_transactions 
                    (transaction_date, transaction_type, amount, from_account_id,
                     to_account_id, reference_type, description)
                    VALUES (?, 'TRANSFER_OUT', ?, ?, ?, 'TRANSFER', ?)
                ''', (date_str, amount, from_id, to_id, description))
                
                # ثبت تراکنش ورودی به بانک
                conn.execute('''
                    INSERT INTO cash_transactions 
                    (transaction_date, transaction_type, amount, from_account_id,
                     to_account_id, reference_type, description)
                    VALUES (?, 'TRANSFER_IN', ?, ?, ?, 'TRANSFER', ?)
                ''', (date_str, amount, from_id, to_id, description))
                
                # به‌روزرسانی موجودی صندوق (کاهش)
                conn.execute('''
                    UPDATE cash_accounts 
                    SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (amount, from_id))
                
                # به‌روزرسانی موجودی بانک (افزایش)
                conn.execute('''
                    UPDATE cash_accounts 
                    SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (amount, to_id))
                
                conn.commit()
                
                # بارگذاری مجدد حساب‌ها
                self._load_accounts()
                
                QMessageBox.information(self, 'موفق',
                    f'برداشت {amount:,.0f} ریال با موفقیت انجام شد.\n\n'
                    f'از: {self.withdraw_from.currentText().split(" (")[0]}\n'
                    f'به: {self.withdraw_to.currentText().split(" (")[0]}')
                
                self.transfer_completed.emit()
                
                # پاک کردن فرم
                self.withdraw_amount.setValue(0)
                self.withdraw_desc.clear()
                
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ثبت برداشت:\n{e}')
    
    def _execute_transfer(self):
        """اجرای انتقال بین حساب‌ها"""
        from_id = self.transfer_from.currentData()
        to_id = self.transfer_to.currentData()
        amount = self.transfer_amount.value()
        
        if not from_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً حساب مبدأ را انتخاب کنید.')
            return
        
        if not to_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً حساب مقصد را انتخاب کنید.')
            return
        
        if from_id == to_id:
            QMessageBox.warning(self, 'خطا', 'حساب مبدأ و مقصد نمی‌توانند یکسان باشند.')
            return
        
        if amount <= 0:
            QMessageBox.warning(self, 'خطا', 'مبلغ باید بیشتر از صفر باشد.')
            return
        
        # بررسی موجودی مبدأ
        from_balance = self._get_account_balance(from_id)
        if from_balance < amount:
            QMessageBox.warning(self, 'خطا', 
                f'موجودی حساب مبدأ کافی نیست!\n'
                f'موجودی: {from_balance:,.0f} ریال\n'
                f'مبلغ انتقال: {amount:,.0f} ریال')
            return
        
        reply = QMessageBox.question(
            self, 'تأیید انتقال',
            f'آیا از انتقال {amount:,.0f} ریال اطمینان دارید؟\n\n'
            f'از: {self.transfer_from.currentText().split(" (")[0]}\n'
            f'به: {self.transfer_to.currentText().split(" (")[0]}',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            with self.db.connect() as conn:
                date_str = self.transfer_date.date().toString('yyyy-MM-dd')
                description = self.transfer_desc.toPlainText() or 'انتقال بین حساب‌ها'
                
                # ثبت تراکنش خروجی از مبدأ
                conn.execute('''
                    INSERT INTO cash_transactions 
                    (transaction_date, transaction_type, amount, from_account_id,
                     to_account_id, reference_type, description)
                    VALUES (?, 'TRANSFER_OUT', ?, ?, ?, 'TRANSFER', ?)
                ''', (date_str, amount, from_id, to_id, description))
                
                # ثبت تراکنش ورودی به مقصد
                conn.execute('''
                    INSERT INTO cash_transactions 
                    (transaction_date, transaction_type, amount, from_account_id,
                     to_account_id, reference_type, description)
                    VALUES (?, 'TRANSFER_IN', ?, ?, ?, 'TRANSFER', ?)
                ''', (date_str, amount, from_id, to_id, description))
                
                # به‌روزرسانی موجودی مبدأ (کاهش)
                conn.execute('''
                    UPDATE cash_accounts 
                    SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (amount, from_id))
                
                # به‌روزرسانی موجودی مقصد (افزایش)
                conn.execute('''
                    UPDATE cash_accounts 
                    SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (amount, to_id))
                
                conn.commit()
                
                # بارگذاری مجدد حساب‌ها
                self._load_accounts()
                
                QMessageBox.information(self, 'موفق',
                    f'انتقال {amount:,.0f} ریال با موفقیت انجام شد.\n\n'
                    f'از: {self.transfer_from.currentText().split(" (")[0]}\n'
                    f'به: {self.transfer_to.currentText().split(" (")[0]}')
                
                self.transfer_completed.emit()
                
                # پاک کردن فرم
                self.transfer_amount.setValue(0)
                self.transfer_desc.clear()
                
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ثبت انتقال:\n{e}')
