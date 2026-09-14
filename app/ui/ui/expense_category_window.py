"""
فرم مدیریت دسته‌بندی‌های هزینه‌های عملیاتی
قابلیت: اضافه، ویرایش، حذف، فعال/غیرفعال کردن دسته‌بندی
"""

from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QGroupBox,
    QMessageBox, QHeaderView, QAbstractItemView, QColorDialog,
    QFrame, QComboBox
)
from PyQt5.QtGui import QColor

# ===================================================================
# فرم مدیریت دسته‌بندی هزینه‌ها
# ===================================================================
class ExpenseCategoryWindow(QDialog):
    """فرم مدیریت دسته‌بندی‌های هزینه"""

    def __init__(self, db, user_data, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.setWindowTitle('مدیریت دسته‌بندی هزینه‌های عملیاتی')
        self.resize(800, 600)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self._load_categories()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # ===== هدر =====
        header = QFrame()
        header.setObjectName('Card')
        header_layout = QVBoxLayout(header)
        title = QLabel('مدیریت دسته‌بندی‌های هزینه')
        title.setObjectName('Title')
        subtitle = QLabel('دسته‌بندی‌های مورد استفاده در فرم ثبت هزینه را مدیریت کنید.')
        subtitle.setObjectName('Muted')
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        # ===== فرم ورود اطلاعات =====
        form_group = QGroupBox("ثبت / ویرایش دسته‌بندی")
        form_layout = QVBoxLayout(form_group)

        # ردیف ۱: نام دسته
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("نام دسته‌بندی:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("مثلاً: حقوق و دستمزد")
        name_row.addWidget(self.name_input, stretch=1)
        form_layout.addLayout(name_row)

        # ردیف ۲: توضیحات
        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel("توضیحات:"))
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("توضیح کوتاه (اختیاری)")
        desc_row.addWidget(self.desc_input, stretch=1)
        form_layout.addLayout(desc_row)

        # ردیف ۳: رنگ + دکمه‌ها
        action_row = QHBoxLayout()
        action_row.addWidget(QLabel("رنگ نمایشی:"))
        self.color_btn = QPushButton("   ")
        self.color_btn.setFixedWidth(60)
        self.color_btn.setFixedHeight(35)
        self.color_btn
        self.color_btn.clicked.connect(self._choose_color)
        action_row.addWidget(self.color_btn)

        self.current_color = '#2563eb'

        save_btn = QPushButton("ذخیره دسته‌بندی")
        save_btn.setObjectName('PrimaryButton')
        save_btn.clicked.connect(self._save_category)
        action_row.addWidget(save_btn)

        clear_btn = QPushButton("پاک کردن فرم")
        clear_btn.setObjectName('SecondaryButton')
        clear_btn.clicked.connect(self._clear_form)
        action_row.addWidget(clear_btn)

        action_row.addStretch()
        form_layout.addLayout(action_row)

        root.addWidget(form_group)

        # ===== جدول دسته‌بندی‌ها =====
        table_group = QGroupBox("دسته‌بندی‌های موجود")
        table_layout = QVBoxLayout(table_group)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "شناسه", "نام دسته‌بندی", "توضیحات", "رنگ", "وضعیت", "عملیات"
        ])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_category_selected)
        table_layout.addWidget(self.table)

        info_lbl = QLabel("برای ویرایش، یک دسته را انتخاب کرده و اطلاعات را تغییر دهید و ذخیره کنید.")
        info_lbl.setStyleSheet("color: #555; font-size: 11px;")
        table_layout.addWidget(info_lbl)

        root.addWidget(table_group)

        # ===== دکمه‌های پایین =====
        bottom_row = QHBoxLayout()
        self.status_lbl = QLabel("آماده")
        self.status_lbl.setStyleSheet("color: #555;")
        bottom_row.addWidget(self.status_lbl)
        bottom_row.addStretch()
        close_btn = QPushButton("بستن")
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(close_btn)
        root.addLayout(bottom_row)

        self.editing_id = None  # شناسه دسته در حال ویرایش

    def _choose_color(self):
        """انتخاب رنگ از Color Dialog"""
        color = QColorDialog.getColor(QColor(self.current_color), self, "انتخاب رنگ")
        if color.isValid():
            self.current_color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self.current_color}; border-radius: 5px;")

    def _load_categories(self):
        """بارگذاری دسته‌بندی‌ها از دیتابیس"""
        with self.db.connect() as conn:
            rows = conn.execute('''
                SELECT id, name, description, color, is_active
                FROM expense_categories
                ORDER BY id
            ''').fetchall()

            self.table.setRowCount(len(rows))
            active_count = 0

            for i, r in enumerate(rows):
                # شناسه (مخفی)
                id_item = QTableWidgetItem(str(r['id']))
                self.table.setItem(i, 0, id_item)

                # نام
                self.table.setItem(i, 1, QTableWidgetItem(r['name']))

                # توضیحات
                desc = r['description'] or '-'
                self.table.setItem(i, 2, QTableWidgetItem(desc))

                # رنگ
                color_item = QTableWidgetItem()
                color_item.setData(Qt.BackgroundRole, QColor(r['color'] or '#2563eb'))
                color_item.setText(r['color'] or '#2563eb')
                self.table.setItem(i, 3, color_item)

                # وضعیت
                is_active = bool(r['is_active'])
                status = "فعال ✅" if is_active else "غیرفعال ❌"
                if is_active:
                    active_count += 1
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 4, status_item)

                # عملیات
                action_item = QTableWidgetItem(
                    "تغییر وضعیت" if is_active else "فعال‌سازی"
                )
                action_item.setTextAlignment(Qt.AlignCenter)
                action_item.setData(Qt.UserRole, r['id'])
                action_item.setData(Qt.UserRole + 1, is_active)
                self.table.setItem(i, 5, action_item)

            self.status_lbl.setText(
                f"تعداد کل: {len(rows)} دسته | فعال: {active_count} | غیرفعال: {len(rows) - active_count}"
            )

    def _on_category_selected(self):
        """وقتی یک دسته انتخاب شد، اطلاعات آن در فرم لود شود"""
        selected = self.table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        self.editing_id = int(self.table.item(row, 0).text())
        name = self.table.item(row, 1).text()
        desc = self.table.item(row, 2).text()
        color = self.table.item(row, 3).text()

        self.name_input.setText(name)
        self.desc_input.setText(desc if desc != '-' else '')
        self.current_color = color
        self.color_btn.setStyleSheet(f"background-color: {color}; border-radius: 5px;")

    def _save_category(self):
        """ذخیره یا بروزرسانی دسته‌بندی"""
        name = self.name_input.text().strip()
        desc = self.desc_input.text().strip()

        if not name:
            QMessageBox.warning(self, "خطا", "نام دسته‌بندی الزامی است.")
            return

        with self.db.connect() as conn:
            if self.editing_id:
                # ویرایش دسته موجود
                conn.execute('''
                    UPDATE expense_categories
                    SET name = ?, description = ?, color = ?
                    WHERE id = ?
                ''', (name, desc, self.current_color, self.editing_id))
                conn.commit()
                QMessageBox.information(self, "موفقیت", f"دسته‌بندی «{name}» با موفقیت ویرایش شد.")
            else:
                # اضافه کردن دسته جدید
                try:
                    conn.execute('''
                        INSERT INTO expense_categories (name, description, color, is_active)
                        VALUES (?, ?, ?, 1)
                    ''', (name, desc, self.current_color))
                    QMessageBox.information(self, "موفقیت", f"دسته‌بندی «{name}» با موفقیت اضافه شد.")
                except Exception as e:
                    if 'UNIQUE' in str(e):
                        QMessageBox.warning(self, "خطا", f"دسته‌بندی «{name}» قبلاً وجود دارد.")
                        return
                    raise

        self._clear_form()
        self._load_categories()

    def _clear_form(self):
        """پاک کردن فرم"""
        self.editing_id = None
        self.name_input.clear()
        self.desc_input.clear()
        self.current_color = '#2563eb'
        self.color_btn

    def toggle_status(self, category_id: int, current_status: bool):
        """تغییر وضعیت فعال/غیرفعال"""
        new_status = 0 if current_status else 1
        with self.db.connect() as conn:
            conn.execute('''
                UPDATE expense_categories SET is_active = ? WHERE id = ?
            ''', (new_status, category_id))

    # ===== استفاده از double-click برای تغییر وضعیت =====
    def _on_table_double_clicked(self, row, col):
        if col == 5:  # ستون عملیات
            item = self.table.item(row, 5)
            if item:
                cat_id = item.data(Qt.UserRole)
                current_active = item.data(Qt.UserRole + 1)
                self.toggle_status(cat_id, current_active)
                self._load_categories()


