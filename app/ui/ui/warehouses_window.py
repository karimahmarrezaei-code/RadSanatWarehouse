# -*- coding: utf-8 -*-
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
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from app.core.database import DatabaseManager
from app.core.validators import ValidationError
from app.repositories.warehouse_repository import WarehouseRepository


# استایل یکدست جدول‌ها؛ رنگ‌ها صریحاً تعریف شده تا ردیف یک‌درمیان
# به جای سفیدِ پوسته ویندوز، تیرهٔ هماهنگ با پوسته برنامه باشد
TABLE_STYLE = '''
QTableWidget {
    background-color: #141c28;
    alternate-background-color: #1d2836;
    color: #e8eef5;
    gridline-color: #33455c;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
    border: 1px solid #33455c;
}
QTableWidget::item {
    padding: 4px 8px;
}
QTableWidget::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #22304a;
    color: #dce6f2;
    font-weight: bold;
    border: 1px solid #33455c;
    padding: 6px 8px;
}
QTableCornerButton::section {
    background-color: #22304a;
    border: 1px solid #33455c;
}
'''


class WarehouseListDialog(QDialog):
    """پنجره مستقل نمایش لیست انبارها (دیتاگرید) با جستجو و فیلتر."""

    warehouse_selected = pyqtSignal(int)

    def __init__(self, repository: WarehouseRepository, parent=None) -> None:
        super().__init__(parent)
        self.repository = repository

        self.setWindowTitle('لیست انبارها')
        self.resize(980, 620)
        # غیرمودال؛ کاربر می‌تواند همزمان با فرم کار کند
        self.setModal(False)
        self._build_ui()
        self.refresh_table()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # --- نوار ابزار جستجو و فیلتر ---
        toolbar_card = QFrame()
        toolbar_card.setObjectName('Card')
        toolbar = QHBoxLayout(toolbar_card)
        toolbar.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('جستجو بر اساس کد، نام یا آدرس انبار...')
        self.search_edit.textChanged.connect(self.refresh_table)

        self.active_filter_combo = QComboBox()
        self.active_filter_combo.addItem('همه وضعیت‌ها', 'ALL')
        self.active_filter_combo.addItem('فقط فعال', 'ACTIVE')
        self.active_filter_combo.addItem('فقط غیرفعال', 'INACTIVE')
        self.active_filter_combo.currentIndexChanged.connect(self.refresh_table)

        refresh_button = QPushButton('بروزرسانی')
        refresh_button.setObjectName('SecondaryButton')
        refresh_button.clicked.connect(self.refresh_table)

        toolbar.addWidget(QLabel('جستجو:'))
        toolbar.addWidget(self.search_edit, 1)
        toolbar.addWidget(QLabel('وضعیت:'))
        toolbar.addWidget(self.active_filter_combo)
        toolbar.addWidget(refresh_button)
        root.addWidget(toolbar_card)

        # --- جدول (دیتاگرید) ---
        table_group = QGroupBox('لیست انبارها')
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            'شناسه', 'کد', 'نام', 'ظرفیت', 'آدرس', 'وضعیت', 'آخرین بروزرسانی',
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnHidden(0, True)
        # --- تنظیمات خوانایی جدول ---
        self._apply_table_style()
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(True)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setMinimumSectionSize(90)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Stretch)   # ستون آدرس کشسان
        header.setStretchLastSection(True)
        header.setFixedHeight(42)
        self.table.setColumnWidth(1, 110)   # کد
        self.table.setColumnWidth(2, 160)   # نام
        self.table.setColumnWidth(3, 110)   # ظرفیت
        self.table.setColumnWidth(5, 100)   # وضعیت
        # دابل‌کلیک روی ردیف => ارسال به فرم برای ویرایش
        self.table.itemDoubleClicked.connect(self._emit_selected)
        table_layout.addWidget(self.table)
        root.addWidget(table_group, 1)

        # --- دکمه‌های پایین پنجره ---
        buttons_row = QHBoxLayout()
        hint = QLabel('برای ویرایش، روی ردیف دابل‌کلیک کنید یا دکمه «انتخاب و ویرایش» را بزنید.')
        hint.setObjectName('Muted')
        buttons_row.addWidget(hint)
        buttons_row.addStretch()

        self.select_button = QPushButton('انتخاب و ویرایش')
        self.select_button.clicked.connect(self._emit_selected)

        close_button = QPushButton('بستن')
        close_button.setObjectName('SecondaryButton')
        close_button.clicked.connect(self.close)

        buttons_row.addWidget(self.select_button)
        buttons_row.addWidget(close_button)
        root.addLayout(buttons_row)

    def _apply_table_style(self) -> None:
        """هماهنگ‌سازی رنگ جدول با تم فعال برنامه (روشن/تاریک)"""
        from PyQt5.QtWidgets import QApplication
        theme = getattr(QApplication.instance(), 'app_theme', 'dark')
        if theme == 'dark':
            self.table.setStyleSheet(TABLE_STYLE)
        else:
            self.table.setStyleSheet('')

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_table_style()

    def refresh_table(self) -> None:
        rows = self.repository.list_warehouses(
            search_text=self.search_edit.text(),
            active_filter=self.active_filter_combo.currentData(),
        )
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            status_text = 'فعال' if row.get('is_active') else 'غیرفعال'
            last_update = row.get('updated_at') or row.get('created_at') or '-'
            values = [
                str(row.get('id')),
                row.get('code') or '-',
                row.get('name') or '-',
                str(row.get('capacity_count') or 0),
                row.get('address') or '-',
                status_text,
                last_update,
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_index, column_index, item)

    def select_row_by_id(self, warehouse_id: int) -> None:
        for row_index in range(self.table.rowCount()):
            item = self.table.item(row_index, 0)
            if item and int(item.text()) == warehouse_id:
                self.table.selectRow(row_index)
                break

    def _emit_selected(self, *args) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, 'انتخاب انبار', 'ابتدا یک ردیف را از جدول انتخاب کنید.')
            return
        warehouse_id = int(self.table.item(selected_items[0].row(), 0).text())
        self.warehouse_selected.emit(warehouse_id)


