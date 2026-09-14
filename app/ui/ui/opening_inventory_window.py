# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
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
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_display_from_iso, today_iso_date
from app.core.validators import ValidationError, validate_opening_inventory_payload
from app.repositories.opening_inventory_repository import OpeningInventoryRepository

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

class HtmlPreviewDialog(QDialog):
    """پیش‌نمایش تحت‌وب سند با هدر شرکت + دکمه‌های چاپ و ذخیره PDF"""

    def __init__(self, title: str, html: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1100, 800)
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.print_button = QPushButton('🖨️ چاپ')
        self.print_button.setObjectName('PrimaryButton')
        self.print_button.clicked.connect(self._print_document)
        self.pdf_button = QPushButton('💾 ذخیره PDF')
        self.pdf_button.setObjectName('PurpleButton')
        self.pdf_button.clicked.connect(self._save_pdf)
        close_button = QPushButton('بستن')
        close_button.setObjectName('SecondaryButton')
        close_button.clicked.connect(self.accept)
        toolbar.addWidget(self.print_button)
        toolbar.addWidget(self.pdf_button)
        toolbar.addStretch()
        toolbar.addWidget(close_button)
        layout.addLayout(toolbar)
        html = self._inject_letterhead(html, parent)
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            self.browser = QWebEngineView()
        except Exception:
            self.browser = QTextBrowser()
        self.browser.setHtml(html)
        layout.addWidget(self.browser)

    def _inject_letterhead(self, html, parent):
        """تزریق سربرگ شرکت به سند (اگر از قبل نداشته باشد)"""
        try:
            if not html or 'company-info' in html:
                return html
            db = getattr(parent, 'db', None) or getattr(getattr(parent, 'repository', None), 'db', None)
            if not db:
                return html
            try:
                from app.core.letterhead import render_letterhead_html, get_company_profile
                profile = get_company_profile(db)
            except Exception:
                from app.core.letterhead import render_letterhead_html, get_filtered_company
                profile = get_filtered_company(db)
            lh = render_letterhead_html(profile)
            if not lh:
                return html
            i = html.lower().find('<body')
            if i != -1:
                j = html.find('>', i)
                if j != -1:
                    return html[:j + 1] + lh + html[j + 1:]
            return lh + html
        except Exception:
            return html

    def _print_document(self) -> None:
        try:
            from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
            printer = QPrinter(QPrinter.HighResolution)
            dlg = QPrintDialog(printer, self)
            if dlg.exec_() != QPrintDialog.Accepted:
                return
            if hasattr(self.browser, 'page'):
                self.browser.page().print_(printer)
            else:
                self.browser.document().print_(printer)
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در پرینت:\n{e}')

    def _save_pdf(self) -> None:
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, 'ذخیره فایل PDF', 'سند-افتتاحیه.pdf', 'PDF Files (*.pdf)')
        if not file_path:
            return
        if not file_path.lower().endswith('.pdf'):
            file_path += '.pdf'
        try:
            if hasattr(self.browser, 'page'):
                self.browser.page().printToPdf(file_path)
            else:
                from PyQt5.QtPrintSupport import QPrinter
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(file_path)
                self.browser.document().print_(printer)
            QMessageBox.information(self, 'موفق', f'فایل PDF ذخیره شد:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ذخیره PDF:\n{e}')
