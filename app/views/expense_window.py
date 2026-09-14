# -*- coding: utf-8 -*-
"""
فرم ثبت هزینه‌های عملیاتی با انتخاب حساب پرداخت
ثبت هزینه با انتخاب صندوق یا بانک + ثبت خودکار تراکنش نقدی

⚠️ نسخه اصلاح‌شده (بازبینی ۱۴۰۵/۰۵/۱۱):
  [C5]  رفع باگ بحرانی «ویرایش هزینه»:
        - تراکنش‌های نقدی قبلی این هزینه برگردانده می‌شوند (موجودی حساب قبلی بازگردانده می‌شود)
        - تراکنش جدید با مبلغ و حساب جدید ثبت می‌شود
  [C5b] رفع باگ «ویرایش ذخیره نمی‌شد»: conn.commit() در مسیر ویرایش صدا زده نمی‌شد
  [ATOMIC] بررسی موجودی و کسر موجودی حالا در یک اتصال/تراکنش واحد انجام می‌شود (رفع race condition)
  [NUM] شماره‌گذاری EX- بر اساس مقدار عددی (رفع اشکال مرز ۱۰۰۰۰؛ EX-10000 دیگر از EX-9999 کوچک‌تر نیست)
  [C1]  یکپارچه‌سازی صندوق/بانک: کار با treasury_accounts و treasury_transactions
        (به جای cash_accounts و cash_transactions — هماهنگ با schema و FK موجود)
  [FIX] تعمیر کامل تخریب‌های کپی-پیست (سینتکس): __init__، _build_ui، self.date_edit، < و ...
"""

from datetime import datetime
from typing import Optional

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QMessageBox, QFrame, QDateEdit,
    QComboBox, QTextEdit, QFormLayout,
)


