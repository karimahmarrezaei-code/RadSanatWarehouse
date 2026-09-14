# -*- coding: utf-8 -*-
"""مدیریت اشخاص - نسخه نهایی یکپارچه
ظاهر مدرن دوستونه + کمبوباکس نام بانک + فرمت خودکار شماره کارت + خروجی PDF حساب‌ها
"""

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCompleter,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.database import DatabaseManager
from app.core.locations import get_cities_by_province, get_provinces
from app.core.banks import get_bank_names
from app.core.validators import (
    PERSON_ROLE_TYPES,
    VEHICLE_TYPES,
    ValidationError,
    validate_bank_account_payload,
)
from app.repositories.person_repository import PersonRepository
from app.ui.plate_widget import PlateWidget, format_plate, parse_plate
from app.services.report_export_service import export_person_bank_accounts_to_pdf

ROLE_LABELS = {
    'CUSTOMER': 'مشتری',
    'SUPPLIER': 'تأمین‌کننده',
    'DRIVER': 'راننده',
}

ROLE_FILTER_OPTIONS = [
    ('همه نقش‌ها', 'ALL'),
    ('فقط مشتری', 'CUSTOMER'),
    ('فقط تأمین‌کننده', 'SUPPLIER'),
    ('فقط راننده', 'DRIVER'),
]


# ================================================================
# 🎨 استایل مرکزی
# ================================================================
GLOBAL_STYLE = """"""


def _colored_button(text: str, color: Optional[str] = None) -> QPushButton:
    btn = QPushButton(text)
    if color:
        btn.setProperty('color', color)
    return btn


# ================================================================
# 📋 پنجره لیست اشخاص
# ================================================================
class PersonListDialog(QDialog):
    """پنجره مستقل نمایش لیست اشخاص با جستجو و فیلترها."""

    person_selected = pyqtSignal(int)

    def __init__(self, repository: PersonRepository, parent=None) -> None:
        super().__init__(parent)
        self.repository = repository
        self.setWindowTitle('لیست اشخاص')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1120, 660)
        self.setModal(False)
        if False: pass
        self._build_ui()
        self.refresh_table()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # هدر
        header = QFrame()
        header.setObjectName('HeaderCard')
        header.setMaximumHeight(64)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(16, 8, 16, 8)
        t = QLabel('📋  لیست اشخاص')
        t.setObjectName('HeaderTitle')
        s = QLabel('جستجو، فیلتر و انتخاب شخص برای ویرایش')
        s.setObjectName('HeaderSubtitle')
        hl.addWidget(t)
        hl.addWidget(s)
        root.addWidget(header)

        # نوار ابزار
        toolbar_card = QFrame()
        toolbar_card.setObjectName('FilterBar')
        toolbar = QHBoxLayout(toolbar_card)
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('🔍 جستجو بر اساس نام، موبایل، کد ملی، ایمیل، استان یا شهر...')
        self.search_edit.textChanged.connect(self.refresh_table)

        self.role_filter_combo = QComboBox()
        for label, value in ROLE_FILTER_OPTIONS:
            self.role_filter_combo.addItem(label, value)
        self.role_filter_combo.currentIndexChanged.connect(self.refresh_table)

        self.active_filter_combo = QComboBox()
        self.active_filter_combo.addItem('همه وضعیت‌ها', 'ALL')
        self.active_filter_combo.addItem('فقط فعال', 'ACTIVE')
        self.active_filter_combo.addItem('فقط غیرفعال', 'INACTIVE')
        self.active_filter_combo.currentIndexChanged.connect(self.refresh_table)

        
        refresh_button = _colored_button('🔄 بروزرسانی')
        refresh_button.clicked.connect(self.refresh_table)

        # ✅ دکمه خروجی اکسل
        export_button = _colored_button('📊 خروجی اکسل', 'success')
        export_button.clicked.connect(self._export_to_excel)

        toolbar.addWidget(self.search_edit, 1)
        toolbar.addWidget(QLabel('نقش:'))
        toolbar.addWidget(self.role_filter_combo)
        toolbar.addWidget(QLabel('وضعیت:'))
        toolbar.addWidget(self.active_filter_combo)
        toolbar.addWidget(refresh_button)
        root.addWidget(toolbar_card)

        # جدول
        table_group = QGroupBox('👥  لیست اشخاص')
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            'شناسه', 'نام و نام خانوادگی', 'نقش‌ها', 'کد ملی',
            'موبایل', 'ایمیل', 'استان / شهر', 'آدرس', 'توضیحات', 'وضعیت',
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        # [ID] ستون شناسه (ID) نمایان شد تا کاربر دقیق انتخاب کند
        self.table.setColumnWidth(0, 70)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.itemDoubleClicked.connect(self._emit_selected)
        table_layout.addWidget(self.table)
        root.addWidget(table_group, 1)

        # دکمه‌های پایین
        buttons_row = QHBoxLayout()
        hint = QLabel('💡 برای ویرایش، روی ردیف دابل‌کلیک کنید یا دکمه «انتخاب و ویرایش» را بزنید.')
        hint.setStyleSheet('color: #64748b; font-size: 11px;')
        buttons_row.addWidget(hint)
        buttons_row.addStretch()

        self.select_button = _colored_button('✏️ انتخاب و ویرایش', 'primary')
        self.select_button.clicked.connect(self._emit_selected)

        close_button = _colored_button('بستن')
        close_button.clicked.connect(self.close)

        buttons_row.addWidget(self.select_button)
        buttons_row.addWidget(close_button)
        root.addLayout(buttons_row)

    def refresh_table(self) -> None:
        rows = self.repository.list_persons(
            search_text=self.search_edit.text(),
            role_filter=self.role_filter_combo.currentData(),
            active_filter=self.active_filter_combo.currentData(),
        )
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            full_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
            roles_text = '، '.join(ROLE_LABELS.get(role, role) for role in row.get('roles', []))
            location_text = ' / '.join(
                part for part in [row.get('province_name'), row.get('city_name')] if part
            ) or '-'
            status_text = 'فعال' if row.get('is_active') else 'غیرفعال'
            values = [
                str(row.get('id')),
                full_name,
                roles_text,
                row.get('national_id') or '-',
                row.get('mobile') or '-',
                row.get('email') or '-',
                location_text,
                row.get('address') or '-',
                row.get('notes') or '-',
                status_text,
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_index, column_index, item)
        self.table.resizeColumnsToContents()

    
    # ✅ متد جدید: خروجی اکسل با تمام ستون‌ها
    def _export_to_excel(self) -> None:
        """خروجی اکسل با تمام ستون‌ها شامل آدرس و توضیحات"""
        from datetime import datetime
        path, _ = QFileDialog.getSaveFileName(
            self, 'خروجی اکسل', 
            f'اشخاص_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xml',
            'Excel XML (*.xml)'
        )
        if not path:
            return
        if not path.lower().endswith('.xml'):
            path += '.xml'
        
        def esc(v):
            return str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # ✅ هدر شامل تمام ۱۰ ستون
        hdr = ['شناسه', 'نام و نام خانوادگی', 'نقش‌ها', 'کد ملی', 'موبایل', 
               'ایمیل', 'استان / شهر', 'آدرس', 'توضیحات', 'وضعیت']
        
        xml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?mso-application progid="Excel.Sheet"?>',
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
            '<Worksheet ss:Name="اشخاص"><Table>'
        ]
        xml.append('<Row>' + ''.join(f'<Cell><Data ss:Type="String">{esc(h)}</Data></Cell>' for h in hdr) + '</Row>')
        
        # ✅ اضافه کردن تمام ردیف‌ها با تمام ستون‌ها
        for i in range(self.table.rowCount()):
            row_data = []
            for c in range(len(hdr)):
                item = self.table.item(i, c)
                row_data.append(item.text() if item else "")
            xml.append('<Row>' + ''.join(f'<Cell><Data ss:Type="String">{esc(v)}</Data></Cell>' for v in row_data) + '</Row>')
        
        xml.append('</Table></Worksheet></Workbook>')
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(''.join(xml))
            QMessageBox.information(self, 'موفق', f'فایل با موفقیت ذخیره شد:\n{path}')
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ذخیره:\n{e}')

    def select_row_by_id(self, person_id: int) -> None:
        for row_index in range(self.table.rowCount()):
            item = self.table.item(row_index, 0)
            if item and int(item.text()) == person_id:
                self.table.selectRow(row_index)
                break

    def _emit_selected(self, *args) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, 'انتخاب شخص', 'ابتدا یک ردیف را از جدول انتخاب کنید.')
            return
        person_id = int(self.table.item(selected_items[0].row(), 0).text())
        self.person_selected.emit(person_id)


