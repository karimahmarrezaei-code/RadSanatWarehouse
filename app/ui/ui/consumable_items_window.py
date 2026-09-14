# -*- coding: utf-8 -*-
"""
consumable_items_window.py - فرم تعریف اقلام مصرفی انبار (v3)

- کد خودکار (CONS-0001 و...) به‌صورت لیبل نمایش داده می‌شود
- افزودن / ویرایش / حذف
- هر قلم به واحد و انبار وصل است

استفاده:
    from app.ui.consumable_items_window import ConsumableItemsWindow
    ConsumableItemsWindow(db, user_data).exec_()
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QMessageBox, QLineEdit, QComboBox,
    QSpinBox, QGroupBox, QFormLayout, QHeaderView, QAbstractItemView,
)

from app.core.unit_utils import list_units
from app.core.consumable_utils import (
    list_consumables, add_consumable, update_consumable, delete_consumable,
    get_consumable, next_consumable_code,
)


class ConsumableItemsWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.editing_id = None
        self.setWindowTitle('🧰 تعریف اقلام مصرفی انبار')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(820, 600)
        self._load_data()
        self._build_ui()
        self.refresh()

    def _load_data(self):
        self.warehouses = []
        self.units = []
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                self.warehouses = conn.execute(
                    'SELECT id, code, name FROM warehouses WHERE is_active = 1 ORDER BY name'
                ).fetchall()
                self.units = list_units(conn, active_only=True)
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در بارگذاری:\n{}'.format(e))

    def _refresh_code_label(self):
        """نمایش کد بعدی به‌صورت لیبل"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                code = next_consumable_code(conn)
            self.code_lbl.setText('کد: {}'.format(code))
        except Exception:
            self.code_lbl.setText('کد: CONS-0001')

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)

        add_group = QGroupBox('افزودن / ویرایش قلم مصرفی')
        form = QFormLayout(add_group)
        form.setSpacing(8)

        # کد خودکار به‌صورت لیبل
        self.code_lbl = QLabel('-')
        self.code_lbl.setStyleSheet('font-size: 14px; font-weight: bold; color: #2563eb;')
        form.addRow('کد:', self.code_lbl)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('نام قلم مصرفی (مثل: روغن، ابزار، دستکش...)')
        form.addRow('نام:', self.name_edit)

        self.unit_combo = QComboBox()
        self.unit_combo.addItem('انتخاب واحد', None)
        for u in self.units:
            self.unit_combo.addItem(u['name'], u['id'])
        form.addRow('واحد:', self.unit_combo)

        self.wh_combo = QComboBox()
        self.wh_combo.addItem('انتخاب انبار', None)
        for w in self.warehouses:
            self.wh_combo.addItem('{} - {}'.format(w[1] or '', w[2] or ''), w[0])
        form.addRow('انبار:', self.wh_combo)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 100000000)
        self.qty_spin.setValue(0)
        form.addRow('موجودی اولیه:', self.qty_spin)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText('توضیحات (اختیاری)')
        form.addRow('توضیحات:', self.desc_edit)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton('➕ افزودن قلم')
        self.add_btn.setStyleSheet(
            'background-color: #2563eb; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px;'
        )
        self.add_btn.clicked.connect(self._add)
        btn_row.addWidget(self.add_btn)

        self.save_edit_btn = QPushButton('💾 ذخیره ویرایش')
        self.save_edit_btn.setStyleSheet(
            'background-color: #0891b2; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px;'
        )
        self.save_edit_btn.clicked.connect(self._save_edit)
        self.save_edit_btn.setEnabled(False)
        btn_row.addWidget(self.save_edit_btn)

        self.cancel_edit_btn = QPushButton('✖ انصراف ویرایش')
        self.cancel_edit_btn.setStyleSheet('padding: 8px 16px;')
        self.cancel_edit_btn.clicked.connect(self._cancel_edit)
        self.cancel_edit_btn.setEnabled(False)
        btn_row.addWidget(self.cancel_edit_btn)

        btn_row.addStretch()
        form.addRow(btn_row)

        root.addWidget(add_group)

        # جدول
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(['شناسه', 'کد', 'نام', 'واحد', 'انبار', 'موجودی', 'وضعیت'])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._start_edit)
        root.addWidget(self.table, 1)

        # دکمه‌ها
        btns = QHBoxLayout()
        self.edit_btn = QPushButton('✏️ ویرایش')
        self.edit_btn
        self.edit_btn.clicked.connect(self._start_edit)
        btns.addWidget(self.edit_btn)

        self.delete_btn = QPushButton('🗑 حذف')
        self.delete_btn
        self.delete_btn.clicked.connect(self._delete)
        btns.addWidget(self.delete_btn)

        btns.addStretch()
        close_btn = QPushButton('بستن')
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        root.addLayout(btns)

        self._refresh_code_label()

    def refresh(self):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                items = list_consumables(conn, active_only=False)
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در بارگذاری اقلام:\n{}'.format(e))
            return
        self.table.setRowCount(len(items))
        for i, it in enumerate(items):
            self.table.setItem(i, 0, QTableWidgetItem(str(it['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(it['code'] or '-'))
            self.table.setItem(i, 2, QTableWidgetItem(it['name']))
            self.table.setItem(i, 3, QTableWidgetItem(it['unit_name']))
            self.table.setItem(i, 4, QTableWidgetItem(it['warehouse_name']))
            qty_item = QTableWidgetItem(str(it['current_qty']))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 5, qty_item)
            self.table.setItem(i, 6, QTableWidgetItem('فعال' if it['is_active'] else 'غیرفعال'))
        self._refresh_code_label()

    def _clear_form(self):
        self.editing_id = None
        self.name_edit.clear()
        self.desc_edit.clear()
        self.qty_spin.setValue(0)
        self.unit_combo.setCurrentIndex(0)
        self.wh_combo.setCurrentIndex(0)
        self.add_btn.setEnabled(True)
        self.save_edit_btn.setEnabled(False)
        self.cancel_edit_btn.setEnabled(False)
        self.add_btn.setText('➕ افزودن قلم')
        self._refresh_code_label()

    def _add(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, 'خطا', 'نام قلم مصرفی را وارد کنید.')
            return
        unit_id = self.unit_combo.currentData()
        wh_id = self.wh_combo.currentData()
        qty = self.qty_spin.value()
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                code = next_consumable_code(conn)
                add_consumable(conn, name, unit_id, wh_id, qty, code,
                               self.desc_edit.text().strip() or None)
            self._clear_form()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در افزودن:\n{}'.format(e))

    def _start_edit(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'قلم مصرفی', 'ابتدا یک قلم را از جدول انتخاب کنید.')
            return
        item_id = int(self.table.item(row, 0).text())
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                it = get_consumable(conn, item_id)
            if not it:
                QMessageBox.warning(self, 'خطا', 'قلم یافت نشد.')
                return
            self.editing_id = item_id
            self.code_lbl.setText('کد: {}'.format(it['code'] or '-'))
            self.name_edit.setText(it['name'])
            self.desc_edit.setText(it['description'] or '')
            self.qty_spin.setValue(int(it['current_qty'] or 0))
            self.unit_combo.setCurrentIndex(0)
            for idx in range(self.unit_combo.count()):
                if self.unit_combo.itemData(idx) == it['unit_id']:
                    self.unit_combo.setCurrentIndex(idx)
                    break
            self.wh_combo.setCurrentIndex(0)
            for idx in range(self.wh_combo.count()):
                if self.wh_combo.itemData(idx) == it['warehouse_id']:
                    self.wh_combo.setCurrentIndex(idx)
                    break
            self.add_btn.setEnabled(False)
            self.save_edit_btn.setEnabled(True)
            self.cancel_edit_btn.setEnabled(True)
            self.add_btn.setText('در حال ویرایش')
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در بارگذاری برای ویرایش:\n{}'.format(e))

    def _save_edit(self):
        if not self.editing_id:
            return
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, 'خطا', 'نام قلم مصرفی را وارد کنید.')
            return
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                update_consumable(
                    conn, self.editing_id,
                    name=name,
                    unit_id=self.unit_combo.currentData(),
                    warehouse_id=self.wh_combo.currentData(),
                    description=self.desc_edit.text().strip() or None,
                )
            self._clear_form()
            self.refresh()
            QMessageBox.information(self, 'موفق', 'ویرایش ذخیره شد.')
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در ذخیره ویرایش:\n{}'.format(e))

    def _cancel_edit(self):
        self._clear_form()

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'قلم مصرفی', 'ابتدا یک قلم را از جدول انتخاب کنید.')
            return
        item_id = int(self.table.item(row, 0).text())
        name = self.table.item(row, 2).text()
        reply = QMessageBox.question(
            self, 'حذف قلم',
            'قلم «{}» حذف شود؟\n(اگر سابقه مصرف داشته باشد فقط غیرفعال می‌شود)'.format(name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                used = conn.execute(
                    'SELECT COUNT(*) FROM expenses WHERE consumable_item_id = ?',
                    (item_id,),
                ).fetchone()
                used_count = int(used[0] if used else 0)
                if used_count > 0:
                    delete_consumable(conn, item_id)
                    QMessageBox.information(
                        self, 'حذف',
                        'این قلم سابقه مصرف دارد؛ غیرفعال شد (برای حفظ تاریخچه مالی).',
                    )
                else:
                    conn.execute('DELETE FROM consumable_items WHERE id = ?', (item_id,))
                    conn.commit()
                    QMessageBox.information(self, 'حذف', 'قلم حذف شد.')
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در حذف:\n{}'.format(e))