class WarehouseManagerWindow(QDialog):
    data_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.repository = WarehouseRepository(db)
        self.current_warehouse_id: Optional[int] = None
        self.list_dialog: Optional[WarehouseListDialog] = None

        permissions = set(user_data.get('permissions', []) or [])
        self.can_manage = 'warehouses.manage' in permissions or user_data.get('role_code') == 'ADMIN'
        self.can_view = self.can_manage or 'warehouses.view' in permissions

        self.setWindowTitle('مدیریت انبارها')
        # فرم تک‌ستونی و جمع‌وجور؛ جدول در پنجره جداگانه باز می‌شود
        self.resize(560, 600)
        self._build_ui()
        self.clear_form()
        self._apply_permissions()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # --- سربرگ ---
        header = QFrame()
        header.setObjectName('Card')
        header_layout = QHBoxLayout(header)

        titles_layout = QVBoxLayout()
        title = QLabel('مدیریت انبارها')
        title.setObjectName('Title')
        subtitle = QLabel('ثبت، ویرایش و حذف امن انبارها با اعتبارسنجی کامل')
        subtitle.setObjectName('Muted')
        subtitle.setWordWrap(True)
        titles_layout.addWidget(title)
        titles_layout.addWidget(subtitle)
        header_layout.addLayout(titles_layout, 1)

        # دکمه جداگانه برای باز کردن دیتاگرید در پنجره مستقل
        self.show_list_button = QPushButton('📋 نمایش لیست انبارها')
        self.show_list_button.clicked.connect(self.open_list_dialog)
        header_layout.addWidget(self.show_list_button, 0, Qt.AlignTop)

        root.addWidget(header)

        # --- فرم اطلاعات انبار (تک‌ستونی) ---
        form_group = QGroupBox('فرم اطلاعات انبار')
        form_layout = QVBoxLayout(form_group)

        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(12)
        info_grid.setVerticalSpacing(10)
        info_grid.setColumnStretch(1, 1)

        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(0, 100000000)
        self.is_active_checkbox = QCheckBox('انبار فعال است')
        self.is_active_checkbox.setChecked(True)

        # هر فیلد در یک ردیف جداگانه (تک‌ستونی)
        single_column_rows = [
            ('کد انبار', self.code_edit),
            ('نام انبار', self.name_edit),
            ('ظرفیت تعدادی', self.capacity_spin),
        ]
        for row_index, (label_text, widget) in enumerate(single_column_rows):
            info_grid.addWidget(QLabel(label_text), row_index, 0)
            info_grid.addWidget(widget, row_index, 1)
        info_grid.addWidget(self.is_active_checkbox, len(single_column_rows), 0, 1, 2)

        self.address_edit = QTextEdit()
        self.address_edit.setMinimumHeight(140)
        self.address_edit.setPlaceholderText('آدرس کامل انبار را وارد کنید...')

        form_layout.addLayout(info_grid)
        form_layout.addWidget(QLabel('آدرس'))
        form_layout.addWidget(self.address_edit)

        self.meta_label = QLabel('وضعیت رکورد: جدید')
        self.meta_label.setObjectName('Muted')
        form_layout.addWidget(self.meta_label)

        # --- دکمه‌های عملیات فرم ---
        form_actions = QHBoxLayout()
        self.new_button = QPushButton('فرم جدید')
        self.new_button.setObjectName('SecondaryButton')
        self.new_button.clicked.connect(self.clear_form)

        self.save_button = QPushButton('ذخیره')
        self.save_button.clicked.connect(self.save_warehouse)

        self.delete_button = QPushButton('حذف / غیرفعالسازی')
        self.delete_button.setObjectName('SecondaryButton')
        self.delete_button.clicked.connect(self.delete_warehouse)

        form_actions.addWidget(self.new_button)
        form_actions.addStretch()
        form_actions.addWidget(self.delete_button)
        form_actions.addWidget(self.save_button)
        form_layout.addLayout(form_actions)

        root.addWidget(form_group, 1)

    # ------------------------------------------------------------------
    # پنجره لیست انبارها (دیتاگرید جداگانه)
    # ------------------------------------------------------------------
    def open_list_dialog(self) -> None:
        """باز کردن دیتاگرید انبارها در یک پنجره مستقل با دکمه جداگانه."""
        if self.list_dialog is None:
            self.list_dialog = WarehouseListDialog(self.repository, parent=self)
            self.list_dialog.warehouse_selected.connect(self._load_warehouse_into_form)
        self.list_dialog.refresh_table()
        self.list_dialog.show()
        self.list_dialog.raise_()
        self.list_dialog.activateWindow()

    def _refresh_list_if_open(self, select_id: Optional[int] = None) -> None:
        if self.list_dialog is not None and self.list_dialog.isVisible():
            self.list_dialog.refresh_table()
            if select_id is not None:
                self.list_dialog.select_row_by_id(select_id)

    # ------------------------------------------------------------------
    # منطق فرم
    # ------------------------------------------------------------------
    def _apply_permissions(self) -> None:
        if not self.can_view:
            QMessageBox.critical(self, 'عدم دسترسی', 'شما اجازه مشاهده این بخش را ندارید.')
            self.setEnabled(False)
            return

        if not self.can_manage:
            widgets = [
                self.code_edit,
                self.name_edit,
                self.capacity_spin,
                self.address_edit,
                self.is_active_checkbox,
                self.new_button,
                self.save_button,
                self.delete_button,
            ]
            for widget in widgets:
                widget.setEnabled(False)
            self.meta_label.setText('دسترسی شما فقط مشاهده است.')

    def _collect_form_data(self) -> Dict[str, Any]:
        return {
            'code': self.code_edit.text(),
            'name': self.name_edit.text(),
            'capacity_count': self.capacity_spin.value(),
            'address': self.address_edit.toPlainText(),
            'is_active': self.is_active_checkbox.isChecked(),
        }

    def clear_form(self) -> None:
        self.current_warehouse_id = None
        self.code_edit.clear()
        self.name_edit.clear()
        self.capacity_spin.setValue(0)
        self.address_edit.clear()
        self.is_active_checkbox.setChecked(True)
        self.meta_label.setText('وضعیت رکورد: جدید')
        if self.list_dialog is not None:
            self.list_dialog.table.clearSelection()
        self.code_edit.setFocus()

    def _load_warehouse_into_form(self, warehouse_id: int) -> None:
        """بارگذاری اطلاعات انبار انتخاب‌شده از پنجره لیست در فرم."""
        row = self.repository.get_warehouse(warehouse_id)
        if not row:
            QMessageBox.warning(self, 'خطا', 'انبار موردنظر یافت نشد. لیست را بروزرسانی کنید.')
            return

        self.current_warehouse_id = warehouse_id
        self.code_edit.setText(row.get('code') or '')
        self.name_edit.setText(row.get('name') or '')
        self.capacity_spin.setValue(int(row.get('capacity_count') or 0))
        self.address_edit.setPlainText(row.get('address') or '')
        self.is_active_checkbox.setChecked(bool(row.get('is_active')))
        self.meta_label.setText(
            f"شناسه: {row.get('id')} | ایجاد: {row.get('created_at') or '-'} | بروزرسانی: {row.get('updated_at') or '-'}"
        )
        # فرم را جلو بیاور تا کاربر بلافاصله ویرایش کند
        self.raise_()
        self.activateWindow()

    def save_warehouse(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه ثبت یا ویرایش در این بخش را ندارید.')
            return

        payload = self._collect_form_data()
        try:
            if self.current_warehouse_id is None:
                saved = self.repository.create_warehouse(payload, user_id=self.user_data.get('id'))
                message = f"انبار «{saved.get('name', '')}» با موفقیت ثبت شد."
            else:
                saved = self.repository.update_warehouse(
                    self.current_warehouse_id,
                    payload,
                    user_id=self.user_data.get('id'),
                )
                message = f"انبار «{saved.get('name', '')}» با موفقیت بروزرسانی شد."
        except ValidationError as exc:
            QMessageBox.warning(self, 'اعتبارسنجی', str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'خطا', f'ذخیره اطلاعات با خطا مواجه شد:\n{exc}')
            return

        QMessageBox.information(self, 'ذخیره موفق', message)
        self._refresh_list_if_open(select_id=int(saved['id']))
        self.data_changed.emit()

    def delete_warehouse(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه حذف یا غیرفعالسازی در این بخش را ندارید.')
            return
        if self.current_warehouse_id is None:
            QMessageBox.information(
                self,
                'حذف انبار',
                'ابتدا یک انبار را از پنجره «لیست انبارها» انتخاب کنید.',
            )
            return

        answer = QMessageBox.question(
            self,
            'تأیید حذف',
            'آیا از حذف این انبار مطمئن هستید؟\nاگر در عملیات انبار یا موجودی استفاده شده باشد، غیرفعال می‌شود.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            action_result, record = self.repository.delete_warehouse(
                self.current_warehouse_id,
                user_id=self.user_data.get('id'),
            )
        except ValidationError as exc:
            QMessageBox.warning(self, 'حذف انبار', str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'خطا', f'حذف اطلاعات با خطا مواجه شد:\n{exc}')
            return

        if action_result == 'deleted':
            QMessageBox.information(self, 'حذف شد', f"انبار «{record.get('name', '')}» حذف شد.")
        else:
            QMessageBox.information(
                self,
                'غیرفعال شد',
                f"انبار «{record.get('name', '')}» به‌صورت امن غیرفعال شد.",
            )
        self.clear_form()
        self._refresh_list_if_open()
        self.data_changed.emit()