# ================================================================
# 🧑 فرم مدیریت اشخاص
# ================================================================
class PersonManagerWindow(QDialog):
    data_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.repository = PersonRepository(db)
        self.current_person_id: Optional[int] = None
        self.current_bank_index: Optional[int] = None
        self.bank_accounts: List[Dict[str, Any]] = []
        self.list_dialog: Optional[PersonListDialog] = None

        permissions = set(user_data.get('permissions', []) or [])
        self.can_manage = 'persons.manage' in permissions or user_data.get('role_code') == 'ADMIN'
        self.can_view = self.can_manage or 'persons.view' in permissions

        self.setWindowTitle('مدیریت اشخاص')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(940, 820)
        self.setMinimumSize(860, 680)
        pass

        self._build_ui()
        self._load_provinces()
        self.clear_form()
        self._apply_permissions()

    # ------------------------------------------------------------------
    # ساخت رابط
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # هدر
        header = QFrame()
        header.setObjectName('HeaderCard')
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)

        titles_layout = QVBoxLayout()
        title = QLabel('👥  مدیریت اشخاص')
        title.setObjectName('HeaderTitle')
        subtitle = QLabel('ثبت مشتری، تأمین‌کننده و راننده با پشتیبانی از چند نقش، استان/شهر و حساب‌های بانکی')
        subtitle.setObjectName('HeaderSubtitle')
        titles_layout.addWidget(title)
        titles_layout.addWidget(subtitle)
        header_layout.addLayout(titles_layout, 1)

        self.show_list_button = _colored_button('📋 نمایش لیست اشخاص', 'primary')
        self.show_list_button.clicked.connect(self.open_list_dialog)
        header_layout.addWidget(self.show_list_button, 0, Qt.AlignTop)
        root.addWidget(header)

        # تب‌ها
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_person_tab(), '🧑  اطلاعات شخص')
        self.tabs.addTab(self._build_bank_tab(), '🏦  حساب‌های بانکی')
        root.addWidget(self.tabs, 1)

        # نوار وضعیت و عملیات
        action_bar = QFrame()
        action_bar.setObjectName('ActionBar')
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(12, 8, 12, 8)
        ab_layout.setSpacing(10)

        self.meta_label = QLabel('وضعیت رکورد: جدید')
        self.meta_label.setObjectName('MetaBadge')
        ab_layout.addWidget(self.meta_label, 1)

        self.delete_button = _colored_button('🗑 حذف / غیرفعالسازی', 'danger')
        self.delete_button.clicked.connect(self.delete_person)

        self.new_button = _colored_button('➕ فرم جدید', 'primary')
        self.new_button.clicked.connect(self.clear_form)

        self.save_button = _colored_button('💾 ذخیره', 'success')
        self.save_button.clicked.connect(self.save_person)
        self.save_button.setMinimumWidth(120)

        ab_layout.addWidget(self.delete_button)
        ab_layout.addWidget(self.new_button)
        ab_layout.addWidget(self.save_button)
        root.addWidget(action_bar)

    # ------------------------------------------------------------------
    # تب اطلاعات شخص (چیدمان دوستونه)
    # ------------------------------------------------------------------
    def _build_person_tab(self) -> QWidget:
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(8, 8, 8, 8)
        form_layout.setSpacing(10)

        # --- اطلاعات هویتی: دوستونه ---
        info_group = QGroupBox('🪪  اطلاعات هویتی و تماس')
        info_grid = QGridLayout(info_group)
        info_grid.setHorizontalSpacing(12)
        info_grid.setVerticalSpacing(10)
        info_grid.setColumnStretch(1, 1)
        info_grid.setColumnStretch(3, 1)

        self.first_name_edit = QLineEdit()
        self.last_name_edit = QLineEdit()
        self.national_id_edit = QLineEdit()
        self.mobile_edit = QLineEdit()
        self.email_edit = QLineEdit()

        self.province_combo = QComboBox()
        self.province_combo.setEditable(True)
        self.province_combo.setInsertPolicy(QComboBox.NoInsert)
        self.province_combo.currentIndexChanged.connect(self._province_changed)
        self.city_combo = QComboBox()
        self.city_combo.setEditable(True)
        self.city_combo.setInsertPolicy(QComboBox.NoInsert)

        self.is_active_checkbox = QCheckBox('شخص فعال است')
        self.is_active_checkbox.setChecked(True)

        info_grid.addWidget(QLabel('نام'), 0, 0)
        info_grid.addWidget(self.first_name_edit, 0, 1)
        info_grid.addWidget(QLabel('نام خانوادگی'), 0, 2)
        info_grid.addWidget(self.last_name_edit, 0, 3)

        info_grid.addWidget(QLabel('کد ملی'), 1, 0)
        info_grid.addWidget(self.national_id_edit, 1, 1)
        info_grid.addWidget(QLabel('شماره موبایل'), 1, 2)
        info_grid.addWidget(self.mobile_edit, 1, 3)

        info_grid.addWidget(QLabel('ایمیل'), 2, 0)
        info_grid.addWidget(self.email_edit, 2, 1)
        info_grid.addWidget(self.is_active_checkbox, 2, 3, Qt.AlignRight)

        info_grid.addWidget(QLabel('استان'), 3, 0)
        info_grid.addWidget(self.province_combo, 3, 1)
        info_grid.addWidget(QLabel('شهر'), 3, 2)
        info_grid.addWidget(self.city_combo, 3, 3)

        form_layout.addWidget(info_group)

        # --- نقش‌ها: کارت‌های کلیکی ---
        roles_group = QGroupBox('🎭  نقش‌های شخص')
        roles_layout = QHBoxLayout(roles_group)
        roles_layout.setSpacing(12)

        self.customer_checkbox = QCheckBox('🛒  مشتری')
        self.supplier_checkbox = QCheckBox('📦  تأمین‌کننده')
        self.driver_checkbox = QCheckBox('🚛  راننده')
        self.driver_checkbox.toggled.connect(self._toggle_driver_fields)

        for cb in (self.customer_checkbox, self.supplier_checkbox, self.driver_checkbox):
            roles_layout.addWidget(self._make_role_card(cb))
        roles_layout.addStretch()
        form_layout.addWidget(roles_group)

        # --- اطلاعات راننده (نمایش شرطی) ---
        driver_group = QGroupBox('🚗  اطلاعات راننده و خودرو')
        driver_grid = QGridLayout(driver_group)
        driver_grid.setHorizontalSpacing(12)
        driver_grid.setVerticalSpacing(10)
        driver_grid.setColumnStretch(1, 1)
        driver_grid.setColumnStretch(3, 1)

        self.vehicle_type_combo = QComboBox()
        self.vehicle_type_combo.addItem('انتخاب کنید', '')
        for item in VEHICLE_TYPES:
            self.vehicle_type_combo.addItem(item, item)
        self.vehicle_plate_edit = QLineEdit()
        self.driver_notes_edit = QTextEdit()
        self.driver_notes_edit.setMinimumHeight(64)
        self.driver_notes_edit.setMaximumHeight(90)

        driver_grid.addWidget(QLabel('نوع وسیله نقلیه'), 0, 0)
        driver_grid.addWidget(self.vehicle_type_combo, 0, 1)
        driver_grid.addWidget(QLabel('شماره پلاک'), 0, 2)
        driver_grid.addWidget(self.vehicle_plate_edit, 0, 3)
        # --- ورودی ساخت‌یافته پلاک + پیش‌نمایش (ترتیب صحیح) ---
        self.plate_two_edit = QLineEdit(); self.plate_two_edit.setMaxLength(2); self.plate_two_edit.setPlaceholderText('۲ رقم')
        self.plate_letter_edit = QLineEdit(); self.plate_letter_edit.setMaxLength(1); self.plate_letter_edit.setPlaceholderText('حرف')
        self.plate_three_edit = QLineEdit(); self.plate_three_edit.setMaxLength(3); self.plate_three_edit.setPlaceholderText('۳ رقم')
        self.plate_iran_edit = QLineEdit(); self.plate_iran_edit.setMaxLength(2); self.plate_iran_edit.setPlaceholderText('ایران')
        self.plate_preview = PlateWidget()
        for _pe in (self.plate_two_edit, self.plate_letter_edit, self.plate_three_edit, self.plate_iran_edit):
            _pe.textChanged.connect(self._on_plate_changed)
        plate_box = QGroupBox('ورود ساخت‌یافته پلاک (چپ‌به‌راست: ۲ رقم | حرف | ۳ رقم | ایران)')
        pb_l = QHBoxLayout(plate_box)
        pb_l.addWidget(QLabel('۲ رقم (چپ)')); pb_l.addWidget(self.plate_two_edit)
        pb_l.addWidget(QLabel('حرف فارسی')); pb_l.addWidget(self.plate_letter_edit)
        pb_l.addWidget(QLabel('۳ رقم')); pb_l.addWidget(self.plate_three_edit)
        pb_l.addWidget(QLabel('کد ایران')); pb_l.addWidget(self.plate_iran_edit)
        driver_grid.addWidget(plate_box, 2, 0, 1, 4)
        driver_grid.addWidget(self.plate_preview, 3, 0, 1, 4)
        driver_grid.addWidget(QLabel('توضیحات راننده'), 1, 0)
        driver_grid.addWidget(self.driver_notes_edit, 1, 1, 1, 3)

        form_layout.addWidget(driver_group)
        self.driver_group = driver_group
        self.driver_group.setVisible(False)

        # --- آدرس و توضیحات: دوستونه کنار هم ---
        location_group = QGroupBox('📍  آدرس و توضیحات')
        location_grid = QGridLayout(location_group)
        location_grid.setHorizontalSpacing(12)
        location_grid.setVerticalSpacing(6)
        location_grid.setColumnStretch(0, 1)
        location_grid.setColumnStretch(1, 1)

        self.address_edit = QTextEdit()
        self.address_edit.setMinimumHeight(70)
        self.address_edit.setMaximumHeight(110)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(70)
        self.notes_edit.setMaximumHeight(110)

        location_grid.addWidget(QLabel('آدرس محل سکونت'), 0, 0)
        location_grid.addWidget(QLabel('توضیحات'), 0, 1)
        location_grid.addWidget(self.address_edit, 1, 0)
        location_grid.addWidget(self.notes_edit, 1, 1)

        form_layout.addWidget(location_group)
        form_layout.addStretch()

        scroll.setWidget(container)
        tab_layout.addWidget(scroll)
        return tab

    # ------------------------------------------------------------------
    # تب حساب‌های بانکی (دوستونه + کمبوباکس بانک + فرمت کارت)
    # ------------------------------------------------------------------
    def _build_bank_tab(self) -> QWidget:
        tab = QWidget()
        bank_layout = QVBoxLayout(tab)
        bank_layout.setContentsMargins(8, 8, 8, 8)
        bank_layout.setSpacing(10)

        bank_group = QGroupBox('🏦  تعریف حساب بانکی')
        bank_form = QGridLayout(bank_group)
        bank_form.setHorizontalSpacing(12)
        bank_form.setVerticalSpacing(10)
        bank_form.setColumnStretch(1, 1)
        bank_form.setColumnStretch(3, 1)

        # کمبوباکس نام بانک (قابل تایپ دستی)
        self.bank_name_edit = QComboBox()
        self.bank_name_edit.setEditable(True)
        self.bank_name_edit.setInsertPolicy(QComboBox.NoInsert)
        self.bank_name_edit.addItems(get_bank_names())
        self.bank_name_edit.setCurrentText('')
        if self.bank_name_edit.lineEdit() is not None:
            self.bank_name_edit.lineEdit().setPlaceholderText('انتخاب از لیست یا تایپ نام بانک...')

        self.account_number_edit = QLineEdit()
        self.iban_edit = QLineEdit()

        # شماره کارت با فرمت خودکار
        self.card_number_edit = QLineEdit()
        self.card_number_edit.setPlaceholderText('مثال: 6037-9975-0000-0000')
        self.card_number_edit.textChanged.connect(self._on_card_text_changed)

        self.branch_name_edit = QLineEdit()
        self.branch_code_edit = QLineEdit()
        self.bank_default_checkbox = QCheckBox('حساب پیش‌فرض')

        bank_form.addWidget(QLabel('نام بانک'), 0, 0)
        bank_form.addWidget(self.bank_name_edit, 0, 1)
        bank_form.addWidget(QLabel('شماره حساب'), 0, 2)
        bank_form.addWidget(self.account_number_edit, 0, 3)

        bank_form.addWidget(QLabel('شماره شبا'), 1, 0)
        bank_form.addWidget(self.iban_edit, 1, 1)
        bank_form.addWidget(QLabel('شماره کارت'), 1, 2)
        bank_form.addWidget(self.card_number_edit, 1, 3)

        bank_form.addWidget(QLabel('نام شعبه'), 2, 0)
        bank_form.addWidget(self.branch_name_edit, 2, 1)
        bank_form.addWidget(QLabel('کد شعبه'), 2, 2)
        bank_form.addWidget(self.branch_code_edit, 2, 3)

        bank_form.addWidget(self.bank_default_checkbox, 3, 1, 1, 3, Qt.AlignRight)
        bank_layout.addWidget(bank_group)

        # دکمه‌های عملیات حساب
        bank_actions_frame = QFrame()
        bank_actions_frame.setObjectName('FilterBar')
        bank_actions = QHBoxLayout(bank_actions_frame)
        bank_actions.setContentsMargins(10, 8, 10, 8)

        self.bank_add_button = _colored_button('➕ افزودن / بروزرسانی حساب', 'success')
        self.bank_add_button.clicked.connect(self._add_or_update_bank_account)
        self.bank_remove_button = _colored_button('🗑 حذف حساب انتخابی', 'danger')
        self.bank_remove_button.clicked.connect(self._remove_selected_bank_account)
        self.bank_clear_button = _colored_button('🧹 پاک کردن فرم حساب')
        self.bank_clear_button.clicked.connect(self._clear_bank_form)
        self.bank_pdf_button = _colored_button('📕 خروجی PDF حساب‌ها', 'danger')
        self.bank_pdf_button.clicked.connect(self._export_bank_accounts_pdf)

        bank_actions.addWidget(self.bank_add_button)
        bank_actions.addWidget(self.bank_remove_button)
        bank_actions.addWidget(self.bank_clear_button)
        bank_actions.addWidget(self.bank_pdf_button)
        bank_actions.addStretch()
        bank_layout.addWidget(bank_actions_frame)

        # جدول حساب‌ها
        accounts_group = QGroupBox('📋  حساب‌های ثبت‌شده این شخص')
        accounts_layout = QVBoxLayout(accounts_group)
        self.bank_table = QTableWidget(0, 5)
        self.bank_table.setHorizontalHeaderLabels(['ردیف', 'بانک', 'شماره حساب', 'شماره کارت', 'پیش‌فرض'])
        self.bank_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.bank_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.bank_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.bank_table.verticalHeader().setVisible(False)
        self.bank_table.setAlternatingRowColors(True)
        self.bank_table.itemSelectionChanged.connect(self._load_selected_bank_account)
        self.bank_table.horizontalHeader().setStretchLastSection(True)
        accounts_layout.addWidget(self.bank_table)
        bank_layout.addWidget(accounts_group, 1)

        return tab

    # ------------------------------------------------------------------
    # کارت نقش
    # ------------------------------------------------------------------
    def _make_role_card(self, checkbox: QCheckBox) -> QFrame:
        card = QFrame()
        card.setObjectName('RoleCard')
        card.setProperty('checked', False)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.addWidget(checkbox)
        checkbox.toggled.connect(lambda checked, c=card: self._refresh_role_card(c, checked))
        return card

    @staticmethod
    def _refresh_role_card(card: QFrame, checked: bool) -> None:
        card.setProperty('checked', checked)
        card.style().unpolish(card)
        card.style().polish(card)

    # ------------------------------------------------------------------
    # پنجره لیست اشخاص
    # ------------------------------------------------------------------
    def open_list_dialog(self) -> None:
        if self.list_dialog is None:
            self.list_dialog = PersonListDialog(self.repository, parent=self)
            self.list_dialog.person_selected.connect(self._load_person_into_form)
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
    # دسترسی‌ها
    # ------------------------------------------------------------------
    def _apply_permissions(self) -> None:
        if not self.can_view:
            QMessageBox.critical(self, 'عدم دسترسی', 'شما اجازه مشاهده این بخش را ندارید.')
            self.setEnabled(False)
            return
        if not self.can_manage:
            widgets = [
                self.first_name_edit, self.last_name_edit, self.national_id_edit,
                self.mobile_edit, self.email_edit, self.province_combo, self.city_combo,
                self.address_edit, self.notes_edit,
                self.customer_checkbox, self.supplier_checkbox, self.driver_checkbox,
                self.vehicle_type_combo, self.vehicle_plate_edit, self.driver_notes_edit,
                self.is_active_checkbox,
                self.bank_name_edit, self.account_number_edit, self.iban_edit,
                self.card_number_edit, self.branch_name_edit, self.branch_code_edit,
                self.bank_default_checkbox,
                self.bank_add_button, self.bank_remove_button, self.bank_clear_button,
                self.bank_pdf_button,
                self.new_button, self.save_button, self.delete_button,
            ]
            for widget in widgets:
                widget.setEnabled(False)
            self.meta_label.setText('🔒 دسترسی شما فقط مشاهده است.')

    # ------------------------------------------------------------------
    # استان / شهر
    # ------------------------------------------------------------------
    def _load_provinces(self) -> None:
        self.province_combo.blockSignals(True)
        self.province_combo.clear()
        self.province_combo.addItem('انتخاب کنید', None)
        for province in get_provinces():
            self.province_combo.addItem(province.get('name', ''), province.get('id'))
        self.province_combo.blockSignals(False)
        self._fill_cities(None)

    def _province_changed(self) -> None:
        self._fill_cities(self.province_combo.currentData())

    def _fill_cities(self, province_id: Optional[int], selected_city_code: Optional[int] = None) -> None:
        self.city_combo.blockSignals(True)
        self.city_combo.clear()
        self.city_combo.addItem('انتخاب کنید', None)
        if province_id:
            for city in get_cities_by_province(int(province_id)):
                self.city_combo.addItem(city.get('name', ''), city.get('id'))
            if selected_city_code is not None:
                for index in range(self.city_combo.count()):
                    if self.city_combo.itemData(index) == selected_city_code:
                        self.city_combo.setCurrentIndex(index)
                        break
        self.city_combo.blockSignals(False)

    def _toggle_driver_fields(self, checked: bool) -> None:
        self.driver_group.setVisible(checked)
        self.driver_group.setEnabled(checked and self.can_manage)
        if not checked:
            self.vehicle_type_combo.setCurrentIndex(0)
            self.vehicle_plate_edit.clear()
            self.driver_notes_edit.clear()

    # ------------------------------------------------------------------
    # جمع‌آوری و پاک‌سازی فرم
    # ------------------------------------------------------------------
    def _on_plate_changed(self, *_args):
        two = self.plate_two_edit.text().strip()
        letter = self.plate_letter_edit.text().strip()
        three = self.plate_three_edit.text().strip()
        iran = self.plate_iran_edit.text().strip()
        canonical = format_plate(two, letter, three, iran)
        self.vehicle_plate_edit.blockSignals(True)
        self.vehicle_plate_edit.setText(canonical)
        self.vehicle_plate_edit.blockSignals(False)
        self.plate_preview.set_plate(two, letter, three, iran)

    def _current_roles(self) -> List[str]:
        roles: List[str] = []
        if self.customer_checkbox.isChecked():
            roles.append('CUSTOMER')
        if self.supplier_checkbox.isChecked():
            roles.append('SUPPLIER')
        if self.driver_checkbox.isChecked():
            roles.append('DRIVER')
        return roles

    def _collect_form_data(self) -> Dict[str, Any]:
        province_index = self.province_combo.currentIndex()
        city_index = self.city_combo.currentIndex()
        return {
            'first_name': self.first_name_edit.text(),
            'last_name': self.last_name_edit.text(),
            'national_id': self.national_id_edit.text(),
            'mobile': self.mobile_edit.text(),
            'email': self.email_edit.text(),
            'province_code': self.province_combo.itemData(province_index),
            'province_name': self.province_combo.currentText() if province_index > 0 else None,
            'city_code': self.city_combo.itemData(city_index),
            'city_name': self.city_combo.currentText() if city_index > 0 else None,
            'address': self.address_edit.toPlainText(),
            'notes': self.notes_edit.toPlainText(),
            'is_active': self.is_active_checkbox.isChecked(),
            'roles': self._current_roles(),
            'driver_profile': {
                'vehicle_type': self.vehicle_type_combo.currentData(),
                'vehicle_plate': self.vehicle_plate_edit.text(),
                'notes': self.driver_notes_edit.toPlainText(),
            },
            'bank_accounts': list(self.bank_accounts),
        }

    def clear_form(self) -> None:
        self.current_person_id = None
        self.first_name_edit.clear()
        self.last_name_edit.clear()
        self.national_id_edit.clear()
        self.mobile_edit.clear()
        self.email_edit.clear()
        self.province_combo.setCurrentIndex(0)
        self._fill_cities(None)
        self.address_edit.clear()
        self.notes_edit.clear()
        self.customer_checkbox.setChecked(False)
        self.supplier_checkbox.setChecked(False)
        self.driver_checkbox.setChecked(False)
        self.driver_group.setVisible(False)
        self.is_active_checkbox.setChecked(True)
        self.bank_accounts = []
        self._render_bank_accounts()
        self._clear_bank_form()
        self.meta_label.setText('وضعیت رکورد: جدید')
        if self.list_dialog is not None:
            self.list_dialog.table.clearSelection()
        self.tabs.setCurrentIndex(0)
        self.first_name_edit.setFocus()

    # ------------------------------------------------------------------
    # بارگذاری شخص در فرم
    # ------------------------------------------------------------------
    def _load_person_into_form(self, person_id: int) -> None:
        row = self.repository.get_person(person_id)
        if not row:
            QMessageBox.warning(self, 'خطا', 'شخص موردنظر یافت نشد. لیست را بروزرسانی کنید.')
            return

        self.current_person_id = person_id
        self.first_name_edit.setText(row.get('first_name') or '')
        self.last_name_edit.setText(row.get('last_name') or '')
        self.national_id_edit.setText(row.get('national_id') or '')
        self.mobile_edit.setText(row.get('mobile') or '')
        self.email_edit.setText(row.get('email') or '')
        self._select_combo_by_data(self.province_combo, row.get('province_code'))
        self._fill_cities(row.get('province_code'), row.get('city_code'))
        self.address_edit.setPlainText(row.get('address') or '')
        self.notes_edit.setPlainText(row.get('notes') or '')
        self.is_active_checkbox.setChecked(bool(row.get('is_active')))

        roles = set(row.get('roles') or [])
        self.customer_checkbox.setChecked('CUSTOMER' in roles)
        self.supplier_checkbox.setChecked('SUPPLIER' in roles)
        self.driver_checkbox.setChecked('DRIVER' in roles)

        driver_profile = row.get('driver_profile') or {}
        self._select_combo_by_data(self.vehicle_type_combo, driver_profile.get('vehicle_type'))
        self.vehicle_plate_edit.setText(driver_profile.get('vehicle_plate') or '')
        _p_two, _p_letter, _p_three, _p_iran = parse_plate(driver_profile.get('vehicle_plate'))
        self.plate_two_edit.setText(_p_two)
        self.plate_letter_edit.setText(_p_letter)
        self.plate_three_edit.setText(_p_three)
        self.plate_iran_edit.setText(_p_iran)
        self.plate_preview.set_plate(_p_two, _p_letter, _p_three, _p_iran)
        self.driver_notes_edit.setPlainText(driver_profile.get('notes') or '')
        self.driver_group.setVisible(self.driver_checkbox.isChecked())
        self.driver_group.setEnabled(self.driver_checkbox.isChecked() and self.can_manage)

        self.bank_accounts = []
        for bank in row.get('bank_accounts') or []:
            self.bank_accounts.append(
                {
                    'bank_name': bank.get('bank_name') or '',
                    'account_number': bank.get('account_number') or '',
                    'iban': bank.get('iban') or '',
                    'card_number': bank.get('card_number') or '',
                    'branch_name': bank.get('branch_name') or '',
                    'branch_code': bank.get('branch_code') or '',
                    'is_default': 1 if bank.get('is_default') else 0,
                }
            )
        self._render_bank_accounts()
        self._clear_bank_form()
        self.meta_label.setText(
            f"🆔 شناسه: {row.get('id')}   |   ایجاد: {row.get('created_at') or '-'}   |   بروزرسانی: {row.get('updated_at') or '-'}"
        )
        self.tabs.setCurrentIndex(0)
        self.raise_()
        self.activateWindow()

    # ------------------------------------------------------------------
    # ذخیره / حذف
    # ------------------------------------------------------------------
    def save_person(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه ثبت یا ویرایش در این بخش را ندارید.')
            return
        payload = self._collect_form_data()
        try:
            if self.current_person_id is None:
                saved = self.repository.create_person(payload, user_id=self.user_data.get('id'))
                message = f"شخص «{saved.get('first_name', '')} {saved.get('last_name', '')}» با موفقیت ثبت شد."
            else:
                saved = self.repository.update_person(self.current_person_id, payload, user_id=self.user_data.get('id'))
                message = f"اطلاعات «{saved.get('first_name', '')} {saved.get('last_name', '')}» با موفقیت بروزرسانی شد."
        except ValidationError as exc:
            QMessageBox.warning(self, 'اعتبارسنجی', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'ذخیره اطلاعات با خطا مواجه شد:\n{exc}')
            return

        QMessageBox.information(self, 'ذخیره موفق', message)
        self._refresh_list_if_open(select_id=int(saved['id']))
        self.data_changed.emit()

    def delete_person(self) -> None:
        if not self.can_manage:
            QMessageBox.warning(self, 'عدم دسترسی', 'شما اجازه حذف یا غیرفعالسازی در این بخش را ندارید.')
            return
        if self.current_person_id is None:
            QMessageBox.information(
                self, 'حذف شخص',
                'ابتدا یک شخص را از پنجره «لیست اشخاص» انتخاب کنید.',
            )
            return

        answer = QMessageBox.question(
            self, 'تأیید حذف',
            'آیا از حذف این شخص مطمئن هستید؟\nاگر در اسناد عملیاتی/مالی استفاده شده باشد، غیرفعال می‌شود.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            action_result, record = self.repository.delete_person(
                self.current_person_id, user_id=self.user_data.get('id')
            )
        except ValidationError as exc:
            QMessageBox.warning(self, 'حذف شخص', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'حذف اطلاعات با خطا مواجه شد:\n{exc}')
            return

        full_name = f"{record.get('first_name', '')} {record.get('last_name', '')}".strip()
        if action_result == 'deleted':
            QMessageBox.information(self, 'حذف شد', f'شخص «{full_name}» حذف شد.')
        else:
            QMessageBox.information(self, 'غیرفعال شد', f'شخص «{full_name}» به‌صورت امن غیرفعال شد.')
        self.clear_form()
        self._refresh_list_if_open()
        self.data_changed.emit()

    # ------------------------------------------------------------------
    # مدیریت حساب‌های بانکی
    # ------------------------------------------------------------------
    def _add_or_update_bank_account(self) -> None:
        if not self.can_manage:
            return
        raw = {
            'bank_name': self.bank_name_edit.currentText(),
            'account_number': self.account_number_edit.text(),
            'iban': self.iban_edit.text(),
            'card_number': self.card_number_edit.text(),
            'branch_name': self.branch_name_edit.text(),
            'branch_code': self.branch_code_edit.text(),
            'is_default': self.bank_default_checkbox.isChecked(),
        }
        if not any(str(raw.get(key) or '').strip() for key in raw if key != 'is_default'):
            QMessageBox.information(self, 'حساب بانکی', 'اطلاعات حساب خالی است.')
            return
        try:
            data = validate_bank_account_payload(raw)
        except ValidationError as exc:
            QMessageBox.warning(self, 'اعتبارسنجی حساب بانکی', str(exc))
            return

        if data['is_default']:
            for item in self.bank_accounts:
                item['is_default'] = 0

        if self.current_bank_index is None:
            self.bank_accounts.append(data)
        else:
            self.bank_accounts[self.current_bank_index] = data

        if self.bank_accounts and not any(item['is_default'] for item in self.bank_accounts):
            self.bank_accounts[0]['is_default'] = 1

        self._render_bank_accounts()
        self._clear_bank_form()

    def _remove_selected_bank_account(self) -> None:
        if self.current_bank_index is None:
            QMessageBox.information(self, 'حساب بانکی', 'ابتدا یک حساب را از جدول انتخاب کنید.')
            return
        self.bank_accounts.pop(self.current_bank_index)
        if self.bank_accounts and not any(item['is_default'] for item in self.bank_accounts):
            self.bank_accounts[0]['is_default'] = 1
        self._render_bank_accounts()
        self._clear_bank_form()

    def _load_selected_bank_account(self) -> None:
        selected_items = self.bank_table.selectedItems()
        if not selected_items:
            return
        row_index = selected_items[0].row()
        if row_index >= len(self.bank_accounts):
            return
        self.current_bank_index = row_index
        bank = self.bank_accounts[row_index]
        self.bank_name_edit.setCurrentText(bank.get('bank_name') or '')
        self.account_number_edit.setText(bank.get('account_number') or '')
        self.iban_edit.setText(bank.get('iban') or '')
        self.card_number_edit.setText(bank.get('card_number') or '')
        self.branch_name_edit.setText(bank.get('branch_name') or '')
        self.branch_code_edit.setText(bank.get('branch_code') or '')
        self.bank_default_checkbox.setChecked(bool(bank.get('is_default')))

    def _render_bank_accounts(self) -> None:
        self.bank_table.setRowCount(len(self.bank_accounts))
        for row_index, row in enumerate(self.bank_accounts):
            values = [
                str(row_index + 1),
                row.get('bank_name') or '-',
                row.get('account_number') or '-',
                row.get('card_number') or '-',
                'بله' if row.get('is_default') else 'خیر',
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.bank_table.setItem(row_index, column_index, item)
        self.bank_table.resizeColumnsToContents()
        if hasattr(self, 'tabs'):
            count = len(self.bank_accounts)
            label = '🏦  حساب‌های بانکی' if count == 0 else f'🏦  حساب‌های بانکی ({count})'
            self.tabs.setTabText(1, label)

    def _clear_bank_form(self) -> None:
        self.current_bank_index = None
        self.bank_name_edit.setCurrentText('')
        self.account_number_edit.clear()
        self.iban_edit.clear()
        self.card_number_edit.clear()
        self.branch_name_edit.clear()
        self.branch_code_edit.clear()
        self.bank_default_checkbox.setChecked(False)
        self.bank_table.clearSelection()

    # ------------------------------------------------------------------
    # فرمت خودکار شماره کارت + خروجی PDF حساب‌ها
    # ------------------------------------------------------------------
    def _on_card_text_changed(self, text: str) -> None:
        """جدا کردن هر 4 رقم شماره کارت با خط تیره، حین تایپ"""
        cursor = self.card_number_edit.cursorPosition()
        digits_before_cursor = len([ch for ch in text[:cursor] if ch.isdigit()])

        digits = ''.join(ch for ch in text if ch.isdigit())[:16]
        grouped = '-'.join(digits[i:i + 4] for i in range(0, len(digits), 4))

        if grouped == text:
            return

        self.card_number_edit.blockSignals(True)
        self.card_number_edit.setText(grouped)

        count = 0
        new_cursor = len(grouped)
        for i, ch in enumerate(grouped):
            if count >= digits_before_cursor:
                new_cursor = i
                break
            if ch.isdigit():
                count += 1
        self.card_number_edit.setCursorPosition(new_cursor)
        self.card_number_edit.blockSignals(False)

    def _export_bank_accounts_pdf(self) -> None:
        """خروجی PDF از لیست حساب‌های بانکی شخص جاری"""
        if not self.bank_accounts:
            QMessageBox.information(self, 'خروجی PDF', 'هیچ حساب بانکی برای خروجی وجود ندارد.')
            return
        person_name = f"{self.first_name_edit.text()} {self.last_name_edit.text()}".strip() or 'شخص جدید (ثبت‌نشده)'
        file_path, _ = QFileDialog.getSaveFileName(
            self, 'ذخیره PDF حساب‌های بانکی', 'bank-accounts.pdf', 'PDF Files (*.pdf)'
        )
        if not file_path:
            return
        try:
            saved_path = export_person_bank_accounts_to_pdf(
                {
                    'person_name': person_name,
                    'person_mobile': self.mobile_edit.text() or '-',
                    'accounts': list(self.bank_accounts),
                },
                file_path,
            )
            QMessageBox.information(self, 'خروجی PDF', f'فایل با موفقیت ذخیره شد:\n{saved_path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطا', f'تولید PDF حساب‌های بانکی با خطا مواجه شد:\n{exc}')

    # ------------------------------------------------------------------
    # ابزار کمکی
    # ------------------------------------------------------------------
    def _select_combo_by_data(self, combo: QComboBox, value: Any) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(0)