# -*- coding: utf-8 -*-
from datetime import date
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QGridLayout)
from app.core.jalali import jalali_date_display_from_iso, today_iso_date

BUCKETS = [('OVERDUE','سررسید گذشته'),('TODAY','امروز'),('W1','۱ تا ۷ روز'),
           ('W2','۸ تا ۱۵ روز'),('M1','۱۶ تا ۳۰ روز'),('LATER','بیش از ۳۰ روز'),('NO_DUE','بدون سررسید')]

class CashflowWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.user_data = user_data or {}
        self.setWindowTitle('پیش‌بینی جریان نقدینگی')
        self.resize(1150, 720); self.setLayoutDirection(Qt.RightToLeft)
        self._build(); self._load()

    def _card(self, title, color):
        lb = QLabel('0 ریال')
        lb.setStyleSheet(f'color:{color};font-size:16px;font-weight:bold;')
        return QLabel(title), lb

    def _build(self):
        root = QVBoxLayout(self)
        g = QGroupBox('خلاصه نقدینگی'); gl = QGridLayout(g)
        self.t_cur, self.v_cur = self._card('مانده فعلی صندوق/بانک', '#047857')
        self.t_in, self.v_in = self._card('وصولی‌های پیش‌رو (چک دریافتنی)', '#93c5fd')
        self.t_out, self.v_out = self._card('پرداخت‌های پیش‌رو (چک پرداختنی)', '#b91c1c')
        self.t_net, self.v_net = self._card('خالص پیش‌بینی', '#f59e0b')
        for i, (t, v) in enumerate([(self.t_cur,self.v_cur),(self.t_in,self.v_in),(self.t_out,self.v_out),(self.t_net,self.v_net)]):
            gl.addWidget(t, 0, i); gl.addWidget(v, 1, i)
        root.addWidget(g)

        self.sum_tbl = QTableWidget(0, 4)
        self.sum_tbl.setHorizontalHeaderLabels(['بازه سررسید', 'ورود (وصولی)', 'خروج (پرداخت)', 'خالص'])
        self.sum_tbl.verticalHeader().setVisible(False)
        root.addWidget(self.sum_tbl)

        self.det_tbl = QTableWidget(0, 6)
        self.det_tbl.setHorizontalHeaderLabels(['تاریخ سررسید (شمسی)', 'میلادی', 'جهت', 'طرف حساب', 'شماره چک', 'مبلغ'])
        self.det_tbl.verticalHeader().setVisible(False)
        root.addWidget(self.det_tbl)

        bar = QHBoxLayout()
        pdf = QPushButton('💾 چاپ / PDF'); pdf.clicked.connect(self._pdf)
        xls = QPushButton('📊 اکسل'); xls.clicked.connect(self._xls)
        bar.addStretch(); bar.addWidget(pdf); bar.addWidget(xls)
        root.addLayout(bar)

    def _load(self):
        today = today_iso_date(); t0 = date.fromisoformat(today)
        buckets = {k: [0, 0] for k, _ in BUCKETS}
        self.details = []
        with self.db.connect() as conn:
            rows = conn.execute("""
                SELECT pe.amount, pe.due_date, fd.direction, pe.check_no,
                       COALESCE(p.first_name||' '||p.last_name,'-') AS person
                FROM payment_entries pe
                JOIN financial_documents fd ON fd.id = pe.financial_document_id
                LEFT JOIN persons p ON p.id = fd.counterparty_person_id
                WHERE pe.status='PENDING'
            """).fetchall()
            cur = conn.execute("SELECT COALESCE(SUM(current_balance),0) FROM treasury_accounts WHERE is_active=1").fetchone()[0]
        for r in rows:
            d = r['due_date']
            if not d: k = 'NO_DUE'
            elif d < today: k = 'OVERDUE'
            else:
                dd = (date.fromisoformat(d) - t0).days
                k = 'TODAY' if dd == 0 else 'W1' if dd <= 7 else 'W2' if dd <= 15 else 'M1' if dd <= 30 else 'LATER'
            amt = int(r['amount'] or 0)
            idx = 0 if r['direction'] == 'RECEIVABLE' else 1
            buckets[k][idx] += amt
            self.details.append({'d': d, 'dir': r['direction'], 'person': r['person'], 'check': r['check_no'], 'amt': amt})
        self.details.sort(key=lambda x: x['d'] or '9999')

        tot_in = sum(b[0] for b in buckets.values()); tot_out = sum(b[1] for b in buckets.values())
        self.v_cur.setText(f"{int(cur):,} ریال")
        self.v_in.setText(f"{tot_in:,} ریال")
        self.v_out.setText(f"{tot_out:,} ریال")
        net = int(cur) + tot_in - tot_out
        self.v_net.setText(f"{net:,} ریال")

        self.sum_tbl.setRowCount(len(BUCKETS))
        for i, (k, name) in enumerate(BUCKETS):
            bi, bo = buckets[k]
            vals = [name, f"{bi:,}", f"{bo:,}", f"{bi-bo:+,}"]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.sum_tbl.setItem(i, c, it)

        self.det_tbl.setRowCount(len(self.details))
        for i, r in enumerate(self.details):
            j = jalali_date_display_from_iso(r['d']) if r['d'] else '-'
            vals = [j, r['d'] or '-', 'ورود' if r['dir'] == 'RECEIVABLE' else 'خروج', r['person'], r['check'] or '-', f"{r['amt']:,}"]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.det_tbl.setItem(i, c, it)

    def _pdf(self):
        rows_html = ''
        for r in self.details:
            j = jalali_date_display_from_iso(r['d']) if r['d'] else '-'
            rows_html += f"<tr><td>{j}</td><td>{r['d'] or '-'}</td><td>{'ورود' if r['dir']=='RECEIVABLE' else 'خروج'}</td><td>{r['person']}</td><td>{r['check'] or '-'}</td><td>{r['amt']:,}</td></tr>"
        html = f"""<html dir='rtl'><head><meta charset='utf-8'><style>
            body{{font-family:Tahoma;padding:20px;}} h2{{text-align:center;}}
            table{{width:100%;border-collapse:collapse;}} th,td{{border:1px solid #999;padding:8px;font-size:12px;text-align:center;}} th{{background:#eee;}}
            .print-btn{{position:fixed;top:20px;left:20px;padding:10px 20px;background:#9333ea;color:#fff;border:none;border-radius:6px;cursor:pointer;}}</style></head><body>
            <button class='print-btn' onclick='window.print()'>چاپ / ذخیره PDF</button>
            <h2>پیش‌بینی جریان نقدینگی</h2>
            <p>مانده فعلی: {self.v_cur.text()} | وصولی پیش‌رو: {self.v_in.text()} | پرداخت پیش‌رو: {self.v_out.text()} | خالص: {self.v_net.text()}</p>
            <table><tr><th>شمسی</th><th>میلادی</th><th>جهت</th><th>طرف حساب</th><th>چک</th><th>مبلغ</th></tr>{rows_html}</table></body></html>"""
        import tempfile, webbrowser
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html); t = f.name
        webbrowser.open('file:///' + t)

    def _xls(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره اکسل', 'cashflow.csv', 'CSV (*.csv)')
        if not path: return
        if not path.lower().endswith('.csv'): path += '.csv'
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            f.write('شمسی,میلادی,جهت,طرف حساب,شماره چک,مبلغ\n')
            for r in self.details:
                j = jalali_date_display_from_iso(r['d']) if r['d'] else '-'
                f.write(f"{j},{r['d'] or '-'},{'ورود' if r['dir']=='RECEIVABLE' else 'خروج'},{r['person']},{r['check'] or '-'},{r['amt']}\n")