# ===================================================================
# نسخه جایگزین با دکمه تغییر وضعیت قابل کلیک
# ===================================================================
class ExpenseCategoryManagerWindow(QDialog):
    """فرم مدیریت دسته‌بندی‌های هزینه با دکمه‌های قابل کلیک"""

    def __init__(self, db, user_data, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.setWindowTitle('مدیریت دسته‌بندی هزینه‌های عملیاتی')
        self.resize(900, 650)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self._load_categories()

    def _build_ui(self):
        from PyQt5.QtWidgets import QGroupBox, QFrame
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # هدر
        header = QFrame()
        header.setObjectName('Card')
        h_layout = QVBoxLayout(header)
        title = QLabel('مدیریت دسته‌بندی‌های هزینه')
        title.setObjectName('Title')
        subtitle = QLabel('دسته‌بندی‌های مورد استفاده در فرم ثبت هزینه را مدیریت کنید.')
        subtitle.setObjectName('Muted')
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        root.addWidget(header)

        # فرم ورود
        form_group = QGroupBox("ثبت / ویرایش دسته‌بندی")
        form_layout = QVBoxLayout(form_group)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("نام دسته‌بندی:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("مثلاً: حقوق و دستمزد")
        name_row.addWidget(self.name_input, stretch=1)
        form_layout.addLayout(name_row)

        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel("توضیحات:"))
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("توضیح کوتاه (اختیاری)")
        desc_row.addWidget(self.desc_input, stretch=1)
        form_layout.addLayout(desc_row)

        action_row = QHBoxLayout()
        action_row.addWidget(QLabel("رنگ نمایشی:"))
        self.color_btn = QPushButton("   ")
        self.color_btn.setFixedWidth(60)
        self.color_btn.setFixedHeight(35)
        self.color_btn
        self.color_btn.clicked.connect(self._choose_color)
        action_row.addWidget(self.color_btn)
        self.current_color = '#2563eb'

        save_btn = QPushButton(" ذخیره دسته‌بندی")
        save_btn.setObjectName('PrimaryButton')
        save_btn.clicked.connect(self._save_category)
        action_row.addWidget(save_btn)

        clear_btn = QPushButton("پاک کردن فرم")
        clear_btn.setObjectName('SecondaryButton')
        clear_btn.clicked.connect(self._clear_form)
        action_row.addWidget(clear_btn)

        action_row.addStretch()
        form_layout.addLayout(action_row)
        root.addWidget(form_group)

        # جدول
        table_group = QGroupBox("دسته‌بندی‌های موجود")
        table_layout = QVBoxLayout(table_group)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "نام دسته‌بندی", "توضیحات", "رنگ", "وضعیت", "عملیات"
        ])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_category_selected)
        table_layout.addWidget(self.table)

        info_lbl = QLabel("برای ویرایش: یک دسته انتخاب کنید، اطلاعات را تغییر دهید و ذخیره کنید. | برای تغییر وضعیت: روی دکمه عملیات کلیک کنید.")
        info_lbl.setStyleSheet("color: #555; font-size: 11px;")
        table_layout.addWidget(info_lbl)

        root.addWidget(table_group)

        # پایین
        bottom_row = QHBoxLayout()
        self.status_lbl = QLabel("آماده")
        self.status_lbl.setStyleSheet("color: #555;")
        bottom_row.addWidget(self.status_lbl)
        bottom_row.addStretch()
        delete_btn = QPushButton("🗑️ حذف دسته انتخاب‌شده")
        delete_btn.setObjectName('SecondaryButton')
        delete_btn.setStyleSheet("QPushButton#SecondaryButton { color: #dc2626; }")
        delete_btn.clicked.connect(self._delete_category)
        bottom_row.addWidget(delete_btn)
        close_btn = QPushButton("بستن")
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(close_btn)
        root.addLayout(bottom_row)

        self.editing_id = None

    def _choose_color(self):
        color = QColorDialog.getColor(QColor(self.current_color), self, "انتخاب رنگ")
        if color.isValid():
            self.current_color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self.current_color}; border-radius: 5px;")

    def _load_categories(self):
        from PyQt5.QtWidgets import QTableWidgetItem, QPushButton, QWidget, QHBoxLayout
        with self.db.connect() as conn:
            rows = conn.execute('''
                SELECT id, name, description, color, is_active
                FROM expense_categories
                ORDER BY id
            ''').fetchall()

            self.table.setRowCount(len(rows))
            active_count = 0

            for i, r in enumerate(rows):
                # نام
                self.table.setItem(i, 0, QTableWidgetItem(r['name']))

                # توضیحات
                self.table.setItem(i, 1, QTableWidgetItem(r['description'] or '-'))

                # رنگ
                color_item = QTableWidgetItem()
                color_item.setData(Qt.BackgroundRole, QColor(r['color'] or '#2563eb'))
                color_item.setText(r['color'] or '#2563eb')
                color_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 2, color_item)

                # وضعیت
                is_active = bool(r['is_active'])
                if is_active:
                    active_count += 1
                status_item = QTableWidgetItem("✅ فعال" if is_active else "❌ غیرفعال")
                status_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 3, status_item)

                # دکمه عملیات
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(5, 2, 5, 2)
                btn_layout.setSpacing(5)

                toggle_btn = QPushButton("غیرفعال" if is_active else "فعال‌سازی")
                toggle_btn.setFlat(True)
                toggle_btn.setStyleSheet(
                    "QPushButton { color: #2563eb; font-weight: bold; border: 1px solid #2563eb; "
                    "border-radius: 3px; padding: 3px 8px; }"
                )
                toggle_btn.clicked.connect(lambda checked, cid=r['id']: self._toggle_status(cid))
                btn_layout.addWidget(toggle_btn)
                btn_layout.addStretch()

                self.table.setCellWidget(i, 4, btn_widget)
                # ذخیره ID در ستون نام
                self.table.item(i, 0).setData(Qt.UserRole, r['id'])

            self.status_lbl.setText(
                f"تعداد کل: {len(rows)} دسته | فعال: {active_count} | غیرفعال: {len(rows) - active_count}"
            )

    def _on_category_selected(self):
        selected = self.table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        self.editing_id = self.table.item(row, 0).data(Qt.UserRole)
        name = self.table.item(row, 0).text()
        desc = self.table.item(row, 1).text()
        color = self.table.item(row, 2).text()

        self.name_input.setText(name)
        self.desc_input.setText(desc if desc != '-' else '')
        self.current_color = color
        self.color_btn.setStyleSheet(f"background-color: {color}; border-radius: 5px;")

    def _save_category(self):
        name = self.name_input.text().strip()
        desc = self.desc_input.text().strip()

        if not name:
            QMessageBox.warning(self, "خطا", "نام دسته‌بندی الزامی است.")
            return

        with self.db.connect() as conn:
            if self.editing_id:
                conn.execute('''
                    UPDATE expense_categories
                    SET name = ?, description = ?, color = ?
                    WHERE id = ?
                ''', (name, desc, self.current_color, self.editing_id))
                QMessageBox.information(self, "موفقیت", f"دسته‌بندی «{name}» ویرایش شد.")
            else:
                try:
                    conn.execute('''
                        INSERT INTO expense_categories (name, description, color, is_active)
                        VALUES (?, ?, ?, 1)
                    ''', (name, desc, self.current_color))
                    conn.commit()
                    QMessageBox.information(self, "موفقیت", f"دسته‌بندی «{name}» اضافه شد.")
                except Exception as e:
                    if 'UNIQUE' in str(e):
                        QMessageBox.warning(self, "خطا", f"دسته‌بندی «{name}» قبلاً وجود دارد.")
                        return
                    raise

        self._clear_form()
        self._load_categories()

    def _clear_form(self):
        self.editing_id = None
        self.name_input.clear()
        self.desc_input.clear()
        self.current_color = '#2563eb'
        self.color_btn
        self.table.clearSelection()

    def _toggle_status(self, category_id: int):
        with self.db.connect() as conn:
            row = conn.execute(
                'SELECT is_active FROM expense_categories WHERE id = ?', (category_id,)
            ).fetchone()
            if row:
                new_status = 0 if row['is_active'] else 1
                conn.execute(
                    'UPDATE expense_categories SET is_active = ? WHERE id = ?',
                    (new_status, category_id)
                )
                conn.commit()
        self._load_categories()

    def _delete_category(self):
        if self.editing_id is None:
            QMessageBox.warning(self, "خطا", "ابتدا یک دسته‌بندی را از جدول انتخاب کنید.")
            return

        # بررسی استفاده
        with self.db.connect() as conn:
            usage = conn.execute(
                'SELECT COUNT(*) as cnt FROM expenses WHERE category_id = ?',
                (self.editing_id,)
            ).fetchone()['cnt']

            if usage > 0:
                QMessageBox.warning(
                    self, "عدم امکان حذف",
                    f"این دسته‌بندی در {usage} هزینه استفاده شده و قابل حذف نیست.\n"
                    "ابتدا هزینه‌های مربوطه را به دسته دیگری منتقل کنید."
                )
                return

            cat_name = conn.execute(
                'SELECT name FROM expense_categories WHERE id = ?',
                (self.editing_id,)
            ).fetchone()['name']

        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف دسته‌بندی «{cat_name}» اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            with self.db.connect() as conn:
                conn.execute('DELETE FROM expense_categories WHERE id = ?', (self.editing_id,))
            QMessageBox.information(self, "موفقیت", f"دسته‌بندی «{cat_name}» حذف شد.")
            self._clear_form()
            self._load_categories()
