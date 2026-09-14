# -*- coding: utf-8 -*-
"""
PalletItemsTable - نسخه کامل با هزارگان و ثبت صحیح
"""
from typing import Any, Dict, List
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from app.core.database import DatabaseManager
from app.core.pallet_service import PalletService


class PalletItemsTable(QWidget):
    avg_price_signal = pyqtSignal(int)

    def __init__(self, db, parent=None, show_price_avg=False, suggested_fill=True):
        super().__init__(parent)
        self.db = db
        self.show_avg = show_price_avg
        self.suggested_fill = suggested_fill
        self.pallets = []
        self.stocks = {}
        self.prices = {}
        self._load()
        self._make_ui()
        self._add_editable_row()

    def _load(self):
        """بارگذاری پالت‌ها، موجودی و قیمت میانگین از کلاس مرکزی PalletService"""
        try:
            from app.core.pallet_service import PalletService
            self._pallet_service = getattr(self, '_pallet_service', None) or PalletService(self.db)
            self._pallet_service.reload()
            self.pallets = self._pallet_service.all_pallets()
            self.stocks = self._pallet_service.stock_map()
            self.prices = self._pallet_service.prices_map()
            self.prices = {k: int(v) for k, v in self.prices.items()}
            print(f'pallet_items_table: {len(self.prices)} prices loaded (via PalletService)')
        except Exception as e:
            print('PalletItemsTable load error:', str(e))
            self.pallets = []
            self.stocks = {}
            self.prices = {}


    def _make_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.setContentsMargins(0, 0, 0, 0)
        
        btns = QHBoxLayout()
        ab = QPushButton('افزودن ردیف جدید')
        ab.setObjectName('SecondaryButton')
        ab.setMinimumWidth(120)
        ab.clicked.connect(self._add_editable_row)
        btns.addWidget(ab)
        btns.addStretch()
        
        if self.show_avg:
            # [UNIFIED-BAR] نوار یکپارچه قیمت و حاشیه (یکسان در پیش‌فاکتور/رسید/حواله)
            self._last_avg = 0
            self.avg_lbl = QLabel('قیمت میانگین:')
            self.avg_lbl.setObjectName('AvgPriceLabel')
            btns.addWidget(self.avg_lbl)
            self.avg_val = QLabel('-')
            self.avg_val.setObjectName('AvgPriceValue')
            btns.addWidget(self.avg_val)
            self.pct_lbl = QLabel('درصد markup روی بها:')
            self.pct_lbl.setObjectName('IssuePctLabel')
            btns.addWidget(self.pct_lbl)
            self.pct_edit = QLineEdit()
            self.pct_edit.setObjectName('IssuePctEdit')
            self.pct_edit.setText('40')
            self.pct_edit.setPlaceholderText('40')
            self.pct_edit.setText('40')
            self.pct_edit.setFixedWidth(70)
            self.pct_edit.setAlignment(Qt.AlignCenter)
            self.pct_edit.textChanged.connect(self._on_percent_change)
            btns.addWidget(self.pct_edit)
            self.suggested_lbl = QLabel('قیمت پیشنهادی: -')
            self.suggested_lbl.setObjectName('IssueCalcValue')
            btns.addWidget(self.suggested_lbl)
            self.margin_lbl = QLabel('حاشیه سود روی فروش: -')
            self.margin_lbl.setObjectName('VatAmountLabel')
            btns.addWidget(self.margin_lbl)
            for _lb in (self.avg_lbl, self.avg_val, self.pct_lbl, self.suggested_lbl, self.margin_lbl):
                _lb.setFixedHeight(38)
            self.pct_edit.setFixedHeight(34)

        btns.addStretch()

        self.tot_lbl = QLabel('جمع کل: 0 ریال')
        self.tot_lbl.setStyleSheet('color: #3b82f6; font-size: 16px; font-weight: bold;')
        self.stock_status_lbl = QLabel('')
        self.stock_status_lbl.setStyleSheet('color:#64748b;font-size:12px;font-weight:bold;')
        btns.addWidget(self.stock_status_lbl, 1)
        self.del_row_btn = QPushButton('🗑 حذف ردیف')
        self.del_row_btn.setObjectName('SecondaryButton')
        self.del_row_btn.clicked.connect(self._delete_current_row)
        btns.addWidget(self.del_row_btn)
        btns.addWidget(self.tot_lbl)
        lay.addLayout(btns)

        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels(['ردیف', 'پالت', 'تعداد', 'قیمت واحد', 'مبلغ کل', 'توضیح', 'عملیات'])
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.tbl.verticalHeader().setDefaultSectionSize(46)
        
        self.tbl
        
        h = self.tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Fixed)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Fixed)
        h.setSectionResizeMode(3, QHeaderView.Fixed)
        h.setSectionResizeMode(4, QHeaderView.Fixed)
        h.setSectionResizeMode(5, QHeaderView.Stretch)
        h.setSectionResizeMode(6, QHeaderView.Fixed)
        self.tbl.setColumnWidth(0, 45)
        self.tbl.setColumnWidth(2, 110)
        self.tbl.setColumnWidth(3, 150)
        self.tbl.setColumnWidth(4, 175)
        self.tbl.setColumnWidth(6, 55)
        
        lay.addWidget(self.tbl)

    def _add_editable_row(self):
        """افزودن ردیف جدید قابل ویرایش"""
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        
        # شماره ردیف
        no_item = QTableWidgetItem(str(row + 1))
        no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
        no_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        no_item.setBackground(QColor('#8a94a3'))
        self.tbl.setItem(row, 0, no_item)
        
        # کمبو پالت
        combo = QComboBox()
        combo.setMinimumHeight(40)
        combo

        combo.addItem('انتخاب پالت', 0)
        for p in self.pallets:
            pid = p['id']
            s = self.stocks.get(pid, 0)
            a = self.prices.get(pid, 0)
            txt = "{} | {} (موجودی: {:,}".format(p['code'], p['name'], s)
            if a > 0:
                txt += " | میانگین: {:,}".format(a)
            txt += ")"
            combo.addItem(txt, pid)
        combo.currentIndexChanged.connect(lambda idx, r=row: self._on_pallet_change(r))
        self.tbl.setCellWidget(row, 1, combo)
        
        # اسپین تعداد
        spin = QSpinBox()
        spin.setMinimumHeight(40)
        spin.setRange(0, 1000000)
        spin.setAlignment(Qt.AlignCenter)
        spin
        spin.valueChanged.connect(lambda v, r=row: self._recalc_row(r))
        spin.valueChanged.connect(lambda v, r=row: self._update_stock_status(r))
        self.tbl.setCellWidget(row, 2, spin)
        
        # فیلد قیمت با هزارگان
        price_edit = QLineEdit()
        price_edit.setAlignment(Qt.AlignCenter)
        price_edit.setPlaceholderText('قیمت به ریال')
        price_edit
        price_edit.textChanged.connect(lambda: self._on_price_change(row))
        self.tbl.setCellWidget(row, 3, price_edit)
        
        # مبلغ کل
        total_item = QTableWidgetItem('0')
        total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        total_item.setBackground(QColor('#8a94a3'))
        self.tbl.setItem(row, 4, total_item)
        
        # توضیح
        note_item = QTableWidgetItem('')
        note_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tbl.setItem(row, 5, note_item)
        from PyQt5.QtCore import Qt as _Qt
        for _cc in range(0, 5):
            _it = self.tbl.item(row, _cc)
            if _it is not None:
                _it.setFlags(_it.flags() & ~_Qt.ItemIsEditable)

        
        # دکمه ثبت
        save_btn = QPushButton('ثبت')
        save_btn
        save_btn.clicked.connect(lambda checked, r=row: self._commit_row(r))
        self.tbl.setCellWidget(row, 6, save_btn)
        
        self._update_total()

    def _on_price_change(self, row):
        """تغییر قیمت -> فرمت هزارگان + بروزرسانی مبلغ کل"""
        price_edit = self.tbl.cellWidget(row, 3)
        if not price_edit:
            return
        digits = ''.join(c for c in price_edit.text() if c.isdigit())
        price = int(digits) if digits else 0
        price_edit.blockSignals(True)
        price_edit.setText('{:,}'.format(price))
        price_edit.blockSignals(False)
        self._recalc_row(row)

    def _recalc_row(self, row):
        """محاسبه مبلغ کل ردیف + جمع کل (بدون نیاز به focus)"""
        price_edit = self.tbl.cellWidget(row, 3)
        total_item = self.tbl.item(row, 4)
        qty_spin = self.tbl.cellWidget(row, 2)
        if not price_edit or not total_item or not qty_spin:
            return
        digits = ''.join(c for c in price_edit.text() if c.isdigit())
        price = int(digits) if digits else 0
        qty = qty_spin.value()
        total_item.setText('{:,}'.format(price * qty))
        self._update_total()



    def _current_pct(self):
        txt = self.pct_edit.text() if hasattr(self, 'pct_edit') else ''
        digits = ''.join(ch for ch in txt if ch.isdigit())
        return float(digits) if digits else 0.0

    def _on_percent_change(self):
        """[UNIFIED] قیمت پیشنهادی = میانگین × (1 + درصد/100) | حاشیه روی فروش = درصد/(100+درصد)"""
        if not self.show_avg or not hasattr(self, 'suggested_lbl'):
            return
        avg = getattr(self, '_last_avg', 0) or 0
        pct = self._current_pct()
        if avg > 0:
            self.suggested_lbl.setText('قیمت پیشنهادی: {:,} ریال'.format(int(avg * (1 + pct / 100.0))))
        else:
            self.suggested_lbl.setText('قیمت پیشنهادی: -')
        if pct > 0:
            self.margin_lbl.setText('حاشیه سود روی فروش: {:.1f}%'.format(pct / (100.0 + pct) * 100.0))
        else:
            self.margin_lbl.setText('حاشیه سود روی فروش: -')
    def _on_pallet_change(self, row):
        """وقتی پالت تغییر کرد"""
        combo = self.tbl.cellWidget(row, 1)
        if not combo:
            return
        
        pid = combo.currentData()
        
        if not pid or pid == 0:
            if self.show_avg:
                self.avg_val.setText('-')
            return
        
        avg_price = self.prices.get(pid, 0)
        self._last_avg = int(avg_price or 0)
        if self.show_avg:
            if avg_price > 0:
                self.avg_val.setText('{:,} ریال'.format(avg_price))
            else:
                self.avg_val.setText('بدون سابقه')
            self._on_percent_change()
        self.avg_price_signal.emit(avg_price)
        # [FIX-PRICE] پر کردن قیمت واحد با قیمت پیشنهادی (میانگین + درصد) — قابل ویرایش
        price_edit = self.tbl.cellWidget(row, 3)
        if price_edit is not None and avg_price > 0:
            if getattr(self, 'suggested_fill', True):
                suggested = int(avg_price * (1 + self._current_pct() / 100.0))
            else:
                suggested = int(avg_price)
            price_edit.blockSignals(True)
            price_edit.setText('{:,}'.format(suggested))
            price_edit.blockSignals(False)
            self._recalc_row(row)
            stock = self.stocks.get(pid, 0)
        spin = self.tbl.cellWidget(row, 2)
        if spin:
            spin.setMaximum(1000000)
            try:
                _pid = combo.currentData() if combo else None
                _st = int(self.stocks.get(_pid, 0) or 0) if _pid else 0
            except Exception:
                _st = 0
            spin.setToolTip('موجودی انبار: {:,}'.format(_st))
            self._update_stock_status(row)

    def _delete_current_row(self):
        """[DEL-ROW] حذف ردیف انتخاب‌شده (یا آخرین ردیف)"""
        row = self.tbl.currentRow()
        if row < 0:
            row = self.tbl.rowCount() - 1
        if row < 0:
            return
        if self.tbl.rowCount() <= 1:
            combo = self.tbl.cellWidget(0, 1)
            spin = self.tbl.cellWidget(0, 2)
            if combo:
                combo.setCurrentIndex(0)
            if spin:
                spin.setValue(0)
            try:
                self._update_stock_status(0)
            except Exception:
                pass
            return
        self.tbl.removeRow(row)
        for r in range(self.tbl.rowCount()):
            it = self.tbl.item(r, 0)
            if it:
                it.setText(str(r + 1))
            try:
                self._recalc_row(r)
            except Exception:
                pass
        try:
            self._update_stock_status(min(row, self.tbl.rowCount() - 1))
        except Exception:
            pass

    def _update_stock_status(self, row):
        """[STOCK-STATUS] نمایش زنده موجودی/درخواست/کسری"""
        if not hasattr(self, 'stock_status_lbl'):
            return
        combo = self.tbl.cellWidget(row, 1)
        spin = self.tbl.cellWidget(row, 2)
        if not combo or not spin:
            return
        pid = combo.currentData()
        if not pid or pid == 0:
            self.stock_status_lbl.setText('')
            return
        stock = int(self.stocks.get(pid, 0) or 0)
        requested = spin.value()
        shortage = max(0, requested - stock)
        code = next((p['code'] for p in self.pallets if p['id'] == pid), '')
        if shortage > 0:
            self.stock_status_lbl.setText('⚠ {}: موجودی {:,} | درخواست {:,} | کسری {:,}'.format(code, stock, requested, shortage))
            self.stock_status_lbl.setStyleSheet('color:#ef4444;font-size:12px;font-weight:bold;')
        elif requested > 0:
            self.stock_status_lbl.setText('✓ {}: موجودی {:,} | درخواست {:,}'.format(code, stock, requested))
            self.stock_status_lbl.setStyleSheet('color:#10b981;font-size:12px;font-weight:bold;')
        else:
            self.stock_status_lbl.setText('')

    def _commit_row(self, row):
        """ثبت ردیف و تبدیل به فقط خواندنی"""
        combo = self.tbl.cellWidget(row, 1)
        spin = self.tbl.cellWidget(row, 2)
        price_edit = self.tbl.cellWidget(row, 3)
        
        if not combo:
            return
        
        pid = combo.currentData()
        if not pid or pid == 0:
            QMessageBox.warning(self, 'خطا', 'لطفاً پالت را انتخاب کنید.')
            return
        

        # [NO-DUP] جلوگیری از ثبت دو ردیف برای یک پالت
        for _other in range(self.tbl.rowCount()):
            if _other == row:
                continue
            _oi = self.tbl.item(_other, 1)
            if _oi is not None and _oi.data(Qt.UserRole) == pid:
                QMessageBox.warning(self, 'ردیف تکراری',
                    'این پالت در ردیف {:,} قبلاً ثبت شده است.\nلطفاً تعداد/قیمت همان ردیف را ویرایش کنید.'.format(_other + 1))
                return
            _oc = self.tbl.cellWidget(_other, 1)
            if isinstance(_oc, QComboBox) and _oc.currentData() == pid:
                QMessageBox.warning(self, 'ردیف تکراری',
                    'این پالت در ردیف {:,} انتخاب شده است؛ هر پالت فقط یک ردیف.'.format(_other + 1))
                return
        qty = spin.value() if spin else 0
        if qty <= 0:
            QMessageBox.warning(self, 'خطا', 'تعداد باید بیشتر از صفر باشد.')
            return
        
        stock = self.stocks.get(pid, 0)
        if qty > stock:
            QMessageBox.warning(self, 'خطا', 'تعداد ({:,}) بیشتر از موجودی ({:,}) است.'.format(qty, stock))
            return
        
        # اعتبارسنجی قیمت با هزارگان
        price_text = price_edit.text() if price_edit else '0'
        digits = ''.join(c for c in price_text if c.isdigit())
        price = int(digits) if digits else 0
        
        if price <= 0:
            QMessageBox.warning(self, 'خطا', 'لطفاً قیمت را وارد کنید.')
            return
        
        # نمایش هزارگان در قیمت
        price_edit.blockSignals(True)
        price_edit.setText('{:,}'.format(price))
        price_edit.blockSignals(False)
        
        # بررسی قیمت نسبت به میانگین
        avg_price = self.prices.get(pid, 0)
        if avg_price > 0 and price < avg_price:
            reply = QMessageBox.question(
                self, 'تأیید قیمت',
                'قیمت ({:,} ریال) کمتر از قیمت میانگین ({:,} ریال) است.\n\nآیا از ثبت این قیمت اطمینان دارید؟'.format(price, avg_price),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # محاسبه مبلغ کل
        total = qty * price
        
        # تبدیل به فقط خواندنی
        pallet_display = combo.currentText().split(' (')[0]
        pallet_item = QTableWidgetItem(pallet_display)
        pallet_item.setFlags(pallet_item.flags() & ~Qt.ItemIsEditable)
        pallet_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pallet_item.setData(Qt.UserRole, pid)
        self.tbl.setItem(row, 1, pallet_item)
        
        qty_item = QTableWidgetItem('{:,}'.format(qty))
        qty_item.setFlags(qty_item.flags() & ~Qt.ItemIsEditable)
        qty_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.tbl.setItem(row, 2, qty_item)
        
        price_item = QTableWidgetItem('{:,}'.format(price))
        price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
        price_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.tbl.setItem(row, 3, price_item)
        from PyQt5.QtCore import Qt as _Qt
        for _cc in range(0, 5):
            _it = self.tbl.item(row, _cc)
            if _it is not None:
                _it.setFlags(_it.flags() & ~_Qt.ItemIsEditable)

        
        total_item = self.tbl.item(row, 4)
        if total_item:
            total_item.setText('{:,}'.format(total))
        
        # حذف ویجت‌های قبلی
        self.tbl.removeCellWidget(row, 1)
        self.tbl.removeCellWidget(row, 2)
        self.tbl.removeCellWidget(row, 3)
        
        status_lbl = QLabel('ثبت شد')
        status_lbl.setStyleSheet('color: #10b981; font-weight: bold; font-size: 12px;')
        status_lbl.setAlignment(Qt.AlignCenter)
        self.tbl.setCellWidget(row, 6, status_lbl)
        
        self._update_total()

    def _update_total(self):
        total = 0
        for row in range(self.tbl.rowCount()):
            total_item = self.tbl.item(row, 4)
            if total_item:
                try:
                    total += int(total_item.text().replace(',', ''))
                except Exception:
                    pass
        self.tot_lbl.setText('جمع کل: {:,} ریال'.format(total))

    def get_items(self):
        items = []
        for row in range(self.tbl.rowCount()):
            widget = self.tbl.cellWidget(row, 6)
            if isinstance(widget, QPushButton):
                continue
            
            pallet_item = self.tbl.item(row, 1)
            qty_item = self.tbl.item(row, 2)
            price_item = self.tbl.item(row, 3)
            note_item = self.tbl.item(row, 5)
            
            if not pallet_item or not qty_item or not price_item:
                continue
            
            pid = pallet_item.data(Qt.UserRole)
            if not pid:
                continue
            
            try:
                qty = int(qty_item.text().replace(',', ''))
            except Exception:
                continue
            
            try:
                price = int(price_item.text().replace(',', ''))
            except Exception:
                price = 0
            
            note = note_item.text() if note_item else ''
            
            items.append({
                'row_no': row + 1,
                'pallet_id': pid,
                'quantity': qty,
                'unit_price': price,
                'total_amount': qty * price,
                'note': note,
            })
        return items

    def get_total_price(self):
        return sum(i['total_price'] for i in self.get_items())

    def clear(self):
        self.tbl.setRowCount(0)
        self.tot_lbl.setText('جمع کل: 0 ریال')
        if self.show_avg:
            self._last_avg = 0
            self.avg_val.setText('-')
            if hasattr(self, 'pct_edit'):
                self.pct_edit.setText('40')
            if hasattr(self, 'suggested_lbl'):
                self.suggested_lbl.setText('قیمت پیشنهادی: -')
            if hasattr(self, 'margin_lbl'):
                self.margin_lbl.setText('حاشیه سود روی فروش: -')
        self._add_editable_row()
    @property
    def table(self):
        return self.tbl
