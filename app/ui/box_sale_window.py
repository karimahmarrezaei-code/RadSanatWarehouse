"""
فرم فروش جعبه
صدور فاکتور فروش، ثبت در حسابداری، کاهش موجودی
"""

from typing import Optional
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from app.core.jalali import jalali_date_display_from_iso
from PyQt5.QtWidgets import (
    QDateEdit, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QComboBox, QFormLayout,
    QMessageBox, QFrame, QTextBrowser,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QDoubleSpinBox, QSpinBox, QTabWidget,
    QWidget, QAbstractItemView, QFileDialog
)
from PyQt5.QtGui import QFont
import tempfile
import webbrowser


class BoxSaleWindow(QDialog):
    """فرم فروش جعبه"""
    
    sale_saved = pyqtSignal()
    
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.user_id = user_data.get('id', 1)
        self.setWindowTitle('فروش جعبه')
        self.resize(1400, 900)
        self.setLayoutDirection(Qt.RightToLeft)
        self.customers = []
        self.inventory_items = []
        self.sale_items = []  # اقلام فاکتور فعلی
        self._build_ui()
        self._load_customers()
        self._load_inventory()
    
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)
        
        # اعمال استایل کلی برای تم تاریک

        
        # هدر
        header = QFrame()
        header.setObjectName('Card')
        h_layout = QVBoxLayout(header)
        title = QLabel('فروش جعبه')
        title.setObjectName('Title')
        subtitle = QLabel('مشتری و جعبه را انتخاب کنید و فاکتور صادر کنید')
        subtitle.setObjectName('Muted')
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        root.addWidget(header)
        
        # تب‌ها
        self.tabs = QTabWidget()

        
        # تب 1: ثبت فاکتور جدید
        new_sale_tab = QWidget()
        new_sale_layout = QVBoxLayout(new_sale_tab)
        
        # فرم مشتری
        customer_group = QGroupBox('مشتری و تاریخ')
        customer_layout = QFormLayout(customer_group)
        
        self.customer_combo = QComboBox()
        self.customer_combo.addItem('-- انتخاب مشتری --', None)
        self.customer_combo.setMinimumWidth(300)
        customer_layout.addRow('مشتری:', self.customer_combo)
        
        self.sale_date = QDateEdit(QDate.currentDate())
        self.sale_date.setCalendarPopup(True)
        self.sale_date.setDisplayFormat('yyyy-MM-dd')
        customer_layout.addRow('تاریخ فروش:', self.sale_date)
        
        new_sale_layout.addWidget(customer_group)
        
        # فرم افزودن جعبه
        add_item_group = QGroupBox('افزودن جعبه به فاکتور')
        add_item_layout = QFormLayout(add_item_group)
        
        item_layout = QHBoxLayout()
        self.item_combo = QComboBox()
        self.item_combo.addItem('-- انتخاب جعبه از موجودی --', None)
        self.item_combo.setMinimumWidth(400)
        item_layout.addWidget(QLabel('جعبه:'))
        item_layout.addWidget(self.item_combo)
        
        self.sale_qty = QSpinBox()
        self.sale_qty.setRange(1, 1000)
        self.sale_qty.setValue(1)
        item_layout.addWidget(QLabel('تعداد:'))
        item_layout.addWidget(self.sale_qty)
        
        self.item_price = QDoubleSpinBox()
        self.item_price.setRange(0, 999999999)
        self.item_price.setSuffix(' ریال')
        self.item_price.setDecimals(0)
        item_layout.addWidget(QLabel('قیمت واحد:'))
        item_layout.addWidget(self.item_price)
        
        add_btn = QPushButton('➕ افزودن به فاکتور')
        add_btn.setObjectName('PrimaryButton')
        add_btn.clicked.connect(self._add_item)
        item_layout.addWidget(add_btn)
        
        add_item_layout.addRow(item_layout)
        new_sale_layout.addWidget(add_item_group)
        
        # جدول اقلام فاکتور
        items_group = QGroupBox('اقلام فاکتور')
        items_layout = QVBoxLayout(items_group)
        
        self.items_table = QTableWidget(0, 7)
        self.items_table.setHorizontalHeaderLabels([
            'ردیف', 'کد جعبه', 'ابعاد (cm)', 'تعداد', 'قیمت واحد (ریال)', 'جمع (ریال)', 'حذف'
        ])
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.verticalHeader().setVisible(False)
        items_layout.addWidget(self.items_table)
        
        self.total_lbl = QLabel('جمع کل: 0 ریال')
        self.total_lbl.setObjectName('Title')
        self.total_lbl.setAlignment(Qt.AlignLeft)
        items_layout.addWidget(self.total_lbl)
        
        new_sale_layout.addWidget(items_group)
        
        # دکمه‌های ثبت
        btn_row = QHBoxLayout()
        
        save_btn = QPushButton('💾 ثبت فاکتور')
        save_btn.setObjectName('PrimaryButton')
        save_btn.setMinimumHeight(50)
        save_btn.setFont(QFont('Tahoma', 12, QFont.Bold))
        save_btn.clicked.connect(self._save_sale)
        btn_row.addWidget(save_btn)
        
        clear_btn = QPushButton('پاک کردن فاکتور')
        clear_btn.setObjectName('SecondaryButton')
        clear_btn.setMinimumHeight(50)
        clear_btn.clicked.connect(self._clear_sale)
        btn_row.addWidget(clear_btn)
        
        btn_row.addStretch()
        new_sale_layout.addLayout(btn_row)
        
        self.tabs.addTab(new_sale_tab, 'ثبت فاکتور جدید')
        
        # تب 2: فاکتورهای صادرشده
        sales_list_tab = QWidget()
        sales_list_layout = QVBoxLayout(sales_list_tab)
        
        self.sales_table = QTableWidget(0, 8)
        self.sales_table.setHorizontalHeaderLabels([
            'ردیف', 'شماره فاکتور', 'تاریخ', 'مشتری', 'تعداد اقلام', 'مبلغ کل', 'پرداختی', 'وضعیت'
        ])
        self.sales_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sales_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sales_table.verticalHeader().setVisible(False)
        self.sales_table.itemSelectionChanged.connect(self._on_sale_selected)
        sales_list_layout.addWidget(self.sales_table)
        
        self.sales_detail_lbl = QLabel('یک فاکتور را برای مشاهده جزئیات انتخاب کنید.')
        self.sales_detail_lbl.setStyleSheet("color: #555; font-size: 12px; padding: 5px;")
        sales_list_layout.addWidget(self.sales_detail_lbl)
        
        print_btn = QPushButton('🖨️ چاپ فاکتور انتخابی')
        print_btn.setObjectName('SecondaryButton')
        print_btn.setMinimumHeight(45)
        print_btn.clicked.connect(self._print_sale)
        sales_list_layout.addWidget(print_btn)
        
        self.tabs.addTab(sales_list_tab, 'فاکتورهای صادرشده')
        
        # تب 3: موجودی جعبه‌ها
        inventory_tab = QWidget()
        inventory_layout = QVBoxLayout(inventory_tab)
        
        self.inventory_table = QTableWidget(0, 7)
        self.inventory_table.setHorizontalHeaderLabels([
            'ردیف', 'کد جعبه', 'ابعاد (cm)', 'نوع چوب', 'موجودی', 'بهای تمام‌شده', 'آخرین به‌روزرسانی'
        ])
        self.inventory_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.inventory_table.verticalHeader().setVisible(False)
        inventory_layout.addWidget(self.inventory_table)
        
        refresh_inv_btn = QPushButton('🔄 به‌روزرسانی موجودی')
        refresh_inv_btn.setObjectName('SecondaryButton')
        refresh_inv_btn.setMinimumHeight(40)
        refresh_inv_btn.clicked.connect(self._refresh_inventory_table)
        inventory_layout.addWidget(refresh_inv_btn)
        
        self.tabs.addTab(inventory_tab, 'موجودی جعبه‌ها')
        
        # بارگذاری موجودی در جدول
        self._refresh_inventory_table()
        
        root.addWidget(self.tabs, stretch=1)
        
        # بارگذاری لیست فاکتورها
        self._load_sales()
    
    def _load_customers(self):
        """بارگذاری لیست مشتریان و تأمین‌کنندگان"""
        try:
            with self.db.connect() as conn:
                rows = conn.execute('''
                    SELECT id, first_name, last_name
                    FROM persons
                    ORDER BY first_name, last_name
                ''').fetchall()
                
                for r in rows:
                    name = f"{r['first_name'] or ''} {r['last_name'] or ''}".strip()
                    if not name:
                        name = 'نامشخص'
                    self.customers.append({
                        'id': r['id'],
                        'name': name
                    })
                    self.customer_combo.addItem(name, r['id'])
        except Exception:
            # اگر خطا رخ داد، فقط یک آیتم پیش‌فرض اضافه کن
            pass
    
    def _load_inventory(self):
        """بارگذاری موجودی جعبه‌ها"""
        try:
            with self.db.connect() as conn:
                rows = conn.execute('''
                    SELECT box_code, length_cm, width_cm, height_cm,
                           quantity, cost_price, wood_type
                    FROM box_inventory
                    WHERE quantity > 0
                    ORDER BY created_at DESC
                ''').fetchall()
                
                self.inventory_items = []
                for r in rows:
                    dims = f"{r['length_cm']}×{r['width_cm']}×{r['height_cm']}"
                    display = f"{r['box_code']} | {dims} cm | موجودی: {r['quantity']} | {r['wood_type'] or ''}"
                    self.inventory_items.append({
                        'box_code': r['box_code'],
                        'length': r['length_cm'],
                        'width': r['width_cm'],
                        'height': r['height_cm'],
                        'quantity': r['quantity'],
                        'cost_price': r['cost_price'],
                        'wood_type': r['wood_type']
                    })
                    self.item_combo.addItem(display, r['box_code'])
        except Exception:
            pass
    
    def _refresh_inventory_table(self):
        """به‌روزرسانی جدول موجودی در تب موجودی"""
        try:
            with self.db.connect() as conn:
                rows = conn.execute('''
                    SELECT box_code, length_cm, width_cm, height_cm,
                           quantity, cost_price, wood_type, updated_at
                    FROM box_inventory
                    ORDER BY updated_at DESC
                ''').fetchall()
                
                self.inventory_table.setRowCount(len(rows))
                for i, r in enumerate(rows):
                    dims = f"{r['length_cm']}×{r['width_cm']}×{r['height_cm']}"
                    self.inventory_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
                    self.inventory_table.setItem(i, 1, QTableWidgetItem(r['box_code']))
                    self.inventory_table.setItem(i, 2, QTableWidgetItem(dims))
                    self.inventory_table.setItem(i, 3, QTableWidgetItem(r['wood_type'] or '-'))
                    qty_item = QTableWidgetItem(str(r['quantity']))
                    qty_item.setTextAlignment(Qt.AlignCenter)
                    if r['quantity'] <= 2:
                        qty_item.setBackground(Qt.GlobalColor(12))  # زرد برای موجودی کم
                    elif r['quantity'] == 0:
                        qty_item.setBackground(Qt.red)
                    self.inventory_table.setItem(i, 4, qty_item)
                    self.inventory_table.setItem(i, 5, QTableWidgetItem(f"{r['cost_price']:,}"))
                    self.inventory_table.setItem(i, 6, QTableWidgetItem(jalali_date_display_from_iso(str(r['updated_at'])[:10]) if r['updated_at'] else '-'))
        except Exception:
            pass
    
    def _add_item(self):
        """افزودن یک قلم به فاکتور"""
        box_code = self.item_combo.currentData()
        if not box_code:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک جعبه انتخاب کنید.')
            return
        
        qty = self.sale_qty.value()
        price = int(self.item_price.value())
        
        if price <= 0:
            QMessageBox.warning(self, 'خطا', 'قیمت باید بیشتر از صفر باشد.')
            return
        
        # بررسی موجودی
        item_data = next((i for i in self.inventory_items if i['box_code'] == box_code), None)
        if not item_data:
            QMessageBox.warning(self, 'خطا', 'جعبه در موجودی یافت نشد.')
            return
        
        if qty > item_data['quantity']:
            QMessageBox.warning(self, 'خطا', 
                f'موجودی کافی نیست!\n'
                f'موجودی: {item_data["quantity"]} عدد\n'
                f'درخواست: {qty} عدد')
            return
        
        # بررسی تکراری بودن
        for si in self.sale_items:
            if si['box_code'] == box_code:
                si['quantity'] += qty
                si['total_price'] = si['quantity'] * price
                self._refresh_items_table()
                QMessageBox.information(self, 'موفق', 'تعداد به‌روز شد.')
                return
        
        self.sale_items.append({
            'box_code': box_code,
            'length': item_data['length'],
            'width': item_data['width'],
            'height': item_data['height'],
            'quantity': qty,
            'unit_price': price,
            'total_price': qty * price,
            'wood_type': item_data['wood_type']
        })
        
        self._refresh_items_table()
        QMessageBox.information(self, 'موفق', 'قلم به فاکتور اضافه شد.')
    
    def _refresh_items_table(self):
        """بازسازی جدول اقلام"""
        self.items_table.setRowCount(len(self.sale_items))
        total = 0
        
        for i, item in enumerate(self.sale_items):
            dims = f"{item['length']}×{item['width']}×{item['height']}"
            self.items_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.items_table.setItem(i, 1, QTableWidgetItem(item['box_code']))
            self.items_table.setItem(i, 2, QTableWidgetItem(dims))
            self.items_table.setItem(i, 3, QTableWidgetItem(str(item['quantity'])))
            self.items_table.setItem(i, 4, QTableWidgetItem(f"{item['unit_price']:,}"))
            self.items_table.setItem(i, 5, QTableWidgetItem(f"{item['total_price']:,}"))
            total += item['total_price']
            
            # دکمه حذف
            del_btn = QPushButton('حذف')
            del_btn.setStyleSheet("color: #dc2626; font-weight: bold;")
            del_btn.clicked.connect(lambda checked, idx=i: self._remove_item(idx))
            self.items_table.setCellWidget(i, 6, del_btn)
        
        self.total_lbl.setText(f'جمع کل: {total:,} ریال')
    
    def _remove_item(self, index):
        """حذف یک قلم از فاکتور"""
        if 0 <= index < len(self.sale_items):
            self.sale_items.pop(index)
            self._refresh_items_table()
    
    def _clear_sale(self):
        """پاک کردن فاکتور فعلی"""
        self.sale_items.clear()
        self._refresh_items_table()
        self.customer_combo.setCurrentIndex(0)
        self.sale_date.setDate(QDate.currentDate())
        QMessageBox.information(self, 'پاک شد', 'فاکتور پاک شد.')
    
    def _save_sale(self):
        """ثبت فاکتور در دیتابیس"""
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً مشتری را انتخاب کنید.')
            return
        
        if not self.sale_items:
            QMessageBox.warning(self, 'خطا', 'فاکتور خالی است.')
            return
        
        try:
            with self.db.connect() as conn:
                # تولید شماره فاکتور
                cursor = conn.execute('SELECT MAX(id) FROM box_sales')
                last_id = cursor.fetchone()[0] or 0
                sale_no = f"BOX-SALE-{last_id + 1:04d}"
                
                total_amount = sum(i['total_price'] for i in self.sale_items)
                sale_date = self.sale_date.date().toString('yyyy-MM-dd')
                
                # ثبت فاکتور در box_sales
                conn.execute('''
                    INSERT INTO box_sales (
                        sale_no, customer_id, sale_date, total_amount,
                        paid_amount, status, user_id
                    ) VALUES (?, ?, ?, ?, 0, 'OPEN', ?)
                ''', (sale_no, customer_id, sale_date, total_amount, self.user_id))
                
                sale_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                
                # ثبت اقلام در box_sale_items و کاهش موجودی
                for item in self.sale_items:
                    conn.execute('''
                        INSERT INTO box_sale_items (
                            sale_id, box_code, length_cm, width_cm, height_cm,
                            quantity, unit_price, total_price
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        sale_id, item['box_code'],
                        item['length'], item['width'], item['height'],
                        item['quantity'], item['unit_price'], item['total_price']
                    ))
                    
                    conn.execute('''
                        UPDATE box_inventory
                        SET quantity = quantity - ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE box_code = ?
                    ''', (item['quantity'], item['box_code']))
                
                # ثبت در financial_documents برای حسابداری
                customer = conn.execute('''
                    SELECT first_name, last_name FROM persons WHERE id = ?
                ''', (customer_id,)).fetchone()
                customer_name = ''
                if customer:
                    customer_name = f"{customer['first_name'] or ''} {customer['last_name'] or ''}".strip()
                
                conn.execute('''
                    INSERT INTO financial_documents (
                        finance_no, operation_type, direction,
                        receipt_id, issue_id, counterparty_person_id,
                        finance_date, total_amount, settled_amount,
                        status, description, created_at, created_by
                    ) VALUES (?, 'OUTBOUND_ISSUE', 'RECEIVABLE',
                              NULL, NULL, ?,
                              ?, ?, 0,
                              'OPEN', ?, ?, ?)
                ''', (
                    sale_no, customer_id, sale_date, total_amount,
                    f"فروش جعبه - {sale_no} - {customer_name}",
                    sale_date, self.user_id
                ))
                
                QMessageBox.information(self, 'موفق',
                    f'✅ فاکتور با موفقیت صادر شد!\n\n'
                    f'شماره فاکتور: {sale_no}\n'
                    f'مشتری: {customer_name}\n'
                    f'مبلغ کل: {total_amount:,} ریال\n\n'
                    f'سند مالی OPEN ثبت شد.\n'
                    f'موجودی انبار به‌روز شد.')
                
                self.sale_saved.emit()
                self._clear_sale()
                self._load_inventory()
                self._load_sales()
                self.tabs.setCurrentIndex(1)
                
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ثبت فاکتور:\n{e}')
            import traceback
            traceback.print_exc()
    
    def _load_sales(self):
        """بارگذاری لیست فاکتورها"""
        try:
            with self.db.connect() as conn:
                rows = conn.execute('''
                    SELECT bs.id, bs.sale_no, bs.sale_date, bs.total_amount,
                           bs.paid_amount, bs.status,
                           p.first_name || ' ' || p.last_name as customer_name,
                           (SELECT COUNT(*) FROM box_sale_items WHERE sale_id = bs.id) as item_count
                    FROM box_sales bs
                    JOIN persons p ON p.id = bs.customer_id
                    ORDER BY bs.created_at DESC
                ''').fetchall()
                
                self.sales_table.setRowCount(len(rows))
                status_labels = {'OPEN': 'باز', 'PARTIAL': 'ناقص', 'SETTLED': 'تسویه'}
                
                for i, r in enumerate(rows):
                    self.sales_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
                    self.sales_table.setItem(i, 1, QTableWidgetItem(r['sale_no']))
                    self.sales_table.setItem(i, 2, QTableWidgetItem(r['sale_date']))
                    self.sales_table.setItem(i, 3, QTableWidgetItem(r['customer_name'] or '-'))
                    self.sales_table.setItem(i, 4, QTableWidgetItem(str(r['item_count'])))
                    self.sales_table.setItem(i, 5, QTableWidgetItem(f"{r['total_amount']:,}"))
                    self.sales_table.setItem(i, 6, QTableWidgetItem(f"{r['paid_amount']:,}"))
                    self.sales_table.setItem(i, 7, QTableWidgetItem(status_labels.get(r['status'], r['status'])))
        except Exception:
            pass
    
    def _on_sale_selected(self):
        """نمایش جزئیات فاکتور انتخابی"""
        selected = self.sales_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        sale_id = int(self.sales_table.item(row, 0).text())
        
        try:
            with self.db.connect() as conn:
                rows = conn.execute('''
                    SELECT box_code, length_cm, width_cm, height_cm,
                           quantity, unit_price, total_price
                    FROM box_sale_items
                    WHERE sale_id = ?
                ''', (sale_id,)).fetchall()
                
                detail_text = f"📦 اقلام فاکتور ({len(rows)} قلم):\n\n"
                for r in rows:
                    dims = f"{r['length_cm']}×{r['width_cm']}×{r['height_cm']}"
                    detail_text += f"• {r['box_code']} | {dims} cm\n"
                    detail_text += f"  تعداد: {r['quantity']} × {r['unit_price']:,} = {r['total_price']:,} ریال\n\n"
                
                self.sales_detail_lbl.setText(detail_text)
        except Exception as e:
            self.sales_detail_lbl.setText(f"خطا: {e}")
    
    def _print_sale(self):
        """چاپ فاکتور انتخابی"""
        selected = self.sales_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک فاکتور انتخاب کنید.')
            return
        
        row = selected[0].row()
        sale_id = int(self.sales_table.item(row, 0).text())
        
        try:
            with self.db.connect() as conn:
                sale = conn.execute('''
                    SELECT bs.sale_no, bs.sale_date, bs.total_amount, bs.paid_amount, bs.status,
                           p.first_name || ' ' || p.last_name as customer_name,
                           p.mobile, p.address
                    FROM box_sales bs
                    JOIN persons p ON p.id = bs.customer_id
                    WHERE bs.id = ?
                ''', (sale_id,)).fetchone()
                
                items = conn.execute('''
                    SELECT box_code, length_cm, width_cm, height_cm,
                           quantity, unit_price, total_price
                    FROM box_sale_items
                    WHERE sale_id = ?
                ''', (sale_id,)).fetchall()
                
                if not sale:
                    QMessageBox.warning(self, 'خطا', 'فاکتور یافت نشد.')
                    return
                
                # اطلاعات شرکت
                company = conn.execute('''
                    SELECT company_name, phone, address FROM company_profile LIMIT 1
                ''').fetchone()
                
                company_name = company['company_name'] if company else 'شرکت'
                company_phone = company['phone'] if company else '-'
                company_address = company['address'] if company else '-'
                
                # ساخت HTML فاکتور
                item_rows = ''
                for i, r in enumerate(items, 1):
                    dims = f"{r['length_cm']}×{r['width_cm']}×{r['height_cm']}"
                    item_rows += f'''
                    <tr>
                        <td>{i}</td>
                        <td>{r['box_code']}</td>
                        <td>{dims} cm</td>
                        <td>{r['quantity']}</td>
                        <td>{r['unit_price']:,}</td>
                        <td>{r['total_price']:,}</td>
                    </tr>'''
                
                status_labels = {'OPEN': 'باز', 'PARTIAL': 'ناقص', 'SETTLED': 'تسویه'}
                
                html = f'''<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: Tahoma; padding: 20px; background: white; }}
    .header {{ border-bottom: 3px solid #46505f; padding-bottom: 10px; margin-bottom: 20px; }}
    .header h1 {{ margin: 0; color: #46505f; }}
    .header p {{ margin: 5px 0; color: #64748b; }}
    .info-box {{ background: #f8fafc; padding: 10px; border-radius: 5px; margin: 10px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
    th {{ background: #46505f; color: white; padding: 8px; }}
    td {{ padding: 8px; border: 1px solid #cbd5e1; }}
    .total {{ background: #dcfce7; font-weight: bold; font-size: 14px; }}
    .footer {{ margin-top: 30px; padding-top: 10px; border-top: 1px solid #cbd5e1; text-align: center; color: #64748b; }}
    @media print {{
        body {{ padding: 10px; }}
        .no-print {{ display: none; }}
    }}
</style>
</head>
<body>

<button class="no-print" onclick="window.print()" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 5px; cursor: pointer; margin-bottom: 20px;">🖨️ چاپ فاکتور</button>

<div class="header">
    <h1>{company_name}</h1>
    <p>تلفن: {company_phone}</p>
    <p>{company_address}</p>
</div>

<div style="text-align: center; margin: 20px 0;">
    <h2 style="color: #46505f;">فاکتور فروش جعبه</h2>
</div>

<div class="info-box">
    <table style="border: none;">
        <tr>
            <td style="border: none;"><b>شماره فاکتور:</b> {sale['sale_no']}</td>
            <td style="border: none;"><b>تاریخ:</b> {sale['sale_date']}</td>
        </tr>
        <tr>
            <td style="border: none;"><b>مشتری:</b> {sale['customer_name']}</td>
            <td style="border: none;"><b>موبایل:</b> {sale['mobile'] or '-'}</td>
        </tr>
        <tr>
            <td style="border: none;"><b>وضعیت:</b> {status_labels.get(sale['status'], sale['status'])}</td>
            <td style="border: none;"><b>آدرس:</b> {sale['address'] or '-'}</td>
        </tr>
    </table>
</div>

<table>
    <tr>
        <th>ردیف</th>
        <th>کد جعبه</th>
        <th>ابعاد (cm)</th>
        <th>تعداد</th>
        <th>قیمت واحد (ریال)</th>
        <th>جمع (ریال)</th>
    </tr>
    {item_rows}
    <tr class="total">
        <td colspan="5">جمع کل</td>
        <td>{sale['total_amount']:,} ریال</td>
    </tr>
    <tr class="total">
        <td colspan="5">پرداختی</td>
        <td>{sale['paid_amount']:,} ریال</td>
    </tr>
    <tr class="total">
        <td colspan="5">مانده</td>
        <td>{sale['total_amount'] - sale['paid_amount']:,} ریال</td>
    </tr>
</table>

<div class="footer">
    <p>با تشکر از اعتماد شما</p>
    <p>{company_name}</p>
</div>

</body>
</html>'''
                
                tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.html', prefix='box_sale_', delete=False, encoding='utf-8')
                tmp.write(html)
                tmp.close()
                webbrowser.open(f'file://{tmp.name}')
                QMessageBox.information(self, 'چاپ', 'فاکتور در مرورگر باز شد. برای چاپ Ctrl+P را بزنید.')
                
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در چاپ:\n{e}')
