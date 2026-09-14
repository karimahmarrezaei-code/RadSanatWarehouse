# -*- coding: utf-8 -*-
# BoxSaleFormWindow - فرم فروش جعبه‌های تولیدشده در انبار
import math
import tempfile
import webbrowser
from datetime import datetime
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QDoubleSpinBox, QFormLayout, QFrame, QMessageBox, QTextBrowser, QGroupBox,
)
from app.core.jalali import today_iso_date, jalali_date_display_from_iso


class BoxSaleFormWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('🧾 فروش جعبه')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1150, 800)
        self._box = None
        self._parts = []
        self._ensure_tables()
        self._build_ui()
        self._load_lookups()

    def _ensure_tables(self):
        try:
            with self.db.connect() as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS box_production_items (id INTEGER PRIMARY KEY AUTOINCREMENT, box_production_id INTEGER, row_no INTEGER, part_name TEXT, count INTEGER, length_cm REAL, width_cm REAL, thickness_cm REAL)")
                conn.execute("CREATE TABLE IF NOT EXISTS box_sale_docs (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_no TEXT, sale_date TEXT, jalali_date_text TEXT, warehouse_id INTEGER, customer_id INTEGER, box_code TEXT, quantity INTEGER, unit_price INTEGER, total_amount INTEGER, total_cost INTEGER, status TEXT DEFAULT 'CONFIRMED', seller_name TEXT, buyer_name TEXT, notes TEXT, created_by INTEGER, created_at TEXT)")
                conn.execute("CREATE TABLE IF NOT EXISTS box_sale_items (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_doc_id INTEGER, row_no INTEGER, part_name TEXT, count INTEGER, length_cm REAL, width_cm REAL, thickness_cm REAL)")
                conn.commit()
        except Exception:
            pass

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        hdr = QFrame(); hdr.setObjectName('Card')
        hl = QVBoxLayout(hdr)
        t = QLabel('فرم فروش جعبه'); t.setObjectName('Title'); t.setAlignment(Qt.AlignCenter)
        s = QLabel('فروش جعبه‌های تولیدشده در انبار با شماره اتوماتیک BS و پیش‌نویس چاپ')
        s.setObjectName('Muted'); s.setAlignment(Qt.AlignCenter)
        hl.addWidget(t); hl.addWidget(s)
        root.addWidget(hdr)

        frm = QGroupBox('مشخصات فروش')
        fl = QFormLayout(frm)
        self.date_lbl = QLabel(jalali_date_display_from_iso(today_iso_date()))
        self.no_lbl = QLabel('(پس از ثبت)')
        self.warehouse_combo = QComboBox()
        self.customer_combo = QComboBox()
        self.box_combo = QComboBox()
        self.box_combo.currentIndexChanged.connect(self._on_box_changed)
        self.qty_spin = QSpinBox(); self.qty_spin.setRange(1, 1000); self.qty_spin.setValue(1)
        self.qty_spin.valueChanged.connect(self._recalc)
        self.basis_combo = QComboBox()
        self.basis_combo.addItem('قیمت مبنا: بهای تمام‌شده', 'cost')
        self.basis_combo.addItem('قیمت مبنا: قیمت فروش', 'sale')
        self.basis_combo.setCurrentIndex(1)
        self.basis_combo.currentIndexChanged.connect(self._recalc)
        self.price_spin = QDoubleSpinBox(); self.price_spin.setRange(0, 999999999999); self.price_spin.setDecimals(0); self.price_spin.setSingleStep(1000000)
        self.price_spin.valueChanged.connect(self._recalc)
        self.total_lbl = QLabel('0 ریال')
        self.total_lbl.setStyleSheet('font-weight:bold;color:#16a34a;font-size:15px;')
        self.dims_lbl = QLabel('-')
        fl.addRow('تاریخ:', self.date_lbl)
        fl.addRow('شماره:', self.no_lbl)
        fl.addRow('انبار:', self.warehouse_combo)
        fl.addRow('خریدار:', self.customer_combo)
        fl.addRow('جعبه:', self.box_combo)
        fl.addRow('ابعاد ساخت:', self.dims_lbl)
        fl.addRow('تعداد:', self.qty_spin)
        fl.addRow('مبنای قیمت:', self.basis_combo)
        fl.addRow('قیمت واحد (ریال):', self.price_spin)
        fl.addRow('مبلغ کل:', self.total_lbl)
        root.addWidget(frm)

        pv = QGroupBox('پیش‌نمایش سه‌بعدی و آیتم‌های ساخت')
        pvl = QVBoxLayout(pv)
        self.preview_browser = QTextBrowser()
        self.preview_browser.setMinimumHeight(330)
        pvl.addWidget(self.preview_browser)
        root.addWidget(pv)

        btn = QHBoxLayout()
        save_btn = QPushButton('💾 ثبت فروش و پیش‌نویس')
        save_btn.setObjectName('PrimaryButton'); save_btn.setMinimumHeight(50)
        save_btn.clicked.connect(self._save)
        print_btn = QPushButton('🖨 چاپ / PDF')
        print_btn.setObjectName('SecondaryButton'); print_btn.setMinimumHeight(50)
        print_btn.clicked.connect(self._do_print)
        close_btn = QPushButton('بستن')
        close_btn.setObjectName('SecondaryButton'); close_btn.setMinimumHeight(50)
        close_btn.clicked.connect(self.accept)
        btn.addWidget(save_btn); btn.addWidget(print_btn); btn.addWidget(close_btn)
        root.addLayout(btn)
        self._last_doc = None

    def _load_lookups(self):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                whs = conn.execute("SELECT id, code, name FROM warehouses WHERE is_active=1 ORDER BY code").fetchall()
                try:
                    cust = conn.execute("SELECT id, TRIM(COALESCE(company_name,'') || ' ' || COALESCE(first_name,'') || ' ' || COALESCE(last_name,'')) FROM persons ORDER BY id").fetchall()
                except Exception:
                    cust = conn.execute("SELECT id, TRIM(COALESCE(first_name,'') || ' ' || COALESCE(last_name,'')) FROM persons ORDER BY id").fetchall()
                boxes = conn.execute("SELECT bi.box_code, bi.quantity, bi.length_cm, bi.width_cm, bi.height_cm, bi.cost_price, COALESCE(bp.total_cost,0), bp.id FROM box_inventory bi LEFT JOIN box_production bp ON bp.box_code=bi.box_code WHERE bi.quantity>0 ORDER BY bi.box_code").fetchall()
        except Exception:
            whs, cust, boxes = [], [], []
        self.warehouse_combo.clear(); self.warehouse_combo.addItem('-- انبار --', None)
        for w in whs:
            self.warehouse_combo.addItem('{} | {}'.format(w[1], w[2]), w[0])
        self.customer_combo.clear(); self.customer_combo.addItem('-- خریدار --', None)
        for c in cust:
            self.customer_combo.addItem(c[1] or 'شخص {}'.format(c[0]), c[0])
        self.box_combo.clear(); self.box_combo.addItem('-- جعبه --', None)
        self._boxes = {}
        for b in boxes:
            self._boxes[b[0]] = {'qty': b[1], 'length_cm': b[2], 'width_cm': b[3], 'height_cm': b[4], 'sale_unit': b[5] or 0, 'total_cost': b[6] or 0, 'prod_id': b[7]}
            self.box_combo.addItem('{} | {}×{}×{} | موجودی: {}'.format(b[0], int(b[2] or 0), int(b[3] or 0), int(b[4] or 0), b[1]), b[0])

    def _on_box_changed(self, *_a):
        code = self.box_combo.currentData()
        self._box = getattr(self, '_boxes', {}).get(code)
        if not self._box:
            self._parts = []; self.dims_lbl.setText('-'); self._refresh_preview(); return
        b = self._box
        self.dims_lbl.setText('{:g} × {:g} × {:g} cm'.format(b['length_cm'] or 0, b['width_cm'] or 0, b['height_cm'] or 0))
        self.qty_spin.setMaximum(max(1, b['qty']))
        self._load_parts(b.get('prod_id'))
        self._recalc()

    def _load_parts(self, prod_id):
        self._parts = []
        if not prod_id:
            self._refresh_preview(); return
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("SELECT part_name, count, length_cm, width_cm, thickness_cm FROM box_production_items WHERE box_production_id=? ORDER BY row_no", (prod_id,)).fetchall()
            self._parts = [{'name': r[0], 'count': r[1], 'l': r[2], 'w': r[3], 't': r[4]} for r in rows]
        except Exception:
            self._parts = []
        self._refresh_preview()

    def _cost_unit(self):
        if not self._box:
            return 0
        q = max(1, self._box['qty'])
        if (self.basis_combo.currentData() or 'sale') == 'sale':
            return int(self._box['sale_unit'] or 0)
        return int(self._box['total_cost'] / q)

    def _recalc(self, *_a):
        if self._box:
            self.price_spin.blockSignals(True)
            self.price_spin.setValue(self._cost_unit())
            self.price_spin.blockSignals(False)
        self.total_lbl.setText('{:,} ریال'.format(int(self.price_spin.value()) * self.qty_spin.value()))

    def _iso_svg(self, L, W, H):
        c30 = math.cos(math.radians(30)); s30 = 0.5
        mx = max(L, W, H) or 1.0
        k = 150.0 / mx
        lx, ly = L*k*c30, L*k*s30
        wx, wy = W*k*c30, W*k*s30
        hz = H*k
        ox, oy = 210.0, 235.0
        p0=(ox,oy); p1=(ox+lx,oy-ly); p2=(ox-wx,oy-wy)
        t0=(ox,oy-hz); t1=(ox+lx,oy-ly-hz); t2=(ox-wx,oy-wy-hz); t3=(ox+lx-wx,oy-ly-wy-hz)
        def P(p): return '{:.1f},{:.1f}'.format(p[0], p[1])
        top=' '.join(P(x) for x in (t0,t1,t3,t2))
        right=' '.join(P(x) for x in (p0,p1,t1,t0))
        left=' '.join(P(x) for x in (p0,p2,t2,t0))
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 300" width="420" height="300">'
            '<rect width="100%%" height="100%%" fill="#f8fafc"/>'
            '<polygon points="%s" fill="#e9c9a0" stroke="#46505f" stroke-width="2"/>'
            '<polygon points="%s" fill="#d3a878" stroke="#46505f" stroke-width="2"/>'
            '<polygon points="%s" fill="#b98d5f" stroke="#46505f" stroke-width="2"/>'
            '<text x="%d" y="%d" font-size="12" font-weight="bold" fill="#2563eb">طول: %g cm</text>'
            '<text x="%d" y="%d" font-size="12" font-weight="bold" fill="#2563eb">عرض: %g cm</text>'
            '<text x="%d" y="%d" font-size="12" font-weight="bold" fill="#dc2626">ارتفاع: %g cm</text>'
            '</svg>') % (top, right, left,
            (p0[0]+p1[0])/2-20, (p0[1]+p1[1])/2+24, L,
            (p0[0]+p2[0])/2-45, (p0[1]+p2[1])/2+24, W,
            ox+8, oy-hz/2, H)

    def _refresh_preview(self):
        b = self._box or {}
        svg = self._iso_svg(b.get('length_cm') or 0, b.get('width_cm') or 0, b.get('height_cm') or 0) if b else ''
        rows = ''.join('<tr><td>{}</td><td>{}</td><td>{}</td><td>{:g}</td><td>{:g}</td><td>{:g}</td></tr>'.format(i, p['name'], p['count'], p['l'] or 0, p['w'] or 0, p['t'] or 0) for i, p in enumerate(self._parts, 1))
        if not rows:
            rows = '<tr><td colspan="6">آیتم ساخت ذخیره‌شده‌ای برای این جعبه نیست.</td></tr>'
        html = ('<html dir="rtl"><body style="font-family:Tahoma;">' + svg +
            '<table border="1" cellspacing="0" cellpadding="6" style="width:100%;border-collapse:collapse;text-align:center;font-size:12px;">'
            '<tr><th>ردیف</th><th>قطعه</th><th>تعداد</th><th>طول</th><th>عرض</th><th>ضخامت</th></tr>' + rows + '</table></body></html>')
        self.preview_browser.setHtml(html)

    def _company_name(self, conn):
        try:
            r = conn.execute("SELECT company_name FROM company_profile ORDER BY id LIMIT 1").fetchone()
            if r and r[0]:
                return str(r[0]).strip()
        except Exception:
            pass
        return 'راد صنعت نوین'

    def _next_sale_no(self, conn):
        jy = jalali_date_display_from_iso(today_iso_date())[:4]
        prefix = 'BS-' + jy + '-'
        row = conn.execute("SELECT COUNT(*) FROM box_sale_docs WHERE sale_no LIKE ?", (prefix + '%',)).fetchone()
        return prefix + '{:04d}'.format((row[0] or 0) + 1)

    def _save(self):
        wh = self.warehouse_combo.currentData()
        cust = self.customer_combo.currentData()
        box = self.box_combo.currentData()
        qty = self.qty_spin.value()
        if not wh or not cust or not box:
            QMessageBox.warning(self, 'توجه', 'انبار، خریدار و جعبه را انتخاب کنید.')
            return
        if qty <= 0:
            QMessageBox.warning(self, 'توجه', 'تعداد باید بزرگ‌تر از صفر باشد.')
            return
        unit = int(self.price_spin.value())
        total = unit * qty
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                stock = conn.execute("SELECT quantity FROM box_inventory WHERE box_code=?", (box,)).fetchone()
                if not stock or (stock[0] or 0) < qty:
                    QMessageBox.warning(self, 'توجه', 'موجودی کافی نیست. موجودی: {}'.format(stock[0] if stock else 0))
                    return
                sale_no = self._next_sale_no(conn)
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                seller = self._company_name(conn)
                buyer = self.customer_combo.currentText()
                conn.execute("INSERT INTO box_sale_docs (sale_no, sale_date, jalali_date_text, warehouse_id, customer_id, box_code, quantity, unit_price, total_amount, total_cost, status, seller_name, buyer_name, notes, created_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (sale_no, today_iso_date(), jalali_date_display_from_iso(today_iso_date()), wh, cust, box, qty, unit, total, int(self._cost_unit()*qty), 'CONFIRMED', seller, buyer, '', self.user_data.get('id') or 1, now))
                doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                for i, p in enumerate(self._parts, 1):
                    conn.execute("INSERT INTO box_sale_items (sale_doc_id, row_no, part_name, count, length_cm, width_cm, thickness_cm) VALUES (?,?,?,?,?,?,?)",
                        (doc_id, i, p['name'], p['count'], p['l'], p['w'], p['t']))
                conn.execute("UPDATE box_inventory SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP WHERE box_code=?", (qty, box))
                try:
                    fno = 'FIN-{:05d}'.format(conn.execute("SELECT COUNT(*)+1 FROM financial_documents").fetchone()[0])
                    conn.execute("INSERT INTO financial_documents (finance_no, operation_type, direction, counterparty_person_id, finance_date, total_amount, settled_amount, status, description, created_at, created_by) VALUES (?,?,?,?,?,?,0,'OPEN',?,?,?)" ,
                        (fno, 'BOX_SALE', 'RECEIVABLE', cust, today_iso_date(), total, 'فروش جعبه ' + sale_no, now, self.user_data.get('id') or 1))
                except Exception as fe:
                    print('[box-sale] finance skip:', fe)
                conn.commit()
            self.no_lbl.setText(sale_no)
            self._last_doc = {'sale_no': sale_no, 'box': box, 'qty': qty, 'unit': unit, 'total': total,
                              'buyer': buyer, 'seller': seller, 'wh': self.warehouse_combo.currentText(),
                              'dims': self.dims_lbl.text()}
            QMessageBox.information(self, 'موفق', 'فروش با شماره {} ثبت شد.\nمبلغ کل: {:,} ریال'.format(sale_no, total))
            self._load_lookups()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'ثبت فروش با خطا مواجه شد:\n{}'.format(e))

    def _print_html(self, d):
        rows = ''.join('<tr><td>{}</td><td>{}</td><td>{}</td><td>{:g}</td><td>{:g}</td><td>{:g}</td></tr>'.format(i, p['name'], p['count'], p['l'] or 0, p['w'] or 0, p['t'] or 0) for i, p in enumerate(self._parts, 1))
        svg = self._iso_svg(self._box['length_cm'] or 0, self._box['width_cm'] or 0, self._box['height_cm'] or 0) if self._box else ''
        return ('<html dir="rtl" lang="fa"><head><meta charset="utf-8"/><style>'
                'body{font-family:Tahoma;margin:24px;color:#0f172a;}'
                'table{width:100%;border-collapse:collapse;margin-top:10px;}'
                'th,td{border:1px solid #cbd5e1;padding:7px;font-size:12px;text-align:center;}'
                'th{background:#e2e8f0;}'
                '.sig{margin-top:60px;}'
                '</style></head><body>'
                '<h1 style="text-align:center;">' + d['seller'] + ' - سند فروش جعبه</h1>'
                '<table><tr><td>شماره</td><td>' + d['sale_no'] + '</td><td>تاریخ</td><td>' + jalali_date_display_from_iso(today_iso_date()) + '</td></tr>'
                '<tr><td>خریدار</td><td>' + d['buyer'] + '</td><td>انبار</td><td>' + d['wh'] + '</td></tr>'
                '<tr><td>جعبه</td><td>' + d['box'] + '</td><td>ابعاد</td><td>' + d['dims'] + '</td></tr>'
                '<tr><td>تعداد</td><td>' + str(d['qty']) + '</td><td>مبلغ کل</td><td>' + '{:,} ریال'.format(d['total']) + '</td></tr></table>'
                '<div style="text-align:center;">' + svg + '</div>'
                '<table><tr><th>ردیف</th><th>قطعه</th><th>تعداد</th><th>طول</th><th>عرض</th><th>ضخامت</th></tr>' + (rows or '<tr><td colspan="6">-</td></tr>') + '</table>'
                '<table class="sig"><tr><td>مهر و امضای فروشنده: ' + d['seller'] + '</td><td>مهر و امضای خریدار: ' + d['buyer'] + '</td></tr></table>'
                '<script>window.onload=function(){setTimeout(function(){window.print();},400);};</script>'
                '</body></html>')

    def _do_print(self):
        if not self._last_doc:
            QMessageBox.warning(self, 'توجه', 'ابتدا فروش را ثبت کنید.')
            return
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(self._print_html(self._last_doc))
            path = f.name
        webbrowser.open('file:///' + path)