class OpeningListDialog(QDialog):
    """پنجره مستقل نمایش لیست اسناد افتتاحیه به همراه جزئیات ردیف‌های هر سند."""

    def __init__(self, repository: OpeningInventoryRepository, parent=None) -> None:
        super().__init__(parent)
        self.repository = repository

        self.setWindowTitle('لیست اسناد افتتاحیه')
        self.resize(1150, 760)
        # غیرمودال؛ کاربر می‌تواند همزمان با فرم کار کند
        self.setModal(False)
        self._build_ui()
        self.refresh_table()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # --- نوار ابزار ---
        toolbar_card = QFrame()
        toolbar_card.setObjectName('Card')
        toolbar = QHBoxLayout(toolbar_card)
        toolbar.setSpacing(10)

        info = QLabel('با کلیک روی هر سند، ردیف‌های آن در جدول پایین نمایش داده می‌شود. دوبار کلیک = پیش‌نمایش چاپی.')
        info.setObjectName('Muted')
        toolbar.addWidget(info, 1)

        refresh_button = QPushButton('بروزرسانی')
        refresh_button.setObjectName('SecondaryButton')
        refresh_button.clicked.connect(self.refresh_table)
        toolbar.addWidget(refresh_button)
        root.addWidget(toolbar_card)

        # --- جدول اسناد (بالا) ---
        table_group = QGroupBox('اسناد افتتاحیه')
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            'شناسه', 'شماره سند', 'انبار', 'تعداد انواع', 'جمع تعداد', 'جمع مبلغ',
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnHidden(0, True)
        # --- تنظیمات خوانایی جدول ---
        apply_table_style_by_theme(self.table)
        self.table.setAlternatingRowColors(True)          # رنگ یک‌درمیان ردیف‌ها
        self.table.verticalHeader().setDefaultSectionSize(40)   # ارتفاع مناسب ردیف‌ها
        self.table.setShowGrid(True)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setMinimumSectionSize(110)                 # حداقل عرض هر ستون
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)   # ستون انبار کشسان
        header.setStretchLastSection(True)
        header.setFixedHeight(42)
        self.table.setColumnWidth(1, 170)   # شماره سند
        self.table.setColumnWidth(3, 120)   # تعداد انواع
        self.table.setColumnWidth(4, 130)   # جمع تعداد
        self.table.setColumnWidth(5, 180)   # جمع مبلغ
        # کلیک => نمایش ردیف‌های سند | دابل‌کلیک => پیش‌نمایش چاپی
        self.table.itemSelectionChanged.connect(self._show_selected_document_lines)
        self.table.itemDoubleClicked.connect(lambda *_: self.preview_selected_document())
        table_layout.addWidget(self.table)
        root.addWidget(table_group, 4)

        # --- جدول جزئیات ردیف‌های سند انتخابی (پایین) ---
        self.details_group = QGroupBox('ردیف‌های سند انتخابی')
        details_layout = QVBoxLayout(self.details_group)

        self.doc_info_label = QLabel('برای مشاهده جزئیات، یک سند را از جدول بالا انتخاب کنید.')
        self.doc_info_label.setObjectName('Muted')
        details_layout.addWidget(self.doc_info_label)

        self.details_table = QTableWidget(0, 8)
        self.details_table.setHorizontalHeaderLabels([
            'ردیف', 'کد پالت', 'نام پالت', 'جنس', 'تعداد', 'قیمت واحد', 'مبلغ کل', 'توضیح',
        ])
        self.details_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.details_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.details_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.details_table.verticalHeader().setVisible(False)
        apply_table_style_by_theme(self.details_table)
        self.details_table.setAlternatingRowColors(True)
        self.details_table.verticalHeader().setDefaultSectionSize(38)
        details_header = self.details_table.horizontalHeader()
        details_header.setDefaultAlignment(Qt.AlignCenter)
        details_header.setFixedHeight(40)
        details_header.setSectionResizeMode(QHeaderView.Interactive)
        details_header.setSectionResizeMode(2, QHeaderView.Stretch)   # نام پالت کشسان
        details_header.setStretchLastSection(True)                    # توضیح کشسان
        self.details_table.setColumnWidth(0, 55)    # ردیف
        self.details_table.setColumnWidth(1, 110)   # کد پالت
        self.details_table.setColumnWidth(3, 110)   # جنس
        self.details_table.setColumnWidth(4, 110)   # تعداد
        self.details_table.setColumnWidth(5, 150)   # قیمت واحد
        self.details_table.setColumnWidth(6, 150)   # مبلغ کل
        details_layout.addWidget(self.details_table)
        root.addWidget(self.details_group, 5)

        # --- دکمه‌های پایین پنجره ---
        buttons_row = QHBoxLayout()
        buttons_row.addStretch()

        self.preview_button = QPushButton('پیش‌نمایش چاپی سند')
        self.preview_button.clicked.connect(self.preview_selected_document)

        close_button = QPushButton('بستن')
        close_button.setObjectName('SecondaryButton')
        close_button.clicked.connect(self.close)

        buttons_row.addWidget(self.preview_button)
        buttons_row.addWidget(close_button)
        root.addLayout(buttons_row)

    def _fmt_money(self, value: int) -> str:
        return f'{int(value):,} ریال'

    def showEvent(self, event) -> None:
        super().showEvent(event)
        apply_table_style_by_theme(self.table)
        apply_table_style_by_theme(self.details_table)

    def refresh_table(self) -> None:
        rows = self.repository.list_recent_openings()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row['id']),
                row['opening_no'],
                row['warehouse_name'],
                str(int(row['total_types_count'] or 0)),
                f"{int(row['total_qty'] or 0):,}",
                self._fmt_money(int(row['total_amount'] or 0)),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                # اعداد وسط‌چین، متن‌ها راست‌چین
                if col in (3, 4, 5):
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_index, col, item)
        # پاک کردن جزئیات قبلی
        self.details_table.setRowCount(0)
        self.doc_info_label.setText('برای مشاهده جزئیات، یک سند را از جدول بالا انتخاب کنید.')

    def _selected_document_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _show_selected_document_lines(self) -> None:
        """نمایش ردیف‌های سند انتخاب‌شده در جدول جزئیات."""
        doc_id = self._selected_document_id()
        if doc_id is None:
            return
        doc = self.repository.get_opening_document(doc_id)
        if not doc:
            self.details_table.setRowCount(0)
            self.doc_info_label.setText('سند موردنظر یافت نشد. لیست را بروزرسانی کنید.')
            return

        # خلاصه اطلاعات سند بالای جدول جزئیات
        self.doc_info_label.setText(
            f"شماره سند: {doc.get('opening_no', '-')} | "
            f"تاریخ: {doc.get('jalali_date_text') or doc.get('opening_date') or '-'} | "
            f"انبار: {doc.get('warehouse_name', '-')} | "
            f"جمع مبلغ: {self._fmt_money(int(doc.get('total_amount') or 0))}"
        )

        items = doc.get('items') or []
        self.details_table.setRowCount(len(items))
        for row_index, line in enumerate(items):
            values = [
                str(row_index + 1),
                line.get('pallet_code') or '-',
                line.get('pallet_name') or '-',
                line.get('material_type') or '-',
                f"{int(line.get('qty') or 0):,}",
                f"{int(line.get('unit_price') or 0):,}",
                f"{int(line.get('total_price') or 0):,}",
                line.get('description') or '-',
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col in (0, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.details_table.setItem(row_index, col, item)

    def preview_selected_document(self) -> None:
        doc_id = self._selected_document_id()
        if doc_id is None:
            QMessageBox.information(self, 'پیش‌نمایش سند', 'ابتدا یک سند را از جدول انتخاب کنید.')
            return
        doc = self.repository.get_opening_document(doc_id)
        if not doc:
            QMessageBox.warning(self, 'خطا', 'سند موردنظر یافت نشد. لیست را بروزرسانی کنید.')
            return
        HtmlPreviewDialog('پیش‌نمایش سند افتتاحیه', self.repository.render_opening_html(doc), self).exec_()


class OpeningInventoryWindow(QDialog):
    data_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.repository = OpeningInventoryRepository(db)
        self.list_dialog: Optional[OpeningListDialog] = None

        permissions = set(user_data.get('permissions', []) or [])
        self.can_manage = 'openings.manage' in permissions or user_data.get('role_code') == 'ADMIN'
        self.warehouses: List[Dict[str, Any]] = []
        self.pallets: List[Dict[str, Any]] = []

        self.setWindowTitle('افتتاحیه انبار')
        # فرم جمع‌وجورتر؛ لیست اسناد در پنجره جداگانه باز می‌شود
        self.resize(1180, 780)
        self._build_ui()
        self._load_lookups()
        self._apply_permissions()
        self.clear_form()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # --- سربرگ ---
        header = QFrame()
        header.setObjectName('Card')
        header_layout = QHBoxLayout(header)

        titles_layout = QVBoxLayout()
        title = QLabel('ثبت افتتاحیه انبار')
        title.setObjectName('Title')
        subtitle = QLabel('ثبت دستی موجودی اولیه و ارزش ریالی اولیه پالت‌ها برای شروع کار با سیستم')
        subtitle.setObjectName('Muted')
        subtitle.setWordWrap(True)
        titles_layout.addWidget(title)
        titles_layout.addWidget(subtitle)
        header_layout.addLayout(titles_layout, 1)

        # دکمه جداگانه برای باز کردن دیتاگرید اسناد در پنجره مستقل
        self.show_list_button = QPushButton('📋 نمایش اسناد افتتاحیه')
        self.show_list_button.clicked.connect(self.open_list_dialog)
        header_layout.addWidget(self.show_list_button, 0, Qt.AlignTop)

        root.addWidget(header)

        # --- اطلاعات سند افتتاحیه ---
        doc_group = QGroupBox('اطلاعات سند افتتاحیه')
        doc_layout = QGridLayout(doc_group)
        doc_layout.setHorizontalSpacing(12)
        doc_layout.setVerticalSpacing(10)

        self.opening_no_label = QLabel('-')
        self.opening_no_label.setObjectName('Title')
        self.date_info_label = QLabel('-')
        self.date_info_label.setObjectName('Muted')

        self.opening_date_edit = QDateEdit(QDate.currentDate())
        self.opening_date_edit.setCalendarPopup(True)
        self.opening_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.opening_date_edit.dateChanged.connect(self._refresh_labels)

        self.warehouse_combo = QComboBox()

        self.description_edit = QTextEdit()
        self.description_edit.setMinimumHeight(70)

        self.total_types_label = QLabel('0')
        self.total_qty_label = QLabel('0')
        self.total_amount_label = QLabel('0 ریال')

        doc_layout.addWidget(QLabel('شماره سند'), 0, 0)
        doc_layout.addWidget(self.opening_no_label, 0, 1)
        doc_layout.addWidget(QLabel('تاریخ'), 0, 2)
        doc_layout.addWidget(self.opening_date_edit, 0, 3)
        doc_layout.addWidget(QLabel('تاریخ شمسی'), 1, 0)
        doc_layout.addWidget(self.date_info_label, 1, 1)
        doc_layout.addWidget(QLabel('انبار'), 1, 2)
        doc_layout.addWidget(self.warehouse_combo, 1, 3)
        doc_layout.addWidget(QLabel('توضیحات'), 2, 0)
        doc_layout.addWidget(self.description_edit, 2, 1, 1, 3)
        root.addWidget(doc_group)

        # --- ردیف‌های افتتاحیه (بخشی از خود سند؛ در فرم می‌ماند) ---
        items_group = QGroupBox('ردیف‌های افتتاحیه')
        items_layout = QVBoxLayout(items_group)
        action_row = QHBoxLayout()
        self.add_row_button = QPushButton('افزودن ردیف')
        self.add_row_button.setObjectName('SecondaryButton')
        self.add_row_button.clicked.connect(self.add_line_row)
        self.remove_row_button = QPushButton('حذف ردیف انتخابی')
        self.remove_row_button.setObjectName('SecondaryButton')
        self.remove_row_button.clicked.connect(self.remove_selected_row)
        action_row.addWidget(self.add_row_button)
        action_row.addWidget(self.remove_row_button)
        action_row.addStretch()
        items_layout.addLayout(action_row)

        self.lines_table = QTableWidget(0, 9)
        self.lines_table.setHorizontalHeaderLabels([
            'ردیف', 'پالت', 'جنس', 'ابعاد', 'تعداد', 'قیمت واحد', 'مبلغ کل', 'توضیح', '',
        ])
        self.lines_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.lines_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lines_table.verticalHeader().setVisible(False)
        # --- تنظیمات خوانایی جدول ردیف‌ها ---
        apply_table_style_by_theme(self.lines_table)
        self.lines_table.setAlternatingRowColors(True)
        self.lines_table.verticalHeader().setDefaultSectionSize(46)  # ارتفاع کافی برای ویجت‌های داخل سلول
        lines_header = self.lines_table.horizontalHeader()
        lines_header.setDefaultAlignment(Qt.AlignCenter)
        lines_header.setFixedHeight(42)
        lines_header.setSectionResizeMode(QHeaderView.Interactive)
        lines_header.setSectionResizeMode(1, QHeaderView.Stretch)   # ستون پالت کشسان
        lines_header.setSectionResizeMode(7, QHeaderView.Stretch)   # ستون توضیح کشسان
        self.lines_table.setColumnWidth(0, 55)    # ردیف
        self.lines_table.setColumnWidth(2, 110)   # جنس
        self.lines_table.setColumnWidth(3, 130)   # ابعاد
        self.lines_table.setColumnWidth(4, 110)   # تعداد
        self.lines_table.setColumnWidth(5, 150)   # قیمت واحد
        self.lines_table.setColumnWidth(6, 150)   # مبلغ کل
        self.lines_table.setColumnWidth(8, 52)    # دکمه افزودن ردیف
        lines_header.setSectionResizeMode(8, QHeaderView.Fixed)
        items_layout.addWidget(self.lines_table)
        root.addWidget(items_group, 1)

        # --- جمع‌های سند ---
        totals_card = QFrame()
        totals_card.setObjectName('Card')
        totals_layout = QHBoxLayout(totals_card)
        totals_layout.setSpacing(18)
        totals_layout.addWidget(QLabel('تعداد انواع:'))
        totals_layout.addWidget(self.total_types_label)
        totals_layout.addSpacing(20)
        totals_layout.addWidget(QLabel('جمع تعداد:'))
        totals_layout.addWidget(self.total_qty_label)
        totals_layout.addSpacing(20)
        totals_layout.addWidget(QLabel('جمع مبلغ:'))
        totals_layout.addWidget(self.total_amount_label)
        totals_layout.addStretch()
        root.addWidget(totals_card)

        # --- دکمه‌های عملیات ---
        footer_actions = QHBoxLayout()
        self.new_button = QPushButton('فرم جدید')
        self.new_button.setObjectName('SecondaryButton')
        self.new_button.clicked.connect(self.clear_form)
        self.preview_button = QPushButton('پیش‌نمایش افتتاحیه')
        self.preview_button.setObjectName('SecondaryButton')
        self.preview_button.clicked.connect(self.preview_document)
        self.save_button = QPushButton('ثبت و تایید افتتاحیه')
        self.save_button.clicked.connect(self.save_opening)
        footer_actions.addWidget(self.new_button)
        footer_actions.addWidget(self.preview_button)
        footer_actions.addStretch()
        footer_actions.addWidget(self.save_button)
        root.addLayout(footer_actions)

    # ------------------------------------------------------------------
    # پنجره لیست اسناد افتتاحیه (دیتاگرید جداگانه)
    # ------------------------------------------------------------------
    def open_list_dialog(self) -> None:
        """باز کردن دیتاگرید اسناد افتتاحیه در یک پنجره مستقل با دکمه جداگانه."""
        if self.list_dialog is None:
            self.list_dialog = OpeningListDialog(self.repository, parent=self)
        self.list_dialog.refresh_table()
        self.list_dialog.show()
        self.list_dialog.raise_()
        self.list_dialog.activateWindow()

    def _refresh_list_if_open(self) -> None:
        if self.list_dialog is not None and self.list_dialog.isVisible():
            self.list_dialog.refresh_table()

    # ------------------------------------------------------------------
    # دسترسی‌ها و داده‌های پایه
    # ------------------------------------------------------------------
    def _apply_permissions(self) -> None:
        if not self.can_manage:
            for widget in [
                self.opening_date_edit, self.warehouse_combo, self.description_edit,
                self.add_row_button, self.remove_row_button,
                self.new_button, self.preview_button, self.save_button,
            ]:
                widget.setEnabled(False)

    def _load_lookups(self) -> None:
        self.warehouses = self.repository.list_warehouses()
        self.pallets = self.repository.list_pallets()
        self.warehouse_combo.clear()
        self.warehouse_combo.addItem('انتخاب کنید', None)
        for item in self.warehouses:
            self.warehouse_combo.addItem(f"{item['code']} | {item['name']}", item['id'])

    def _refresh_labels(self) -> None:
        iso_date = self.opening_date_edit.date().toString('yyyy-MM-dd')
        self.date_info_label.setText(jalali_date_display_from_iso(iso_date))
        self.opening_no_label.setText(self.repository.next_opening_no(iso_date))

    # ------------------------------------------------------------------
    # ابزارهای کمکی
    # ------------------------------------------------------------------
    def _fmt_money(self, value: int) -> str:
        return f'{int(value):,} ریال'

    def _int_from_text(self, value: str) -> int:
        digits = ''.join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else 0

    # ------------------------------------------------------------------
    # مدیریت ردیف‌های افتتاحیه
    # ------------------------------------------------------------------
    def add_line_row(self) -> None:
        row = self.lines_table.rowCount()
        self.lines_table.insertRow(row)
        row_no_item = QTableWidgetItem(str(row + 1))
        row_no_item.setTextAlignment(Qt.AlignCenter)
        row_no_item.setFlags(row_no_item.flags() & ~Qt.ItemIsEditable)
        self.lines_table.setItem(row, 0, row_no_item)

        pallet_combo = QComboBox()
        pallet_combo.addItem('انتخاب پالت', None)
        for item in self.pallets:
            pallet_combo.addItem(f"{item['code']} | {item['name']}", item['id'])
        # ردیف بر اساس خود ویجت پیدا می‌شود تا بعد از حذف ردیف‌ها هم درست کار کند
        pallet_combo.currentIndexChanged.connect(
            lambda _, combo=pallet_combo: self._update_row_info_by_widget(combo)
        )

        material_item = QTableWidgetItem('-')
        material_item.setTextAlignment(Qt.AlignCenter)
        dims_item = QTableWidgetItem('-')
        dims_item.setTextAlignment(Qt.AlignCenter)
        qty_spin = QSpinBox()
        qty_spin.setRange(0, 100000000)
        qty_spin.setAlignment(Qt.AlignCenter)
        qty_spin.valueChanged.connect(self.recalculate_totals)
        unit_price_edit = QLineEdit()
        unit_price_edit.setAlignment(Qt.AlignCenter)
        unit_price_edit.setPlaceholderText('0')
        unit_price_edit.textChanged.connect(lambda: self._price_changed(unit_price_edit))
        total_item = QTableWidgetItem('0')
        total_item.setTextAlignment(Qt.AlignCenter)
        total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText('توضیح ردیف...')

        # دکمه افزودن ردیف جدید — کنار فیلد توضیح هر ردیف
        add_button = QPushButton('➕')
        add_button.setToolTip('افزودن ردیف جدید')
        add_button.setFixedSize(34, 34)
        add_button.clicked.connect(self._add_row_and_focus)
        add_container = QWidget()
        add_container_layout = QHBoxLayout(add_container)
        add_container_layout.setContentsMargins(2, 2, 2, 2)
        add_container_layout.setAlignment(Qt.AlignCenter)
        add_container_layout.addWidget(add_button)

        self.lines_table.setCellWidget(row, 1, pallet_combo)
        self.lines_table.setItem(row, 2, material_item)
        self.lines_table.setItem(row, 3, dims_item)
        self.lines_table.setCellWidget(row, 4, qty_spin)
        self.lines_table.setCellWidget(row, 5, unit_price_edit)
        self.lines_table.setItem(row, 6, total_item)
        self.lines_table.setCellWidget(row, 7, desc_edit)
        self.lines_table.setCellWidget(row, 8, add_container)
        self.recalculate_totals()

    def _add_row_and_focus(self) -> None:
        """افزودن ردیف جدید و بردن فوکوس روی انتخاب پالت آن."""
        self.add_line_row()
        new_row = self.lines_table.rowCount() - 1
        self.lines_table.scrollToBottom()
        combo = self.lines_table.cellWidget(new_row, 1)
        if isinstance(combo, QComboBox):
            combo.setFocus()

    def _update_row_info_by_widget(self, combo: QComboBox) -> None:
        # پیدا کردن ردیف فعلی ویجت (ایمن در برابر حذف/جابجایی ردیف‌ها)
        for row in range(self.lines_table.rowCount()):
            if self.lines_table.cellWidget(row, 1) is combo:
                pallet_id = combo.currentData()
                pallet = next((p for p in self.pallets if p['id'] == pallet_id), None)
                self.lines_table.item(row, 2).setText(pallet['material_type'] if pallet else '-')
                self.lines_table.item(row, 3).setText(pallet['dimensions'] if pallet else '-')
                break
        self.recalculate_totals()

    def _price_changed(self, edit: QLineEdit) -> None:
        digits = ''.join(ch for ch in edit.text() if ch.isdigit())
        edit.blockSignals(True)
        edit.setText(f'{int(digits):,}' if digits else '')
        edit.blockSignals(False)
        self.recalculate_totals()

    def remove_selected_row(self) -> None:
        row = self.lines_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'افتتاحیه انبار', 'ابتدا یک ردیف را انتخاب کنید.')
            return
        self.lines_table.removeRow(row)
        for idx in range(self.lines_table.rowCount()):
            item = self.lines_table.item(idx, 0)
            if item:
                item.setText(str(idx + 1))
        if self.lines_table.rowCount() == 0:
            self.add_line_row()
        self.recalculate_totals()

    def recalculate_totals(self) -> None:
        total_types = 0
        total_qty = 0
        total_amount = 0
        for row in range(self.lines_table.rowCount()):
            combo = self.lines_table.cellWidget(row, 1)
            qty_widget = self.lines_table.cellWidget(row, 4)
            unit_edit = self.lines_table.cellWidget(row, 5)
            qty = qty_widget.value() if isinstance(qty_widget, QSpinBox) else 0
            unit_price = self._int_from_text(unit_edit.text()) if isinstance(unit_edit, QLineEdit) else 0
            line_total = qty * unit_price
            item = self.lines_table.item(row, 6)
            if item:
                item.setText(f'{line_total:,}')
            if isinstance(combo, QComboBox) and combo.currentData():
                total_types += 1
            total_qty += qty
            total_amount += line_total
        self.total_types_label.setText(str(total_types))
        self.total_qty_label.setText(f'{total_qty:,}')
        self.total_amount_label.setText(self._fmt_money(total_amount))

    # ------------------------------------------------------------------
    # جمع‌آوری داده‌های سند
    # ------------------------------------------------------------------
    def _collect_lines(self) -> List[Dict[str, Any]]:
        lines: List[Dict[str, Any]] = []
        for row in range(self.lines_table.rowCount()):
            combo = self.lines_table.cellWidget(row, 1)
            qty_widget = self.lines_table.cellWidget(row, 4)
            unit_edit = self.lines_table.cellWidget(row, 5)
            desc_edit = self.lines_table.cellWidget(row, 7)
            lines.append(
                {
                    'pallet_id': combo.currentData() if isinstance(combo, QComboBox) else None,
                    'qty': qty_widget.value() if isinstance(qty_widget, QSpinBox) else 0,
                    'unit_price': unit_edit.text() if isinstance(unit_edit, QLineEdit) else '0',
                    'description': desc_edit.text() if isinstance(desc_edit, QLineEdit) else '',
                }
            )
        return lines

    def _collect_payload(self) -> Dict[str, Any]:
        return {
            'opening_date': self.opening_date_edit.date().toString('yyyy-MM-dd'),
            'warehouse_id': self.warehouse_combo.currentData(),
            'description': self.description_edit.toPlainText(),
            'lines': self._collect_lines(),
        }

    # ------------------------------------------------------------------
    # پیش‌نمایش و ثبت
    # ------------------------------------------------------------------
    def preview_document(self) -> None:
        try:
            payload = validate_opening_inventory_payload(self._collect_payload())
            document = {
                'opening_no': self.repository.next_opening_no(payload['opening_date']),
                'opening_date': payload['opening_date'],
                'jalali_date_text': jalali_date_display_from_iso(payload['opening_date']),
                'warehouse_name': self.warehouse_combo.currentText(),
                'document_status': 'CONFIRMED',
                'total_types_count': payload['total_types_count'],
                'total_qty': payload['total_qty'],
                'total_amount': payload['total_amount'],
                'description': payload['description'],
                'items': [],
            }
            for line in payload['lines']:
                pallet = next((p for p in self.pallets if p['id'] == line['pallet_id']), None)
                document['items'].append(
                    {
                        'pallet_code': pallet['code'] if pallet else '-',
                        'pallet_name': pallet['name'] if pallet else '-',
                        'material_type': pallet['material_type'] if pallet else '-',
                        'qty': line['qty'],
                        'unit_price': line['unit_price'],
                        'total_price': line['total_price'],
                        'description': line['description'],
                    }
                )
            html = self.repository.render_opening_html(document)
        except ValidationError as exc:
            QMessageBox.warning(self, 'پیش‌نمایش افتتاحیه', str(exc))
            return
        HtmlPreviewDialog('پیش‌نمایش سند افتتاحیه', html, self).exec_()

    def save_opening(self) -> None:
        if not self.can_manage:
            return
        try:
            saved = self.repository.create_opening_document(self._collect_payload(), user_id=self.user_data.get('id'))
        except ValidationError as exc:
            QMessageBox.warning(self, 'افتتاحیه انبار', str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'خطا', f'ثبت افتتاحیه با خطا مواجه شد:\n{exc}')
            return
        QMessageBox.information(self, 'ثبت افتتاحیه', f"افتتاحیه انبار با شماره «{saved.get('opening_no')}» ثبت شد.")
        self._refresh_list_if_open()
        self.clear_form()
        self.data_changed.emit()
        HtmlPreviewDialog('پیش‌نمایش سند ثبت‌شده', self.repository.render_opening_html(saved), self).exec_()

    def clear_form(self) -> None:
        self.opening_date_edit.setDate(QDate.fromString(today_iso_date(), 'yyyy-MM-dd'))
        self.warehouse_combo.setCurrentIndex(0)
        self.description_edit.clear()
        self.lines_table.setRowCount(0)
        self.add_line_row()
        self._refresh_labels()
        self.recalculate_totals()
