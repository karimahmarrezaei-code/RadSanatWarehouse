from typing import Any, Dict
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QCheckBox, QPushButton, QGroupBox, QMessageBox
)

from app.core.database import DatabaseManager
from app.repositories.company_repository import CompanyRepository

class CompanyProfileDialog(QDialog):
    def __init__(self, db: DatabaseManager, user_data=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('ثبت / ویرایش مشخصات شرکت')
        self.resize(550, 650)

        self.db = db
        self.user_data = user_data or {}
        self.repository = CompanyRepository(db)
                       
        # بارگیری اطلاعات قبلی در زمان باز شدن فرم
        self.current_data = self.repository.get_company_profile()
        
        self.inputs = {}
        self.checkboxes = {}
        
        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        
        group_box = QGroupBox('اطلاعات شرکت رسمی (تنظیمات سربرگ چاپ)')
        layout = QGridLayout(group_box)
        layout.setHorizontalSpacing(15)
        layout.setVerticalSpacing(12)
        
        fields = [
            ('company_name', 'نام شرکت / فروشگاه', QLineEdit),
            ('ceo_name', 'نام مدیر عامل / شخص', QLineEdit),
            ('national_id', 'شناسه ملی / کد ملی', QLineEdit),
            ('economic_code', 'کد اقتصادی', QLineEdit),
            ('registration_number', 'شماره ثبت', QLineEdit),
            ('phone', 'تلفن ثابت', QLineEdit),
            ('mobile', 'موبایل', QLineEdit),
            ('email', 'ایمیل', QLineEdit),
            ('website', 'وب‌سایت', QLineEdit),
            ('address', 'آدرس', QTextEdit),
        ]
        
        layout.addWidget(QLabel('عنوان فیلد'), 0, 0)
        layout.addWidget(QLabel('مقدار'), 0, 1)
        layout.addWidget(QLabel('نمایش در چاپ؟'), 0, 2, alignment=Qt.AlignCenter)
        
        for row, (field_key, field_label, widget_class) in enumerate(fields, start=1):
            label_widget = QLabel(f"{field_label}:")
            
            input_widget = widget_class()
            if widget_class == QTextEdit:
                input_widget.setMinimumHeight(60)
            self.inputs[field_key] = input_widget
            
            checkbox_widget = QCheckBox('چاپ در سربرگ')
            checkbox_widget.setChecked(True)
            self.checkboxes[field_key] = checkbox_widget
            
            layout.addWidget(label_widget, row, 0, Qt.AlignTop if widget_class == QTextEdit else Qt.AlignVCenter)
            layout.addWidget(input_widget, row, 1)
            layout.addWidget(checkbox_widget, row, 2, Qt.AlignTop if widget_class == QTextEdit else Qt.AlignVCenter)

        root.addWidget(group_box)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton('ذخیره تنظیمات')
        save_btn.clicked.connect(self._save_settings)
        
        cancel_btn = QPushButton('انصراف')
        cancel_btn.setObjectName('SecondaryButton')
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        root.addLayout(btn_layout)

    def _load_data(self) -> None:
        for key, widget in self.inputs.items():
            val = self.current_data.get(key)
            if val is None:
                val = ''
                
            if isinstance(widget, QLineEdit):
                widget.setText(str(val))
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(val))
                
            show_key = f"show_{key}"
            # مقادیر از دیتابیس بصورت 0 و 1 برمی‌گردند
            show_val = self.current_data.get(show_key, 1) 
            self.checkboxes[key].setChecked(bool(show_val))

    def _save_settings(self) -> None:
        payload = {}
        for key, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                payload[key] = widget.text().strip()
            elif isinstance(widget, QTextEdit):
                payload[key] = widget.toPlainText().strip()
                
            show_key = f"show_{key}"
            payload[show_key] = self.checkboxes[key].isChecked()
            
        self.repository.save_company_profile(payload)
        
        QMessageBox.information(self, "موفق", "تنظیمات شرکت و سربرگ با موفقیت ذخیره شد.")
        self.accept()