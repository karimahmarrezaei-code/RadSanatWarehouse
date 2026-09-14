"""
ابزار محاسبه‌گر طراحی جعبه چوبی - نسخه نهایی
با مدیریت قیمت مصالح به ازای هر کاربر + دکمه ثبت در انبار
"""

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QComboBox, QFormLayout,
    QMessageBox, QFrame, QTextBrowser, QFileDialog,
    QTabWidget, QWidget, QDoubleSpinBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QStyledItemDelegate
)
from PyQt5.QtGui import QFont
import tempfile
import webbrowser
import os


# ===================================================================
# Delegate برای نمایش جداکننده هزارگان
# ===================================================================
class IntegerCommaDelegate(QStyledItemDelegate):
    """نمایش اعداد با جداکننده هزارگان در جدول"""
    def displayText(self, value, locale):
        try:
            return f"{int(value):,}"
        except:
            return str(value)
    
    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        if isinstance(value, str):
            value = value.replace(',', '')
        try:
            editor.setText(str(int(value)) if value else "0")
        except:
            editor.setText("0")
    
    def setModelData(self, editor, model, index):
        text = editor.text().replace(',', '')
        try:
            model.setData(index, int(text), Qt.EditRole)
        except:
            pass


# ===================================================================
# داده‌های چوب‌ها
# ===================================================================
WOOD_TYPES = {
    'کاج (Pine)':           {'density': 0.50, 'price': 1500, 'color': '#F5DEB3'},
    'راش (Beech)':          {'density': 0.70, 'price': 2200, 'color': '#DEB887'},
    'گردو (Walnut)':        {'density': 0.65, 'price': 4500, 'color': '#5C3317'},
    'تخته سه‌لایی (Plywood)': {'density': 0.60, 'price': 1800, 'color': '#D2B48C'},
    'MDF':                  {'density': 0.75, 'price': 1200, 'color': '#C19A6B'},
    'چوب روسی':             {'density': 0.45, 'price': 1000, 'color': '#EEDC82'},
    'بلوط (Oak)':           {'density': 0.75, 'price': 3500, 'color': '#8B4513'},
}


STRENGTH_LEVELS = {
    'سبک (تا 10 کیلوگرم)':         {'clearance': 2.0, 'min_thickness': 1.0, 'factor': 1.0},
    'متوسط (10 تا 30 کیلوگرم)':     {'clearance': 2.5, 'min_thickness': 1.5, 'factor': 1.3},
    'سنگین (30 تا 70 کیلوگرم)':     {'clearance': 3.0, 'min_thickness': 2.0, 'factor': 1.6},
    'بسیار سنگین (بالای 70 کیلوگرم)': {'clearance': 4.0, 'min_thickness': 2.5, 'factor': 2.0},
}


# ===================================================================
# اقلام مصالح با قیمت پیش‌فرض (ریال)
# ===================================================================
MATERIAL_ITEMS = [
    {'type': 'wood_per_cm3', 'name': 'چوب (هر cm³)', 'default_price': 1500, 'unit': 'cm³'},
    {'type': 'screw_4x40', 'name': 'پیچ 4×40', 'default_price': 500, 'unit': 'عدد'},
    {'type': 'screw_5x60', 'name': 'پیچ 5×60', 'default_price': 800, 'unit': 'عدد'},
    {'type': 'glue_per_kg', 'name': 'چسب چوب', 'default_price': 180000, 'unit': 'kg'},
    {'type': 'hinge_pair', 'name': 'لولا فلزی', 'default_price': 45000, 'unit': 'جفت'},
    {'type': 'handle', 'name': 'دستگیره فلزی', 'default_price': 65000, 'unit': 'عدد'},
    {'type': 'lock_set', 'name': 'قفل و کلید', 'default_price': 120000, 'unit': 'ست'},
    {'type': 'metal_bracket', 'name': 'نبشی فلزی', 'default_price': 25000, 'unit': 'عدد'},
    {'type': 'sandpaper_120', 'name': 'سمباده 120', 'default_price': 15000, 'unit': 'برگ'},
    {'type': 'sandpaper_220', 'name': 'سمباده 220', 'default_price': 18000, 'unit': 'برگ'},
    {'type': 'labor_per_hour', 'name': 'دستمزد ساعتی (نرخ هر ساعت یک کارگر)', 'default_price': 200000, 'unit': 'ریال/ساعت'},
    {'type': 'labor_hours', 'name': 'تعداد ساعت کار', 'default_price': 6, 'unit': 'ساعت'},
    {'type': 'labor_workers', 'name': 'تعداد کارگر', 'default_price': 1, 'unit': 'نفر'},
    {'type': 'profit_margin_percent', 'name': 'حاشیه سود', 'default_price': 25, 'unit': 'درصد'},
]


