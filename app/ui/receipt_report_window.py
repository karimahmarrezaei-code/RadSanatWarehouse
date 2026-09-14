# -*- coding: utf-8 -*-
import os
import tempfile
from PyQt5.QtCore import Qt, QUrl, QDate
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTableWidget, QTableWidgetItem, QFileDialog, 
                             QMessageBox, QTabWidget, QTextBrowser, QComboBox, QWidget,
                             QFrame, QHeaderView, QAbstractItemView, QDateEdit)
from app.core.jalali import today_iso_date, jalali_date_display_from_iso

STATUS_FA = {
    'CONFIRMED': 'تایید شده', 'OPEN': 'باز', 'PARTIAL': 'جزئی',
    'COMPLETED': 'تکمیل شده', 'CANCELLED': 'لغو شده'
}

class ReceiptReportWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('گزارش ورود کالا (رسیدها)')
        self.resize(1180, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        
        self._ids = []
        self._refs = []
        self._loads = []
        self._sups = []
        
        self._build()
        self._load_persons()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        # --- نوار ابزار بالا (دکمه‌ها و فیلترها) ---
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName('ToolbarFrame')
        toolbar_frame.setStyleSheet("""
            QFrame#ToolbarFrame {
                
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        bar = QHBoxLayout(toolbar_frame)
        bar.setContentsMargins(10, 10, 10, 10)
        
        # فیلد از تاریخ + لیبل شمسی
        bar.addWidget(QLabel('از تاریخ:'))
        self.from_edit = QDateEdit()
        self.from_edit.setCalendarPopup(True)
        self.from_edit.setDisplayFormat('yyyy-MM-dd')
        self.from_edit.setFixedWidth(130)
        self.from_edit.dateChanged.connect(self._update_from_jalali)
        bar.addWidget(self.from_edit)
        
        self.from_jalali_lbl = QLabel('-')
        self.from_jalali_lbl.setStyleSheet("color: #0284c7; font-weight: bold; padding: 0 5px;")
        bar.addWidget(self.from_jalali_lbl)
        
        # فیلد تا تاریخ + لیبل شمسی
        bar.addWidget(QLabel('تا تاریخ:'))
        self.to_edit = QDateEdit()
        self.to_edit.setCalendarPopup(True)
        self.to_edit.setDisplayFormat('yyyy-MM-dd')
        self.to_edit.setFixedWidth(130)
        self.to_edit.dateChanged.connect(self._update_to_jalali)
        bar.addWidget(self.to_edit)
        
        self.to_jalali_lbl = QLabel('-')
        self.to_jalali_lbl.setStyleSheet("color: #0284c7; font-weight: bold; padding: 0 5px;")
        bar.addWidget(self.to_jalali_lbl)
        
        bar.addWidget(QLabel('تأمین‌کننده:'))
        self.person_combo = QComboBox()
        self.person_combo.setMinimumWidth(200)
        bar.addWidget(self.person_combo)
        
        bar.addStretch()
        
        rb = QPushButton('🔄 بروزرسانی')
        rb.setObjectName('PrimaryButton')
        rb.clicked.connect(self.refresh)
        bar.addWidget(rb)
        
        pv = QPushButton('🌐 پیش‌نمایش وب')
        pv.setObjectName('SecondaryButton')
        pv.clicked.connect(self._open_web)
        bar.addWidget(pv)
        
        ex = QPushButton('💾 اکسل')
        ex.setObjectName('SuccessButton')
        ex.clicked.connect(self._export)
        bar.addWidget(ex)
        
        root.addWidget(toolbar_frame)

        # --- تب‌ها ---
        self.tabs = QTabWidget()
        
        # تب ۱: گزارش
        w1 = QWidget()
        l1 = QVBoxLayout(w1)
        l1.setSpacing(10)
        
        self.tbl = QTableWidget(0, 11)
        self.tbl.setHorizontalHeaderLabels([
            'شماره رسید', 'شماره مرجع', 'مرحله', 'تاریخ', 'تأمین‌کننده', 
            'راننده', 'بارنامه', 'تعداد مرحله', 'تعداد کل بار', 'مبلغ کل', 'وضعیت'
        ])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setDefaultSectionSize(32)
        self.tbl.currentCellChanged.connect(self._on_select)
        l1.addWidget(self.tbl)
        
        l1.addWidget(QLabel('📦 اقلام رسید انتخاب‌شده:'))
        self.itbl = QTableWidget(0, 5)
        self.itbl.setHorizontalHeaderLabels(['کد پالت', 'نام پالت', 'تعداد', 'قیمت واحد', 'مبلغ کل'])
        self.itbl.verticalHeader().setVisible(False)
        self.itbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.itbl.setAlternatingRowColors(True)
        self.itbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.itbl.horizontalHeader().setStretchLastSection(True)
        self.itbl.verticalHeader().setDefaultSectionSize(30)
        l1.addWidget(self.itbl)
        
        self.tabs.addTab(w1, '📋 گزارش')
        
        # تب ۲: پیش‌نمایش وب
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.tabs.addTab(self.browser, '🌐 پیش‌نمایش وب')
        
        root.addWidget(self.tabs)
        
        # تنظیم تاریخ پیش‌فرض
        from datetime import date
        first_day_of_month = date.fromisoformat(today_iso_date()).replace(day=1)
        self.from_edit.setDate(QDate.fromString(first_day_of_month.isoformat(), 'yyyy-MM-dd'))
        self.to_edit.setDate(QDate.fromString(today_iso_date(), 'yyyy-MM-dd'))

        # بروزرسانی اولیه لیبل‌های شمسی
        self._update_from_jalali()
        self._update_to_jalali()

    def _load_persons(self):
        with self.db.connect() as conn:
            try:
                rows = conn.execute("SELECT DISTINCT p.id, (p.first_name||' '||p.last_name) n FROM persons p JOIN warehouse_receipts wr ON wr.supplier_id=p.id ORDER BY p.id").fetchall()
            except Exception:
                rows = conn.execute("SELECT id, (first_name||' '||last_name) n FROM persons ORDER BY id").fetchall()
        
        self.person_combo.clear()
        self.person_combo.addItem('همه تأمین‌کنندگان', None)
        for r in rows:
            self.person_combo.addItem((r['n'] or str(r['id'])), r['id'])

    def _update_from_jalali(self):
        iso_date = self.from_edit.date().toString('yyyy-MM-dd')
        self.from_jalali_lbl.setText(jalali_date_display_from_iso(iso_date))

    def _update_to_jalali(self):
        iso_date = self.to_edit.date().toString('yyyy-MM-dd')
        self.to_jalali_lbl.setText(jalali_date_display_from_iso(iso_date))

    def refresh(self):
        # خواندن تاریخ از QDateEdit
        f = self.from_edit.date().toString('yyyy-MM-dd')
        t = self.to_edit.date().toString('yyyy-MM-dd')
        c = self.person_combo.currentData()
        
        q = ("SELECT wr.*, il.Reference_no AS ref, il.total_load_qty AS tlq, d.first_name||' '||d.last_name AS drv, "
             "COALESCE(p.first_name||' '||p.last_name,'-') AS cust, "
             "COALESCE(SUM(ri.qty),0) AS q, COALESCE(SUM(ri.qty*ri.unit_price),0) AS amt "
             "FROM warehouse_receipts wr "
             "LEFT JOIN inbound_loads il ON il.id=wr.inbound_load_id "
             "LEFT JOIN persons p ON p.id=wr.supplier_id "
             "LEFT JOIN persons d ON d.id=wr.driver_id "
             "LEFT JOIN warehouse_receipt_items ri ON ri.receipt_id=wr.id")
        
        conds, params = [], []
        if f: conds.append("wr.receipt_date >= ?"); params.append(f)
        if t: conds.append("wr.receipt_date <= ?"); params.append(t)
        if c is not None: conds.append("wr.supplier_id = ?"); params.append(c)
        
        if conds: q += " WHERE " + " AND ".join(conds)
        q += " GROUP BY wr.id ORDER BY wr.receipt_date DESC, wr.id DESC"
        
        with self.db.connect() as conn:
            try:
                rows = conn.execute(q, params).fetchall()
            except Exception as e:
                QMessageBox.critical(self, 'خطا', str(e))
                rows = []
        
        self.tbl.setRowCount(len(rows))
        self._ids = []
        self._refs = []
        self._loads = []
        self._sups = []
        
        for i, r in enumerate(rows):
            self._ids.append(r['id'])
            self._refs.append(r['ref'] or '')
            self._loads.append(r['inbound_load_id'])
            self._sups.append(r['cust'] or '-')
            
            vals = [
                r['receipt_no'] or '', r['ref'] or '', str(r['stage_no'] or 1), 
                jalali_date_display_from_iso(r['receipt_date']), r['cust'], 
                r['drv'] or '-', r['waybill_no'] or '', 
                f"{int(r['q'] or 0):,}", f"{int(r['tlq'] or 0):,}", 
                f"{int(r['amt'] or 0):,}", STATUS_FA.get(r['receipt_status'], r['receipt_status'] or '')
            ]
            for cc, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl.setItem(i, cc, it)
        
        if self.tbl.rowCount():
            self._on_select(0, 0, -1, -1)

    def _on_select(self, row, col, pr, pc):
        if row < 0 or row >= len(self._ids):
            self.itbl.setRowCount(0)
            return
            
        with self.db.connect() as conn:
            items = conn.execute(
                "SELECT p.code, p.name, ri.qty, ri.unit_price FROM warehouse_receipt_items ri "
                "JOIN pallets p ON p.id=ri.pallet_id WHERE ri.receipt_id=? ORDER BY ri.id", 
                (self._ids[row],)
            ).fetchall()
            
        self.itbl.setRowCount(len(items))
        for i, r in enumerate(items):
            vals = [
                r['code'], r['name'], 
                f"{int(r['qty'] or 0):,}", 
                f"{int(r['unit_price'] or 0):,}", 
                f"{int((r['qty'] or 0)*(r['unit_price'] or 0)):,}"
            ]
            for cc, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.itbl.setItem(i, cc, it)
                
        self.browser.setHtml(self._preview_html(row))

    def _preview_html(self, row):
        from app.core.letterhead import render_letterhead_html, get_company_profile
        with self.db.connect() as conn:
            stages = conn.execute(
                "SELECT id, receipt_no, stage_no, receipt_date, stage_load_qty, delivered_qty "
                "FROM warehouse_receipts WHERE inbound_load_id=? ORDER BY stage_no", 
                (self._loads[row],)
            ).fetchall()
            
            parts = []
            tq = 0
            ta = 0
            for s in stages:
                its = conn.execute(
                    "SELECT p.code, p.name, ri.qty, ri.unit_price FROM warehouse_receipt_items ri "
                    "JOIN pallets p ON p.id=ri.pallet_id WHERE ri.receipt_id=? ORDER BY ri.id", 
                    (s['id'],)
                ).fetchall()
                
                trs = ''.join(
                    f"<tr><td>{r['code']}</td><td>{r['name']}</td><td>{int(r['qty'] or 0):,}</td>"
                    f"<td>{int(r['unit_price'] or 0):,}</td><td>{int((r['qty'] or 0)*(r['unit_price'] or 0)):,}</td></tr>" 
                    for r in its
                )
                tq += sum(int(r['qty'] or 0) for r in its)
                ta += sum(int((r['qty'] or 0)*(r['unit_price'] or 0)) for r in its)
                
                rem = (int(s['stage_load_qty'] or 0)) - (int(s['delivered_qty'] or 0))
                parts.append(
                    f"<h3>رسید {s['receipt_no']} — مرحله {s['stage_no']} — {jalali_date_display_from_iso(s['receipt_date'])}</h3>"
                    f"<p>تعداد این مرحله: {int(s['stage_load_qty'] or 0):,} — دریافت‌شده: {int(s['delivered_qty'] or 0):,} — "
                    f"<b>باقیمانده: {rem:,}</b></p>"
                    f"<table border=1 cellspacing=0 cellpadding=6 style='border-collapse: collapse; width:100%; text-align:right'>"
                    f"<tr style='background:#f1f1f1'><th>کد پالت</th><th>نام پالت</th><th>تعداد</th><th>قیمت واحد</th><th>مبلغ کل</th></tr>{trs}</table>"
                )
                
        lh = render_letterhead_html(get_company_profile(self.db))
        summ = f"<p style='color:#d00000;font-weight:bold;font-size:16px;border-top:2px solid #d00000;padding-top:8px'>جمع کل: تعداد پالت {tq:,} — مبلغ کل {ta:,} ریال</p>"
        return f"<html dir=rtl><body style='background:#ffffff;color:#111;padding:20px; font-family: Tahoma, sans-serif'>{lh}<h2>گزارش ورود کالا — مرجع {self._refs[row] or '-'} — تأمین‌کننده: {self._sups[row]}</h2>{''.join(parts)}{summ}</body></html>"

    def _open_web(self):
        row = self.tbl.currentRow()
        if row < 0: 
            QMessageBox.warning(self, 'پیش‌نمایش', 'یک رسید انتخاب کنید.')
            return
        
        html = self._preview_html(row)
        
        # استفاده از دیالوگ داخلی به جای باز کردن در مرورگر
        from app.ui.html_preview_dialog import HtmlPreviewDialog
        dialog = HtmlPreviewDialog(html, 'پیش‌نمایش رسید ورود کالا', self)
        dialog.exec_()

    def _export(self):
        from datetime import datetime
        default = 'ورود_کالا_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.xml'
        path, _ = QFileDialog.getSaveFileName(self, 'خروجی اکسل', default, 'Excel XML (*.xml)')
        if not path: return
        if not path.lower().endswith('.xml'): path += '.xml'
        
        def esc(v): return str(v).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        
        hdr = ['شماره رسید','شماره مرجع','مرحله','تاریخ','تأمین‌کننده','راننده','بارنامه','تعداد مرحله','تعداد کل بار','مبلغ کل','وضعیت']
        xml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?mso-application progid="Excel.Sheet"?>',
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
            '<Worksheet ss:Name="ورود کالا"><Table>'
        ]
        xml.append('<Row>'+''.join(f'<Cell><Data ss:Type="String">{esc(h)}</Data></Cell>' for h in hdr)+'</Row>')
        
        for i in range(self.tbl.rowCount()):
            xml.append('<Row>'+''.join(f'<Cell><Data ss:Type="String">{esc(self.tbl.item(i,c).text() if self.tbl.item(i,c) else "")}</Data></Cell>' for c in range(len(hdr)))+'</Row>')
            
        xml.append('</Table></Worksheet></Workbook>')
        
        try:
            with open(path, 'w', encoding='utf-8') as f: 
                f.write(''.join(xml))
        except PermissionError:
            alt = path.replace('.xml', '_new.xml')
            try:
                with open(alt, 'w', encoding='utf-8') as f: 
                    f.write(''.join(xml))
                QMessageBox.warning(self, 'اکسل', f'فایل اصلی باز/قفل بود؛ ذخیره شد در:\n{alt}')
                return
            except Exception as e2:
                QMessageBox.critical(self, 'خطا', f'امکان نوشتن نیست. فایل را ببندید یا مسیر دیگری انتخاب کنید.\n{e2}')
                return
                
        QMessageBox.information(self, 'اکسل', f'فایل با موفقیت ذخیره شد:\n{path}')