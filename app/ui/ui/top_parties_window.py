# -*- coding: utf-8 -*-
import tempfile, webbrowser
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDateEdit, QGridLayout, QTabWidget, QFileDialog)
from app.core.jalali import jalali_date_display_from_iso

class TopPartiesWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.user_data = user_data or {}
        self.setWindowTitle('طرف‌های حساب برتر')
        self.resize(1150, 720); self.setLayoutDirection(Qt.RightToLeft)
        self._build(); self._update_jalali(); self._load()

    def _build(self):
        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.df = QDateEdit(QDate.currentDate().addDays(-365)); self.df.setDisplayFormat('yyyy-MM-dd'); self.df.setCalendarPopup(True)
        self.dt = QDateEdit(QDate.currentDate()); self.dt.setDisplayFormat('yyyy-MM-dd'); self.dt.setCalendarPopup(True)
        self.df_j = QLabel('-'); self.df_j.setStyleSheet('color:#f59e0b;font-weight:bold;')
        self.dt_j = QLabel('-'); self.dt_j.setStyleSheet('color:#f59e0b;font-weight:bold;')
        go = QPushButton('محاسبه'); go.setObjectName('PrimaryButton'); go.clicked.connect(self._load)
        bar.addWidget(QLabel('از:')); bar.addWidget(self.df); bar.addWidget(self.df_j)
        bar.addWidget(QLabel('تا:')); bar.addWidget(self.dt); bar.addWidget(self.dt_j)
        bar.addWidget(go); bar.addStretch()
        self.df.dateChanged.connect(self._update_jalali); self.dt.dateChanged.connect(self._update_jalali)
        root.addLayout(bar)

        cards = QGridLayout()
        self.v_sale = QLabel('0'); self.v_buy = QLabel('0'); self.v_recv = QLabel('0'); self.v_pay = QLabel('0')
        for i, (t, v, c) in enumerate([('جمع فروش', self.v_sale, '#047857'), ('جمع خرید', self.v_buy, '#b91c1c'),
                                       ('مطالبات باز', self.v_recv, '#93c5fd'), ('بدهی باز', self.v_pay, '#b45309')]):
            tl = QLabel(t); tl.setStyleSheet('color:#64748b;font-weight:bold;')
            v.setStyleSheet(f'color:{c};font-size:16px;font-weight:bold;')
            cards.addWidget(tl, 0, i); cards.addWidget(v, 1, i)
        root.addLayout(cards)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet('')
        self.cust_tbl = QTableWidget(0, 5); self.cust_tbl.setHorizontalHeaderLabels(['مشتری', 'تعداد سند', 'مبلغ کل', 'تسویه شده', 'مانده باز'])
        self.sup_tbl = QTableWidget(0, 5); self.sup_tbl.setHorizontalHeaderLabels(['تأمین‌کننده', 'تعداد سند', 'مبلغ کل', 'تسویه شده', 'مانده باز'])
        for t in (self.cust_tbl, self.sup_tbl): t.verticalHeader().setVisible(False)
        self.tabs.addTab(self.cust_tbl, '🏆 مشتریان برتر')
        self.tabs.addTab(self.sup_tbl, '🏆 تأمین‌کنندگان برتر')
        root.addWidget(self.tabs)

        bb = QHBoxLayout()
        pdf = QPushButton('💾 چاپ / PDF'); pdf.clicked.connect(self._pdf)
        xls = QPushButton('📊 اکسل'); xls.clicked.connect(self._xls)
        bb.addStretch(); bb.addWidget(pdf); bb.addWidget(xls)
        root.addLayout(bb)

    def _update_jalali(self):
        self.df_j.setText(jalali_date_display_from_iso(self.df.date().toString('yyyy-MM-dd')))
        self.dt_j.setText(jalali_date_display_from_iso(self.dt.date().toString('yyyy-MM-dd')))

    def _load(self):
        d0 = self.df.date().toString('yyyy-MM-dd'); d1 = self.dt.date().toString('yyyy-MM-dd')
        with self.db.connect() as conn:
            rows = conn.execute("""
                SELECT fd.counterparty_person_id, COALESCE(p.first_name||' '||p.last_name,'-') AS name,
                       fd.direction, COUNT(*) AS cnt, SUM(fd.total_amount) AS tot, SUM(fd.settled_amount) AS stl
                FROM financial_documents fd
                LEFT JOIN persons p ON p.id = fd.counterparty_person_id
                WHERE fd.status != 'CANCELLED' AND fd.finance_date BETWEEN ? AND ?
                  AND fd.operation_type IN ('INBOUND_RECEIPT','OUTBOUND_ISSUE')
                  AND fd.finance_no NOT LIKE 'BS-%' AND fd.finance_no NOT LIKE 'BR-%' AND fd.finance_no NOT LIKE 'WP-%'
                GROUP BY fd.counterparty_person_id, fd.direction""", (d0, d1)).fetchall()
        cust = {}; sup = {}; ts = tb = tr = tp = 0
        for r in rows:
            tot = int(r['tot'] or 0); stl = int(r['stl'] or 0); rem = max(tot - stl, 0)
            if r['direction'] == 'RECEIVABLE':
                a = cust.setdefault(r['name'], [0, 0, 0, 0]); ts += tot; tr += rem
            else:
                a = sup.setdefault(r['name'], [0, 0, 0, 0]); tb += tot; tp += rem
            a[0] += int(r['cnt'] or 0); a[1] += tot; a[2] += stl; a[3] += rem
        self.v_sale.setText(f"{ts:,} ریال"); self.v_buy.setText(f"{tb:,} ریال")
        self.v_recv.setText(f"{tr:,} ریال"); self.v_pay.setText(f"{tp:,} ریال")
        self._fill(self.cust_tbl, cust); self._fill(self.sup_tbl, sup)

    def _fill(self, tbl, data):
        items = sorted(data.items(), key=lambda kv: kv[1][1], reverse=True)[:20]
        tbl.setRowCount(len(items))
        for i, (name, (cnt, tot, stl, rem)) in enumerate(items):
            vals = [name, f"{cnt:,}", f"{tot:,}", f"{stl:,}", f"{rem:,}"]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tbl.setItem(i, c, it)
        tbl.resizeColumnsToContents()

    def _pdf(self):
        def th(t):
            s = '<table><tr><th>' + '</th><th>'.join([t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]) + '</th></tr>'
            for r in range(t.rowCount()):
                s += '<tr>' + ''.join(f"<td>{t.item(r,c).text() if t.item(r,c) else ''}</td>" for c in range(t.columnCount())) + '</tr>'
            return s + '</table>'
        html = f"""<html dir='rtl'><head><meta charset='utf-8'><style>
            body{{font-family:Tahoma;padding:20px;}} h2{{text-align:center;}}
            table{{width:100%;border-collapse:collapse;margin:10px 0;}} th,td{{border:1px solid #999;padding:6px;font-size:11px;text-align:center;}} th{{background:#eee;}}
            .print-btn{{position:fixed;top:20px;left:20px;padding:10px 20px;background:#9333ea;color:#fff;border:none;border-radius:6px;cursor:pointer;}}</style></head><body>
            <button class='print-btn' onclick='window.print()'>چاپ / PDF</button>
            <h2>طرف‌های حساب برتر</h2><p>بازه: {self.df_j.text()} تا {self.dt_j.text()}</p>
            <h3>مشتریان برتر</h3>{th(self.cust_tbl)}<h3>تأمین‌کنندگان برتر</h3>{th(self.sup_tbl)}</body></html>"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html); t = f.name
        webbrowser.open('file:///' + t)

    def _xls(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره اکسل', 'top_parties.csv', 'CSV (*.csv)')
        if not path: return
        if not path.lower().endswith('.csv'): path += '.csv'
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            f.write('== مشتریان برتر ==\nنام,تعداد سند,مبلغ کل,تسویه شده,مانده باز\n')
            for r in range(self.cust_tbl.rowCount()):
                f.write(','.join(self.cust_tbl.item(r,c).text() for c in range(5)) + '\n')
            f.write('\n== تأمین‌کنندگان برتر ==\nنام,تعداد سند,مبلغ کل,تسویه شده,مانده باز\n')
            for r in range(self.sup_tbl.rowCount()):
                f.write(','.join(self.sup_tbl.item(r,c).text() for c in range(5)) + '\n')
