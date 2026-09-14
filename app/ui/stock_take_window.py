import tempfile
import webbrowser
from datetime import datetime
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class StockTakeWindow(QDialog):
    take_completed = pyqtSignal()

    def __init__(self, db, user_data: Dict) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.stock_items: List[Dict] = []
        self.stock_take_id: Optional[int] = None

        self.setWindowTitle('انبارگردانی')
        self.resize(1600, 900)
        self._build_ui()
        self._load_warehouses()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName('Card')
        header_layout = QVBoxLayout(header)
        title = QLabel('فرم انبارگردانی')
        title.setObjectName('Title')
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel('شمارش واقعی موجودی پالت‌ها و ثبت مغایرت‌ها در کاردکس')
        subtitle.setObjectName('Muted')
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        filter_card = QFrame()
        filter_card.setObjectName('Card')
        filter_layout = QHBoxLayout(filter_card)

        self.warehouse_combo = QComboBox()
        self.warehouse_combo.setMinimumWidth(250)

        refresh_btn = QPushButton('بارگذاری موجودی')
        refresh_btn.setObjectName('PrimaryButton')
        refresh_btn.clicked.connect(self._load_stock_items)

        filter_layout.addWidget(QLabel('انتخاب انبار:'))
        filter_layout.addWidget(self.warehouse_combo)
        filter_layout.addWidget(refresh_btn)
        filter_layout.addStretch()
        root.addWidget(filter_card)

        self.main_table = QTableWidget(0, 9)
        self.main_table.setHorizontalHeaderLabels([
            'ردیف', 'کد پالت', 'نام پالت', 'موجودی سیستم',
            'میانگین قیمت', 'موجودی واقعی', 'مغایرت', 'ارزش مغایرت', 'علت'
        ])

        header_view = self.main_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(8, QHeaderView.Stretch)

        self.main_table.verticalHeader().setVisible(False)
        self.main_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.main_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.main_table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.main_table)

        summary_group = QGroupBox('خلاصه انبارگردانی')
        summary_layout = QVBoxLayout(summary_group)

        # ردیف اول
        row1 = QHBoxLayout()
        row1.addWidget(QLabel('تعداد کل اقلام:'))
        self.total_items_label = QLabel('0')
        self.total_items_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #1d4ed8; min-width: 40px;')
        row1.addWidget(self.total_items_label)
        row1.addSpacing(15)
        row1.addWidget(QLabel('شمارش شده:'))
        self.counted_items_label = QLabel('0')
        self.counted_items_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #047857; min-width: 40px;')
        row1.addWidget(self.counted_items_label)
        row1.addSpacing(15)
        row1.addWidget(QLabel('مثبت:'))
        self.positive_count_label = QLabel('0')
        self.positive_count_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #047857; min-width: 40px;')
        row1.addWidget(self.positive_count_label)
        row1.addSpacing(15)
        row1.addWidget(QLabel('منفی:'))
        self.negative_count_label = QLabel('0')
        self.negative_count_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #b91c1c; min-width: 40px;')
        row1.addWidget(self.negative_count_label)
        row1.addStretch()
        summary_layout.addLayout(row1)

        # ردیف دوم
        row2 = QHBoxLayout()
        row2.addWidget(QLabel('ارزش کسری:'))
        self.shortage_value_label = QLabel('0 ریال')
        self.shortage_value_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #b91c1c; min-width: 100px;')
        row2.addWidget(self.shortage_value_label)
        row2.addSpacing(15)
        row2.addWidget(QLabel('ارزش اضافی:'))
        self.surplus_value_label = QLabel('0 ریال')
        self.surplus_value_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #047857; min-width: 100px;')
        row2.addWidget(self.surplus_value_label)
        row2.addSpacing(15)
        row2.addWidget(QLabel('جمع جبری تعداد:'))
        self.net_qty_label = QLabel('0')
        self.net_qty_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #b45309; min-width: 40px;')
        row2.addWidget(self.net_qty_label)
        row2.addSpacing(15)
        row2.addWidget(QLabel('جمع جبری ارزش:'))
        self.net_value_label = QLabel('0 ریال')
        self.net_value_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #b45309; min-width: 100px;')
        row2.addWidget(self.net_value_label)
        row2.addStretch()
        summary_layout.addLayout(row2)

        root.addWidget(summary_group)

        button_layout = QHBoxLayout()

        save_btn = QPushButton('ثبت انبارگردانی')
        save_btn.setObjectName('PrimaryButton')
        save_btn.setMinimumHeight(50)
        save_btn.clicked.connect(self._save_stock_take)

        history_btn = QPushButton('تاریخچه انبارگردانی')
        history_btn.setObjectName('SecondaryButton')
        history_btn.setMinimumHeight(50)
        history_btn.clicked.connect(self._show_history)

        print_btn = QPushButton('پرینت گزارش')
        print_btn.setObjectName('SecondaryButton')
        print_btn.setMinimumHeight(50)
        print_btn.clicked.connect(self._print_report)

        export_btn = QPushButton('خروجی HTML')
        export_btn.setObjectName('SecondaryButton')
        export_btn.setMinimumHeight(50)
        export_btn.clicked.connect(self._export_html)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(history_btn)
        button_layout.addWidget(print_btn)
        button_layout.addWidget(export_btn)
        root.addLayout(button_layout)

    def _load_warehouses(self) -> None:
        try:
            with self.db.connect() as conn:
                self.warehouses = conn.execute("""
                    SELECT id, code, name
                    FROM warehouses
                    WHERE is_active = 1
                    ORDER BY code
                """).fetchall()
        except Exception as e:
            self.warehouses = []

        self.warehouse_combo.blockSignals(True)
        self.warehouse_combo.clear()
        self.warehouse_combo.addItem('انتخاب انبار', None)

        for wh in self.warehouses:
            self.warehouse_combo.addItem(f"{wh['code']} | {wh['name']}", wh['id'])

        self.warehouse_combo.blockSignals(False)

        if len(self.warehouses) > 0:
            self.warehouse_combo.setCurrentIndex(1)

    def _load_stock_items(self) -> None:
        warehouse_id = self.warehouse_combo.currentData()
        if not warehouse_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک انبار انتخاب کنید.')
            return

        try:
            with self.db.connect() as conn:
                rows = conn.execute("""
                    SELECT
                        il.id,
                        il.pallet_id,
                        p.code as pallet_code,
                        p.name as pallet_name,
                        il.quantity
                    FROM inventory_levels il
                    JOIN pallets p ON il.pallet_id = p.id
                    WHERE il.warehouse_id = ? AND il.quantity > 0
                    ORDER BY p.code
                """, (warehouse_id,)).fetchall()

                # میانگین وزنی = (ارزش افتتاحیه + ارزش ورودها) / (تعداد افتتاحیه + تعداد ورودها)
                prices = {}
                avg_rows = conn.execute("""
                    SELECT pid, SUM(val)/SUM(q) AS avg FROM (
                        SELECT oii.pallet_id AS pid, oii.qty*oii.unit_price AS val, oii.qty AS q
                        FROM opening_inventory_items oii
                        JOIN opening_inventory_documents oid ON oii.opening_document_id=oid.id
                        WHERE oid.warehouse_id=?
                        UNION ALL
                        SELECT it.pallet_id, it.qty_in*it.unit_price, it.qty_in
                        FROM inventory_transactions it
                        WHERE it.warehouse_id=? AND it.transaction_type='IN' AND it.qty_in>0
                          AND it.unit_price>0 AND it.reference_type<>'TRANSFER'
                    ) GROUP BY pid""", (warehouse_id, warehouse_id)).fetchall()
                for a in avg_rows:
                    prices[a['pid']] = int(a['avg'] or 0)
                # fallback سراسری (برای پالت‌های بدون سابقه در این انبار)
                g_rows = conn.execute("""
                    SELECT pid, SUM(val)/SUM(q) AS avg FROM (
                        SELECT oii.pallet_id AS pid, oii.qty*oii.unit_price AS val, oii.qty AS q
                        FROM opening_inventory_items oii
                        UNION ALL
                        SELECT it.pallet_id, it.qty_in*it.unit_price, it.qty_in
                        FROM inventory_transactions it
                        WHERE it.transaction_type='IN' AND it.qty_in>0 AND it.unit_price>0
                          AND it.reference_type<>'TRANSFER'
                    ) GROUP BY pid""").fetchall()
                for a in g_rows:
                    if not prices.get(a['pid']):
                        prices[a['pid']] = int(a['avg'] or 0)

        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در بارگذاری موجودی:\n\n{e}')
            return

        self.stock_items = []
        for r in rows:
            self.stock_items.append({
                'id': r['id'],
                'pallet_id': r['pallet_id'],
                'pallet_code': r['pallet_code'],
                'pallet_name': r['pallet_name'],
                'quantity': r['quantity'],
                'unit_price': prices.get(r['pallet_id'], 0),
            })

        if not self.stock_items:
            QMessageBox.information(self, 'اطلاع', 'هیچ پالتی با موجودی در این انبار یافت نشد.')
            self.main_table.setRowCount(0)
            self._update_summary()
            return

        self._populate_table()

    def _populate_table(self) -> None:
        self.main_table.blockSignals(True)
        self.main_table.setRowCount(len(self.stock_items))

        bg_dark = QColor('#dbeafe')
        text_color = QColor('#0f172a')

        for idx, item in enumerate(self.stock_items):
            row_item = QTableWidgetItem(str(idx + 1))
            row_item.setFlags(row_item.flags() & ~Qt.ItemIsEditable)
            row_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            row_item.setForeground(text_color)
            self.main_table.setItem(idx, 0, row_item)

            code_item = QTableWidgetItem(item['pallet_code'])
            code_item.setFlags(code_item.flags() & ~Qt.ItemIsEditable)
            code_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            code_item.setForeground(text_color)
            self.main_table.setItem(idx, 1, code_item)

            name_item = QTableWidgetItem(item['pallet_name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setForeground(text_color)
            self.main_table.setItem(idx, 2, name_item)

            qty = item['quantity']
            sys_item = QTableWidgetItem(f'{qty:,}')
            sys_item.setFlags(sys_item.flags() & ~Qt.ItemIsEditable)
            sys_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            sys_item.setBackground(bg_dark)
            sys_item.setForeground(text_color)
            self.main_table.setItem(idx, 3, sys_item)

            price = item['unit_price']
            price_item = QTableWidgetItem(f'{int(price):,} ریال')
            price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
            price_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            price_item.setBackground(bg_dark)
            price_item.setForeground(text_color)
            self.main_table.setItem(idx, 4, price_item)

            actual_item = QTableWidgetItem('')
            actual_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            actual_item.setData(Qt.UserRole, 'actual_qty')
            actual_item.setData(Qt.UserRole + 1, qty)
            actual_item.setData(Qt.UserRole + 2, price)
            actual_item.setData(Qt.UserRole + 3, item['id'])
            actual_item.setData(Qt.UserRole + 4, item['pallet_id'])
            self.main_table.setItem(idx, 5, actual_item)

            diff_item = QTableWidgetItem('')
            diff_item.setFlags(diff_item.flags() & ~Qt.ItemIsEditable)
            diff_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.main_table.setItem(idx, 6, diff_item)

            value_item = QTableWidgetItem('')
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            value_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.main_table.setItem(idx, 7, value_item)

            reason_item = QTableWidgetItem('')
            reason_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            reason_item.setData(Qt.UserRole, 'reason')
            self.main_table.setItem(idx, 8, reason_item)

        self.main_table.blockSignals(False)
        self._update_summary()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.data(Qt.UserRole) != 'actual_qty':
            return

        row = item.row()
        actual_text = item.text().strip()

        bg_dark = QColor('#dbeafe')
        red_color = QColor('#dc2626')
        green_color = QColor('#059669')
        white_color = QColor('#ffffff')
        text_color = QColor('#0f172a')

        if not actual_text:
            self.main_table.blockSignals(True)
            for col in [5, 6, 7]:
                cell = self.main_table.item(row, col)
                if cell:
                    cell.setBackground(bg_dark)
                    cell.setForeground(text_color)
            self.main_table.blockSignals(False)
            self._update_summary()
            return

        try:
            actual_qty = int(actual_text.replace(',', ''))
        except ValueError:
            return

        sys_qty = item.data(Qt.UserRole + 1)
        price = item.data(Qt.UserRole + 2)

        discrepancy = actual_qty - sys_qty
        value_diff = discrepancy * price

        diff_item = QTableWidgetItem(f'{discrepancy:+,}')
        diff_item.setFlags(diff_item.flags() & ~Qt.ItemIsEditable)
        diff_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        value_item = QTableWidgetItem(f'{int(value_diff):+,} ریال')
        value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
        value_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        if discrepancy < 0:
            item.setBackground(red_color)
            diff_item.setBackground(red_color)
            value_item.setBackground(red_color)
            item.setForeground(white_color)
            diff_item.setForeground(white_color)
            value_item.setForeground(white_color)
        elif discrepancy > 0:
            item.setBackground(green_color)
            diff_item.setBackground(green_color)
            value_item.setBackground(green_color)
            item.setForeground(white_color)
            diff_item.setForeground(white_color)
            value_item.setForeground(white_color)
        else:
            item.setBackground(bg_dark)
            diff_item.setBackground(bg_dark)
            value_item.setBackground(bg_dark)
            item.setForeground(text_color)
            diff_item.setForeground(text_color)
            value_item.setForeground(text_color)

        self.main_table.blockSignals(True)
        self.main_table.setItem(row, 6, diff_item)
        self.main_table.setItem(row, 7, value_item)
        self.main_table.blockSignals(False)

        self._update_summary()

    def _update_summary(self) -> None:
        total = len(self.stock_items)
        counted = 0
        positive_count = 0
        negative_count = 0
        shortage_value = 0
        surplus_value = 0
        net_qty = 0
        net_value = 0

        for row in range(self.main_table.rowCount()):
            actual_item = self.main_table.item(row, 5)
            if actual_item and actual_item.text().strip():
                counted += 1
                try:
                    actual_qty = int(actual_item.text().replace(',', ''))
                    sys_qty = actual_item.data(Qt.UserRole + 1)
                    price = actual_item.data(Qt.UserRole + 2)
                    diff = actual_qty - sys_qty
                    value_diff = diff * price

                    if diff > 0:
                        positive_count += 1
                        surplus_value += value_diff
                        net_qty += diff
                        net_value += value_diff
                    elif diff < 0:
                        negative_count += 1
                        shortage_value += abs(value_diff)
                        net_qty += diff
                        net_value += value_diff
                except Exception:
                    pass

        self.total_items_label.setText(f'{total:,}')
        self.counted_items_label.setText(f'{counted:,}')
        self.positive_count_label.setText(f'{positive_count:,}')
        self.negative_count_label.setText(f'{negative_count:,}')
        self.shortage_value_label.setText(f'{int(shortage_value):,} ریال')
        self.surplus_value_label.setText(f'{int(surplus_value):,} ریال')
        self.net_qty_label.setText(f'{net_qty:+,}')
        self.net_value_label.setText(f'{int(net_value):+,} ریال')

    def _get_discrepancies(self) -> List[Dict]:
        discrepancies = []
        for row in range(self.main_table.rowCount()):
            actual_item = self.main_table.item(row, 5)
            if not actual_item or not actual_item.text().strip():
                continue

            try:
                actual_qty = int(actual_item.text().replace(',', ''))
            except ValueError:
                continue

            sys_qty = actual_item.data(Qt.UserRole + 1)
            price = actual_item.data(Qt.UserRole + 2)
            discrepancy = actual_qty - sys_qty

            if discrepancy != 0:
                reason_item = self.main_table.item(row, 8)
                reason = reason_item.text().strip() if reason_item else ''

                discrepancies.append({
                    'row': row + 1,
                    'pallet_code': self.main_table.item(row, 1).text(),
                    'pallet_name': self.main_table.item(row, 2).text(),
                    'system_qty': sys_qty,
                    'actual_qty': actual_qty,
                    'discrepancy': discrepancy,
                    'unit_cost': price,
                    'value_diff': discrepancy * price,
                    'reason': reason
                })

        return discrepancies

    def _save_stock_take(self) -> None:
        warehouse_id = self.warehouse_combo.currentData()
        if not warehouse_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً یک انبار انتخاب کنید.')
            return

        counted_rows = 0
        for row in range(self.main_table.rowCount()):
            actual_item = self.main_table.item(row, 5)
            if actual_item and actual_item.text().strip():
                counted_rows += 1

        if counted_rows == 0:
            QMessageBox.warning(self, 'خطا', 'حداقل یک پالت باید شمارش شود.')
            return

        try:
            with self.db.connect() as conn:
                today = datetime.now().strftime('%Y%m%d')
                cursor = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 as next_id FROM stock_takes")
                next_id = cursor.fetchone()[0]
                stock_take_no = f"ST-{today}-{next_id:03d}"

                user_id = self.user_data.get('user_id', 1)
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                today_date = datetime.now().strftime('%Y-%m-%d')

                total_sys = 0
                total_actual = 0
                total_diff = 0
                total_loss = 0

                for row in range(self.main_table.rowCount()):
                    actual_item = self.main_table.item(row, 5)
                    if actual_item and actual_item.text().strip():
                        try:
                            aq = int(actual_item.text().replace(',', ''))
                            sq = actual_item.data(Qt.UserRole + 1)
                            pr = actual_item.data(Qt.UserRole + 2)
                            total_sys += sq
                            total_actual += aq
                            d = aq - sq
                            total_diff += d
                            if d < 0:
                                total_loss += abs(d * pr)
                        except Exception:
                            pass

                conn.execute("""
                    INSERT INTO stock_takes
                    (stock_take_no, take_date, total_system_qty, total_actual_qty,
                     total_difference, total_value_loss, status, user_id, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, ?, ?)
                """, (stock_take_no, today_date, total_sys, total_actual,
                      total_diff, total_loss, user_id, 'انبارگردانی', now))

                cursor = conn.execute('SELECT last_insert_rowid()')
                stock_take_id = cursor.fetchone()[0]

                for row in range(self.main_table.rowCount()):
                    actual_item = self.main_table.item(row, 5)
                    if not actual_item or not actual_item.text().strip():
                        continue

                    try:
                        actual_qty = int(actual_item.text().replace(',', ''))
                    except ValueError:
                        continue

                    sys_qty = actual_item.data(Qt.UserRole + 1)
                    price = actual_item.data(Qt.UserRole + 2)
                    pallet_id = actual_item.data(Qt.UserRole + 4)
                    reason_item = self.main_table.item(row, 8)
                    reason = reason_item.text().strip() if reason_item else ''

                    discrepancy = actual_qty - sys_qty
                    total_value_diff = discrepancy * price

                    conn.execute("""
                        INSERT INTO stock_take_items
                        (stock_take_id, pallet_id, system_qty, actual_qty, difference, unit_price, total_value_diff, reason, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
                    """, (stock_take_id, pallet_id, sys_qty, actual_qty, discrepancy, int(price), int(total_value_diff), reason))

                conn.commit()

            QMessageBox.information(
                self, 'موفق',
                f'انبارگردانی با شماره {stock_take_no} ثبت شد.\n'
                f'وضعیت: در انتظار تایید ادمین'
            )
            self.take_completed.emit()
            
            # رفرش جدول برای نمایش موجودی جدید
            self._load_stock_items()

        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'ثبت انبارگردانی با خطا مواجه شد:\n\n{e}')

    def _show_history(self) -> None:
        """نمایش تاریخچه انبارگردانی‌ها"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                raw_rows = conn.execute("""
                    SELECT id, stock_take_no, take_date,
                           total_system_qty, total_actual_qty,
                           total_difference, total_value_loss, status, user_id, notes
                    FROM stock_takes
                    ORDER BY take_date DESC, id DESC
                """).fetchall()
                # تبدیل به dict قابل ویرایش
                rows = []
                for r in raw_rows:
                    rows.append({
                        'id': r[0],
                        'stock_take_no': r[1],
                        'take_date': r[2],
                        'total_system_qty': r[3],
                        'total_actual_qty': r[4],
                        'total_difference': r[5],
                        'total_value_loss': r[6],
                        'status': r[7],
                        'user_id': r[8],
                        'notes': r[9],
                    })

            if not rows:
                QMessageBox.information(self, 'تاریخچه', 'هیچ انبارگردانی ثبت نشده است.')
                return

            history_dialog = QDialog(self)
            history_dialog.setWindowTitle('تاریخچه انبارگردانی')
            history_dialog.resize(1400, 700)
            history_dialog

            layout = QVBoxLayout(history_dialog)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(14)

            title_lbl = QLabel('تاریخچه اسناد انبارگردانی')
            title_lbl.setObjectName('Title')
            title_lbl.setAlignment(Qt.AlignCenter)
            title_lbl.setStyleSheet('font-size: 18px; font-weight: bold; color: #1d4ed8;')
            layout.addWidget(title_lbl)

            history_table = QTableWidget(0, 9)
            history_table.setHorizontalHeaderLabels([
                'شناسه', 'شماره سند', 'تاریخ', 'موجودی سیستم', 'موجودی واقعی',
                'تفاوت', 'ارزش زیان', 'وضعیت', 'انتخاب'
            ])
            history_table.setRowCount(len(rows))
            history_table.verticalHeader().setVisible(False)
            history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            history_table.setSelectionMode(QAbstractItemView.SingleSelection)
            history_table.setAlternatingRowColors(True)

            STATUS_LABELS = {
                'DRAFT': 'پیش‌نویس',
                'PENDING_APPROVAL': 'در انتظار تایید',
                'APPROVED': 'تایید شده',
                'REJECTED': 'رد شده',
            }
            STATUS_COLORS = {
                'DRAFT': '#64748b',
                'PENDING_APPROVAL': '#b45309',
                'APPROVED': '#047857',
                'REJECTED': '#b91c1c',
            }

            # متغیر برای نگهداری ID سند انتخاب‌شده
            selected_take_id = [rows[0]['id'] if rows else None]

            # متغیر برای نگهداری وضعیت سند انتخاب‌شده
            selected_status = [rows[0]['status'] if rows else None]

            # ساخت دکمه تایید
            approve_btn = QPushButton('تایید سند')
            approve_btn.setMinimumHeight(45)
            approve_btn

            def _update_approve_button():
                """بروزرسانی دکمه تایید بر اساس وضعیت"""
                status = selected_status[0]
                if status in ('DRAFT', 'PENDING_APPROVAL'):
                    approve_btn.setEnabled(True)
                    approve_btn
                else:
                    approve_btn.setEnabled(False)
                    approve_btn

            def _update_reject_button():
                """بروزرسانی دکمه رد بر اساس وضعیت"""
                status = selected_status[0]
                if status in ('DRAFT', 'PENDING_APPROVAL'):
                    reject_btn.setEnabled(True)
                else:
                    reject_btn.setEnabled(False)

            def _on_select_row(take_id):
                """انتخاب سند و بارگذاری جزئیات"""
                selected_take_id[0] = take_id
                # پیدا کردن وضعیت از جدول
                for r in rows:
                    if r['id'] == take_id:
                        selected_status[0] = r['status']
                        break
                load_details(take_id)
                # بروزرسانی دکمه‌ها
                _update_approve_button()
                _update_reject_button()

            for idx, row in enumerate(rows):
                status_text = STATUS_LABELS.get(row['status'], row['status'])
                values = [
                    str(row['id']),
                    row['stock_take_no'],
                    row['take_date'],
                    f"{row['total_system_qty']:,}",
                    f"{row['total_actual_qty']:,}",
                    f"{row['total_difference']:+,}",
                    f"{int(row['total_value_loss']):,} ریال",
                    status_text,
                ]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setBackground(QColor('#dbeafe'))
                    if col == 7:  # ستون وضعیت
                        item.setForeground(QColor(STATUS_COLORS.get(row['status'], '#e2e8f0')))
                        item.setFont(QFont('Tahoma', 10, QFont.Bold))
                    elif row['total_difference'] < 0:
                        item.setForeground(QColor('#b91c1c'))
                    else:
                        item.setForeground(QColor('#1d4ed8'))
                    history_table.setItem(idx, col, item)

                # اضافه کردن دکمه انتخاب در ستون آخر
                select_btn = QPushButton('انتخاب')
                select_btn.setFixedSize(70, 28)
                select_btn
                select_btn.clicked.connect(lambda checked, tid=row['id']: _on_select_row(tid))
                history_table.setCellWidget(idx, 8, select_btn)

            history_table.resizeColumnsToContents()
            # تنظیم عرض ستون‌ها
            history_table.setColumnWidth(8, 80)  # ستون انتخاب
            layout.addWidget(history_table)

            # راهنمای وضعیت
            status_guide = QFrame()
            status_guide.setObjectName('Card')
            status_guide
            guide_layout = QHBoxLayout(status_guide)
            guide_layout.setSpacing(20)
            guide_layout.addWidget(QLabel('راهنمای وضعیت:'))
            for status_key, status_label in STATUS_LABELS.items():
                lbl = QLabel(f'● {status_label}')
                lbl.setStyleSheet(f'color: {STATUS_COLORS[status_key]}; font-weight: bold; font-size: 12px;')
                guide_layout.addWidget(lbl)
            guide_layout.addStretch()
            layout.addWidget(status_guide)

            # جزئیات
            detail_label = QLabel('ریز اقلام سند انتخاب‌شده:')
            detail_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #1d4ed8;')
            layout.addWidget(detail_label)

            detail_table = QTableWidget(0, 9)
            detail_table.setHorizontalHeaderLabels([
                'ردیف', 'کد پالت', 'نام پالت', 'سیستم', 'واقعی',
                'مغایرت', 'قیمت واحد', 'ارزش مغایرت', 'علت'
            ])
            detail_table.verticalHeader().setVisible(False)
            detail_table.setAlternatingRowColors(True)
            layout.addWidget(detail_table)

            # توابع کمکی
            def load_details(take_id):
                detail_table.setRowCount(0)
                try:
                    with self.db.connect() as local_conn:
                        local_conn.row_factory = None
                        items = local_conn.execute("""
                            SELECT sti.pallet_id, p.code as pallet_code, p.name as pallet_name,
                                   sti.system_qty, sti.actual_qty, sti.difference,
                                   sti.unit_price, sti.total_value_diff, sti.reason
                            FROM stock_take_items sti
                            JOIN pallets p ON sti.pallet_id = p.id
                            WHERE sti.stock_take_id = ?
                            ORDER BY p.code
                        """, (take_id,)).fetchall()

                        detail_table.setRowCount(len(items))
                        for idx2, item in enumerate(items):
                            pallet_id, pallet_code, pallet_name, system_qty, actual_qty, difference, unit_price, total_value_diff, reason = item
                            values = [
                                str(idx2 + 1),
                                str(pallet_code),
                                str(pallet_name),
                                f"{int(system_qty):,}",
                                f"{int(actual_qty):,}",
                                f"{int(difference):+,}",
                                f"{int(unit_price):,} ریال",
                                f"{int(total_value_diff):,} ریال",
                                str(reason) if reason else '-',
                            ]
                            for col, value in enumerate(values):
                                cell = QTableWidgetItem(value)
                                cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                                cell.setBackground(QColor('#dbeafe'))
                                if difference > 0:
                                    cell.setForeground(QColor('#047857'))
                                elif difference < 0:
                                    cell.setForeground(QColor('#b91c1c'))
                                else:
                                    cell.setForeground(QColor('#0f172a'))
                                detail_table.setItem(idx2, col, cell)

                        detail_table.resizeColumnsToContents()
                except Exception as e:
                    QMessageBox.warning(history_dialog, 'خطا', f'بارگذاری جزئیات با خطا مواجه شد:\n\n{e}')



            def get_selected_data():
                take_id = selected_take_id[0]
                if not take_id:
                    QMessageBox.warning(history_dialog, 'خطا', f'selected_take_id is None. currentRow: {history_table.currentRow()}')
                    return None, None
                try:
                    with self.db.connect() as local_conn:
                        local_conn.row_factory = None
                        take = local_conn.execute("""
                            SELECT id, stock_take_no, take_date,
                                   total_system_qty, total_actual_qty,
                                   total_difference, total_value_loss, status, user_id, notes
                            FROM stock_takes WHERE id = ?
                        """, (take_id,)).fetchone()
                        if not take:
                            QMessageBox.warning(history_dialog, 'خطا', f'Take not found for ID: {take_id}')
                            return None, None
                        take_data = {
                            'id': take[0],
                            'stock_take_no': take[1],
                            'take_date': take[2],
                            'total_system_qty': take[3],
                            'total_actual_qty': take[4],
                            'total_difference': take[5],
                            'total_value_loss': take[6],
                            'status': take[7],
                            'user_id': take[8],
                            'notes': take[9],
                        }
                        items = local_conn.execute("""
                            SELECT p.code as pallet_code, p.name as pallet_name,
                                   sti.system_qty, sti.actual_qty, sti.difference,
                                   sti.unit_price, sti.total_value_diff, sti.reason
                            FROM stock_take_items sti
                            JOIN pallets p ON sti.pallet_id = p.id
                            WHERE sti.stock_take_id = ?
                            ORDER BY p.code
                        """, (take_id,)).fetchall()
                        items_data = []
                        for it in items:
                            items_data.append({
                                'pallet_code': it[0],
                                'pallet_name': it[1],
                                'system_qty': it[2],
                                'actual_qty': it[3],
                                'difference': it[4],
                                'unit_price': it[5],
                                'total_value_diff': it[6],
                                'reason': it[7],
                            })
                        return take_data, items_data
                except Exception as e:
                    import traceback
                    QMessageBox.warning(history_dialog, 'خطا', f'Error in get_selected_data:\n{traceback.format_exc()}')
                    return None, None

            def generate_take_html(take_data, items_data):
                take = take_data
                items = items_data
                stock_take_no = take['stock_take_no']

                return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>گزارش انبارگردانی {stock_take_no}</title>
    <style>
        body {{ font-family: Tahoma, Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #46505f; border-bottom: 3px solid #2563eb; padding-bottom: 15px; }}
        .header-info {{ display: flex; justify-content: space-between; margin-bottom: 20px; padding: 15px; background: #f1f5f9; border-radius: 6px; flex-wrap: wrap; }}
        .header-info div {{ margin: 5px 15px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .summary-card {{ padding: 15px; border-radius: 6px; text-align: center; }}
        .summary-card.total {{ background: #dbeafe; border: 2px solid #2563eb; }}
        .summary-card.counted {{ background: #dcfce7; border: 2px solid #059669; }}
        .summary-card.diff {{ background: #fef3c7; border: 2px solid #f59e0b; }}
        .summary-card.loss {{ background: #fee2e2; border: 2px solid #dc2626; }}
        .summary-card .label {{ font-size: 14px; color: #64748b; margin-bottom: 5px; }}
        .summary-card .value {{ font-size: 22px; font-weight: bold; color: #46505f; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #46505f; color: white; padding: 12px; text-align: center; font-size: 14px; }}
        td {{ padding: 10px; text-align: center; border-bottom: 1px solid #e2e8f0; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        .discrepancy-negative {{ background: #fee2e2 !important; color: #dc2626; font-weight: bold; }}
        .discrepancy-positive {{ background: #dcfce7 !important; color: #059669; font-weight: bold; }}
        .footer {{ margin-top: 40px; text-align: center; color: #64748b; font-size: 12px; border-top: 2px solid #e2e8f0; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>گزارش انبارگردانی</h1>
        <div class="header-info">
            <div><strong>شماره:</strong> {stock_take_no}</div>
            <div><strong>تاریخ:</strong> {take['take_date']}</div>
            <div><strong>وضعیت:</strong> تایید شده</div>
        </div>
        <div class="summary">
            <div class="summary-card total">
                <div class="label">موجودی سیستم</div>
                <div class="value">{take['total_system_qty']:,}</div>
            </div>
            <div class="summary-card counted">
                <div class="label">موجودی واقعی</div>
                <div class="value">{take['total_actual_qty']:,}</div>
            </div>
            <div class="summary-card diff">
                <div class="label">تفاوت</div>
                <div class="value">{take['total_difference']:+,}</div>
            </div>
            <div class="summary-card loss">
                <div class="label">ارزش زیان</div>
                <div class="value">{int(take['total_value_loss']):,} ریال</div>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>ردیف</th>
                    <th>کد پالت</th>
                    <th>نام پالت</th>
                    <th>سیستم</th>
                    <th>واقعی</th>
                    <th>مغایرت</th>
                    <th>قیمت واحد</th>
                    <th>ارزش مغایرت</th>
                    <th>علت</th>
                </tr>
            </thead>
            <tbody>""" + "".join(f"""
                <tr class="{'discrepancy-negative' if it['difference'] < 0 else ('discrepancy-positive' if it['difference'] > 0 else '')}">
                    <td>{idx + 1}</td>
                    <td>{it['pallet_code']}</td>
                    <td>{it['pallet_name']}</td>
                    <td>{it['system_qty']:,}</td>
                    <td>{it['actual_qty']:,}</td>
                    <td>{it['difference']:+,}</td>
                    <td>{int(it['unit_price']):,} ریال</td>
                    <td>{int(it['total_value_diff']):,} ریال</td>
                    <td>{it.get('reason', '') or '-'}</td>
                </tr>""" for idx, it in enumerate(items)) + """
            </tbody>
        </table>
        <div class="footer">
            <p>تاریخ تولید: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
        </div>
    </div>
</body>
</html>"""

            def do_print():
                take_data, items_data = get_selected_data()
                if not take_data:
                    QMessageBox.warning(history_dialog, 'خطا', 'لطفاً یک سند از جدول انتخاب کنید.')
                    return
                html = generate_take_html(take_data, items_data)
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html)
                    temp_file = f.name
                webbrowser.open(f'file:///{temp_file}')

            def do_export():
                take_data, items_data = get_selected_data()
                if not take_data:
                    QMessageBox.warning(history_dialog, 'خطا', 'لطفاً یک سند از جدول انتخاب کنید.')
                    return
                file_path, _ = QFileDialog.getSaveFileName(
                    history_dialog, 'ذخیره خروجی HTML',
                    f"stock_take_{take_data['stock_take_no']}.html",
                    'HTML Files (*.html)'
                )
                if not file_path:
                    return
                html = generate_take_html(take_data, items_data)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                QMessageBox.information(history_dialog, 'خروجی HTML', f'گزارش ذخیره شد:\n{file_path}')

            def do_details():
                take_id = selected_take_id[0]
                if not take_id:
                    QMessageBox.warning(history_dialog, 'خطا', 'لطفاً یک سند از جدول انتخاب کنید.')
                    return
                load_details(take_id)

            def do_approve():
                """تایید سند و ثبت تراکنش‌های انبارگردانی"""
                take_id = selected_take_id[0]
                if not take_id:
                    QMessageBox.warning(history_dialog, 'خطا', 'لطفاً یک سند از جدول انتخاب کنید.')
                    return
                
                status = selected_status[0]
                if status not in ('DRAFT', 'PENDING_APPROVAL'):
                    QMessageBox.warning(history_dialog, 'خطا', 'این سند قبلاً تایید شده یا رد شده است.')
                    return
                
                # پیام تایید
                reply = QMessageBox.question(
                    history_dialog,
                    'تایید سند',
                    'آیا از تایید این سند انبارگردانی اطمینان دارید؟\n\n'
                    'پس از تایید:\n'
                    '- تراکنش‌های STOCK_TAKE در کاردکس ثبت می‌شوند\n'
                    '- موجودی انبار بروزرسانی می‌شود\n'
                    '- وضعیت سند به "تایید شده" تغییر می‌کند',
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    return
                
                try:
                    with self.db.connect() as local_conn:
                        local_conn.row_factory = None
                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        today_date = datetime.now().strftime('%Y-%m-%d')
                        
                        # دریافت اطلاعات سند
                        take = local_conn.execute("""
                            SELECT stock_take_no FROM stock_takes WHERE id = ?
                        """, (take_id,)).fetchone()
                        
                        if not take:
                            QMessageBox.warning(history_dialog, 'خطا', 'سند یافت نشد.')
                            return
                        
                        stock_take_no = take[0]
                        
                        # دریافت آیتم‌های سند
                        items = local_conn.execute("""
                            SELECT id, pallet_id, system_qty, actual_qty, difference, unit_price
                            FROM stock_take_items 
                            WHERE stock_take_id = ? AND status = 'PENDING'
                        """, (take_id,)).fetchall()
                        
                        transaction_count = 0
                        user_id = self.user_data.get('user_id', 1)
                        
                        for item in items:
                            item_id, pallet_id, sys_qty, actual_qty, diff, price = item
                            
                            # آپدیت وضعیت آیتم
                            local_conn.execute("""
                                UPDATE stock_take_items SET status = 'APPROVED' WHERE id = ?
                            """, (item_id,))
                            
                            if diff != 0:
                                transaction_type = 'IN' if diff > 0 else 'OUT'
                                abs_diff = abs(diff)
                                qty_in = abs_diff if diff > 0 else 0
                                qty_out = abs_diff if diff < 0 else 0
                                
                                # دریافت warehouse_id
                                wr = local_conn.execute("""
                                    SELECT warehouse_id FROM inventory_levels 
                                    WHERE pallet_id = ? LIMIT 1
                                """, (pallet_id,)).fetchone()
                                
                                if wr:
                                    warehouse_id = wr[0]
                                    
                                    # ثبت در inventory_transactions
                                    local_conn.execute("""
                                        INSERT INTO inventory_transactions (
                                            transaction_date, transaction_type, reference_type, reference_id,
                                            pallet_id, warehouse_id, qty_in, qty_out, unit_price, total_price,
                                            description, created_at
                                        )
                                        VALUES (?, ?, 'STOCK_TAKE', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        today_date, transaction_type, take_id, pallet_id, warehouse_id,
                                        qty_in, qty_out, price, abs_diff * price,
                                        f"انبارگردانی {stock_take_no} - مغایرت {diff:+d}",
                                        now
                                    ))
                                    
                                    # آپدیت موجودی
                                    local_conn.execute("""
                                        UPDATE inventory_levels 
                                        SET quantity = ? 
                                        WHERE pallet_id = ? AND warehouse_id = ?
                                    """, (actual_qty, pallet_id, warehouse_id))
                                    
                                    transaction_count += 1
                        
                        # آپدیت وضعیت سند
                        local_conn.execute("""
                            UPDATE stock_takes
                            SET status = 'APPROVED', approval_date = ?, approver_id = ?
                            WHERE id = ?
                        """, (now, user_id, take_id))
                        
                        local_conn.commit()
                    
                    QMessageBox.information(history_dialog, 'موفق', 
                        f'سند با موفقیت تایید شد.\n'
                        f'تعداد تراکنش‌های ثبت‌شده: {transaction_count} مورد')
                    
                    # بروزرسانی وضعیت در rows
                    for r in rows:
                        if r['id'] == take_id:
                            r['status'] = 'APPROVED'
                            break
                    
                    # بروزرسانی وضعیت دکمه‌ها
                    selected_status[0] = 'APPROVED'
                    _update_approve_button()
                    _update_reject_button()
                    
                    # رفرش جدول تاریخچه
                    history_table.setRowCount(len(rows))
                    for idx, row in enumerate(rows):
                        status_text = STATUS_LABELS.get(row['status'], row['status'])
                        values = [
                            str(row['id']),
                            row['stock_take_no'],
                            row['take_date'],
                            f"{row['total_system_qty']:,}",
                            f"{row['total_actual_qty']:,}",
                            f"{row['total_difference']:+,}",
                            f"{int(row['total_value_loss']):,} ریال",
                            status_text,
                        ]
                        for col, value in enumerate(values):
                            item = QTableWidgetItem(str(value))
                            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            item.setBackground(QColor('#dbeafe'))
                            if col == 7:  # ستون وضعیت
                                item.setForeground(QColor(STATUS_COLORS.get(row['status'], '#e2e8f0')))
                                item.setFont(QFont('Tahoma', 10, QFont.Bold))
                            elif row['total_difference'] < 0:
                                item.setForeground(QColor('#b91c1c'))
                            else:
                                item.setForeground(QColor('#1d4ed8'))
                            history_table.setItem(idx, col, item)
                        
                        # بازسازی دکمه انتخاب
                        select_btn = QPushButton('انتخاب')
                        select_btn.setFixedSize(70, 28)
                        select_btn
                        select_btn.clicked.connect(lambda checked, tid=row['id']: _on_select_row(tid))
                        history_table.setCellWidget(idx, 8, select_btn)
                    
                    # رفرش جزئیات
                    load_details(take_id)
                    
                except Exception as e:
                    import traceback
                    QMessageBox.critical(history_dialog, 'خطا', f'خطا در تایید سند:\n{traceback.format_exc()}')

            def do_reject():
                """رد سند انبارگردانی"""
                take_id = selected_take_id[0]
                if not take_id:
                    QMessageBox.warning(history_dialog, 'خطا', 'لطفاً یک سند از جدول انتخاب کنید.')
                    return
                
                status = selected_status[0]
                if status not in ('DRAFT', 'PENDING_APPROVAL'):
                    QMessageBox.warning(history_dialog, 'خطا', 'این سند قبلاً تایید شده یا رد شده است.')
                    return
                
                # پیام رد
                reply = QMessageBox.question(
                    history_dialog,
                    'رد سند',
                    'آیا از رد این سند انبارگردانی اطمینان دارید؟\n\n'
                    'پس از رد:\n'
                    '- هیچ تراکنشی در کاردکس ثبت نمی‌شود\n'
                    '- موجودی انبار تغییر نمی‌کند\n'
                    '- وضعیت سند به "رد شده" تغییر می‌کند\n'
                    '- این عمل قابل بازگشت نیست',
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    return
                
                try:
                    with self.db.connect() as local_conn:
                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        user_id = self.user_data.get('user_id', 1)
                        
                        # تغییر وضعیت آیتم‌ها به REJECTED
                        local_conn.execute("""
                            UPDATE stock_take_items SET status = 'REJECTED' WHERE stock_take_id = ?
                        """, (take_id,))
                        
                        # تغییر وضعیت سند به REJECTED
                        local_conn.execute("""
                            UPDATE stock_takes
                            SET status = 'REJECTED', approval_date = ?, approver_id = ?
                            WHERE id = ?
                        """, (now, user_id, take_id))
                        
                        local_conn.commit()
                    
                    QMessageBox.information(history_dialog, 'موفق', 'سند با موفقیت رد شد.')
                    
                    # بروزرسانی وضعیت در rows
                    for r in rows:
                        if r['id'] == take_id:
                            r['status'] = 'REJECTED'
                            break
                    
                    # بروزرسانی وضعیت دکمه‌ها
                    selected_status[0] = 'REJECTED'
                    _update_approve_button()
                    _update_reject_button()
                    
                    # رفرش جدول تاریخچه
                    history_table.setRowCount(len(rows))
                    for idx, row in enumerate(rows):
                        status_text = STATUS_LABELS.get(row['status'], row['status'])
                        values = [
                            str(row['id']),
                            row['stock_take_no'],
                            row['take_date'],
                            f"{row['total_system_qty']:,}",
                            f"{row['total_actual_qty']:,}",
                            f"{row['total_difference']:+,}",
                            f"{int(row['total_value_loss']):,} ریال",
                            status_text,
                        ]
                        for col, value in enumerate(values):
                            item = QTableWidgetItem(str(value))
                            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            item.setBackground(QColor('#dbeafe'))
                            if col == 7:  # ستون وضعیت
                                item.setForeground(QColor(STATUS_COLORS.get(row['status'], '#e2e8f0')))
                                item.setFont(QFont('Tahoma', 10, QFont.Bold))
                            elif row['total_difference'] < 0:
                                item.setForeground(QColor('#b91c1c'))
                            else:
                                item.setForeground(QColor('#1d4ed8'))
                            history_table.setItem(idx, col, item)
                        
                        # بازسازی دکمه انتخاب
                        select_btn = QPushButton('انتخاب')
                        select_btn.setFixedSize(70, 28)
                        select_btn
                        select_btn.clicked.connect(lambda checked, tid=row['id']: _on_select_row(tid))
                        history_table.setCellWidget(idx, 8, select_btn)
                    
                    # رفرش جزئیات
                    load_details(take_id)
                    
                except Exception as e:
                    import traceback
                    QMessageBox.critical(history_dialog, 'خطا', f'خطا در رد سند:\n{traceback.format_exc()}')
                    
                    # بروزرسانی وضعیت در rows
                    for r in rows:
                        if r['id'] == take_id:
                            r['status'] = 'APPROVED'
                            break
                    
                    # بروزرسانی وضعیت دکمه تایید
                    selected_status[0] = 'APPROVED'
                    _update_approve_button()
                    
                    # رفرش جدول تاریخچه
                    history_table.setRowCount(len(rows))
                    for idx, row in enumerate(rows):
                        status_text = STATUS_LABELS.get(row['status'], row['status'])
                        values = [
                            str(row['id']),
                            row['stock_take_no'],
                            row['take_date'],
                            f"{row['total_system_qty']:,}",
                            f"{row['total_actual_qty']:,}",
                            f"{row['total_difference']:+,}",
                            f"{int(row['total_value_loss']):,} ریال",
                            status_text,
                        ]
                        for col, value in enumerate(values):
                            item = QTableWidgetItem(str(value))
                            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            item.setBackground(QColor('#dbeafe'))
                            if col == 7:  # ستون وضعیت
                                item.setForeground(QColor(STATUS_COLORS.get(row['status'], '#e2e8f0')))
                                item.setFont(QFont('Tahoma', 10, QFont.Bold))
                            elif row['total_difference'] < 0:
                                item.setForeground(QColor('#b91c1c'))
                            else:
                                item.setForeground(QColor('#1d4ed8'))
                            history_table.setItem(idx, col, item)
                        
                        # بازسازی دکمه انتخاب
                        select_btn = QPushButton('انتخاب')
                        select_btn.setFixedSize(70, 28)
                        select_btn
                        select_btn.clicked.connect(lambda checked, tid=row['id']: _on_select_row(tid))
                        history_table.setCellWidget(idx, 8, select_btn)
                    
                    # رفرش جزئیات
                    load_details(take_id)
                    
                except Exception as e:
                    import traceback
                    QMessageBox.critical(history_dialog, 'خطا', f'خطا در تایید سند:\n{traceback.format_exc()}')

            # حذف اتصال cellClicked چون از دکمه استفاده می‌کنیم

            # دکمه‌ها
            btn_layout = QHBoxLayout()

            detail_btn = QPushButton('نمایش ریز اقلام')
            detail_btn.setObjectName('SecondaryButton')
            detail_btn.setMinimumHeight(45)
            detail_btn.clicked.connect(do_details)

            print_btn = QPushButton('پرینت گزارش')
            print_btn.setObjectName('PrimaryButton')
            print_btn.setMinimumHeight(45)
            print_btn.clicked.connect(do_print)

            export_btn = QPushButton('خروجی HTML')
            export_btn.setObjectName('SecondaryButton')
            export_btn.setMinimumHeight(45)
            export_btn.clicked.connect(do_export)

            # دکمه رد سند
            reject_btn = QPushButton('رد سند')
            reject_btn.setMinimumHeight(45)
            reject_btn

            def _update_reject_button():
                """بروزرسانی دکمه رد بر اساس وضعیت"""
                status = selected_status[0]
                if status in ('DRAFT', 'PENDING_APPROVAL'):
                    reject_btn.setEnabled(True)
                else:
                    reject_btn.setEnabled(False)

            # اتصال signal ها
            approve_btn.clicked.connect(do_approve)
            reject_btn.clicked.connect(do_reject)

            close_btn = QPushButton('بستن')
            close_btn.setObjectName('SecondaryButton')
            close_btn.setMinimumHeight(45)
            close_btn.clicked.connect(history_dialog.close)

            btn_layout.addWidget(detail_btn)
            btn_layout.addWidget(print_btn)
            btn_layout.addWidget(export_btn)
            btn_layout.addWidget(approve_btn)
            btn_layout.addWidget(reject_btn)
            btn_layout.addWidget(close_btn)
            layout.addLayout(btn_layout)

            # بارگذاری خودکار جزئیات اولین سند
            if rows:
                selected_take_id[0] = rows[0]['id']
                selected_status[0] = rows[0]['status']
                history_table.selectRow(0)
                load_details(rows[0]['id'])
                _update_approve_button()
                _update_reject_button()

            history_dialog.exec_()

        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'خطا', f'نمایش تاریخچه با خطا مواجه شد:\n\n{traceback.format_exc()}')

    def _print_report(self) -> None:
        discrepancies = self._get_discrepancies()
        if not discrepancies:
            QMessageBox.information(self, 'پرینت', 'مغایرتی برای پرینت وجود ندارد.')
            return

        html = self._generate_html_report(discrepancies)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            temp_file = f.name

        webbrowser.open(f'file:///{temp_file}')

    def _export_html(self) -> None:
        discrepancies = self._get_discrepancies()
        if not discrepancies:
            QMessageBox.information(self, 'خروجی', 'مغایرتی برای خروجی وجود ندارد.')
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, 'ذخیره خروجی HTML', 'stock_take_report.html', 'HTML Files (*.html)'
        )
        if not file_path:
            return

        html = self._generate_html_report(discrepancies)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)

        QMessageBox.information(self, 'خروجی HTML', f'گزارش ذخیره شد:\n{file_path}')

    def _generate_html_report(self, discrepancies: List[Dict]) -> str:
        warehouse_name = self.warehouse_combo.currentText()
        today = datetime.now()
        stock_take_no = f"ST-{today.strftime('%Y%m%d')}-001"

        html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>گزارش انبارگردانی {stock_take_no}</title>
    <style>
        body {{ font-family: Tahoma, Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #46505f; border-bottom: 3px solid #2563eb; padding-bottom: 15px; }}
        .header-info {{ display: flex; justify-content: space-between; margin-bottom: 20px; padding: 15px; background: #f1f5f9; border-radius: 6px; flex-wrap: wrap; }}
        .header-info div {{ margin: 5px 15px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .summary-card {{ padding: 15px; border-radius: 6px; text-align: center; }}
        .summary-card.total {{ background: #dbeafe; border: 2px solid #2563eb; }}
        .summary-card.counted {{ background: #dcfce7; border: 2px solid #059669; }}
        .summary-card.shortage {{ background: #fee2e2; border: 2px solid #dc2626; }}
        .summary-card.surplus {{ background: #fef3c7; border: 2px solid #f59e0b; }}
        .summary-card .label {{ font-size: 14px; color: #64748b; margin-bottom: 5px; }}
        .summary-card .value {{ font-size: 24px; font-weight: bold; color: #46505f; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #46505f; color: white; padding: 12px; text-align: center; font-size: 14px; }}
        td {{ padding: 10px; text-align: center; border-bottom: 1px solid #e2e8f0; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        .discrepancy-negative {{ background: #fee2e2 !important; color: #dc2626; font-weight: bold; }}
        .discrepancy-positive {{ background: #dcfce7 !important; color: #059669; font-weight: bold; }}
        .footer {{ margin-top: 40px; text-align: center; color: #64748b; font-size: 12px; border-top: 2px solid #e2e8f0; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>گزارش انبارگردانی</h1>
        <div class="header-info">
            <div><strong>شماره:</strong> {stock_take_no}</div>
            <div><strong>تاریخ:</strong> {today.strftime('%Y-%m-%d')}</div>
            <div><strong>انبار:</strong> {warehouse_name}</div>
            <div><strong>وضعیت:</strong> تاییدشده</div>
        </div>
        <div class="summary">
            <div class="summary-card total">
                <div class="label">جمع سیستم</div>
                <div class="value">{sum(d['system_qty'] for d in discrepancies):,}</div>
            </div>
            <div class="summary-card counted">
                <div class="label">جمع واقعی</div>
                <div class="value">{sum(d['actual_qty'] for d in discrepancies):,}</div>
            </div>
            <div class="summary-card shortage">
                <div class="label">ارزش کسری</div>
                <div class="value">{abs(int(sum(d['value_diff'] for d in discrepancies if d['value_diff'] < 0))):,} ریال</div>
            </div>
            <div class="summary-card surplus">
                <div class="label">ارزش اضافی</div>
                <div class="value">{int(sum(d['value_diff'] for d in discrepancies if d['value_diff'] > 0)):,} ریال</div>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>ردیف</th>
                    <th>کد</th>
                    <th>نام</th>
                    <th>سیستم</th>
                    <th>میانگین</th>
                    <th>واقعی</th>
                    <th>مغایرت</th>
                    <th>ارزش</th>
                    <th>دلیل</th>
                </tr>
            </thead>
            <tbody>
"""

        for d in discrepancies:
            row_class = ''
            if d['discrepancy'] < 0:
                row_class = 'discrepancy-negative'
            elif d['discrepancy'] > 0:
                row_class = 'discrepancy-positive'

            html += f"""
                <tr class="{row_class}">
                    <td>{d['row']}</td>
                    <td>{d['pallet_code']}</td>
                    <td>{d['pallet_name']}</td>
                    <td>{d['system_qty']:,}</td>
                    <td>{int(d['unit_cost']):,} ریال</td>
                    <td>{d['actual_qty']:,}</td>
                    <td>{d['discrepancy']:+,}</td>
                    <td>{int(d['value_diff']):+,} ریال</td>
                    <td>{d['reason'] if d['reason'] else '-'}</td>
                </tr>
"""

        html += f"""
            </tbody>
        </table>
        <div class="footer">
            <p>تاریخ و ساعت تولید: {today.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""

        return html
