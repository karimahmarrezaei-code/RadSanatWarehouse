# -*- coding: utf-8 -*-
# گزارش ترکیبی مالی-عملیاتی (VIEW سریع)
import csv
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QComboBox, QDateEdit, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QAbstractItemView, QGroupBox, QTabWidget, QFileDialog)
from app.core.jalali import jalali_date_display_from_iso

class CombinedReportWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._ids = []
        self.setWindowTitle('گزارش ترکیبی مالی-عملیاتی')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1350, 780)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.showMaximized()
        self._build_ui()
        self._load_persons()
        self._run()

    def _build_ui(self):
        root = QVBoxLayout(self)
        fg = QGroupBox('فیلترها')
        gl = QGridLayout(fg)
        self.role_combo = QComboBox(); self.role_combo.addItems(['هر دو نقش', 'مشتری', 'راننده'])
        self.person_combo = QComboBox(); self.person_combo.setMinimumWidth(220)
        self.date_from = QDateEdit(QDate.currentDate().addDays(-60)); self.date_from.setCalendarPopup(True); self.date_from.setDisplayFormat('yyyy-MM-dd')
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True); self.date_to.setDisplayFormat('yyyy-MM-dd')
        self.status_combo = QComboBox(); self.status_combo.addItems(['همه وضعیت‌ها', 'تایید', 'ابطال'])
        self.fin_combo = QComboBox(); self.fin_combo.addItems(['همه مالی', 'پرداخت‌نشده', 'پرداخت جزئی', 'پرداخت کامل'])
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText('جستجو در شماره حواله / مرجع...')
        go = QPushButton('محاسبه'); go.setObjectName('PrimaryButton'); go.clicked.connect(self._run)
        xls = QPushButton('اکسل'); xls.setObjectName('SecondaryButton'); xls.clicked.connect(self._xls)
        gl.addWidget(QLabel('نقش:'), 0, 0); gl.addWidget(self.role_combo, 0, 1)
        gl.addWidget(QLabel('شخص:'), 0, 2); gl.addWidget(self.person_combo, 0, 3, 1, 3)
        gl.addWidget(QLabel('از:'), 0, 4); gl.addWidget(self.date_from, 0, 5)
        gl.addWidget(QLabel('تا:'), 0, 6); gl.addWidget(self.date_to, 0, 7)
        gl.addWidget(QLabel('وضعیت:'), 1, 0); gl.addWidget(self.status_combo, 1, 1)
        gl.addWidget(QLabel('مالی:'), 1, 2); gl.addWidget(self.fin_combo, 1, 3)
        gl.addWidget(QLabel('جستجو:'), 1, 4); gl.addWidget(self.search_edit, 1, 5)
        gl.addWidget(xls, 1, 6); gl.addWidget(go, 1, 7)
        root.addWidget(fg)

        cards = QGridLayout()
        self.c_count = QLabel('0'); self.c_amount = QLabel('0')
        self.c_paid = QLabel('0'); self.c_balance = QLabel('0')
        self.c_delivered = QLabel('0'); self.c_remaining = QLabel('0')
        cfg = [('تعداد حواله', self.c_count, '#2563eb'), ('جمع مبلغ', self.c_amount, '#059669'),
               ('جمع پرداختی/دریافتی', self.c_paid, '#7c3aed'), ('مانده حساب', self.c_balance, '#dc2626'),
               ('جمع تحویل', self.c_delivered, '#f59e0b'), ('مانده بار', self.c_remaining, '#0891b2')]
        for i, (t, v, c) in enumerate(cfg):
            tl = QLabel(t); tl.setStyleSheet('color: #94a3b8; font-size: 11px;')
            v.setStyleSheet('color:%s;font-size:16px;font-weight:bold;' % c)
            cards.addWidget(tl, 0, i); cards.addWidget(v, 1, i)
        root.addLayout(cards)

        self.tabs = QTabWidget()
        self.tbl = QTableWidget(0, 14)
        self.tbl.setHorizontalHeaderLabels(['مرجع','شماره حواله','تاریخ','مشتری','راننده','مرحله',
            'مبلغ (ریال)','پرداختی','مانده','روش','آخرین پرداخت','تحویل','مانده بار','وضعیت'])
        for t_ in (self.tbl,): t_.setSelectionBehavior(QAbstractItemView.SelectRows); t_.setEditTriggers(QAbstractItemView.NoEditTriggers); t_.verticalHeader().setVisible(False); t_.setAlternatingRowColors(True)
        self.tbl.itemDoubleClicked.connect(self._show_detail)

        self.tbl_ref = QTableWidget(0, 8)
        self.tbl_ref.setHorizontalHeaderLabels(['مرجع','مشتری','تعداد حواله','جمع مبلغ','پرداختی','مانده','تحویل','مانده بار'])
        self.tbl_ref.setSelectionBehavior(QAbstractItemView.SelectRows); self.tbl_ref.setEditTriggers(QAbstractItemView.NoEditTriggers); self.tbl_ref.verticalHeader().setVisible(False); self.tbl_ref.setAlternatingRowColors(True)

        self.tbl_pal = QTableWidget(0, 4)
        self.tbl_pal.setHorizontalHeaderLabels(['کد پالت','نام پالت','جمع تعداد','جمع مبلغ'])
        self.tbl_pal.setSelectionBehavior(QAbstractItemView.SelectRows); self.tbl_pal.setEditTriggers(QAbstractItemView.NoEditTriggers); self.tbl_pal.verticalHeader().setVisible(False); self.tbl_pal.setAlternatingRowColors(True)

        self.tbl_pay = QTableWidget(0, 8)
        self.tbl_pay.setHorizontalHeaderLabels(['مرجع','شماره حواله','تاریخ','مشتری','تاریخ پرداخت','مبلغ','روش','وضعیت'])
        self.tbl_pay.setSelectionBehavior(QAbstractItemView.SelectRows); self.tbl_pay.setEditTriggers(QAbstractItemView.NoEditTriggers); self.tbl_pay.verticalHeader().setVisible(False); self.tbl_pay.setAlternatingRowColors(True)

        self.tbl_per = QTableWidget(0, 5)
        self.tbl_per.setHorizontalHeaderLabels(['شخص','جمع حواله‌ها','جمع پرداختی/دریافتی','مانده حساب','تعداد حواله'])
        self.tbl_per.setSelectionBehavior(QAbstractItemView.SelectRows); self.tbl_per.setEditTriggers(QAbstractItemView.NoEditTriggers); self.tbl_per.verticalHeader().setVisible(False); self.tbl_per.setAlternatingRowColors(True)

        self.tabs.addTab(self.tbl, 'جزئیات حواله‌ها')
        self.tabs.addTab(self.tbl_ref, 'خلاصه مرجع')
        self.tabs.addTab(self.tbl_pal, 'خلاصه پالت')
        self.tabs.addTab(self.tbl_pay, 'ریز پرداخت‌ها/دریافت‌ها')
        self.tabs.addTab(self.tbl_per, 'مانده حساب اشخاص')
        root.addWidget(self.tabs, 1)

        hint = QLabel('دابل‌کلیک روی ردیف حواله → نمایش اقلام پالت | ستون «مانده» = مبلغ حواله − پرداختی')
        hint.setStyleSheet('color:#64748b;font-size:11px;')
        root.addWidget(hint)

    def _load_persons(self):
        self.person_combo.clear(); self.person_combo.addItem('همه اشخاص', None)
        try:
            with self.db.connect() as conn:
                rows = conn.execute("SELECT id, first_name||' '||last_name FROM persons WHERE is_active=1 ORDER BY first_name").fetchall()
            for r in rows: self.person_combo.addItem(r[1] or '-', r[0])
        except Exception: pass

    def _person_cond(self, ac, ad):
        pid = self.person_combo.currentData()
        if not pid: return '', []
        r = self.role_combo.currentIndex()
        if r == 1: return ' AND %s=?' % ac, [pid]
        if r == 2: return ' AND %s=?' % ad, [pid]
        return ' AND (%s=? OR %s=?)' % (ac, ad), [pid, pid]

    def _filters(self):
        d0 = self.date_from.date().toString('yyyy-MM-dd'); d1 = self.date_to.date().toString('yyyy-MM-dd')
        st = self.status_combo.currentIndex()
        stc = ''
        if st == 1: stc = " AND issue_status='CONFIRMED'"
        elif st == 2: stc = " AND issue_status='CANCELLED'"
        fin = self.fin_combo.currentIndex()
        fc = ''
        if fin == 1: fc = ' AND paid_amount=0 AND amount>0'
        elif fin == 2: fc = ' AND paid_amount>0 AND paid_amount<amount'
        elif fin == 3: fc = ' AND paid_amount>=amount AND amount>0'
        s = self.search_edit.text().strip()
        sc = ''; sp = []
        if s:
            sc = ' AND (issue_no LIKE ? OR reference_no LIKE ?)'; sp = ['%'+s+'%', '%'+s+'%']
        return d0, d1, stc, fc, sc, sp

    def _run(self):
        d0, d1, stc, fc, sc, sp = self._filters()
        pc, pp = self._person_cond('customer_id', 'driver_id')
        base = ' FROM v_combined_issues WHERE issue_date BETWEEN ? AND ?' + pc + stc + fc + sc
        params = [d0, d1] + pp + sp
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute('SELECT issue_id, reference_no, issue_no, issue_date, stage_count, amount, paid_amount, payment_method, last_payment_date, delivered_qty, remaining_qty, issue_status, customer_name, driver_name' + base + ' ORDER BY reference_no, issue_no', params).fetchall()
            rows2 = conn.execute('SELECT reference_no, MAX(customer_name), COUNT(*), SUM(amount), SUM(paid_amount), MAX(remaining_qty), SUM(delivered_qty)' + base + ' GROUP BY reference_no ORDER BY reference_no', params).fetchall()
            rows4 = conn.execute('SELECT reference_no, issue_no, issue_date, customer_name, payment_date, amount, method_name, pay_status FROM v_issue_payments WHERE issue_date BETWEEN ? AND ?' + pc.replace('customer_id','customer_id').replace('driver_id','driver_id') + stc.replace('issue_status','issue_status') + ' AND pay_id IS NOT NULL ORDER BY payment_date DESC, issue_no', [d0, d1] + pp).fetchall()
            rows5 = conn.execute('SELECT customer_name, SUM(amount), SUM(paid_amount), COUNT(*)' + base + ' GROUP BY customer_id, customer_name ORDER BY SUM(amount)-SUM(paid_amount) DESC', params).fetchall()
        pc3, pp3 = self._person_cond('wi.customer_id', 'ol.driver_id')
        q3 = ('SELECT p.code, p.name, SUM(wii.qty), SUM(wii.total_price) FROM warehouse_issue_items wii '
              'JOIN warehouse_issues wi ON wi.id=wii.issue_id LEFT JOIN outbound_loads ol ON ol.id=wi.outbound_load_id '
              'JOIN pallets p ON p.id=wii.pallet_id '
              "WHERE COALESCE(wi.issue_status,'CONFIRMED')<>'CANCELLED' AND wi.issue_date BETWEEN ? AND ?" + pc3 + stc.replace('issue_status','wi.issue_status') + ' GROUP BY p.id, p.code, p.name ORDER BY p.code')
        with self.db.connect() as conn:
            conn.row_factory = None
            rows3 = conn.execute(q3, [d0, d1] + pp3).fetchall()
        self._ids = [r[0] for r in rows]
        st_map = {'CONFIRMED': 'تایید', 'CANCELLED': 'ابطال'}
        pm_map = {'CHECK': 'چک', 'CASH': 'نقد', 'TRANSFER': 'کارت‌به‌کارت', 'CREDIT': 'اعتباری'}
        ps_map = {'PAID': 'پرداخت‌شده', 'PENDING': 'در انتظار', 'PARTIAL': 'جزئی'}

        # تب ۱: جزئیات
        self.tbl.setRowCount(len(rows))
        ta = tp = tb = td = tr = 0
        for i, r in enumerate(rows):
            amt = int(r[5] or 0); paid = int(r[6] or 0); bal = amt - paid
            ta += amt; tp += paid; tb += bal; td += int(r[9] or 0); tr += int(r[10] or 0)
            pm = pm_map.get(r[7], r[7]) if r[7] and r[7] != '-' else '-'
            ld = jalali_date_display_from_iso(r[8]) if r[8] else '-'
            vals = [r[1], r[2], jalali_date_display_from_iso(r[3]) if r[3] else '-', r[12], r[13], str(r[4] or 0),
                    '{:,}'.format(amt), '{:,}'.format(paid), '{:,}'.format(bal), pm, ld,
                    '{:,}'.format(int(r[9] or 0)), '{:,}'.format(int(r[10] or 0)), st_map.get(r[11], r[11])]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c == 8 and bal > 0:
                    it.setForeground(Qt.red)
                self.tbl.setItem(i, c, it)

        # تب ۲: خلاصه مرجع
        self.tbl_ref.setRowCount(len(rows2))
        for i, r in enumerate(rows2):
            amt = int(r[3] or 0); paid = int(r[4] or 0); bal = amt - paid
            vals = [r[0], r[1], str(r[2] or 0), '{:,}'.format(amt), '{:,}'.format(paid), '{:,}'.format(bal),
                    '{:,}'.format(int(r[6] or 0)), '{:,}'.format(int(r[5] or 0))]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c == 5 and bal > 0: it.setForeground(Qt.red)
                self.tbl_ref.setItem(i, c, it)

        # تب ۳: خلاصه پالت
        self.tbl_pal.setRowCount(len(rows3))
        for i, r in enumerate(rows3):
            vals = [r[0], r[1], '{:,}'.format(int(r[2] or 0)), '{:,}'.format(int(r[3] or 0))]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_pal.setItem(i, c, it)

        # تب ۴: ریز پرداخت‌ها
        self.tbl_pay.setRowCount(len(rows4))
        for i, r in enumerate(rows4):
            vals = [r[0], r[1], jalali_date_display_from_iso(r[2]) if r[2] else '-', r[3],
                    jalali_date_display_from_iso(r[4]) if r[4] else '-', '{:,}'.format(int(r[5] or 0)),
                    pm_map.get(r[6], r[6]) if r[6] else '-', ps_map.get(r[7], r[7])]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_pay.setItem(i, c, it)

        # تب ۵: مانده حساب اشخاص
        self.tbl_per.setRowCount(len(rows5))
        for i, r in enumerate(rows5):
            amt = int(r[1] or 0); paid = int(r[2] or 0); bal = amt - paid
            vals = [r[0], '{:,}'.format(amt), '{:,}'.format(paid), '{:,}'.format(bal), str(r[3] or 0)]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c == 3 and bal > 0: it.setForeground(Qt.red)
                self.tbl_per.setItem(i, c, it)

        self.c_count.setText(str(len(rows)))
        self.c_amount.setText('{:,}'.format(ta))
        self.c_paid.setText('{:,}'.format(tp))
        self.c_balance.setText('{:,}'.format(tb))
        self.c_delivered.setText('{:,}'.format(td))
        self.c_remaining.setText('{:,}'.format(tr))

    def _show_detail(self, item):
        row = item.row()
        if row >= len(self._ids): return
        issue_id = self._ids[row]
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                items = conn.execute('SELECT wii.row_no, p.code, p.name, wii.qty, wii.unit_price, wii.total_price FROM warehouse_issue_items wii JOIN pallets p ON p.id=wii.pallet_id WHERE wii.issue_id=? ORDER BY wii.row_no', (issue_id,)).fetchall()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e)); return
        dlg = QDialog(self); dlg.setWindowTitle('اقلام حواله'); dlg.resize(700, 420); dlg.setLayoutDirection(Qt.RightToLeft)
        from PyQt5.QtWidgets import QVBoxLayout as V2, QPushButton as B2
        ly = V2(dlg)
        tb = QTableWidget(0, 6); tb.setHorizontalHeaderLabels(['ردیف','کد پالت','نام پالت','تعداد','قیمت واحد','مبلغ کل'])
        tb.verticalHeader().setVisible(False); tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tb.setRowCount(len(items))
        for i, r in enumerate(items):
            vals = [str(r[0]), r[1], r[2], '{:,}'.format(int(r[3] or 0)), '{:,}'.format(int(r[4] or 0)), '{:,}'.format(int(r[5] or 0))]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter); tb.setItem(i, c, it)
        tb.resizeColumnsToContents(); ly.addWidget(tb)
        cb = B2('بستن'); cb.clicked.connect(dlg.accept); ly.addWidget(cb)
        dlg.exec_()

    def _xls(self):
        path, _ = QFileDialog.getSaveFileName(self, 'خروجی اکسل', 'combined-report.csv', 'CSV (*.csv)')
        if not path: return
        if not path.lower().endswith('.csv'): path += '.csv'
        try:
            with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                w = csv.writer(f)
                for title, tbl in [('جزئیات حواله‌ها', self.tbl), ('خلاصه به تفکیک مرجع', self.tbl_ref),
                                   ('خلاصه به تفکیک پالت', self.tbl_pal), ('ریز پرداخت‌ها/دریافت‌ها', self.tbl_pay),
                                   ('مانده حساب اشخاص', self.tbl_per)]:
                    w.writerow(['== ' + title + ' =='])
                    w.writerow([tbl.horizontalHeaderItem(c).text() for c in range(tbl.columnCount())])
                    for r in range(tbl.rowCount()):
                        w.writerow([(tbl.item(r, c).text() if tbl.item(r, c) else '') for c in range(tbl.columnCount())])
                    w.writerow([])
            QMessageBox.information(self, 'اکسل', 'خروجی ذخیره شد: ' + path)
        except PermissionError:
            QMessageBox.warning(self, 'خطا', 'فایل در Excel باز است؛ آن را ببندید.')
        except Exception as e:
            QMessageBox.warning(self, 'خطا', str(e))
