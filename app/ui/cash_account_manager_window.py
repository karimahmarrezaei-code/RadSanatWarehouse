"""
فرم مدیریت حساب‌های نقدی (صندوق و بانک) - نسخه اصلاح‌شده
- رفع مشکل لود اطلاعات در ویرایش
- جداکننده هزارگان فعال
- نمایش مبلغ به حروف
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QComboBox, QFormLayout,
    QMessageBox, QFrame, QDoubleSpinBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QRadioButton, QButtonGroup,
    QLineEdit
)
from PyQt5.QtGui import QFont, QColor


# لیست بانک‌های پیش‌فرض ایران
DEFAULT_BANKS = [
    '',
    'بانک ملی ایران',
    'بانک سپه',
    'بانک صادرات ایران',
    'بانک تجارت',
    'بانک ملت',
    'بانک پاسارگاد',
    'بانک سامان',
    'بانک شهر',
    'بانک سینا',
    'بانک پارسیان',
    'بانک کارآفرین',
    'بانک آینده',
    'بانک خاورمیانه',
    'بانک گردشگری',
    'بانک ایران زمین',
    'بانک قوامین',
    'بانک دی',
    'بانک کشاورزی',
    'بانک مسکن',
    'بانک توسعه صادرات',
    'پست بانک ایران',
]


# ===================================================================
# توابع تبدیل عدد به حروف فارسی
# ===================================================================
def number_to_persian_words(number):
    """تبدیل عدد به حروف فارسی"""
    if number == 0:
        return "صفر"
    
    ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه']
    teens = ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']
    tens = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
    hundreds = ['', 'یکصد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']
    
    def three_digits(n):
        if n == 0:
            return ''
        result = []
        h = n // 100
        t = (n % 100) // 10
        o = n % 10
        
        if h > 0:
            result.append(hundreds[h])
        
        if t == 1:
            result.append(teens[o])
        else:
            if t > 0:
                result.append(tens[t])
            if o > 0:
                result.append(ones[o])
        
        return ' و '.join(result) if result else ''
    
    if number < 0:
        return 'منفی ' + number_to_persian_words(abs(number))
    
    # میلیارد
    result = []
    billions = number // 1000000000
    if billions > 0:
        result.append(three_digits(billions) + ' میلیارد')
    
    # میلیون
    millions = (number % 1000000000) // 1000000
    if millions > 0:
        result.append(three_digits(millions) + ' میلیون')
    
    # هزار
    thousands = (number % 1000000) // 1000
    if thousands > 0:
        result.append(three_digits(thousands) + ' هزار')
    
    # باقیمانده
    remainder = number % 1000
    if remainder > 0:
        result.append(three_digits(remainder))
    
    return ' و '.join(result)


class CashAccountManagerWindow(QDialog):
    """فرم مدیریت حساب‌های نقدی"""
    
    accounts_changed = pyqtSignal()
    
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.user_id = user_data.get('id', 1)
        self.setWindowTitle('مدیریت حساب‌های نقدی (صندوق و بانک)')
        self.resize(1000, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        
        self.editing_account_id = None
        self._build_ui()
        self._load_accounts()
    
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # هدر
        header = QFrame()
        header.setObjectName('Card')
        h_layout = QVBoxLayout(header)
        title = QLabel('مدیریت حساب‌های نقدی')
        title.setObjectName('Title')
        subtitle = QLabel('افزودن، ویرایش و غیرفعال‌سازی حساب‌های صندوق و بانک')
        subtitle.setObjectName('Muted')
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        root.addWidget(header)

        # بخش فرم افزودن/ویرایش
        form_group = QGroupBox('اطلاعات حساب (جدید / ویرایش)')
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        # نام حساب
        self.account_name = QLineEdit()
        self.account_name.setPlaceholderText('مثلاً: صندوق اصلی، بانک ملی - جاری')
        form_layout.addRow('نام حساب:', self.account_name)

        # نوع حساب
        self.type_group = QButtonGroup(self)
        self.type_cash = QRadioButton('💵 صندوق (Cash)')
        self.type_bank = QRadioButton(' بانک (Bank)')
        self.type_cash.setChecked(True)
        self.type_group.addButton(self.type_cash)
        self.type_group.addButton(self.type_bank)
        self.type_cash.toggled.connect(self._on_type_changed)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(self.type_cash)
        type_layout.addWidget(self.type_bank)
        type_layout.addStretch()
        form_layout.addRow('نوع حساب:', type_layout)

        # نام بانک (فقط برای بانک)
        self.bank_name_combo = QComboBox()
        self.bank_name_combo.setEditable(True)
        self.bank_name_combo.addItems(DEFAULT_BANKS)
        self.bank_name_combo.setPlaceholderText('نام بانک را انتخاب یا تایپ کنید')
        form_layout.addRow('نام بانک:', self.bank_name_combo)

        # شماره حساب
        self.account_number = QLineEdit()
        self.account_number.setPlaceholderText('شماره حساب (اختیاری)')
        form_layout.addRow('شماره حساب:', self.account_number)

        # موجودی اولیه - با جداکننده هزارگان
        self.initial_balance = QDoubleSpinBox()
        self.initial_balance.setRange(0, 999999999999)
        self.initial_balance.setDecimals(0)
        self.initial_balance.setSuffix(' ریال')
        self.initial_balance.setGroupSeparatorShown(True)  # ✅ فعال‌سازی جداکننده هزارگان
        self.initial_balance.valueChanged.connect(self._update_balance_words)
        form_layout.addRow('موجودی اولیه:', self.initial_balance)

        # نمایش مبلغ به حروف
        self.balance_words_lbl = QLabel('صفر ریال')
        self.balance_words_lbl
        form_layout.addRow('مبلغ به حروف:', self.balance_words_lbl)

        # توضیحات
        self.account_desc = QTextEdit()
        self.account_desc.setMaximumHeight(60)
        self.account_desc.setPlaceholderText('توضیحات (اختیاری)')
        form_layout.addRow('توضیحات:', self.account_desc)

        # دکمه‌های فرم
        form_buttons = QHBoxLayout()
        self.save_btn = QPushButton('💾 ذخیره حساب')
        self.save_btn.setObjectName('SuccessButton')
        self.save_btn.setMinimumHeight(45)
        self.save_btn.clicked.connect(self._save_account)
        form_buttons.addWidget(self.save_btn)

        self.cancel_btn = QPushButton(' پاک کردن فرم')
        self.cancel_btn.setObjectName('SecondaryButton')
        self.cancel_btn.setMinimumHeight(45)
        self.cancel_btn.clicked.connect(self._clear_form)
        form_buttons.addWidget(self.cancel_btn)

        form_buttons.addStretch()
        form_layout.addRow(form_buttons)

        root.addWidget(form_group)

        # بخش لیست حساب‌ها
        list_group = QGroupBox('حساب‌های ثبت‌شده')
        list_layout = QVBoxLayout(list_group)

        self.accounts_table = QTableWidget(0, 6)
        self.accounts_table.setHorizontalHeaderLabels([
            'ردیف', 'نام حساب', 'نوع', 'نام بانک', 'موجودی (ریال)', 'وضعیت'
        ])
        self.accounts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.accounts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.accounts_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.accounts_table.verticalHeader().setVisible(False)
        self.accounts_table.itemSelectionChanged.connect(self._on_account_selected)
        
        # فرمت‌بندی ستون موجودی (هزارگان)
        self.accounts_table.setColumnWidth(4, 160)
        
        list_layout.addWidget(self.accounts_table)

        # دکمه‌های لیست
        list_buttons = QHBoxLayout()
        
        self.edit_btn = QPushButton('✏️ ویرایش')
        self.edit_btn.setObjectName('PrimaryButton')
        self.edit_btn.setMinimumHeight(40)
        self.edit_btn.clicked.connect(self._edit_selected)
        self.edit_btn.setEnabled(False)
        list_buttons.addWidget(self.edit_btn)

        self.toggle_btn = QPushButton('🔄 تغییر وضعیت (فعال/غیرفعال)')
        self.toggle_btn.setObjectName('SecondaryButton')
        self.toggle_btn.setMinimumHeight(40)
        self.toggle_btn.clicked.connect(self._toggle_account)
        self.toggle_btn.setEnabled(False)
        list_buttons.addWidget(self.toggle_btn)

        self.opening_btn = QPushButton('📊 ثبت موجودی افتتاحیه')
        self.opening_btn.setObjectName('WarningButton')
        self.opening_btn.setMinimumHeight(40)
        self.opening_btn.clicked.connect(self._register_opening_balance)
        self.opening_btn.setEnabled(False)
        list_buttons.addWidget(self.opening_btn)

        list_buttons.addStretch()
        list_layout.addLayout(list_buttons)

        root.addWidget(list_group)

        # به‌روزرسانی اولیه UI
        self._on_type_changed()

    def _update_balance_words(self):
        """به‌روزرسانی نمایش مبلغ به حروف"""
        amount = int(self.initial_balance.value())
        words = number_to_persian_words(amount)
        self.balance_words_lbl.setText(f"{words} ریال")

    def _on_type_changed(self):
        """تغییر نمایش فیلدها بر اساس نوع حساب"""
        if self.type_bank.isChecked():
            self.bank_name_combo.setEnabled(True)
            self.bank_name_combo.setStyleSheet("")
        else:
            self.bank_name_combo.setEnabled(False)
            self.bank_name_combo
            self.bank_name_combo.setCurrentIndex(0)

    def _load_accounts(self):
        """بارگذاری حساب‌ها در جدول"""
        try:
            with self.db.connect() as conn:
                rows = conn.execute('''
                    SELECT id, name, type, bank_name, account_number, 
                           balance, description, is_active
                    FROM cash_accounts 
                    ORDER BY type, name
                ''').fetchall()

                self.accounts_table.setRowCount(len(rows))
                for i, r in enumerate(rows):
                    # ردیف
                  # self.accounts_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                    self.accounts_table.setItem(i, 0, QTableWidgetItem(str(r['id'])))
                    # نام حساب
                    self.accounts_table.setItem(i, 1, QTableWidgetItem(r['name']))
                    
                    # نوع
                    type_label = '💵 صندوق' if r['type'] == 'CASH' else '🏦 بانک'
                    self.accounts_table.setItem(i, 2, QTableWidgetItem(type_label))
                    
                    # نام بانک
                    self.accounts_table.setItem(i, 3, QTableWidgetItem(r['bank_name'] or '-'))
                    
                    # موجودی با جداکننده هزارگان
                    balance_item = QTableWidgetItem(f"{int(r['balance']):,}")
                    balance_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.accounts_table.setItem(i, 4, balance_item)
                    
                    # وضعیت
                    is_active = bool(r['is_active'])
                    status_label = '✅ فعال' if is_active else '❌ غیرفعال'
                    status_item = QTableWidgetItem(status_label)
                    status_item.setTextAlignment(Qt.AlignCenter)
                    if is_active:
                        status_item.setForeground(QColor('#16a34a'))
                    else:
                        status_item.setForeground(QColor('#dc2626'))
                    self.accounts_table.setItem(i, 5, status_item)
        except Exception as e:
            QMessageBox.warning(self, 'خطا', f'خطا در بارگذاری حساب‌ها:\n{e}')

    def _on_account_selected(self):
        """فعال‌سازی دکمه‌ها هنگام انتخاب"""
        selected = self.accounts_table.selectedItems()
        has_selection = len(selected) > 0
        self.edit_btn.setEnabled(has_selection)
        self.toggle_btn.setEnabled(has_selection)
        if hasattr(self, 'opening_btn'):
            self.opening_btn.setEnabled(has_selection)

    def _save_account(self):
        """ذخیره حساب جدید یا به‌روزرسانی حساب موجود"""
        name = self.account_name.text().strip()
        if not name:
            QMessageBox.warning(self, 'خطا', 'لطفاً نام حساب را وارد کنید.')
            return

        account_type = 'CASH' if self.type_cash.isChecked() else 'BANK'
        bank_name = self.bank_name_combo.currentText().strip() if account_type == 'BANK' else None
        account_number = self.account_number.text().strip() or None
        balance = self.initial_balance.value()
        description = self.account_desc.toPlainText().strip() or None

        try:
            with self.db.connect() as conn:
                if self.editing_account_id:
                    # ویرایش حساب موجود
                    conn.execute('''
                        UPDATE cash_accounts 
                        SET name=?, type=?, bank_name=?, account_number=?, 
                            balance=?, description=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    ''', (name, account_type, bank_name, account_number,
                          balance, description, self.editing_account_id))
                    QMessageBox.information(
                        self, 'موفق',
                        f'حساب "{name}" با موجودی {balance:,.0f} ریال ویرایش شد.'
                    )
                else:
                    # افزودن جدید
                    conn.execute('''
                        INSERT INTO cash_accounts 
                        (name, type, bank_name, account_number, balance, description, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, 1)
                    ''', (name, account_type, bank_name, account_number, balance, description))
                    QMessageBox.information(
                        self, 'موفق',
                        f'حساب "{name}" با موجودی اولیه {balance:,.0f} ریال اضافه شد.\n\n'
                        f'مبلغ به حروف: {number_to_persian_words(int(balance))} ریال'
                    )

                conn.commit()

            self._clear_form()
            self._load_accounts()
            self.accounts_changed.emit()

        except Exception as e:
            if 'UNIQUE' in str(e):
                QMessageBox.warning(self, 'خطا', f'حسابی با نام "{name}" قبلاً ثبت شده است.')
            else:
                QMessageBox.critical(self, 'خطا', f'خطا در ذخیره حساب:\n{e}')

    def _edit_selected(self):
        """بارگذاری اطلاعات حساب انتخاب‌شده در فرم"""
        selected = self.accounts_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        account_id = int(self.accounts_table.item(row, 0).text())

        try:
            with self.db.connect() as conn:
                row_data = conn.execute('''
                    SELECT id, name, type, bank_name, account_number, balance, description
                    FROM cash_accounts WHERE id=?
                ''', (account_id,)).fetchone()

                if not row_data:
                    return

                self.editing_account_id = account_id
                
                # نام حساب
                self.account_name.setText(row_data['name'] or '')
                
                # نوع حساب
                if row_data['type'] == 'CASH':
                    self.type_cash.setChecked(True)
                else:
                    self.type_bank.setChecked(True)
                    if row_data['bank_name']:
                        self.bank_name_combo.setCurrentText(row_data['bank_name'])
                
                # شماره حساب
                self.account_number.setText(row_data['account_number'] or '')
                
                # موجودی فعلی
                self.initial_balance.setValue(float(row_data['balance']))
                
                # توضیحات
                self.account_desc.setPlainText(row_data['description'] or '')

                # تغییر متن دکمه
                self.save_btn.setText('💾 به‌روزرسانی حساب')
                self.save_btn

        except Exception as e:
            QMessageBox.warning(self, 'خطا', f'خطا در بارگذاری حساب:\n{e}')

    def _toggle_account(self):
        """تغییر وضعیت فعال/غیرفعال حساب"""
        selected = self.accounts_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        account_id = int(self.accounts_table.item(row, 0).text())
        account_name = self.accounts_table.item(row, 1).text()
        current_status = self.accounts_table.item(row, 5).text()
        
        is_active = '✅' in current_status
        new_status = 'غیرفعال' if is_active else 'فعال'

        reply = QMessageBox.question(
            self, 'تأیید تغییر وضعیت',
            f'آیا می‌خواهید حساب "{account_name}" را {new_status} کنید؟',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            with self.db.connect() as conn:
                conn.execute('''
                    UPDATE cash_accounts 
                    SET is_active=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                ''', (0 if is_active else 1, account_id))
                conn.commit()

            QMessageBox.information(self, 'موفق', f'حساب "{account_name}" {new_status} شد.')
            self._load_accounts()
            self.accounts_changed.emit()

        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در تغییر وضعیت:\n{e}')


    def _register_opening_balance(self):
        """ثبت موجودی افتتاحیه (فقط وقتی حساب هیچ گردشی ندارد)"""
        selected = self.accounts_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        account_id = int(self.accounts_table.item(row, 0).text())
        account_name = self.accounts_table.item(row, 1).text()

        # بررسی وجود گردش
        has_transaction = False
        tx_tables = []
        try:
            with self.db.connect() as conn:
                tables = [r['name'] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                tx_tables = [t for t in tables if any(k in t.lower() for k in ['transaction', 'tx', 'movement', 'entry'])]
                for tt in tx_tables:
                    cols = [c['name'] for c in conn.execute(f"PRAGMA table_info({tt})")]
                    acol = next((c for c in cols if 'account' in c.lower() or 'treasury' in c.lower()), None)
                    if acol and conn.execute(f"SELECT 1 FROM {tt} WHERE {acol}=? LIMIT 1", (account_id,)).fetchone():
                        has_transaction = True
                        break
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در بررسی گردش:\n{e}')
            return

        if has_transaction:
            QMessageBox.warning(
                self, 'ثبت افتتاحیه مجاز نیست',
                f'حساب "{account_name}" قبلاً گردش داشته است.\n'
                'موجودی افتتاحیه فقط برای حساب‌های تازه (بدون تراکنش) مجاز است.\n'
                'برای تغییر موجودی، از "مدیریت نقدینگی" استفاده کنید.')
            return

        # گرفتن مبلغ از کاربر
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self, 'موجودی افتتاحیه',
            f'مبلغ موجودی اولیه برای "{account_name}" (ریال):')
        if not ok:
            return
        digits = ''.join(ch for ch in text if ch.isdigit())
        amount = int(digits) if digits else 0
        if amount <= 0:
            QMessageBox.warning(self, 'افتتاحیه', 'مبلغ معتبر وارد کنید.')
            return

        # ثبت در cash_accounts و treasury_accounts + تراکنش OPENING
        try:
            with self.db.connect() as conn:
                # ۱) به‌روزرسانی cash_accounts
                conn.execute("UPDATE cash_accounts SET balance=? WHERE id=?", (amount, account_id))

                # ۲) به‌روزرسانی treasury_accounts (اگر کد CA-* دارد)
                ca_row = conn.execute(
                    "SELECT id FROM cash_accounts WHERE id=?", (account_id,)).fetchone()
                if ca_row:
                    # پیدا کردن کد مرتبط (CA-0000X)
                    code_match = None
                    for r in conn.execute("SELECT code, name FROM treasury_accounts"):
                        if r['name'] and account_name in r['name']:
                            code_match = r['code']
                            break
                    if code_match:
                        cols = [c['name'] for c in conn.execute("PRAGMA table_info(treasury_accounts)")]
                        init_col = next((c for c in cols if c.startswith('opening') or c.startswith('initial')), None)
                        cur_col = next((c for c in cols if c.startswith('current') or c == 'balance'), None)
                        if init_col and cur_col:
                            conn.execute(f"UPDATE treasury_accounts SET {init_col}=?, {cur_col}=? WHERE code=?",
                                        (amount, amount, code_match))

                # ۳) ثبت تراکنش OPENING
                for tt in ['cash_transactions', 'treasury_transactions', 'transactions']:
                    if tt in tx_tables:
                        cols = [c['name'] for c in conn.execute(f"PRAGMA table_info({tt})")]
                        acol = next((c for c in cols if 'account' in c.lower() or 'treasury' in c.lower()), None)
                        if acol:
                            amount_col = next((c for c in cols if 'amount' in c.lower()), None)
                            type_col = next((c for c in cols if 'type' in c.lower() or 'kind' in c.lower()), None)
                            date_col = next((c for c in cols if 'date' in c.lower()), None)
                            note_col = next((c for c in cols if 'note' in c.lower() or 'desc' in c.lower()), None)
                            
                            vals = {acol: account_id}
                            if amount_col: vals[amount_col] = amount
                            if type_col: vals[type_col] = 'TRANSFER_IN'
                            if date_col: vals[date_col] = 'CURRENT_TIMESTAMP'
                            if note_col: vals[note_col] = 'موجودی افتتاحیه (واریز اولیه)'
                            
                            sql = f"INSERT INTO {tt} ({','.join(vals.keys())}) VALUES ({','.join(['?']*len(vals))})"
                            conn.execute(sql, tuple(vals.values()))
                            break

                conn.commit()

            QMessageBox.information(
                self, 'موفق',
                f'موجودی افتتاحیه "{account_name}" با مبلغ {amount:,} ریال ثبت شد.\n'
                f'مبلغ به حروف: {number_to_persian_words(amount)} ریال')
            self._load_accounts()
            self.accounts_changed.emit()

        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ثبت افتتاحیه:\n{e}')

    def _clear_form(self):
        """پاک کردن فرم"""
        self.editing_account_id = None
        self.account_name.clear()
        self.type_cash.setChecked(True)
        self.bank_name_combo.setCurrentIndex(0)
        self.account_number.clear()
        self.initial_balance.setValue(0)
        self.balance_words_lbl.setText('صفر ریال')
        self.account_desc.clear()
        self.save_btn.setText(' ذخیره حساب')
        self.save_btn.setObjectName('SuccessButton')
        self.save_btn.setStyleSheet('')
        self.accounts_table.clearSelection()
