# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
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
from app.core.jalali import jalali_date_display_from_iso
from app.core.database import DatabaseManager
from app.core.validators import ValidationError
from app.repositories.pallet_repository import PalletRepository


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



def apply_table_style_by_theme(table) -> None:
    """هماهنگ‌سازی رنگ جدول با تم فعال برنامه (روشن/تاریک)"""
    from PyQt5.QtWidgets import QApplication
    theme = getattr(QApplication.instance(), 'app_theme', 'dark')
    if theme == 'dark':
        table.setStyleSheet(TABLE_STYLE)
    else:
        table.setStyleSheet('')

class PalletListDialog(QDialog):
    """پنجره مستقل نمایش لیست پالت‌ها (دیتاگرید) با جستجو و فیلتر."""

    pallet_selected = pyqtSignal(int)

    def __init__(self, repository: PalletRepository, parent=None) -> None:
        super().__init__(parent)
        self.repository = repository

        self.setWindowTitle('لیست پالت‌ها')
        self.resize(980, 620)
        # پنجره غیرمودال؛ کاربر می‌تواند همزمان با فرم کار کند
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
        self.search_edit.setPlaceholderText('جستجو بر اساس کد، نام یا جنس پالت...')
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
        table_group = QGroupBox('لیست پالت‌ها')
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            'شناسه', 'کد', 'نام', 'جنس', 'ابعاد',
            'موجودی اولیه', 'حد هشدار', 'وضعیت', 'آخرین بروزرسانی',
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnHidden(0, True)
        # --- تنظیمات خوانایی جدول ---
        apply_table_style_by_theme(self.table)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(True)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setMinimumSectionSize(90)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)   # ستون نام کشسان
        header.setStretchLastSection(True)
        header.setFixedHeight(42)
        self.table.setColumnWidth(1, 110)   # کد
        self.table.setColumnWidth(3, 110)   # جنس
        self.table.setColumnWidth(4, 140)   # ابعاد
        self.table.setColumnWidth(5, 120)   # موجودی اولیه
        self.table.setColumnWidth(6, 110)   # حد هشدار
        self.table.setColumnWidth(7, 100)   # وضعیت
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

    def showEvent(self, event) -> None:
        super().showEvent(event)
        apply_table_style_by_theme(self.table)

    def refresh_table(self) -> None:
        rows = self.repository.list_pallets(
            search_text=self.search_edit.text(),
            active_filter=self.active_filter_combo.currentData(),
        )
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            dimensions = f"{row['length_cm']} × {row['width_cm']} × {row['height_cm']}"
            status_text = 'فعال' if row['is_active'] else 'غیرفعال'
            raw_update = row['updated_at'] or row['created_at']
            last_update = jalali_date_display_from_iso(str(raw_update)[:10]) if raw_update else '-'
            values = [
                str(row['id']),
                row['code'],
                row['name'],
                row['material_type'],
                dimensions,
                str(row['opening_stock']),
                str(row['low_stock_threshold']),
                status_text,
                last_update,
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_index, column_index, item)

    def select_row_by_id(self, pallet_id: int) -> None:
        for row_index in range(self.table.rowCount()):
            item = self.table.item(row_index, 0)
            if item and int(item.text()) == pallet_id:
                self.table.selectRow(row_index)
                break

    def _emit_selected(self, *args) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, 'انتخاب پالت', 'ابتدا یک ردیف را از جدول انتخاب کنید.')
            return
        pallet_id = int(self.table.item(selected_items[0].row(), 0).text())
        self.pallet_selected.emit(pallet_id)


