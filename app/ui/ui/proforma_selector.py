# -*- coding: utf-8 -*-
'''Proforma Selector Dialog - for linking proformas to warehouse issues'''
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox,
    QDateEdit,
    QComboBox,
)
from app.core.jalali import jalali_date_display_from_iso, today_iso_date


class ProformaSelectorDialog(QDialog):
    '''Dialog to select a proforma for linking to warehouse issue'''
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_proforma_id = None
        self.selected_items = []
        
        self.setWindowTitle('انتخاب پیش‌فاکتور')
        self.resize(900, 600)
        self.setLayoutDirection(Qt.RightToLeft)
        
        self._build_ui()
        self._load_proformas()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Info label
        info = QLabel('پیش‌فاکتور مورد نظر را انتخاب کنید:')
        info.setStyleSheet('font-size: 14px; font-weight: bold;')
        layout.addWidget(info)
        
        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            'شماره', 'تاریخ', 'مشتری', 'تعداد ردیف', 'جمع کل', 'وضعیت'
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        select_btn = QPushButton('انتخاب و بارگذاری آیتم‌ها')
        select_btn.setObjectName('PrimaryButton')
        select_btn.setMinimumHeight(40)
        select_btn.clicked.connect(self._on_select)
        cancel_btn = QPushButton('انصراف')
        cancel_btn.setObjectName('SecondaryButton')
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(select_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def _load_proformas(self):
        '''Load non-converted proformas'''
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute('''
                    SELECT pi.id, pi.proforma_no, pi.proforma_date, pi.total_amount,
                           pi.status, p.first_name || ' ' || p.last_name,
                           (SELECT COUNT(*) FROM proforma_invoice_items WHERE proforma_id=pi.id)
                    FROM proforma_invoices pi
                    LEFT JOIN persons p ON p.id=pi.customer_id
                    WHERE pi.status != 'CONVERTED'
                    ORDER BY pi.id DESC
                ''').fetchall()
                
                self.table.setRowCount(len(rows))
                for idx, r in enumerate(rows):
                    status_labels = {'DRAFT': 'پیش‌نویس', 'FINALIZED': 'نهایی', 'CANCELLED': 'باطل شده'}
                    vals = [
                        r[1],
                        jalali_date_display_from_iso(r[2]) if r[2] else '-',
                        r[5] or '-',
                        str(r[6]),
                        '{:,} ریال'.format(int(r[3] or 0)),
                        status_labels.get(r[4], r[4] or '-'),
                    ]
                    for col, v in enumerate(vals):
                        item = QTableWidgetItem(str(v))
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        self.table.setItem(idx, col, item)
                
                self.table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در بارگذاری:\n' + str(e))
    
    def _on_select(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'توجه', 'لطفاً یک پیش‌فاکتور انتخاب کنید.')
            return
        
        proforma_id = int(self.table.item(row, 0).text())
        
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                items = conn.execute('''
                    SELECT pii.pallet_id, p.code, p.name, pii.quantity, pii.unit_price, pii.total_amount
                    FROM proforma_invoice_items pii
                    JOIN pallets p ON p.id=pii.pallet_id
                    WHERE pii.proforma_id=?
                    ORDER BY pii.row_no
                ''', (proforma_id,)).fetchall()
                
                self.selected_proforma_id = proforma_id
                self.selected_items = []
                for it in items:
                    self.selected_items.append({
                        'pallet_id': it[0],
                        'code': it[1],
                        'name': it[2],
                        'quantity': int(it[3] or 0),
                        'unit_price': int(it[4] or 0),
                        'total_amount': int(it[5] or 0),
                    })
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در دریافت آیتم‌ها:\n' + str(e))
    
    def get_selected_proforma_id(self):
        return self.selected_proforma_id
    
    def get_selected_items(self):
        return self.selected_items
