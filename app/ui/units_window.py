# -*- coding: utf-8 -*-
"""
units_window.py - فرم مدیریت واحدهای کالا

- نمایش واحدهای موجود (پیش‌فرض + تعریف‌شده)
- افزودن واحد جدید
- ویرایش / غیرفعال کردن

استفاده:
    from app.ui.units_window import UnitsManagerWindow
    UnitsManagerWindow(db, user_data).exec_()
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QMessageBox, QLineEdit, QHeaderView,
    QAbstractItemView,
)

from app.core.unit_utils import list_units, add_unit, update_unit, delete_unit


class UnitsManagerWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('📦 مدیریت واحدهای کالا')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(650, 500)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # فرم افزودن
        add_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('نام واحد (مثل: عدد، کارتن، لیتر...)')
        add_row.addWidget(self.name_edit, 2)
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText('کد (اختیاری)')
        self.code_edit.setFixedWidth(120)
        add_row.addWidget(self.code_edit)
        self.add_btn = QPushButton('➕ افزودن')
        self.add_btn.setStyleSheet(
            'background-color: #2563eb; color: white; font-weight: bold; padding: 8px 18px; border-radius: 6px;'
        )
        self.add_btn.clicked.connect(self._add)
        add_row.addWidget(self.add_btn)
        root.addLayout(add_row)

        # جدول
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['شناسه', 'نام واحد', 'کد', 'وضعیت'])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        # دکمه‌ها
        btns = QHBoxLayout()
        self.disable_btn = QPushButton('🚫 غیرفعال کردن')
        self.disable_btn
        self.disable_btn.clicked.connect(self._disable)
        btns.addWidget(self.disable_btn)
        btns.addStretch()
        close_btn = QPushButton('بستن')
        close_btn.setStyleSheet('padding: 8px 20px;')
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        root.addLayout(btns)

    def refresh(self):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                units = list_units(conn, active_only=False)
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در بارگذاری واحدها:\n{}'.format(e))
            return
        self.table.setRowCount(len(units))
        for i, u in enumerate(units):
            self.table.setItem(i, 0, QTableWidgetItem(str(u['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(u['name']))
            self.table.setItem(i, 2, QTableWidgetItem(u['code'] or '-'))
            self.table.setItem(i, 3, QTableWidgetItem('فعال' if u['is_active'] else 'غیرفعال'))

    def _add(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, 'خطا', 'نام واحد را وارد کنید.')
            return
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                add_unit(conn, name, self.code_edit.text().strip() or None)
            self.name_edit.clear()
            self.code_edit.clear()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در افزودن:\n{}'.format(e))

    def _disable(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'واحد', 'ابتدا یک واحد را انتخاب کنید.')
            return
        uid = int(self.table.item(row, 0).text())
        name = self.table.item(row, 1).text()
        reply = QMessageBox.question(
            self, 'غیرفعال کردن', 'واحد «{}» غیرفعال شود؟'.format(name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                delete_unit(conn, uid)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا:\n{}'.format(e))