class PalletManagerWindow(QDialog):
    data_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.repository = PalletRepository(db)
        self.current_pallet_id: Optional[int] = None
        self.list_dialog: Optional[PalletListDialog] = None

        permissions = user_data.get('permissions', []) or []
        self.can_manage = 'pallets.manage' in permissions or user_data.get('role_code') == 'ADMIN'
        self.can_view = self.can_manage or 'pallets.view' in permissions

        self.setWindowTitle('مدیریت پالت‌ها')
        # حالا که جدول جدا شده، فرم کوچک‌تر و جمع‌وجورتر است
        self.resize(720, 640)
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
        title = QLabel('مدیریت پالت‌ها')
        title.setObjectName('Title')
        subtitle = QLabel('ثبت، ویرایش، حذف و غیرفعالسازی پالت‌ها با اعتبارسنجی کامل')
        subtitle.setObjectName('Muted')
        titles_layout.addWidget(title)
        titles_layout.addWidget(subtitle)
        header_layout.addLayout(titles_layout, 1)

        # دکمه جداگانه برای باز کردن دیتاگرید در پنجره مستقل
        self.show_list_button = QPushButton('📋 نمایش لیست پالت‌ها')
        self.show_list_button.clicked.connect(self.open_list_dialog)
        header_layout.addWidget(self.show_list_button, 0, Qt.AlignTop)

        root.addWidget(header)

        # --- فرم اطلاعات پالت ---
        form_group = QGroupBox('فرم اطلاعات پالت')
        form_layout = QVBoxLayout(form_group)

        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(12)
        info_grid.setVerticalSpacing(12)

        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.material_edit = QLineEdit()

        self.length_spin = QSpinBox(); self.length_spin.setRange(1, 1000000)
        self.length_spin.setRange(1, 100000)
        self.width_spin = QSpinBox(); self.width_spin.setRange(1, 1000000)
        self.width_spin.setRange(1, 100000)
        self.height_spin = QSpinBox(); self.height_spin.setRange(1, 1000000)
        self.height_spin.setRange(1, 100000)
        self.opening_stock_spin = QSpinBox(); self.opening_stock_spin.setRange(0, 1000000)
        self.opening_stock_spin.setRange(0, 100000000)
        self.low_stock_spin = QSpinBox(); self.low_stock_spin.setRange(0, 1000000)
        self.low_stock_spin.setRange(0, 100000000)

        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText('مسیر فایل تصویر پالت')
        browse_button = QPushButton('انتخاب تصویر')
        browse_button.setObjectName('SecondaryButton')
        browse_button.clicked.connect(self._browse_image)

        image_row = QHBoxLayout()
        image_row.addWidget(self.image_path_edit, 1)
        image_row.addWidget(browse_button)

        self.is_active_checkbox = QCheckBox('پالت فعال است')
        self.is_active_checkbox.setChecked(True)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText('توضیحات تکمیلی، عیوب، نوع مصرف و ...')
        self.description_edit.setMinimumHeight(110)

        info_grid.addWidget(QLabel('کد پالت'), 0, 0)
        info_grid.addWidget(self.code_edit, 0, 1)
        info_grid.addWidget(QLabel('نام پالت'), 0, 2)
        info_grid.addWidget(self.name_edit, 0, 3)

        info_grid.addWidget(QLabel('جنس پالت'), 1, 0)
        info_grid.addWidget(self.material_edit, 1, 1)
        info_grid.addWidget(QLabel('موجودی اولیه'), 1, 2)
        info_grid.addWidget(self.opening_stock_spin, 1, 3)

        info_grid.addWidget(QLabel('طول (سانتی‌متر)'), 2, 0)
        info_grid.addWidget(self.length_spin, 2, 1)
        info_grid.addWidget(QLabel('عرض (سانتی‌متر)'), 2, 2)
        info_grid.addWidget(self.width_spin, 2, 3)

        info_grid.addWidget(QLabel('ارتفاع (سانتی‌متر)'), 3, 0)
        info_grid.addWidget(self.height_spin, 3, 1)
        info_grid.addWidget(QLabel('حد هشدار موجودی'), 3, 2)
        info_grid.addWidget(self.low_stock_spin, 3, 3)

        info_grid.addWidget(QLabel('تصویر'), 4, 0)
        info_grid.addLayout(image_row, 4, 1, 1, 3)

        info_grid.addWidget(self.is_active_checkbox, 5, 0, 1, 2)

        self.created_meta_label = QLabel('وضعیت رکورد: جدید')
        self.created_meta_label.setObjectName('Muted')

        form_layout.addLayout(info_grid)
        form_layout.addWidget(QLabel('توضیحات'))
        form_layout.addWidget(self.description_edit)
        form_layout.addWidget(self.created_meta_label)

        # --- دکمه‌های عملیات فرم ---
        form_actions = QHBoxLayout()
        self.new_button = QPushButton('فرم جدید')
        self.new_button.setObjectName('SecondaryButton')
        self.new_button.clicked.connect(self.clear_form)

        self.save_button = QPushButton('ذخیره')
        self.save_button.clicked.connect(self.save_pallet)

        self.delete_button = QPushButton('حذف / غیرفعالسازی')
        self.delete_button.setObjectName('SecondaryButton')
        self.delete_button.clicked.connect(self.delete_pallet)

        form_actions.addWidget(self.new_button)
        form_actions.addStretch()
        form_actions.addWidget(self.delete_button)
        form_actions.addWidget(self.save_button)
        form_layout.addLayout(form_actions)

        root.addWidget(form_group, 1)

    # ------------------------------------------------------------------
    # پنجره لیست پالت‌ها (دیتاگرید جداگانه)
    # ------------------------------------------------------------------
    def open_list_dialog(self) -> None:
        """باز کردن دیتاگرید در یک پنجره مستقل با دکمه جداگانه."""
        if self.list_dialog is None:
            self.list_dialog = PalletListDialog(self.repository, parent=self)
            self.list_dialog.pallet_selected.connect(self._load_pallet_into_form)
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
                self.material_edit,
                self.length_spin,
                self.width_spin,
                self.height_spin,
                self.opening_stock_spin,
                self.low_stock_spin,
                self.image_path_edit,
                self.description_edit,
                self.is_active_checkbox,
                self.save_button,
                self.delete_button,
                self.new_button,
            ]
            for widget in widgets:
                widget.setEnabled(False)
            self.created_meta_label.setText('دسترسی شما فقط مشاهده است.')

    def _browse_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'انتخاب تصویر پالت',
            '',
            'Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp)',
        )
        if file_path:
            self.image_path_edit.setText(file_path)

    def _collect_form_data(self) -> Dict[str, Any]:
        return {
            'code': self.code_edit.text(),
            'name': self.name_edit.text(),
            'material_type': self.material_edit.text(),
            'length_cm': self.length_spin.value(),
            'width_cm': self.width_spin.value(),
            'height_cm': self.height_spin.value(),
            'opening_stock': self.opening_stock_spin.value(),
            'low_stock_threshold': self.low_stock_spin.value(),
            'image_path': self.image_path_edit.text(),
            'description': self.description_edit.toPlainText(),
            'is_active': self.is_active_checkbox.isChecked(),
        }

    def clear_form(self) -> None:
        self.current_pallet_id = None
        self.code_edit.clear()
        self.name_edit.clear()
        self.material_edit.clear()
        self.length_spin.setValue(120)
        self.width_spin.setValue(100)
        self.height_spin.setValue(15)
        self.opening_stock_spin.setValue(0)
        self.low_stock_spin.setValue(0)
        self.image_path_edit.clear()
        self.description_edit.clear()
        self.is_active_checkbox.setChecked(True)
        self.created_meta_label.setText('وضعیت رکورد: جدید')
        if self.list_dialog is not None:
            self.list_dialog.table.clearSelection()
        self.code_edit.setFocus()

    def _load_pallet_into_form(self, pallet_id: int) -> None:
        """بارگذاری اطلاعات پالت انتخاب‌شده از پنجره لیست در فرم."""
        row = self.repository.get_pallet(pallet_id)
        if not row:
            QMessageBox.warning(self, 'خطا', 'پالت موردنظر یافت نشد. لیست را بروزرسانی کنید.')
            return

        self.current_pallet_id = pallet_id
        self.code_edit.setText(row['code'] or '')
        self.name_edit.setText(row['name'] or '')
        self.material_edit.setText(row['material_type'] or '')
        self.length_spin.setValue(int(row['length_cm'] or 1))
        self.width_spin.setValue(int(row['width_cm'] or 1))
        self.height_spin.setValue(int(row['height_cm'] or 1))
        self.opening_stock_spin.setValue(int(row['opening_stock'] or 0))
        self.low_stock_spin.setValue(int(row['low_stock_threshold'] or 0))
        self.image_path_edit.setText(row['image_path'] or '')
        self.description_edit.setPlainText(row['description'] or '')
        self.is_active_checkbox.setChecked(bool(row['is_active']))
        created_j = jalali_date_display_from_iso(str(row['created_at'])[:10]) if row['created_at'] else '-'
        updated_j = jalali_date_display_from_iso(str(row['updated_at'])[:10]) if row['updated_at'] else '-'
        self.created_meta_label.setText(
            f"شناسه: {row['id']} | ایجاد: {created_j} | بروزرسانی: {updated_j}"
        )
        
        # فرم را جلو بیاور تا کاربر بلافاصله ویرایش کند
        self.raise_()
        self.activateWindow()

    def save_pallet(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه ثبت یا ویرایش در این بخش را ندارید.')
            return

        payload = self._collect_form_data()
        try:
            if self.current_pallet_id is None:
                saved = self.repository.create_pallet(payload, user_id=self.user_data.get('id'))
                message = f"پالت «{saved.get('name', '')}» با موفقیت ثبت شد."
            else:
                saved = self.repository.update_pallet(
                    self.current_pallet_id,
                    payload,
                    user_id=self.user_data.get('id'),
                )
                message = f"پالت «{saved.get('name', '')}» با موفقیت بروزرسانی شد."
        except ValidationError as exc:
            QMessageBox.warning(self, 'اعتبارسنجی', str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'خطا', f'ذخیره اطلاعات با خطا مواجه شد:\n{exc}')
            return

        QMessageBox.information(self, 'ذخیره موفق', message)
        self._refresh_list_if_open(select_id=int(saved['id']))
        self.data_changed.emit()

    def delete_pallet(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه حذف یا غیرفعالسازی در این بخش را ندارید.')
            return
        if self.current_pallet_id is None:
            QMessageBox.information(
                self,
                'حذف پالت',
                'ابتدا یک پالت را از پنجره «لیست پالت‌ها» انتخاب کنید.',
            )
            return

        answer = QMessageBox.question(
            self,
            'تأیید حذف',
            'آیا از حذف این پالت مطمئن هستید؟\nاگر به اسناد دیگر متصل باشد، به جای حذف، غیرفعال می‌شود.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            action_result, record = self.repository.delete_pallet(
                self.current_pallet_id,
                user_id=self.user_data.get('id'),
            )
        except ValidationError as exc:
            QMessageBox.warning(self, 'حذف پالت', str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'خطا', f'حذف اطلاعات با خطا مواجه شد:\n{exc}')
            return

        if action_result == 'deleted':
            QMessageBox.information(self, 'حذف شد', f"پالت «{record.get('name', '')}» حذف شد.")
        else:
            QMessageBox.information(
                self,
                'غیرفعال شد',
                f"پالت «{record.get('name', '')}» به اسناد دیگر متصل بود و به‌صورت امن غیرفعال شد.",
            )

        self.clear_form()
        self._refresh_list_if_open()
        self.data_changed.emit()
