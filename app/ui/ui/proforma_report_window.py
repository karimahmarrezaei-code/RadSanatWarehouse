# -- coding: utf-8 --
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
'DRAFT': 'پیش‌نویس', 'FINALIZED': 'نهایی',
'CONVERTED': 'تبدیل شده', 'CANCELLED': 'ابطال شده'
}

class ProformaReportWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('گزارش پیش‌فاکتورها')
        self.resize(1180, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        self._ids = []
        self._custs = []
        self._build()
        self._load_persons()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setObjectName('ToolbarFrame')
        toolbar_frame.setStyleSheet("""
            QFrame#ToolbarFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        bar = QHBoxLayout(toolbar_frame)
        bar.setContentsMargins(10, 10, 10, 10)

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

        bar.addWidget(QLabel('مشتری:'))
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

        self.tabs = QTabWidget()
        w1 = QWidget()
        l1 = QVBoxLayout(w1)
        l1.setSpacing(10)
        self.tbl = QTableWidget(0, 9)
        self.tbl.setHorizontalHeaderLabels([
            'شماره پیش‌فاکتور', 'تاریخ', 'مشتری', 'تعداد اقلام', 
            'جمع کل', 'ارزش افزوده', 'جمع با ارزش افزوده', 'اعتبار (روز)', 'وضعیت'
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

        l1.addWidget(QLabel('📦 اقلام پیش‌فاکتور انتخاب‌شده:'))
        self.itbl = QTableWidget(0, 7)
        self.itbl.setHorizontalHeaderLabels(['ردیف', 'کد پالت', 'نام پالت', 'تعداد', 'قیمت واحد', 'مبلغ کل', 'توضیحات'])
        self.itbl.verticalHeader().setVisible(False)
        self.itbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.itbl.setAlternatingRowColors(True)
        self.itbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.itbl.horizontalHeader().setStretchLastSection(True)
        self.itbl.verticalHeader().setDefaultSectionSize(30)
        l1.addWidget(self.itbl)
        self.tabs.addTab(w1, '📋 گزارش')

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.tabs.addTab(self.browser, '🌐 پیش‌نمایش وب')
        root.addWidget(self.tabs)

        from datetime import date
        first_day_of_month = date.fromisoformat(today_iso_date()).replace(day=1)
        self.from_edit.setDate(QDate.fromString(first_day_of_month.isoformat(), 'yyyy-MM-dd'))
        self.to_edit.setDate(QDate.fromString(today_iso_date(), 'yyyy-MM-dd'))
        self._update_from_jalali()
        self._update_to_jalali()

    def _load_persons(self):
        with self.db.connect() as conn:
            try:
                rows = conn.execute("SELECT DISTINCT p.id, (p.first_name||' '||p.last_name) n FROM persons p JOIN proforma_invoices pi ON pi.customer_id=p.id ORDER BY p.id").fetchall()
            except Exception:
                rows = conn.execute("SELECT id, (first_name||' '||last_name) n FROM persons ORDER BY id").fetchall()
        self.person_combo.clear()
        self.person_combo.addItem('همه مشتریان', None)
        for r in rows:
            self.person_combo.addItem((r['n'] or str(r['id'])), r['id'])

    def _update_from_jalali(self):
        iso_date = self.from_edit.date().toString('yyyy-MM-dd')
        self.from_jalali_lbl.setText(jalali_date_display_from_iso(iso_date))

    def _update_to_jalali(self):
        iso_date = self.to_edit.date().toString('yyyy-MM-dd')
        self.to_jalali_lbl.setText(jalali_date_display_from_iso(iso_date))

    def refresh(self):
        f = self.from_edit.date().toString('yyyy-MM-dd')
        t = self.to_edit.date().toString('yyyy-MM-dd')
        c = self.person_combo.currentData()
        q = ("SELECT pi.id, pi.proforma_no, pi.proforma_date, pi.total_amount, "
             "pi.vat_amount, pi.total_with_vat, pi.validity_days, pi.status, "
             "COALESCE(p.first_name||' '||p.last_name, '-') AS customer_name, "
             "(SELECT COUNT(*) FROM proforma_invoice_items pii WHERE pii.proforma_id=pi.id) AS items_count "
             "FROM proforma_invoices pi "
             "LEFT JOIN persons p ON p.id=pi.customer_id")
        conds, params = [], []
        if f: conds.append("pi.proforma_date >= ?"); params.append(f)
        if t: conds.append("pi.proforma_date <= ?"); params.append(t)
        if c is not None: conds.append("pi.customer_id = ?"); params.append(c)
        if conds: q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY pi.proforma_date DESC, pi.id DESC"
        with self.db.connect() as conn:
            try:
                rows = conn.execute(q, params).fetchall()
            except Exception as e:
                QMessageBox.critical(self, 'خطا', str(e))
                rows = []
        self.tbl.setRowCount(len(rows))
        self._ids = []
        self._custs = []
        for i, r in enumerate(rows):
            self._ids.append(r['id'])
            self._custs.append(r['customer_name'] or '-')
            vals = [
                r['proforma_no'] or '', jalali_date_display_from_iso(r['proforma_date']), 
                r['customer_name'], f"{int(r['items_count'] or 0):,}",
                f"{int(r['total_amount'] or 0):,}", f"{int(r['vat_amount'] or 0):,}", 
                f"{int(r['total_with_vat'] or 0):,}", str(r['validity_days'] or 30),
                STATUS_FA.get(r['status'], r['status'] or '')
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
                "SELECT pii.row_no, p.code, p.name, pii.quantity, pii.unit_price, pii.total_amount, pii.note "
                "FROM proforma_invoice_items pii "
                "LEFT JOIN pallets p ON p.id=pii.pallet_id "
                "WHERE pii.proforma_id=? ORDER BY pii.row_no", 
                (self._ids[row],)
            ).fetchall()
        self.itbl.setRowCount(len(items))
        for i, r in enumerate(items):
            vals = [
                str(r['row_no'] or i+1), r['code'] or '-', r['name'] or '-', 
                f"{int(r['quantity'] or 0):,}", f"{int(r['unit_price'] or 0):,}", 
                f"{int(r['total_amount'] or 0):,}", r['note'] or ''
            ]
            for cc, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.itbl.setItem(i, cc, it)
        self.browser.setHtml(self._preview_html(row))

    def _preview_html(self, row):
        from app.core.letterhead import render_letterhead_html, get_company_profile
        with self.db.connect() as conn:
            pi = conn.execute(
                "SELECT pi.proforma_no, pi.proforma_date, pi.total_amount, pi.vat_amount, pi.total_with_vat, pi.validity_days, pi.status, pi.description, "
                "COALESCE(p.first_name||' '||p.last_name, '-') AS customer_name "
                "FROM proforma_invoices pi LEFT JOIN persons p ON p.id=pi.customer_id WHERE pi.id=?", 
                (self._ids[row],)
            ).fetchone()
            items = conn.execute(
                "SELECT pii.row_no, p.code, p.name, pii.quantity, pii.unit_price, pii.total_amount, pii.note "
                "FROM proforma_invoice_items pii "
                "LEFT JOIN pallets p ON p.id=pii.pallet_id "
                "WHERE pii.proforma_id=? ORDER BY pii.row_no", 
                (self._ids[row],)
            ).fetchall()
        trs = ''.join(
            f"<tr><td>{r['row_no']}</td><td>{r['code'] or '-'}</td><td>{r['name'] or '-'}</td>"
            f"<td>{int(r['quantity'] or 0):,}</td><td>{int(r['unit_price'] or 0):,}</td>"
            f"<td>{int(r['total_amount'] or 0):,}</td><td>{r['note'] or ''}</td></tr>" 
            for r in items
        )
        lh = render_letterhead_html(get_company_profile(self.db))
        desc_html = f"<p><b>توضیحات:</b> {pi['description']}</p>" if pi['description'] else ""
        summ = (
            f"<p style='color:#d00000;font-weight:bold;font-size:16px;border-top:2px solid #d00000;padding-top:8px'>"
            f"جمع کل: {int(pi['total_amount'] or 0):,} ریال — ارزش افزوده: {int(pi['vat_amount'] or 0):,} ریال — "
            f"<b>جمع نهایی: {int(pi['total_with_vat'] or 0):,} ریال</b></p>"
        )
        return (
            f"<html dir=rtl><body style='background:#ffffff;color:#111;padding:20px; font-family: Tahoma, sans-serif'>"
            f"{lh}"
            f"<h2>پیش‌فاکتور شماره {pi['proforma_no']} — تاریخ: {jalali_date_display_from_iso(pi['proforma_date'])}</h2>"
            f"<p><b>مشتری:</b> {pi['customer_name']} | <b>وضعیت:</b> {STATUS_FA.get(pi['status'], pi['status'])} | <b>اعتبار:</b> {pi['validity_days']} روز</p>"
            f"{desc_html}"
            f"<table border=1 cellspacing=0 cellpadding=6 style='border-collapse: collapse; width:100%; text-align:right'>"
            f"<tr style='background:#f1f1f1'><th>ردیف</th><th>کد پالت</th><th>نام پالت</th><th>تعداد</th><th>قیمت واحد</th><th>مبلغ کل</th><th>توضیحات</th></tr>{trs}</table>"
            f"{summ}</body></html>"
        )

    def _open_web(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'پیش‌نمایش', 'یک پیش‌فاکتور انتخاب کنید.')
            return
        html = self._preview_html(row)
        try:
            from app.ui.html_preview_dialog import HtmlPreviewDialog
            dialog = HtmlPreviewDialog(html, 'پیش‌نمایش پیش‌فاکتور', self)
            dialog.exec_()
        except Exception as e:
            import tempfile
            fd, path = tempfile.mkstemp(suffix='.html')
            os.write(fd, html.encode('utf-8'))
            os.close(fd)
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            print(f"[WARN] HtmlPreviewDialog اجرا نشد، مرورگر باز شد. خطا: {e}")

    def _export(self):
        from datetime import datetime
        default = 'گزارش_پیش_فاکتور_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.xml'
        path, _ = QFileDialog.getSaveFileName(self, 'خروجی اکسل', default, 'Excel XML (*.xml)')
        if not path: return
        if not path.lower().endswith('.xml'): path += '.xml'
        def esc(v): return str(v).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        hdr = ['شماره پیش‌فاکتور','تاریخ','مشتری','تعداد اقلام','جمع کل','ارزش افزوده','جمع با ارزش افزوده','اعتبار (روز)','وضعیت']
        xml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?mso-application progid="Excel.Sheet"?>',
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
            '<Worksheet ss:Name="پیش‌فاکتورها"><Table>'
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