# ===================================================================
# فرم اصلی
# ===================================================================
class BoxDesignCalculator(QDialog):
    def __init__(self, db=None, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.user_id = user_data.get('id') if user_data else None
        if not self.user_id:
            self.user_id = 1
        self.setWindowTitle('ابزار طراحی و محاسبه جعبه چوبی')
        self.resize(1300, 900)
        self.setLayoutDirection(Qt.RightToLeft)
        self.last_result = None
        self.material_prices = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # هدر
        header = QFrame()
        header.setObjectName('Card')
        h_layout = QVBoxLayout(header)
        title = QLabel('ابزار طراحی و محاسبه جعبه چوبی حمل‌ونقل')
        title.setObjectName('Title')
        subtitle = QLabel('ابعاد物品 را وارد کنید - محاسبه ابعاد، نقشه فنی سه‌نما و قیمت نهایی به صورت خودکار')
        subtitle.setObjectName('Muted')
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        root.addWidget(header)

        # بخش ورودی‌ها
        input_group = QGroupBox('مشخصات物品 و جعبه')
        input_layout = QFormLayout(input_group)
        input_layout.setSpacing(10)

        dims_layout = QHBoxLayout()
        self.length_input = QDoubleSpinBox()
        self.length_input.setRange(1, 500); self.length_input.setValue(60)
        self.length_input.setSuffix(' cm'); self.length_input.setDecimals(1)

        self.width_input = QDoubleSpinBox()
        self.width_input.setRange(1, 500); self.width_input.setValue(45)
        self.width_input.setSuffix(' cm'); self.width_input.setDecimals(1)

        self.height_input = QDoubleSpinBox()
        self.height_input.setRange(1, 500); self.height_input.setValue(35)
        self.height_input.setSuffix(' cm'); self.height_input.setDecimals(1)

        dims_layout.addWidget(QLabel('طول物品:')); dims_layout.addWidget(self.length_input)
        dims_layout.addWidget(QLabel('عرض物品:')); dims_layout.addWidget(self.width_input)
        dims_layout.addWidget(QLabel('ارتفاع物品:')); dims_layout.addWidget(self.height_input)
        input_layout.addRow('ابعاد物品:', dims_layout)

        weight_layout = QHBoxLayout()
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0.1, 1000); self.weight_input.setValue(20)
        self.weight_input.setSuffix(' kg'); self.weight_input.setDecimals(1)
        weight_layout.addWidget(QLabel('وزن物品:')); weight_layout.addWidget(self.weight_input)
        weight_layout.addStretch()
        input_layout.addRow(weight_layout)

        count_layout = QHBoxLayout()
        self.count_input = QSpinBox()
        self.count_input.setRange(1, 100); self.count_input.setValue(1)
        count_layout.addWidget(QLabel('تعداد物品 در هر جعبه:')); count_layout.addWidget(self.count_input)
        count_layout.addStretch()
        input_layout.addRow(count_layout)

        self.strength_combo = QComboBox()
        for key in STRENGTH_LEVELS.keys():
            self.strength_combo.addItem(key)
        self.strength_combo.setCurrentIndex(1)
        input_layout.addRow('سطح استقامت:', self.strength_combo)

        self.wood_combo = QComboBox()
        for key in WOOD_TYPES.keys():
            self.wood_combo.addItem(key)
        input_layout.addRow('نوع چوب:', self.wood_combo)

        thickness_layout = QHBoxLayout()
        self.thickness_input = QDoubleSpinBox()
        self.thickness_input.setRange(0, 5); self.thickness_input.setValue(0)
        self.thickness_input.setSuffix(' cm'); self.thickness_input.setDecimals(1)
        thickness_layout.addWidget(self.thickness_input)
        thickness_layout.addWidget(QLabel('(0 = محاسبه خودکار)'))
        thickness_layout.addStretch()
        input_layout.addRow('ضخامت چوب دلخواه:', thickness_layout)
        self.box_warehouse_combo = QComboBox()
        input_layout.addRow('انبار مقصد:', self.box_warehouse_combo)
        self._load_box_warehouses()
        root.addWidget(input_group)

        # دکمه‌ها
        btn_row = QHBoxLayout()
        calc_btn = QPushButton('🧮 محاسبه و تولید نقشه فنی')
        calc_btn.setObjectName('PrimaryButton')
        calc_btn.setMinimumHeight(50)
        calc_btn.setFont(QFont('Tahoma', 12, QFont.Bold))
        calc_btn.clicked.connect(self._calculate)
        btn_row.addWidget(calc_btn)

        print_btn = QPushButton('️ چاپ نقشه فنی')
        print_btn.setObjectName('SecondaryButton')
        print_btn.setMinimumHeight(50)
        print_btn.clicked.connect(self._print_result)
        btn_row.addWidget(print_btn)

        export_btn = QPushButton(' خروجی SVG')
        export_btn.setObjectName('SecondaryButton')
        export_btn.setMinimumHeight(50)
        export_btn.clicked.connect(self._export_html)
        btn_row.addWidget(export_btn)

        # ✅ دکمه ثبت تولید در انبار
        save_btn = QPushButton('💾 ذخیره در انبار')
        save_btn.setObjectName('SuccessButton')
        save_btn.setMinimumHeight(50)
        save_btn.setFont(QFont('Tahoma', 12, QFont.Bold))
        save_btn.clicked.connect(self._save_production)
        save_btn.setEnabled(False)
        self.save_inventory_btn = save_btn
        btn_row.addWidget(save_btn)



        self.pallet_price_combo = QComboBox()
        self.pallet_price_combo.addItem('قیمت مبنا: بهای تمام‌شده', 'cost')
        self.pallet_price_combo.addItem('قیمت مبنا: قیمت فروش', 'sale')
        btn_row.addWidget(self.pallet_price_combo)

        btn_row.addStretch()
        root.addLayout(btn_row)

        # تب‌های خروجی
        self.tabs = QTabWidget()


        # تب ۱: نتایج محاسبه
        result_tab = QWidget()
        result_layout = QVBoxLayout(result_tab)
        result_scroll = QScrollArea()
        result_scroll.setWidgetResizable(True)
        result_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        result_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.result_browser = QTextBrowser()
        self.result_browser.setOpenExternalLinks(False)
        self.result_browser.setMinimumSize(600, 500)
        result_scroll.setWidget(self.result_browser)
        result_layout.addWidget(result_scroll)
        self.tabs.addTab(result_tab, 'نتایج محاسبه')

        # تب ۲: نقشه فنی سه‌نما
        drawing_tab = QWidget()
        drawing_layout = QVBoxLayout(drawing_tab)
        drawing_scroll = QScrollArea()
        drawing_scroll.setWidgetResizable(True)
        drawing_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        drawing_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.drawing_browser = QTextBrowser()
        self.drawing_browser.setOpenExternalLinks(False)
        self.drawing_browser.setMinimumSize(800, 600)
        drawing_scroll.setWidget(self.drawing_browser)
        drawing_layout.addWidget(drawing_scroll)
        self.tabs.addTab(drawing_tab, 'نقشه فنی سه‌نما')

        # تب ۳: لیست قطعات
        parts_tab = QWidget()
        parts_layout = QVBoxLayout(parts_tab)
        self.parts_table = QTableWidget(0, 6)
        self.parts_table.setHorizontalHeaderLabels([
            'ردیف', 'نام قطعه', 'تعداد', 'طول (cm)', 'عرض (cm)', 'ضخامت (cm)'
        ])
        self.parts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.parts_table.verticalHeader().setVisible(False)
        parts_layout.addWidget(self.parts_table)
        self.tabs.addTab(parts_tab, 'لیست قطعات')

        # تب ۴: دستور ساخت
        guide_tab = QWidget()
        guide_layout = QVBoxLayout(guide_tab)
        guide_scroll = QScrollArea()
        guide_scroll.setWidgetResizable(True)
        guide_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        guide_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.guide_browser = QTextBrowser()
        self.guide_browser.setOpenExternalLinks(False)
        self.guide_browser.setMinimumSize(600, 500)
        guide_scroll.setWidget(self.guide_browser)
        guide_layout.addWidget(guide_scroll)
        self.tabs.addTab(guide_tab, 'دستور ساخت')

        # تب ۵: مدیریت قیمت مصالح
        prices_tab = QWidget()
        prices_layout = QVBoxLayout(prices_tab)
        
        prices_header = QLabel('مدیریت قیمت مصالح (ریال)')
        prices_header.setObjectName('Title')
        prices_layout.addWidget(prices_header)
        
        prices_info = QLabel('قیمت‌ها به ازای هر کاربر ذخیره می‌شوند. آخرین قیمت ذخیره‌شده هنگام محاسبه استفاده می‌شود.')
        prices_info.setObjectName('Muted')
        prices_layout.addWidget(prices_info)
        
        self.prices_table = QTableWidget(0, 4)
        self.prices_table.setHorizontalHeaderLabels([
            'ردیف', 'نام مصالح', 'قیمت / مقدار (ریال)', 'واحد'
        ])
        self.prices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.prices_table.verticalHeader().setVisible(False)
        self.prices_table.setItemDelegateForColumn(2, IntegerCommaDelegate(self.prices_table))
        prices_layout.addWidget(self.prices_table)
        
        save_prices_btn = QPushButton('💾 ذخیره قیمت‌ها')
        save_prices_btn.setObjectName('PrimaryButton')
        save_prices_btn.setMinimumHeight(45)
        save_prices_btn.clicked.connect(self._save_material_prices)
        prices_layout.addWidget(save_prices_btn)
        
        self.tabs.addTab(prices_tab, 'مدیریت قیمت مصالح')

        root.addWidget(self.tabs, stretch=1)
        
        # بارگذاری قیمت‌های ذخیره‌شده
        self._load_material_prices()

    def _load_box_warehouses(self):
        try:
            with self.db.connect() as conn:
                rows = conn.execute("SELECT id, code, name FROM warehouses WHERE is_active=1 ORDER BY code").fetchall()
            self.box_warehouse_combo.clear()
            self.box_warehouse_combo.addItem('-- انبار مقصد را انتخاب کنید --', None)
            for r in rows:
                self.box_warehouse_combo.addItem('{} | {}'.format(r[1] or '', r[2] or ''), r[0])
        except Exception:
            pass

    def _load_material_prices(self):
        """بارگذاری قیمت‌های ذخیره‌شده از دیتابیس"""
        try:
            if not self.db or not self.user_id:
                for item in MATERIAL_ITEMS:
                    self.material_prices[item['type']] = item['default_price']
                self._show_prices_in_table()
                return
            
            with self.db.connect() as conn:
                rows = conn.execute('''
                    SELECT material_type, price_per_unit
                    FROM box_material_prices
                    WHERE user_id = ?
                ''', (self.user_id,)).fetchall()
                
                for row in rows:
                    self.material_prices[row['material_type']] = row['price_per_unit']
                
                for item in MATERIAL_ITEMS:
                    if item['type'] not in self.material_prices:
                        self.material_prices[item['type']] = item['default_price']
        except Exception:
            for item in MATERIAL_ITEMS:
                self.material_prices[item['type']] = item['default_price']
        
        self._show_prices_in_table()

    def _show_prices_in_table(self):
        """نمایش قیمت‌ها در جدول با جداکننده هزارگان"""
        self.prices_table.setRowCount(len(MATERIAL_ITEMS))
        for i, item in enumerate(MATERIAL_ITEMS):
            price = self.material_prices.get(item['type'], item['default_price'])
            self.prices_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.prices_table.setItem(i, 1, QTableWidgetItem(item['name']))
            price_item = QTableWidgetItem(f"{price:,}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.prices_table.setItem(i, 2, price_item)
            self.prices_table.setItem(i, 3, QTableWidgetItem(item['unit']))

    def _save_material_prices(self):
        """ذخیره قیمت‌ها در دیتابیس"""
        new_prices = {}
        for i in range(self.prices_table.rowCount()):
            item_type = MATERIAL_ITEMS[i]['type']
            price_text = self.prices_table.item(i, 2).text().replace(',', '')
            try:
                price = int(price_text)
                if price < 0:
                    raise ValueError()
                new_prices[item_type] = price
            except:
                QMessageBox.warning(self, 'خطا', f'قیمت برای {MATERIAL_ITEMS[i]["name"]} نامعتبر است.')
                return
        
        if self.db and self.user_id:
            try:
                with self.db.connect() as conn:
                    for item_type, price in new_prices.items():
                        conn.execute('''
                            INSERT INTO box_material_prices (user_id, material_type, price_per_unit, unit)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(user_id, material_type) 
                            DO UPDATE SET price_per_unit = ?, updated_at = CURRENT_TIMESTAMP
                        ''', (self.user_id, item_type, price, 
                              next(item['unit'] for item in MATERIAL_ITEMS if item['type'] == item_type),
                              price))
            except Exception as e:
                QMessageBox.warning(self, 'خطا در دیتابیس', f'قیمت‌ها در حافظه ذخیره شدند ولی در دیتابیس خطا رخ داد:\n{e}')
        
        self.material_prices = new_prices.copy()
        self._show_prices_in_table()
        
        QMessageBox.information(self, 'موفق', 
            f'✅ {len(new_prices)} قیمت با موفقیت ذخیره شدند.\n'
            f'این قیمت‌ها در محاسبه بعدی استفاده خواهند شد.')

    def _get_price(self, material_type):
        """دریافت قیمت یک مصالح"""
        if material_type in self.material_prices:
            return self.material_prices[material_type]
        for item in MATERIAL_ITEMS:
            if item['type'] == material_type:
                return item['default_price']
        return 0

    def _get_company_info(self):
        """خواندن اطلاعات شرکت از دیتابیس"""
        info = {
            'name': 'شرکت انبار پالت',
            'phone': '-',
            'address': '-',
            'logo_text': 'شرکت انبار پالت'
        }
        if self.db:
            try:
                with self.db.connect() as conn:
                    row = conn.execute('''
                        SELECT company_name, phone, address 
                        FROM company_profile LIMIT 1
                    ''').fetchone()
                    if row:
                        info['name'] = row['company_name'] or info['name']
                        info['phone'] = row['phone'] or '-'
                        info['address'] = row['address'] or '-'
                        info['logo_text'] = info['name']
            except:
                pass
        return info

    def _calculate(self):
        """محاسبه کامل"""
        item_length = self.length_input.value()
        item_width = self.width_input.value()
        item_height = self.height_input.value()
        item_weight = self.weight_input.value()
        item_count = self.count_input.value()
        
        strength_key = self.strength_combo.currentText()
        strength = STRENGTH_LEVELS[strength_key]
        
        wood_key = self.wood_combo.currentText()
        wood = WOOD_TYPES[wood_key]
        
        manual_thickness = self.thickness_input.value()
        
        # ابعاد داخلی
        if item_count > 1:
            inner_length = (item_length * item_count) + (2 * strength['clearance'])
            inner_width = item_width + (2 * strength['clearance'])
            inner_height = item_height + strength['clearance']
        else:
            inner_length = item_length + (2 * strength['clearance'])
            inner_width = item_width + (2 * strength['clearance'])
            inner_height = item_height + strength['clearance']
        
        # ضخامت
        if manual_thickness > 0:
            thickness = manual_thickness
        else:
            total_weight = item_weight * item_count
            thickness = strength['min_thickness'] * strength['factor']
            if total_weight > 50:
                thickness += 0.5
            if total_weight > 100:
                thickness += 0.5
            thickness = round(thickness * 2) / 2
        
        # ابعاد خارجی
        outer_length = inner_length + (2 * thickness)
        outer_width = inner_width + (2 * thickness)
        outer_height = inner_height + (2 * thickness)
        
        # قطعات
        parts = [
            {'name': 'کف جعبه', 'count': 1, 'l': outer_length, 'w': outer_width, 't': thickness},
            {'name': 'درب جعبه', 'count': 1, 'l': outer_length, 'w': outer_width, 't': thickness},
            {'name': 'دیواره جلو', 'count': 1, 'l': outer_length, 'w': outer_height, 't': thickness},
            {'name': 'دیواره عقب', 'count': 1, 'l': outer_length, 'w': outer_height, 't': thickness},
            {'name': 'دیواره چپ', 'count': 1, 'l': outer_width - (2*thickness), 'w': outer_height, 't': thickness},
            {'name': 'دیواره راست', 'count': 1, 'l': outer_width - (2*thickness), 'w': outer_height, 't': thickness},
        ]
        
        # حجم و وزن چوب
        total_wood_volume = sum(p['l'] * p['w'] * p['t'] * p['count'] for p in parts)
        wood_weight = total_wood_volume * wood['density'] / 1000
        total_weight = wood_weight + (item_weight * item_count)
        
        # محاسبه قیمت
        wood_price_per_cm3 = self._get_price('wood_per_cm3')
        wood_cost = total_wood_volume * wood_price_per_cm3
        
        # محاسبه تعداد یراق مورد نیاز
        total_screws_4x40 = 24
        total_screws_5x60 = 6 if thickness > 1.5 else 0
        glue_kg = total_wood_volume / 50000
        hinges = 2
        handles = 2
        locks = 1
        brackets = 4
        sandpaper_120 = 1
        sandpaper_220 = 1
        
        # هزینه یراق‌آلات
        hardware_cost = (
            total_screws_4x40 * self._get_price('screw_4x40') +
            total_screws_5x60 * self._get_price('screw_5x60') +
            glue_kg * self._get_price('glue_per_kg') +
            hinges * self._get_price('hinge_pair') +
            handles * self._get_price('handle') +
            locks * self._get_price('lock_set') +
            brackets * self._get_price('metal_bracket') +
            sandpaper_120 * self._get_price('sandpaper_120') +
            sandpaper_220 * self._get_price('sandpaper_220')
        )
        
        labor_hours = self._get_price('labor_hours')
        labor_workers = self._get_price('labor_workers')
        labor_rate = self._get_price('labor_per_hour')
        labor_cost = labor_hours * labor_workers * labor_rate
        
        material_cost = wood_cost + hardware_cost
        subtotal = material_cost + labor_cost
        
        profit_margin = self._get_price('profit_margin_percent') / 100
        profit_amount = subtotal * profit_margin
        final_price = subtotal + profit_amount
        
        self.last_result = {
            'item_length': item_length, 'item_width': item_width, 'item_height': item_height,
            'item_weight': item_weight, 'item_count': item_count,
            'strength_key': strength_key, 'wood_key': wood_key,
            'wood_density': wood['density'],
            'thickness': thickness,
            'inner_length': inner_length, 'inner_width': inner_width, 'inner_height': inner_height,
            'outer_length': outer_length, 'outer_width': outer_width, 'outer_height': outer_height,
            'parts': parts,
            'wood_volume': total_wood_volume,
            'wood_weight': wood_weight,
            'total_weight': total_weight,
            'clearance': strength['clearance'],
            'wood_cost': wood_cost,
            'hardware_cost': hardware_cost,
            'labor_hours': labor_hours,
            'labor_workers': labor_workers,
            'labor_rate': labor_rate,
            'labor_cost': labor_cost,
            'material_cost': material_cost,
            'subtotal': subtotal,
            'profit_margin': profit_margin,
            'profit_amount': profit_amount,
            'final_price': final_price,
            'total_cost': subtotal,  # ✅ اضافه شد: بهای تمام‌شده = subtotal
            'total_screws_4x40': total_screws_4x40,
            'total_screws_5x60': total_screws_5x60,
            'glue_kg': glue_kg,
            'hinges': hinges,
            'handles': handles,
            'locks': locks,
            'brackets': brackets,
            'sandpaper_120': sandpaper_120,
            'sandpaper_220': sandpaper_220,
        }
        
        self._show_results()
        self._show_drawing()
        self._show_parts()
        self._show_guide()
        
        QMessageBox.information(self, 'موفق', 'محاسبه و نقشه فنی با موفقیت تولید شد!')
        
        # ✅ فعال کردن دکمه ثبت در انبار
        if hasattr(self, 'save_inventory_btn'):
            self.save_inventory_btn.setEnabled(True)
    def _format_price(self, price):
        return f"{price:,.0f} ریال"

    def _show_results(self):
        r = self.last_result
        html = f'''
<html dir="rtl" lang="fa"><head><meta charset="utf-8">
<style>
    body {{ font-family: Tahoma; padding: 20px; background: #ffffff; color: #000000; }}
    h2 {{ color: #000000; border-bottom: 3px solid #2563eb; padding-bottom: 10px; font-size: 22px; }}
    h3 {{ color: #000000; margin-top: 20px; font-size: 18px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 15px 0; background: #ffffff; border: 1px solid #333; }}
    th, td {{ border: 1px solid #555; padding: 10px; text-align: center; color: #000000; font-size: 14px; }}
    th {{ background: #2563eb; color: #ffffff; font-weight: bold; }}
    .highlight {{ background: #dbeafe; font-weight: bold; color: #000000; }}
    .box {{ background: #ffffff; padding: 15px; margin: 10px 0; border-radius: 8px; border: 2px solid #2563eb; }}
    .cost {{ background: #fef3c7; border: 2px solid #f59e0b; }}
    .cost td {{ color: #000000; }}
    .metric {{ display: inline-block; padding: 10px 15px; margin: 5px; background: #f1f5f9; border-radius: 5px; color: #000000; }}
    .metric b {{ color: #000000; font-size: 16px; }}
    .final-price {{ font-size: 28px; color: #16a34a; font-weight: bold; }}
</style></head><body>

<h2>نتایج محاسبه جعبه چوبی</h2>

<div class="box">
    <h3>اطلاعات ورودی</h3>
    <table>
        <tr><th>مشخصه</th><th>مقدار</th></tr>
        <tr><td>ابعاد物品</td><td>{r['item_length']} × {r['item_width']} × {r['item_height']} cm</td></tr>
        <tr><td>وزن物品</td><td>{r['item_weight']} kg</td></tr>
        <tr><td>تعداد</td><td>{r['item_count']} عدد</td></tr>
        <tr><td>استقامت</td><td>{r['strength_key']}</td></tr>
        <tr><td>چوب</td><td>{r['wood_key']} (چگالی: {r['wood_density']} g/cm³)</td></tr>
    </table>
</div>

<div class="box highlight">
    <h3>ابعاد داخلی</h3>
    <div class="metric"><b>طول:</b> {r['inner_length']:.1f} cm</div>
    <div class="metric"><b>عرض:</b> {r['inner_width']:.1f} cm</div>
    <div class="metric"><b>ارتفاع:</b> {r['inner_height']:.1f} cm</div>
</div>

<div class="box" style="border-right-color:#16a34a">
    <h3>ابعاد خارجی</h3>
    <div class="metric"><b>طول:</b> {r['outer_length']:.1f} cm</div>
    <div class="metric"><b>عرض:</b> {r['outer_width']:.1f} cm</div>
    <div class="metric"><b>ارتفاع:</b> {r['outer_height']:.1f} cm</div>
</div>

<div class="box cost">
    <h3>محاسبه قیمت نهایی</h3>
    <table>
        <tr><th>ردیف</th><th>سرفصل</th><th>مبلغ (ریال)</th></tr>
        <tr><td>1</td><td>هزینه چوب ({r['wood_volume']/1000:.3f} لیتر)</td><td>{self._format_price(r['wood_cost'])}</td></tr>
        <tr><td>2</td><td>یراق‌آلات (پیچ، چسب، لولا، ...)</td><td>{self._format_price(r['hardware_cost'])}</td></tr>
        <tr><td>3</td><td>دستمزد ({r['labor_hours']} ساعت × {r['labor_workers']} کارگر × {self._format_price(r['labor_rate'])})</td><td>{self._format_price(r['labor_cost'])}</td></tr>
        <tr style="background:#fef3c7"><td colspan="2"><b>جمع کل هزینه‌ها</b></td><td><b>{self._format_price(r['subtotal'])}</b></td></tr>
        <tr><td>4</td><td>سود ({r['profit_margin']*100:.0f}%)</td><td>{self._format_price(r['profit_amount'])}</td></tr>
        <tr class="highlight"><td colspan="2" style="font-size:18px"><b>مبلغ نهایی</b></td><td class="final-price">{self._format_price(r['final_price'])}</td></tr>
    </table>
</div>

</body></html>'''
        self.result_browser.setHtml(html)

    def _build_svg_drawing(self):
        """ساخت SVG کامل برای چاپ و خروجی"""
        r = self.last_result
        company = self._get_company_info()
        date_str = QDate.currentDate().toString('yyyy-MM-dd')
        
        L = r['outer_length']
        W = r['outer_width']
        H = r['outer_height']
        T = r['thickness']
        
        scale = 4
        sL, sW, sH = int(L*scale), int(W*scale), int(H*scale)
        sT = int(T*scale)
        wood_color = WOOD_TYPES[r['wood_key']]['color']
        
        total_w, total_h = 1000, 750
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" width="{total_w}" height="{total_h}">
<defs><style>text {{ font-family: Tahoma, Arial, sans-serif; }}</style></defs>
<rect width="100%" height="100%" fill="white"/>

<rect x="20" y="10" width="{total_w-40}" height="90" fill="#46505f" rx="8"/>
<text x="{total_w/2}" y="38" text-anchor="middle" font-size="22" font-weight="bold" fill="white">{company['logo_text']}</text>
<text x="{total_w/2}" y="60" text-anchor="middle" font-size="13" fill="#cbd5e1">نقشه فنی جعبه چوبی حمل‌ونقل</text>
<text x="{total_w/2}" y="78" text-anchor="middle" font-size="11" fill="#64748b">شماره سفارش: BOX-{date_str.replace("-","")} | تاریخ: {date_str}</text>
<text x="{total_w/2}" y="95" text-anchor="middle" font-size="10" fill="#64748b">تلفن: {company['phone']} | {company['address'][:70]}</text>

<text x="{total_w/2}" y="130" text-anchor="middle" font-size="15" font-weight="bold" fill="#46505f">ابعاد خارجی: {L:.1f} × {W:.1f} × {H:.1f} cm | چوب: {r['wood_key']} | ضخامت: {T:.1f} cm</text>

<g transform="translate(80, 160)">
    <text x="{sL/2}" y="-10" text-anchor="middle" font-size="12" font-weight="bold" fill="#46505f">نمای روبرو</text>
    <rect x="0" y="0" width="{sL}" height="{sH}" fill="{wood_color}" stroke="#46505f" stroke-width="2"/>
    <rect x="{sT}" y="{sT}" width="{sL-2*sT}" height="{sH-2*sT}" fill="none" stroke="#46505f" stroke-width="1" stroke-dasharray="4,2"/>
    <line x1="0" y1="{sH+15}" x2="{sL}" y2="{sH+15}" stroke="#2563eb" stroke-width="2"/>
    <polygon points="0,{sH+15} 6,{sH+11} 6,{sH+19}" fill="#2563eb"/>
    <polygon points="{sL},{sH+15} {sL-6},{sH+11} {sL-6},{sH+19}" fill="#2563eb"/>
    <text x="{sL/2}" y="{sH+32}" text-anchor="middle" font-size="11" font-weight="bold" fill="#2563eb">{L:.1f} cm</text>
    <line x1="{sL+15}" y1="0" x2="{sL+15}" y2="{sH}" stroke="#dc2626" stroke-width="2"/>
    <polygon points="{sL+15},0 {sL+11},6 {sL+19},6" fill="#dc2626"/>
    <polygon points="{sL+15},{sH} {sL+11},{sH-6} {sL+19},{sH-6}" fill="#dc2626"/>
    <text x="{sL+35}" y="{sH/2}" font-size="11" font-weight="bold" fill="#dc2626" transform="rotate(90 {sL+35} {sH/2})">{H:.1f} cm</text>
</g>

<g transform="translate({80+sL+60}, 160)">
    <text x="{sW/2}" y="-10" text-anchor="middle" font-size="12" font-weight="bold" fill="#46505f">نمای بغل</text>
    <rect x="0" y="0" width="{sW}" height="{sH}" fill="{wood_color}" stroke="#46505f" stroke-width="2"/>
    <rect x="{sT}" y="{sT}" width="{sW-2*sT}" height="{sH-2*sT}" fill="none" stroke="#46505f" stroke-width="1" stroke-dasharray="4,2"/>
    <line x1="0" y1="{sH+15}" x2="{sW}" y2="{sH+15}" stroke="#2563eb" stroke-width="2"/>
    <polygon points="0,{sH+15} 6,{sH+11} 6,{sH+19}" fill="#2563eb"/>
    <polygon points="{sW},{sH+15} {sW-6},{sH+11} {sW-6},{sH+19}" fill="#2563eb"/>
    <text x="{sW/2}" y="{sH+32}" text-anchor="middle" font-size="11" font-weight="bold" fill="#2563eb">{W:.1f} cm</text>
    <line x1="{sW+15}" y1="0" x2="{sW+15}" y2="{sH}" stroke="#dc2626" stroke-width="2"/>
    <polygon points="{sW+15},0 {sW+11},6 {sW+19},6" fill="#dc2626"/>
    <polygon points="{sW+15},{sH} {sW+11},{sH-6} {sW+19},{sH-6}" fill="#dc2626"/>
    <text x="{sW+35}" y="{sH/2}" font-size="11" font-weight="bold" fill="#dc2626" transform="rotate(90 {sW+35} {sH/2})">{H:.1f} cm</text>
</g>

<g transform="translate({80+2*(sL+60)}, 160)">
    <text x="{sL/2}" y="-10" text-anchor="middle" font-size="12" font-weight="bold" fill="#46505f">نمای بالا (درب)</text>
    <rect x="0" y="0" width="{sL}" height="{sW}" fill="{wood_color}" stroke="#46505f" stroke-width="2"/>
    <rect x="{sT}" y="{sT}" width="{sL-2*sT}" height="{sW-2*sT}" fill="none" stroke="#46505f" stroke-width="1" stroke-dasharray="4,2"/>
    <text x="{sL/2}" y="{sW/2+5}" text-anchor="middle" font-size="14" font-weight="bold" fill="#46505f" opacity="0.4">درب</text>
    <line x1="0" y1="{sW+15}" x2="{sL}" y2="{sW+15}" stroke="#2563eb" stroke-width="2"/>
    <polygon points="0,{sW+15} 6,{sW+11} 6,{sW+19}" fill="#2563eb"/>
    <polygon points="{sL},{sW+15} {sL-6},{sW+11} {sL-6},{sW+19}" fill="#2563eb"/>
    <text x="{sL/2}" y="{sW+32}" text-anchor="middle" font-size="11" font-weight="bold" fill="#2563eb">{L:.1f} cm</text>
    <line x1="{sL+15}" y1="0" x2="{sL+15}" y2="{sW}" stroke="#dc2626" stroke-width="2"/>
    <polygon points="{sL+15},0 {sL+11},6 {sL+19},6" fill="#dc2626"/>
    <polygon points="{sL+15},{sW} {sL+11},{sW-6} {sL+19},{sW-6}" fill="#dc2626"/>
    <text x="{sL+35}" y="{sW/2}" font-size="11" font-weight="bold" fill="#dc2626" transform="rotate(90 {sL+35} {sW/2})">{W:.1f} cm</text>
</g>

<g transform="translate(50, 520)">
    <rect x="0" y="0" width="{total_w-100}" height="180" fill="#f8fafc" stroke="#5b6675" stroke-width="2" rx="8"/>
    <text x="{(total_w-100)/2}" y="25" text-anchor="middle" font-size="15" font-weight="bold" fill="#46505f">صورتحساب ساخت جعبه چوبی</text>
    <line x1="20" y1="35" x2="{total_w-120}" y2="35" stroke="#5b6675"/>
    
    <text x="30" y="60" font-size="12" fill="#5b6675">هزینه چوب {r['wood_key']}:</text>
    <text x="{total_w-130}" y="60" text-anchor="end" font-size="12" font-weight="bold" fill="#46505f">{self._format_price(r['wood_cost'])}</text>
    
    <text x="30" y="85" font-size="12" fill="#5b6675">یراق‌آلات:</text>
    <text x="{total_w-130}" y="85" text-anchor="end" font-size="12" font-weight="bold" fill="#46505f">{self._format_price(r['hardware_cost'])}</text>
    
    <text x="30" y="110" font-size="12" fill="#5b6675">دستمزد ({r['labor_hours']} ساعت × {r['labor_workers']} کارگر × {self._format_price(r['labor_rate'])}):</text>
    <text x="{total_w-130}" y="110" text-anchor="end" font-size="12" font-weight="bold" fill="#46505f">{self._format_price(r['labor_cost'])}</text>
    
    <line x1="20" y1="120" x2="{total_w-120}" y2="120" stroke="#5b6675" stroke-width="0.5"/>
    
    <text x="30" y="140" font-size="12" fill="#5b6675">جمع هزینه‌ها:</text>
    <text x="{total_w-130}" y="140" text-anchor="end" font-size="13" font-weight="bold" fill="#46505f">{self._format_price(r['subtotal'])}</text>
    
    <text x="30" y="160" font-size="12" fill="#5b6675">سود ({r['profit_margin']*100:.0f}%):</text>
    <text x="{total_w-130}" y="160" text-anchor="end" font-size="12" fill="#6b7280">{self._format_price(r['profit_amount'])}</text>
    
    <rect x="10" y="168" width="{total_w-140}" height="25" fill="#dcfce7" rx="4"/>
    <text x="30" y="186" font-size="14" font-weight="bold" fill="#16a34a">مبلغ نهایی:</text>
    <text x="{total_w-130}" y="186" text-anchor="end" font-size="16" font-weight="bold" fill="#16a34a">{self._format_price(r['final_price'])}</text>
</g>

<text x="{total_w/2}" y="{total_h-15}" text-anchor="middle" font-size="10" fill="#6b7280">
سیستم انبار پالت | وزن جعبه: {r['wood_weight']:.2f} kg | وزن کل: {r['total_weight']:.2f} kg
</text>
</svg>'''

    def _show_drawing(self):
        """نمایش table-based ساده در QTextBrowser"""
        r = self.last_result
        company = self._get_company_info()
        date_str = QDate.currentDate().toString('yyyy-MM-dd')
        
        L = r['outer_length']
        W = r['outer_width']
        H = r['outer_height']
        T = r['thickness']
        wood_color = WOOD_TYPES[r['wood_key']]['color']
        
        html = f'''<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head><meta charset="utf-8">
<style>
    body {{ font-family: Tahoma; margin: 15px; background: white; color: #000; }}
    table {{ border-collapse: collapse; width: 100%; }}
    .header {{ background: #46505f; color: white; }}
    .header td {{ padding: 10px; text-align: center; }}
    .name {{ font-size: 22px; font-weight: bold; }}
    .title {{ font-size: 13px; color: #cbd5e1; }}
    .meta {{ font-size: 11px; color: #64748b; }}
    .dims {{ background: #f1f5f9; padding: 10px; text-align: center; font-weight: bold; font-size: 14px; margin: 15px 0; }}
    .view {{ text-align: center; padding: 10px; vertical-align: top; }}
    .label {{ font-weight: bold; color: #46505f; margin-bottom: 5px; font-size: 12px; }}
    .box {{ background: {wood_color}; border: 3px solid #46505f; display: inline-block; }}
    .dim {{ font-size: 11px; font-weight: bold; margin-top: 5px; color: #000; }}
    .dim-blue {{ color: #2563eb; }}
    .dim-red {{ color: #dc2626; }}
    .price {{ margin-top: 20px; border: 2px solid #5b6675; }}
    .price th {{ background: #5b6675; color: white; padding: 8px; }}
    .price td {{ padding: 6px; border: 1px solid #e2e8f0; color: #000; }}
    .total {{ background: #dcfce7; font-size: 16px; font-weight: bold; color: #16a34a; }}
    .btn {{ display: block; margin: 15px auto; padding: 12px 30px; background: #2563eb; color: white; 
            border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; text-decoration: none; text-align: center; width: 300px; }}
</style></head><body>

<table class="header">
    <tr><td class="name">{company['logo_text']}</td></tr>
    <tr><td class="title">نقشه فنی جعبه چوبی حمل‌ونقل</td></tr>
    <tr><td class="meta">شماره سفارش: BOX-{date_str.replace("-","")} | تاریخ: {date_str}</td></tr>
    <tr><td class="meta">تلفن: {company['phone']} | {company['address'][:80]}</td></tr>
</table>

<div class="dims">
    ابعاد خارجی: {L:.1f} × {W:.1f} × {H:.1f} cm | چوب: {r['wood_key']} | ضخامت: {T:.1f} cm
</div>

<table>
    <tr>
        <td class="view">
            <div class="label">نمای روبرو</div>
            <div class="box" style="width:{int(L*3)}px; height:{int(H*3)}px;"></div>
            <div class="dim dim-blue">طول: {L:.1f} cm</div>
            <div class="dim dim-red">ارتفاع: {H:.1f} cm</div>
        </td>
        <td class="view">
            <div class="label">نمای بغل</div>
            <div class="box" style="width:{int(W*3)}px; height:{int(H*3)}px;"></div>
            <div class="dim dim-blue">عرض: {W:.1f} cm</div>
            <div class="dim dim-red">ارتفاع: {H:.1f} cm</div>
        </td>
        <td class="view">
            <div class="label">نمای بالا (درب)</div>
            <div class="box" style="width:{int(L*3)}px; height:{int(W*3)}px;"></div>
            <div class="dim dim-blue">{L:.1f} × {W:.1f} cm</div>
        </td>
    </tr>
</table>

<table class="price">
    <tr><th colspan="2">صورتحساب ساخت جعبه چوبی</th></tr>
    <tr><td>هزینه چوب {r['wood_key']}:</td><td>{self._format_price(r['wood_cost'])}</td></tr>
    <tr><td>یراق‌آلات:</td><td>{self._format_price(r['hardware_cost'])}</td></tr>
    <tr><td>دستمزد ({r['labor_hours']} ساعت × {r['labor_workers']} کارگر):</td><td>{self._format_price(r['labor_cost'])}</td></tr>
    <tr style="background:#fef3c7"><td><b>جمع هزینه‌ها:</b></td><td><b>{self._format_price(r['subtotal'])}</b></td></tr>
    <tr><td>سود ({r['profit_margin']*100:.0f}%):</td><td>{self._format_price(r['profit_amount'])}</td></tr>
    <tr class="total"><td>مبلغ نهایی:</td><td>{self._format_price(r['final_price'])}</td></tr>
</table>

<a class="btn" href="file://{{TEMP_SVG}}">مشاهده نقشه فنی کامل با SVG در مرورگر</a>

</body></html>'''
        
        svg_content = self._build_svg_drawing()
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', prefix='box_', delete=False, encoding='utf-8')
        tmp.write(svg_content)
        tmp.close()
        svg_path = tmp.name
        
        html = html.replace('{{TEMP_SVG}}', svg_path)
        self.drawing_browser.setHtml(html)

    def _show_parts(self):
        r = self.last_result
        self.parts_table.setRowCount(len(r['parts']))
        for i, p in enumerate(r['parts']):
            self.parts_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.parts_table.setItem(i, 1, QTableWidgetItem(p['name']))
            self.parts_table.setItem(i, 2, QTableWidgetItem(str(p['count'])))
            self.parts_table.setItem(i, 3, QTableWidgetItem(f"{p['l']:.1f}"))
            self.parts_table.setItem(i, 4, QTableWidgetItem(f"{p['w']:.1f}"))
            self.parts_table.setItem(i, 5, QTableWidgetItem(f"{p['t']:.1f}"))

    def _show_guide(self):
        r = self.last_result
        company = self._get_company_info()
        html = f'''
<html dir="rtl" lang="fa"><head><meta charset="utf-8">
<style>
    body {{ font-family: Tahoma; padding: 20px; background: #f8fafc; color: #000; }}
    h2 {{ color: #000; border-bottom: 3px solid #2563eb; padding-bottom: 10px; }}
    h3 {{ color: #000; margin-top: 20px; }}
    .step {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-right: 5px solid #2563eb; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    .step-num {{ display: inline-block; width: 30px; height: 30px; background: #2563eb; color: white; border-radius: 50%; text-align: center; line-height: 30px; font-weight: bold; margin-left: 10px; }}
    .warning {{ background: #fef3c7; border-right-color: #f59e0b; }}
    .material {{ background: #dbeafe; border-right-color: #3b82f6; }}
    ul {{ padding-right: 20px; }}
    li {{ margin: 5px 0; color: #000; }}
    table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px; text-align: center; color: #000; }}
    th {{ background: #5b6675; color: white; }}
    .total {{ background: #dcfce7; font-weight: bold; font-size: 14px; }}
</style></head><body>

<h2>دستور ساخت جعبه چوبی - {company['logo_text']}</h2>

<div class="material">
    <h3>لیست مصالح و یراق‌آلات</h3>
    <table>
        <tr><th>ردیف</th><th>قطعه</th><th>تعداد</th><th>قیمت واحد</th><th>مجموع</th></tr>
        <tr><td>1</td><td>ورق چوب {r['wood_key']} ({r['wood_volume']/1000:.3f} لیتر)</td><td>1 ورق</td><td>-</td><td>{self._format_price(r['wood_cost'])}</td></tr>
        <tr><td>2</td><td>پیچ چوب 4×40</td><td>{r['total_screws_4x40']} عدد</td><td>{self._format_price(self._get_price('screw_4x40'))}</td><td>{self._format_price(r['total_screws_4x40'] * self._get_price('screw_4x40'))}</td></tr>
        <tr><td>3</td><td>پیچ چوب 5×60</td><td>{r['total_screws_5x60']} عدد</td><td>{self._format_price(self._get_price('screw_5x60'))}</td><td>{self._format_price(r['total_screws_5x60'] * self._get_price('screw_5x60'))}</td></tr>
        <tr><td>4</td><td>چسب چوب</td><td>{r['glue_kg']:.2f} kg</td><td>{self._format_price(self._get_price('glue_per_kg'))}</td><td>{self._format_price(r['glue_kg'] * self._get_price('glue_per_kg'))}</td></tr>
        <tr><td>5</td><td>لولا فلزی</td><td>{r['hinges']} جفت</td><td>{self._format_price(self._get_price('hinge_pair'))}</td><td>{self._format_price(r['hinges'] * self._get_price('hinge_pair'))}</td></tr>
        <tr><td>6</td><td>دستگیره</td><td>{r['handles']} عدد</td><td>{self._format_price(self._get_price('handle'))}</td><td>{self._format_price(r['handles'] * self._get_price('handle'))}</td></tr>
        <tr><td>7</td><td>قفل و کلید</td><td>{r['locks']} ست</td><td>{self._format_price(self._get_price('lock_set'))}</td><td>{self._format_price(r['locks'] * self._get_price('lock_set'))}</td></tr>
        <tr><td>8</td><td>نبشی فلزی</td><td>{r['brackets']} عدد</td><td>{self._format_price(self._get_price('metal_bracket'))}</td><td>{self._format_price(r['brackets'] * self._get_price('metal_bracket'))}</td></tr>
        <tr><td>9</td><td>سمباده 120</td><td>{r['sandpaper_120']} برگ</td><td>{self._format_price(self._get_price('sandpaper_120'))}</td><td>{self._format_price(r['sandpaper_120'] * self._get_price('sandpaper_120'))}</td></tr>
        <tr><td>10</td><td>سمباده 220</td><td>{r['sandpaper_220']} برگ</td><td>{self._format_price(self._get_price('sandpaper_220'))}</td><td>{self._format_price(r['sandpaper_220'] * self._get_price('sandpaper_220'))}</td></tr>
        <tr><td>11</td><td>دستمزد ({r['labor_hours']} ساعت × {r['labor_workers']} کارگر)</td><td>{r['labor_hours'] * r['labor_workers']} ساعت</td><td>{self._format_price(self._get_price('labor_per_hour'))}</td><td>{self._format_price(r['labor_cost'])}</td></tr>
        <tr class="total"><td colspan="4">جمع کل یراق‌آلات + دستمزد</td><td>{self._format_price(r['hardware_cost'] + r['labor_cost'])}</td></tr>
    </table>
</div>

<div class="step"><h3><span class="step-num">1</span>برش قطعات</h3>
<table>
<tr><th>قطعه</th><th>تعداد</th><th>طول (cm)</th><th>عرض (cm)</th><th>ضخامت (cm)</th></tr>
<tr><td>کف و درب</td><td>2</td><td>{r['outer_length']:.1f}</td><td>{r['outer_width']:.1f}</td><td>{r['thickness']:.1f}</td></tr>
<tr><td>دیواره جلو/عقب</td><td>2</td><td>{r['outer_length']:.1f}</td><td>{r['outer_height']:.1f}</td><td>{r['thickness']:.1f}</td></tr>
<tr><td>دیواره چپ/راست</td><td>2</td><td>{r['outer_width'] - 2*r['thickness']:.1f}</td><td>{r['outer_height']:.1f}</td><td>{r['thickness']:.1f}</td></tr>
</table>
</div>

<div class="step"><h3><span class="step-num">2</span>سنباده‌زنی اولیه</h3><ul>
<li>تمام قطعات را با سمباده 120 سنباده بزنید</li>
<li>سپس با سمباده 220 سطح را یکدست کنید</li>
<li>لبه‌های تیز را گرد کنید</li>
</ul></div>

<div class="step"><h3><span class="step-num">3</span>مونتاژ دیواره‌ها</h3><ul>
<li>دیواره جلو و عقب را روی سطح صاف قرار دهید</li>
<li>دیواره چپ را بین آنها با پیچ و چسب محکم کنید (3 پیچ در هر گوشه)</li>
<li>دیواره راست را نیز به همین روش نصب کنید</li>
</ul></div>

<div class="step"><h3><span class="step-num">4</span>نصب کف</h3><ul>
<li>قاب دیواره‌ها را روی قطعه کف قرار دهید</li>
<li>از داخل با پیچ‌های 4×40 محکم کنید</li>
</ul></div>

<div class="step"><h3><span class="step-num">5</span>نصب یراق‌آلات</h3><ul>
<li>دستگیره‌ها را روی دیواره‌های چپ و راست نصب کنید</li>
<li>لولاها را به دیواره عقب و درب نصب کنید</li>
<li>قفل را در جلو قرار دهید</li>
</ul></div>

<div class="step warning"><h3><span class="step-num">!</span>نکات ایمنی</h3><ul>
<li>هنگام برش از عینک و ماسک استفاده کنید</li>
<li>پیچ‌ها را بیش از حد سفت نکنید</li>
<li>چسب 24 ساعت زمان خشک شدن نیاز دارد</li>
<li><b>ظرفیت این جعبه: حدود {r['item_weight'] * r['item_count'] * 1.5:.0f} kg</b></li>
</ul></div>

</body></html>'''
        self.guide_browser.setHtml(html)

    def _print_result(self):
        """باز کردن SVG کامل در مرورگر برای چاپ"""
        if not self.last_result:
            QMessageBox.warning(self, 'خطا', 'ابتدا محاسبه را انجام دهید.')
            return
        try:
            svg_content = self._build_svg_drawing()
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', prefix='box_print_', delete=False, encoding='utf-8')
            tmp.write(svg_content)
            tmp.close()
            
            webbrowser.open(f'file://{tmp.name}')
            QMessageBox.information(self, 'چاپ', 
                f'نقشه فنی کامل SVG در مرورگر باز شد.\n\n'
                f'برای چاپ: Ctrl+P را بزنید\n'
                f'فایل: {tmp.name}')
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e))

    def _export_html(self):
        """ذخیره SVG به صورت فایل"""
        if not self.last_result:
            QMessageBox.warning(self, 'خطا', 'ابتدا محاسبه را انجام دهید.')
            return
        try:
            path, _ = QFileDialog.getSaveFileName(self, 'ذخیره نقشه فنی', 'box_design.svg', 'SVG Files (*.svg)')
            if not path: return
            svg_content = self._build_svg_drawing()
            with open(path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            QMessageBox.information(self, 'خروجی', f'نقشه SVG ذخیره شد:\n{path}\n\nمی‌توانید در مرورگر باز کنید و چاپ کنید.')
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e))

    # ===================================================================
    # ✅ دکمه ثبت تولید در انبار
    # ===================================================================
    def _add_box_to_pallet(self):
        """[BOX-TO-PALLET] اضافه کردن جعبه تولیدشده به مدیریت پالت (قابل فروش)"""
        if not self.last_result:
            QMessageBox.warning(self, 'خطا', 'ابتدا محاسبه را انجام دهید.')
            return
        r = self.last_result
        try:
            with self.db.connect() as conn:
                row = conn.execute("SELECT MAX(id) FROM box_production").fetchone()
                last_id = int(row[0]) if row and row[0] else 0
                pallet_code = "BOX-{:04d}".format(last_id + 1)

                from PyQt5.QtWidgets import QInputDialog
                default_name = "جعبه {}x{}x{}".format(
                    int(r.get("outer_length", 0)), int(r.get("outer_width", 0)),
                    int(r.get("outer_height", 0)))
                name, ok = QInputDialog.getText(
                    self, "نام پالت", "نام پالت (برای فروش):", text=default_name)
                if not ok or not name.strip():
                    return
                name = name.strip()

                basis = self.pallet_price_combo.currentData() or "cost"
                qty = int(r.get("item_count", 1)) or 1
                if basis == "sale":
                    unit_price = int(r.get("final_price", 0) / qty)
                else:
                    unit_price = int(r.get("total_cost", 0) / qty)

                length = int(r.get("outer_length", 0))
                width = int(r.get("outer_width", 0))
                height = int(r.get("outer_height", 0))
                wood = r.get("wood_key", "چوبی")

                conn.execute(
                    "INSERT INTO pallets ("
                    " code, name, material_type, length_cm, width_cm, height_cm,"
                    " opening_stock, low_stock_threshold, image_path, description,"
                    " is_active, created_at, updated_at"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, 1, NULL, ?, 1, ?, ?)",
                    (pallet_code, name, wood, length, width, height, qty,
                     "اضافه از تولید جعبه (" + pallet_code + ")",
                     "2026-08-05 00:00:00", "2026-08-05 00:00:00"))
                pallet_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                wh_id = self.box_warehouse_combo.currentData() if hasattr(self, 'box_warehouse_combo') and self.box_warehouse_combo.currentData() else None
                if not wh_id:
                    wh_id = self._ask_warehouse()
                    if not wh_id:
                        wh_id = 1
                total_price = unit_price * qty
                conn.execute(
                    "INSERT INTO inventory_transactions ("
                    " transaction_date, transaction_type, reference_type, reference_id,"
                    " pallet_id, warehouse_id, qty_in, qty_out, unit_price, total_price,"
                    " description, created_at, is_void"
                    ") VALUES (?, 'IN', 'BOX_PRODUCTION', ?, ?, ?, ?, 0, ?, ?, ?, ?, 0)",
                    ("2026-08-05 00:00:00", pallet_id, pallet_id, wh_id, qty,
                     unit_price, total_price, "تولید جعبه: " + pallet_code,
                     "2026-08-05 00:00:00"))

                lvl = conn.execute(
                    "SELECT id FROM inventory_levels WHERE pallet_id = ? AND warehouse_id = ?",
                    (pallet_id, wh_id)).fetchone()
                if lvl:
                    conn.execute(
                        "UPDATE inventory_levels SET quantity = quantity + ?, updated_at = ? WHERE id = ?",
                        (qty, "2026-08-05 00:00:00", lvl[0]))
                else:
                    conn.execute(
                        "INSERT INTO inventory_levels (pallet_id, warehouse_id, quantity, updated_at) "
                        "VALUES (?, ?, ?, ?)",
                        (pallet_id, wh_id, qty, "2026-08-05 00:00:00"))

                conn.commit()

            QMessageBox.information(
                self, "موفق",
                "جعبه به مدیریت پالت اضافه شد!\n\n"
                "کد پالت: {}\nنام: {}\nابعاد: {}x{}x{} cm\n"
                "تعداد: {} عدد\nقیمت واحد: {:,} ریال\n\n"
                "حالا در «حواله خروج» قابل فروش است.".format(
                    pallet_code, name, length, width, height, qty, unit_price))
        except Exception as e:
            QMessageBox.critical(self, "خطا", "خطا در اضافه کردن به پالت:\n{}".format(e))

    def _ask_warehouse(self, title='انتخاب انبار مقصد'):
        """[NEW] فرم مجزا و ساده برای پرسیدن انبار مقصد"""
        try:
            with self.db.connect() as conn:
                rows = conn.execute("SELECT id, code, name FROM warehouses WHERE is_active=1 ORDER BY code").fetchall()
        except Exception:
            rows = []
        if not rows:
            return None
        names = ['{} | {}'.format(r[1], r[2]) for r in rows]
        default = 0
        try:
            cur = self.box_warehouse_combo.currentData()
            for i, r in enumerate(rows):
                if r[0] == cur:
                    default = i
        except Exception:
            pass
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(self, title, 'انبار مقصد:', names, default, False)
        if not ok:
            return None
        try:
            return rows[names.index(name)][0]
        except Exception:
            return None

    def _save_production(self):
        """ثبت تولید در انبار (box_production و box_inventory)"""
        if not self.last_result:
            QMessageBox.warning(self, 'خطا', 'ابتدا محاسبه را انجام دهید.')
            return

        wh_id_sel = self.box_warehouse_combo.currentData() if hasattr(self, 'box_warehouse_combo') else None
        if not wh_id_sel:
            QMessageBox.warning(self, 'خطا', 'لطفاً ابتدا انبار مقصد را انتخاب کنید.')
            return
        
        try:
            with self.db.connect() as conn:
                # بررسی وجود جداول
                tables = conn.execute('''
                    SELECT name FROM sqlite_master WHERE type='table'
                ''').fetchall()
                table_names = [t['name'] for t in tables]
                
                if 'box_production' not in table_names or 'box_inventory' not in table_names:
                    QMessageBox.critical(self, 'خطا', 
                        'جداول box_production یا box_inventory وجود ندارند!\n\n'
                        'لطفاً migration_box_module.py را اجرا کنید.')
                    return
                
                # تولید کد جعبه
                cursor = conn.execute('SELECT MAX(id) FROM box_production')
                last_id = cursor.fetchone()[0] or 0
                box_code = f"BOX-{last_id + 1:04d}"
                
                r = self.last_result
                
                # ثبت در box_production
                conn.execute('''
                    INSERT INTO box_production (
                        box_code, length_cm, width_cm, height_cm, quantity,
                        materials_cost, labor_cost, total_cost, wood_type,
                        user_id, production_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    box_code, 
                    r['outer_length'], r['outer_width'], r['outer_height'], 
                    r['item_count'],
                    int(r['wood_cost'] + r['hardware_cost']),
                    int(r['labor_cost']),
                    int(r['total_cost']),
                    r['wood_key'],
                    self.user_id,
                    QDate.currentDate().toString('yyyy-MM-dd')
                ))
                
                prod_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            try:
                conn.execute('CREATE TABLE IF NOT EXISTS box_production_items (id INTEGER PRIMARY KEY AUTOINCREMENT, box_production_id INTEGER, row_no INTEGER, part_name TEXT, count INTEGER, length_cm REAL, width_cm REAL, thickness_cm REAL)')
                conn.execute('DELETE FROM box_production_items WHERE box_production_id=?', (prod_id,))
                for _pi, _p in enumerate(r['parts'], start=1):
                    conn.execute('INSERT INTO box_production_items (box_production_id, row_no, part_name, count, length_cm, width_cm, thickness_cm) VALUES (?,?,?,?,?,?,?)', (prod_id, _pi, _p['name'], _p['count'], _p['l'], _p['w'], _p['t']))
            except Exception:
                pass
            # به‌روزرسانی یا ایجاد در box_inventory
                existing = conn.execute('''
                    SELECT id FROM box_inventory WHERE box_code = ?
                ''', (box_code,)).fetchone()
                
                if existing:
                    conn.execute('''
                        UPDATE box_inventory
                        SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP
                        WHERE box_code = ?
                    ''', (r['item_count'], box_code))
                else:
                    conn.execute('''
                        INSERT INTO box_inventory (
                            box_code, length_cm, width_cm, height_cm,
                            quantity, cost_price, wood_type, created_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        box_code, 
                        r['outer_length'], r['outer_width'], r['outer_height'],
                        r['item_count'], int(r['final_price'] / r['item_count']),
                        r['wood_key'], self.user_id
                    ))
                
                conn.commit()
                # [SAVE-TO-PALLET] اضافه کردن جعبه به پالت‌ها (برای گزارش انبار و حواله خروج)
                try:
                    pallet_code = box_code
                    pname = 'جعبه {}×{}×{}'.format(
                        int(r['outer_length']), int(r['outer_width']), int(r['outer_height']))
                    pqty = int(r['item_count'])
                    unit_price = int(r['total_cost'] / max(pqty, 1))
                    wood = r.get('wood_key', 'چوبی')

                    existing_pallet = conn.execute(
                        'SELECT id FROM pallets WHERE code = ?', (pallet_code,)).fetchone()
                    if existing_pallet:
                        pallet_id = int(existing_pallet[0])
                    else:
                        conn.execute(
                            'INSERT INTO pallets (code, name, material_type, length_cm, width_cm, '
                            'height_cm, opening_stock, low_stock_threshold, image_path, description, '
                            'is_active, created_at, updated_at) '
                            'VALUES (?, ?, ?, ?, ?, ?, ?, 1, NULL, ?, 1, ?, ?)',
                            (pallet_code, pname, wood,
                             int(r['outer_length']), int(r['outer_width']), int(r['outer_height']),
                             pqty, 'تولید جعبه {}'.format(pallet_code),
                             '2026-08-05 00:00:00', '2026-08-05 00:00:00'))
                        pallet_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

                    wh_id = self.box_warehouse_combo.currentData() if hasattr(self, 'box_warehouse_combo') and self.box_warehouse_combo.currentData() else None
                    if not wh_id:
                        wh_id = self._ask_warehouse()
                        if not wh_id:
                            wh_id = 1

                    wh_id = int(wh_id_sel)
                    total_price = unit_price * pqty
                    conn.execute(
                        'INSERT INTO inventory_transactions (transaction_date, transaction_type, '
                        'reference_type, reference_id, pallet_id, warehouse_id, qty_in, qty_out, '
                        'unit_price, total_price, description, created_at, is_void) '
                        "VALUES (?, 'IN', 'BOX_PRODUCTION', ?, ?, ?, ?, 0, ?, ?, ?, ?, 0)",
                        ('2026-08-05 00:00:00', pallet_id, pallet_id, wh_id, pqty,
                         unit_price, total_price, 'تولید جعبه {}'.format(pallet_code),
                         '2026-08-05 00:00:00'))

                    lvl = conn.execute(
                        'SELECT id FROM inventory_levels WHERE pallet_id = ? AND warehouse_id = ?',
                        (pallet_id, wh_id)).fetchone()
                    if lvl:
                        conn.execute(
                            'UPDATE inventory_levels SET quantity = quantity + ?, updated_at = ? WHERE id = ?',
                            (pqty, '2026-08-05 00:00:00', lvl[0]))
                    else:
                        conn.execute(
                            'INSERT INTO inventory_levels (pallet_id, warehouse_id, quantity, updated_at) '
                            'VALUES (?, ?, ?, ?)',
                            (pallet_id, wh_id, pqty, '2026-08-05 00:00:00'))
                    try:
                        conn.execute('UPDATE box_production SET warehouse_id=? WHERE box_code=?', (wh_id, box_code))
                        conn.execute('UPDATE box_inventory SET warehouse_id=? WHERE box_code=?', (wh_id, box_code))
                    except Exception:
                        pass
                except Exception as _p_err:
                    print('[save-to-pallet] warning:', _p_err)


                
                QMessageBox.information(self, 'موفق',
                    f'✅ تولید با موفقیت ثبت شد!\n\n'
                    f'کد جعبه: {box_code}\n'
                    f'ابعاد: {r["outer_length"]:.1f} × {r["outer_width"]:.1f} × {r["outer_height"]:.1f} cm\n'
                    f'تعداد: {r["item_count"]} عدد\n'
                    f'بهای تمام‌شده: {r["total_cost"]:,.0f} ریال\n'
                    f'مبلغ فروش: {r["final_price"]:,.0f} ریال\n'
                    f'موجودی انبار «{self.box_warehouse_combo.currentText()}» به‌روز شد.')
                
        except Exception as e:
            QMessageBox.critical(self, 'خطا در ثبت تولید', 
                f'خطا در ثبت تولید:\n{e}')
