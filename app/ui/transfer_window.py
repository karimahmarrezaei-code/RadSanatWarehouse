# -*- coding: utf-8 -*-
"""فرم جابجایی پالت بین انبارها - سه‌تبّه (ثبت / لیست / موجودی انبار) + قیمت میانگین"""
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QPushButton, QGroupBox, QComboBox, QFormLayout, QTabWidget,
    QMessageBox, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QAbstractItemView, QSpinBox, QLineEdit,
)
from PyQt5.QtGui import QFont
from app.core.jalali import now_iso, jalali_date_display_from_iso, today_iso_date


class TransferWindow(QDialog):
    transfer_completed = pyqtSignal()

    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.user_id = self.user_data.get('id', 1)
        self.setWindowTitle('جابجایی پالت بین انبارها')
        self.resize(1150, 760)
        self.setLayoutDirection(Qt.RightToLeft)
        self._ensure_tables()
        self._build_ui()
        self._load_warehouses()
        for t in (self.source_table, self.transfer_table, self.transfers_table,
                  self.transfer_items_table, self.stock_table):
            self._stretch(t)

    # ------------------------------------------------------------------
    def _ensure_tables(self):
        with self.db.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS pallet_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transfer_no TEXT, transfer_date TEXT,
                from_warehouse_id INTEGER, to_warehouse_id INTEGER,
                description TEXT, created_by INTEGER, created_at TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS pallet_transfer_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transfer_id INTEGER, pallet_id INTEGER, qty INTEGER)""")
            for col, ddl in [('unit_price', 'INTEGER NOT NULL DEFAULT 0'),
                             ('total_price', 'INTEGER NOT NULL DEFAULT 0')]:
                try:
                    conn.execute(f"ALTER TABLE pallet_transfer_items ADD COLUMN {col} {ddl}")
                except Exception:
                    pass
            conn.commit()

    def _next_transfer_no(self, conn):
        year = jalali_date_display_from_iso(today_iso_date()).split('/')[0]
        row = conn.execute("SELECT transfer_no FROM pallet_transfers WHERE transfer_no LIKE ? "
                           "ORDER BY id DESC LIMIT 1", (f'TR-{year}-%',)).fetchone()
        if row and row['transfer_no']:
            try: n = int(row['transfer_no'].split('-')[-1]) + 1
            except Exception: n = 1
        else: n = 1
        return f'TR-{year}-{n:04d}'

    def _avg_price(self, conn, pallet_id, warehouse_id):
        try:
            with self.db.connect() as c2:
                c2.row_factory = None
                r = c2.execute("SELECT COALESCE(SUM(qty_in*unit_price),0)/COALESCE(SUM(qty_in),0) FROM inventory_transactions WHERE pallet_id=? AND warehouse_id=? AND qty_in>0 AND unit_price>0 AND reference_type<>'TRANSFER'", (pallet_id, warehouse_id)).fetchone()
                if r and r[0]:
                    return int(r[0])
                r2 = c2.execute("SELECT COALESCE(SUM(qty*unit_price),0)/COALESCE(SUM(qty),0) FROM opening_inventory_items WHERE pallet_id=? AND qty>0 AND unit_price>0", (pallet_id,)).fetchone()
                if r2 and r2[0]:
                    return int(r2[0])
                return 0
        except Exception:
            return 0

    def _digits(self, s): return int(''.join(ch for ch in s if ch.isdigit()) or 0)

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(18, 18, 18, 18)
        header = QFrame(); header.setObjectName('Card')
        hl = QVBoxLayout(header)
        t = QLabel('جابجایی پالت بین انبارها'); t.setObjectName('Title')
        s = QLabel('ثبت، لیست و مشاهده موجودی انبارها'); s.setObjectName('Muted')
        hl.addWidget(t); hl.addWidget(s); root.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_transfer_tab(), '➕ ثبت جابجایی')
        self.tabs.addTab(self._build_list_tab(), '📋 لیست جابجایی‌ها')
        self.tabs.addTab(self._build_stock_tab(), '🏬 موجودی انبار')
        self.tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self.tabs)

        btn_row = QHBoxLayout()
        close_btn = QPushButton('بستن'); close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(self.accept)
        btn_row.addStretch(); btn_row.addWidget(close_btn); root.addLayout(btn_row)

    def _stretch(self, table):
        h = table.horizontalHeader()
        for i in range(table.columnCount()): h.setSectionResizeMode(i, QHeaderView.Stretch)
        table.verticalHeader().setDefaultSectionSize(36); table.setShowGrid(True)

    # ---------------- تب ۱ ----------------
    def _build_transfer_tab(self):
        tab = QWidget(); lay = QVBoxLayout(tab); lay.setSpacing(12)
        info = QGroupBox('اطلاعات جابجایی'); fl = QFormLayout(info)
        self.transfer_date = QDateEdit(QDate.currentDate()); self.transfer_date.setCalendarPopup(True)
        self.transfer_date.setDisplayFormat('yyyy-MM-dd')
        self.from_warehouse = QComboBox(); self.from_warehouse.addItem('-- انبار مبدأ --', None)
        self.to_warehouse = QComboBox(); self.to_warehouse.addItem('-- انبار مقصد --', None)
        self.from_warehouse.currentIndexChanged.connect(self._load_source_pallets)
        fl.addRow('تاریخ جابجایی:', self.transfer_date)
        fl.addRow('انبار مبدأ:', self.from_warehouse)
        fl.addRow('انبار مقصد:', self.to_warehouse)
        lay.addWidget(info)

        src = QGroupBox('پالت‌های انبار مبدأ (دابل‌کلیک = افزودن)'); sl = QVBoxLayout(src)
        self.source_table = QTableWidget(0, 5)
        self.source_table.setHorizontalHeaderLabels(['ردیف', 'کد پالت', 'نام پالت', 'موجودی', 'میانگین قیمت'])
        self.source_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.source_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.source_table.verticalHeader().setVisible(False)
        self.source_table.doubleClicked.connect(self._add_transfer_row)
        sl.addWidget(self.source_table); lay.addWidget(src, 2)

        tr = QGroupBox('لیست جابجایی'); tl = QVBoxLayout(tr)
        self.transfer_table = QTableWidget(0, 5)
        self.transfer_table.setHorizontalHeaderLabels(['کد پالت', 'نام پالت', 'تعداد', 'قیمت واحد (ریال)', 'جمع کل (ریال)'])
        self.transfer_table.verticalHeader().setVisible(False)
        tl.addWidget(self.transfer_table)
        ar = QHBoxLayout()
        add_btn = QPushButton('افزودن ردیف'); add_btn.setObjectName('SecondaryButton'); add_btn.clicked.connect(self._add_transfer_row)
        rem_btn = QPushButton('حذف ردیف'); rem_btn.setObjectName('SecondaryButton'); rem_btn.clicked.connect(self._remove_transfer_row)
        ar.addWidget(add_btn); ar.addWidget(rem_btn); ar.addStretch(); tl.addLayout(ar)
        lay.addWidget(tr, 2)

        br = QHBoxLayout()
        save_btn = QPushButton('✅ ثبت جابجایی'); save_btn.setObjectName('SuccessButton')
        save_btn.setMinimumHeight(45); save_btn.setFont(QFont('Tahoma', 11, QFont.Bold)); save_btn.clicked.connect(self._save_transfer)
        clear_btn = QPushButton('پاک کردن فرم'); clear_btn.setObjectName('SecondaryButton'); clear_btn.clicked.connect(self._clear_form)
        br.addWidget(save_btn); br.addWidget(clear_btn); br.addStretch(); lay.addLayout(br)
        return tab

    def _build_list_tab(self):
        tab = QWidget(); lay = QVBoxLayout(tab); lay.setSpacing(12)
        top = QGroupBox('جابجایی‌های ثبت‌شده'); tl = QVBoxLayout(top)
        self.transfers_table = QTableWidget(0, 6)
        self.transfers_table.setHorizontalHeaderLabels(['شناسه', 'شماره', 'تاریخ', 'از انبار', 'به انبار', 'اقلام'])
        self.transfers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.transfers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.transfers_table.verticalHeader().setVisible(False); self.transfers_table.setColumnHidden(0, True)
        self.transfers_table.itemSelectionChanged.connect(self._load_transfer_items)
        tl.addWidget(self.transfers_table); lay.addWidget(top, 2)
        bot = QGroupBox('اقلام جابجایی انتخاب‌شده'); bl = QVBoxLayout(bot)
        self.transfer_items_table = QTableWidget(0, 5)
        self.transfer_items_table.setHorizontalHeaderLabels(['کد پالت', 'نام پالت', 'تعداد', 'قیمت واحد', 'جمع کل'])
        self.transfer_items_table.verticalHeader().setVisible(False)
        bl.addWidget(self.transfer_items_table); lay.addWidget(bot, 2)
        return tab

    def _build_stock_tab(self):
        tab = QWidget(); lay = QVBoxLayout(tab); lay.setSpacing(12)
        bar = QHBoxLayout(); bar.addWidget(QLabel('انبار:'))
        self.stock_warehouse = QComboBox(); self.stock_warehouse.addItem('-- انتخاب انبار --', None)
        self.stock_warehouse.currentIndexChanged.connect(self._refresh_stock)
        bar.addWidget(self.stock_warehouse, 1); self.stock_total = QLabel(''); bar.addWidget(self.stock_total)
        lay.addLayout(bar)
        self.stock_table = QTableWidget(0, 4)
        self.stock_table.setHorizontalHeaderLabels(['ردیف', 'کد پالت', 'نام پالت', 'موجودی'])
        self.stock_table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.stock_table.verticalHeader().setVisible(False)
        lay.addWidget(self.stock_table); return tab

    def _on_tab_changed(self, idx):
        if idx == 1: self._refresh_transfers()
        elif idx == 2: self._refresh_stock()

    def _load_warehouses(self):
        with self.db.connect() as conn:
            rows = conn.execute('SELECT id, code, name FROM warehouses ORDER BY name').fetchall()
        for r in rows:
            d = f"{r['code']} - {r['name']}"
            self.from_warehouse.addItem(d, r['id']); self.to_warehouse.addItem(d, r['id']); self.stock_warehouse.addItem(d, r['id'])

    def _stock_rows(self, wid):
        from app.repositories.report_repository import ReportRepository
        if not wid:
            return []
        rep = ReportRepository(self.db).get_warehouse_stock_value_report(int(wid))
        out = []
        for it in rep.get('items', []):
            q = int(it.get('current_qty') or 0)
            if q > 0:
                out.append({'pallet_id': it['pallet_id'], 'code': it['pallet_code'], 'name': it['pallet_name'], 'quantity': q})
        return out

    def _load_source_pallets(self):
        wid = self.from_warehouse.currentData()
        if not wid: self.source_table.setRowCount(0); return
        with self.db.connect() as conn:
            rows = self._stock_rows(wid)
        self.source_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.source_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.source_table.setItem(i, 1, QTableWidgetItem(r['code']))
            self.source_table.setItem(i, 2, QTableWidgetItem(r['name']))
            q = QTableWidgetItem(f"{int(r['quantity']):,}"); q.setTextAlignment(Qt.AlignCenter); self.source_table.setItem(i, 3, q)
            ap = self._avg_price(conn, r['pallet_id'], wid)
            pv = QTableWidgetItem(f"{ap:,}"); pv.setTextAlignment(Qt.AlignCenter); self.source_table.setItem(i, 4, pv)

    def _add_transfer_row(self, *a):
        sel = self.source_table.selectedItems()
        if not sel: QMessageBox.warning(self, 'خطا', 'لطفاً یک پالت از جدول مبدأ انتخاب کنید.'); return
        r = sel[0].row()
        code = self.source_table.item(r, 1).text(); name = self.source_table.item(r, 2).text()
        avg = self._digits(self.source_table.item(r, 4).text())
        n = self.transfer_table.rowCount(); self.transfer_table.setRowCount(n+1)
        self.transfer_table.setItem(n, 0, QTableWidgetItem(code))
        self.transfer_table.setItem(n, 1, QTableWidgetItem(name))
        sp = QSpinBox(); sp.setRange(1, 1000000); sp.setValue(1)
        self.transfer_table.setCellWidget(n, 2, sp)
        pe = QLineEdit(str(avg)); pe.setAlignment(Qt.AlignCenter)
        self.transfer_table.setCellWidget(n, 3, pe)
        self.transfer_table.setItem(n, 4, QTableWidgetItem('0'))
        sp.valueChanged.connect(lambda _, i=n: self._recompute_row(i))
        pe.textChanged.connect(lambda _, i=n: self._recompute_row(i))
        self._recompute_row(n)

    def _recompute_row(self, i):
        if i >= self.transfer_table.rowCount(): return
        qty = self.transfer_table.cellWidget(i, 2).value()
        price = self._digits(self.transfer_table.cellWidget(i, 3).text())
        tot = qty * price
        it = QTableWidgetItem(f"{tot:,}"); it.setTextAlignment(Qt.AlignCenter)
        self.transfer_table.setItem(i, 4, it)

    def _remove_transfer_row(self):
        sel = self.transfer_table.selectedItems()
        if not sel: return
        self.transfer_table.removeRow(sel[0].row())

    # ------------------------------------------------------------------
    def _save_transfer(self):
        fw = self.from_warehouse.currentData(); tw = self.to_warehouse.currentData()
        if not fw or not tw: QMessageBox.warning(self, 'خطا', 'مبدأ و مقصد را انتخاب کنید.'); return
        if fw == tw: QMessageBox.warning(self, 'خطا', 'مبدأ و مقصد نمی‌توانند یکسان باشند.'); return
        if self.transfer_table.rowCount() == 0: QMessageBox.warning(self, 'خطا', 'حداقل یک ردیف اضافه کنید.'); return
        if QMessageBox.question(self, 'تأیید', f'جابجایی {self.transfer_table.rowCount()} پالت انجام شود؟',
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        try:
            with self.db.connect() as conn:
                now = now_iso(); tno = self._next_transfer_no(conn)
                cur = conn.execute("INSERT INTO pallet_transfers (transfer_no,transfer_date,from_warehouse_id,"
                                   "to_warehouse_id,created_by,created_at) VALUES (?,?,?,?,?,?)",
                                   (tno, self.transfer_date.date().toString('yyyy-MM-dd'), fw, tw, self.user_id, now))
                tid = cur.lastrowid
                date_iso = self.transfer_date.date().toString('yyyy-MM-dd'); count = 0
                for i in range(self.transfer_table.rowCount()):
                    code = self.transfer_table.item(i, 0).text()
                    qty = self.transfer_table.cellWidget(i, 2).value()
                    price = self._digits(self.transfer_table.cellWidget(i, 3).text())
                    total = qty * price
                    pr = conn.execute('SELECT id FROM pallets WHERE code=?', (code,)).fetchone()
                    if not pr: continue
                    pid = pr['id']
                    src = conn.execute('SELECT quantity FROM inventory_levels WHERE pallet_id=? AND warehouse_id=?', (pid, fw)).fetchone()
                    if not src or src['quantity'] < qty:
                        conn.rollback(); QMessageBox.warning(self, 'خطا', f'موجودی کافی نیست: {code}'); return
                    conn.execute('UPDATE inventory_levels SET quantity=quantity-?, updated_at=? WHERE pallet_id=? AND warehouse_id=?', (qty, now, pid, fw))
                    ex = conn.execute('SELECT id FROM inventory_levels WHERE pallet_id=? AND warehouse_id=?', (pid, tw)).fetchone()
                    if ex:
                        conn.execute('UPDATE inventory_levels SET quantity=quantity+?, updated_at=? WHERE pallet_id=? AND warehouse_id=?', (qty, now, pid, tw))
                    else:
                        conn.execute('INSERT INTO inventory_levels (pallet_id,warehouse_id,quantity,updated_at) VALUES (?,?,?,?)', (pid, tw, qty, now))
                    conn.execute('INSERT INTO pallet_transfer_items (transfer_id,pallet_id,qty,unit_price,total_price) VALUES (?,?,?,?,?)',
                                 (tid, pid, qty, price, total))
                    conn.execute("""INSERT INTO inventory_transactions
                        (transaction_date,transaction_type,reference_type,reference_id,pallet_id,warehouse_id,
                         qty_in,qty_out,unit_price,total_price,description,created_at)
                        VALUES (?,?,?,?,?,?,0,?,?,?,?,?)""",
                                 (date_iso, 'OUT', 'TRANSFER', tid, pid, fw, qty, price, total, f'جابجایی {tno} به مقصد', now))
                    conn.execute("""INSERT INTO inventory_transactions
                        (transaction_date,transaction_type,reference_type,reference_id,pallet_id,warehouse_id,
                         qty_in,qty_out,unit_price,total_price,description,created_at)
                        VALUES (?,?,?,?,?,?,?,0,?,?,?,?)""",
                                 (date_iso, 'IN', 'TRANSFER', tid, pid, tw, qty, price, total, f'جابجایی {tno} از مبدأ', now))
                    count += 1
                conn.commit()
            QMessageBox.information(self, 'موفق', f'جابجایی {tno} با {count} پالت ثبت شد.')
            self.transfer_completed.emit(); self._clear_form(); self._load_source_pallets()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا:\n{e}')

    def _clear_form(self):
        self.from_warehouse.setCurrentIndex(0); self.to_warehouse.setCurrentIndex(0)
        self.source_table.setRowCount(0); self.transfer_table.setRowCount(0)

    def _refresh_transfers(self):
        with self.db.connect() as conn:
            rows = conn.execute('''SELECT t.id, t.transfer_no, t.transfer_date, f.name AS fn, o.name AS onn,
                (SELECT COUNT(*) FROM pallet_transfer_items i WHERE i.transfer_id=t.id) AS cnt
                FROM pallet_transfers t LEFT JOIN warehouses f ON f.id=t.from_warehouse_id
                LEFT JOIN warehouses o ON o.id=t.to_warehouse_id ORDER BY t.id DESC''').fetchall()
        self.transfers_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [str(r['id']), r['transfer_no'],
                    jalali_date_display_from_iso(r['transfer_date']) if r['transfer_date'] else '-',
                    r['fn'] or '-', r['onn'] or '-', str(r['cnt'])]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter); self.transfers_table.setItem(i, c, it)

    def _load_transfer_items(self):
        r = self.transfers_table.currentRow()
        if r < 0: return
        tid = int(self.transfers_table.item(r, 0).text())
        with self.db.connect() as conn:
            rows = conn.execute('''SELECT p.code, p.name, i.qty, i.unit_price, i.total_price
                FROM pallet_transfer_items i JOIN pallets p ON p.id=i.pallet_id WHERE i.transfer_id=?''', (tid,)).fetchall()
        self.transfer_items_table.setRowCount(len(rows))
        for i, x in enumerate(rows):
            self.transfer_items_table.setItem(i, 0, QTableWidgetItem(x['code']))
            self.transfer_items_table.setItem(i, 1, QTableWidgetItem(x['name']))
            q = QTableWidgetItem(f"{int(x['qty']):,}"); q.setTextAlignment(Qt.AlignCenter); self.transfer_items_table.setItem(i, 2, q)
            pv = QTableWidgetItem(f"{int(x['unit_price'] or 0):,}"); pv.setTextAlignment(Qt.AlignCenter); self.transfer_items_table.setItem(i, 3, pv)
            tv = QTableWidgetItem(f"{int(x['total_price'] or 0):,}"); tv.setTextAlignment(Qt.AlignCenter); self.transfer_items_table.setItem(i, 4, tv)

    def _refresh_stock(self):
        wid = self.stock_warehouse.currentData()
        if not wid: self.stock_table.setRowCount(0); self.stock_total.setText(''); return
        with self.db.connect() as conn:
            rows = self._stock_rows(wid)
        self.stock_table.setRowCount(len(rows)); tot = 0
        for i, r in enumerate(rows):
            tot += int(r['quantity'])
            self.stock_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.stock_table.setItem(i, 1, QTableWidgetItem(r['code']))
            self.stock_table.setItem(i, 2, QTableWidgetItem(r['name']))
            q = QTableWidgetItem(f"{int(r['quantity']):,}"); q.setTextAlignment(Qt.AlignCenter); self.stock_table.setItem(i, 3, q)
        self.stock_total.setText(f'جمع: {tot:,} عدد')
