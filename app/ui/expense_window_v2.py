"""
فرم ثبت هزینه‌های عملیاتی با شماره خودکار
ثبت هزینه جدید با شماره پیش‌فرض (EX-0001, EX-0002, ...)
"""

from typing import Optional
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QMessageBox, QFrame, QDateEdit,
    QComboBox, QTextEdit, QFormLayout
)


class ExpenseWindow(QDialog):
    """فرم ثبت هزینه جدید با شماره خودکار"""

    def __init__(self, db, user_data, expense_id: Optional[int] = None, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.expense_id = expense_id
        self.next_expense_no = None
        self.setWindowTitle('ویرایش هزینه' if expense_id else 'ثبت هزینه جدید')
        self.resize(650, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self._load_categories()
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
        subtitle = QLabel('اطلاعات هزینه عملیاتی را وارد کنید. شماره به صورت خودکار تولید می‌شود.')
        subtitle.setObjectName('Muted')
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        root.addWidget(header)

        # فرم
        form_group = QGroupBox("اطلاعات هزینه")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # شماره هزینه
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

    def _generate_next_expense_no(self):
        """تولید شماره هزینه جدید به صورت خودکار"""
        with self.db.connect() as conn:
            row = conn.execute('''
                SELECT expense_no FROM expenses 
                WHERE expense_no LIKE 'EX-%'
                ORDER BY expense_no DESC 
                LIMIT 1
            ''').fetchone()

            if row and row['expense_no']:
                try:
                    last_no = int(row['expense_no'].replace('EX-', ''))
                    next_no = last_no + 1
                except:
                    next_no = 1
            else:
                next_no = 1

            self.next_expense_no = f"EX-{next_no:04d}"
            self.expense_no_lbl.setText(self.next_expense_no)

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
                       paid_amount, reference_doc_id
                FROM expenses WHERE id = ?
            ''', (expense_id,)).fetchone()

            if not row:
                QMessageBox.warning(self, "خطا", "هزینه مورد نظر یافت نشد.")
                self.reject()
                return

            # نمایش شماره موجود
            self.expense_no_lbl.setText(row['expense_no'] or f"ID-{expense_id}")
            self.expense_no_lbl.setStyleSheet(
                "font-weight: bold; color: #6b7280; font-size: 16px; padding: 8px; "
                "background: #f3f4f6; border-radius: 5px; border: 1px solid #d1d5db;"
            )

            # تاریخ
            try:
                date = QDate.fromString(row['expense_date'], 'yyyy-MM-dd')
                self.date_edit.setDate(date)
            except:
                pass

            # دسته‌بندی
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == row['category_id']:
                    self.category_combo.setCurrentIndex(i)
                    break

            # مبالغ
            self.amount_input.setText(str(row['amount']))
            self.paid_input.setText(str(row['paid_amount'] or 0))

            # مرجع
            if row['reference_doc_id']:
                self.ref_input.setText(str(row['reference_doc_id']))

            # توضیحات
            if row['description']:
                self.desc_input.setPlainText(row['description'])

    def _calculate_balance(self):
        """محاسبه خودکار مانده باز"""
        try:
            amount = int(self.amount_input.text().replace(',', ''))
        except:
            amount = 0

        try:
            paid = int(self.paid_input.text().replace(',', '') or '0')
        except:
            paid = 0

        balance = amount - paid
        self.balance_lbl.setText(f"{balance:,} ریال")

        if balance > 0:
            self.balance_lbl.setStyleSheet("font-weight: bold; color: #dc2626; font-size: 14px;")
        elif balance == 0:
            self.balance_lbl.setStyleSheet("font-weight: bold; color: #16a34a; font-size: 14px;")
        else:
            self.balance_lbl.setStyleSheet("font-weight: bold; color: #ea580c; font-size: 14px;")

    def _save_expense(self):
        """ذخیره یا بروزرسانی هزینه"""
        # اعتبارسنجی
        category_id = self.category_combo.currentData()
        if not category_id:
            QMessageBox.warning(self, "خطا", "لطفاً یک دسته‌بندی انتخاب کنید.")
            return

        try:
            amount = int(self.amount_input.text().replace(',', ''))
            if amount <= 0:
                raise ValueError()
        except:
            QMessageBox.warning(self, "خطا", "مبلغ کل باید یک عدد مثبت باشد.")
            return

        try:
            paid = int(self.paid_input.text().replace(',', '') or '0')
            if paid < 0:
                raise ValueError()
        except:
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
            except:
                ref_doc_id = None

        # تعیین وضعیت
        if paid == 0:
            status = 'OPEN'
        elif paid >= amount:
            status = 'SETTLED'
        else:
            status = 'PARTIAL'

        with self.db.connect() as conn:
            if self.expense_id:
                # ویرایش
                conn.execute('''
                    UPDATE expenses
                    SET expense_date = ?, category_id = ?, description = ?,
                        amount = ?, paid_amount = ?, status = ?,
                        reference_doc_id = ?
                    WHERE id = ?
                ''', (expense_date, category_id, description, amount, paid,
                      status, ref_doc_id, self.expense_id))
                QMessageBox.information(self, "موفقیت", "هزینه با موفقیت ویرایش شد.")
            else:
                # جدید - با شماره خودکار
                expense_no = self.next_expense_no
                
                # بررسی تکراری نبودن
                existing = conn.execute(
                    "SELECT id FROM expenses WHERE expense_no = ?", (expense_no,)
                ).fetchone()
                
                if existing:
                    row = conn.execute('''
                        SELECT expense_no FROM expenses 
                        WHERE expense_no LIKE 'EX-%'
                        ORDER BY expense_no DESC 
                        LIMIT 1
                    ''').fetchone()
                    last_no = int(row['expense_no'].replace('EX-', ''))
                    expense_no = f"EX-{last_no + 1:04d}"
                
                conn.execute('''
                    INSERT INTO expenses (
                        expense_no, expense_date, category_id, description, amount,
                        paid_amount, status, reference_doc_id, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (expense_no, expense_date, category_id, description, amount,
                      paid, status, ref_doc_id, self.user_data['id']))
                
                QMessageBox.information(
                    self, "موفقیت",
                    f"هزینه با شماره {expense_no} با موفقیت ثبت شد."
                )

        self.accept()