class ExpenseWindow(QDialog):
    """فرم ثبت هزینه جدید با انتخاب حساب پرداخت"""

    def __init__(self, db, user_data, expense_id: Optional[int] = None, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.expense_id = expense_id
        self.next_expense_no = None
        self.setWindowTitle('ویرایش هزینه' if expense_id else 'ثبت هزینه جدید')
        self.resize(700, 800)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self._load_categories()
        self._load_accounts()
        if expense_id:
            self._load_expense(expense_id)
        else:
            self._generate_next_expense_no()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # هدر
        header = QFrame()
        header.setObjectName('Card')
        h_layout = QVBoxLayout(header)
        title = QLabel('ویرایش هزینه' if self.expense_id else 'ثبت هزینه جدید')
        title.setObjectName('Title')
        subtitle = QLabel('اطلاعات هزینه عملیاتی را وارد کنید.')
        subtitle.setObjectName('Muted')
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        root.addWidget(header)

        # فرم
        form_group = QGroupBox("اطلاعات هزینه")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # شماره هزینه (فقط نمایشی)
        self.expense_no_lbl = QLabel("-")
        self.expense_no_lbl.setStyleSheet(
            "font-weight: bold; color: #2563eb; font-size: 16px; padding: 8px; "
            "background: #f0f9ff; border-radius: 5px; border: 2px dashed #2563eb;"
        )
        form_layout.addRow("شماره هزینه:", self.expense_no_lbl)

        # تاریخ
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat('yyyy-MM-dd')
        form_layout.addRow("تاریخ هزینه:", self.date_edit)

        # دسته‌بندی
        self.category_combo = QComboBox()
        self.category_combo.setMinimumHeight(35)
        form_layout.addRow("دسته‌بندی:", self.category_combo)

        # مبلغ کل
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("مثلاً: 5000000")
        self.amount_input.textChanged.connect(self._calculate_balance)
        form_layout.addRow("مبلغ کل (ریال):", self.amount_input)

        # مبلغ پرداخت‌شده
        self.paid_input = QLineEdit()
        self.paid_input.setPlaceholderText("مبلغ پرداخت‌شده (پیش‌فرض = مبلغ کل)")
        self.paid_input.textChanged.connect(self._calculate_balance)
        form_layout.addRow("مبلغ پرداخت‌شده (ریال):", self.paid_input)

        # مانده باز
        self.balance_lbl = QLabel("0 ریال")
        self.balance_lbl.setStyleSheet("font-weight: bold; color: #2563eb; font-size: 14px;")
        form_layout.addRow("مانده باز:", self.balance_lbl)

        # ====== جدید: پرداخت از حساب ======
        self.account_combo = QComboBox()
        self.account_combo.setMinimumHeight(35)
        self.account_combo.currentIndexChanged.connect(self._on_account_changed)
        form_layout.addRow("پرداخت از حساب:", self.account_combo)

        # نمایش موجودی حساب
        self.account_balance_lbl = QLabel("موجودی: 0 ریال")
        self.account_balance_lbl.setStyleSheet("font-size: 12px; color: #16a34a; font-weight: bold;")
        form_layout.addRow("موجودی حساب:", self.account_balance_lbl)

        # شماره فاکتور / مرجع
        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("شماره فاکتور یا مرجع خارجی (اختیاری)")
        form_layout.addRow("شماره فاکتور/مرجع:", self.ref_input)

        # توضیحات
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("توضیحات هزینه (اختیاری)")
        self.desc_input.setMaximumHeight(80)
        form_layout.addRow("توضیحات:", self.desc_input)

        root.addWidget(form_group)

        # دکمه‌های پایین
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        save_btn = QPushButton("ذخیره هزینه")
        save_btn.setObjectName('PrimaryButton')
        save_btn.setMinimumHeight(50)
        save_btn.clicked.connect(self._save_expense)
        bottom_row.addWidget(save_btn)

        cancel_btn = QPushButton("انصراف")
        cancel_btn.setObjectName('SecondaryButton')
        cancel_btn.setMinimumHeight(50)
        cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(cancel_btn)

        root.addLayout(bottom_row)

    def _load_accounts(self):
        """بارگذاری حساب‌های نقدی فعال (treasury_accounts)"""
        try:
            with self.db.connect() as conn:
                rows = conn.execute('''
                    SELECT id, name, account_type, current_balance
                    FROM treasury_accounts
                    WHERE is_active = 1
                    ORDER BY account_type, name
                ''').fetchall()

                self.account_combo.clear()
                self.account_combo.addItem("-- انتخاب حساب --", None)
                for r in rows:
                    type_icon = "💵" if r['account_type'] == 'CASHBOX' else "🏦"
                    display = f"{type_icon} {r['name']} (موجودی: {r['current_balance']:,.0f} ریال)"
                    self.account_combo.addItem(display, r['id'])
        except Exception as e:
            print(f"خطا در بارگذاری حساب‌ها: {e}")

    def _on_account_changed(self):
        """به‌روزرسانی نمایش موجودی هنگام تغییر حساب"""
        account_id = self.account_combo.currentData()
        if not account_id:
            self.account_balance_lbl.setText("موجودی: 0 ریال")
            return

        try:
            with self.db.connect() as conn:
                row = conn.execute(
                    "SELECT current_balance FROM treasury_accounts WHERE id = ?", (account_id,)
                ).fetchone()
                if row:
                    balance = row['current_balance']
                    self.account_balance_lbl.setText(f"موجودی: {balance:,.0f} ریال")
        except Exception:
            pass

    def _generate_next_expense_no(self):
        """تولید شماره هزینه جدید به صورت خودکار"""
        with self.db.connect() as conn:
            # [NUM] مرتب‌سازی بر اساس مقدار عددی (SUBSTR بعد از 'EX-')
            row = conn.execute('''
                SELECT expense_no FROM expenses
                WHERE expense_no LIKE 'EX-%'
                ORDER BY CAST(SUBSTR(expense_no, 4) AS INTEGER) DESC
                LIMIT 1
            ''').fetchone()

            if row and row['expense_no']:
                try:
                    last_no = int(row['expense_no'].replace('EX-', ''))
                    next_no = last_no + 1
                except ValueError:
                    next_no = 1
            else:
                next_no = 1

            self.next_expense_no = f"EX-{next_no:04d}"
            self.expense_no_lbl.setText(self.next_expense_no)
            self.ref_input.setText(self.next_expense_no)

    def _load_categories(self):
        """بارگذاری دسته‌بندی‌های فعال"""
        with self.db.connect() as conn:
            rows = conn.execute('''
                SELECT id, name, color
                FROM expense_categories
                WHERE is_active = 1
                ORDER BY name
            ''').fetchall()

            self.category_combo.clear()
            self.category_combo.addItem("-- انتخاب دسته‌بندی --", None)
            for r in rows:
                self.category_combo.addItem(r['name'], r['id'])

    def _load_expense(self, expense_id: int):
        """بارگذاری اطلاعات هزینه برای ویرایش"""
        with self.db.connect() as conn:
            row = conn.execute('''
                SELECT expense_no, expense_date, category_id, description, amount,
                       paid_amount, reference_doc_id, paid_from_account_id
                FROM expenses WHERE id = ?
            ''', (expense_id,)).fetchone()

            if not row:
                QMessageBox.warning(self, "خطا", "هزینه مورد نظر یافت نشد.")
                self.reject()
                return

            self.expense_no_lbl.setText(row['expense_no'] or f"ID-{expense_id}")
            self.expense_no_lbl.setStyleSheet(
                "font-weight: bold; color: #6b7280; font-size: 16px; padding: 8px; "
                "background: #f3f4f6; border-radius: 5px; border: 1px solid #d1d5db;"
            )

            try:
                date = QDate.fromString(row['expense_date'], 'yyyy-MM-dd')
                self.date_edit.setDate(date)
            except Exception:
                pass

            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == row['category_id']:
                    self.category_combo.setCurrentIndex(i)
                    break

            self.amount_input.setText(str(row['amount']))
            self.paid_input.setText(str(row['paid_amount'] or 0))

            if row['reference_doc_id']:
                self.ref_input.setText(str(row['reference_doc_id']))

            if row['description']:
                self.desc_input.setPlainText(row['description'])

            # بارگذاری حساب پرداخت
            if row['paid_from_account_id']:
                for i in range(self.account_combo.count()):
                    if self.account_combo.itemData(i) == row['paid_from_account_id']:
                        self.account_combo.setCurrentIndex(i)
                        break

    def _calculate_balance(self):
        """محاسبه خودکار مانده باز"""
        try:
            amount = int(self.amount_input.text().replace(',', ''))
        except ValueError:
            amount = 0

        try:
            paid = int(self.paid_input.text().replace(',', '') or '0')
        except ValueError:
            paid = 0

        balance = amount - paid
        self.balance_lbl.setText(f"{balance:,} ریال")

        if balance > 0:
            self.balance_lbl.setStyleSheet("font-weight: bold; color: #dc2626; font-size: 14px;")
        elif balance == 0:
            self.balance_lbl.setStyleSheet("font-weight: bold; color: #16a34a; font-size: 14px;")
        else:
            self.balance_lbl.setStyleSheet("font-weight: bold; color: #ea580c; font-size: 14px;")

    # ------------------------------------------------------------------
    # [C5] هستهٔ اصلی رفع: برگردانی تراکنش‌های قبلی هنگام ویرایش
    # ------------------------------------------------------------------
    def _revert_expense_cash_transactions(self, conn, expense_id: int) -> int:
        """تراکنش‌های نقدی ثبت‌شده برای این هزینه را برمی‌گرداند (موجودی حساب‌ها بازگردانده می‌شود).

        تعداد تراکنش‌های برگردانده‌شده را برمی‌گرداند.
        """
        old_txs = conn.execute(
            "SELECT id, amount, treasury_account_id FROM treasury_transactions "
            "WHERE source_type = 'EXPENSE' AND source_id = ?",
            (expense_id,),
        ).fetchall()
        for tx in old_txs:
            # بازگرداندن موجودی حسابی که قبلاً از آن کسر شده بود
            conn.execute(
                'UPDATE treasury_accounts SET current_balance = current_balance + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (tx['amount'], tx['treasury_account_id']),
            )
            conn.execute('DELETE FROM treasury_transactions WHERE id = ?', (tx['id'],))
        return len(old_txs)

    def _save_expense(self):
        """ذخیره یا بروزرسانی هزینه با ثبت تراکنش نقدی"""
        category_id = self.category_combo.currentData()
        if not category_id:
            QMessageBox.warning(self, "خطا", "لطفاً یک دسته‌بندی انتخاب کنید.")
            return

        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "خطا", "لطفاً حساب پرداخت را انتخاب کنید.")
            return

        try:
            amount = int(self.amount_input.text().replace(',', ''))
            if amount <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "خطا", "مبلغ کل باید یک عدد مثبت باشد.")
            return

        try:
            paid = int(self.paid_input.text().replace(',', '') or '0')
            if paid < 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "خطا", "مبلغ پرداخت‌شده باید یک عدد غیرمنفی باشد.")
            return

        if paid > amount:
            QMessageBox.warning(self, "خطا", "مبلغ پرداخت‌شده نمی‌تواند بیشتر از مبلغ کل باشد.")
            return

        expense_date = self.date_edit.date().toString('yyyy-MM-dd')
        description = self.desc_input.toPlainText().strip()
        ref_doc_id = self.ref_input.text().strip()
        if ref_doc_id:
            try:
                ref_doc_id = int(ref_doc_id)
            except ValueError:
                ref_doc_id = None

        if paid == 0:
            status = 'OPEN'
        elif paid >= amount:
            status = 'SETTLED'
        else:
            status = 'PARTIAL'

        # [ATOMIC] بررسی موجودی و همهٔ تغییرات در یک تراکنش واحد
        with self.db.connect() as conn:
            # بررسی موجودی حساب (در همان اتصالِ کسر)
            account_row = conn.execute(
                "SELECT current_balance, name FROM treasury_accounts WHERE id = ?", (account_id,)
            ).fetchone()
            if not account_row:
                QMessageBox.critical(self, "خطا", "حساب انتخاب‌شده یافت نشد.")
                return

            balance_before = int(account_row['current_balance'] or 0)
            if balance_before < paid:
                QMessageBox.critical(
                    self, "خطا: موجودی کافی نیست",
                    f"موجودی حساب \"{account_row['name']}\" کافی نیست!\n\n"
                    f"موجودی: {balance_before:,.0f} ریال\n"
                    f"مبلغ پرداخت: {paid:,.0f} ریال\n"
                    f"کسری: {paid - balance_before:,.0f} ریال"
                )
                return

            if self.expense_id:
                # ================== ویرایش ==================
                # ۱) [C5] برگردانی تراکنش‌های نقدی قبلی این هزینه
                self._revert_expense_cash_transactions(conn, self.expense_id)

                # ۲) به‌روزرسانی سند هزینه
                conn.execute('''
                    UPDATE expenses
                    SET expense_date = ?, category_id = ?, description = ?,
                        amount = ?, paid_amount = ?, status = ?,
                        reference_doc_id = ?, paid_from_account_id = ?
                    WHERE id = ?
                ''', (expense_date, category_id, description, amount, paid,
                      status, ref_doc_id, account_id, self.expense_id))

                # ۳) ثبت تراکنش نقدی جدید (اگر پرداختی وجود دارد)
                if paid > 0:
                    new_balance = balance_before - paid
                    conn.execute('''
                        UPDATE treasury_accounts
                        SET current_balance = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_balance, account_id))
                    conn.execute('''
                        INSERT INTO treasury_transactions (
                            treasury_account_id, transaction_date, transaction_type,
                            source_type, source_id, amount, balance_after, description, created_at
                        ) VALUES (?, ?, 'OUT', 'EXPENSE', ?, ?, ?, ?, ?)
                    ''', (account_id, expense_date, self.expense_id, paid, new_balance,
                          f"هزینه ویرایش‌شده - {description or ''}", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

                conn.commit()  # [C5b] ویرایش قبلاً commit نمی‌شد!
                QMessageBox.information(self, "موفقیت", "هزینه با موفقیت ویرایش شد.")
            else:
                # ================== ثبت جدید ==================
                expense_no = self.next_expense_no

                existing = conn.execute(
                    "SELECT id FROM expenses WHERE expense_no = ?", (expense_no,)
                ).fetchone()

                if existing:
                    # [NUM] مرتب‌سازی عددی (مثل _generate_next_expense_no)
                    row = conn.execute('''
                        SELECT expense_no FROM expenses
                        WHERE expense_no LIKE 'EX-%'
                        ORDER BY CAST(SUBSTR(expense_no, 4) AS INTEGER) DESC
                        LIMIT 1
                    ''').fetchone()
                    last_no = int(str(row['expense_no']).replace('EX-', ''))
                    expense_no = f"EX-{last_no + 1:04d}"

                # ثبت هزینه
                conn.execute('''
                    INSERT INTO expenses (
                        expense_no, expense_date, category_id, description, amount,
                        paid_amount, status, reference_doc_id, created_by, paid_from_account_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (expense_no, expense_date, category_id, description, amount,
                      paid, status, ref_doc_id, self.user_data['id'], account_id))

                expense_id_new = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

                # ثبت تراکنش نقدی (اگر مبلغ پرداخت > 0)
                if paid > 0:
                    new_balance = balance_before - paid
                    conn.execute('''
                        UPDATE treasury_accounts
                        SET current_balance = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_balance, account_id))
                    conn.execute('''
                        INSERT INTO treasury_transactions (
                            treasury_account_id, transaction_date, transaction_type,
                            source_type, source_id, amount, balance_after, description, created_at
                        ) VALUES (?, ?, 'OUT', 'EXPENSE', ?, ?, ?, ?, ?)
                    ''', (account_id, expense_date, expense_id_new, paid, new_balance,
                          f"هزینه {expense_no} - {description or ''}", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

                conn.commit()

                QMessageBox.information(
                    self, "موفقیت",
                    f"هزینه با شماره {expense_no} با موفقیت ثبت شد.\n\n"
                    f"مبلغ پرداخت: {paid:,.0f} ریال\n"
                    f"از حساب: {account_row['name']}\n"
                    f"موجودی باقی‌مانده: {balance_before - paid:,.0f} ریال"
                )

        self.accept()
