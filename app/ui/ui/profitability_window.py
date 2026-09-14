# -*- coding: utf-8 -*-
import tempfile, webbrowser
from datetime import date, timedelta
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDateEdit, QGroupBox, QGridLayout, QTabWidget, QWidget, QFileDialog)
from app.core.jalali import jalali_date_display_from_iso

class ProfitabilityWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.user_data = user_data or {}
        self.setWindowTitle('سودآوری به تفکیک مشتری / کالا')
        self.resize(1200, 750); self.setLayoutDirection(Qt.RightToLeft)
        self._build(); self._update_jalali(); self._load()

    def _build(self):
        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.df = QDateEdit(QDate.currentDate().addDays(-30)); self.df.setDisplayFormat('yyyy-MM-dd'); self.df.setCalendarPopup(True)
        self.dt = QDateEdit(QDate.currentDate()); self.dt.setDisplayFormat('yyyy-MM-dd'); self.dt.setCalendarPopup(True)
        go = QPushButton('محاسبه'); go.setObjectName('PrimaryButton'); go.clicked.connect(self._load)
        bar.addWidget(QLabel('از:')); bar.addWidget(self.df)
        self.df_jalali_lbl = QLabel('-'); self.df_jalali_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        bar.addWidget(self.df_jalali_lbl)
        bar.addWidget(QLabel('تا:')); bar.addWidget(self.dt)
        self.dt_jalali_lbl = QLabel('-'); self.dt_jalali_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        bar.addWidget(self.dt_jalali_lbl)
        bar.addWidget(go); bar.addStretch()
        self.df.dateChanged.connect(self._update_jalali)
        self.dt.dateChanged.connect(self._update_jalali)
        root.addLayout(bar)

        cards = QGridLayout()
        self.v_rev = QLabel('0'); self.v_cost = QLabel('0'); self.v_profit = QLabel('0'); self.v_margin = QLabel('0%')
        for i, (t, v, c) in enumerate([('درآمد فروش', self.v_rev, '#047857'), ('بهای تمام‌شده', self.v_cost, '#b91c1c'),
                                       ('سود ناخالص', self.v_profit, '#059669'), ('حاشیه سود', self.v_margin, '#0891b2')]):
            tl = QLabel(t); tl.setStyleSheet('color:#64748b;font-weight:bold;')
            v.setStyleSheet(f'color:{c};font-size:16px;font-weight:bold;')
            cards.addWidget(tl, 0, i); cards.addWidget(v, 1, i)
        root.addLayout(cards)

        self.tabs = QTabWidget()
        self.cust_tbl = QTableWidget(0, 7); self.cust_tbl.setHorizontalHeaderLabels(['مشتری', 'تعداد', 'درآمد', 'بهای تمام', 'سود', 'حاشیه٪', 'markup روی بها٪'])
        self.prod_tbl = QTableWidget(0, 7); self.prod_tbl.setHorizontalHeaderLabels(['کالا', 'تعداد', 'درآمد', 'بهای تمام', 'سود', 'حاشیه٪', 'markup روی بها٪'])
        for t in (self.cust_tbl, self.prod_tbl): t.verticalHeader().setVisible(False)
        self.tabs.addTab(self.cust_tbl, 'به تفکیک مشتری')
        self.tabs.addTab(self.prod_tbl, 'به تفکیک کالا')
        self.tabs.setStyleSheet('')
        root.addWidget(self.tabs)

        bb = QHBoxLayout()
        pdf = QPushButton('💾 چاپ / PDF'); pdf.clicked.connect(self._pdf)
        xls = QPushButton('📊 اکسل'); xls.clicked.connect(self._xls)
        bb.addStretch(); bb.addWidget(pdf); bb.addWidget(xls)
        root.addLayout(bb)

    def _update_jalali(self):
        self.df_jalali_lbl.setText(jalali_date_display_from_iso(self.df.date().toString('yyyy-MM-dd')))
        self.dt_jalali_lbl.setText(jalali_date_display_from_iso(self.dt.date().toString('yyyy-MM-dd')))

    def _cost_map(self, conn):
        rows = conn.execute("""
            SELECT pid, SUM(val)/SUM(q) AS avg FROM (
                SELECT oii.pallet_id AS pid, oii.qty*oii.unit_price AS val, oii.qty AS q FROM opening_inventory_items oii
                UNION ALL
                SELECT ri.pallet_id, ri.qty*ri.unit_price, ri.qty FROM warehouse_receipt_items ri WHERE ri.unit_price>0 AND ri.qty>0
            ) GROUP BY pid""").fetchall()
        return {r['pid']: (r['avg'] or 0) for r in rows}

    def _load(self):
        d0 = self.df.date().toString('yyyy-MM-dd'); d1 = self.dt.date().toString('yyyy-MM-dd')
        with self.db.connect() as conn:
            cost = self._cost_map(conn)
            sales = conn.execute("""
                SELECT wi.customer_id, COALESCE(p.first_name||' '||p.last_name,'-') AS cust,
                       ii.pallet_id, pal.code||' '||pal.name AS prod, ii.qty, ii.unit_price
                FROM warehouse_issues wi
                JOIN warehouse_issue_items ii ON ii.issue_id=wi.id
                LEFT JOIN persons p ON p.id=wi.customer_id
                JOIN pallets pal ON pal.id=ii.pallet_id
                WHERE wi.issue_date BETWEEN ? AND ?""", (d0, d1)).fetchall()
            rets = conn.execute("""
                SELECT wi.customer_id, COALESCE(p.first_name||' '||p.last_name,'-') AS cust,
                       ri.pallet_id, pal.code||' '||pal.name AS prod, ri.qty, ri.unit_price
                FROM return_items ri
                JOIN warehouse_issues wi ON wi.id=ri.source_doc_id
                LEFT JOIN persons p ON p.id=wi.customer_id
                JOIN pallets pal ON pal.id=ri.pallet_id
                WHERE ri.return_type='ISSUE' AND ri.return_date BETWEEN ? AND ?""", (d0, d1)).fetchall()

        cust = {}; prod = {}; tot = [0, 0]
        def add(d, key, qty, price, sign):
            c = cost.get(key_pid, 0)
        # aggregate
        for r in sales:
            key_pid = r['pallet_id']
            rev = r['qty'] * (r['unit_price'] or 0); cst = r['qty'] * cost.get(key_pid, 0)
            tot[0] += rev; tot[1] += cst
            a = cust.setdefault(r['cust'], [0, 0, 0]); a[0] += r['qty']; a[1] += rev; a[2] += cst
            b = prod.setdefault(r['prod'], [0, 0, 0]); b[0] += r['qty']; b[1] += rev; b[2] += cst
        for r in rets:
            key_pid = r['pallet_id']
            rev = r['qty'] * (r['unit_price'] or 0); cst = r['qty'] * cost.get(key_pid, 0)
            tot[0] -= rev; tot[1] -= cst
            a = cust.setdefault(r['cust'], [0, 0, 0]); a[0] -= r['qty']; a[1] -= rev; a[2] -= cst
            b = prod.setdefault(r['prod'], [0, 0, 0]); b[0] -= r['qty']; b[1] -= rev; b[2] -= cst

        profit = tot[0] - tot[1]
        self.v_rev.setText(f"{tot[0]:,} ریال"); self.v_cost.setText(f"{tot[1]:,} ریال")
        self.v_profit.setText(f"{profit:,} ریال")
        self.v_margin.setText(f"{(profit/tot[0]*100) if tot[0] else 0:.1f}%")
        self._rows = {'cust': cust, 'prod': prod}
        self._fill(self.cust_tbl, cust); self._fill(self.prod_tbl, prod)

    def _fill(self, tbl, data):
        items = sorted(data.items(), key=lambda kv: kv[1][2]-kv[1][1], reverse=False)
        items = sorted(data.items(), key=lambda kv: (kv[1][1]-kv[1][2]), reverse=True)
        tbl.setRowCount(len(items))
        for i, (name, (q, rev, cst)) in enumerate(items):
            pr = rev - cst; mg = (pr/rev*100) if rev else 0
            mk = (pr/cst*100) if cst else 0
            vals = [name, f"{q:,}", f"{rev:,}", f"{cst:,}", f"{pr:,}", f"{mg:.1f}", f"{mk:.1f}"]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tbl.setItem(i, c, it)
        tbl.resizeColumnsToContents()

    def _pdf(self):
        def tbl_html(t):
            s = '<table><tr><th>' + '</th><th>'.join([t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]) + '</th></tr>'
            for r in range(t.rowCount()):
                s += '<tr>' + ''.join(f"<td>{t.item(r,c).text() if t.item(r,c) else ''}</td>" for c in range(t.columnCount())) + '</tr>'
            return s + '</table>'
        html = f"""<html dir='rtl'><head><meta charset='utf-8'><style>
            body{{font-family:Tahoma;padding:20px;}} h2{{text-align:center;}}
            table{{width:100%;border-collapse:collapse;margin:10px 0;}} th,td{{border:1px solid #999;padding:6px;font-size:11px;text-align:center;}} th{{background:#eee;}}
            .print-btn{{position:fixed;top:20px;left:20px;padding:10px 20px;background:#9333ea;color:#fff;border:none;border-radius:6px;cursor:pointer;}}</style></head><body>
            <button class='print-btn' onclick='window.print()'>چاپ / PDF</button>
            <h2>سودآوری به تفکیک مشتری / کالا</h2>
            <p>بازه گزارش: {self.df_jalali_lbl.text()} تا {self.dt_jalali_lbl.text()}</p>
            <p>درآمد: {self.v_rev.text()} | بهای تمام: {self.v_cost.text()} | سود: {self.v_profit.text()} | حاشیه: {self.v_margin.text()}</p>
            <h3>به تفکیک مشتری</h3>{tbl_html(self.cust_tbl)}
            <h3>به تفکیک کالا</h3>{tbl_html(self.prod_tbl)}</body></html>"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html); t = f.name
        webbrowser.open('file:///' + t)

    def _xls(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره اکسل', 'profitability.csv', 'CSV (*.csv)')
        if not path: return
        if not path.lower().endswith('.csv'): path += '.csv'
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            f.write('== به تفکیک مشتری ==\nنام,تعداد,درآمد,بهای تمام,سود,حاشیه%\n')
            for r in range(self.cust_tbl.rowCount()):
                f.write(','.join(self.cust_tbl.item(r,c).text() for c in range(7)) + '\n')
            f.write('\n== به تفکیک کالا ==\nنام,تعداد,درآمد,بهای تمام,سود,حاشیه%\n')
            for r in range(self.prod_tbl.rowCount()):
                f.write(','.join(self.prod_tbl.item(r,c).text() for c in range(7)) + '\n')
