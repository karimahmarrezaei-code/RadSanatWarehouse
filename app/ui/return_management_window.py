import sqlite3
import tempfile
import webbrowser
from typing import Any, Dict, List, Optional
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QGroupBox,
    QMessageBox, QAbstractItemView, QTextEdit, QFrame,
    QComboBox, QRadioButton, QButtonGroup
)
from app.repositories.return_repository import ReturnRepository
from app.core.jalali import jalali_date_display_from_iso


class ReturnManagementWindow(QDialog):
    """فرم هوشمند برگشت از خرید و فروش با انتخاب سند از کمبوباکس"""
    data_changed = pyqtSignal()

    def __init__(self, db, user_data) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.current_doc_id = None
        self.current_doc_type = None
        self.current_warehouse_id = None

        self.setWindowTitle('مدیریت هوشمند برگشت از خرید و فروش')
        self.resize(1100, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()
        self._load_available_documents()  # ✅ بارگذاری اسناد در شروع

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # =========================================================
        # بخش انتخاب نوع سند و شماره سند (با کمبوباکس)
        # =========================================================
        search_group = QGroupBox("انتخاب سند مرجع")
        search_layout = QVBoxLayout(search_group)
        search_layout.setSpacing(10)

        # ردیف ۱: انتخاب نوع سند با Radio Button
        type_layout = QHBoxLayout()
        type_layout.setSpacing(20)
        type_layout.addWidget(QLabel("نوع سند:"))

        self.radio_receipt = QRadioButton("رسید خرید (برگشت از خرید)")
        self.radio_issue = QRadioButton("حواله فروش (برگشت از فروش)")
        self.radio_receipt.setChecked(True)  # پیش‌فرض

        self.radio_button_group = QButtonGroup(self)
        self.radio_button_group.addButton(self.radio_receipt)
        self.radio_button_group.addButton(self.radio_issue)

        # با تغییر نوع سند، کمبوباکس شماره سند رفرش شود
        self.radio_receipt.toggled.connect(self._on_doc_type_changed)
        self.radio_issue.toggled.connect(self._on_doc_type_changed)

        type_layout.addWidget(self.radio_receipt)
        type_layout.addWidget(self.radio_issue)
        type_layout.addStretch()
        search_layout.addLayout(type_layout)

        wh_layout = QHBoxLayout()
        wh_layout.addWidget(QLabel("فیلتر انبار:"))
        self.warehouse_filter_combo = QComboBox()
        self.warehouse_filter_combo.addItem("همه انبارها", None)
        try:
            with self.db.connect() as conn:
                for w in conn.execute("SELECT id, code, name FROM warehouses WHERE is_active=1 ORDER BY code"):
                    self.warehouse_filter_combo.addItem(f"{w['code']} | {w['name']}", w['id'])
        except Exception:
            pass
        self.warehouse_filter_combo.currentIndexChanged.connect(self._load_available_documents)
        wh_layout.addWidget(self.warehouse_filter_combo, 1)
        wh_layout.addStretch()
        search_layout.addLayout(wh_layout)

        # ردیف ۲: کمبوباکس انتخاب شماره سند + دکمه فراخوانی
        select_layout = QHBoxLayout()
        select_layout.setSpacing(10)
        select_layout.addWidget(QLabel("شماره سند:"))

        self.doc_combo = QComboBox()
        self.doc_combo.setMinimumWidth(400)
        self.doc_combo.setPlaceholderText("ابتدا نوع سند را انتخاب کنید...")
        select_layout.addWidget(self.doc_combo, stretch=1)

        # دکمه فراخوانی (اختیاری - می‌تواند با تغییر کمبوباکس هم لود شود)
        fetch_btn = QPushButton("فراخوانی اقلام")
        fetch_btn.setObjectName('PrimaryButton')
        fetch_btn.clicked.connect(self._fetch_selected_doc)
        select_layout.addWidget(fetch_btn)

        # دکمه رفرش لیست
        refresh_btn = QPushButton("🔄 رفرش لیست")
        refresh_btn.setObjectName('SecondaryButton')
        refresh_btn.clicked.connect(self._load_available_documents)
        select_layout.addWidget(refresh_btn)

        list_btn = QPushButton("📋 لیست اسناد برگشتی")
        list_btn.setObjectName('SecondaryButton')
        list_btn.clicked.connect(self._open_returns_list)
        select_layout.addWidget(list_btn)
        select_layout.addStretch()
        search_layout.addLayout(select_layout)

        layout.addWidget(search_group)

        # لیبل وضعیت
        self.info_lbl = QLabel("منتظر انتخاب سند...")
        self.info_lbl.setStyleSheet("font-weight: bold; color: #f59e0b;")
        layout.addWidget(self.info_lbl)

        # جدول اقلام
        self.items_table = QTableWidget(0, 6)
        self.items_table.setHorizontalHeaderLabels([
            "ID", "کد پالت", "نام پالت", "تعداد در سند", "قیمت واحد", "تعداد برگشتی"
        ])
        self.items_table.setColumnHidden(0, True)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.items_table)

        # توضیحات
        self.reason_txt = QTextEdit()
        self.reason_txt.setPlaceholderText("علت برگشت کالا را اینجا بنویسید...")
        self.reason_txt.setMaximumHeight(80)
        layout.addWidget(self.reason_txt)

        # دکمه ثبت
        self.btn_save = QPushButton("ثبت سند برگشتی")
        self.btn_save.setFixedHeight(60)
        self.btn_save.setObjectName("SuccessButton")
        self.btn_save.clicked.connect(self.save_return)
        self.btn_preview = QPushButton("پیش‌نمایش و چاپ")
        self.btn_preview.setFixedHeight(60)
        self.btn_preview.setObjectName("SecondaryButton")
        self.btn_preview.clicked.connect(self._preview_return)
        save_row = QHBoxLayout()
        save_row.addWidget(self.btn_preview)
        save_row.addWidget(self.btn_save)
        layout.addLayout(save_row)

    def _on_doc_type_changed(self):
        """وقتی نوع سند (رسید/حواله) تغییر کرد، کمبوباکس رفرش شود"""
        self.doc_combo.clear()
        self.doc_combo.setPlaceholderText("در حال بارگذاری...")
        self.current_doc_id = None
        self.current_doc_type = None
        self.items_table.setRowCount(0)
        self.info_lbl.setText("در حال بارگذاری اسناد...")
        self._load_available_documents()

    def _load_available_documents(self):
        """لیست اسناد با فیلتر انبار + تاریخ شمسی/میلادی + انبار + وضعیت"""
        self.doc_combo.clear()
        wid = self.warehouse_filter_combo.currentData() if hasattr(self, 'warehouse_filter_combo') else None
        with self.db.connect() as conn:
            if self.radio_receipt.isChecked():
                q = """SELECT wr.id, wr.receipt_no, wr.receipt_date, COALESCE(wr.receipt_status,'CONFIRMED') AS st,
                    (SELECT first_name||' '||last_name FROM persons WHERE id=wr.supplier_id) AS nm,
                    (SELECT GROUP_CONCAT(DISTINCT w.name) FROM warehouse_receipt_items wri JOIN warehouses w ON w.id=wri.warehouse_id WHERE wri.receipt_id=wr.id) AS wn,
                    (SELECT MIN(wri.warehouse_id) FROM warehouse_receipt_items wri WHERE wri.receipt_id=wr.id) AS wid
                    FROM warehouse_receipts wr"""
                params = []
                if wid:
                    q += " WHERE (SELECT MIN(wri.warehouse_id) FROM warehouse_receipt_items wri WHERE wri.receipt_id=wr.id)=?"
                    params.append(wid)
                q += " ORDER BY wr.id DESC"
                rows = conn.execute(q, params).fetchall()
                if not rows:
                    self.doc_combo.addItem("⚠️ هیچ رسید خریدی ثبت نشده است"); return
                for r in rows:
                    g = r['receipt_date'] or '-'
                    j = jalali_date_display_from_iso(g) if g and g != '-' else '-'
                    st = ' | ❌ ابطال شده' if r['st'] == 'CANCELLED' else ''
                    self.doc_combo.addItem(f"{r['receipt_no']} | {r['nm'] or 'نامشخص'} | {j} / {g} | انبار: {r['wn'] or '-'}{st}", r['id'])
            else:
                q = """SELECT wi.id, wi.issue_no, wi.issue_date, COALESCE(wi.issue_status,'CONFIRMED') AS st,
                    (SELECT first_name||' '||last_name FROM persons WHERE id=wi.customer_id) AS nm,
                    (SELECT GROUP_CONCAT(DISTINCT w.name) FROM warehouse_issue_items wii JOIN warehouses w ON w.id=wii.warehouse_id WHERE wii.issue_id=wi.id) AS wn,
                    (SELECT MIN(wii.warehouse_id) FROM warehouse_issue_items wii WHERE wii.issue_id=wi.id) AS wid
                    FROM warehouse_issues wi"""
                params = []
                if wid:
                    q += " WHERE (SELECT MIN(wii.warehouse_id) FROM warehouse_issue_items wii WHERE wii.issue_id=wi.id)=?"
                    params.append(wid)
                q += " ORDER BY wi.id DESC"
                rows = conn.execute(q, params).fetchall()
                if not rows:
                    self.doc_combo.addItem("⚠️ هیچ حواله فروشی ثبت نشده است"); return
                for r in rows:
                    g = r['issue_date'] or '-'
                    j = jalali_date_display_from_iso(g) if g and g != '-' else '-'
                    st = ' | ❌ ابطال شده' if r['st'] == 'CANCELLED' else ''
                    self.doc_combo.addItem(f"{r['issue_no']} | {r['nm'] or 'نامشخص'} | {j} / {g} | انبار: {r['wn'] or '-'}{st}", r['id'])

    def _fetch_selected_doc(self):
        """فراخوانی اقلام سند انتخاب‌شده از کمبوباکس"""
        doc_id = self.doc_combo.currentData()

        if doc_id is None:
            QMessageBox.warning(self, "خطا", "لطفاً یک سند معتبر انتخاب کنید.")
            return

        # بررسی اینکه آیتم واقعی انتخاب شده (نه پیام هشدار)
        if isinstance(doc_id, str) or doc_id == 0:
            QMessageBox.warning(self, "خطا", "این گزینه قابل انتخاب نیست.")
            return

        if self.radio_receipt.isChecked():
            self.current_doc_type = 'RECEIPT'
            doc_label = "رسید خرید"
        else:
            self.current_doc_type = 'ISSUE'
            doc_label = "حواله فروش"

        with self.db.connect() as conn:
            if self.radio_receipt.isChecked():
                st = conn.execute("SELECT COALESCE(receipt_status,'CONFIRMED') FROM warehouse_receipts WHERE id=?", (doc_id,)).fetchone()[0]
            else:
                st = conn.execute("SELECT COALESCE(issue_status,'CONFIRMED') FROM warehouse_issues WHERE id=?", (doc_id,)).fetchone()[0]
        if st == 'CANCELLED':
            QMessageBox.warning(self, 'سند ابطال شده', 'این سند قبلاً ابطال گردیده است و قابل برگشت نیست.')
            return
        self.current_doc_id = doc_id

        # ✅ خواندن warehouse_id از جدول pallets
        self.current_warehouse_id = self._resolve_warehouse(self.current_doc_id, self.current_doc_type)

        # نمایش اطلاعات
        doc_display = self.doc_combo.currentText()
        self.info_lbl.setText(f"✅ سند انتخاب شد: {doc_label} ({doc_display})")

        # لود کردن اقلام
        self._load_items(self.current_doc_id, self.current_doc_type)

    def _resolve_warehouse(self, doc_id, doc_type):
        """warehouse_id را از جدول pallets (از طریق آیتم‌های سند) پیدا می‌کند"""
        if doc_type == 'RECEIPT':
            table = "warehouse_receipt_items"
            col = "receipt_id"
        else:
            table = "warehouse_issue_items"
            col = "issue_id"

        try:
            with self.db.connect() as conn:
                row = conn.execute(f'''
                    SELECT p.warehouse_id
                    FROM {table} itm
                    JOIN pallets p ON p.id = itm.pallet_id
                    WHERE itm.{col} = ?
                    LIMIT 1
                ''', (doc_id,)).fetchone()

                if row and row['warehouse_id']:
                    return row['warehouse_id']

                # اگر warehouse_id در pallets نبود، اولین انبار
                fallback = conn.execute('SELECT id FROM warehouses LIMIT 1').fetchone()
                return fallback['id'] if fallback else 1
        except Exception:
            return 1

    def _load_items(self, d_id, d_type):
        table = "warehouse_receipt_items" if d_type == 'RECEIPT' else "warehouse_issue_items"
        col = "receipt_id" if d_type == 'RECEIPT' else "issue_id"

        with self.db.connect() as conn:
            rows = conn.execute(f'''
                SELECT itm.pallet_id, p.code, p.name, itm.qty, itm.unit_price
                FROM {table} itm
                JOIN pallets p ON p.id = itm.pallet_id
                WHERE itm.{col} = ?
            ''', (d_id,)).fetchall()

            if not rows:
                self.items_table.setRowCount(0)
                QMessageBox.warning(self, "خطا", "این سند فاقد اقلام است.")
                return

            self.items_table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                self.items_table.setItem(i, 0, QTableWidgetItem(str(r['pallet_id'])))
                self.items_table.setItem(i, 1, QTableWidgetItem(r['code']))
                self.items_table.setItem(i, 2, QTableWidgetItem(r['name']))
                self.items_table.setItem(i, 3, QTableWidgetItem(str(r['qty'])))
                # ✅ مدیریت NULL در unit_price
                price = r['unit_price'] if r['unit_price'] is not None else 0
                self.items_table.setItem(i, 4, QTableWidgetItem(f"{price:,}"))

                edit_qty = QLineEdit("0")
                edit_qty.setAlignment(Qt.AlignCenter)
                self.items_table.setCellWidget(i, 5, edit_qty)


    def _preview_return(self):
        """پیش‌نمایش/چاپ: آمار سند اصلی + اقلام برگشتی + مبلغ پرداختنی/دریافتنی"""
        if not self.current_doc_id:
            QMessageBox.warning(self, 'خطا', 'ابتدا سند مرجع را فراخوانی کنید.')
            return
        from app.core.letterhead import get_filtered_company
        company = get_filtered_company(self.db)

        # ۱) آمار سند اصلی (تعداد کل پالت + مبلغ ثبت‌شده)
        with self.db.connect() as conn:
            if self.current_doc_type == 'RECEIPT':
                t, c = 'warehouse_receipt_items', 'receipt_id'
            else:
                t, c = 'warehouse_issue_items', 'issue_id'
            o = conn.execute(f"SELECT COALESCE(SUM(qty),0), COALESCE(SUM(total_price),0) FROM {t} WHERE {c}=?",
                             (self.current_doc_id,)).fetchone()
            orig_qty = int(o[0] or 0); orig_amount = int(o[1] or 0)
            d = conn.execute(f"SELECT {'receipt_date' if self.current_doc_type=='RECEIPT' else 'issue_date'} FROM {'warehouse_receipts' if self.current_doc_type=='RECEIPT' else 'warehouse_issues'} WHERE id=?", (self.current_doc_id,)).fetchone()
            src_date = d[0] if d and d[0] else None

        # ۲) اقلام برگشتی
        rows_html = ''; total = 0
        for i in range(self.items_table.rowCount()):
            qw = self.items_table.cellWidget(i, 5)
            rq = int(''.join(ch for ch in (qw.text() if qw else '0') if ch.isdigit()) or 0)
            if rq <= 0:
                continue
            code = self.items_table.item(i, 1).text(); name = self.items_table.item(i, 2).text()
            price = int(self.items_table.item(i, 4).text().replace(',', '') or 0)
            total += rq * price
            rows_html += f"<tr><td>{i+1}</td><td>{code}</td><td>{name}</td><td>{rq:,}</td><td>{price:,}</td><td>{rq*price:,}</td></tr>"

        is_purchase = self.current_doc_type == 'RECEIPT'
        doc_label = 'برگشت از خرید' if is_purchase else 'برگشت از فروش'
        money_label = 'مبلغ دریافتنی از تأمین‌کننده' if is_purchase else 'مبلغ پرداختنی به مشتری'

        html = f"""<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8"><style>
            body{{font-family:Tahoma;padding:20px;max-width:900px;margin:0 auto;}}
            .company-info h1{{margin:0;font-size:30px;font-weight:bold;color:#46505f;}}
            .company-info p{{margin:4px 0;font-size:14px;color:#6b7686;}}
            .box{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px;margin:12px 0;}}
            .box h3{{margin:0 0 8px 0;color:#39424f;}}
            table{{width:100%;border-collapse:collapse;margin-top:8px;}}
            th{{background:#f59e0b;color:#46505f;padding:8px;border:1px solid #5b6675;font-size:13px;}}
            td{{padding:8px;border:1px solid #e2e8f0;text-align:center;font-size:12px;}}
            .money{{background:#dcfce7;border:1px solid #16a34a;border-radius:6px;padding:12px;margin-top:15px;font-size:16px;font-weight:bold;color:#14532d;}}
            .print-btn{{position:fixed;top:20px;left:20px;padding:10px 20px;background:#9333ea;color:#fff;border:none;border-radius:6px;cursor:pointer;}}
            </style></head><body>
            <button class="print-btn" onclick="window.print()">چاپ / ذخیره PDF</button>
            <div class="company-info"><h1>{company.get('company_name','')}</h1>
            <p>مدیر عامل: {company.get('ceo_name','')} | شناسه ملی: {company.get('national_id','')}</p>
            <p>تلفن: {company.get('phone','')} | آدرس: {company.get('address','')}</p></div>
            <h2>سند {doc_label}</h2>
            <p><b>سند مرجع:</b> {self.doc_combo.currentText()}</p>
            <p><b>تاریخ سند مرجع:</b> {(jalali_date_display_from_iso(src_date) + ' / ' + src_date) if src_date else '-'}</p>
            <p><b>علت برگشت:</b> {self.reason_txt.toPlainText() or '-'}</p>

            <div class="box"><h3>۱) سند اصلی</h3>
            <table><tr><th>تعداد کل پالت</th><th>مبلغ ثبت‌شده (ریال)</th></tr>
            <tr><td>{orig_qty:,}</td><td>{orig_amount:,}</td></tr></table></div>

            <div class="box"><h3>۲) اقلام برگشتی</h3>
            <table><tr><th>ردیف</th><th>کد</th><th>نام</th><th>تعداد برگشتی</th><th>قیمت</th><th>جمع</th></tr>{rows_html}</table>
            <p style="text-align:left;font-weight:bold;">جمع برگشتی: {total:,} ریال</p></div>

            <div class="money">{money_label}: {total:,} ریال</div>
            </body></html>"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html); t = f.name
        webbrowser.open('file:///' + t)


    def _open_returns_list(self):
        """لیست اسناد برگشتی ثبت‌شده + پیش‌نمایش/چاپ"""
        from app.repositories.return_repository import ReturnRepository
        repo = ReturnRepository(self.db)
        rows = repo.list_returns()
        dlg = QDialog(self); dlg.setWindowTitle('اسناد برگشتی ثبت‌شده')
        dlg.resize(1000, 550); dlg.setLayoutDirection(Qt.RightToLeft)
        lay = QVBoxLayout(dlg)
        tbl = QTableWidget(0, 7)
        tbl.setHorizontalHeaderLabels(['شناسه', 'شماره', 'تاریخ (شمسی/میلادی)', 'نوع', 'طرف حساب', 'مبلغ (ریال)', 'علت'])
        tbl.setColumnHidden(0, True)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [str(r['id']), r['finance_no'], f"{r['finance_date_jalali']} / {r['finance_date']}",
                    r['type_label'], r['person_name'], f"{r['total_amount']:,}", r['reason']]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tbl.setItem(i, c, it)
        tbl.resizeColumnsToContents()
        lay.addWidget(tbl)
        btn_row = QHBoxLayout()
        prev = QPushButton('پیش‌نمایش / چاپ'); prev.setObjectName('PrimaryButton')
        prev.clicked.connect(lambda: self._preview_saved_return(tbl))
        close = QPushButton('بستن'); close.setObjectName('SecondaryButton'); close.clicked.connect(dlg.accept)
        btn_row.addWidget(prev); btn_row.addStretch(); btn_row.addWidget(close)
        lay.addLayout(btn_row)
        dlg.exec_()

    def _preview_saved_return(self, tbl):
        """پیش‌نمایش/چاپ یک سند برگشتی ذخیره‌شده"""
        row = tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, 'توجه', 'ابتدا یک سند برگشتی انتخاب کنید.'); return
        fd_id = int(tbl.item(row, 0).text())
        from app.repositories.return_repository import ReturnRepository
        from app.core.letterhead import get_filtered_company
        repo = ReturnRepository(self.db); company = get_filtered_company(self.db)
        items = repo.get_return_items(fd_id)
        with self.db.connect() as conn:
            meta = conn.execute("SELECT smart_no, return_type, source_doc_id, source_doc_no, reason, return_date "
                                "FROM return_items WHERE financial_document_id=? LIMIT 1", (fd_id,)).fetchone()
            fd = conn.execute("SELECT counterparty_person_id FROM financial_documents WHERE id=?", (fd_id,)).fetchone()
            person = '-'
            if fd and fd['counterparty_person_id']:
                pr = conn.execute("SELECT first_name||' '||last_name FROM persons WHERE id=?", (fd['counterparty_person_id'],)).fetchone()
                person = pr[0] if pr else '-'
        if not meta:
            QMessageBox.warning(self, 'خطا', 'ریز اقلام این سند یافت نشد.'); return
        is_purchase = meta['return_type'] == 'RECEIPT'
        with self.db.connect() as conn:
            t, c = ('warehouse_receipt_items', 'receipt_id') if is_purchase else ('warehouse_issue_items', 'issue_id')
            o = conn.execute(f"SELECT COALESCE(SUM(qty),0), COALESCE(SUM(total_price),0) FROM {t} WHERE {c}=?",
                             (meta['source_doc_id'],)).fetchone()
            orig_qty = int(o[0] or 0); orig_amount = int(o[1] or 0)
            d = conn.execute(f"SELECT {'receipt_date' if is_purchase else 'issue_date'} FROM {'warehouse_receipts' if is_purchase else 'warehouse_issues'} WHERE id=?", (meta['source_doc_id'],)).fetchone()
            src_date = d[0] if d and d[0] else None
        rows_html = ''; total = 0
        for it in items:
            total += it['total_price']
            rows_html += f"<tr><td>{it['row_no']}</td><td>{it['pallet_code']}</td><td>{it['pallet_name']}</td><td>{it['qty']:,}</td><td>{it['unit_price']:,}</td><td>{it['total_price']:,}</td></tr>"
        doc_label = 'برگشت از خرید' if is_purchase else 'برگشت از فروش'
        money_label = 'مبلغ دریافتنی از تأمین‌کننده' if is_purchase else 'مبلغ پرداختنی به مشتری'
        html = f"""<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8"><style>
            body{{font-family:Tahoma;padding:20px;max-width:900px;margin:0 auto;}}
            .company-info h1{{margin:0;font-size:30px;font-weight:bold;color:#46505f;}}
            .company-info p{{margin:4px 0;font-size:14px;color:#6b7686;}}
            .box{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px;margin:12px 0;}}
            .box h3{{margin:0 0 8px 0;}}
            table{{width:100%;border-collapse:collapse;margin-top:8px;}}
            th{{background:#f59e0b;color:#46505f;padding:8px;border:1px solid #5b6675;font-size:13px;}}
            td{{padding:8px;border:1px solid #e2e8f0;text-align:center;font-size:12px;}}
            .money{{background:#dcfce7;border:1px solid #16a34a;border-radius:6px;padding:12px;margin-top:15px;font-size:16px;font-weight:bold;color:#14532d;}}
            .print-btn{{position:fixed;top:20px;left:20px;padding:10px 20px;background:#9333ea;color:#fff;border:none;border-radius:6px;cursor:pointer;}}
            </style></head><body>
            <button class="print-btn" onclick="window.print()">چاپ / ذخیره PDF</button>
            <div class="company-info"><h1>{company.get('company_name','')}</h1>
            <p>مدیر عامل: {company.get('ceo_name','')} | شناسه ملی: {company.get('national_id','')}</p>
            <p>تلفن: {company.get('phone','')} | آدرس: {company.get('address','')}</p></div>
            <h2>سند {doc_label} — {meta['smart_no']}</h2>
            <p><b>سند مرجع:</b> {meta['source_doc_no'] or '-'} | <b>طرف حساب:</b> {person}</p>
            <p><b>تاریخ سند مرجع:</b> {(jalali_date_display_from_iso(src_date) + ' / ' + src_date) if src_date else '-'} | <b>تاریخ برگشت:</b> {jalali_date_display_from_iso(meta['return_date'])}</p>
            <p><b>علت:</b> {meta['reason'] or '-'}</p>
            <div class="box"><h3>۱) سند اصلی</h3>
            <table><tr><th>تعداد کل پالت</th><th>مبلغ ثبت‌شده (ریال)</th></tr><tr><td>{orig_qty:,}</td><td>{orig_amount:,}</td></tr></table></div>
            <div class="box"><h3>۲) اقلام برگشتی</h3>
            <table><tr><th>ردیف</th><th>کد</th><th>نام</th><th>تعداد</th><th>قیمت</th><th>جمع</th></tr>{rows_html}</table>
            <p style="text-align:left;font-weight:bold;">جمع برگشتی: {total:,} ریال</p></div>
            <div class="money">{money_label}: {total:,} ریال</div>
            </body></html>"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html); t = f.name
        webbrowser.open('file:///' + t)

    def save_return(self):
        if not self.current_doc_id:
            QMessageBox.warning(self, "خطا", "ابتدا یک سند مرجع انتخاب کنید.")
            return

        if not self.current_warehouse_id:
            QMessageBox.warning(self, "خطا", "انبار مبدأ مشخص نیست. با مدیر سیستم تماس بگیرید.")
            return

        items_to_return = []
        errors = []

        for i in range(self.items_table.rowCount()):
            ret_qty_str = self.items_table.cellWidget(i, 5).text().strip()

            if not ret_qty_str.isdigit():
                continue

            ret_qty = int(ret_qty_str)
            if ret_qty <= 0:
                continue

            pallet_id = int(self.items_table.item(i, 0).text())
            pallet_name = self.items_table.item(i, 2).text()
            max_qty = int(self.items_table.item(i, 3).text())

            # ✅ اعتبارسنجی: تعداد برگشتی نباید بیشتر از تعداد اصلی باشد
            if ret_qty > max_qty:
                errors.append(f"«{pallet_name}»: تعداد برگشتی ({ret_qty}) بیشتر از تعداد سند ({max_qty}) است.")
                continue

            items_to_return.append({
                'pallet_id': pallet_id,
                'qty': ret_qty,
                'warehouse_id': self.current_warehouse_id
            })

        if errors:
            QMessageBox.warning(self, "خطای اعتبارسنجی", "\n".join(errors))
            return

        if not items_to_return:
            QMessageBox.warning(self, "خطا", "تعداد برگشتی اقلام را وارد کنید.")
            return

        try:
            repo = ReturnRepository(self.db)
            ctx = repo.register_return(
                self.current_doc_id, self.current_doc_type,
                items_to_return, self.user_data['id'], self.reason_txt.toPlainText()
            )

            self.data_changed.emit()

            QMessageBox.information(self, "موفقیت", f"سند برگشتی {ctx['smart_no']} با موفقیت ثبت شد.")
            try:
                from app.ui.return_print_preview import show_return_preview
                show_return_preview(self, repo, ctx)
            except Exception as _ex:
                import traceback
                traceback.print_exc()
                print('[preview] خطا:', _ex)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))
