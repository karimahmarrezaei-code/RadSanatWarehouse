# -*- coding: utf-8 -*-
"""Issue Report Window - گزارش خروج کالا (حواله‌ها)"""

import os
import sys
import tempfile
import sqlite3
from datetime import date

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFileDialog,
QMessageBox, QTabWidget, QTextBrowser, QComboBox, QWidget, QInputDialog,
    QFrame, QHeaderView, QAbstractItemView, QDateEdit
)

from app.core.jalali import today_iso_date, jalali_date_display_from_iso

STATUS_FA = {
    'CONFIRMED': 'تایید شده',
    'OPEN': 'باز',
    'PARTIAL': 'جزئی',
    'COMPLETED': 'تکمیل شده',
    'CANCELLED': 'لغو شده'
}


class IssueReportWindow(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('گزارش خروج کالا (حواله‌ها)')
        self.resize(1180, 750)
        self.setLayoutDirection(Qt.RightToLeft)

        self._ids = []
        self._refs = []
        self._loads = []
        self._custs = []

        self._build()
        self._load_persons()
        self._load_issues()
        self.refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        # --- نوار ابزار ---
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

        bar.addWidget(QLabel('شماره حواله:'))
        self.issue_combo = QComboBox()
        self.issue_combo.setMinimumWidth(250)
        self.issue_combo.currentIndexChanged.connect(self._on_issue_combo_changed)
        bar.addWidget(self.issue_combo)

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

        ref_btn = QPushButton('📋 گزارش مرجع خروج')
        ref_btn.setObjectName('PrimaryButton')
        ref_btn.clicked.connect(self._report_by_reference)
        bar.addWidget(ref_btn)

        issue_btn = QPushButton('📄 گزارش حواله مرحله')
        issue_btn.setObjectName('SecondaryButton')
        issue_btn.clicked.connect(self._report_by_issue)
        bar.addWidget(issue_btn)

        root.addWidget(toolbar_frame)

        # --- تب‌ها ---
        self.tabs = QTabWidget()

        # تب ۱: گزارش
        w1 = QWidget()
        l1 = QVBoxLayout(w1)
        l1.setSpacing(10)

        self.tbl = QTableWidget(0, 11)
        self.tbl.setHorizontalHeaderLabels([
            'شماره حواله', 'شماره مرجع', 'مرحله', 'تاریخ', 'مشتری',
            'راننده', 'بارنامه', 'تعداد پالت', 'تعداد بار این حواله', 'مبلغ کل', 'وضعیت'
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

        l1.addWidget(QLabel('📦 اقلام حواله انتخاب‌شده:'))

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
        first_day_of_month = date.fromisoformat(today_iso_date()).replace(day=1)
        self.from_edit.setDate(QDate.fromString(first_day_of_month.isoformat(), 'yyyy-MM-dd'))
        self.to_edit.setDate(QDate.fromString(today_iso_date(), 'yyyy-MM-dd'))

        self._update_from_jalali()
        self._update_to_jalali()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _load_persons(self):
        with self.db.connect() as conn:
            conn.row_factory = sqlite3.Row
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT DISTINCT p.id, (p.first_name||' '||p.last_name) n "
                    "FROM persons p JOIN warehouse_issues wi ON wi.customer_id=p.id "
                    "ORDER BY p.id"
                ).fetchall()
            except Exception:
                rows = conn.execute(
                    "SELECT id, (first_name||' '||last_name) n FROM persons ORDER BY id"
                ).fetchall()

        self.person_combo.clear()
        self.person_combo.addItem('همه مشتریان', None)
        for r in rows:
            self.person_combo.addItem((r['n'] or str(r['id'])), r['id'])

    def _load_issues(self):
        """لود لیست حواله‌ها برای کامبو باکس"""
        with self.db.connect() as conn:
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT wi.id, wi.issue_no, ol.reference_no, "
                    "       COALESCE(p.first_name||' '||p.last_name, '-') as cust, "
                    "       wi.issue_date "
                    "FROM warehouse_issues wi "
                    "LEFT JOIN outbound_loads ol ON ol.id = wi.outbound_load_id "
                    "LEFT JOIN persons p ON p.id = wi.customer_id "
                    "WHERE 1=1 "
                    "ORDER BY wi.id DESC"
                ).fetchall()
            except Exception:
                rows = []

        self.issue_combo.blockSignals(True)
        self.issue_combo.clear()
        self.issue_combo.addItem('همه حواله‌ها', None)
        for r in rows:
            issue_no = r['issue_no'] or '-'
            ref_no = r['reference_no'] or '-'
            cust = r['cust'] or '-'
            label = f"{issue_no} | {ref_no} | {cust}"
            self.issue_combo.addItem(label, r['id'])
        self.issue_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Combo events
    # ------------------------------------------------------------------
    def _on_issue_combo_changed(self):
        selected_issue_id = self.issue_combo.currentData()
        if selected_issue_id is not None:
            self._filter_by_issue_id(selected_issue_id)
        else:
            self.refresh()

    def _filter_by_issue_id(self, issue_id: int):
        with self.db.connect() as conn:
            conn.row_factory = sqlite3.Row
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT wi.*, ol.reference_no AS ref, ol.total_load_qty AS tlq, "
                    "       d.first_name||' '||d.last_name AS drv, "
                    "       COALESCE(p.first_name||' '||p.last_name,'-') AS cust, "
                    "       COALESCE(SUM(ii.qty),0) AS q, COALESCE(SUM(ii.qty*ii.unit_price),0) AS amt "
                    "FROM warehouse_issues wi "
                    "LEFT JOIN outbound_loads ol ON ol.id=wi.outbound_load_id "
                    "LEFT JOIN persons p ON p.id=wi.customer_id "
                    "LEFT JOIN persons d ON d.id=wi.driver_id "
                    "LEFT JOIN warehouse_issue_items ii ON ii.issue_id=wi.id "
                    "WHERE wi.id = ? "
                    "GROUP BY wi.id",
                    (issue_id,)
                ).fetchall()
            except Exception as e:
                QMessageBox.critical(self, 'خطا', str(e))
                rows = []

        self._fill_table(rows, use_dict=True)


    def _filter_by_load_id(self, load_id: int):
        with self.db.connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT wi.*, ol.reference_no AS ref, ol.total_load_qty AS tlq, "
                "       d.first_name||' '||d.last_name AS drv, "
                "       COALESCE(p.first_name||' '||p.last_name,'-') AS cust, "
                "       COALESCE(SUM(ii.qty),0) AS q, COALESCE(SUM(ii.qty*ii.unit_price),0) AS amt "
                "FROM warehouse_issues wi "
                "LEFT JOIN outbound_loads ol ON ol.id=wi.outbound_load_id "
                "LEFT JOIN persons p ON p.id=wi.customer_id "
                "LEFT JOIN persons d ON d.id=wi.driver_id "
                "LEFT JOIN warehouse_issue_items ii ON ii.issue_id=wi.id "
                "WHERE wi.outbound_load_id = ? AND wi.issue_status != 'CANCELLED' "
                "GROUP BY wi.id ORDER BY wi.stage_no",
                (load_id,)
            ).fetchall()
        self.tbl.setRowCount(len(rows))
        self._ids, self._refs, self._loads, self._custs = [], [], [], []
        for i, r in enumerate(rows):
            self._ids.append(r['id'])
            self._refs.append(r['ref'] or '')
            self._loads.append(r['outbound_load_id'])
            self._custs.append(r['cust'] or '-')
            vals = [r['issue_no'] or '', r['ref'] or '', str(r['stage_no'] or 1),
                    jalali_date_display_from_iso(r['issue_date']) if r['issue_date'] else '-',
                    r['cust'], r['drv'] or '-', r['waybill_no'] or '',
                    f"{int(r['q'] or 0):,}", f"{int(r['tlq'] or 0):,}",
                    f"{int(r['amt'] or 0):,}", STATUS_FA.get(r['issue_status'], r['issue_status'] or '')]
            for cc, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl.setItem(i, cc, it)
        if self.tbl.rowCount():
            self._on_select(0, 0, -1, -1)

    def refresh(self):
        f = self.from_edit.date().toString('yyyy-MM-dd')
        t = self.to_edit.date().toString('yyyy-MM-dd')
        c = self.person_combo.currentData()

        q = ("SELECT wi.id, wi.issue_no, wi.stage_no, wi.issue_date, wi.waybill_no, wi.issue_status, "
             "       wi.stage_load_qty, wi.delivered_qty, "
             "       ol.reference_no AS ref, ol.total_load_qty AS tlq, ol.id AS load_id, "
             "       COALESCE(d.first_name||' '||d.last_name, '-') AS drv, "
             "       COALESCE(p.first_name||' '||p.last_name, '-') AS cust, "
             "       COALESCE(SUM(ii.qty),0) AS q, COALESCE(SUM(ii.qty*ii.unit_price),0) AS amt "
             "FROM warehouse_issues wi "
             "LEFT JOIN outbound_loads ol ON ol.id=wi.outbound_load_id "
             "LEFT JOIN persons p ON p.id=wi.customer_id "
             "LEFT JOIN persons d ON d.id=wi.driver_id "
             "LEFT JOIN warehouse_issue_items ii ON ii.issue_id=wi.id "
             "WHERE 1=1")

        conds, params = [], []
        if f:
            conds.append("wi.issue_date >= ?"); params.append(f)
        if t:
            conds.append("wi.issue_date <= ?"); params.append(t)
        if c is not None:
            conds.append("wi.customer_id = ?"); params.append(c)
        if conds:
            q += " AND " + " AND ".join(conds)
        q += " GROUP BY wi.id ORDER BY wi.issue_date DESC, wi.id DESC"

        with self.db.connect() as conn:
            conn.row_factory = None
            try:
                rows = conn.execute(q, params).fetchall()
            except Exception as e:
                QMessageBox.critical(self, 'خطا', str(e))
                rows = []

        self.tbl.setRowCount(len(rows))
        self._ids, self._refs, self._loads, self._custs = [], [], [], []

        for i, r in enumerate(rows):
            self._ids.append(r[0])
            self._refs.append(r[8] or '')
            self._loads.append(r[10])
            self._custs.append(r[12] or '-')

            status = r[5] or ''
            vals = [
                r[1] or '', r[8] or '', str(r[2] or 1),
                jalali_date_display_from_iso(r[3]) if r[3] else '-',
                r[12] or '-', r[11] or '-', r[4] or '-',
                f"{int(r[13] or 0):,}", f"{int(r[6] or 0):,}", f"{int(r[14] or 0):,}",
                STATUS_FA.get(status, status)
            ]

            # ✅ رنگ‌بندی بر اساس وضعیت
            if status == 'CANCELLED':
                bg = QBrush(QColor(254, 226, 226))   # قرمز کم‌رنگ
                fg = QBrush(QColor(153, 27, 27))      # متن قرمز تیره
            elif status == 'PARTIAL':
                bg = QBrush(QColor(254, 240, 199))   # زرد کم‌رنگ
                fg = None
            elif status == 'COMPLETED':
                bg = QBrush(QColor(220, 252, 231))   # سبز کم‌رنگ
                fg = None
            else:
                bg, fg = None, None

            for cc, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if bg:
                    it.setBackground(bg)
                if fg:
                    it.setForeground(fg)
                self.tbl.setItem(i, cc, it)

        if self.tbl.rowCount():
            self._on_select(0, 0, -1, -1)
    def _fill_table(self, rows, use_dict=False):
        if use_dict:
            rows = [r if isinstance(r, dict) else dict(r) for r in rows]
        if use_dict:
            rows = [r if isinstance(r, dict) else dict(r) for r in rows]
        """پر کردن جدول اصلی از نتایج کوئری"""
        self.tbl.setRowCount(len(rows))
        self._ids = []
        self._refs = []
        self._loads = []
        self._custs = []

        for i, r in enumerate(rows):
            if use_dict:
                rid = r['id']
                issue_no = r['issue_no'] or ''
                ref = r['ref'] or ''
                stage = r['stage_no'] or 1
                idate = r['issue_date']
                cust = r['cust'] or '-'
                drv = r['drv'] or '-'
                waybill = r['waybill_no'] or ''
                qty = int(r['q'] or 0)
                tlq = int(r['tlq'] or 0)
                amt = int(r['amt'] or 0)
                status = r['issue_status'] or ''
                load_id = r['outbound_load_id']
                stage_load = int(r.get('stage_load_qty') or r.get('stage_load_qty', 0) or 0)
            else:
                rid = r[0]
                issue_no = r[1] or ''
                ref = r[8] or ''
                stage = r[2] or 1
                idate = r[3]
                cust = r[12] or '-'
                drv = r[11] or '-'
                waybill = r[4] or ''
                qty = int(r[13] or 0)
                tlq = int(r[9] or 0)
                amt = int(r[14] or 0)
                status = r[5] or ''
                load_id = r[10]
                stage_load = int(r[6] or 0)

            self._ids.append(rid)
            self._refs.append(ref)
            self._loads.append(load_id)
            self._custs.append(cust)

            vals = [
                issue_no, ref, str(stage),
                jalali_date_display_from_iso(idate) if idate else '-',
                cust, drv, waybill,
                f"{qty:,}", f"{stage_load:,}", f"{amt:,}",
                STATUS_FA.get(status, status)
            ]

            for cc, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl.setItem(i, cc, it)

        if self.tbl.rowCount():
            self._on_select(0, 0, -1, -1)

    # ------------------------------------------------------------------
    # Selection / Items
    # ------------------------------------------------------------------
    def _on_select(self, row, col, pr, pc):
        if row < 0 or row >= len(self._ids):
            self.itbl.setRowCount(0)
            return

        with self.db.connect() as conn:
            conn.row_factory = sqlite3.Row
            items = conn.execute(
                "SELECT p.code, p.name, ii.qty, ii.unit_price "
                "FROM warehouse_issue_items ii "
                "JOIN pallets p ON p.id=ii.pallet_id "
                "WHERE ii.issue_id=? ORDER BY ii.id",
                (self._ids[row],)
            ).fetchall()

        self.itbl.setRowCount(len(items))
        for i, r in enumerate(items):
            vals = [
                r['code'], r['name'],
                f"{int(r['qty'] or 0):,}",
                f"{int(r['unit_price'] or 0):,}",
                f"{int((r['qty'] or 0) * (r['unit_price'] or 0)):,}"
            ]
            for cc, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.itbl.setItem(i, cc, it)

        self.browser.setHtml(self._preview_html(row))

    # ------------------------------------------------------------------
    # Preview HTML
    # ------------------------------------------------------------------
    def _preview_html(self, row):
        try:
            from app.core.letterhead import render_letterhead_html, get_company_profile
            lh = render_letterhead_html(get_company_profile(self.db))
        except Exception:
            lh = ''

        with self.db.connect() as conn:
            conn.row_factory = None
            stages = conn.execute(
                "SELECT id, issue_no, stage_no, issue_date, stage_load_qty, delivered_qty, issue_status "
                "FROM warehouse_issues WHERE outbound_load_id=? AND issue_status != 'CANCELLED' "
                "ORDER BY stage_no",
                (self._loads[row],)
            ).fetchall()

            parts = []
            tq = 0
            ta = 0

            for s in stages:
                # s[0]=id, s[1]=issue_no, s[2]=stage_no, s[3]=issue_date,
                # s[4]=stage_load_qty, s[5]=delivered_qty, s[6]=issue_status
                status = s[6] if len(s) > 6 else 'CONFIRMED'

                its = conn.execute(
                    "SELECT p.code, p.name, ii.qty, ii.unit_price "
                    "FROM warehouse_issue_items ii "
                    "JOIN pallets p ON p.id=ii.pallet_id "
                    "WHERE ii.issue_id=? ORDER BY ii.id",
                    (s[0],)
                ).fetchall()

                if status == 'CANCELLED':
                    row_style = "background:#fee2e2; color:#991b1b;"
                elif status == 'PARTIAL':
                    row_style = " color:#92400e;"
                else:
                    row_style = "background:#f1f1f1;"

                trs = ''.join(
                    f"<tr style='{row_style}'>"
                    f"<td>{r[0]}</td><td>{r[1]}</td><td>{int(r[2] or 0):,}</td>"
                    f"<td>{int(r[3] or 0):,}</td><td>{int((r[2] or 0) * (r[3] or 0)):,}</td>"
                    f"</tr>"
                    for r in its
                )

                tq += sum(int(r[2] or 0) for r in its)
                ta += sum(int((r[2] or 0) * (r[3] or 0)) for r in its)

                stage_qty = int(s[4] or 0)
                delivered = int(s[5] or 0)
                rem = stage_qty - delivered

                status_text = STATUS_FA.get(status, status)
                status_color = (
                    '#dc2626' if status == 'CANCELLED'
                    else ('#d97706' if status == 'PARTIAL' else '#059669')
                )

                parts.append(
                    f"<h3 style='border-right: 4px solid {status_color}; padding-right: 10px;'>"
                    f"حواله {s[1]} — مرحله {s[2]} — {jalali_date_display_from_iso(s[3])} "
                    f"<span style='color:{status_color}; font-size: 14px;'>[{status_text}]</span></h3>"
                    f"<p>تعداد این مرحله: {stage_qty:,} — تحویل‌شده: {delivered:,} — "
                    f"<b style='color:#059669;'>باقیمانده: {rem:,}</b></p>"
                    f"<table border=1 cellspacing=0 cellpadding=6 "
                    f"style='border-collapse: collapse; width:100%; text-align:right; margin-bottom: 20px;'>"
                    f"<tr style='background:#1e293b; color:white;'>"
                    f"<th>کد پالت</th><th>نام پالت</th><th>تعداد</th><th>قیمت واحد</th><th>مبلغ کل</th>"
                    f"</tr>{trs}</table>"
                )

        summ = (
            f"<p style='color:#d00000;font-weight:bold;font-size:16px;"
            f"border-top:2px solid #d00000;padding-top:8px'>"
            f"جمع کل: تعداد پالت {tq:,} — مبلغ کل {ta:,} ریال</p>"
        )

        return (
            f"<html dir=rtl><body style='background:#ffffff;color:#111;padding:20px;"
            f"font-family: Tahoma, sans-serif'>"
            f"{lh}"
            f"<h2>گزارش خروج کالا — مرجع {self._refs[row] or '-'} — مشتری: {self._custs[row]}</h2>"
            f"{''.join(parts)}{summ}"
            f"</body></html>"
        )

    # ------------------------------------------------------------------
    # Open in browser
    # ------------------------------------------------------------------

    def _open_web(self):
        """✅ پیش‌نمایش وب با پنجره مستقل (بدون وابستگی به ماژول خارجی)"""
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'پیش‌نمایش', 'یک حواله انتخاب کنید.')
            return
        try:
            html = self._preview_html(row)
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ساخت پیش‌نمایش:\n{e}')
            return
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            dlg = QDialog(self)
            dlg.setWindowTitle('پیش‌نمایش حواله خروج کالا')
            dlg.resize(1400, 900)
            lay = QVBoxLayout(dlg)
            bar = QHBoxLayout()
            print_btn = QPushButton('🖨️ پرینت')
            print_btn.setObjectName('PrimaryButton')
            pdf_btn = QPushButton('💾 ذخیره PDF')
            pdf_btn.setObjectName('SuccessButton')
            close_btn = QPushButton('بستن')
            close_btn.setObjectName('SecondaryButton')
            bar.addWidget(print_btn)
            bar.addWidget(pdf_btn)
            bar.addStretch()
            bar.addWidget(close_btn)
            lay.addLayout(bar)
            view = QWebEngineView()
            view.setHtml(html)
            lay.addWidget(view)
            print_btn.clicked.connect(lambda: self._print_view(view))
            pdf_btn.clicked.connect(lambda: self._save_pdf_from_view(view))
            close_btn.clicked.connect(dlg.accept)
            dlg.exec_()
        except Exception:
            # fallback: مرورگر سیستم
            import webbrowser
            fd, path = tempfile.mkstemp(suffix='.html')
            os.write(fd, html.encode('utf-8'))
            os.close(fd)
            webbrowser.open('file:///' + path.replace('\\', '/'))


    def _print_view(self, view):
        try:
            from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
            printer = QPrinter(QPrinter.HighResolution)
            dlg = QPrintDialog(printer, self)
            if dlg.exec_() == QPrintDialog.Accepted:
                view.page().print_(printer)
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در پرینت:\n{e}')

    def _save_pdf_from_view(self, view):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 'ذخیره فایل PDF', 'حواله-خروج.pdf', 'PDF Files (*.pdf)')
            if not file_path:
                return
            if not file_path.lower().endswith('.pdf'):
                file_path += '.pdf'
            view.page().printToPdf(file_path)
            QMessageBox.information(self, 'موفق', f'فایل PDF ذخیره شد:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در ذخیره PDF:\n{e}')
    def _open_file_cross_platform(path: str):
        """باز کردن فایل در مرورگر پیش‌فرض (سازگار با همه سیستم‌عامل‌ها)"""
        import webbrowser
        webbrowser.open('file:///' + path.replace('\\', '/'))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def _export(self):
        from datetime import datetime
        default = 'خروج_کالا_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.xml'
        path, _ = QFileDialog.getSaveFileName(self, 'خروجی اکسل', default, 'Excel XML (*.xml)')
        if not path:
            return
        if not path.lower().endswith('.xml'):
            path += '.xml'

        def esc(v):
            return str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        hdr = [
            'شماره حواله', 'شماره مرجع', 'مرحله', 'تاریخ', 'مشتری',
            'راننده', 'بارنامه', 'تعداد مرحله', 'تعداد کل بار', 'مبلغ کل', 'وضعیت'
        ]

        xml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?mso-application progid="Excel.Sheet"?>',
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
            'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
            '<Worksheet ss:Name="خروج کالا"><Table>'
        ]

        xml.append(
            '<Row>' +
            ''.join(f'<Cell><Data ss:Type="String">{esc(h)}</Data></Cell>' for h in hdr) +
            '</Row>'
        )

        for i in range(self.tbl.rowCount()):
            xml.append(
                '<Row>' +
                ''.join(
                    f'<Cell><Data ss:Type="String">'
                    f'{esc(self.tbl.item(i, c).text() if self.tbl.item(i, c) else "")}'
                    f'</Data></Cell>'
                    for c in range(len(hdr))
                ) +
                '</Row>'
            )

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
                QMessageBox.critical(
                    self, 'خطا',
                    f'امکان نوشتن نیست. فایل را ببندید یا مسیر دیگری انتخاب کنید.\n{e2}'
                )
                return

        QMessageBox.information(self, 'اکسل', f'فایل با موفقیت ذخیره شد:\n{path}')

    # ------------------------------------------------------------------
    # Jalali date labels
    # ------------------------------------------------------------------


    def _report_by_reference(self):
        """✅ گزارش همه حواله‌های یک مرجع خروج"""
        # پیش‌فرض: مرجع حوالهٔ انتخاب‌شدهٔ فعلی
        row = self.tbl.currentRow()
        default_ref = self._refs[row] if 0 <= row < len(self._refs) else ''
        ref, ok = QInputDialog.getText(
            self, 'گزارش مرجع خروج',
            'شماره مرجع خروج را وارد کنید:',
            text=default_ref
        )
        if not ok or not ref.strip():
            return
        ref = ref.strip()

        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute(
                "SELECT wi.id, wi.issue_no, wi.stage_no, wi.issue_date, wi.waybill_no, wi.issue_status, "
                "       wi.stage_load_qty, wi.delivered_qty, "
                "       ol.reference_no AS ref, ol.total_load_qty AS tlq, ol.id AS load_id, "
                "       COALESCE(d.first_name||' '||d.last_name, '-') AS drv, "
                "       COALESCE(p.first_name||' '||p.last_name, '-') AS cust, "
                "       COALESCE(SUM(ii.qty),0) AS q, COALESCE(SUM(ii.qty*ii.unit_price),0) AS amt "
                "FROM warehouse_issues wi "
                "LEFT JOIN outbound_loads ol ON ol.id=wi.outbound_load_id "
                "LEFT JOIN persons p ON p.id=wi.customer_id "
                "LEFT JOIN persons d ON d.id=wi.driver_id "
                "LEFT JOIN warehouse_issue_items ii ON ii.issue_id=wi.id "
                "WHERE ol.reference_no = ? "
                "GROUP BY wi.id ORDER BY wi.stage_no, wi.id",
                (ref,)
            ).fetchall()

        if not rows:
            QMessageBox.information(self, 'گزارش مرجع', f'هیچ حواله‌ای برای مرجع «{ref}» یافت نشد.')
            return

        self.tbl.setRowCount(len(rows))
        self._ids, self._refs, self._loads, self._custs = [], [], [], []
        for i, r in enumerate(rows):
            self._ids.append(r[0])
            self._refs.append(r[8] or '')
            self._loads.append(r[10])
            self._custs.append(r[12] or '-')
            status = r[5] or ''
            vals = [
                r[1] or '', r[8] or '', str(r[2] or 1),
                jalali_date_display_from_iso(r[3]) if r[3] else '-',
                r[12] or '-', r[11] or '-', r[4] or '-',
                f"{int(r[13] or 0):,}", f"{int(r[6] or 0):,}", f"{int(r[14] or 0):,}",
                STATUS_FA.get(status, status)
            ]
            if status == 'CANCELLED':
                bg, fg = QBrush(QColor(254, 226, 226)), QBrush(QColor(153, 27, 27))
            elif status == 'PARTIAL':
                bg, fg = QBrush(QColor(254, 240, 199)), None
            elif status == 'COMPLETED':
                bg, fg = QBrush(QColor(220, 252, 231)), None
            else:
                bg, fg = None, None
            for cc, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if bg: it.setBackground(bg)
                if fg: it.setForeground(fg)
                self.tbl.setItem(i, cc, it)

        if self.tbl.rowCount():
            self._on_select(0, 0, -1, -1)
        QMessageBox.information(self, 'گزارش مرجع',
                                f'تعداد {len(rows)} حواله برای مرجع «{ref}» نمایش داده شد.')

    def _report_by_issue(self):
        """✅ گزارش یک حوالهٔ خاص"""
        row = self.tbl.currentRow()
        default_issue = self.tbl.item(row, 0).text() if 0 <= row < self.tbl.rowCount() and self.tbl.item(row, 0) else ''
        issue_no, ok = QInputDialog.getText(
            self, 'گزارش حواله مرحله',
            'شماره حواله را وارد کنید:',
            text=default_issue
        )
        if not ok or not issue_no.strip():
            return
        issue_no = issue_no.strip()

        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute(
                "SELECT wi.id, wi.issue_no, wi.stage_no, wi.issue_date, wi.waybill_no, wi.issue_status, "
                "       wi.stage_load_qty, wi.delivered_qty, "
                "       ol.reference_no AS ref, ol.total_load_qty AS tlq, ol.id AS load_id, "
                "       COALESCE(d.first_name||' '||d.last_name, '-') AS drv, "
                "       COALESCE(p.first_name||' '||p.last_name, '-') AS cust, "
                "       COALESCE(SUM(ii.qty),0) AS q, COALESCE(SUM(ii.qty*ii.unit_price),0) AS amt "
                "FROM warehouse_issues wi "
                "LEFT JOIN outbound_loads ol ON ol.id=wi.outbound_load_id "
                "LEFT JOIN persons p ON p.id=wi.customer_id "
                "LEFT JOIN persons d ON d.id=wi.driver_id "
                "LEFT JOIN warehouse_issue_items ii ON ii.issue_id=wi.id "
                "WHERE wi.issue_no = ? "
                "GROUP BY wi.id",
                (issue_no,)
            ).fetchall()

        if not rows:
            QMessageBox.information(self, 'گزارش حواله', f'حواله «{issue_no}» یافت نشد.')
            return

        self.tbl.setRowCount(len(rows))
        self._ids, self._refs, self._loads, self._custs = [], [], [], []
        for i, r in enumerate(rows):
            self._ids.append(r[0])
            self._refs.append(r[8] or '')
            self._loads.append(r[10])
            self._custs.append(r[12] or '-')
            status = r[5] or ''
            vals = [
                r[1] or '', r[8] or '', str(r[2] or 1),
                jalali_date_display_from_iso(r[3]) if r[3] else '-',
                r[12] or '-', r[11] or '-', r[4] or '-',
                f"{int(r[13] or 0):,}", f"{int(r[6] or 0):,}", f"{int(r[14] or 0):,}",
                STATUS_FA.get(status, status)
            ]
            if status == 'CANCELLED':
                bg, fg = QBrush(QColor(254, 226, 226)), QBrush(QColor(153, 27, 27))
            elif status == 'PARTIAL':
                bg, fg = QBrush(QColor(254, 240, 199)), None
            elif status == 'COMPLETED':
                bg, fg = QBrush(QColor(220, 252, 231)), None
            else:
                bg, fg = None, None
            for cc, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if bg: it.setBackground(bg)
                if fg: it.setForeground(fg)
                self.tbl.setItem(i, cc, it)

        if self.tbl.rowCount():
            self._on_select(0, 0, -1, -1)
    def _update_from_jalali(self):
        iso_date = self.from_edit.date().toString('yyyy-MM-dd')
        self.from_jalali_lbl.setText(jalali_date_display_from_iso(iso_date))

    def _update_to_jalali(self):
        iso_date = self.to_edit.date().toString('yyyy-MM-dd')
        self.to_jalali_lbl.setText(jalali_date_display_from_iso(iso_date))
