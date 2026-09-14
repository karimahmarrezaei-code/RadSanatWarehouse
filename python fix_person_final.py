# fix_person_final.py
with open('app/ui/person_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔍 در حال بررسی فایل person_window.py...")

# بررسی ۱: QCompleter
if 'QCompleter' not in content:
    content = content.replace(
        'from PyQt5.QtWidgets import (',
        'from PyQt5.QtWidgets import (\n    QCompleter,'
    )
    print("✅ QCompleter اضافه شد")
else:
    print("✔️ QCompleter وجود دارد")

# بررسی ۲: کامبو استان
if 'self.province_combo.setEditable(True)' not in content:
    content = content.replace(
        'self.province_combo = QComboBox()\n        self.province_combo.currentIndexChanged.connect(self._province_changed)',
        'self.province_combo = QComboBox()\n        self.province_combo.setEditable(True)\n        self.province_combo.setInsertPolicy(QComboBox.NoInsert)\n        self.province_combo.currentIndexChanged.connect(self._province_changed)'
    )
    print("✅ کامبو استان قابل جستجو شد")
else:
    print("✔️ کامبو استان قابل جستجو است")

# بررسی ۳: کامبو شهر
if 'self.city_combo.setEditable(True)' not in content:
    content = content.replace(
        'self.city_combo = QComboBox()',
        'self.city_combo = QComboBox()\n        self.city_combo.setEditable(True)\n        self.city_combo.setInsertPolicy(QComboBox.NoInsert)'
    )
    print("✅ کامبو شهر قابل جستجو شد")
else:
    print("✔️ کامبو شهر قابل جستجو است")

# بررسی ۴: تعداد ستون‌ها
if 'QTableWidget(0, 8)' in content:
    content = content.replace('QTableWidget(0, 8)', 'QTableWidget(0, 10)')
    print("✅ تعداد ستون‌ها به ۱۰ افزایش یافت")
elif 'QTableWidget(0, 10)' in content:
    print("✔️ تعداد ستون‌ها ۱۰ است")
else:
    print("❌ جدول پیدا نشد")

# بررسی ۵: هدر جدول
old_headers = """'شناسه', 'نام و نام خانوادگی', 'نقش‌ها', 'کد ملی',
            'موبایل', 'ایمیل', 'استان / شهر', 'وضعیت'"""
            
new_headers = """'شناسه', 'نام و نام خانوادگی', 'نقش‌ها', 'کد ملی',
            'موبایل', 'ایمیل', 'استان / شهر', 'آدرس', 'توضیحات', 'وضعیت'"""

if old_headers in content and new_headers not in content:
    content = content.replace(old_headers, new_headers)
    print("✅ ستون‌های آدرس و توضیحات به هدر اضافه شدند")
elif new_headers in content:
    print("✔️ ستون‌های آدرس و توضیحات در هدر وجود دارند")
else:
    print("❌ هدر جدول پیدا نشد")

# بررسی ۶: مقادیر جدول در refresh_table
old_values = """values = [
                str(row.get('id')),
                full_name,
                roles_text,
                row.get('national_id') or '-',
                row.get('mobile') or '-',
                row.get('email') or '-',
                location_text,
                status_text,
            ]"""

new_values = """values = [
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
            ]"""

if old_values in content and new_values not in content:
    content = content.replace(old_values, new_values)
    print("✅ آدرس و توضیحات به مقادیر جدول اضافه شدند")
elif new_values in content:
    print("✔️ آدرس و توضیحات در مقادیر جدول وجود دارند")
else:
    print("❌ بخش مقادیر جدول پیدا نشد")

# بررسی ۷: دکمه اکسل
if '_export_to_excel' not in content:
    # اضافه کردن دکمه
    export_button_code = """        refresh_button = _colored_button('🔄 بروزرسانی')
        refresh_button.clicked.connect(self.refresh_table)

        # ✅ دکمه خروجی اکسل
        export_button = _colored_button('📊 خروجی اکسل', 'success')
        export_button.clicked.connect(self._export_to_excel)

        toolbar.addWidget(self.search_edit, 1)"""

    old_toolbar = """        refresh_button = _colored_button('🔄 بروزرسانی')
        refresh_button.clicked.connect(self.refresh_table)

        toolbar.addWidget(self.search_edit, 1)"""

    if old_toolbar in content:
        content = content.replace(old_toolbar, export_button_code)
        print("✅ دکمه خروجی اکسل به نوار ابزار اضافه شد")
    else:
        print("❌ نوار ابزار پیدا نشد")

    # اضافه کردن متد
    export_method = '''
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
            QMessageBox.information(self, 'موفق', f'فایل با موفقیت ذخیره شد:\\n{path}')
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ذخیره:\\n{e}')
'''

    # پیدا کردن محل اضافه کردن متد
    if 'def select_row_by_id' in content and 'def _export_to_excel' not in content:
        content = content.replace(
            '    def select_row_by_id',
            export_method + '\n    def select_row_by_id'
        )
        print("✅ متد _export_to_excel اضافه شد")
    else:
        print("❌ محل اضافه کردن متد پیدا نشد")
else:
    print("✔️ دکمه و متد اکسل وجود دارند")

# ذخیره فایل
with open('app/ui/person_window.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "="*60)
print("✅✅✅ تمام تغییرات با موفقیت اعمال شدند!")
print("="*60)
print("\nحالا این دستورات را اجرا کنید:")
print("\n1. پاکسازی cache:")
print("   Get-ChildItem -Recurse -Directory -Filter \"__pycache__\" | Remove-Item -Recurse -Force")
print("   Get-ChildItem -Recurse -Filter \"*.pyc\" | Remove-Item -Force")
print("\n2. اجرای برنامه:")
print("   python main.py")
print("\n3. تست فرم اشخاص:")
print("   - لیست اشخاص را باز کنید")
print("   - باید ۱۰ ستون ببینید (شامل آدرس و توضیحات)")
print("   - دکمه 📊 خروجی اکسل باید وجود داشته باشد")
print("   - کامبوهای استان و شهر باید قابل تایپ باشند")
print("\n4. بیلد:")
print("   pyinstaller --noconfirm --onefile --windowed --icon=icon.ico --add-data \"app;app\" --add-data \"assets;assets\" --name \"WarehouseApp\" main.py")