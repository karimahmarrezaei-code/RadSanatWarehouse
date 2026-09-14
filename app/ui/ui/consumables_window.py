# -*- coding: utf-8 -*-
"""
consumables_window.py - فرم ثبت مصارف مصرفی انبار (v5)

- انتخاب قلم مصرفی → واحد به‌صورت کامبو لود می‌شود
- انتخاب حساب پرداخت (صندوق/بانک) → موجودی آن کم می‌شود
- بدون خطای موجودی قلم — کاربر مصرف‌کننده است (موجودی به صفر می‌رسد)
- ثبت هزینه در expenses (SETTLED) + کسر از treasury_accounts + treasury_transactions
- بعد از ثبت: فقط پیام موفقیت (جلوگیری از ثبت دوباره)
- دکمه گزارش خرید اقلام مصرفی

استفاده:
    from app.ui.consumables_window import ConsumablesWindow
    ConsumablesWindow(db, user_data).exec_()
"""
import sqlite3
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QComboBox, QLineEdit, QDateEdit, QGroupBox, QFormLayout, QSpinBox,
)

from app.core.unit_utils import list_units
from app.core.consumable_utils import (
    list_consumables, get_consumable, ensure_expenses_qty_columns,
)


class ConsumablesWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('🧰 ثبت مصارف مصرفی انبار')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(640, 620)
        self._load_data()
        self._build_ui()

    def _load_data(self):
        self.warehouses = []
        self.consumables = []
        self.units = []
        self.accounts = []
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                ensure_expenses_qty_columns(conn)
                self.warehouses = conn.execute(
                    'SELECT id, code, name FROM warehouses WHERE is_active = 1 ORDER BY name'
                ).fetchall()
                self.consumables = list_consumables(conn, active_only=True)
                self.units = list_units(conn, active_only=True)
                self.accounts = conn.execute(
                    'SELECT id, code, name, account_type, current_balance '
                    'FROM treasury_accounts WHERE is_active = 1 ORDER BY name'
                ).fetchall()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در بارگذاری:\n{}'.format(e))

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(14)

        group = QGroupBox('اطلاعات مصرف')
        form = QFormLayout(group)
        form.setSpacing(10)

        # انبار
        self.warehouse_combo = QComboBox()
        self.warehouse_combo.addItem('انتخاب انبار', None)
        for w in self.warehouses:
            self.warehouse_combo.addItem('{} - {}'.format(w[1] or '', w[2] or ''), w[0])
        form.addRow('انبار:', self.warehouse_combo)

        # قلم مصرفی
        self.item_combo = QComboBox()
        self.item_combo.addItem('انتخاب قلم مصرفی', None)
        for c in self.consumables:
            label = '{} (موجودی: {})'.format(c['name'], c['current_qty'])
            self.item_combo.addItem(label, c['id'])
        form.addRow('قلم مصرفی:', self.item_combo)

        # واحد (کامبو)
        self.unit_combo = QComboBox()
        self.unit_combo.addItem('انتخاب واحد', None)
        for u in self.units:
            self.unit_combo.addItem(u['name'], u['id'])
        form.addRow('واحد:', self.unit_combo)

        # تعداد
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 100000000)
        self.qty_spin.setValue(1)
        form.addRow('تعداد:', self.qty_spin)

        # مبلغ واحد
        self.price_edit = QLineEdit()
        self.price_edit.setPlaceholderText('مبلغ واحد (ریال)')
        form.addRow('مبلغ واحد:', self.price_edit)

        # حساب پرداخت (صندوق/بانک)
        self.account_combo = QComboBox()
        self.account_combo.addItem('انتخاب حساب پرداخت (صندوق/بانک)', None)
        for a in self.accounts:
            type_label = 'صندوق' if a[3] == 'CASHBOX' else 'بانک'
            display = '{} [{}] (موجودی: {:,} ریال)'.format(a[2], type_label, int(a[4] or 0))
            self.account_combo.addItem(display, a[0])
        form.addRow('حساب پرداخت:', self.account_combo)

        # تاریخ
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat('yyyy-MM-dd')
        form.addRow('تاریخ:', self.date_edit)

        self.date_jalali_lbl = QLabel('-')
        self.date_jalali_lbl.setStyleSheet('font-size: 13px; font-weight: bold; color: #0284c7;')
        form.addRow('تاریخ شمسی:', self.date_jalali_lbl)
        # توضیحات
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText('توضیحات مصرف (اختیاری)')
        form.addRow('توضیحات:', self.desc_edit)

        root.addWidget(group)

        # جمع مبلغ
        total_row = QHBoxLayout()
        total_row.addStretch()
        self.total_lbl = QLabel('جمع مبلغ: 0 ریال')
        self.total_lbl.setStyleSheet('font-size: 15px; font-weight: bold; color: #2563eb;')
        total_row.addWidget(self.total_lbl)
        root.addLayout(total_row)

        # دکمه‌ها
        btns = QHBoxLayout()
        self.save_btn = QPushButton('✔ ثبت مصرف')
        self.save_btn.setStyleSheet(
            'background-color: #10b981; color: white; font-weight: bold; padding: 10px 24px; border-radius: 8px;'
        )
        self.save_btn.clicked.connect(self._save)
        btns.addWidget(self.save_btn)

        new_btn = QPushButton('فرم جدید')
        new_btn.clicked.connect(self._reset_form)
        btns.addWidget(new_btn)
        del_btn = QPushButton('🗑 حذف آخرین مصرف')
        del_btn.setStyleSheet('background-color: #dc2626; color: white; font-weight: bold; padding: 10px 20px; border-radius: 8px;')
        del_btn.clicked.connect(self._delete_last)
        btns.addWidget(del_btn)
        report_btn = QPushButton('📊 گزارش خرید اقلام')
        report_btn.setStyleSheet(
            'background-color: #7c3aed; color: white; font-weight: bold; padding: 10px 20px; border-radius: 8px;'
        )
        report_btn.clicked.connect(self._open_report)
        btns.addWidget(report_btn)

        btns.addStretch()
        close_btn = QPushButton('بستن')
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        root.addLayout(btns)

        # اتصال
        self.item_combo.currentIndexChanged.connect(self._on_item_changed)
        self.date_edit.dateChanged.connect(self._update_jalali_lbl)
        self._update_jalali_lbl()
        self.qty_spin.valueChanged.connect(self._update_total)
        self.price_edit.textChanged.connect(self._update_total)

    def _on_item_changed(self):
        item_id = self.item_combo.currentData()
        if item_id:
            try:
                with self.db.connect() as conn:
                    conn.row_factory = None
                    it = get_consumable(conn, item_id)
                if it:
                    self.unit_combo.setCurrentIndex(0)
                    for idx in range(self.unit_combo.count()):
                        if self.unit_combo.itemData(idx) == it['unit_id']:
                            self.unit_combo.setCurrentIndex(idx)
                            break
                    return
            except Exception:
                pass
        self.unit_combo.setCurrentIndex(0)

    def _int_from_text(self, t):
        try:
            return int(''.join(ch for ch in t if ch.isdigit()) or 0)
        except Exception:
            return 0

    def _update_total(self):
        qty = self.qty_spin.value()
        price = self._int_from_text(self.price_edit.text())
        self.total_lbl.setText('جمع مبلغ: {:,} ریال'.format(qty * price))

    def _save(self):
        wh_id = self.warehouse_combo.currentData()
        item_id = self.item_combo.currentData()
        unit_id = self.unit_combo.currentData()
        account_id = self.account_combo.currentData()
        qty = self.qty_spin.value()
        price = self._int_from_text(self.price_edit.text())
        if not wh_id:
            QMessageBox.warning(self, 'خطا', 'انبار را انتخاب کنید.')
            return
        if not item_id:
            QMessageBox.warning(self, 'خطا', 'قلم مصرفی را انتخاب کنید.')
            return
        if not unit_id:
            QMessageBox.warning(self, 'خطا', 'واحد را انتخاب کنید.')
            return
        if not account_id:
            QMessageBox.warning(self, 'خطا', 'حساب پرداخت (صندوق/بانک) را انتخاب کنید.')
            return
        if price <= 0:
            QMessageBox.warning(self, 'خطا', 'مبلغ واحد را وارد کنید.')
            return
        total = qty * price
        date_iso = self.date_edit.date().toString('yyyy-MM-dd')
        today_iso = QDate.currentDate().toString('yyyy-MM-dd')
        is_future = date_iso > today_iso
        desc = self.desc_edit.text().strip() or 'مصرف مصرفی انبار'
        from datetime import datetime as _dt
        now_ts = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with self.db.connect() as conn:
                conn.row_factory = sqlite3.Row
                ensure_expenses_qty_columns(conn)
                conn.execute('BEGIN')
                acc_row = conn.execute(
                    'SELECT current_balance, name FROM treasury_accounts WHERE id = ?', (account_id,)
                ).fetchone()
                if not acc_row:
                    raise ValueError('حساب پرداخت یافت نشد.')
                balance_before = int(acc_row[0] or 0)
                if not is_future and balance_before < total:
                    raise ValueError(
                        'موجودی حساب «{}» کافی نیست!\nموجودی: {:,} ریال\nمبلغ: {:,} ریال\nکسری: {:,} ریال'.format(
                            acc_row[1], balance_before, total, total - balance_before))
                # [DUE] سررسید آینده => هزینه باز بدون پرداخت؛ sonst تسویه فوری
                if is_future:
                    status, paid_now = 'OPEN', 0
                else:
                    status, paid_now = 'SETTLED', total
                cat_id = 7
                row = conn.execute('SELECT id FROM expense_categories WHERE id = 7').fetchone()
                if not row:
                    row2 = conn.execute('SELECT id FROM expense_categories WHERE name LIKE ?',
                                        ('%مصرفی%',)).fetchone()
                    cat_id = row2[0] if row2 else 5
                exp_no = None
                try:
                    from app.core.sequence_utils import next_sequence_no
                    candidate = next_sequence_no(conn, 'EX', iso_date=date_iso)
                    existing_no = conn.execute(
                        'SELECT id FROM expenses WHERE expense_no = ?', (candidate,)
                    ).fetchone()
                    if not existing_no:
                        exp_no = candidate
                except Exception:
                    pass
                if not exp_no:
                    row_max = conn.execute(
                        "SELECT MAX(CAST(SUBSTR(expense_no, 4) AS INTEGER)) AS mx FROM expenses WHERE expense_no LIKE 'EX-%'"
                    ).fetchone()
                    last_num = int(row_max[0]) if row_max and row_max[0] else 0
                    exp_no = 'EX-{:06d}'.format(last_num + 1)
                it = get_consumable(conn, item_id)
                item_name = it['name'] if it else desc
                conn.execute(
                    'INSERT INTO expenses (expense_no, expense_date, category_id, description, '
                    'amount, paid_amount, status, created_by, created_at, quantity, consumable_item_id, paid_from_account_id) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (exp_no, date_iso, cat_id, 'مصرف مصرفی: {}'.format(item_name),
                     total, paid_now, status, self.user_data.get('id'), now_ts,
                     qty, item_id, account_id)
                )
                expense_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                # کسر موجودی قلم (کالا صادر شده) - همیشه
                if it:
                    current = int(it['current_qty'] or 0)
                    new_qty = max(current - qty, 0)
                    conn.execute(
                        'UPDATE consumable_items SET current_qty = ?, updated_at = ? WHERE id = ?',
                        (new_qty, now_ts, item_id),
                    )
                # [DUE] کسر از حساب فقط وقتی سررسید نرسیده باشد
                if not is_future:
                    new_balance = balance_before - total
                    conn.execute(
                        'UPDATE treasury_accounts SET current_balance = ?, updated_at = ? WHERE id = ?',
                        (new_balance, now_ts, account_id),
                    )
                    try:
                        conn.execute(
                            "INSERT INTO treasury_transactions (treasury_account_id, transaction_date, "
                            "transaction_type, source_type, source_id, amount, balance_after, description, created_at) "
                            "VALUES (?, ?, 'OUT', 'EXPENSE', ?, ?, ?, ?, ?)",
                            (account_id, date_iso, expense_id, total, new_balance,
                             'مصرف مصرفی: {}'.format(item_name), now_ts),
                        )
                    except Exception:
                        pass
                conn.commit()
            if is_future:
                QMessageBox.information(
                    self, 'ثبت موفق',
                    'مصرف با تاریخ سررسید {} ثبت شد.\nهزینه: {:,} ریال | شماره: {}\n\n'
                    'چون سررسید در آینده است، فعلاً از حساب کسر نشد و هزینه «باز» ثبت شد.\n'
                    'در سررسید از «گزارش هزینه‌ها» دکمه «تسویه هزینه» را بزنید.'.format(date_iso, total, exp_no))
            else:
                QMessageBox.information(
                    self, 'ثبت موفق',
                    'مصرف ثبت شد.\nهزینه: {:,} ریال\nشماره: {}\nاز حساب «{}» کسر شد.\n\nاین هزینه قبلاً در حسابداری ثبت شده است.'.format(
                        total, exp_no, acc_row[1]),
                )
            self._reset_form()
        except ValueError as e:
            try:
                with self.db.connect() as conn:
                    conn.execute('ROLLBACK')
            except Exception:
                pass
            QMessageBox.warning(self, 'خطا', str(e))
        except Exception as e:
            try:
                with self.db.connect() as conn:
                    conn.execute('ROLLBACK')
            except Exception:
                pass
            QMessageBox.critical(self, 'خطا', 'خطا در ثبت مصرف:\n{}'.format(e))
    def _update_jalali_lbl(self):
        try:
            from app.core.jalali import jalali_date_display_from_iso
            self.date_jalali_lbl.setText(jalali_date_display_from_iso(self.date_edit.date().toString('yyyy-MM-dd')))
        except Exception:
            self.date_jalali_lbl.setText('-')

    def _delete_last(self):
        eid = getattr(self, 'last_expense_id', None)
        if not eid:
            QMessageBox.information(self, 'حذف', 'در این جلسه مصرفی ثبت نشده است.')
            return
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute('SELECT quantity, consumable_item_id, paid_from_account_id, amount, expense_no FROM expenses WHERE id = ?', (eid,)).fetchone()
                if not row:
                    QMessageBox.information(self, 'حذف', 'این مصرف قبلاً حذف شده است.')
                    self.last_expense_id = None
                    return
                reply = QMessageBox.question(self, 'تأیید حذف', 'مصرف {} به مبلغ {:,} ریال حذف و معکوس شود؟'.format(row[4], int(row[3] or 0)), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
                conn.execute('BEGIN')
                if row[1]:
                    conn.execute('UPDATE consumable_items SET current_qty = current_qty + ? WHERE id = ?', (int(row[0] or 0), row[1]))
                if row[2]:
                    conn.execute('UPDATE treasury_accounts SET current_balance = current_balance + ? WHERE id = ?', (int(row[3] or 0), row[2]))
                    bal = conn.execute('SELECT current_balance FROM treasury_accounts WHERE id = ?', (row[2],)).fetchone()
                    try:
                        from datetime import datetime as _dt
                        conn.execute("INSERT INTO treasury_transactions (treasury_account_id, transaction_date, transaction_type, source_type, source_id, amount, balance_after, description, created_at) VALUES (?, ?, 'IN', 'EXPENSE_REVERSE', ?, ?, ?, ?, ?)", (row[2], self.date_edit.date().toString('yyyy-MM-dd'), eid, int(row[3] or 0), int(bal[0] or 0), 'حذف مصرف: {}'.format(row[4]), _dt.now().strftime('%Y-%m-%d %H:%M:%S')))
                    except Exception:
                        pass
                conn.execute("DELETE FROM treasury_transactions WHERE source_type = 'EXPENSE' AND source_id = ?", (eid,))
                conn.execute('DELETE FROM expenses WHERE id = ?', (eid,))
                conn.commit()
            self.last_expense_id = None
            QMessageBox.information(self, 'حذف', 'مصرف حذف شد؛ مبلغ به حساب و موجودی قلم بازگردانده شد.')
            self._reset_form()
        except Exception as e:
            try:
                with self.db.connect() as conn:
                    conn.execute('ROLLBACK')
            except Exception:
                pass
            QMessageBox.critical(self, 'خطا', 'خطا در حذف:\n{}'.format(e))

    def _open_report(self):
        try:
            from app.ui.consumable_report_window import ConsumableReportWindow
            dlg = ConsumableReportWindow(self.db, self.user_data, self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در باز کردن گزارش:\n{}'.format(e))

    def _reset_form(self):
        self.item_combo.setCurrentIndex(0)
        self.unit_combo.setCurrentIndex(0)
        self.qty_spin.setValue(1)
        self.price_edit.clear()
        self.desc_edit.clear()
        self._update_total()
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                self.consumables = list_consumables(conn, active_only=True)
            current = self.item_combo.currentData()
            self.item_combo.clear()
            self.item_combo.addItem('انتخاب قلم مصرفی', None)
            for c in self.consumables:
                label = '{} (موجودی: {})'.format(c['name'], c['current_qty'])
                self.item_combo.addItem(label, c['id'])
            if current:
                idx = self.item_combo.findData(current)
                self.item_combo.setCurrentIndex(idx if idx >= 0 else 0)
        except Exception:
            pass
