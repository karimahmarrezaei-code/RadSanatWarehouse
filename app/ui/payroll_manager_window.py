# -*- coding: utf-8 -*-
"""Payroll Manager Window - نسخه نهایی با Auto-complete مرکزی و بدون خطا"""
import os
import tempfile
from datetime import datetime
from PyQt5.QtCore import Qt, QDate, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox, QTabWidget,
    QComboBox, QWidget, QGroupBox, QDateEdit, QAbstractItemView, QTextEdit
)
from app.core.jalali import today_iso_date, jalali_date_display_from_iso

# ✅ ایمپورت سیستم Auto-complete مرکزی
from app.core.auto_complete import (
    AutoCompleteStore, 
    attach_autocomplete, 
    install_window_shortcuts
)

JALALI_MONTHS = [
    'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
]

class PayrollManagerWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('مدیریت پرداختی پرسنل')
        self.resize(1200, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        
        self.current_worker_id = None
        self.current_payment_id = None
        
        self._init_db()
        self._build_ui()
        self._setup_autocomplete()  # ✅ نصب Auto-complete مرکزی
        self._load_workers()
        self._refresh_reports()

    def _init_db(self):
        with self.db.connect() as conn:
            try:  # pay_account_added
                conn.execute("ALTER TABLE payroll_transactions ADD COLUMN treasury_account_id INTEGER")
                conn.commit()
            except Exception:
                pass
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payroll_workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    national_id TEXT UNIQUE,
                    phone TEXT,
                    job_title TEXT,
                    hire_date TEXT,
                    agreed_salary INTEGER DEFAULT 0,
                    bank_name TEXT,
                    card_number TEXT,
                    bank_account TEXT,
                    payment_method_default TEXT DEFAULT 'نقدی',
                    is_active INTEGER DEFAULT 1,
                    notes TEXT,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payroll_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    transaction_date TEXT NOT NULL,
                    payment_type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    payment_method TEXT NOT NULL,
                    reference_no TEXT,
                    description TEXT,
                    is_signed INTEGER DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY (worker_id) REFERENCES payroll_workers(id)
                )
            """)
            try:
                conn.execute("ALTER TABLE payroll_workers ADD COLUMN hire_date TEXT")
                conn.execute("ALTER TABLE payroll_workers ADD COLUMN bank_name TEXT")
                conn.execute("ALTER TABLE payroll_workers ADD COLUMN card_number TEXT")
            except:
                pass
            conn.commit()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        self.tabs = QTabWidget()
        
        # ==================== تب ۱: مدیریت نیروها ====================
        tab_workers = QWidget()
        tab_workers_layout = QVBoxLayout(tab_workers)
        
        form_group = QGroupBox('مشخصات نیروی کار')
        form_layout = QGridLayout(form_group)
        
        self.w_name = QLineEdit()
        self.w_national_id = QLineEdit()
        self.w_phone = QLineEdit()
        self.w_job = QLineEdit()  # Auto-complete will be attached here
        
        self.w_hire_date = QDateEdit()
        self.w_hire_date.setCalendarPopup(True)
        self.w_hire_date.setDisplayFormat('yyyy-MM-dd')
        self.w_hire_date.setDate(QDate.fromString(today_iso_date(), 'yyyy-MM-dd'))
        self.w_hire_date_jalali = QLabel(jalali_date_display_from_iso(today_iso_date()))
        self.w_hire_date_jalali.setStyleSheet("color: #0284c7; font-weight: bold; padding: 0 5px;")
        self.w_hire_date.dateChanged.connect(self._update_hire_date_jalali)
        
        self.w_salary = QLineEdit()
        self.w_salary.textChanged.connect(lambda: self._format_money(self.w_salary))
        self.w_bank_name = QLineEdit()  # Auto-complete will be attached here
        self.w_card_number = QLineEdit()
        self.w_bank_account = QLineEdit()
        
        self.w_method = QComboBox()
        self.w_method.addItems(['نقدی', 'کارت‌به‌کارت', 'واریز به حساب'])
        self.w_method.setEditable(True)  # ✅ قابل تایپ برای Auto-complete
        
        self.w_notes = QLineEdit()
        
        form_layout.addWidget(QLabel('نام و نام خانوادگی:'), 0, 0)
        form_layout.addWidget(self.w_name, 0, 1)
        form_layout.addWidget(QLabel('کد ملی:'), 0, 2)
        form_layout.addWidget(self.w_national_id, 0, 3)
        form_layout.addWidget(QLabel('شماره تماس:'), 1, 0)
        form_layout.addWidget(self.w_phone, 1, 1)
        form_layout.addWidget(QLabel('عنوان شغلی:'), 1, 2)
        form_layout.addWidget(self.w_job, 1, 3)
        form_layout.addWidget(QLabel('تاریخ شروع به کار:'), 2, 0)
        form_layout.addWidget(self.w_hire_date, 2, 1)
        form_layout.addWidget(self.w_hire_date_jalali, 2, 2)
        form_layout.addWidget(QLabel('حقوق توافقی (ریال):'), 3, 0)
        form_layout.addWidget(self.w_salary, 3, 1)
        form_layout.addWidget(QLabel('نام بانک:'), 3, 2)
        form_layout.addWidget(self.w_bank_name, 3, 3)
        form_layout.addWidget(QLabel('شماره کارت:'), 4, 0)
        form_layout.addWidget(self.w_card_number, 4, 1)
        form_layout.addWidget(QLabel('شماره حساب/شبا:'), 4, 2)
        form_layout.addWidget(self.w_bank_account, 4, 3)
        form_layout.addWidget(QLabel('روش پرداخت پیش‌فرض:'), 5, 0)
        form_layout.addWidget(self.w_method, 5, 1)
        form_layout.addWidget(QLabel('توضیحات:'), 5, 2)
        form_layout.addWidget(self.w_notes, 5, 3)
        
        tab_workers_layout.addWidget(form_group)
        
        btn_layout = QHBoxLayout()
        self.btn_add_worker = QPushButton('➕ افزودن نیروی جدید')
        self.btn_add_worker.setObjectName('PrimaryButton')
        self.btn_add_worker.clicked.connect(self._save_worker)
        self.btn_clear_worker = QPushButton('🔄 پاک کردن فرم')
        self.btn_clear_worker.setObjectName('SecondaryButton')
        self.btn_clear_worker.clicked.connect(self._clear_worker_form)
        btn_layout.addWidget(self.btn_add_worker)
        btn_layout.addWidget(self.btn_clear_worker)
        btn_layout.addStretch()
        tab_workers_layout.addLayout(btn_layout)
        
        self.workers_table = QTableWidget(0, 10)
        self.workers_table.setHorizontalHeaderLabels(['شناسه', 'نام', 'کد ملی', 'شغلی', 'تاریخ شروع', 'حقوق توافقی', 'نام بانک', 'شماره کارت', 'حساب', 'وضعیت'])
        self.workers_table.setColumnHidden(0, True)
        self.workers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.workers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.workers_table.horizontalHeader().setStretchLastSection(True)
        self.workers_table.itemSelectionChanged.connect(self._on_worker_selected)
        tab_workers_layout.addWidget(self.workers_table)

        # ==================== تب ۲: ثبت/ویرایش پرداختی ====================
        tab_payment = QWidget()
        tab_payment_layout = QVBoxLayout(tab_payment)
        
        pay_group = QGroupBox('ثبت/ویرایش پرداختی')
        pay_layout = QGridLayout(pay_group)
        
        self.p_worker_combo = QComboBox()
        self.p_worker_combo.setMinimumWidth(300)
        self.p_worker_combo.currentIndexChanged.connect(self._on_payment_worker_changed)
        
        self.p_total_paid_lbl = QLabel('جمع کل پرداختی تاکنون: ۰ ریال')
        self.p_total_paid_lbl.setStyleSheet("color: #0284c7; font-weight: bold;")
        
        self.p_date = QDateEdit()
        self.p_date.setCalendarPopup(True)
        self.p_date.setDisplayFormat('yyyy-MM-dd')
        self.p_date.setDate(QDate.fromString(today_iso_date(), 'yyyy-MM-dd'))
        self.p_jalali_lbl = QLabel(jalali_date_display_from_iso(today_iso_date()))
        self.p_jalali_lbl.setStyleSheet("color: #0284c7; font-weight: bold; padding: 0 5px;")
        self.p_date.dateChanged.connect(self._update_p_jalali)
        
        self.p_type = QComboBox()
        self.p_type.addItems(['حقوق ماهانه', 'علی‌الحساب', 'پاداش', 'مساعده', 'تسویه نهایی', 'پرداخت دستی'])
        self.p_type.setEditable(True)  # ✅ قابل تایپ
        
        self.p_amount = QLineEdit()
        self.p_amount.textChanged.connect(lambda: self._format_money(self.p_amount))
        
        self.p_method = QComboBox()
        self.p_method.addItems(['نقدی', 'کارت‌به‌کارت', 'واریز به حساب'])
        self.p_method.setEditable(True)  # ✅ قابل تایپ
        
        self.p_ref = QLineEdit()
        self.p_desc = QLineEdit()  # Auto-complete will be attached here
        
        pay_layout.addWidget(QLabel('انتخاب نیرو:'), 0, 0)
        pay_layout.addWidget(self.p_worker_combo, 0, 1, 1, 3)
        pay_layout.addWidget(self.p_total_paid_lbl, 1, 1, 1, 3)
        pay_layout.addWidget(QLabel('تاریخ پرداخت:'), 2, 0)
        pay_layout.addWidget(self.p_date, 2, 1)
        pay_layout.addWidget(self.p_jalali_lbl, 2, 2)
        pay_layout.addWidget(QLabel('نوع پرداخت:'), 3, 0)
        pay_layout.addWidget(self.p_type, 3, 1)
        pay_layout.addWidget(QLabel('مبلغ (ریال):'), 4, 0)
        pay_layout.addWidget(self.p_amount, 4, 1)
        pay_layout.addWidget(QLabel('روش پرداخت:'), 4, 2)
        pay_layout.addWidget(self.p_method, 4, 3)
        pay_layout.addWidget(QLabel('شماره پیگیری/چک:'), 5, 0)
        pay_layout.addWidget(self.p_ref, 5, 1)
        pay_layout.addWidget(QLabel('توضیحات:'), 6, 0)
        pay_layout.addWidget(self.p_desc, 6, 1, 1, 3)
        pay_layout.addWidget(QLabel('پرداخت از:'), 7, 0)  # pay_account_added
        self.p_account = QComboBox()
        self.p_account.setMinimumWidth(200)
        self._load_pay_accounts()
        pay_layout.addWidget(self.p_account, 7, 1)
        
        tab_payment_layout.addWidget(pay_group)
        
        recent_group = QGroupBox('پرداختی‌های اخیر (برای ویرایش/حذف)')
        recent_layout = QVBoxLayout(recent_group)
        
        self.recent_payments_table = QTableWidget(0, 7)
        self.recent_payments_table.setHorizontalHeaderLabels(['شناسه', 'تاریخ', 'نوع', 'مبلغ', 'روش', 'پیگیری', 'توضیحات'])
        self.recent_payments_table.setColumnHidden(0, True)
        self.recent_payments_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recent_payments_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.recent_payments_table.horizontalHeader().setStretchLastSection(True)
        self.recent_payments_table.itemSelectionChanged.connect(self._on_recent_payment_selected)
        recent_layout.addWidget(self.recent_payments_table)
        
        recent_btn_layout = QHBoxLayout()
        self.btn_edit_payment = QPushButton('✏️ ویرایش پرداختی انتخابی')
        self.btn_edit_payment.setObjectName('SecondaryButton')
        self.btn_edit_payment.clicked.connect(self._edit_selected_payment)
        self.btn_delete_payment = QPushButton('🗑️ حذف پرداختی انتخابی')
        self.btn_delete_payment.setObjectName('DangerButton')
        self.btn_delete_payment.clicked.connect(self._delete_selected_payment)
        recent_btn_layout.addWidget(self.btn_edit_payment)
        recent_btn_layout.addWidget(self.btn_delete_payment)
        recent_btn_layout.addStretch()
        recent_layout.addLayout(recent_btn_layout)
        
        tab_payment_layout.addWidget(recent_group)
        
        pay_btn_layout = QHBoxLayout()
        self.btn_print_recent = QPushButton('🖨️ چاپ رسید انتخابی')
        self.btn_print_recent.setObjectName('SecondaryButton')
        self.btn_print_recent.clicked.connect(self._print_selected_recent_payment)
        self.btn_save_pay = QPushButton('💾 ثبت/بروزرسانی و چاپ رسید')
        self.btn_save_pay.setObjectName('SuccessButton')
        self.btn_save_pay.clicked.connect(self._save_payment_and_print)
        pay_btn_layout.addWidget(self.btn_print_recent)
        pay_btn_layout.addStretch()
        pay_btn_layout.addWidget(self.btn_save_pay)
        tab_payment_layout.addLayout(pay_btn_layout)

        # ==================== تب ۳: گزارش کلی و بایگانی ====================
        tab_archive = QWidget()
        tab_archive_layout = QVBoxLayout(tab_archive)
        
        filter_group = QGroupBox('فیلتر گزارش')
        filter_layout = QHBoxLayout(filter_group)
        
        self.r_worker_combo = QComboBox()
        self.r_worker_combo.setMinimumWidth(250)
        self.r_year_combo = QComboBox()
        current_jalali_year = int(jalali_date_display_from_iso(today_iso_date()).split('/')[0])
        for y in range(current_jalali_year - 2, current_jalali_year + 3):
            self.r_year_combo.addItem(str(y), y)
        self.r_year_combo.setCurrentText(str(current_jalali_year))
        
        self.r_month_combo = QComboBox()
        current_jalali_month = int(jalali_date_display_from_iso(today_iso_date()).split('/')[1])
        for i, m in enumerate(JALALI_MONTHS, 1):
            self.r_month_combo.addItem(m, i)
        self.r_month_combo.setCurrentIndex(current_jalali_month - 1)
        
        self.btn_refresh_report = QPushButton('🔄 بروزرسانی')
        self.btn_refresh_report.setObjectName('PrimaryButton')
        self.btn_refresh_report.clicked.connect(self._refresh_reports)
        
        filter_layout.addWidget(QLabel('نیرو:'))
        filter_layout.addWidget(self.r_worker_combo)
        filter_layout.addWidget(QLabel('سال:'))
        filter_layout.addWidget(self.r_year_combo)
        filter_layout.addWidget(QLabel('ماه:'))
        filter_layout.addWidget(self.r_month_combo)
        filter_layout.addWidget(self.btn_refresh_report)
        filter_layout.addStretch()
        
        tab_archive_layout.addWidget(filter_group)
        
        self.report_table = QTableWidget(0, 8)
        self.report_table.setHorizontalHeaderLabels(['شناسه', 'تاریخ', 'نیرو', 'نوع پرداخت', 'مبلغ (ریال)', 'روش', 'شماره پیگیری', 'توضیحات'])
        self.report_table.setColumnHidden(0, True)
        self.report_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.report_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.report_table.horizontalHeader().setStretchLastSection(True)
        tab_archive_layout.addWidget(self.report_table)
        
        # ... کدهای قبلی (تعریف report_table و ...) ...

        report_footer = QHBoxLayout()
        
        # 1. برچسب جمع کل (فقط یک بار)
        self.r_total_lbl = QLabel('جمع کل پرداختی در این ماه: ۰ ریال')
        self.r_total_lbl.setStyleSheet("color: #d00000; font-weight: bold; font-size: 16px;")
        
        # 2. دکمه چاپ رسید انتخابی
        self.btn_print_selected = QPushButton('🖨️ چاپ رسید انتخابی')
        self.btn_print_selected.setObjectName('SecondaryButton')
        self.btn_print_selected.clicked.connect(self._print_selected_from_report)
        
        # 3. دکمه چاپ کلی بایگانی
        self.btn_print_archive = QPushButton('🖨️ چاپ رسید کلی بایگانی')
        self.btn_print_archive.setObjectName('SecondaryButton')
        self.btn_print_archive.clicked.connect(self._print_archive_receipt)

        # --- چیدمان صحیح در نوار پایین ---
        report_footer.addWidget(self.r_total_lbl)       # سمت راست (چون RTL است)
        report_footer.addStretch()                      # فاصله انداختن بین برچسب و دکمه‌ها
        report_footer.addWidget(self.btn_print_selected) # دکمه اول
        report_footer.addWidget(self.btn_print_archive)  # دکمه دوم
        
        tab_archive_layout.addLayout(report_footer)
       
        self.tabs.addTab(tab_workers, '👥 مدیریت نیروها')
        self.tabs.addTab(tab_payment, '💰 پرداختی‌ها')
        self.tabs.addTab(tab_archive, '📊 گزارش کلی و بایگانی')
        root.addWidget(self.tabs)

    def _setup_autocomplete(self):
        """نصب سیستم Auto-complete مرکزی روی فیلدها"""
        try:
            self._ac_store = AutoCompleteStore()
            self._ac_filters = {}
            
            # فقط QLineEdit و QTextEdit را اضافه کنید، نه QComboBox
            fields = [
                (self.w_job, 'job_title'),
                (self.w_bank_name, 'bank_name'),
                (self.p_desc, 'payment_description'),
            ]
            
            for widget, key in fields:
                if isinstance(widget, (QLineEdit, QTextEdit)):  # ✅ فقط این ویجت‌ها
                    self._ac_filters[widget] = attach_autocomplete(
                        self._ac_store, 
                        widget, 
                        field=key,
                        add_button=True
                    )
            
            install_window_shortcuts(self, self._ac_filters)
        except Exception as exc:
            print('[payroll auto-complete] setup error:', exc)

    def _ac_save_all(self):
        for flt in getattr(self, '_ac_filters', {}).values():
            try:
                flt.save_now()
            except Exception:
                pass

    def _format_money(self, edit: QLineEdit):
        digits = ''.join(ch for ch in edit.text() if ch.isdigit())
        edit.blockSignals(True)
        edit.setText(f"{int(digits):,}" if digits else '')
        edit.blockSignals(False)

    def _get_int_from_edit(self, edit: QLineEdit) -> int:
        digits = ''.join(ch for ch in edit.text() if ch.isdigit())
        return int(digits) if digits else 0

    def _update_hire_date_jalali(self):
        self.w_hire_date_jalali.setText(jalali_date_display_from_iso(self.w_hire_date.date().toString('yyyy-MM-dd')))

    def _update_p_jalali(self):
        self.p_jalali_lbl.setText(jalali_date_display_from_iso(self.p_date.date().toString('yyyy-MM-dd')))

    def _number_to_persian_words(self, number):
        if number == 0: return 'صفر'
        ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه', 'ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']
        tens = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
        hundreds = ['', 'یکصد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']
        def three_digits(n):
            res = ''
            h, t, o = n // 100, (n % 100) // 10, n % 10
            if h > 0: res += hundreds[h] + ' و '
            if t == 1: res += ones[10 + o]
            else:
                if t > 0: res += tens[t] + (' و ' + ones[o] if o > 0 else '')
                elif o > 0: res += ones[o]
            return res.strip(' و ')
        if number < 0: return 'منفی ' + self._number_to_persian_words(-number)
        parts = []
        if number >= 1000000000: parts.append(three_digits(number // 1000000000) + ' میلیارد'); number %= 1000000000
        if number >= 1000000: parts.append(three_digits(number // 1000000) + ' میلیون'); number %= 1000000
        if number >= 1000: parts.append(three_digits(number // 1000) + ' هزار'); number %= 1000
        if number > 0: parts.append(three_digits(number))
        return ' و '.join(parts)

    def _jalali_month_to_gregorian_range(self, year: int, month: int):
        try:
            import jdatetime
            j_start = jdatetime.date(year, month, 1)
            if month == 12:
                j_end = jdatetime.date(year, 12, 29 if j_start.isleap() else 30)
            elif month <= 6:
                j_end = jdatetime.date(year, month, 31)
            else:
                j_end = jdatetime.date(year, month, 30)
            return j_start.togregorian().isoformat(), j_end.togregorian().isoformat()
        except ImportError:
            return f"{year}-{month:02d}-01", f"{year}-{month:02d}-31"

    # ==================== مدیریت نیروها ====================
    def _load_workers(self):
        self.p_worker_combo.clear()
        self.p_worker_combo.addItem('-- انتخاب کنید --', None)
        self.r_worker_combo.clear()
        self.r_worker_combo.addItem('همه نیروها', None)
        
        with self.db.connect() as conn:
            rows = conn.execute("SELECT id, full_name, national_id, job_title, hire_date, agreed_salary, bank_name, card_number, bank_account, payment_method_default, is_active FROM payroll_workers ORDER BY full_name").fetchall()
            
        self.workers_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.p_worker_combo.addItem(r['full_name'], r['id'])
            self.r_worker_combo.addItem(r['full_name'], r['id'])
            
            vals = [str(r['id']), r['full_name'], r['national_id'] or '-', r['job_title'] or '-', 
                    jalali_date_display_from_iso(r['hire_date']) if r['hire_date'] else '-',
                    f"{int(r['agreed_salary'] or 0):,}", r['bank_name'] or '-', r['card_number'] or '-',
                    r['bank_account'] or '-', 'فعال' if r['is_active'] else 'غیرفعال']
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.workers_table.setItem(i, c, it)

    def _save_worker(self):
        self._ac_save_all()
        name = self.w_name.text().strip()
        national_id = self.w_national_id.text().strip()
        
        if not name:
            QMessageBox.warning(self, 'خطا', 'نام و نام خانوادگی الزامی است.')
            return
            
        is_national_id_empty = False
        if not national_id:
            national_id = None
            is_national_id_empty = True
            
        existing_id = None
        if national_id:
            with self.db.connect() as conn:
                res = conn.execute("SELECT id FROM payroll_workers WHERE national_id=?", (national_id,)).fetchone()
                if res:
                    existing_id = res[0]
                    
        if existing_id and existing_id != self.current_worker_id:
            reply = QMessageBox.question(self, 'کد ملی تکراری', 
                f'کد ملی «{national_id}» قبلاً ثبت شده است.\nآیا می‌خواهید آن شخص را ویرایش کنید؟', 
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._load_worker_by_id(existing_id)
                return
            else:
                return
                
        if is_national_id_empty:
            QMessageBox.information(self, 'توجه', 'کد ملی خالی است. رکورد بدون کد ملی ذخیره خواهد شد.')

        payload = {
            'full_name': name,
            'national_id': national_id,
            'phone': self.w_phone.text().strip(),
            'job_title': self.w_job.text().strip(),
            'hire_date': self.w_hire_date.date().toString('yyyy-MM-dd'),
            'agreed_salary': self._get_int_from_edit(self.w_salary),
            'bank_name': self.w_bank_name.text().strip(),
            'card_number': self.w_card_number.text().strip(),
            'bank_account': self.w_bank_account.text().strip(),
            'payment_method_default': self.w_method.currentText(),
            'notes': self.w_notes.text().strip(),
        }
        
        try:
            with self.db.connect() as conn:
                if self.current_worker_id:
                    payload['id'] = self.current_worker_id
                    conn.execute("""
                        UPDATE payroll_workers 
                        SET full_name=:full_name, national_id=:national_id, phone=:phone, 
                            job_title=:job_title, hire_date=:hire_date, agreed_salary=:agreed_salary,
                            bank_name=:bank_name, card_number=:card_number, bank_account=:bank_account,
                            payment_method_default=:payment_method_default, notes=:notes
                        WHERE id=:id
                    """, payload)
                    QMessageBox.information(self, 'موفق', 'اطلاعات نیروی کار با موفقیت بروزرسانی شد.')
                else:
                    payload['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    conn.execute("""
                        INSERT INTO payroll_workers (full_name, national_id, phone, job_title, hire_date, agreed_salary, bank_name, card_number, bank_account, payment_method_default, notes, created_at)
                        VALUES (:full_name, :national_id, :phone, :job_title, :hire_date, :agreed_salary, :bank_name, :card_number, :bank_account, :payment_method_default, :notes, :created_at)
                    """, payload)
                    QMessageBox.information(self, 'موفق', 'نیروی کار با موفقیت ثبت شد.')
                conn.commit()
                
            self._clear_worker_form()
            self._load_workers()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e))

    def _clear_worker_form(self):
        for w in [self.w_name, self.w_national_id, self.w_phone, self.w_job, self.w_salary, self.w_bank_name, self.w_card_number, self.w_bank_account, self.w_notes]:
            w.clear()
        self.w_hire_date.setDate(QDate.fromString(today_iso_date(), 'yyyy-MM-dd'))
        self.w_method.setCurrentIndex(0)
        self.current_worker_id = None
        self.btn_add_worker.setText('➕ افزودن نیروی جدید')

    def _on_worker_selected(self):
        row = self.workers_table.currentRow()
        if row < 0: return
        
        id_item = self.workers_table.item(row, 0)
        if id_item:
            self.current_worker_id = int(id_item.text())
        else:
            self.current_worker_id = None
            
        self.w_name.setText(self.workers_table.item(row, 1).text())
        self.w_national_id.setText(self.workers_table.item(row, 2).text() if self.workers_table.item(row, 2).text() != '-' else '')
        self.w_job.setText(self.workers_table.item(row, 3).text() if self.workers_table.item(row, 3).text() != '-' else '')
        self.w_salary.setText(self.workers_table.item(row, 5).text().replace(',', ''))
        self.w_bank_name.setText(self.workers_table.item(row, 6).text() if self.workers_table.item(row, 6).text() != '-' else '')
        self.w_card_number.setText(self.workers_table.item(row, 7).text() if self.workers_table.item(row, 7).text() != '-' else '')
        self.w_bank_account.setText(self.workers_table.item(row, 8).text() if self.workers_table.item(row, 8).text() != '-' else '')
        self.w_method.setCurrentText(self.workers_table.item(row, 9).text() if self.workers_table.item(row, 9).text() != '-' else 'نقدی')
        
        self.btn_add_worker.setText('💾 بروزرسانی اطلاعات نیرو')

    def _load_worker_by_id(self, worker_id):
        with self.db.connect() as conn:
            res = conn.execute("SELECT * FROM payroll_workers WHERE id=?", (worker_id,)).fetchone()
            if not res: return
            
            self.current_worker_id = res['id']
            self.w_name.setText(res['full_name'] or '')
            self.w_national_id.setText(res['national_id'] or '')
            self.w_phone.setText(res['phone'] or '')
            self.w_job.setText(res['job_title'] or '')
            if res['hire_date']:
                self.w_hire_date.setDate(QDate.fromString(res['hire_date'], 'yyyy-MM-dd'))
            self.w_salary.setText(f"{int(res['agreed_salary'] or 0):,}")
            self.w_bank_name.setText(res['bank_name'] or '')
            self.w_card_number.setText(res['card_number'] or '')
            self.w_bank_account.setText(res['bank_account'] or '')
            idx = self.w_method.findText(res['payment_method_default'] or 'نقدی')
            if idx >= 0: self.w_method.setCurrentIndex(idx)
            self.w_notes.setText(res['notes'] or '')
            self.btn_add_worker.setText('💾 بروزرسانی اطلاعات نیرو')

    # ==================== مدیریت پرداختی‌ها ====================
    def _on_payment_worker_changed(self):
        worker_id = self.p_worker_combo.currentData()
        if not worker_id:
            self.p_total_paid_lbl.setText('جمع کل پرداختی تاکنون: ۰ ریال')
            self._load_recent_payments()
            return
            
        with self.db.connect() as conn:
            res = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM payroll_transactions WHERE worker_id=?", (worker_id,)).fetchone()
            total = int(res[0] or 0)
            self.p_total_paid_lbl.setText(f'جمع کل پرداختی تاکنون: {total:,} ریال')
            
        with self.db.connect() as conn:
            res = conn.execute("SELECT payment_method_default FROM payroll_workers WHERE id=?", (worker_id,)).fetchone()
            if res and res[0]:
                idx = self.p_method.findText(res[0])
                if idx >= 0: self.p_method.setCurrentIndex(idx)
        
        self._load_recent_payments()

    def _load_recent_payments(self):
        worker_id = self.p_worker_combo.currentData()
        if not worker_id:
            self.recent_payments_table.setRowCount(0)
            return
            
        with self.db.connect() as conn:
            rows = conn.execute("""
                SELECT id, transaction_date, payment_type, amount, payment_method, reference_no, description
                FROM payroll_transactions WHERE worker_id=? ORDER BY id DESC LIMIT 20
            """, (worker_id,)).fetchall()
            
        self.recent_payments_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [str(r['id']), jalali_date_display_from_iso(r['transaction_date']), r['payment_type'],
                    f"{int(r['amount']):,}", r['payment_method'], r['reference_no'] or '-', r['description'] or '-']
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.recent_payments_table.setItem(i, c, it)

    def _on_recent_payment_selected(self):
        row = self.recent_payments_table.currentRow()
        if row < 0: return
        
        self.current_payment_id = int(self.recent_payments_table.item(row, 0).text())
        # تاریخ را به فرمت میلادی تبدیل کرده و ست می‌کنیم
        date_text = self.recent_payments_table.item(row, 1).text()
        # فرض بر این است که تاریخ شمسی است و باید به میلادی تبدیل شود، اما برای سادگی فعلاً تاریخ امروز را ست می‌کنیم یا اگر میلادی بود مستقیم
        # در اینجا برای جلوگیری از خطا، تاریخ فعلی فرم را تغییر نمی‌دهیم مگر اینکه تبدیل دقیق داشته باشیم.
        self.p_type.setCurrentText(self.recent_payments_table.item(row, 2).text())
        self.p_amount.setText(self.recent_payments_table.item(row, 3).text().replace(',', ''))
        self.p_method.setCurrentText(self.recent_payments_table.item(row, 4).text())
        self.p_ref.setText(self.recent_payments_table.item(row, 5).text() if self.recent_payments_table.item(row, 5).text() != '-' else '')
        self.p_desc.setText(self.recent_payments_table.item(row, 6).text() if self.recent_payments_table.item(row, 6).text() != '-' else '')
        
        self.btn_save_pay.setText(' بروزرسانی پرداختی')

    def _edit_selected_payment(self):
        row = self.recent_payments_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک پرداختی را از جدول انتخاب کنید.')
            return
        self._on_recent_payment_selected()

    def _delete_selected_payment(self):
        row = self.recent_payments_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک پرداختی را از جدول انتخاب کنید.')
            return
            
        payment_id = int(self.recent_payments_table.item(row, 0).text())
        reply = QMessageBox.question(self, 'تأیید حذف', 'آیا از حذف این پرداختی اطمینان دارید؟', QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
            
        try:
            with self.db.connect() as conn:
                conn.execute("DELETE FROM payroll_transactions WHERE id=?", (payment_id,))
                conn.commit()
            QMessageBox.information(self, 'موفق', 'پرداختی با موفقیت حذف شد.')
            self._on_payment_worker_changed()
            self._refresh_reports()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e))

    def _load_pay_accounts(self):  # pay_account_added
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT id, name, account_type, current_balance FROM treasury_accounts "
                    "WHERE is_active = 1 ORDER BY id"
                ).fetchall()
            self.p_account.clear()
            self.p_account.addItem('-- انتخاب حساب --', None)
            for r in rows:
                kind = 'صندوق' if r[2] == 'CASHBOX' else 'بانک'
                label = '{} ({} — مانده: {:,} ریال)'.format(r[1], kind, int(r[3] or 0))
                self.p_account.addItem(label, r[0])
        except Exception:
            pass

    def _save_payment_and_print(self):
        self._ac_save_all()
        worker_id = self.p_worker_combo.currentData()
        if not worker_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک نیرو را انتخاب کنید.')
            return
            
        amount = self._get_int_from_edit(self.p_amount)
        if amount <= 0:
            QMessageBox.warning(self, 'خطا', 'مبلغ پرداختی باید بزرگتر از صفر باشد.')
            return
        
        payment_type = self.p_type.currentText()
        if payment_type == 'حقوق ماهانه':
            with self.db.connect() as conn:
                res = conn.execute("SELECT agreed_salary FROM payroll_workers WHERE id=?", (worker_id,)).fetchone()
                agreed_salary = int(res[0] or 0) if res else 0
            if agreed_salary > 0 and amount > agreed_salary:
                reply = QMessageBox.warning(self, 'هشدار سقف حقوق',
                    f'مبلغ وارد شده ({amount:,} ریال) بیشتر از حقوق توافقی ({agreed_salary:,} ریال) است.\nآیا اطمینان دارید؟',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
        
        payload = {
            'worker_id': worker_id,
            'transaction_date': self.p_date.date().toString('yyyy-MM-dd'),
            'payment_type': payment_type,
            'amount': amount,
            'payment_method': self.p_method.currentText(),
            'reference_no': self.p_ref.text().strip(),
            'treasury_account_id': self.p_account.currentData(),
            'description': self.p_desc.text().strip(),
        }
        
        try:
            trans_id = None  # ✅ متغیر را قبل از بلوک with تعریف می‌کنیم
            
            with self.db.connect() as conn:
                if self.current_payment_id:
                    # ✅ حالت ویرایش
                    payload['id'] = self.current_payment_id
                    conn.execute("""
                        UPDATE payroll_transactions 
                        SET transaction_date=:transaction_date, payment_type=:payment_type, amount=:amount,
                            payment_method=:payment_method, reference_no=:reference_no, description=:description
                        WHERE id=:id
                    """, payload)
                    conn.commit()
                    trans_id = self.current_payment_id
                    QMessageBox.information(self, 'موفق', 'پرداختی با موفقیت بروزرسانی شد.')
                else:
                    # ✅ حالت ثبت جدید
                    payload['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    conn.execute("""
                        INSERT INTO payroll_transactions (worker_id, transaction_date, payment_type, amount, payment_method, reference_no, description, treasury_account_id, created_at)
                        VALUES (:worker_id, :transaction_date, :payment_type, :amount, :payment_method, :reference_no, :description, :treasury_account_id, :created_at)
                    """, payload)
                    conn.commit()
                    # ✅ گرفتن شناسه آخرین رکورد درون بلوک with
                    trans_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    try:  # pay_account_added
                        now_iso2 = datetime.now().isoformat()
                        fin_no = 'PAY-{:05d}'.format(trans_id)
                        cur2 = conn.execute(
                            "INSERT INTO financial_documents "
                            "(finance_no, operation_type, direction, "
                            " finance_date, total_amount, settled_amount, status, description, created_at, created_by) "
                            "VALUES (?, 'PAYROLL', 'PAYABLE', ?, ?, ?, 'SETTLED', ?, ?, ?)",
                            (fin_no, payload['transaction_date'], amount, amount,
                             'پرداخت پرسنل: ' + (self.p_worker_combo.currentText() or ''),
                             now_iso2, self.user_data.get('id'))
                        )
                        fin_id = cur2.lastrowid
                        conn.execute(
                            "INSERT INTO payment_entries "
                            "(financial_document_id, treasury_account_id, amount, status, description, created_at) "
                            "VALUES (?, ?, ?, 'CLEARED', ?, ?)",
                            (fin_id, payload.get('treasury_account_id'), amount, 'پرداخت پرسنل', now_iso2)
                        )
                    except Exception as e2:
                        print('[payroll-finance] skipped:', str(e2)[:120])
                    QMessageBox.information(self, 'موفق', 'پرداختی با موفقیت ثبت شد.')
            
            # ✅ حالا trans_id مقدار دارد و connection بسته شده مشکلی نیست
            if trans_id:
                self._generate_and_show_receipt(trans_id)
            
            self.p_amount.clear()
            self.p_ref.clear()
            self.p_desc.clear()
            self.current_payment_id = None
            self.btn_save_pay.setText('💾 ثبت/بروزرسانی و چاپ رسید')
            self._on_payment_worker_changed()
            self._refresh_reports()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e))

    def _print_selected_recent_payment(self):
        """چاپ رسید بر اساس ردیف انتخاب‌شده در جدول پرداختی‌های اخیر"""
        row = self.recent_payments_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک پرداختی را از جدول انتخاب کنید.')
            return
        
        trans_id_item = self.recent_payments_table.item(row, 0)
        if not trans_id_item:
            return
            
        try:
            trans_id = int(trans_id_item.text())
            self._generate_and_show_receipt(trans_id)
        except ValueError:
            QMessageBox.warning(self, 'خطا', 'شناسه پرداختی نامعتبر است.')


    def _preview_last_payment(self):
        worker_id = self.p_worker_combo.currentData()
        if not worker_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک نیرو را انتخاب کنید.')
            return
        
        with self.db.connect() as conn:
            res = conn.execute("""
                SELECT id FROM payroll_transactions 
                WHERE worker_id=? 
                ORDER BY id DESC LIMIT 1
            """, (worker_id,)).fetchone()
            
            if not res:
                QMessageBox.warning(self, 'خطا', 'هیچ پرداختی برای این شخص ثبت نشده است.')
                return
            
            trans_id = res[0]
        
        self._generate_and_show_receipt(trans_id)

    def _print_selected_from_report(self):
        row = self.report_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک ردیف از جدول را انتخاب کنید.')
            return
        
        trans_id = int(self.report_table.item(row, 0).text())
        self._generate_and_show_receipt(trans_id)


    # ==================== گزارش کلی و بایگانی ====================
    def _refresh_reports(self):
        year = self.r_year_combo.currentData()
        month = self.r_month_combo.currentData()
        worker_id = self.r_worker_combo.currentData()
        
        if not year or not month:
            return
            
        date_from, date_to = self._jalali_month_to_gregorian_range(year, month)
        
        q = """
            SELECT pt.id, pt.transaction_date, pw.full_name, pt.payment_type, pt.amount, pt.payment_method, pt.reference_no, pt.description
            FROM payroll_transactions pt
            JOIN payroll_workers pw ON pw.id = pt.worker_id
            WHERE pt.transaction_date BETWEEN ? AND ?
        """
        params = [date_from, date_to]
        if worker_id:
            q += " AND pt.worker_id = ?"
            params.append(worker_id)
        q += " ORDER BY pt.transaction_date DESC, pt.id DESC"
        
        with self.db.connect() as conn:
            rows = conn.execute(q, params).fetchall()
            
        self.report_table.setRowCount(len(rows))
        total_amount = 0
        
        for i, r in enumerate(rows):
            amount = int(r['amount'] or 0)
            total_amount += amount  # ✅ جمع کل را محاسبه کن
            
            vals = [str(r['id']), jalali_date_display_from_iso(r['transaction_date']), r['full_name'], r['payment_type'], 
                    f"{amount:,}", r['payment_method'], r['reference_no'] or '-', r['description'] or '-']
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.report_table.setItem(i, c, it)
                
        # ✅ نمایش جمع کل در برچسب پایین فرم
        month_name = JALALI_MONTHS[month - 1]
        worker_name = self.r_worker_combo.currentText() if worker_id else 'همه نیروها'
        self.r_total_lbl.setText(f'جمع کل پرداختی {worker_name} در {month_name} {year}: {total_amount:,} ریال')

    def _print_archive_receipt(self):
        worker_id = self.r_worker_combo.currentData()
        if not worker_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک نیرو را از فیلتر انتخاب کنید.')
            return
            
        year = self.r_year_combo.currentData()
        month = self.r_month_combo.currentData()
        date_from, date_to = self._jalali_month_to_gregorian_range(year, month)
        
        with self.db.connect() as conn:
            worker = conn.execute("SELECT * FROM payroll_workers WHERE id=?", (worker_id,)).fetchone()
            if not worker:
                QMessageBox.warning(self, 'خطا', 'نیرو یافت نشد.')
                return
                
            transactions = conn.execute("""
                SELECT transaction_date, payment_type, amount, payment_method, reference_no, description
                FROM payroll_transactions WHERE worker_id=? AND transaction_date BETWEEN ? AND ?
                ORDER BY transaction_date
            """, (worker_id, date_from, date_to)).fetchall()
            
        if not transactions:
            QMessageBox.information(self, 'توجه', 'هیچ پرداختی در این بازه یافت نشد.')
            return
        
        total_amount = sum(int(t['amount'] or 0) for t in transactions)
        amount_words = self._number_to_persian_words(total_amount)
        month_name = JALALI_MONTHS[month - 1]
        
        # ✅ استفاده از سربرگ استاندارد شرکت
        from app.core.letterhead import get_filtered_company, render_letterhead_html
        company_profile = get_filtered_company(self.db)
        company_name = company_profile.get('company_name', 'شرکت')
        header_html = render_letterhead_html(company_profile)
        
        rows_html = ''.join(f"""<tr>
            <td>{i+1}</td>
            <td>{jalali_date_display_from_iso(t['transaction_date'])}</td>
            <td>{t['payment_type']}</td>
            <td>{int(t['amount']):,}</td>
            <td>{t['payment_method']}</td>
            <td>{t['reference_no'] or '-'}</td>
            <td>{t['description'] or '-'}</td>
        </tr>""" for i, t in enumerate(transactions))
        
        html = f"""<!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>رسید کلی پرداختی - {worker['full_name']}</title>
        <style>
            body {{ font-family: 'Tahoma', 'Arial', sans-serif; padding: 30px; max-width: 900px; margin: 0 auto; direction: rtl; line-height: 1.8; }}
            .header {{ text-align: center; border-bottom: 3px double #333; padding-bottom: 15px; margin-bottom: 30px; }}
            .header h1 {{ margin: 0; font-size: 24px; color: #2c3e50; }}
            .header p {{ margin: 5px 0; color: #7f8c8d; font-size: 14px; }}
            .info-box {{ background: #f8f9fa; border: 2px solid #2980b9; border-radius: 8px; padding: 15px; margin: 20px 0; }}
            .info-box p {{ margin: 5px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background: #2980b9; color: white; padding: 10px; text-align: center; }}
            td {{ padding: 8px; text-align: center; border: 1px solid #ddd; }}
            .total-box {{ background: #f8f9fa; border: 2px solid #2980b9; border-radius: 8px; padding: 15px; margin: 20px 0; text-align: center; }}
            .total-box .num {{ font-size: 20px; font-weight: bold; color: #c0392b; }}
            .total-box .words {{ font-size: 18px; font-weight: bold; color: #2c3e50; margin-top: 10px; }}
            .signature {{ display: flex; justify-content: space-between; margin-top: 60px; }}
            .sign-box {{ width: 45%; text-align: center; }}
            .sign-line {{ border-top: 2px solid #333; margin-top: 80px; padding-top: 10px; font-weight: bold; }}
            @media print {{
                .no-print {{ display: none; }}
                body {{ padding: 0; }}
            }}
        </style>
    </head>
    <body>
        <button class="no-print" onclick="window.print()" style="position:fixed; top:20px; left:20px; padding:10px 20px; background:#2980b9; color:white; border:none; border-radius:5px; cursor:pointer;">🖨️ چاپ</button>
        
        {header_html}
        
        <div style="text-align:center; margin-bottom:20px;">
            <h2 style="margin:10px 0; color:#2c3e50;">رسید کلی پرداختی به پرسنل</h2>
            <p style="color:#7f8c8d; font-size:14px;">بازه: {month_name} {year}</p>
        </div>
        
        <div class="info-box">
            <p><strong>نام و نام خانوادگی:</strong> {worker['full_name']}</p>
            <p><strong>کد ملی:</strong> {worker['national_id'] or '---'}</p>
            <p><strong>عنوان شغلی:</strong> {worker['job_title'] or '---'}</p>
            <p><strong>نام بانک:</strong> {worker['bank_name'] or '---'}</p>
            <p><strong>شماره کارت:</strong> {worker['card_number'] or '---'}</p>
            <p><strong>شماره حساب:</strong> {worker['bank_account'] or '---'}</p>
        </div>
        
        <table>
            <thead>
                <tr><th>ردیف</th><th>تاریخ</th><th>نوع پرداخت</th><th>مبلغ (ریال)</th><th>روش</th><th>پیگیری</th><th>توضیحات</th></tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        
        <div class="total-box">
            <div class="num">جمع کل پرداختی: {total_amount:,} ریال</div>
            <div class="words">معادل {amount_words} ریال</div>
        </div>
        
        <p style="margin-top:30px; text-align:justify;">
            اینجانب <strong>{worker['full_name']}</strong> با کد ملی <strong>{worker['national_id'] or '---'}</strong> 
            اقرار می‌نمایم که کلیه مبالغ مندرج در جدول فوق را در بازه زمانی {month_name} {year} از شرکت {company_name} دریافت نموده‌ام 
            و هیچگونه ادعای بعدی نسبت به این مبالغ نخواهم داشت.
        </p>
        
        <div class="signature">
            <div class="sign-box">
                <div class="sign-line">امضاء و اثر انگشت دریافت‌کننده<br><small>({worker['full_name']})</small></div>
            </div>
            <div class="sign-box">
                <div class="sign-line">مهر و امضاء پرداخت‌کننده<br><small>نماینده مجاز {company_name}</small></div>
            </div>
        </div>
    </body>
    </html>"""
        
        fd, path = tempfile.mkstemp(suffix='.html')
        os.write(fd, html.encode('utf-8'))
        os.close(fd)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))        

    def _generate_and_show_receipt(self, trans_id):
        with self.db.connect() as conn:
            res = conn.execute("""
                SELECT pt.transaction_date, pt.payment_type, pt.amount, pt.payment_method, 
                    pt.reference_no, pt.description,
                    pw.full_name, pw.national_id, pw.job_title, 
                    pw.bank_name, pw.card_number, pw.bank_account
                FROM payroll_transactions pt
                JOIN payroll_workers pw ON pw.id = pt.worker_id
                WHERE pt.id = ?
            """, (trans_id,)).fetchone()
            
            if not res:
                QMessageBox.warning(self, 'خطا', 'پرداختی یافت نشد.')
                return
            
            # ✅ استفاده از سربرگ استاندارد شرکت
            from app.core.letterhead import get_filtered_company, render_letterhead_html
            company_profile = get_filtered_company(self.db)
            company_name = company_profile.get('company_name', 'شرکت')
            header_html = render_letterhead_html(company_profile)

        amount_num = int(res['amount'])
        amount_words = self._number_to_persian_words(amount_num)
        date_jalali = jalali_date_display_from_iso(res['transaction_date'])
        
        ref_text = f" (شماره پیگیری/چک: {res['reference_no']})" if res['reference_no'] else ""
        desc_text = f"<br><strong>توضیحات:</strong> {res['description']}" if res['description'] else ""
        bank_info = f"<br><strong>نام بانک:</strong> {res['bank_name'] or '---'} | <strong>شماره کارت:</strong> {res['card_number'] or '---'} | <strong>شماره حساب:</strong> {res['bank_account'] or '---'}"
        
        html = f"""<!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>رسید پرداخت</title>
        <style>
            body {{ font-family: 'Tahoma', 'Arial', sans-serif; padding: 30px; max-width: 800px; margin: 0 auto; direction: rtl; line-height: 1.8; }}
            .header {{ text-align: center; border-bottom: 3px double #333; padding-bottom: 15px; margin-bottom: 30px; }}
            .header h1 {{ margin: 0; font-size: 24px; color: #2c3e50; }}
            .header p {{ margin: 5px 0; color: #7f8c8d; font-size: 14px; }}
            .content {{ font-size: 16px; text-align: justify; margin-bottom: 40px; }}
            .highlight {{ font-weight: bold; color: #2980b9; }}
            .amount-box {{ background: #f8f9fa; border: 2px solid #2980b9; border-radius: 8px; padding: 15px; margin: 20px 0; text-align: center; }}
            .amount-box .num {{ font-size: 20px; font-weight: bold; color: #c0392b; }}
            .amount-box .words {{ font-size: 18px; font-weight: bold; color: #2c3e50; margin-top: 10px; }}
            .signatures {{ display: flex; justify-content: space-between; margin-top: 60px; }}
            .sign-box {{ width: 40%; text-align: center; }}
            .sign-line {{ border-top: 2px solid #333; margin-top: 80px; padding-top: 10px; font-weight: bold; }}
            .fingerprint {{ border: 2px dashed #95a5a6; height: 80px; width: 80px; margin: 10px auto; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #95a5a6; font-size: 12px; }}
            @media print {{
                .no-print {{ display: none; }}
                body {{ padding: 0; }}
            }}
        </style>
    </head>
    <body>
        <button class="no-print" onclick="window.print()" style="position:fixed; top:20px; left:20px; padding:10px 20px; background:#2980b9; color:white; border:none; border-radius:5px; cursor:pointer;">️ چاپ رسید</button>
        
        {header_html}
        
        <div style="text-align:center; margin-bottom:20px;">
            <h2 style="margin:10px 0; color:#2c3e50;">رسید رسمی پرداخت وجه به پرسنل</h2>
            <p style="color:#7f8c8d; font-size:14px;">تاریخ صدور سیستمی: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        
        <div class="content">
            <p>اینجانب <span class="highlight">{res['full_name']}</span> به کد ملی <span class="highlight">{res['national_id'] or '---'}</span> 
            و با سمت <span class="highlight">{res['job_title'] or '---'}</span>،</p>
            
            <p>اقرار می‌نمایم که در تاریخ <span class="highlight">{date_jalali}</span>، مبلغ زیر را بابت 
            <span class="highlight">{res['payment_type']}{ref_text}</span> به صورت 
            <span class="highlight">{res['payment_method']}</span> از شرکت {company_name} دریافت نمودم.{bank_info}</p>
            
            {desc_text}
            
            <p style="margin-top:20px;">بدینوسیله تأیید می‌کنم که نسبت به مبلغ دریافتی فوق هیچگونه ادعای بعدی نخواهم داشت و این رسید به منزله‌ی تسویه حساب بابت مورد ذکر شده می‌باشد.</p>
        </div>
        
        <div class="amount-box">
            <div class="num">مبلغ دریافتی: {amount_num:,} ریال</div>
            <div class="words">معادل {amount_words} ریال</div>
        </div>
        
        <div class="signatures">
            <div class="sign-box">
                <div class="fingerprint">محل اثر انگشت</div>
                <div class="sign-line">امضاء و اثر انگشت دریافت‌کننده<br><small>({res['full_name']})</small></div>
            </div>
            <div class="sign-box">
                <div class="sign-line">مهر و امضاء پرداخت‌کننده<br><small>نماینده مجاز {company_name}</small></div>
            </div>
        </div>
    </body>
    </html>"""
        
        fd, path = tempfile.mkstemp(suffix='.html')
        os.write(fd, html.encode('utf-8'))
        os.close(fd)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))