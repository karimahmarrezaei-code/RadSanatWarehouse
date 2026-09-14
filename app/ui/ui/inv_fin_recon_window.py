# -*- coding: utf-8 -*-
import tempfile, webbrowser
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGridLayout, QFileDialog)
from app.core.jalali import jalali_date_display_from_iso, today_iso_date

class InvFinReconWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.user_data = user_data or {}
        self.setWindowTitle('مغایرت انبار و مالی (کنترل داخلی)')
        self.resize(1150, 720); self.setLayoutDirection(Qt.RightToLeft)
        self._build(); self._load()

    def _build(self):
        root = QVBoxLayout(self)
        self.asof = QLabel(''); self.asof.setStyleSheet('color:#f59e0b;font-weight:bold;')
        root.addWidget(self.asof)
        cards = QGridLayout()
        self.v_actual = QLabel('0'); self.v_theo = QLabel('0'); self.v_diff = QLabel('0')
        self.v_recv = QLabel('0'); self.v_pay = QLabel('0')
        for i, (t, v, c) in enumerate([('ارزش موجودی انبار (واقعی)', self.v_actual, '#047857'),
                                       ('ارزش تئوری (افتتاحیه+خرید−فروش)', self.v_theo, '#93c5fd'),
                                       ('مغایرت انبار', self.v_diff, '#f59e0b'),
                                       ('مطالبات باز', self.v_recv, '#bfdbfe'), ('بدهی باز', self.v_pay, '#fca5a5')]):
            tl = QLabel(t); tl.setStyleSheet('color:#64748b;font-weight:bold;')
            v.setStyleSheet(f'color:{c};font-size:16px;font-weight:bold;')
            cards.addWidget(tl, 0, i); cards.addWidget(v, 1, i)
        root.addLayout(cards)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(['کالا', 'موجودی', 'میانگین بهای تمام', 'ارزش (ریال)', 'انبار'])
        self.tbl.verticalHeader().setVisible(False)
        root.addWidget(self.tbl)

        bb = QHBoxLayout()
        pdf = QPushButton('💾 چاپ / PDF'); pdf.clicked.connect(self._pdf)
        xls = QPushButton('📊 اکسل'); xls.clicked.connect(self._xls)
        bb.addStretch(); bb.addWidget(pdf); bb.addWidget(xls)
        root.addLayout(bb)

    def _load(self):
        self.asof.setText(f'تاریخ گزارش: {jalali_date_display_from_iso(today_iso_date())}')
        with self.db.connect() as conn:
            cost = {r['pid']: (r['avg'] or 0) for r in conn.execute("""
                SELECT pid, SUM(val)/SUM(q) AS avg FROM (
                    SELECT oii.pallet_id AS pid, oii.qty*oii.unit_price AS val, oii.qty AS q FROM opening_inventory_items oii
                    UNION ALL SELECT ri.pallet_id, ri.qty*ri.unit_price, ri.qty FROM warehouse_receipt_items ri WHERE ri.unit_price>0 AND ri.qty>0
                ) GROUP BY pid""").fetchall()}
            levels = conn.execute("SELECT pallet_id, warehouse_id, quantity FROM inventory_levels WHERE quantity>0").fetchall()
            opening = conn.execute("SELECT COALESCE(SUM(qty*unit_price),0) FROM opening_inventory_items").fetchone()[0]
            purchases = conn.execute("SELECT COALESCE(SUM(qty*unit_price),0) FROM warehouse_receipt_items WHERE unit_price>0").fetchone()[0]
            issue_qty = conn.execute("SELECT pallet_id, SUM(qty) q FROM warehouse_issue_items GROUP BY pallet_id").fetchall()
            wh = {r['id']: r['name'] for r in conn.execute("SELECT id, name FROM warehouses")}
            openfin = conn.execute("""SELECT direction, SUM(total_amount-settled_amount) FROM financial_documents
                WHERE status!='CANCELLED' AND operation_type IN ('INBOUND_RECEIPT','OUTBOUND_ISSUE')
                AND finance_no NOT LIKE 'BS-%' AND finance_no NOT LIKE 'BR-%' AND finance_no NOT LIKE 'WP-%'
                GROUP BY direction""").fetchall()
        cogs = sum((r['q'] or 0) * cost.get(r['pallet_id'], 0) for r in issue_qty)
        actual = 0; rows = []
        for r in levels:
            c = cost.get(r['pallet_id'], 0); val = (r['quantity'] or 0) * c; actual += val
            rows.append((r['pallet_id'], r['quantity'], c, val, wh.get(r['warehouse_id'], '-')))
        theo = (opening or 0) + (purchases or 0) - cogs
        diff = actual - theo
        recv = pay = 0
        for d, v in openfin:
            if d == 'RECEIVABLE': recv = int(v or 0)
            else: pay = int(v or 0)
        self.v_actual.setText(f"{actual:,.0f} ریال"); self.v_theo.setText(f"{theo:,.0f} ریال")
        self.v_diff.setText(f"{diff:,.0f} ریال")
        self.v_recv.setText(f"{recv:,} ریال"); self.v_pay.setText(f"{pay:,} ریال")

        # نام پالت‌ها
        with self.db.connect() as conn:
            names = {r['id']: (r['code'] + ' ' + r['name']) for r in conn.execute("SELECT id, code, name FROM pallets")}
        rows.sort(key=lambda x: x[3], reverse=True)
        self.tbl.setRowCount(len(rows))
        for i, (pid, q, c, val, wname) in enumerate(rows):
            vals = [names.get(pid, str(pid)), f"{q:,}", f"{c:,.0f}", f"{val:,.0f}", wname]
            for cc, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl.setItem(i, cc, it)
        self.tbl.resizeColumnsToContents()

    def _pdf(self):
        s = '<table><tr><th>' + '</th><th>'.join([self.tbl.horizontalHeaderItem(c).text() for c in range(5)]) + '</th></tr>'
        for r in range(self.tbl.rowCount()):
            s += '<tr>' + ''.join(f"<td>{self.tbl.item(r,c).text()}</td>" for c in range(5)) + '</tr>'
        html = f"""<html dir='rtl'><head><meta charset='utf-8'><style>
            body{{font-family:Tahoma;padding:20px;}} h2{{text-align:center;}}
            table{{width:100%;border-collapse:collapse;}} th,td{{border:1px solid #999;padding:6px;font-size:11px;text-align:center;}} th{{background:#eee;}}
            .print-btn{{position:fixed;top:20px;left:20px;padding:10px 20px;background:#9333ea;color:#fff;border:none;border-radius:6px;cursor:pointer;}}</style></head><body>
            <button class='print-btn' onclick='window.print()'>چاپ / PDF</button>
            <h2>مغایرت انبار و مالی</h2><p>{self.asof.text()}</p>
            <p>واقعی: {self.v_actual.text()} | تئوری: {self.v_theo.text()} | مغایرت: {self.v_diff.text()} | مطالبات: {self.v_recv.text()} | بدهی: {self.v_pay.text()}</p>
            {s}</table></body></html>"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html); t = f.name
        webbrowser.open('file:///' + t)

    def _xls(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره اکسل', 'inv_recon.csv', 'CSV (*.csv)')
        if not path: return
        if not path.lower().endswith('.csv'): path += '.csv'
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            f.write('کالا,موجودی,میانگین بها,ارزش,انبار\n')
            for r in range(self.tbl.rowCount()):
                f.write(','.join(self.tbl.item(r,c).text() for c in range(5)) + '\n')
